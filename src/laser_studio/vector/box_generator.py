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
coulisse dans une rainure des parois gauche / droite ; la façade est abaissée),
« hinged » (charnière vivante : la paroi arrière se prolonge par une zone à fentes qui
fléchit, puis par la plaque du couvercle, le tout d'une seule pièce), « pinned »
(charnière à axe : plaques percées empilées autour d'une tige, une sur deux dans la
paroi arrière, les autres dans le couvercle ; à coller, la tige reste libre).

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
LID_TYPES = ("none", "finger", "lip", "sliding", "hinged", "pinned")
HINGE_STYLES = ("round", "butterfly")     # contour des plaques de la charnière à axe
HANDLE_LIDS = ("lip", "sliding", "hinged", "pinned")   # couvercles qui peuvent recevoir une encoche d'ouverture
MAGNET_LIDS = ("hinged", "pinned")        # couvercles plats qui reposent sur la façade : on y colle des aimants
MAX_MAGNETS = 4                           # paires d'aimants
# Charnière vivante : rangées de fentes parallèles à l'axe, décalées d'une demi-période.
HINGE_PITCH = 2.0                 # écart entre deux rangées (mm)
HINGE_SEGMENT = 20.0              # longueur visée d'une fente
HINGE_BRIDGE = 4.0                # matière laissée entre deux fentes d'une rangée
HINGE_MARGIN = 2.0                # matière laissée entre les fentes et le bord
MAX_DIVIDERS = 20
MAX_HINGE = 100.0
MAX_HINGES = 5                    # charnières à axe
ARC_STEP_DEG = 10.0               # finesse des arcs des plaques de charnière


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
    feet: bool = False                # pieds : plaques carrées empilées sous le fond (aux 4 coins)
    foot_size: float = 15.0           # côté d'un pied (mm)
    foot_layers: int = 2              # plaques empilées par pied
    ratios_x: tuple = ()              # largeurs relatives des compartiments en X (n+1 valeurs) ; vide = égaux
    ratios_y: tuple = ()              # idem pour Y
    hinge_length: float = 20.0        # longueur DÉPLIÉE de la zone de charnière (couvercle « hinged »)
    hinge_count: int = 2              # nombre de charnières à axe (couvercle « pinned »)
    hinge_plates: int = 3             # plaques par charnière : impair, la 1re et la dernière sont fixées à la boîte
    pin_diameter: float = 3.0         # diamètre de la tige (mm) ; le trou des plaques ajoute le jeu
    pin_through: bool = True          # tige sur toute la largeur, passée dans les parois gauche et droite : retient les plaques
    pin_fit: float = 0.1              # serrage (mm, au total) des pieds et des bras dans leurs encoches, et de la tige dans les parois
    hinge_style: str = "round"        # voir HINGE_STYLES
    plate_radius: float = 0.0         # rayon des plaques (mm) ; 0 = automatique (tige + une épaisseur)
    handle: bool = False              # encoche demi-circulaire au bord avant du couvercle (impossible avec le couvercle à doigts)
    handle_radius: float = 10.0       # rayon de l'encoche (mm)
    engrave_motif: bool = False       # papillon gravé au centre du dessus
    motif_size: float = 30.0          # envergure du motif (mm)
    motif_shape: str = "butterfly"    # "butterfly" | "leaf" | "star" | "mandala"
    engrave_index: bool = False       # numéro de pièce gravé sur chaque panneau
    index_size: float = 4.0           # hauteur des chiffres (mm)
    magnets: bool = False             # aimants de fermeture : deux plaques à trou par aimant (couvercle à charnière)
    magnet_diameter: float = 6.0      # diamètre des aimants (mm) ; le trou ajoute le jeu
    magnet_count: int = 2             # paires d'aimants, réparties sur la largeur de la façade


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
    slits: list = field(default_factory=list)   # traits ouverts (fentes de charnière), repère local, sans kerf
    faces: dict = field(default_factory=dict)   # faces portées en plus : {"top": (u0, v0, u1, v1)} (repère local)

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

    def placed_slits(self):
        """Fentes de charnière (segments ouverts) en coordonnées plateau (mm)."""
        return [[(px + self.x, py + self.y) for px, py in slit] for slit in self.slits]

    def face_center(self, face=None):
        """Centre de la face (repère plateau), pour y placer un décor.

        `face` désigne une face portée par ce panneau (voir `faces`) ; sinon le panneau entier."""
        if face in self.faces:
            u0, v0, u1, v1 = self.faces[face]
            return (u0 + u1) / 2.0 + self.x, (v0 + v1) / 2.0 + self.y
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
    pin: tuple = ()                   # (nombre de tiges, diamètre, longueur) pour une charnière à axe
    motif: list = field(default_factory=list)    # contours gravés du papillon, coordonnées plateau
    index: list = field(default_factory=list)    # [(texte, x, y, hauteur)] numéros de pièce, coordonnées plateau
    magnets: tuple = ()               # (paires, diamètre) d'aimants à fournir

    def face_panels(self):
        """{face: objet avec face_center()} : un panneau par face, y compris les faces portées par un
        autre panneau (le couvercle à charnière fait partie de la paroi arrière)."""
        out = {panel.name: panel for panel in self.panels}
        for panel in self.panels:
            for face in panel.faces:
                out[face] = _FaceView(panel, face)
        return out


class _FaceView:
    """Vue d'une face portée par un panneau : même interface que Panel pour poser un décor."""

    def __init__(self, panel, face):
        self.panel, self.name = panel, face

    def face_center(self):
        return self.panel.face_center(self.name)
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


def short_wall(kind):
    """Paroi plus basse que les autres : la façade (couvercle coulissant) ou l'arrière (charnière)."""
    return {"sliding": "front", "hinged": "back"}.get(kind)


def hinge_radius(p):
    """Rayon (ligne neutre) du quart de cercle que décrit la charnière une fois pliée."""
    return 2.0 * p.hinge_length / math.pi


def wall_heights(p, H):
    """(hauteur des parois, hauteur de la paroi basse). Hors couvercle coulissant ou à charnière, égales."""
    t, cl = p.thickness, p.clearance
    kind = lid_kind(p)
    if kind in ("lip", "pinned"):
        return H - t, H - t
    if kind == "sliding":
        return H, H - 2 * t - cl
    if kind == "hinged":
        # L'arrière s'arrête là où commence l'arc de la charnière ; la plaque repose à H - t / 2 (ligne neutre).
        return H - t, H - t / 2.0 - hinge_radius(p)
    return H, H


def lid_length(p, D):
    """Longueur de la plaque d'un couvercle à charnière : de l'arc jusqu'à la face avant."""
    return D - p.thickness / 2.0 - hinge_radius(p)


@dataclass
class PinGeometry:
    r_hole: float        # rayon du trou de la tige (jeu compris)
    radius: float        # rayon extérieur des plaques (anneau autour de la tige)
    ring_depth: float    # dégagement creusé sous le dessus de la paroi arrière, au droit des plaques du couvercle
    foot: float          # profondeur de l'encoche qui reçoit le pied des plaques fixes
    arm: float           # longueur du bras des plaques du couvercle, depuis l'axe
    r_ear: float = 0.0   # rayon du trou de la tige dans les parois gauche et droite
    ear: float = 0.0     # rayon de l'oreille qui entoure ce trou (dépasse du dessus et de l'arrière de la boîte)


def pin_geometry(p):
    """Dimensions d'une charnière à axe (indépendantes de la boîte). La tige est à mi-épaisseur du couvercle,
    à l'aplomb du milieu de la paroi arrière."""
    t, cl = p.thickness, p.clearance
    r_hole = (p.pin_diameter + cl) / 2.0
    radius = max(r_hole + t, p.plate_radius)
    ring_depth = radius + cl - t / 2.0
    r_ear = max(p.pin_diameter / 2.0 - p.pin_fit / 2.0, 0.25)
    return PinGeometry(r_hole=r_hole, radius=radius, ring_depth=ring_depth,
                       foot=max(2 * t, ring_depth + t), arm=radius + 2 * t,
                       r_ear=r_ear, ear=r_ear + max(t / 2.0, 1.0))


def pin_hinge_columns(p, W):
    """[[(x0, fixe)] par charnière] : bord gauche de chaque plaque ; fixe = plaque de la boîte (sinon du couvercle).
    Les plaques sont jointives et alternent ; les charnières se répartissent en parts égales de la largeur."""
    t, k, n = p.thickness, int(p.hinge_plates), int(p.hinge_count)
    out = []
    for i in range(n):
        start = W * (2 * i + 1) / (2.0 * n) - k * t / 2.0
        out.append([(start + j * t, j % 2 == 0) for j in range(k)])
    return out


def _disk_stub_outline(cu, cv, radius, half_w, length, direction):
    """Contour anti-horaire de l'union d'un disque (centre cu, cv) et d'une patte de largeur 2 x half_w qui part
    du centre vers le bas (« down ») ou vers l'avant, -u (« left »), sur `length` mm."""
    h = math.sqrt(radius * radius - half_w * half_w)
    a0 = math.atan2(-h, half_w)
    a1 = math.atan2(-h, -half_w) + 2 * math.pi
    steps = max(8, int(math.ceil(math.degrees(a1 - a0) / ARC_STEP_DEG)))
    local = [(-half_w, -length), (half_w, -length), (half_w, -h)]
    local += [(radius * math.cos(a0 + (a1 - a0) * i / steps), radius * math.sin(a0 + (a1 - a0) * i / steps))
              for i in range(1, steps)]
    local.append((-half_w, -h))
    if direction == "down":
        return [(cu + a, cv + b) for a, b in local]
    return [(cu + b, cv - a) for a, b in local]        # rotation de -90° : le bas devient l'avant


def _circle(cu, cv, radius, clockwise):
    steps = max(12, int(math.ceil(360.0 / ARC_STEP_DEG)))
    pts = [(cu + radius * math.cos(2 * math.pi * i / steps), cv + radius * math.sin(2 * math.pi * i / steps))
           for i in range(steps)]
    return pts[::-1] if clockwise else pts


def offset_polygon(poly, d):
    """Décale un contour anti-horaire de `d` mm vers l'extérieur (d < 0 : vers l'intérieur), angles vifs compris
    (coin au point de rencontre des deux côtés décalés). Pour un contour orthogonal, identique à offset_orthogonal."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        n1 = (e1[1] / l1, -e1[0] / l1)
        n2 = (e2[1] / l2, -e2[0] / l2)
        k = d / (1.0 + n1[0] * n2[0] + n1[1] * n2[1])
        out.append((p1[0] + k * (n1[0] + n2[0]), p1[1] + k * (n1[1] + n2[1])))
    return out


# Papillon : un corps (disque autour du trou) et quatre ailes, symétriques par rapport à la verticale.
# (angle du centre de l'aile en degrés, distance du centre / rayon des plaques, rayon de l'aile / rayon des plaques)
_BUTTERFLY_WINGS = ((52.0, 0.56, 0.44), (128.0, 0.56, 0.44), (-50.0, 0.50, 0.30), (-130.0, 0.50, 0.30))
_BUTTERFLY_STEP_DEG = 2.0


def _wing_reach(theta, wing, radius):
    """Distance à laquelle le rayon d'angle `theta` (depuis l'axe) quitte une aile ronde ; 0 s'il la manque."""
    angle, dist, size = wing
    d, a = dist * radius, size * radius
    phi = theta - math.radians(angle)
    side = d * math.sin(phi)
    if abs(side) >= a:
        return 0.0
    return d * math.cos(phi) + math.sqrt(a * a - side * side)


