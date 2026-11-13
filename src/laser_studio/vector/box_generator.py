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

Couvercles (`lid_type`) : « none » (boîte ouverte), « finger » (dessus à doigts),
« lip » (plaque posée + rebord intérieur qui la centre), « sliding » (plaque qui
coulisse dans une rainure des parois gauche / droite ; la façade est abaissée).

Cloisons (`dividers_x`, `dividers_y`) : plaques verticales qui partagent
l'intérieur en compartiments égaux. Leurs languettes traversent des fentes
(trous) découpées dans les parois et dans le fond ; quand les deux sens sont
présents, elles s'emboîtent à mi-hauteur (assemblage « à moitié »).
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
LID_TYPES = ("none", "finger", "lip", "sliding")
MAX_DIVIDERS = 20


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
    lid_type: str = "finger"          # voir LID_TYPES (ignoré si lid est False : boîte ouverte)
    clearance: float = 0.1            # jeu des assemblages « libres » : couvercle, rainure, fentes de cloison
    dividers_x: int = 0               # cloisons qui partagent la largeur (plans perpendiculaires à X)
    dividers_y: int = 0               # cloisons qui partagent la profondeur (plans perpendiculaires à Y)


@dataclass
class Panel:
    name: str
    width: float                      # a : taille nominale le long de u
    height: float                     # b : taille nominale le long de v
    outline: list                     # contour nominal (u, v), anti-horaire, repère local
    cut: list                         # contour de découpe (kerf appliqué), même repère
    x: float = 0.0                    # translation de disposition appliquée à `cut`
    y: float = 0.0
    holes: list = field(default_factory=list)   # trous de découpe (fentes de cloison), kerf appliqué

    def placed(self):
        """Contour de découpe en coordonnées plateau (mm)."""
        return [(px + self.x, py + self.y) for px, py in self.cut]

    def placed_holes(self):
        """Trous de découpe en coordonnées plateau (mm)."""
        return [[(px + self.x, py + self.y) for px, py in hole] for hole in self.holes]

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
    lid_type: str = "finger"
    dividers: tuple = (0, 0)          # (cloisons en X, cloisons en Y)
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


def lid_kind(p):
    """Type de couvercle effectif : « none » si la boîte est ouverte."""
    return p.lid_type if p.lid else "none"


def wall_heights(p, H):
    """(hauteur des parois, hauteur de la façade). Seule la façade d'un couvercle coulissant est plus basse."""
    t, cl = p.thickness, p.clearance
    kind = lid_kind(p)
    if kind == "lip":
        return H - t, H - t
    if kind == "sliding":
        return H, H - 2 * t - cl
    return H, H


def divider_top(p, H):
    """Cote Z du haut des cloisons : elles restent sous le couvercle."""
    t, cl = p.thickness, p.clearance
    return {"none": H, "finger": H - t, "lip": H - 2 * t, "sliding": H - 2 * t - cl}[lid_kind(p)]


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
    if p.lid_type not in LID_TYPES:
        raise BoxError("lid_type", value=p.lid_type)
    if p.clearance < 0 or p.clearance >= p.thickness:
        raise BoxError("clearance", value=p.clearance)
    for n in (p.dividers_x, p.dividers_y):
        if int(n) != n or n < 0 or n > MAX_DIVIDERS:
            raise BoxError("dividers", value=n, maximum=MAX_DIVIDERS)
    W, D, H = resolve_outer_dimensions(p)
    t = p.thickness
    minimum = 3 * t
    for label, value in (("X", W), ("Y", D), ("Z", H)):
        if value < minimum:
            raise BoxError("too_small", axis=label, value=value, minimum=minimum)
    wall_h = min(wall_heights(p, H))
    if wall_h < minimum - _EPS:
        raise BoxError("too_small", axis="Z", value=wall_h, minimum=minimum)
    target = p.finger_width if p.finger_width > 0 else 3 * t
    if target < t:
        raise BoxError("finger_too_small", value=target, minimum=t)
    for label, total, n in (("X", W, p.dividers_x), ("Y", D, p.dividers_y)):
        if n:
            room = ((total - 2 * t) - n * t) / (n + 1)
            if room < minimum - _EPS:
                raise BoxError("compartment_too_small", axis=label, value=room, minimum=minimum)
    if p.dividers_x or p.dividers_y:
        height = divider_top(p, H) - t
        if height < minimum - _EPS:
            raise BoxError("dividers_too_low", value=height, minimum=minimum)
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


