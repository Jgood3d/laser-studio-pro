"""Générateur de boîte à encoches (assemblage « doigts »), sans dépendance à Qt.

Une boîte rectangulaire est décrite par ses trois dimensions X (largeur),
Y (profondeur) et Z (hauteur), l'épaisseur du matériau et la compensation du
trait de découpe (kerf). Le module calcule les contours des panneaux (jusqu'à
six), prêts à être découpés, et leur disposition sur le plateau.

Convention des repères (mm) — boîte posée sur le plan XY, vue de dessus :
    X vers la droite, Y vers l'arrière, Z vers le haut.
Chaque panneau a un repère local (u, v) tel qu'on le voit DE L'EXTÉRIEUR de la
boîte, haut du panneau vers le haut : un texte gravé en u -> droite, v -> haut
se lit donc à l'endroit sur la face extérieure (voir panel_to_3d).

Principe des encoches : chaque arête de la boîte est partagée par deux
panneaux ; l'un porte les doigts (« mâle »), l'autre les fentes (« femelle »),
en alternance sur n segments égaux (n impair : les extrémités sont des doigts
sur le mâle, des fentes sur la femelle). Pour qu'un coin ne soit occupé que par
un seul panneau, le panneau mâle d'une arête est toujours le plus prioritaire
des deux selon un même ordre de priorité (par défaut : avant, arrière, gauche,
droite, dessus, dessous). Un ordre total garantit qu'en chaque coin un seul
panneau est mâle sur ses deux arêtes : c'est lui qui occupe le coin.
"""
import math
from dataclasses import dataclass, field

FACE_NAMES = ("bottom", "top", "front", "back", "left", "right")
DEFAULT_PRIORITY = ("front", "back", "left", "right", "top", "bottom")

# Dimensions du panneau (a le long de u, b le long de v) : W = X, D = Y, H = Z.
_PANEL_DIMS = {
    "front": ("W", "H"), "back": ("W", "H"),
    "left": ("D", "H"), "right": ("D", "H"),
    "top": ("W", "D"), "bottom": ("W", "D"),
}
# Panneau voisin de chacune des 4 arêtes, dans l'ordre : bas (v=0), droite (u=a), haut (v=b), gauche (u=0).
_NEIGHBORS = {
    "front": ("bottom", "right", "top", "left"),
    "back": ("bottom", "left", "top", "right"),
    "left": ("bottom", "front", "top", "back"),
    "right": ("bottom", "back", "top", "front"),
    "top": ("front", "right", "back", "left"),
    "bottom": ("front", "left", "back", "right"),
}
_EDGES = ("bottom", "right", "top", "left")
_EPS = 1e-9