def _stub_reach(theta, half_w, length):
    """Distance à laquelle le rayon d'angle `theta` quitte la patte (rectangle sous l'axe, largeur 2 x half_w)."""
    sin, cos = math.sin(theta), math.cos(theta)
    if sin >= -1e-12:
        return 0.0
    reach = length / -sin
    if abs(cos) > 1e-12:
        reach = min(reach, half_w / abs(cos))
    return reach


def _butterfly_stub_outline(cu, cv, radius, body, half_w, length, direction):
    """Contour anti-horaire de l'union du papillon (inscrit dans le cercle de `radius`) et d'une patte,
    même convention que _disk_stub_outline. La fonction « portée » est étoilée autour de l'axe : le contour
    de l'union est le maximum des portées."""
    corners = [math.atan2(-length, half_w), math.atan2(-length, -half_w)]
    steps = int(round(360.0 / _BUTTERFLY_STEP_DEG))
    angles = {-math.pi + 2 * math.pi * i / steps for i in range(steps)}
    angles |= {a for a in corners}
    local = []
    for theta in sorted(angles):
        reach = max([body, _stub_reach(theta, half_w, length)] + [_wing_reach(theta, w, radius) for w in _BUTTERFLY_WINGS])
        local.append((reach * math.cos(theta), reach * math.sin(theta)))
    local = _simplify([(round(a, 9), round(b, 9)) for a, b in local])
    if direction == "down":
        return [(cu + a, cv + b) for a, b in local]
    return [(cu + b, cv - a) for a, b in local]


