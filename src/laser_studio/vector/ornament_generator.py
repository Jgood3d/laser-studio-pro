"""Générateur de boules de Noël personnalisables (prénom + motifs), géométrie pure.

Repère LSP : X vers la droite, Y vers le haut, en mm. Le centre de la boule est en (0, 0) pendant le calcul ;
`OrnamentGeometry.bounds` donne l'étendue réelle (l'accroche dépasse au-dessus du cercle).

Ce module ne dépend pas de Qt. Il décrit les FORMES, pas leur assemblage :

    outer   formes pleines qui forment le corps de la boule (disque, accroche)
    voids   zones à évider dans le corps (disque intérieur : on ne garde que l'anneau)
    solids  formes pleines ajoutées dans le vide (flocons, suspentes, barre de soutien) ; elles sont
            rognées au disque extérieur, jamais au-delà
    holes   trous retirés en dernier (trou de la ficelle)
    text    où et à quelle échelle poser le contour du prénom

La soudure de toutes ces formes (union / soustraction, y compris les contreformes des lettres a, e, o…) est
faite par `vector.ornament_region`, avec les opérations booléennes de QPainterPath : le laser ne doit jamais
suivre un contour qui traverse de la matière, sinon il découpe l'intérieur d'une lettre ou d'un flocon.
"""
from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

from laser_studio.vector.ornament_fills import FILL_KINDS, MIN_PITCH_MM, antler_shapes, fill_shapes
from laser_studio.vector.ornament_motifs import (
    HOLLY_STYLES, STAR_STYLES, TREE_STYLES, UPRIGHT_BUILDERS, MotifShape, bulb_shape, star_points_for, star_polygon,
)

Point = Tuple[float, float]
Polygon = List[Point]

HANGERS = ("Anneau", "Bouchon", "Capuchon", "Aucun")
RADIAL_MOTIFS = ("Flocons", "Étoiles")                       # symétriques : une pointe vers l'anneau
UPRIGHT_MOTIFS = tuple(UPRIGHT_BUILDERS)                    # ont un haut et un bas
GARLAND_MOTIFS = ("Guirlande",)                            # un fil d'ampoules d'un côté à l'autre du haut
MOTIFS = ("Flocons", "Étoiles", "Sapins", "Père Noël", "Bonhomme de neige", "Cadeaux", "Lune", "Houx", "Bougie",
          "Cloche", "Guirlande", "Aucun")
FLAKE_LAYOUTS = ("Suspendus", "Haut et bas", "Haut", "Bas")
FLAKE_STYLES = ("Classique", "Dentelle", "Étoile")
# Styles proposés selon le motif.
MOTIF_STYLES = {
    "Flocons": FLAKE_STYLES,
    "Étoiles": STAR_STYLES,
    "Sapins": TREE_STYLES,
    "Père Noël": ("Classique",),
    "Bonhomme de neige": ("Classique",),
    "Cadeaux": ("Classique",),
    "Lune": ("Classique",),
    "Houx": HOLLY_STYLES,
    "Bougie": ("Classique",),
    "Cloche": ("Classique",),
    "Guirlande": ("Classique",),
}
# Taille proposée par défaut selon le motif (mm).
MOTIF_DEFAULT_SIZE = {"Flocons": 16.0, "Étoiles": 12.0, "Sapins": 20.0, "Père Noël": 26.0,
                      "Bonhomme de neige": 24.0, "Cadeaux": 18.0, "Lune": 16.0, "Houx": 18.0, "Bougie": 22.0,
                      "Cloche": 18.0, "Guirlande": 10.0}
NAME_MODES = ("Découpé", "Gravé")        # Découpé : lettres soudées à l'anneau ; Gravé : lettres gravées sur une bande
FILLS = ("Aucun",) + FILL_KINDS          # remplissages à motif des zones au-dessus et au-dessous du prénom
FILL_ZONES = ("Haut et bas", "Haut", "Bas")
CROWNS = ("Aucune", "Bois de renne")
SUPPORTS = ("Barre", "Bandeau", "Aucun")  # Bandeau : une barre sous le prénom ET une au niveau du haut des lettres

# Précision des cercles : l'écart à un vrai cercle reste sous 0,01 mm jusqu'à 400 mm de diamètre.
CIRCLE_POINTS = 180
# Largeur de matière minimale d'un flocon ou d'une suspente que le laser tient sans casser (mm).
MIN_STEM_MM = 1.2
# Suspente d'un motif (le fil qui le relie à l'anneau) : largeur automatique, plus large que la tige d'un flocon.
STEM_AUTO_MIN_MM = 2.0
STEM_AUTO_RATIO = 0.12