def rectilinear_loops(rects, removals=()):
    """Contours de l'union des rectangles `rects` privée des rectangles `removals`.

    Chaque rectangle est (x0, y0, x1, y1). La matière reste TOUJOURS à gauche du sens de
    parcours : contour extérieur anti-horaire, trous horaires (aire négative).

    On découpe le plan en cellules selon toutes les coordonnées en jeu, on garde
    les cellules remplies, puis on suit leur frontière : méthode sans cas
    particuliers pour les coins, où deux arêtes se rejoignent."""
    # Toutes les coordonnées sont arrondies (1e-9 mm) : sans cela, deux valeurs censées
    # être égales (ex. 100 et 11 x 9,0909…) diffèrent de 1e-14 et créent des cellules
    # « fantômes » d'épaisseur nulle, donc des contours multiples.
    rects = [tuple(_snap(v) for v in r) for r in rects]
    removals = [tuple(_snap(v) for v in r) for r in removals]
    xs = sorted({v for r in rects + removals for v in (r[0], r[2])})
    ys = sorted({v for r in rects + removals for v in (r[1], r[3])})
    nx, ny = len(xs) - 1, len(ys) - 1

    def inside(ix, iy):
        if ix < 0 or iy < 0 or ix >= nx or iy >= ny:
            return False
        cx = (xs[ix] + xs[ix + 1]) / 2.0
        cy = (ys[iy] + ys[iy + 1]) / 2.0
        if not any(x0 < cx < x1 and y0 < cy < y1 for x0, y0, x1, y1 in rects):
            return False
        return not any(x0 < cx < x1 and y0 < cy < y1 for x0, y0, x1, y1 in removals)

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
    loops = []
    while edges:
        start = min(edges)
        loop = [start]
        current = start
        while True:
            nxt = edges.pop(current, None)
            if nxt is None:
                raise BoxError("open_outline")
            if len(nxt) != 1:
                raise BoxError("pinched_panel", point=current)
            current = nxt[0]
            if current == start:
                break
            loop.append(current)
            if len(loop) > 100000:
                raise BoxError("open_outline")
        loops.append(_simplify(loop))
    return loops


def rectilinear_outline(a, b, removals):
    """Contour (anti-horaire) du rectangle [0,a]x[0,b] privé de rectangles `removals` (un seul contour)."""
    loops = rectilinear_loops([(0.0, 0.0, a, b)], removals)
    if len(loops) != 1:
        raise BoxError("several_outlines")
    return loops[0]


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
def _make_panel(name, a, b, kerf, rects=None, removals=()):
    """Panneau nominal a x b (ou union de `rects`) moins `removals`, avec trous éventuels ; kerf appliqué."""
    loops = rectilinear_loops(rects or [(0.0, 0.0, a, b)], removals)
    outers = [loop for loop in loops if polygon_area(loop) > 0]
    if len(outers) != 1:
        raise BoxError("several_outlines")
    outline = outers[0]
    holes = [loop for loop in loops if polygon_area(loop) < 0]
    half = kerf / 2.0
    cut = offset_orthogonal(outline, half) if kerf > 0 else list(outline)
    # Matière à gauche : « vers l'extérieur de la matière » = vers le centre du trou, qui rétrécit.
    cut_holes = [offset_orthogonal(h, half) if kerf > 0 else list(h) for h in holes]
    return Panel(name=name, width=a, height=b, outline=outline, cut=cut, holes=cut_holes)


def _tab_intervals(start, end, target, t):
    """Languettes dans [start, end] : segments égaux, impairs (>= 3), une languette un segment sur deux.

    Les deux segments des extrémités restent vides (>= t) : une languette ne touche jamais
    une autre pièce ni le bord."""
    length = end - start
    if length < 3 * t - _EPS:
        return []
    n = max(3, odd_finger_count(length, target))
    step = length / n
    return [(start + i * step, start + (i + 1) * step) for i in range(1, n, 2)]


def _free_intervals(length, excluded):
    """Intervalles de [0, length] hors des intervalles `excluded`."""
    out, cursor = [], 0.0
    for a, b in sorted(excluded):
        if a > cursor + _EPS:
            out.append((cursor, a))
        cursor = max(cursor, b)
    if length > cursor + _EPS:
        out.append((cursor, length))
    return out


def divider_positions(total, n, t):
    """Position (coin inférieur) des n cloisons dans [0, total] : compartiments égaux entre les parois."""
    room = ((total - 2 * t) - n * t) / (n + 1)
    return [t + (k + 1) * room + k * t for k in range(n)]