def _pin_plate(name, p, pin, axis, fixed, wall_top):
    """Plaque percée d'une charnière à axe, dans son plan (u = Y, v = Z de la boîte)."""
    t, k = p.thickness, p.kerf / 2.0
    y_p, z_p = axis
    if fixed:       # pied qui descend dans l'encoche de la paroi arrière
        length, direction = z_p - (wall_top - pin.foot), "down"
    else:           # bras qui s'avance dans le couvercle
        length, direction = pin.arm, "left"
    if p.hinge_style == "butterfly":
        body = pin.r_hole + max(0.8, t / 3.0)                      # matière minimale autour du trou
        outline = _butterfly_stub_outline(y_p, z_p, pin.radius, body, t / 2.0, length, direction)
        cut = offset_polygon(outline, k) if k > 0 else list(outline)
    else:
        outline = _disk_stub_outline(y_p, z_p, pin.radius, t / 2.0, length, direction)
        cut = _disk_stub_outline(y_p, z_p, pin.radius + k, t / 2.0 + k, length + k, direction)
    xs, ys = [q[0] for q in outline], [q[1] for q in outline]
    return Panel(name=name, width=max(xs) - min(xs), height=max(ys) - min(ys), outline=outline, cut=cut,
                 holes=[_circle(y_p, z_p, pin.r_hole - k, clockwise=True)])


def _ear_outline(outline, side, wall_top, axis_u, axis_v, ear):
    """Contour d'une paroi gauche ou droite avec son oreille : un disque de rayon `ear` centré sur l'axe de la tige,
    posé sur le dessus de la paroi au coin arrière (il dépasse un peu du dessus du couvercle et de l'arrière de la
    boîte). `side` : « left » (arrière en u = 0) ou « right » (arrière en u = largeur de la paroi)."""
    drop = wall_top - axis_v                                   # < 0 : le dessus de la paroi est sous l'axe
    chord = math.sqrt(ear * ear - drop * drop)
    a_start = math.atan2(drop, chord)                          # extrémité droite de la corde
    a_end = math.atan2(drop, -chord) + 2 * math.pi             # extrémité gauche, en passant par le haut
    steps = max(8, int(math.ceil(math.degrees(a_end - a_start) / ARC_STEP_DEG)))
    arc = [(axis_u + ear * math.cos(a_start + (a_end - a_start) * i / steps),
            axis_v + ear * math.sin(a_start + (a_end - a_start) * i / steps)) for i in range(steps + 1)]
    arc[0], arc[-1] = (axis_u + chord, wall_top), (axis_u - chord, wall_top)
    corner = max(q[0] for q in outline) if side == "right" else min(q[0] for q in outline)
    for i, q in enumerate(outline):
        if abs(q[0] - corner) < 1e-6 and abs(q[1] - wall_top) < 1e-6:
            return outline[:i] + ([q] + arc if side == "right" else arc + [q]) + outline[i + 1:]
    raise BoxError("ear_corner")


def _insert_arc(poly, cu, cv, radius, edge):
    """Insère dans le contour anti-horaire `poly` un arc de cercle (centre cu, cv) qui entame un bord droit :
    « bottom » : bord bas, l'arc monte dans la matière ; « top » : bord haut, l'arc descend."""
    n = len(poly)
    for i in range(n):
        p0, p1 = poly[i], poly[(i + 1) % n]
        if abs(p0[1] - p1[1]) > _EPS:
            continue
        along = p1[0] - p0[0]
        if (edge == "bottom") != (along > 0):
            continue
        e = p0[1]
        room = radius * radius - (e - cv) ** 2
        if room <= 0:
            continue
        h = math.sqrt(room)
        lo, hi = min(p0[0], p1[0]), max(p0[0], p1[0])
        if cu - h < lo - _EPS or cu + h > hi + _EPS:
            continue
        a_left, a_right = math.atan2(e - cv, -h), math.atan2(e - cv, h)
        if edge == "bottom":              # de gauche à droite, par le haut du cercle
            start, end, first, last = a_left, a_right, (cu - h, e), (cu + h, e)
        else:                             # de droite à gauche, par le bas du cercle
            start, end, first, last = a_right, a_left, (cu + h, e), (cu - h, e)
        if end > start:
            end -= 2 * math.pi
        steps = max(4, int(math.ceil(math.degrees(start - end) / ARC_STEP_DEG)))
        arc = [(cu + radius * math.cos(start + (end - start) * j / steps),
                cv + radius * math.sin(start + (end - start) * j / steps)) for j in range(1, steps)]
        return poly[:i + 1] + [first] + arc + [last] + poly[i + 1:]
    raise BoxError("handle_no_edge")