class BoxError(ValueError):
    """Paramètres de boîte invalides (message prêt à être affiché)."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


@dataclass
class BoxParams:
    width: float                      # X
    depth: float                      # Y
    height: float                     # Z
    thickness: float = 3.0
    kerf: float = 0.0                 # largeur de matière enlevée par le laser
    finger_width: float = 0.0         # largeur visée d'un doigt ; 0 = automatique (3 x épaisseur)
    dimensions: str = "outer"         # "outer" : dimensions extérieures ; "inner" : intérieures
    lid: bool = True                  # False : boîte ouverte (pas de dessus)
    priority: tuple = DEFAULT_PRIORITY
    gap: float = 3.0                  # espace entre panneaux à la disposition
    max_width: float = 0.0            # largeur disponible pour la disposition ; 0 = tout sur une ligne


@dataclass
class Panel:
    name: str
    width: float                      # a : taille nominale le long de u
    height: float                     # b : taille nominale le long de v
    outline: list                     # contour nominal (u, v), anti-horaire, repère local
    cut: list                         # contour de découpe (kerf appliqué), même repère
    x: float = 0.0                    # translation de disposition appliquée à `cut`
    y: float = 0.0

    def placed(self):
        """Contour de découpe en coordonnées plateau (mm)."""
        return [(px + self.x, py + self.y) for px, py in self.cut]

    def bounds(self):
        xs = [p[0] for p in self.placed()]
        ys = [p[1] for p in self.placed()]
        return min(xs), min(ys), max(xs), max(ys)

    def face_center(self):
        """Centre de la face (repère plateau), pour y placer un décor."""
        x0, y0, x1, y1 = self.bounds()
        return (x0 + x1) / 2.0, (y0 + y1) / 2.0


@dataclass
class BoxResult:
    outer: tuple                      # (X, Y, Z) extérieurs retenus
    thickness: float
    panels: list = field(default_factory=list)
    finger_counts: dict = field(default_factory=dict)   # {"W": n, "D": n, "H": n}
    width: float = 0.0                # emprise totale de la disposition
    height: float = 0.0


@dataclass
class BoxDecor:
    """Décor gravé sur une face : un texte ou un fichier SVG, centré sur la face puis décalé de (dx, dy) mm."""
    face: str
    kind: str = "text"              # "text" | "svg"
    text: str = ""
    font_family: str = "Arial"
    size_mm: float = 8.0
    bold: bool = False
    italic: bool = False
    svg_path: str = ""
    width_mm: float = 0.0           # largeur voulue du SVG ; 0 = taille d'origine
    dx: float = 0.0
    dy: float = 0.0


# ----------------------------------------------------------------------
# Validation et nombre de doigts
# ----------------------------------------------------------------------
def odd_finger_count(length, target):
    """Plus grand nombre IMPAIR de segments de largeur >= target dans `length` (au moins 1)."""
    n = int(length // target)
    if n % 2 == 0:
        n -= 1
    return max(n, 1)


def resolve_outer_dimensions(p):
    t = p.thickness
    if p.dimensions == "inner":
        return p.width + 2 * t, p.depth + 2 * t, p.height + 2 * t
    return p.width, p.depth, p.height


def validate(p):
    if p.thickness <= 0:
        raise BoxError("thickness", value=p.thickness)
    if p.kerf < 0 or p.kerf >= p.thickness:
        raise BoxError("kerf", value=p.kerf)
    if p.dimensions not in ("outer", "inner"):
        raise BoxError("dimensions_mode", value=p.dimensions)
    if sorted(p.priority) != sorted(FACE_NAMES):
        raise BoxError("priority", value=p.priority)
    if p.finger_width < 0:
        raise BoxError("finger_width", value=p.finger_width)
    W, D, H = resolve_outer_dimensions(p)
    t = p.thickness
    minimum = 3 * t
    for label, value in (("X", W), ("Y", D), ("Z", H)):
        if value < minimum:
            raise BoxError("too_small", axis=label, value=value, minimum=minimum)
    target = p.finger_width if p.finger_width > 0 else 3 * t
    if target < t:
        raise BoxError("finger_too_small", value=target, minimum=t)
    return W, D, H, target


# ----------------------------------------------------------------------
# Contour d'un panneau
# ----------------------------------------------------------------------
def _segments(length, n):
    step = length / n
    return [(i * step, (i + 1) * step) for i in range(n)]


def _removal_rects(a, b, t, edge, segments, male):
    """Rectangles (x0, y0, x1, y1) à retirer du panneau pour les fentes d'une arête."""
    rects = []
    for i, (s, e) in enumerate(segments):
        slot = (i % 2 == 1) if male else (i % 2 == 0)
        if not slot:
            continue
        if edge == "bottom":
            rects.append((s, 0.0, e, t))
        elif edge == "top":
            rects.append((s, b - t, e, b))
        elif edge == "left":
            rects.append((0.0, s, t, e))
        else:  # right
            rects.append((a - t, s, a, e))
    return rects


def _snap(value):
    return round(float(value), 9) + 0.0          # + 0.0 : évite « -0.0 »


def _simplify(points):
    """Supprime les sommets alignés (et doublons consécutifs)."""
    pts = []
    for p in points:
        if not pts or abs(p[0] - pts[-1][0]) > _EPS or abs(p[1] - pts[-1][1]) > _EPS:
            pts.append(p)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        out = []
        n = len(pts)
        for i in range(n):
            p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
            cross = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
            if abs(cross) < _EPS:
                changed = True
                continue
            out.append(p1)
        pts = out
    return pts


def rectilinear_outline(a, b, removals):
    """Contour (anti-horaire) du rectangle [0,a]x[0,b] privé de rectangles `removals`.

    On découpe le plan en cellules selon toutes les coordonnées en jeu, on garde
    les cellules restantes, puis on suit leur frontière : méthode sans cas
    particuliers pour les coins, où deux arêtes se rejoignent."""
    # Toutes les coordonnées sont arrondies (1e-9 mm) : sans cela, deux valeurs censées
    # être égales (ex. 100 et 11 x 9,0909…) diffèrent de 1e-14 et créent des cellules
    # « fantômes » d'épaisseur nulle, donc des contours multiples.
    a, b = _snap(a), _snap(b)
    removals = [tuple(_snap(v) for v in r) for r in removals]
    xs = sorted({0.0, a, *[min(max(r[0], 0.0), a) for r in removals], *[min(max(r[2], 0.0), a) for r in removals]})
    ys = sorted({0.0, b, *[min(max(r[1], 0.0), b) for r in removals], *[min(max(r[3], 0.0), b) for r in removals]})
    nx, ny = len(xs) - 1, len(ys) - 1

    def inside(ix, iy):
        if ix < 0 or iy < 0 or ix >= nx or iy >= ny:
            return False
        cx = (xs[ix] + xs[ix + 1]) / 2.0
        cy = (ys[iy] + ys[iy + 1]) / 2.0
        for x0, y0, x1, y1 in removals:
            if x0 < cx < x1 and y0 < cy < y1:
                return False
        return True

    edges = {}
    for ix in range(nx):
        for iy in range(ny):
            if not inside(ix, iy):
                continue
            x0, x1, y0, y1 = xs[ix], xs[ix + 1], ys[iy], ys[iy + 1]
            if not inside(ix, iy - 1):
                edges.setdefault((x0, y0), []).append((x1, y0))
            if not inside(ix + 1, iy):
                edges.setdefault((x1, y0), []).append((x1, y1))
            if not inside(ix, iy + 1):
                edges.setdefault((x1, y1), []).append((x0, y1))
            if not inside(ix - 1, iy):
                edges.setdefault((x0, y1), []).append((x0, y0))
    if not edges:
        raise BoxError("empty_panel")
    start = min(edges)
    loop = [start]
    current = start
    while True:
        nxt = edges[current]
        if len(nxt) != 1:
            raise BoxError("pinched_panel", point=current)
        current = nxt[0]
        if current == start:
            break
        loop.append(current)
        if len(loop) > 100000:
            raise BoxError("open_outline")
    used = sum(len(v) for v in edges.values())
    if len(loop) != used:
        raise BoxError("several_outlines")
    return _simplify(loop)


