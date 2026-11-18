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

Point = Tuple[float, float]
Polygon = List[Point]

HANGERS = ("Anneau", "Bouchon", "Aucun")
MOTIFS = ("Flocons", "Aucun")
FLAKE_LAYOUTS = ("Suspendus", "Haut et bas", "Haut", "Bas")
FLAKE_STYLES = ("Classique", "Dentelle", "Étoile")
SUPPORTS = ("Barre", "Aucun")

# Précision des cercles : l'écart à un vrai cercle reste sous 0,01 mm jusqu'à 400 mm de diamètre.
CIRCLE_POINTS = 180
# Largeur de matière minimale d'un flocon ou d'une suspente que le laser tient sans casser (mm).
MIN_STEM_MM = 1.2


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
        flake_style="Classique",
        flake_count=3,
        flake_size=16.0,
        seed=1,
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
        self.flake_style = flake_style
        self.flake_count = int(flake_count)
        self.flake_size = float(flake_size)
        self.seed = int(seed)


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
        self.flakes: List[Flake] = []
        self.text: Optional[TextPlacement] = None
        self.bar: Optional[Polygon] = None
        self.hole_center: Optional[Point] = None
        self.floating_name = False  # le prénom ne touche rien : il tomberait à la découpe
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
    if params.hanger == "Bouchon":
        cap_w = max(params.diameter * 0.18, 2 * ring_r + 2.0)
        cap_h = params.diameter * 0.10
        c = 1.5  # chanfrein des coins du bouchon
        y0, y1 = radius - 2.0, radius + cap_h
        shapes.append([(-cap_w / 2, y0), (cap_w / 2, y0), (cap_w / 2, y1 - c), (cap_w / 2 - c, y1),
                       (-cap_w / 2 + c, y1), (-cap_w / 2, y1 - c)])
        center = (0.0, y1 + ring_r - 1.0)
    else:
        center = (0.0, radius + ring_r - 1.5)
    shapes.append(circle_polygon(center[0], center[1], ring_r))
    return shapes, center


# ---------------------------------------------------------------------------------------------------------
# Motifs
# ---------------------------------------------------------------------------------------------------------

def _hanging_flakes(params, geo, rng):
    """Flocons suspendus à l'anneau par une fine suspente, comme sur la boule « Emma »."""
    n, size, r_in = params.flake_count, params.flake_size, geo.inner_radius
    a = size / 2.0
    stem = max(MIN_STEM_MM, 0.07 * size)
    x_max = min(0.58 * r_in, 0.5 * (n - 1) * (size + 3.0)) if n > 1 else 0.0
    for i in range(n):
        x = 0.0 if n == 1 else -x_max + 2 * x_max * i / (n - 1)
        top = math.sqrt(max(r_in * r_in - x * x, 0.0))  # bord intérieur de l'anneau à cet x
        # Plus long au milieu, plus court sur les côtés : la ligne des flocons suit la courbure.
        centrality = 1.0 - (abs(x) / x_max if x_max > 0 else 0.0)
        hang = size * (0.30 + 0.40 * centrality) + 1.0
        cy = top - hang - a
        geo.flakes.append(Flake(x, cy, a, 90.0, snowflake_polygon(x, cy, a, 90.0, params.flake_style)))
        # La suspente part de la pointe haute du flocon et s'enfonce de 1 mm dans l'anneau.
        geo.solids.append(rect_polygon(x - stem / 2, cy + a - 0.5, x + stem / 2, top + 1.0))


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
            cx, cy = rho * math.cos(math.radians(ang)), rho * math.sin(math.radians(ang))
            rot = ang
            geo.flakes.append(Flake(cx, cy, a, rot, snowflake_polygon(cx, cy, a, rot, params.flake_style)))


# ---------------------------------------------------------------------------------------------------------
# Prénom
# ---------------------------------------------------------------------------------------------------------

def _auto_name_offset(params, radius):
    layout = params.flake_layout if params.motif == "Flocons" else None
    return {"Suspendus": -0.18, "Haut": -0.14, "Bas": 0.14}.get(layout, 0.0) * radius


def place_text(params, geo, bounds):
    """Échelle et position du prénom. `bounds` = (x0, y0, x1, y1) de son contour (Y vers le haut, ligne de
    base à 0, unités quelconques)."""
    x0, y0, x1, y1 = bounds
    tw, th = x1 - x0, y1 - y0
    if tw <= 0 or th <= 0:
        return None
    radius, r_in = geo.radius, geo.inner_radius
    offset = params.name_offset if params.name_offset is not None else _auto_name_offset(params, radius)
    if params.name_size > 0:
        scale = params.name_size / th
    else:
        chord = 2.0 * math.sqrt(max(r_in * r_in - offset * offset, 0.0))
        scale = min((chord + params.ring_width) / tw, 0.34 * params.diameter / th)
    # Jamais plus large que le disque extérieur à la hauteur du prénom.
    outer_chord = 2.0 * math.sqrt(max(radius * radius - offset * offset, 0.0)) - 1.0
    scale = min(scale, outer_chord / tw)
    return TextPlacement(scale, -scale * (x0 + x1) / 2.0, offset - scale * (y0 + y1) / 2.0, tw * scale, th * scale, offset)


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
    if len(params.name) > 40:
        raise OrnamentError("name_too_long", value=len(params.name))
    if params.motif == "Flocons":
        if params.flake_layout not in FLAKE_LAYOUTS:
            raise OrnamentError("layout", value=params.flake_layout)
        if params.flake_style not in FLAKE_STYLES:
            raise OrnamentError("style", value=params.flake_style)
        if not 1 <= params.flake_count <= 7:
            raise OrnamentError("flake_count", value=params.flake_count)
        if not 8.0 <= params.flake_size <= d * 0.6:
            raise OrnamentError("flake_size", value=params.flake_size, lo=8.0, hi=d * 0.6)
    if params.support == "Barre" and not 1.0 <= params.bar_thickness <= 6.0:
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
    if hole_center is not None:
        geo.hole_center = hole_center
        geo.holes.append(circle_polygon(hole_center[0], hole_center[1], params.hole_diameter / 2.0))

    if params.motif == "Flocons":
        if params.flake_layout == "Suspendus":
            _hanging_flakes(params, geo, rng)
        else:
            _ring_flakes(params, geo, rng, top=params.flake_layout in ("Haut", "Haut et bas"),
                         bottom=params.flake_layout in ("Bas", "Haut et bas"))
        geo.solids += [f.polygon for f in geo.flakes]

    if params.name.strip() and text_bounds is not None:
        geo.text = place_text(params, geo, text_bounds)
        if geo.text is not None:
            t = geo.text
            if params.support == "Barre":
                thick = params.bar_thickness
                # La barre est à cheval sur la ligne de base : 70 % au-dessus, là où les lettres la croisent.
                geo.bar = rect_polygon(-radius, t.baseline - 0.3 * thick, radius, t.baseline + 0.7 * thick)
                geo.solids.append(geo.bar)
            else:
                # Sans barre, le prénom ne tient que s'il touche l'anneau des deux côtés.
                chord = 2.0 * math.sqrt(max(geo.inner_radius ** 2 - t.center_y ** 2, 0.0))
                geo.floating_name = t.width < chord - 0.5

    xs = [p[0] for poly in geo.outer for p in poly]
    ys = [p[1] for poly in geo.outer for p in poly]
    geo.bounds = (min(xs), min(ys), max(xs), max(ys))
    return geo