def _add_handle(panel, cu, cv, radius, edge, kerf):
    """Encoche demi-circulaire au bord (« bottom » ou « top ») du panneau ; elle s'agrandit de kerf / 2 côté vide :
    le trait de découpe, décalé hors de la matière, passe sur un cercle plus petit."""
    panel.outline = _insert_arc(panel.outline, cu, cv, radius, edge)
    panel.cut = _insert_arc(panel.cut, cu, cv, radius - kerf / 2.0, edge)


def handle_limit(p, W, D):
    """(rayon minimal, rayon maximal) de l'encoche d'ouverture du couvercle."""
    t, cl = p.thickness, p.clearance
    kind = lid_kind(p)
    width = W - cl if kind == "sliding" else W
    reach = {"lip": D - 4 * t, "sliding": D - 4 * t, "hinged": lid_length(p, D) - 2 * t,
             "pinned": (D - t / 2.0) - pin_geometry(p).arm - cl / 2.0 - 2 * t}.get(kind, 0.0)
    return t + 4.0, min((width - 2 * t) / 2.0, reach)


def top_face_size(p, W, D):
    """(largeur, profondeur) de la face visible du dessus."""
    t, cl = p.thickness, p.clearance
    kind = lid_kind(p)
    if kind == "pinned":
        return W, D - t / 2.0
    if kind == "hinged":
        return W, lid_length(p, D)
    if kind == "sliding":
        return W - cl, D - 2 * t
    return W, D


def motif_limit(p, W, D):
    """(envergure minimale, maximale) du papillon gravé : il reste loin de l'encoche et des encoches de charnière."""
    fw, fh = top_face_size(p, W, D)
    front = p.handle_radius + 2.0 if p.handle and lid_kind(p) in HANDLE_LIDS else 3.0
    rear = pin_geometry(p).arm + p.clearance + 2.0 if lid_kind(p) == "pinned" else 3.0
    return 8.0, min(fw - 6.0, fh - 2.0 * max(front, rear))