class OrnamentError(ValueError):
    """Paramètres invalides (le code sert de clé de traduction `ornament.err.<code>`)."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


class OrnamentParams:
    def __init__(
        self,
        diameter=80.0,
        ring_width=4.0,
        hanger="Anneau",
        hole_diameter=3.0,
        name="",
        name_size=0.0,
        name_offset=None,
        support="Barre",
        bar_thickness=2.0,
        motif="Flocons",
        flake_layout="Suspendus",
        flake_style=None,
        flake_count=3,
        flake_size=16.0,
        motif_drop=0.0,
        stem_width=0.0,
        seed=1,
        name_mode="Découpé",
        band_height=0.0,
        band_frame=False,
        crown="Aucune",
        fill="Aucun",
        fill_zone="Haut et bas",
        fill_pitch=6.0,
    ):
        self.diameter = float(diameter)
        self.ring_width = float(ring_width)
        self.hanger = hanger
        self.hole_diameter = float(hole_diameter)
        self.name = name or ""
        # Hauteur du prénom en mm ; 0 = automatique (le prénom remplit la largeur de la boule).
        self.name_size = float(name_size)
        # Décalage vertical du prénom en mm (positif = vers le haut) ; None = selon la disposition.
        self.name_offset = None if name_offset is None else float(name_offset)
        self.support = support
        self.bar_thickness = float(bar_thickness)
        self.motif = motif
        self.flake_layout = flake_layout
        # None = le premier style du motif (« Classique » pour les flocons, « 5 branches » pour les étoiles…).
        self.flake_style = flake_style if flake_style is not None else MOTIF_STYLES.get(motif, ("Classique",))[0]
        self.flake_count = int(flake_count)
        self.flake_size = float(flake_size)
        # Écart du motif à l'anneau, en mm, vers le centre de la boule : positif = les motifs du haut ou suspendus
        # descendent (la suspente ou la tige s'allonge), ceux du bas montent ; négatif = ils se rapprochent de
        # l'anneau. Une tige garde toujours le contact avec l'anneau.
        self.motif_drop = float(motif_drop)
        # Largeur de la suspente en mm ; 0 = automatique (selon la taille du motif).
        self.stem_width = float(stem_width)
        self.seed = int(seed)
        # Gravé : le prénom est gravé sur une bande pleine qui traverse la boule (la bande est découpée avec la boule).
        self.name_mode = name_mode
        # Hauteur de la bande en mm ; 0 = automatique. Cadre : un filet gravé tout autour du prénom, dans la bande.
        self.band_height = float(band_height)
        self.band_frame = bool(band_frame)
        self.crown = crown
        self.fill = fill
        self.fill_zone = fill_zone
        self.fill_pitch = float(fill_pitch)


class Flake:
    """Un flocon posé : centre, rayon (du centre à la pointe) et rotation en degrés."""

    def __init__(self, cx, cy, radius, rotation, polygon):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.rotation = rotation
        self.polygon = polygon


class TextPlacement:
    """Transformation du contour du prénom : x_mm = scale * x + tx, y_mm = scale * y + ty.

    Le contour du texte est en Y vers le haut, la ligne de base à y = 0."""

    def __init__(self, scale, tx, ty, width, height, center_y=0.0):
        self.scale = scale
        self.tx = tx
        self.ty = ty
        self.center_y = center_y  # hauteur du milieu du prénom
        self.width = width    # largeur du prénom en mm
        self.height = height  # hauteur du prénom en mm (jambages compris)

    @property
    def baseline(self):
        return self.ty


class OrnamentGeometry:
    def __init__(self, params, radius, inner_radius):
        self.params = params
        self.radius = radius
        self.inner_radius = inner_radius
        self.outer: List[Polygon] = []
        self.voids: List[Polygon] = []
        self.solids: List[Polygon] = []
        self.holes: List[Polygon] = []
        self.cuts: List[Polygon] = []   # découpes dans les motifs (visage, yeux…), retirées des formes pleines
        self.late: List[Polygon] = []   # formes pleines ajoutées après ces découpes (moustache, nez)
        self.flakes: List[Flake] = []
        self.text: Optional[TextPlacement] = None
        self.bar: Optional[Polygon] = None      # barre à la ligne de base
        self.top_bar: Optional[Polygon] = None  # barre du haut (support « Bandeau »)
        self.hole_center: Optional[Point] = None
        # Limites verticales des motifs : bord bas de ceux du haut, bord haut de ceux du bas (None = aucun). Le prénom
        # se place entre les deux.
        self.upper_edge: Optional[float] = None
        self.lower_edge: Optional[float] = None
        self.floating_name = False  # le prénom ne touche rien : il tomberait à la découpe
        self.engrave_text = False   # le prénom est gravé (sur la bande) au lieu d'être découpé
        self.band: Optional[Polygon] = None            # bande pleine du prénom gravé
        self.band_span: Optional[Tuple[float, float]] = None  # (bas, haut) de la bande
        self.frame: List[Polygon] = []                 # filet gravé autour du prénom (contour extérieur puis intérieur)
        self.name_block: Optional[Tuple[float, float]] = None  # (bas, haut) de la zone du prénom
        # Remplissages : [(barres, zone de découpe rectangulaire)] ; ils sont rognés à la zone puis soudés.
        self.fills: List[Tuple[List[Polygon], Polygon]] = []
        self.bounds = (-radius, -radius, radius, radius)

    @property
    def width(self):
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self):
        return self.bounds[3] - self.bounds[1]


# ---------------------------------------------------------------------------------------------------------
# Formes de base
# ---------------------------------------------------------------------------------------------------------

def circle_polygon(cx, cy, r, n=CIRCLE_POINTS) -> Polygon:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rect_polygon(x0, y0, x1, y1) -> Polygon:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _rotate(points: Sequence[Point], degrees, cx=0.0, cy=0.0) -> Polygon:
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in points]


# Demi-profil d'un bras de flocon, du pied (x_v, w) à la pointe (1, 0), en unités de rayon : liste de (x, hauteur
# au-dessus de l'axe du bras). Les pointes latérales (« branches ») restent sous la bissectrice entre deux bras,
# avec de la marge : jamais de contact, même quand la tige est épaissie sur un petit flocon.
_TAN30 = math.tan(math.radians(30.0))


def _spike(x, length, w, lean=0.13):
    """Branche posée sur le bord du bras en `x` : (pied, pointe, retour au bord). Sa hauteur est limitée pour
    rester à bonne distance de la bissectrice ; vide si la tige est trop large pour la loger."""
    apex_x = x + lean
    room = _TAN30 * apex_x - w
    g = min(length, 0.45 * room)
    if g < 0.02:
        return [(x, w)]
    return [(x, w), (apex_x, w + g), (x + lean - 0.03, w)]


def _arm_profile(style, w):
    xv = w * math.sqrt(3.0)  # là où le bord du bras croise la bissectrice à 30° du bras voisin
    if style == "Étoile":
        w = w * 1.7
        return [(w * math.sqrt(3.0), w), (1.0, 0.0)]
    pts = [(xv, w)]
    if style == "Dentelle":
        for x in (0.30, 0.50, 0.68):
            pts += _spike(x, 0.075 + 0.05 * x, w, lean=0.07)
        pts += [(0.84, w), (1.0, 0.0)]
        return pts
    for x, g in ((0.34, 0.10), (0.58, 0.13)):
        pts += _spike(x, g, w)
    pts += [(0.80, w), (1.0, 0.0)]
    return pts


def snowflake_polygon(cx, cy, radius, rotation=0.0, style="Classique") -> Polygon:
    """Flocon à six bras, UN seul contour simple (aucune auto-intersection), prêt à découper.

    `radius` : du centre à la pointe d'un bras. `rotation` : angle du premier bras en degrés (90 = un bras
    vers le haut). La tige garde au moins MIN_STEM_MM de large, même pour un petit flocon."""
    if radius <= 0:
        raise OrnamentError("flake_size", value=radius)
    w = max(0.075, (MIN_STEM_MM / 2.0) / radius)
    upper = _arm_profile(style, w)
    lower = [(x, -y) for x, y in upper[:-1]]  # côté bas, du pied vers la pointe (la pointe n'est pas dupliquée)
    arm = lower + [upper[-1]] + list(reversed(upper[1:-1]))
    # Le pied haut (upper[0]) d'un bras est le pied bas (lower[0]) du suivant : on ne le répète pas.
    pts: Polygon = []
    for k in range(6):
        pts += _rotate([(x * radius, y * radius) for x, y in arm], rotation + 60.0 * k)
    return [(cx + x, cy + y) for x, y in pts]


def polygon_area(points: Sequence[Point]) -> float:
    """Aire signée (positive si les points tournent dans le sens trigonométrique)."""
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, list(points[1:]) + [points[0]]))


def is_simple(points: Sequence[Point]) -> bool:
    """Vrai si aucun côté non adjacent n'en croise un autre."""
    n = len(points)
    segs = [(points[i], points[(i + 1) % n]) for i in range(n)]

    def ccw(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            a, b = segs[i]
            c, d = segs[j]
            d1, d2, d3, d4 = ccw(a, b, c), ccw(a, b, d), ccw(c, d, a), ccw(c, d, b)
            if d1 * d2 < 0 and d3 * d4 < 0:
                return False
    return True


# ---------------------------------------------------------------------------------------------------------
# Accroche
# ---------------------------------------------------------------------------------------------------------

def _hanger_shapes(params, radius):
    """(formes pleines, centre du trou) de l'accroche, ou ([], None)."""
    if params.hanger == "Aucun":
        return [], None
    hole_r = params.hole_diameter / 2.0
    ring_r = hole_r + max(1.8, params.ring_width * 0.5)  # rayon extérieur de la petite boucle
    shapes: List[Polygon] = []
    if params.hanger in ("Bouchon", "Capuchon"):
        wide = params.hanger == "Capuchon"
        cap_w = max(params.diameter * (0.24 if wide else 0.18), 2 * ring_r + 2.0)
        cap_h = params.diameter * (0.08 if wide else 0.10)
        c = 1.5  # chanfrein des coins du bouchon
        y0, y1 = radius - 2.0, radius + cap_h
        shapes.append([(-cap_w / 2, y0), (cap_w / 2, y0), (cap_w / 2, y1 - c), (cap_w / 2 - c, y1),
                       (-cap_w / 2 + c, y1), (-cap_w / 2, y1 - c)])
        center = (0.0, y1 + ring_r - 1.0)
    else:
        center = (0.0, radius + ring_r - 1.5)
    shapes.append(circle_polygon(center[0], center[1], ring_r))
    return shapes, center


def _cap_slots(params, radius) -> List[Polygon]:
    """Les trois fentes verticales du capuchon (nervures), ou [] si le capuchon est trop petit pour les tenir."""
    if params.hanger != "Capuchon":
        return []
    hole_r = params.hole_diameter / 2.0
    ring_r = hole_r + max(1.8, params.ring_width * 0.5)
    cap_w = max(params.diameter * 0.24, 2 * ring_r + 2.0)
    cap_h = params.diameter * 0.08
    slot_w, margin = 1.2, 1.0
    y0, y1 = radius + margin, radius + cap_h - margin
    if cap_w < 12.0 or y1 - y0 < 2.0:
        return []
    pitch = cap_w / 4.0
    return [rect_polygon(x - slot_w / 2.0, y0, x + slot_w / 2.0, y1) for x in (-pitch, 0.0, pitch)]


# ---------------------------------------------------------------------------------------------------------
# Motifs
# ---------------------------------------------------------------------------------------------------------

def _note_edge(geo, upper=None, lower=None):
    """Retient le bord bas le plus bas des motifs du haut (`upper`) et le bord haut le plus haut de ceux du bas."""
    if upper is not None:
        geo.upper_edge = upper if geo.upper_edge is None else min(geo.upper_edge, upper)
    if lower is not None:
        geo.lower_edge = lower if geo.lower_edge is None else max(geo.lower_edge, lower)


def _radial_polygon(params, index, cx, cy, radius, rotation):
    """Forme d'un motif symétrique (flocon ou étoile) centrée en (cx, cy), une pointe à `rotation` degrés."""
    if params.motif == "Étoiles":
        return star_polygon(cx, cy, radius, star_points_for(params.flake_style, index), rotation)
    return snowflake_polygon(cx, cy, radius, rotation, params.flake_style)


def _stem_polygon(x0, y0, x1, y1, w):
    """Tige de largeur `w` entre deux points (rectangle orienté)."""
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n * w / 2.0, dx / n * w / 2.0
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def _stem_width(params, size):
    """Largeur de la suspente d'un motif : celle demandée, sinon automatique ; jamais sous MIN_STEM_MM."""
    if params.stem_width > 0.0:
        return max(params.stem_width, MIN_STEM_MM)
    return max(STEM_AUTO_MIN_MM, STEM_AUTO_RATIO * size)


def _stem_embed(size):
    """Profondeur dont la suspente s'enfonce dans le motif : assez pour sortir de la pointe fine du motif et
    s'ancrer là où il est plus large (au lieu d'un col étroit sous la suspente)."""
    return min(max(1.5, 0.12 * size), 3.0)


def _stem_shapes(x0, y0, x1, y1, w, r_in=None, r_out=None):
    """Suspente de (x0, y0), côté motif, à (x1, y1), côté anneau : UN seul contour.

    - côté anneau : la tige de largeur `w` monte droit et finit par un arc au milieu de la bande de l'anneau :
      ses deux flancs y sont toujours enfoncés, même décentrée, sans cran côté centre ni dépassement côté
      extérieur. Pas d'évasement : à grande largeur, il dessinait une pointe qui dépassait de l'anneau ;
    - côté motif : la tige se resserre en douceur (courbe en S) jusqu'à MIN_STEM_MM, la largeur du bras du motif,
      au lieu de finir par une marche brutale sur un bras fin. Ce resserrement commence dans le motif : il n'est
      visible que lorsque la suspente est large.

    Le contour est fusionné avec l'anneau et le motif plus loin."""
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy)
    if n < 1e-9:
        return [_stem_polygon(x0, y0, x1, y1, w)]
    ux, uy = dx / n, dy / n
    nx, ny = -uy, ux

    half = w / 2.0
    rm = None                       # côté anneau : arc au milieu de la bande de l'anneau
    if r_in is not None and r_out is not None and r_out > r_in:
        rm = (r_in + r_out) / 2.0

    def wall_end(sign):
        """Point du flanc (sign = +1 gauche, -1 droit) qui atteint le rayon `rm`, ou le bout `x1, y1`."""
        if rm is None:
            return x1 + sign * nx * half, y1 + sign * ny * half
        lo, hi = 0.0, n + r_out
        for _ in range(40):
            mid = (lo + hi) / 2.0
            if math.hypot(x0 + ux * mid + sign * nx * half, y0 + uy * mid + sign * ny * half) < rm:
                lo = mid
            else:
                hi = mid
        return x0 + ux * hi + sign * nx * half, y0 + uy * hi + sign * ny * half

    end_l, end_r = wall_end(+1), wall_end(-1)
    n = max(math.hypot(end_l[0] - x0, end_l[1] - y0), math.hypot(end_r[0] - x0, end_r[1] - y0)) if rm else n

    narrow = min(w, MIN_STEM_MM)
    neck = min(2.5 * (w - narrow) / 2.0, 0.6 * n)   # longueur du resserrement
    left, right = [], []
    steps = 10 if neck > 1e-6 and w - narrow > 1e-6 else 0
    for i in range(steps + 1):
        t = i / steps if steps else 0.0
        smooth = t * t * (3.0 - 2.0 * t)
        half = (narrow + (w - narrow) * smooth) / 2.0
        d = neck * t
        px, py = x0 + ux * d, y0 + uy * d
        left.append((px + nx * half, py + ny * half))
        right.append((px - nx * half, py - ny * half))
    if not steps:
        half = w / 2.0
        left.append((x0 + nx * half, y0 + ny * half))
        right.append((x0 - nx * half, y0 - ny * half))
    cap = [end_l]
    if rm is not None:
        a0, a1 = math.atan2(end_l[1], end_l[0]), math.atan2(end_r[1], end_r[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        cap += [(rm * math.cos(a0 + da * k / 6.0), rm * math.sin(a0 + da * k / 6.0)) for k in range(1, 6)]
    cap.append(end_r)
    return [left + cap + right[::-1]]


def _hanging_flakes(params, geo, rng):
    """Flocons suspendus à l'anneau par une fine suspente, comme sur la boule « Emma »."""
    n, size, r_in = params.flake_count, params.flake_size, geo.inner_radius
    a = size / 2.0
    stem = _stem_width(params, size)
    x_max = min(0.58 * r_in, 0.5 * (n - 1) * (size + 3.0)) if n > 1 else 0.0
    for i in range(n):
        x = 0.0 if n == 1 else -x_max + 2 * x_max * i / (n - 1)
        top = math.sqrt(max(r_in * r_in - x * x, 0.0))  # bord intérieur de l'anneau à cet x
        # Plus long au milieu, plus court sur les côtés : la ligne des flocons suit la courbure.
        centrality = 1.0 - (abs(x) / x_max if x_max > 0 else 0.0)
        base_hang = size * (0.30 + 0.40 * centrality) + 1.0
        extra = max(params.motif_drop, 1.0 - base_hang)   # il reste toujours 1 mm de suspente
        # Le décalage demandé ne doit pas faire sortir le flocon du disque : on le réduit jusqu'à ce qu'il rentre.
        while extra > 0.0 and math.hypot(x, top - (base_hang + extra) - 2 * a) > geo.radius - 0.8:
            extra = max(extra - 0.2, 0.0)
        hang = base_hang + extra
        cy = top - hang - a
        geo.flakes.append(Flake(x, cy, a, 90.0, _radial_polygon(params, i, x, cy, a, 90.0)))
        # La suspente s'enfonce dans le flocon (ancrage) et de 1 mm dans l'anneau, où elle s'évase.
        geo.solids += _stem_shapes(x, cy + a - _stem_embed(size), x, top + 1.0, stem, r_in, geo.radius)
        _note_edge(geo, upper=cy - a)


def _ring_flakes(params, geo, rng, top, bottom):
    """Flocons posés contre l'anneau, en haut et/ou en bas, comme sur la boule « Daniela »."""
    n, size, r_in = params.flake_count, params.flake_size, geo.inner_radius
    a = size / 2.0
    # Un bras du flocon pointe vers l'anneau et s'y enfonce de 2 mm : le flocon est soudé à l'anneau.
    rho = r_in + 2.0 - a
    step = max(math.degrees((size + 2.5) / max(rho, 1.0)), 28.0)
    for side, enabled in ((+1, top), (-1, bottom)):
        if not enabled:
            continue
        base = 90.0 if side > 0 else 270.0
        # En bas, on décale un peu les flocons pour qu'ils ne soient pas le miroir exact de ceux du haut.
        shift = 0.0 if side > 0 else step / 2.0 * (1 if n % 2 == 0 else 0)
        for i in range(n):
            ang = base + shift + (i - (n - 1) / 2.0) * step * (-1 if side < 0 else 1)
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            # Décalage vers le centre (réglage « descendre ») : au plus jusqu'à laisser 1 mm au centre de la boule.
            move = min(max(params.motif_drop, -2.0), max(rho - a - 1.0, 0.0))
            r_flake = rho - move
            cx, cy = r_flake * ca, r_flake * sa
            if move > 1.7:   # le bras (qui s'enfonce de 2 mm) ne touche plus l'anneau : une tige radiale relie le flocon à l'anneau
                geo.solids += _stem_shapes(cx, cy, (r_in + 1.0) * ca, (r_in + 1.0) * sa, _stem_width(params, size),
                                           r_in, geo.radius)
            rot = ang
            geo.flakes.append(Flake(cx, cy, a, rot, _radial_polygon(params, len(geo.flakes), cx, cy, a, rot)))
            _note_edge(geo, upper=cy - a if side > 0 else None, lower=cy + a if side < 0 else None)


def _add_shape(geo, shape: MotifShape, cx, cy, radius, rotation):
    geo.solids += shape.solids
    geo.cuts += shape.cuts
    geo.late += shape.late
    geo.flakes.append(Flake(cx, cy, radius, rotation, None))


def _axis_y(shape: MotifShape, side):
    """Hauteur du point d'attache d'un motif posé, sur son axe : le haut (side > 0) ou le bas (side < 0)."""
    return shape.axis_top() if side > 0 else shape.axis_bottom()


def _upright_motifs(params, geo):
    """Motifs à haut et bas (sapin, Père Noël, bonhomme de neige, cadeau). Suspendus : accrochés à l'anneau par une
    suspente. En haut : le sommet s'enfonce directement dans l'anneau. En bas : le pied repose dans l'anneau (la
    forêt de sapins au bas de la boule, la tête du Père Noël posée sur l'anneau). Contre l'anneau, ils restent
    DROITS (un sapin penché ou un Père Noël couché ferait bizarre) ; si les `flake_count` motifs ne tiennent pas côte
    à côte à la taille demandée, ils sont réduits (de 7 % à la fois, jusqu'à 8 mm) plutôt que de se chevaucher."""
    n, r_in = params.flake_count, geo.inner_radius
    build = UPRIGHT_BUILDERS[params.motif]
    size = params.flake_size
    base = build(size, params.flake_style)
    a_top, a_bot, width = base.axis_top(), base.axis_bottom(), base.width
    radius = max(width, base.height) / 2.0
    drop = params.motif_drop

    def inside(shape):
        return all(math.hypot(px, py) <= geo.radius - 0.8 for poly in shape.solids + shape.late for px, py in poly)

    if params.flake_layout == "Suspendus":
        stem = _stem_width(params, size)
        x_max = min(0.58 * r_in, 0.5 * (n - 1) * (width + 3.0)) if n > 1 else 0.0
        for i in range(n):
            x = 0.0 if n == 1 else -x_max + 2 * x_max * i / (n - 1)
            top = math.sqrt(max(r_in * r_in - x * x, 0.0))
            centrality = 1.0 - (abs(x) / x_max if x_max > 0 else 0.0)
            base_hang = size * (0.30 + 0.40 * centrality) + 1.0
            # Réglage « descendre » : la suspente s'allonge (ou se raccourcit, mais il en reste toujours 1 mm) ; le
            # décalage est réduit jusqu'à ce que le motif reste dans le disque. Sans réglage, rien ne change.
            extra = max(drop, 1.0 - base_hang)
            while True:
                hang = base_hang + extra
                anchor_y = top - hang
                placed = base.transformed(0.0, x, anchor_y - a_top)
                if extra == 0.0 or inside(placed):
                    break
                extra = max(extra - 0.2, 0.0) if extra > 0 else min(extra + 0.2, 0.0)
            geo.solids += _stem_shapes(x, anchor_y - _stem_embed(size), x, top + 1.0, stem, r_in, geo.radius)
            _add_shape(geo, placed, x, anchor_y - base.height / 2.0, radius, 0.0)
            _note_edge(geo, upper=placed.ymin)
        return

    depth = 2.5

    def make_placement(shape, top_anchor, bottom_anchor):
        def placement(x, side):
            """Motif droit posé à l'abscisse x contre l'anneau du haut (side > 0) ou du bas (side < 0). Le point
            d'appui s'enfonce le plus possible dans l'anneau (2,5 mm au plus) tant que le reste du motif reste dans
            le disque : une base plate large ne peut s'enfoncer que de peu."""
            ring_y = math.sqrt(max(r_in * r_in - x * x, 0.0))
            d = depth
            while True:
                if side > 0:
                    placed = shape.transformed(0.0, x, ring_y + d - top_anchor)
                else:
                    placed = shape.transformed(0.0, x, -ring_y - d - bottom_anchor)
                if d <= 0.8 or inside(placed):
                    return placed
                d = max(0.8, d - 0.1)
        return placement

    while True:
        placement = make_placement(base, a_top, a_bot)
        # Plus loin du centre, la base plate d'un motif large sortirait du disque : on borne l'écart des motifs.
        x_lim = 0.0
        while x_lim + 0.5 < r_in and inside(placement(x_lim + 0.5, +1)) and inside(placement(x_lim + 0.5, -1)):
            x_lim += 0.5
        if n == 1 or (width + 3.0) * (n - 1) <= 2.0 * x_lim or size * 0.93 < 8.0:
            break
        size *= 0.93
        base = build(size, params.flake_style)
        a_top, a_bot, width = base.axis_top(), base.axis_bottom(), base.width
        radius = max(width, base.height) / 2.0
    step_x = min(width + 3.0, 2.0 * x_lim / (n - 1)) if n > 1 else 0.0
    for side, enabled in ((+1, params.flake_layout in ("Haut", "Haut et bas")),
                          (-1, params.flake_layout in ("Bas", "Haut et bas"))):
        if not enabled:
            continue
        for i in range(n):
            x = (i - (n - 1) / 2.0) * step_x
            placed = placement(x, side)
            # Réglage « descendre » : le motif s'écarte de l'anneau vers le centre (les motifs du bas montent). Il
            # reste dans le disque ; une tige entre le motif et l'anneau garde le contact quand il ne le touche plus.
            move = drop
            while move != 0.0:
                moved = placed.transformed(0.0, 0.0, -move * side)
                if inside(moved):
                    break
                move = move - 0.1 if move > 0 else move + 0.1
                if abs(move) < 0.1:
                    move = 0.0
            if move != 0.0:
                placed = moved
                if move > 0.0:
                    ring_y = math.sqrt(max(r_in * r_in - x * x, 0.0))
                    stem = _stem_width(params, size)
                    embed = _stem_embed(size)
                    if side > 0:
                        y_a = _axis_y(placed, +1)
                        geo.solids += _stem_shapes(x, y_a - embed, x, ring_y + 1.0, stem, r_in, geo.radius)
                    else:
                        y_a = _axis_y(placed, -1)
                        geo.solids += _stem_shapes(x, y_a + embed, x, -ring_y - 1.0, stem, r_in, geo.radius)
            _note_edge(geo, upper=placed.ymin if side > 0 else None, lower=placed.ymax if side < 0 else None)
            _add_shape(geo, placed, x, (placed.ymin + placed.ymax) / 2.0, radius, 0.0)


def _garland(params, geo):
    """Guirlande : un fil qui plonge d'un côté du haut de l'anneau à l'autre, avec `flake_count` ampoules qui
    pendent. Le fil et ses deux extrémités s'enfoncent dans l'anneau ; chaque ampoule est soudée au fil."""
    n, size, r_in = params.flake_count, params.flake_size, geo.inner_radius
    string_w = max(MIN_STEM_MM, 0.03 * params.diameter)
    end_angle = math.radians(36.0)
    xe = (r_in + 1.5) * math.cos(end_angle)
    ye = (r_in + 1.5) * math.sin(end_angle)
    sag = 0.26 * 2.0 * xe

    def y_at(x):
        return ye - sag * (1.0 - (x / xe) ** 2)

    def slope(x):
        return 2.0 * sag * x / (xe * xe)

    # Ruban du fil : points décalés de chaque côté de la courbe, perpendiculairement à elle.
    steps = 48
    left, right = [], []
    for i in range(steps + 1):
        x = -xe + 2.0 * xe * i / steps
        norm = math.hypot(1.0, slope(x))
        nx, ny = -slope(x) / norm, 1.0 / norm
        left.append((x + nx * string_w / 2.0, y_at(x) + ny * string_w / 2.0))
        right.append((x - nx * string_w / 2.0, y_at(x) - ny * string_w / 2.0))
    geo.solids.append(left + list(reversed(right)))

    bulb = bulb_shape(size)
    a_top = bulb.axis_top()
    reach = 0.74 * xe
    for i in range(n):
        x = 0.0 if n == 1 else -reach + 2.0 * reach * i / (n - 1)
        # La douille remonte de 0,8 mm dans l'épaisseur du fil : l'ampoule est soudée.
        placed = bulb.transformed(0.0, x, y_at(x) - string_w / 2.0 + 0.8 - a_top)
        _add_shape(geo, placed, x, (placed.ymin + placed.ymax) / 2.0, size / 2.0, 0.0)
        _note_edge(geo, upper=placed.ymin)


# ---------------------------------------------------------------------------------------------------------
# Prénom
# ---------------------------------------------------------------------------------------------------------

def _auto_name_offset(params, radius):
    layout = params.flake_layout if params.motif != "Aucun" else None
    return {"Suspendus": -0.18, "Haut": -0.14, "Bas": 0.14}.get(layout, 0.0) * radius


def place_text(params, geo, bounds):
    """Échelle et position du prénom. `bounds` = (x0, y0, x1, y1) de son contour (Y vers le haut, ligne de
    base à 0, unités quelconques)."""
    x0, y0, x1, y1 = bounds
    tw, th = x1 - x0, y1 - y0
    if tw <= 0 or th <= 0:
        return None
    radius, r_in = geo.radius, geo.inner_radius
    band = None
    if params.name_offset is not None:
        offset = params.name_offset
    elif geo.upper_edge is not None or geo.lower_edge is not None:
        # Le prénom occupe la bande libre entre les motifs du haut et ceux du bas.
        gap = 2.0
        hi = geo.upper_edge - gap if geo.upper_edge is not None else 0.85 * r_in
        lo = geo.lower_edge + gap if geo.lower_edge is not None else -0.85 * r_in
        band = max(hi - lo, 6.0)
        offset = (hi + lo) / 2.0
    else:
        offset = _auto_name_offset(params, radius)
    if params.name_size > 0:
        scale = params.name_size / th
    else:
        chord = 2.0 * math.sqrt(max(r_in * r_in - offset * offset, 0.0))
        max_h = 0.34 * params.diameter if band is None else min(band, 0.34 * params.diameter)
        scale = min((chord + params.ring_width) / tw, max_h / th)
    # Jamais plus large que le disque extérieur à la hauteur du prénom.
    outer_chord = 2.0 * math.sqrt(max(radius * radius - offset * offset, 0.0)) - 1.0
    scale = min(scale, outer_chord / tw)
    return TextPlacement(scale, -scale * (x0 + x1) / 2.0, offset - scale * (y0 + y1) / 2.0, tw * scale, th * scale, offset)


def _band_geometry(params, geo):
    """(bas, haut) de la bande du prénom gravé. Elle se pose directement sous les motifs du haut, directement au-dessus
    de ceux du bas, ou au milieu de la bande libre quand il y en a des deux côtés."""
    r_in = geo.inner_radius
    bh = params.band_height if params.band_height > 0 else 0.24 * params.diameter
    bh = min(max(bh, 6.0), 0.6 * params.diameter)
    gap = 2.0
    up, lo = geo.upper_edge, geo.lower_edge
    if params.name_offset is not None:
        c = params.name_offset
    elif up is not None and lo is not None:
        c = ((up - gap) + (lo + gap)) / 2.0
    elif up is not None:
        c = up - gap - bh / 2.0
    elif lo is not None:
        c = lo + gap + bh / 2.0
    else:
        c = 0.0
    limit = max(0.85 * r_in - bh / 2.0, 0.0)
    c = max(-limit, min(limit, c))
    return c - bh / 2.0, c + bh / 2.0


def _place_name_in_band(params, geo, bounds, span):
    x0, y0, x1, y1 = bounds
    tw, th = x1 - x0, y1 - y0
    if tw <= 0 or th <= 0:
        return None
    lo, hi = span
    c, bh = (lo + hi) / 2.0, hi - lo
    pad = max(1.5, 0.12 * bh)
    target = params.name_size if params.name_size > 0 else bh - 2.0 * pad
    # Largeur disponible : celle du disque intérieur au bord de la bande le plus éloigné du centre, moins une marge.
    far = max(abs(lo), abs(hi))
    avail = 2.0 * math.sqrt(max(geo.inner_radius ** 2 - far ** 2, 0.0)) - 2.0 * 2.0
    scale = min(target / th, max(avail, 1.0) / tw)
    return TextPlacement(scale, -scale * (x0 + x1) / 2.0, c - scale * (y0 + y1) / 2.0, tw * scale, th * scale, c)


def _rounded_rect(x0, y0, x1, y1, r, n=8) -> Polygon:
    r = max(min(r, (x1 - x0) / 2.0, (y1 - y0) / 2.0), 0.01)
    pts: Polygon = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, 90.0), (x0 + r, y0 + r, 180.0), (x1 - r, y0 + r, 270.0)):
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _band_frame(geo, span, line=0.6, inset=1.2) -> List[Polygon]:
    """Filet gravé en retrait des bords de la bande : [contour extérieur, contour intérieur] (un trait de `line`)."""
    lo, hi = span
    y0, y1 = lo + inset, hi - inset
    if y1 - y0 < 3.0:
        return []
    far = max(abs(y0), abs(y1))
    half = math.sqrt(max(geo.inner_radius ** 2 - far ** 2, 0.0)) - 2.0
    if half < 6.0:
        return []
    r = min(3.0, (y1 - y0) / 2.0)
    return [_rounded_rect(-half, y0, half, y1, r), _rounded_rect(-half + line, y0 + line, half - line, y1 - line, max(r - line, 0.2))]


