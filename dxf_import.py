"""Lecteur de fichiers DXF (format texte ASCII), sans dépendance externe ni Qt.

Transforme les entités géométriques d'un dessin en tracés (listes de points en
mm, ouverts ou fermés) que l'éditeur vectoriel sait importer, comme il le fait
pour un SVG.

Entités prises en charge : LINE, LWPOLYLINE et POLYLINE (avec arrondis « bulge »),
CIRCLE, ARC, ELLIPSE, SPLINE (B-splines rationnelles, sinon points d'ajustage) et
INSERT (blocs, imbriqués, avec rotation, échelle, symétrie et réseaux).
Les autres entités (TEXT, MTEXT, HATCH, DIMENSION, POINT, SOLID...) sont ignorées
et comptées dans `DxfDrawing.skipped` pour pouvoir le signaler à l'utilisateur.

Repère : celui du fichier (Y vers le haut), ramené en millimètres grâce à
$INSUNITS (mm si l'unité est absente). Les courbes sont découpées en segments avec
une flèche maximale de `tolerance` mm.
"""
import math
from dataclasses import dataclass, field

# Facteur vers le millimètre selon $INSUNITS (0 = sans unité : on suppose des mm).
INSUNITS_TO_MM = {
    0: 1.0, 1: 25.4, 2: 304.8, 3: 1609344.0, 4: 1.0, 5: 10.0, 6: 1000.0, 7: 1000000.0,
    8: 0.0000254, 9: 0.0254, 10: 914.4, 11: 1e-7, 12: 1e-6, 13: 0.001, 14: 100.0,
    15: 10000.0, 16: 1e12, 17: 1e9, 18: 1.496e14, 19: 9.4607e18, 20: 3.0857e19,
}
MAX_INSERT_DEPTH = 8
_ARRAY_LIMIT = 10000


class DxfError(ValueError):
    """Fichier illisible ; `code` identifie le cas pour le message affiché."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


@dataclass
class DxfPath:
    points: list            # [(x, y), ...] en mm
    closed: bool
    layer: str = "0"
    kind: str = ""          # type d'entité d'origine (LINE, ARC...)


@dataclass
class DxfDrawing:
    paths: list = field(default_factory=list)
    units_code: int = 0
    scale_to_mm: float = 1.0
    skipped: dict = field(default_factory=dict)      # {"TEXT": 3, ...}
    layers: list = field(default_factory=list)       # noms de calques DXF rencontrés, dans l'ordre

    def bounds(self):
        xs = [p[0] for path in self.paths for p in path.points]
        ys = [p[1] for path in self.paths for p in path.points]
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)


# ----------------------------------------------------------------------
# Lecture des balises
# ----------------------------------------------------------------------
def decode_dxf(data):
    """Décode le contenu binaire d'un fichier DXF texte (UTF-8, sinon Windows-1252)."""
    if data.startswith(b"AutoCAD Binary DXF"):
        raise DxfError("binary")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def read_tags(text):
    """Liste de (code, valeur) : le DXF alterne une ligne « code de groupe » et une ligne « valeur »."""
    lines = text.splitlines()
    tags = []
    for i in range(0, len(lines) - 1, 2):
        raw = lines[i].strip()
        try:
            code = int(raw)
        except ValueError:
            raise DxfError("not_dxf", line=i + 1)
        tags.append((code, lines[i + 1].strip()))
    if not tags:
        raise DxfError("not_dxf", line=1)
    return tags


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def split_sections(tags):
    """{"HEADER": [...], "BLOCKS": [...], "ENTITIES": [...]} : balises de chaque section (sans SECTION/ENDSEC)."""
    sections = {}
    i, n = 0, len(tags)
    while i < n:
        if tags[i] == (0, "SECTION") and i + 1 < n and tags[i + 1][0] == 2:
            name = tags[i + 1][1].upper()
            j = i + 2
            while j < n and tags[j] != (0, "ENDSEC"):
                j += 1
            sections[name] = tags[i + 2:j]
            i = j + 1
        else:
            i += 1
    return sections