def butterfly_motif(cx, cy, size):
    """Contours fermés du papillon gravé (envergure `size`) centré sur (cx, cy) : les ailes et le corps."""
    R = size / 2.0
    body = 0.16 * R
    wings = []
    for i in range(180):
        theta = 2 * math.pi * i / 180
        reach = max([body] + [_wing_reach(theta, w, R) for w in _BUTTERFLY_WINGS])
        wings.append((cx + reach * math.cos(theta), cy + reach * math.sin(theta)))
    trunk = [(cx + 0.07 * R * math.cos(2 * math.pi * i / 36), cy + 0.38 * R * math.sin(2 * math.pi * i / 36))
             for i in range(36)]
    span = max(q[0] for q in wings) - min(q[0] for q in wings)        # l'envergure est la largeur réelle des ailes
    k = size / span
    return [[(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in loop] for loop in (wings, trunk)]


MOTIF_SHAPES = ("butterfly", "leaf", "star", "mandala")


def _polar(cx, cy, radius_of, n=180):
    return [(cx + radius_of(2 * math.pi * i / n) * math.cos(2 * math.pi * i / n),
             cy + radius_of(2 * math.pi * i / n) * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _fit_width(loops, cx, cy, size):
    """Met les contours à l'échelle pour que leur largeur totale vaille `size`, centrés sur (cx, cy)."""
    xs = [q[0] for loop in loops for q in loop]
    ys = [q[1] for loop in loops for q in loop]
    k = size / (max(xs) - min(xs))
    mx, my = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    return [[(cx + (x - mx) * k, cy + (y - my) * k) for x, y in loop] for loop in loops]


def motif_loops(shape, cx, cy, size):
    """Contours fermés du motif gravé `shape` (largeur `size`) centré sur (cx, cy)."""
    if shape == "butterfly":
        return butterfly_motif(cx, cy, size)
    R = size / 2.0
    if shape == "leaf":
        n = 60
        top = [(cx - R + 2 * R * i / n, cy + 0.32 * R * math.sin(math.pi * i / n) ** 0.85) for i in range(n + 1)]
        bottom = [(x, 2 * cy - y) for x, y in reversed(top[1:-1])]
        vein = [(cx - 0.8 * R, cy), (cx - 0.78 * R, cy + 0.02 * R), (cx + 0.55 * R, cy + 0.02 * R),
                (cx + 0.58 * R, cy), (cx + 0.55 * R, cy - 0.02 * R), (cx - 0.78 * R, cy - 0.02 * R)]
        return _fit_width([top + bottom, vein], cx, cy, size)
    if shape == "star":
        pts = []
        for i in range(10):
            a = math.pi / 2 + i * math.pi / 5
            r = R if i % 2 == 0 else 0.42 * R
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return _fit_width([pts], cx, cy, size)
    if shape == "mandala":
        return [_polar(cx, cy, lambda t: R),
                _polar(cx, cy, lambda t: 0.82 * R * (1.0 + 0.14 * math.cos(12 * t)) * 0.9, 240),
                _polar(cx, cy, lambda t: 0.45 * R * (1.0 + 0.25 * math.cos(8 * t)), 200),
                _polar(cx, cy, lambda t: 0.12 * R, 36)]
    raise BoxError("motif_shape", value=shape)


def magnet_layout(p, W):
    """(côté des plaques carrées, [x du centre de chaque aimant]) : réparti en parts égales de la largeur."""
    n = int(p.magnet_count)
    return p.magnet_diameter + 2 * p.thickness, [W * (2 * i + 1) / (2.0 * n) for i in range(n)]


def _magnet_plates(p, W, H):
    """Deux plaques carrées par aimant, percées du diamètre de l'aimant : l'une collée sous le couvercle, l'autre
    sur la face intérieure de la façade, juste dessous. Les aimants se collent dans les trous, face à face."""
    cl, k = p.clearance, p.kerf / 2.0
    s, xs = magnet_layout(p, W)
    r_hole = (p.magnet_diameter + cl) / 2.0
    square = [(0.0, 0.0), (s, 0.0), (s, s), (0.0, s)]
    plates = []
    for i in range(len(xs)):
        for kind in ("lid", "wall"):
            cut = [(-k, -k), (s + k, -k), (s + k, s + k), (-k, s + k)]
            plates.append(Panel(name=f"magnet_{kind}{i + 1}", width=s, height=s, outline=list(square), cut=cut,
                                holes=[_circle(s / 2.0, s / 2.0, r_hole - k, clockwise=True)]))
    return plates


def foot_inset(p):
    """Retrait des pieds par rapport au bord extérieur de la boîte (mm)."""
    return p.thickness + 2.0


def foot_origins(p, W, D):
    """[(x, y)] du coin inférieur gauche de chacun des 4 pieds."""
    a, s = foot_inset(p), p.foot_size
    return [(a, a), (W - a - s, a), (a, D - a - s), (W - a - s, D - a - s)]


def _foot_plates(p):
    """4 pieds, chacun de `foot_layers` plaques carrées à coller les unes sur les autres sous le fond."""
    s, k = p.foot_size, p.kerf / 2.0
    square = [(0.0, 0.0), (s, 0.0), (s, s), (0.0, s)]
    plates = []
    for i in range(4):
        for layer in range(int(p.foot_layers)):
            cut = [(-k, -k), (s + k, -k), (s + k, s + k), (-k, s + k)]
            plates.append(Panel(name=f"foot{i + 1}_{layer + 1}", width=s, height=s, outline=list(square), cut=cut))
    return plates


def _in_polygon(poly, x, y):
    inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def _label_spot(panel, size, text):
    """Centre (repère plateau) d'un numéro gravé sur `panel`, ou None s'il n'y a pas la place : un rectangle libre
    (loin du contour, des trous et de la zone des fentes de charnière), de préférence vers le bas à gauche."""
    w, h, m = 0.7 * size * len(text) + 1.0, size, 1.5
    xs, ys = [q[0] for q in panel.cut], [q[1] for q in panel.cut]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    band = (min(q[1] for sl in panel.slits for q in sl), max(q[1] for sl in panel.slits for q in sl)) if panel.slits else None
    loops = [panel.cut] + list(panel.holes)

    def free(cx, cy):
        a0, a1, b0, b1 = cx - w / 2 - m, cx + w / 2 + m, cy - h / 2 - m, cy + h / 2 + m
        if band and b1 > band[0] and b0 < band[1]:
            return False
        probes = [(a0, b0), (a1, b0), (a0, b1), (a1, b1), (cx, b0), (cx, b1), (a0, cy), (a1, cy), (cx, cy)]
        if not all(_in_polygon(panel.cut, x, y) and not any(_in_polygon(hole, x, y) for hole in panel.holes)
                   for x, y in probes):
            return False
        return not any(a0 < q[0] < a1 and b0 < q[1] < b1 for loop in loops for q in loop)

    px, py = x0 + 0.25 * (x1 - x0), y0 + 0.3 * (y1 - y0)
    step = 1.0
    cands = []
    u = x0 + w / 2 + m
    while u <= x1 - w / 2 - m:
        v = y0 + h / 2 + m
        while v <= y1 - h / 2 - m:
            cands.append((((u - px) ** 2 + (v - py) ** 2), u, v))
            v += step
        u += step
    for _d, u, v in sorted(cands):
        if free(u, v):
            return u + panel.x, v + panel.y
    return None


def hinge_slits(width, v0, length):
    """Fentes (segments [(u0, v), (u1, v)]) d'une charnière vivante de `width` de large, sur [v0, v0 + length].

    Rangées parallèles à l'axe de pliage ; une rangée sur deux est décalée d'une demi-période, de sorte
    que la matière entre les fentes se tord au lieu de se casser."""
    usable = width - 2 * HINGE_MARGIN
    n = max(1, round((usable + HINGE_BRIDGE) / (HINGE_SEGMENT + HINGE_BRIDGE)))
    seg = (usable - (n - 1) * HINGE_BRIDGE) / n
    starts = [HINGE_MARGIN + i * (seg + HINGE_BRIDGE) for i in range(n)]
    row_a = [(a, a + seg) for a in starts]
    centres = [a + seg / 2.0 for a in starts]
    half = HINGE_BRIDGE / 2.0
    bounds = [HINGE_MARGIN] + [x for c in centres for x in (c - half, c + half)] + [width - HINGE_MARGIN]
    row_b = [(bounds[i], bounds[i + 1]) for i in range(0, len(bounds), 2)]
    rows = max(2, int(length / HINGE_PITCH))
    slits = []
    for k in range(rows):
        v = v0 + (k + 0.5) * length / rows
        for a, b in (row_a if k % 2 == 0 else row_b):
            if b - a > 0.5:
                slits.append([(a, v), (b, v)])
    return slits


def divider_top(p, H):
    """Cote Z du haut des cloisons : elles restent sous le couvercle."""
    t, cl = p.thickness, p.clearance
    return {"none": H, "finger": H - t, "lip": H - 2 * t, "sliding": H - 2 * t - cl,
            "hinged": H - t, "pinned": H - t}[lid_kind(p)]


def _validate_magnets(p, W, D):
    t, cl = p.thickness, p.clearance
    if lid_kind(p) not in MAGNET_LIDS:
        raise BoxError("magnet_lid")
    if not 3.0 <= p.magnet_diameter <= 20.0 or int(p.magnet_count) != p.magnet_count \
            or not 1 <= p.magnet_count <= MAX_MAGNETS:
        raise BoxError("magnet_size", minimum=3.0, maximum=20.0, count=MAX_MAGNETS)
    s, xs = magnet_layout(p, W)
    fixed = divider_positions(W, int(p.dividers_x), t, p.ratios_x) if p.dividers_x else []
    for xc in xs:
        x0, x1 = xc - s / 2.0, xc + s / 2.0
        if x0 < t + cl or x1 > W - t - cl:
            raise BoxError("magnet_room", size=s)
        if any(x0 - cl < pos + t and x1 + cl > pos for pos in fixed):
            raise BoxError("magnet_dividers")
        if p.handle and p.handle_radius > t and abs(xc - W / 2.0) < p.handle_radius + s / 2.0 + 1.0:
            raise BoxError("magnet_handle")
    if p.dividers_y and t + cl + s > divider_positions(D, int(p.dividers_y), t, p.ratios_y)[0] - cl:
        raise BoxError("magnet_room", size=s)
    if D - 2 * t < s + 2 * cl:
        raise BoxError("magnet_room", size=s)


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
    if lid_kind(p) == "hinged" and (p.hinge_length < minimum - _EPS or p.hinge_length > MAX_HINGE):
        raise BoxError("hinge_length", value=p.hinge_length, minimum=minimum, maximum=MAX_HINGE)
    wall_h = min(wall_heights(p, H))
    if wall_h < minimum - _EPS:
        raise BoxError("too_small", axis="Z", value=wall_h, minimum=minimum)
    if lid_kind(p) == "hinged" and lid_length(p, D) < minimum - _EPS:
        raise BoxError("hinge_too_long", value=lid_length(p, D), minimum=minimum)
    if lid_kind(p) == "pinned":
        biggest = min(12.0, t) if p.pin_through else 12.0          # tige traversante : sous l'arrière, donc <= épaisseur
        if not 0.5 <= p.pin_diameter <= biggest:
            raise BoxError("pin_diameter", value=p.pin_diameter, minimum=0.5, maximum=biggest)
        if p.hinge_style not in HINGE_STYLES:
            raise BoxError("hinge_style", value=p.hinge_style)
        if not 0.0 <= p.pin_fit <= t / 4.0:
            raise BoxError("pin_fit", value=p.pin_fit, maximum=t / 4.0)
        r_min = (p.pin_diameter + p.clearance) / 2.0 + t
        if p.plate_radius != 0 and not r_min - _EPS <= p.plate_radius <= 25.0:
            raise BoxError("plate_radius", value=p.plate_radius, minimum=r_min, maximum=25.0)
        if int(p.hinge_count) != p.hinge_count or not 1 <= p.hinge_count <= MAX_HINGES:
            raise BoxError("hinge_count", value=p.hinge_count, maximum=MAX_HINGES)
        if int(p.hinge_plates) != p.hinge_plates or p.hinge_plates % 2 == 0 or not 3 <= p.hinge_plates <= 9:
            raise BoxError("hinge_plates", value=p.hinge_plates)
        pin = pin_geometry(p)
        needed = p.hinge_count * (p.hinge_plates + 4) * t           # chaque charnière + 2 x t de marge de chaque côté
        if W < needed - _EPS:
            raise BoxError("hinges_dont_fit", value=W, minimum=needed)
        if H - t - pin.foot < 2 * t - _EPS:
            raise BoxError("too_small", axis="Z", value=H, minimum=3 * t + pin.foot)
        if D - t / 2.0 - pin.arm < 2 * t - _EPS:
            raise BoxError("hinge_too_long", value=D - t / 2.0 - pin.arm, minimum=2 * t)
    if p.handle and lid_kind(p) != "none":
        if lid_kind(p) not in HANDLE_LIDS:
            raise BoxError("handle_finger")
        low, high = handle_limit(p, W, D)
        if not low - _EPS <= p.handle_radius <= high + _EPS:
            raise BoxError("handle_radius", value=p.handle_radius, minimum=low, maximum=high)
    if lid_kind(p) != "none":
        if p.engrave_motif:
            if p.motif_shape not in MOTIF_SHAPES:
                raise BoxError("motif_shape", value=p.motif_shape)
            low, high = motif_limit(p, W, D)
            if not low - _EPS <= p.motif_size <= high + _EPS:
                raise BoxError("motif_size", value=p.motif_size, minimum=low, maximum=high)
        if p.magnets:
            _validate_magnets(p, W, D)
    if p.feet:
        if int(p.foot_layers) != p.foot_layers or not 1 <= p.foot_layers <= 4:
            raise BoxError("foot_layers", minimum=1, maximum=4)
        high = min(W, D) / 2.0 - foot_inset(p)
        if not 8.0 - _EPS <= p.foot_size <= high + _EPS:
            raise BoxError("foot_size", value=p.foot_size, minimum=8.0, maximum=high)
    if p.engrave_index and not 2.0 <= p.index_size <= 15.0:
        raise BoxError("index_size", value=p.index_size, minimum=2.0, maximum=15.0)
    target = p.finger_width if p.finger_width > 0 else 3 * t
    if target < t:
        raise BoxError("finger_too_small", value=target, minimum=t)
    for label, total, n, ratios in (("X", W, p.dividers_x, p.ratios_x), ("Y", D, p.dividers_y, p.ratios_y)):
        if n:
            _check_ratios(n, ratios, label)
            room = min(compartment_widths(total, int(n), t, ratios))
            if room < minimum - _EPS:
                raise BoxError("compartment_too_small", axis=label, value=room, minimum=minimum)
    if p.dividers_x or p.dividers_y:
        height = divider_top(p, H) - t
        if lid_kind(p) in ("hinged", "pinned") and p.dividers_x:
            height = min(height, _back_tab_height(p, H))       # les languettes entrent dans l'arrière, plus bas
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


def compartment_widths(total, n, t, ratios=()):
    """Largeurs des n+1 compartiments (égales, ou proportionnelles à `ratios`)."""
    room = (total - 2 * t) - n * t
    if not ratios:
        return [room / (n + 1)] * (n + 1)
    whole = float(sum(ratios))
    return [room * r / whole for r in ratios]


def divider_positions(total, n, t, ratios=()):
    """Position (coin inférieur) des n cloisons dans [0, total] : compartiments égaux entre les parois, ou
    proportionnels à `ratios` (n + 1 valeurs)."""
    widths = compartment_widths(total, n, t, ratios)
    out, cursor = [], t
    for k in range(n):
        cursor += widths[k]
        out.append(cursor)
        cursor += t
    return out


def _check_ratios(n, ratios, axis):
    if ratios and n and (len(ratios) != n + 1 or any(r <= 0 for r in ratios)):
        raise BoxError("divider_ratios", axis=axis, count=n + 1)


def _back_tab_height(p, H):
    """Hauteur utile (depuis le fond) des languettes de cloison qui entrent dans la paroi arrière basse."""
    t = p.thickness
    floor = H - t - pin_geometry(p).foot if lid_kind(p) == "pinned" else wall_heights(p, H)[1]
    return floor - 2 * t


def _build_dividers(p, W, D, H, target, extra):
    """Cloisons : panneaux + fentes à ajouter aux parois et au fond (dans `extra`, par nom de panneau)."""
    t, cl, half = p.thickness, p.clearance, p.clearance / 2.0
    nx, ny = int(p.dividers_x), int(p.dividers_y)
    xs, ys = divider_positions(W, nx, t, p.ratios_x), divider_positions(D, ny, t, p.ratios_y)
    height = divider_top(p, H) - t
    end_tabs = _tab_intervals(0.0, height, target, t)          # verticales : dans les parois
    if lid_kind(p) in ("hinged", "pinned"):                    # l'arrière est plus bas / encoché : languettes limitées
        end_tabs = _tab_intervals(0.0, min(height, _back_tab_height(p, H)), target, t)
    # Intervalles occupés par les cloisons de l'autre sens (en coordonnée le long de la cloison).
    cross_x = [(y - t - half, y + half) for y in ys]            # cloisons en X croisées par les cloisons en Y
    cross_y = [(x - t - half, x + half) for x in xs]
    panels = []

    def divider(name, span, pos_list, notch_top, others, corner_cuts=()):
        bottom_tabs = []
        for a, b in _free_intervals(span, others):
            bottom_tabs += _tab_intervals(a, b, target, t)
        rects = [(t, t, t + span, t + height)]
        removals = list(corner_cuts)
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

    hinge_x, ring_cut = [], ()
    if lid_kind(p) == "pinned":
        # Les anneaux des plaques dépassent sous le dessus de la paroi arrière : une cloison placée au droit
        # d'une charnière perd son coin arrière haut (repère de la cloison : u = Y, v = Z).
        pin = pin_geometry(p)
        hinge_x = [(c[0][0] - half, c[-1][0] + t + half) for c in pin_hinge_columns(p, W)]
        ring_cut = [(D - t / 2.0 - pin.radius - cl, H - t / 2.0 - pin.radius - cl, D + 2 * t, H + t)]
    for k, x in enumerate(xs):                                  # cloison dans un plan x = const : longe Y
        x0, x1 = x - half, x + t + half
        touches_hinge = any(x0 < b and x1 > a for a, b in hinge_x)
        bottom_tabs = divider(f"divider_x{k + 1}", D - 2 * t, xs, True, cross_x, ring_cut if touches_hinge else ())
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


def _hinged_back(p, a, wall_top, D, removals):
    """Paroi arrière + zone de charnière + plaque du couvercle, d'une seule pièce (rectangle a x total)."""
    hinge, lid = p.hinge_length, lid_length(p, D)
    panel = _make_panel("back", a, wall_top + hinge + lid, p.kerf, removals=removals)
    if p.handle:
        _add_handle(panel, a / 2.0, wall_top + hinge + lid, p.handle_radius, "top", p.kerf)
    panel.slits = hinge_slits(a, wall_top, hinge)
    panel.faces = {"top": (0.0, wall_top + hinge, a, wall_top + hinge + lid)}
    return panel


def build_box(p):
    """Calcule les panneaux de la boîte (sans disposition : voir layout_panels)."""
    W, D, H, target = validate(p)
    t, cl = p.thickness, p.clearance
    kind = lid_kind(p)
    wall_h, short_h = wall_heights(p, H)
    short = short_wall(kind)                              # paroi plus basse (façade ou arrière), ou None
    dims = {"W": W, "D": D, "H": wall_h}
    counts = {k: odd_finger_count(v, target) for k, v in dims.items()}
    short_count = odd_finger_count(short_h, target)       # arêtes verticales partagées avec la paroi basse
    jointed = [f for f in FACE_NAMES if f != "top" or kind == "finger"]
    rank = {name: i for i, name in enumerate(p.priority)}
    extra = {name: [] for name in FACE_NAMES}              # fentes de cloison, par panneau
    dividers = _build_dividers(p, W, D, H, target, extra) if (p.dividers_x or p.dividers_y) else []

    def edge_pattern(name, edge, neighbor, a_key, b_key):
        if short and ((name == short and edge in ("left", "right"))
                      or (name in ("left", "right") and neighbor == short)):
            return short_h, short_count
        key = a_key if edge in ("bottom", "top") else b_key
        return dims[key], counts[key]

    pin = pin_geometry(p)
    through = kind == "pinned" and p.pin_through
    fit = p.pin_fit
    rear_slots = {}        # paroi -> fente du coin arrière haut, si la paroi arrière occupe ce coin : on le lui reprend
    if through:
        for side in ("left", "right"):
            a_key, b_key = _PANEL_DIMS[side]
            edge = "left" if side == "left" else "right"
            length, n = edge_pattern(side, edge, "back", a_key, b_key)
            for rect in _removal_rects(dims[a_key], dims[b_key], t, edge, _segments(length, n), rank[side] < rank["back"]):
                if rect[3] > wall_h - _EPS:
                    rear_slots[side] = rect
    panels = []
    for name in jointed:
        a_key, b_key = _PANEL_DIMS[name]
        a, b = dims[a_key], dims[b_key]
        if name == short:
            b = short_h
        removals = list(extra[name])
        for edge, neighbor in zip(_EDGES, _NEIGHBORS[name]):
            if neighbor not in jointed:
                continue                                  # arête sans voisin : bord droit
            length, n = edge_pattern(name, edge, neighbor, a_key, b_key)
            male = rank[name] < rank[neighbor]
            rects = _removal_rects(a, b, t, edge, _segments(length, n), male)
            if name in rear_slots and neighbor == "back":
                rects = [r for r in rects if r != rear_slots[name]]
            removals += rects
        if kind == "pinned" and name == "back":
            # Encoches de la charnière : un passage commun pour les anneaux, et le pied des plaques fixes (profond,
            # ajusté serré). Les parois gauche et droite portent la tige : elles gardent le coin arrière haut.
            for hinge in pin_hinge_columns(p, W):
                removals.append((W - hinge[-1][0] - t - cl / 2.0, wall_h - pin.ring_depth,
                                 W - hinge[0][0] + cl / 2.0, wall_h))
                for x0, fixed in hinge:
                    if fixed:
                        removals.append((W - x0 - t + fit / 2.0, wall_h - pin.foot, W - x0 - fit / 2.0, wall_h))
            for side, rect in rear_slots.items():
                u0 = W - t if side == "left" else 0.0
                removals.append((u0, rect[1], u0 + t, rect[3]))
        if kind == "sliding" and name in ("left", "right"):
            # Rainure du couvercle : ouverte vers l'avant, fermée à 2 x t de l'arrière.
            u0, u1 = (2 * t, D) if name == "left" else (0.0, D - 2 * t)
            removals.append((u0, short_h, u1, short_h + t + cl))
        if kind == "hinged" and name == "back":
            panels.append(_hinged_back(p, a, b, D, removals))
        else:
            panel = _make_panel(name, a, b, p.kerf, removals=removals)
            if through and name in ("left", "right"):
                axis_u = D - t / 2.0 if name == "right" else t / 2.0
                panel.outline = _ear_outline(panel.outline, name, wall_h, axis_u, H - t / 2.0, pin.ear)
                panel.cut = offset_polygon(panel.outline, p.kerf / 2.0) if p.kerf > 0 else list(panel.outline)
                panel.holes.append(_circle(axis_u, H - t / 2.0, pin.r_ear - p.kerf / 2.0, clockwise=True))
            panels.append(panel)
    handle = p.handle and kind in HANDLE_LIDS
    r = p.handle_radius
    if kind == "lip":
        top = _make_panel("top", W, D, p.kerf)
        lip = _make_panel("lip", W - 2 * t - cl, D - 2 * t - cl, p.kerf)
        if handle:
            _add_handle(top, W / 2.0, 0.0, r, "bottom", p.kerf)
            _add_handle(lip, (W - 2 * t - cl) / 2.0, -(t + cl / 2.0), r, "bottom", p.kerf)
        panels += [top, lip]
    elif kind == "sliding":
        top = _make_panel("top", W - cl, D - 2 * t, p.kerf)
        if handle:
            _add_handle(top, (W - cl) / 2.0, 0.0, r, "bottom", p.kerf)
        panels.append(top)
    elif kind == "pinned":
        axis = (D - t / 2.0, H - t / 2.0)                  # (y, z) de la tige
        columns = pin_hinge_columns(p, W)
        notches = []
        for hinge in columns:
            notches.append((hinge[0][0] - cl / 2.0, axis[0] - (pin.radius + cl), hinge[-1][0] + t + cl / 2.0, axis[0]))
            for x0, fixed in hinge:
                if not fixed:
                    notches.append((x0 + fit / 2.0, axis[0] - (pin.arm + cl / 2.0), x0 + t - fit / 2.0, axis[0]))
        if through:                                        # dégagement des oreilles qui portent la tige
            depth = axis[0] - (pin.ear + cl)
            notches += [(0.0, depth, t + cl, axis[0]), (W - t - cl, depth, W, axis[0])]
        top = _make_panel("top", W, axis[0], p.kerf, removals=notches)
        if handle:
            _add_handle(top, W / 2.0, 0.0, r, "bottom", p.kerf)
        panels.append(top)
        for i, hinge in enumerate(columns):
            for j, (_x0, fixed) in enumerate(hinge):
                panels.append(_pin_plate(f"hinge{i + 1}_{j + 1}", p, pin, axis, fixed, wall_h))
    panels += dividers
    if p.magnets and kind in MAGNET_LIDS:
        panels += _magnet_plates(p, W, H)
    if p.feet:
        panels += _foot_plates(p)
    result = BoxResult(outer=(W, D, H), thickness=t, panels=panels, finger_counts=counts,
                       lid_type=kind, dividers=(int(p.dividers_x), int(p.dividers_y)),
                       pin=((1, p.pin_diameter, W) if through else (int(p.hinge_count), p.pin_diameter, p.hinge_plates * t))
                       if kind == "pinned" else ())
    layout_panels(result, p.gap, p.max_width)
    if p.magnets and kind in MAGNET_LIDS:
        result.magnets = (int(p.magnet_count), p.magnet_diameter)
    if p.engrave_motif and kind != "none":
        cx, cy = result.face_panels()["top"].face_center()
        result.motif = motif_loops(p.motif_shape, cx, cy, p.motif_size)
    if p.engrave_index:
        for number, panel in enumerate(result.panels, start=1):
            spot = _label_spot(panel, p.index_size, str(number))
            if spot is not None:
                result.index.append((str(number), spot[0], spot[1], p.index_size))
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