def _add_fills(params, geo):
    """Remplissages à motif au-dessus et/ou au-dessous du prénom."""
    if params.fill == "Aucun" or geo.name_block is None:
        return
    lo, hi = geo.name_block
    radius = geo.radius
    box_x = (-radius - 2.0, radius + 2.0)
    overlap = 0.8  # les barres mordent un peu dans la bande, pour y être soudées
    zones = []
    if params.fill_zone in ("Haut", "Haut et bas"):
        zones.append((hi - overlap, radius + 1.0))
    if params.fill_zone in ("Bas", "Haut et bas"):
        zones.append((-radius - 1.0, lo + overlap))
    for y0, y1 in zones:
        if y1 - y0 < 1.0:
            continue
        clip = rect_polygon(box_x[0], y0, box_x[1], y1)
        geo.fills.append((fill_shapes(params.fill, params.fill_pitch, (box_x[0], y0, box_x[1], y1)), clip))


# ---------------------------------------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------------------------------------

def validate(params):
    d = params.diameter
    if not 30.0 <= d <= 400.0:
        raise OrnamentError("diameter", value=d)
    if not 1.5 <= params.ring_width <= d * 0.25:
        raise OrnamentError("ring_width", value=params.ring_width, lo=1.5, hi=d * 0.25)
    if params.hanger not in HANGERS:
        raise OrnamentError("hanger", value=params.hanger)
    if params.hanger != "Aucun" and not 1.5 <= params.hole_diameter <= 10.0:
        raise OrnamentError("hole", value=params.hole_diameter)
    if params.motif not in MOTIFS:
        raise OrnamentError("motif", value=params.motif)
    if params.support not in SUPPORTS:
        raise OrnamentError("support", value=params.support)
    if params.name_mode not in NAME_MODES:
        raise OrnamentError("name_mode", value=params.name_mode)
    if params.crown not in CROWNS:
        raise OrnamentError("crown", value=params.crown)
    if params.fill not in FILLS or params.fill_zone not in FILL_ZONES:
        raise OrnamentError("fill", value=params.fill)
    if params.fill != "Aucun" and not MIN_PITCH_MM <= params.fill_pitch <= d * 0.4:
        raise OrnamentError("fill_pitch", value=params.fill_pitch, lo=MIN_PITCH_MM, hi=d * 0.4)
    if params.name_mode == "Gravé" and params.band_height != 0 and not 6.0 <= params.band_height <= 0.6 * d:
        raise OrnamentError("band_height", value=params.band_height, lo=6.0, hi=0.6 * d)
    if len(params.name) > 40:
        raise OrnamentError("name_too_long", value=len(params.name))
    if params.motif in RADIAL_MOTIFS + UPRIGHT_MOTIFS + GARLAND_MOTIFS:
        if params.motif not in GARLAND_MOTIFS and params.flake_layout not in FLAKE_LAYOUTS:
            raise OrnamentError("layout", value=params.flake_layout)
        if params.flake_style not in MOTIF_STYLES[params.motif]:
            raise OrnamentError("style", value=params.flake_style)
        if not 1 <= params.flake_count <= 7:
            raise OrnamentError("flake_count", value=params.flake_count)
        if not 8.0 <= params.flake_size <= d * 0.6:
            raise OrnamentError("flake_size", value=params.flake_size, lo=8.0, hi=d * 0.6)
    if params.support in ("Barre", "Bandeau") and not 1.0 <= params.bar_thickness <= 6.0:
        raise OrnamentError("bar", value=params.bar_thickness)