def header_units(header_tags):
    for i, (code, value) in enumerate(header_tags):
        if code == 9 and value.upper() == "$INSUNITS":
            for c2, v2 in header_tags[i + 1:i + 3]:
                if c2 == 70:
                    return _int(v2)
    return 0


def split_records(tags):
    """Découpe une liste de balises en enregistrements [(0, TYPE), (code, valeur), ...]."""
    records, current = [], None
    for code, value in tags:
        if code == 0:
            if current is not None:
                records.append(current)
            current = [(0, value.upper())]
        elif current is not None:
            current.append((code, value))
    if current is not None:
        records.append(current)
    return records


def parse_blocks(block_tags):
    """{nom: (point_de_base, [enregistrements])} depuis la section BLOCKS."""
    blocks = {}
    records = split_records(block_tags)
    i = 0
    while i < len(records):
        rec = records[i]
        if rec[0][1] == "BLOCK":
            name, bx, by = "", 0.0, 0.0
            for code, value in rec[1:]:
                if code == 2 and not name:
                    name = value
                elif code == 10:
                    bx = _float(value)
                elif code == 20:
                    by = _float(value)
            body = []
            i += 1
            while i < len(records) and records[i][0][1] != "ENDBLK":
                body.append(records[i])
                i += 1
            blocks[name.upper()] = ((bx, by), group_polylines(body))
        i += 1
    return blocks


def group_polylines(records):
    """Rattache chaque VERTEX à son POLYLINE (jusqu'à SEQEND) : ("POLYLINE", tags, [vertex_tags])."""
    out, i = [], 0
    while i < len(records):
        rec = records[i]
        kind = rec[0][1]
        if kind == "POLYLINE":
            vertices = []
            i += 1
            while i < len(records) and records[i][0][1] not in ("SEQEND",):
                if records[i][0][1] == "VERTEX":
                    vertices.append(records[i])
                i += 1
            out.append(("POLYLINE", rec, vertices))
        elif kind in ("VERTEX", "SEQEND", "ENDBLK"):
            pass
        else:
            out.append((kind, rec, None))
        i += 1
    return out


# ----------------------------------------------------------------------
# Géométrie
# ----------------------------------------------------------------------
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)      # x' = a x + c y + tx ; y' = b x + d y + ty


def mat_mul(m, n):
    """Applique n d'abord, puis m."""
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def mat_apply(m, p):
    a, b, c, d, e, f = m
    return (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f)


def _segments_for(radius, sweep, tol):
    """Nombre de segments pour décrire `sweep` radians d'un cercle de rayon `radius` avec une flèche <= tol."""
    if radius <= tol:
        step = math.pi / 2
    else:
        step = 2 * math.acos(max(-1.0, min(1.0, 1 - tol / radius)))
    step = max(step, 1e-3)
    return max(1, int(math.ceil(abs(sweep) / step - 1e-9)))


def arc_points(cx, cy, r, a0, sweep, tol):
    """Points d'un arc de centre (cx, cy), rayon r, de l'angle a0 (rad) sur `sweep` rad (signé)."""
    n = _segments_for(r, sweep, tol)
    return [(cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n)) for k in range(n + 1)]


def bulge_arc(p0, p1, bulge, tol):
    """Points intermédiaires + p1 de l'arc défini par un « bulge » (tan(angle/4)) entre p0 et p1."""
    c = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    if c < 1e-12 or abs(bulge) < 1e-12:
        return [p1]
    ux, uy = (p1[0] - p0[0]) / c, (p1[1] - p0[1]) / c
    nr = (uy, -ux)                                     # normale à droite de p0 -> p1
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    off = (c / 2) * (bulge * bulge - 1) / (2 * bulge)
    center = (mid[0] + nr[0] * off, mid[1] + nr[1] * off)
    r = math.hypot(p0[0] - center[0], p0[1] - center[1])
    a0 = math.atan2(p0[1] - center[1], p0[0] - center[0])
    sweep = 4 * math.atan(bulge)
    pts = arc_points(center[0], center[1], r, a0, sweep, tol)
    pts[-1] = p1
    return pts[1:]