def _build_dividers(p, W, D, H, target, extra):
    """Cloisons : panneaux + fentes à ajouter aux parois et au fond (dans `extra`, par nom de panneau)."""
    t, cl, half = p.thickness, p.clearance, p.clearance / 2.0
    nx, ny = int(p.dividers_x), int(p.dividers_y)
    xs, ys = divider_positions(W, nx, t), divider_positions(D, ny, t)
    height = divider_top(p, H) - t
    end_tabs = _tab_intervals(0.0, height, target, t)          # verticales : dans les parois
    # Intervalles occupés par les cloisons de l'autre sens (en coordonnée le long de la cloison).
    cross_x = [(y - t - half, y + half) for y in ys]            # cloisons en X croisées par les cloisons en Y
    cross_y = [(x - t - half, x + half) for x in xs]
    panels = []

    def divider(name, span, pos_list, notch_top, others):
        bottom_tabs = []
        for a, b in _free_intervals(span, others):
            bottom_tabs += _tab_intervals(a, b, target, t)
        rects = [(t, t, t + span, t + height)]
        removals = []
        for s, e in bottom_tabs:
            rects.append((t + s, 0.0, t + e, t))
        for s, e in end_tabs:
            rects.append((0.0, t + s, t, t + e))
            rects.append((t + span, t + s, 2 * t + span, t + e))
        for s, e in others:
            if notch_top:
                removals.append((t + s, t + height - height / 2.0, t + e, t + height))
            else:
                removals.append((t + s, 0.0, t + e, t + height / 2.0))
        panels.append(_make_panel(name, span + 2 * t, height + t, p.kerf, rects, removals))
        return bottom_tabs

    for k, x in enumerate(xs):                                  # cloison dans un plan x = const : longe Y
        bottom_tabs = divider(f"divider_x{k + 1}", D - 2 * t, xs, True, cross_x)
        x0, x1 = x - half, x + t + half
        for s, e in end_tabs:
            extra["front"].append((x0, t + s, x1, t + e))
            extra["back"].append((W - x1, t + s, W - x0, t + e))
        for s, e in bottom_tabs:
            extra["bottom"].append((W - x1, t + s, W - x0, t + e))
    for j, y in enumerate(ys):                                  # cloison dans un plan y = const : longe X
        bottom_tabs = divider(f"divider_y{j + 1}", W - 2 * t, ys, False, cross_y)
        y0, y1 = y - half, y + t + half
        for s, e in end_tabs:
            extra["left"].append((D - y1, t + s, D - y0, t + e))
            extra["right"].append((y0, t + s, y1, t + e))
        for s, e in bottom_tabs:
            extra["bottom"].append((W - (t + e), y0, W - (t + s), y1))
    return panels


def build_box(p):
    """Calcule les panneaux de la boîte (sans disposition : voir layout_panels)."""
    W, D, H, target = validate(p)
    t, cl = p.thickness, p.clearance
    kind = lid_kind(p)
    wall_h, front_h = wall_heights(p, H)
    dims = {"W": W, "D": D, "H": wall_h}
    counts = {k: odd_finger_count(v, target) for k, v in dims.items()}
    front_count = odd_finger_count(front_h, target)       # arêtes verticales de la façade (couvercle coulissant)
    jointed = [f for f in FACE_NAMES if f != "top" or kind == "finger"]
    rank = {name: i for i, name in enumerate(p.priority)}
    extra = {name: [] for name in FACE_NAMES}              # fentes de cloison, par panneau
    dividers = _build_dividers(p, W, D, H, target, extra) if (p.dividers_x or p.dividers_y) else []

    def edge_pattern(name, edge, neighbor, a_key, b_key):
        if kind == "sliding" and ((name == "front" and edge in ("left", "right"))
                                  or (name in ("left", "right") and neighbor == "front")):
            return front_h, front_count
        key = a_key if edge in ("bottom", "top") else b_key
        return dims[key], counts[key]

    panels = []
    for name in jointed:
        a_key, b_key = _PANEL_DIMS[name]
        a, b = dims[a_key], dims[b_key]
        if kind == "sliding" and name == "front":
            b = front_h
        removals = list(extra[name])
        for edge, neighbor in zip(_EDGES, _NEIGHBORS[name]):
            if neighbor not in jointed:
                continue                                  # arête sans voisin : bord droit
            length, n = edge_pattern(name, edge, neighbor, a_key, b_key)
            male = rank[name] < rank[neighbor]
            removals += _removal_rects(a, b, t, edge, _segments(length, n), male)
        if kind == "sliding" and name in ("left", "right"):
            # Rainure du couvercle : ouverte vers l'avant, fermée à 2 x t de l'arrière.
            u0, u1 = (2 * t, D) if name == "left" else (0.0, D - 2 * t)
            removals.append((u0, front_h, u1, front_h + t + cl))
        panels.append(_make_panel(name, a, b, p.kerf, removals=removals))
    if kind == "lip":
        panels.append(_make_panel("top", W, D, p.kerf))
        panels.append(_make_panel("lip", W - 2 * t - cl, D - 2 * t - cl, p.kerf))
    elif kind == "sliding":
        panels.append(_make_panel("top", W - cl, D - 2 * t, p.kerf))
    panels += dividers
    result = BoxResult(outer=(W, D, H), thickness=t, panels=panels, finger_counts=counts,
                       lid_type=kind, dividers=(int(p.dividers_x), int(p.dividers_y)))
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