def build_ornament(params, text_bounds=None) -> OrnamentGeometry:
    """Calcule les formes d'une boule. `text_bounds` : étendue du contour du prénom (voir `place_text`),
    ou None s'il n'y a pas de prénom."""
    validate(params)
    radius = params.diameter / 2.0
    geo = OrnamentGeometry(params, radius, radius - params.ring_width)
    rng = random.Random(params.seed)

    geo.outer.append(circle_polygon(0.0, 0.0, radius))
    hanger_shapes, hole_center = _hanger_shapes(params, radius)
    geo.outer += hanger_shapes
    geo.voids.append(circle_polygon(0.0, 0.0, geo.inner_radius))
    geo.holes += _cap_slots(params, radius)
    if params.crown == "Bois de renne":
        geo.outer += antler_shapes(radius, max(2.0, 0.045 * params.diameter))
    if hole_center is not None:
        geo.hole_center = hole_center
        geo.holes.append(circle_polygon(hole_center[0], hole_center[1], params.hole_diameter / 2.0))

    if params.motif in RADIAL_MOTIFS:
        if params.flake_layout == "Suspendus":
            _hanging_flakes(params, geo, rng)
        else:
            _ring_flakes(params, geo, rng, top=params.flake_layout in ("Haut", "Haut et bas"),
                         bottom=params.flake_layout in ("Bas", "Haut et bas"))
        geo.solids += [f.polygon for f in geo.flakes]
    elif params.motif in UPRIGHT_MOTIFS:
        _upright_motifs(params, geo)
    elif params.motif in GARLAND_MOTIFS:
        _garland(params, geo)

    engraved = params.name_mode == "Gravé"
    has_name = bool(params.name.strip()) and text_bounds is not None
    if engraved:
        span = _band_geometry(params, geo)
        geo.band_span = span
        geo.name_block = span
        geo.band = rect_polygon(-radius, span[0], radius, span[1])
        geo.solids.append(geo.band)
        geo.engrave_text = True
        if has_name:
            geo.text = _place_name_in_band(params, geo, text_bounds, span)
        if params.band_frame:
            geo.frame = _band_frame(geo, span)
    elif has_name:
        geo.text = place_text(params, geo, text_bounds)
        if geo.text is not None:
            t = geo.text
            geo.name_block = (t.center_y - t.height / 2.0, t.center_y + t.height / 2.0)
            if params.support in ("Barre", "Bandeau"):
                thick = params.bar_thickness
                # La barre est à cheval sur la ligne de base : 70 % au-dessus, là où les lettres la croisent.
                geo.bar = rect_polygon(-radius, t.baseline - 0.3 * thick, radius, t.baseline + 0.7 * thick)
                geo.solids.append(geo.bar)
                if params.support == "Bandeau":
                    # Bandeau : une seconde barre au sommet du prénom, à cheval sur la ligne du haut des lettres.
                    top = t.center_y + t.height / 2.0
                    geo.top_bar = rect_polygon(-radius, top - 0.7 * thick, radius, top + 0.3 * thick)
                    geo.solids.append(geo.top_bar)
            else:
                # Sans barre, le prénom ne tient que s'il touche l'anneau des deux côtés.
                chord = 2.0 * math.sqrt(max(geo.inner_radius ** 2 - t.center_y ** 2, 0.0))
                geo.floating_name = t.width < chord - 0.5
    if geo.name_block is None:
        c = params.name_offset if params.name_offset is not None else _auto_name_offset(params, radius)
        geo.name_block = (c - 0.12 * params.diameter, c + 0.12 * params.diameter)
    _add_fills(params, geo)

    xs = [p[0] for poly in geo.outer for p in poly]
    ys = [p[1] for poly in geo.outer for p in poly]
    geo.bounds = (min(xs), min(ys), max(xs), max(ys))
    return geo