def _find_span(n, p, t, knots):
    if t >= knots[n + 1]:
        return n
    if t <= knots[p]:
        return p
    low, high = p, n + 1
    mid = (low + high) // 2
    while t < knots[mid] or t >= knots[mid + 1]:
        if t < knots[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
    return mid


def _basis(span, t, p, knots):
    basis = [1.0]
    left = [0.0] * (p + 1)
    right = [0.0] * (p + 1)
    for j in range(1, p + 1):
        left[j] = t - knots[span + 1 - j]
        right[j] = knots[span + j] - t
        saved = 0.0
        for r in range(j):
            denom = right[r + 1] + left[j - r]
            temp = basis[r] / denom if denom else 0.0
            basis[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        basis.append(saved)
    return basis


def nurbs_points(degree, knots, ctrl, weights, samples):
    """Échantillonne une B-spline rationnelle ; None si les données sont incohérentes."""
    n = len(ctrl) - 1
    if degree < 1 or n < degree or len(knots) != n + degree + 2:
        return None
    if weights is None or len(weights) != len(ctrl):
        weights = [1.0] * len(ctrl)
    t0, t1 = knots[degree], knots[n + 1]
    if t1 <= t0:
        return None
    pts = []
    for k in range(samples + 1):
        t = t0 + (t1 - t0) * k / samples
        span = _find_span(n, degree, t, knots)
        b = _basis(span, t, degree, knots)
        x = y = w = 0.0
        for j in range(degree + 1):
            idx = span - degree + j
            bw = b[j] * weights[idx]
            x += bw * ctrl[idx][0]
            y += bw * ctrl[idx][1]
            w += bw
        if abs(w) < 1e-12:
            return None
        pts.append((x / w, y / w))
    return pts


def catmull_rom(points, closed, per_segment=12):
    """Courbe passant par des points d'ajustage (spline sans points de contrôle)."""
    n = len(points)
    if n < 3:
        return list(points)
    out = []
    count = n if closed else n - 1
    for i in range(count):
        p0 = points[(i - 1) % n] if (closed or i > 0) else points[0]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n] if (closed or i + 2 < n) else points[-1]
        for k in range(per_segment):
            t = k / per_segment
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(points[-1])
    return out


# ----------------------------------------------------------------------
# Entités -> tracés (dans le repère du dessin, avant mise à l'échelle)
# ----------------------------------------------------------------------
def _layer(tags):
    for code, value in tags:
        if code == 8:
            return value
    return "0"


def _mirrored(tags):
    """Extrusion (0, 0, -1) : le repère de l'entité est retourné autour de Y (x -> -x)."""
    for code, value in tags:
        if code == 230 and _float(value, 1.0) < 0:
            return True
    return False


def _values(tags, code):
    return [_float(v) for c, v in tags if c == code]


def _first(tags, code, default=0.0):
    for c, v in tags:
        if c == code:
            return _float(v, default)
    return default


def entity_paths(kind, tags, vertices, tol):
    """[(points, fermé), ...] pour une entité ; None si le type n'est pas géré."""
    mirror = _mirrored(tags)
    flip = (lambda p: (-p[0], p[1])) if mirror else (lambda p: p)

    if kind == "LINE":
        p0 = (_first(tags, 10), _first(tags, 20))
        p1 = (_first(tags, 11), _first(tags, 21))
        return [([p0, p1], False)]

    if kind == "CIRCLE":
        c = flip((_first(tags, 10), _first(tags, 20)))
        r = _first(tags, 40)
        if r <= 0:
            return []
        pts = arc_points(c[0], c[1], r, 0.0, 2 * math.pi, tol)
        return [(pts[:-1], True)]

    if kind == "ARC":
        r = _first(tags, 40)
        if r <= 0:
            return []
        a0 = math.radians(_first(tags, 50))
        a1 = math.radians(_first(tags, 51))
        sweep = (a1 - a0) % (2 * math.pi) or 2 * math.pi
        cx, cy = _first(tags, 10), _first(tags, 20)
        pts = arc_points(cx, cy, r, a0, sweep, tol)
        return [([flip(p) for p in pts], False)]

    if kind == "ELLIPSE":
        cx, cy = _first(tags, 10), _first(tags, 20)
        mx, my = _first(tags, 11), _first(tags, 21)
        ratio = _first(tags, 40, 1.0)
        t0, t1 = _first(tags, 41, 0.0), _first(tags, 42, 2 * math.pi)
        major = math.hypot(mx, my)
        if major <= 0:
            return []
        sweep = (t1 - t0) % (2 * math.pi) or 2 * math.pi
        n = max(8, _segments_for(major, sweep, tol))
        nx, ny = -my * ratio, mx * ratio                 # demi petit axe : grand axe tourné de 90°, x ratio
        pts = [(cx + mx * math.cos(t0 + sweep * k / n) + nx * math.sin(t0 + sweep * k / n),
                cy + my * math.cos(t0 + sweep * k / n) + ny * math.sin(t0 + sweep * k / n)) for k in range(n + 1)]
        full = abs(sweep - 2 * math.pi) < 1e-9
        return [(pts[:-1] if full else pts, full)]

    if kind == "LWPOLYLINE":
        flags = _int(next((v for c, v in tags if c == 70), 0))
        verts = []                                       # [x, y, bulge]
        for code, value in tags:
            if code == 10:
                verts.append([_float(value), 0.0, 0.0])
            elif code == 20 and verts:
                verts[-1][1] = _float(value)
            elif code == 42 and verts:
                verts[-1][2] = _float(value)
        return [_polyline_path([(flip((v[0], v[1])), -v[2] if mirror else v[2]) for v in verts], bool(flags & 1), tol)]

    if kind == "POLYLINE":
        flags = _int(next((v for c, v in tags if c == 70), 0))
        if flags & (16 | 64):                            # maillage 3D / polyface : pas un tracé 2D
            return None
        verts = []
        for rec in vertices or []:
            vt = rec[1:]
            vflags = _int(next((v for c, v in vt if c == 70), 0))
            if vflags & (16 | 128):                      # points de contrôle de spline / index de polyface
                continue
            verts.append((flip((_first(vt, 10), _first(vt, 20))), -_first(vt, 42) if mirror else _first(vt, 42)))
        return [_polyline_path(verts, bool(flags & 1), tol)]

    if kind == "SPLINE":
        return [_spline_path(tags, tol)]

    return None


def _polyline_path(verts, closed, tol):
    """verts : [((x, y), bulge), ...] -> (points, fermé), arrondis développés."""
    if len(verts) < 2:
        return ([v[0] for v in verts], False)
    pts = [verts[0][0]]
    count = len(verts) if closed else len(verts) - 1
    for i in range(count):
        p0, bulge = verts[i]
        p1 = verts[(i + 1) % len(verts)][0]
        pts += bulge_arc(p0, p1, bulge, tol)
    if closed and len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-9:
        pts.pop()
    return (pts, closed)


def _spline_path(tags, tol):
    flags = _int(next((v for c, v in tags if c == 70), 0))
    closed = bool(flags & 1)
    degree = _int(next((v for c, v in tags if c == 71), 3), 3)
    knots = _values(tags, 40)
    weights = _values(tags, 41)
    ctrl = []
    for code, value in tags:                  # points de contrôle : codes 10 / 20
        if code == 10:
            ctrl.append([_float(value), 0.0])
        elif code == 20 and ctrl:
            ctrl[-1][1] = _float(value)
    # points d'ajustage : codes 11 / 21
    fx = [_float(v) for c, v in tags if c == 11]
    fy = [_float(v) for c, v in tags if c == 21]
    fit = list(zip(fx, fy))
    ctrl = [tuple(c) for c in ctrl]
    if len(ctrl) > degree:
        length = sum(math.hypot(ctrl[i + 1][0] - ctrl[i][0], ctrl[i + 1][1] - ctrl[i][1]) for i in range(len(ctrl) - 1))
        samples = max(24, min(4000, int(length / max(tol, 1e-6) ** 0.5) + 8 * len(ctrl)))
        pts = nurbs_points(degree, knots, ctrl, weights or None, samples)
        if pts:
            if closed and len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
                pts.pop()
            return (pts, closed)
    if len(fit) >= 2:
        return (catmull_rom(fit, closed), closed)
    if len(ctrl) >= 2:
        return (ctrl, closed)
    return ([], False)


# ----------------------------------------------------------------------
# Dessin complet
# ----------------------------------------------------------------------
class _Reader:
    def __init__(self, blocks, tol_units):
        self.blocks = blocks
        self.tol = tol_units
        self.paths = []
        self.skipped = {}
        self.layers = []

    def note_layer(self, layer):
        if layer not in self.layers:
            self.layers.append(layer)

    def skip(self, kind):
        self.skipped[kind] = self.skipped.get(kind, 0) + 1

    def read(self, entities, matrix, inherited_layer=None, depth=0):
        for kind, rec, vertices in entities:
            tags = rec[1:]
            layer = _layer(tags)
            if inherited_layer is not None and layer == "0":
                layer = inherited_layer
            if kind == "INSERT":
                self._insert(tags, matrix, layer, depth)
                continue
            result = entity_paths(kind, tags, vertices, self.tol)
            if result is None:
                self.skip(kind)
                continue
            self.note_layer(layer)
            for pts, closed in result:
                if len(pts) < 2:
                    continue
                self.paths.append(DxfPath([mat_apply(matrix, p) for p in pts], closed, layer, kind))

    def _insert(self, tags, matrix, layer, depth):
        name = next((v for c, v in tags if c == 2), "").upper()
        block = self.blocks.get(name)
        if block is None or depth >= MAX_INSERT_DEPTH:
            self.skip("INSERT")
            return
        (bx, by), body = block
        ix, iy = _first(tags, 10), _first(tags, 20)
        sx, sy = _first(tags, 41, 1.0), _first(tags, 42, 1.0)
        rot = math.radians(_first(tags, 50))
        cols = max(1, _int(next((v for c, v in tags if c == 70), 1), 1))
        rows = max(1, _int(next((v for c, v in tags if c == 71), 1), 1))
        dx, dy = _first(tags, 44), _first(tags, 45)
        if cols * rows > _ARRAY_LIMIT:
            self.skip("INSERT")
            return
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        local = mat_mul((cos_r, sin_r, -sin_r, cos_r, 0.0, 0.0), (sx, 0.0, 0.0, sy, 0.0, 0.0))
        local = mat_mul(local, (1.0, 0.0, 0.0, 1.0, -bx, -by))
        for r in range(rows):
            for c in range(cols):
                ox = ix + c * dx * cos_r - r * dy * sin_r
                oy = iy + c * dx * sin_r + r * dy * cos_r
                placed = mat_mul((1.0, 0.0, 0.0, 1.0, ox, oy), local)
                self.read(body, mat_mul(matrix, placed), inherited_layer=layer, depth=depth + 1)


def join_paths(paths, tol=0.01):
    """Réunit bout à bout les tracés ouverts d'un même calque (des LINE séparées deviennent un contour fermé)."""
    result = [p for p in paths if p.closed]
    grid = max(tol, 1e-6)

    def key(pt):
        return (round(pt[0] / grid), round(pt[1] / grid))

    layers = []
    for p in paths:
        if not p.closed and p.layer not in layers:
            layers.append(p.layer)
    for layer in layers:
        items = [p for p in paths if not p.closed and p.layer == layer]
        used = [False] * len(items)
        ends = {}
        for i, p in enumerate(items):
            for which, pt in ((0, p.points[0]), (1, p.points[-1])):
                ends.setdefault(key(pt), []).append((i, which))

        def find(pt):
            kx, ky = key(pt)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for i, which in ends.get((kx + dx, ky + dy), []):
                        if not used[i]:
                            q = items[i].points[0 if which == 0 else -1]
                            if math.hypot(q[0] - pt[0], q[1] - pt[1]) <= tol:
                                return i, which
            return None

        for i, p in enumerate(items):
            if used[i]:
                continue
            used[i] = True
            chain = list(p.points)
            kinds = {p.kind}
            for grow_tail in (True, False):
                if not grow_tail:
                    chain.reverse()                  # on prolonge maintenant l'autre extrémité
                while True:
                    hit = find(chain[-1])
                    if hit is None:
                        break
                    j, which = hit
                    used[j] = True
                    nxt = list(items[j].points)
                    if which == 1:
                        nxt.reverse()
                    chain += nxt[1:]
                    kinds.add(items[j].kind)
            chain.reverse()                          # retour au sens d'origine du premier tracé
            closed = len(chain) > 2 and math.hypot(chain[0][0] - chain[-1][0], chain[0][1] - chain[-1][1]) <= tol
            if closed:
                chain.pop()
            result.append(DxfPath(chain, closed, layer, "+".join(sorted(k for k in kinds if k))))
    return result


def _clean(points, eps=1e-9):
    out = []
    for p in points:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    return out


def parse_dxf_text(text, tolerance=0.01, join=True):
    """Analyse le texte d'un DXF et renvoie un DxfDrawing en millimètres."""
    sections = split_sections(read_tags(text))
    if "ENTITIES" not in sections:
        raise DxfError("no_entities")
    units = header_units(sections.get("HEADER", []))
    scale = INSUNITS_TO_MM.get(units, 1.0)
    reader = _Reader(parse_blocks(sections.get("BLOCKS", [])), tolerance / scale)
    reader.read(group_polylines(split_records(sections["ENTITIES"])), IDENTITY)
    paths = []
    for p in reader.paths:
        pts = _clean([(x * scale, y * scale) for x, y in p.points])
        if p.closed and len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-9:
            pts.pop()
        if len(pts) >= 2:
            paths.append(DxfPath(pts, p.closed and len(pts) >= 3, p.layer, p.kind))
    if join:
        paths = join_paths(paths, tol=max(tolerance, 1e-3))
    return DxfDrawing(paths=paths, units_code=units, scale_to_mm=scale, skipped=reader.skipped, layers=reader.layers)


def read_dxf(path, tolerance=0.01, join=True):
    """Lit un fichier DXF (ASCII) et renvoie un DxfDrawing en millimètres."""
    with open(path, "rb") as f:
        data = f.read()
    return parse_dxf_text(decode_dxf(data), tolerance=tolerance, join=join)


_UNIT_LABELS = {1: "in", 2: "ft", 4: "mm", 5: "cm", 6: "m", 9: "mil", 13: "µm", 14: "dm"}


def units_label(drawing):
    """Libellé court de l'unité du fichier (« mm » si aucune unité n'est indiquée)."""
    if drawing.units_code in _UNIT_LABELS:
        return _UNIT_LABELS[drawing.units_code]
    if drawing.units_code == 0:
        return "mm"
    return f"x{drawing.scale_to_mm:g} mm"