def offset_orthogonal(poly, d):
    """Décale un contour orthogonal anti-horaire de `d` mm vers l'extérieur (d < 0 : vers l'intérieur)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        n1 = (e1[1] / l1, -e1[0] / l1)       # normale sortante d'un contour anti-horaire
        n2 = (e2[1] / l2, -e2[0] / l2)
        out.append((p1[0] + d * (n1[0] + n2[0]), p1[1] + d * (n1[1] + n2[1])))
    return out


def polygon_area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        s += x0 * y1 - x1 * y0
    return s / 2.0


# ----------------------------------------------------------------------
# Boîte complète
# ----------------------------------------------------------------------
def build_box(p):
    """Calcule les panneaux de la boîte (sans disposition : voir layout_panels)."""
    W, D, H, target = validate(p)
    t = p.thickness
    dims = {"W": W, "D": D, "H": H}
    counts = {k: odd_finger_count(v, target) for k, v in dims.items()}
    present = [f for f in FACE_NAMES if p.lid or f != "top"]
    rank = {name: i for i, name in enumerate(p.priority)}

    panels = []
    for name in present:
        a_key, b_key = _PANEL_DIMS[name]
        a, b = dims[a_key], dims[b_key]
        removals = []
        for edge, neighbor in zip(_EDGES, _NEIGHBORS[name]):
            if neighbor not in present:
                continue                                  # arête sans voisin : bord droit
            along = a if edge in ("bottom", "top") else b
            key = a_key if edge in ("bottom", "top") else b_key
            segments = _segments(along, counts[key])
            male = rank[name] < rank[neighbor]
            removals += _removal_rects(a, b, t, edge, segments, male)
        outline = rectilinear_outline(a, b, removals)
        cut = offset_orthogonal(outline, p.kerf / 2.0) if p.kerf > 0 else list(outline)
        panels.append(Panel(name=name, width=a, height=b, outline=outline, cut=cut))
    result = BoxResult(outer=(W, D, H), thickness=t, panels=panels, finger_counts=counts)
    layout_panels(result, p.gap, p.max_width)
    return result


def layout_panels(result, gap=3.0, max_width=0.0):
    """Dispose les panneaux en rangées (les plus hauts d'abord), à partir de (0, 0)."""
    items = []
    for panel in result.panels:
        xs = [q[0] for q in panel.cut]
        ys = [q[1] for q in panel.cut]
        items.append((panel, min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
    items.sort(key=lambda it: (-it[4], -it[3]))
    x = y = row_h = total_w = 0.0
    for panel, minx, miny, w, h in items:
        if max_width > 0 and x > 0 and x + w > max_width + _EPS:
            x, y, row_h = 0.0, y + row_h + gap, 0.0
        panel.x, panel.y = x - minx, y - miny
        x += w + gap
        row_h = max(row_h, h)
        total_w = max(total_w, x - gap)
    result.width = total_w
    result.height = y + row_h


def panel_to_3d(name, u, v, outer, thickness, depth_fraction=0.5):
    """Point 3D (x, y, z) correspondant au point (u, v) du panneau `name`, au milieu de son épaisseur."""
    W, D, H = outer
    t = thickness
    w = t * depth_fraction
    if name == "front":
        return u, w, v
    if name == "back":
        return W - u, D - t + w, v
    if name == "left":
        return w, D - u, v
    if name == "right":
        return W - t + w, u, v
    if name == "top":
        return u, v, H - t + w
    if name == "bottom":
        return W - u, v, w
    raise KeyError(name)


def describe(result):
    """Résumé lisible : nombre de panneaux, doigts par axe, emprise."""
    return {
        "panels": [p.name for p in result.panels],
        "fingers": dict(result.finger_counts),
        "footprint": (round(result.width, 2), round(result.height, 2)),
    }
