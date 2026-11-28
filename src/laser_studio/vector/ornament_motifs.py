"""Motifs des boules de Noël, géométrie pure (sans Qt) : étoiles, sapins, Père Noël, bonhomme de neige, cadeau.

Repère local d'un motif : X vers la droite, Y vers le haut, en mm ; le « haut » du motif est son sommet (pointe du
sapin, bonnet du Père Noël…), son « bas » est son pied. Un motif est fait de trois listes de polygones :

    solids  formes pleines, qui se soudent entre elles
    cuts    découpes dans ces formes pleines (visage du Père Noël, yeux, fente du ruban…)
    late    formes pleines ajoutées APRÈS les découpes (moustache et nez dans le visage évidé)

Tous les polygones sont lus par `ornament_region`, qui les met dans le sens trigonométrique avant de les
souder : l'orientation écrite ici n'a pas d'importance.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple

Point = Tuple[float, float]
Polygon = List[Point]

# Plus petite largeur de matière ou de trou que le laser tient proprement (mm). Un détail plus fin est omis.
MIN_DETAIL_MM = 1.2

STAR_STYLES = ("5 branches", "4 branches", "8 branches", "Mixte")
TREE_STYLES = ("Classique", "Simple", "Fin")
HOLLY_STYLES = ("Trio", "Duo")

# Rapport rayon intérieur / rayon extérieur selon le nombre de branches : branches fines mais jamais filiformes.
_STAR_INNER = {4: 0.32, 5: 0.42, 8: 0.50}


def circle(cx, cy, r, n=48) -> Polygon:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def ellipse(cx, cy, rx, ry, n=48) -> Polygon:
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rect(x0, y0, x1, y1) -> Polygon:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def star_polygon(cx, cy, radius, points=5, rotation=90.0) -> Polygon:
    """Étoile à `points` branches, UN contour simple. `rotation` : angle de la première pointe en degrés (90 = vers
    le haut). `radius` : du centre à la pointe."""
    inner = radius * _STAR_INNER.get(points, 0.45)
    out: Polygon = []
    for i in range(2 * points):
        r = radius if i % 2 == 0 else inner
        a = math.radians(rotation + 180.0 * i / points)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def star_points_for(style, index):
    """Nombre de branches de la `index`-ième étoile pour un style (« Mixte » alterne 5, 4 et 8)."""
    if style == "Mixte":
        return (5, 4, 8)[index % 3]
    return {"4 branches": 4, "8 branches": 8}.get(style, 5)


def point_in_polygon(x, y, poly: Sequence[Point]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


class MotifShape:
    def __init__(self, solids, cuts=(), late=()):
        self.solids: List[Polygon] = [list(p) for p in solids]
        self.cuts: List[Polygon] = [list(p) for p in cuts]
        self.late: List[Polygon] = [list(p) for p in late]

    def _points(self):
        return [p for poly in self.solids + self.late for p in poly]

    @property
    def ymin(self):
        return min(p[1] for p in self._points())

    @property
    def ymax(self):
        return max(p[1] for p in self._points())

    @property
    def width(self):
        xs = [p[0] for p in self._points()]
        return max(xs) - min(xs)

    @property
    def height(self):
        return self.ymax - self.ymin

    def contains(self, x, y):
        """Vrai si (x, y) est dans de la matière du motif (formes pleines moins découpes, plus formes tardives)."""
        if any(point_in_polygon(x, y, p) for p in self.late):
            return True
        return any(point_in_polygon(x, y, p) for p in self.solids) and not any(
            point_in_polygon(x, y, c) for c in self.cuts)

    def axis_top(self):
        """Hauteur du point le plus haut de l'axe (x = 0) qui est dans de la matière : là où s'attache la suspente
        ou la pointe qui s'enfonce dans l'anneau."""
        return self._scan(self.ymax, self.ymin)

    def axis_bottom(self):
        """Idem pour le point le plus bas de l'axe : là où le motif repose sur l'anneau."""
        return self._scan(self.ymin, self.ymax)

    def _scan(self, start, stop, steps=400):
        for i in range(steps + 1):
            y = start + (stop - start) * i / steps
            if self.contains(1e-6, y):  # à peine décalé de l'axe : un sommet exactement sur l'axe fausserait le test
                return y
        return (self.ymax + self.ymin) / 2.0

    def transformed(self, rotation=0.0, dx=0.0, dy=0.0):
        """Copie tournée de `rotation` degrés autour de l'origine puis décalée de (dx, dy)."""
        a = math.radians(rotation)
        ca, sa = math.cos(a), math.sin(a)

        def move(poly):
            return [(x * ca - y * sa + dx, x * sa + y * ca + dy) for x, y in poly]

        return MotifShape([move(p) for p in self.solids], [move(p) for p in self.cuts], [move(p) for p in self.late])


# ---------------------------------------------------------------------------------------------------------
# Sapin
# ---------------------------------------------------------------------------------------------------------

def tree_shape(h, style="Classique") -> MotifShape:
    """Sapin à étages de hauteur `h`, pied en (0, 0), UN contour simple."""
    tiers = {"Simple": 1, "Fin": 5}.get(style, 3)
    top_w = {"Simple": 0.55, "Fin": 0.50}.get(style, 0.62) * h
    trunk_w = max(1.6, 0.09 * h)
    trunk_h = 0.12 * h
    bottoms = [trunk_h + (h - trunk_h) * k / tiers for k in range(tiers)]
    widths = [top_w * (1.0 - 0.5 * k / max(tiers - 1, 1)) for k in range(tiers)]
    right: Polygon = [(0.0, h)]
    for k in range(tiers - 1, -1, -1):
        right.append((widths[k] / 2.0, bottoms[k]))
        if k > 0:
            # Le bord de l'étage du dessous repart un peu en retrait du coin de l'étage du dessus.
            right.append((widths[k] / 2.0 - 0.18 * widths[k], bottoms[k]))
    right += [(trunk_w / 2.0, trunk_h), (trunk_w / 2.0, 0.0)]
    left = [(-x, y) for x, y in reversed(right)][:-1]  # sans le sommet, déjà dans `right`
    return MotifShape([right + left])


# ---------------------------------------------------------------------------------------------------------
# Père Noël (tête)
# ---------------------------------------------------------------------------------------------------------

def _smooth_closed(points, iterations=2):
    """Contour fermé arrondi (Chaikin) : les coins du polygone de contrôle deviennent des courbes."""
    for _ in range(iterations):
        out = []
        n = len(points)
        for i in range(n):
            (x0, y0), (x1, y1) = points[i], points[(i + 1) % n]
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        points = out
    return points


def _capsule(x0, y0, x1, y1, n=10) -> Polygon:
    """Rectangle aux deux bouts en demi-cercle (bandeau de fourrure du bonnet)."""
    r = (y1 - y0) / 2.0
    cy = (y0 + y1) / 2.0
    right = [(x1 - r + r * math.cos(math.radians(-90 + 180 * i / n)), cy + r * math.sin(math.radians(-90 + 180 * i / n)))
             for i in range(n + 1)]
    left = [(x0 + r + r * math.cos(math.radians(90 + 180 * i / n)), cy + r * math.sin(math.radians(90 + 180 * i / n)))
            for i in range(n + 1)]
    return right + left


def santa_shape(h) -> MotifShape:
    """Tête de Père Noël de hauteur `h`, pied (bas de la barbe) en (0, 0) : bonnet dont la pointe retombe sur le côté
    avec son pompon, bandeau de fourrure arrondi, barbe à deux lobes, visage évidé fermé en bas par la moustache
    (deux boucles) et le nez. Tout est soudé : le pompon touche la pointe du bonnet, la moustache la barbe.
    Sous ~17 mm de haut, le visage serait trop fin : il reste une silhouette pleine."""
    s = h
    # Bonnet : le sommet est sur l'axe (là s'attache la suspente), la pointe retombe vers la droite.
    hat_ctrl = [(-0.29, 0.62), (-0.27, 0.78), (-0.17, 0.90), (-0.02, 0.96), (0.15, 0.95), (0.29, 0.90), (0.37, 0.82),
                (0.31, 0.80), (0.24, 0.80), (0.27, 0.70), (0.29, 0.62)]
    hat = _smooth_closed([(x * s, y * s) for x, y in hat_ctrl], 2)
    pompom = circle(0.375 * s, 0.80 * s, 0.075 * s, 32)          # posé à cheval sur la pointe du bonnet
    brim = _capsule(-0.37 * s, 0.555 * s, 0.37 * s, 0.675 * s)
    beard_ctrl = [(-0.36, 0.60), (-0.40, 0.46), (-0.37, 0.31), (-0.29, 0.17), (-0.20, 0.06), (-0.10, 0.0),
                  (-0.03, 0.05), (0.03, 0.05), (0.10, 0.0), (0.20, 0.06), (0.29, 0.17), (0.37, 0.31), (0.40, 0.46),
                  (0.36, 0.60)]
    beard = _smooth_closed([(x * s, y * s) for x, y in beard_ctrl], 2)
    solids = [hat, pompom, brim, beard]
    cuts: List[Polygon] = []
    late: List[Polygon] = []
    if 0.11 * s >= MIN_DETAIL_MM and 0.07 * s >= MIN_DETAIL_MM:
        cuts.append(ellipse(0.0, 0.505 * s, 0.215 * s, 0.085 * s))
        # Moustache : deux boucles qui se chevauchent au centre, soudées à la barbe sous le visage, puis le nez.
        late.append(ellipse(-0.10 * s, 0.425 * s, 0.13 * s, 0.055 * s))
        late.append(ellipse(0.10 * s, 0.425 * s, 0.13 * s, 0.055 * s))
        late.append(circle(0.0, 0.485 * s, 0.05 * s, 24))
    return MotifShape(solids, cuts, late)


# ---------------------------------------------------------------------------------------------------------
# Bonhomme de neige
# ---------------------------------------------------------------------------------------------------------

def snowman_shape(h) -> MotifShape:
    """Bonhomme de neige de hauteur `h`, pied en (0, 0) : deux boules et un haut-de-forme ; yeux et boutons évidés
    quand il est assez grand."""
    s = h
    body = circle(0.0, 0.27 * s, 0.27 * s, 64)
    head = circle(0.0, 0.66 * s, 0.19 * s, 64)
    hat_brim = rect(-0.20 * s, 0.82 * s, 0.20 * s, 0.86 * s)
    hat_top = rect(-0.11 * s, 0.85 * s, 0.11 * s, 1.0 * s)
    cuts: List[Polygon] = []
    dot = 0.026 * s  # rayon d'un œil ou d'un bouton
    if 2 * dot >= MIN_DETAIL_MM:
        cuts += [circle(-0.07 * s, 0.69 * s, dot, 24), circle(0.07 * s, 0.69 * s, dot, 24),
                 circle(0.0, 0.34 * s, dot, 24), circle(0.0, 0.22 * s, dot, 24)]
    return MotifShape([body, head, hat_brim, hat_top], cuts)


# ---------------------------------------------------------------------------------------------------------
# Cadeau
# ---------------------------------------------------------------------------------------------------------

def gift_shape(h) -> MotifShape:
    """Paquet cadeau de hauteur `h`, pied en (0, 0) : boîte, couvercle, nœud à deux boucles ; fente du ruban dans
    la boîte et boucles évidées quand elles sont assez grandes."""
    s = h
    box = rect(-0.42 * s, 0.0, 0.42 * s, 0.57 * s)
    lid = rect(-0.46 * s, 0.56 * s, 0.46 * s, 0.72 * s)
    # Deux boucles écartées : un creux (~0,10 h) reste entre elles au-dessus du nœud, pour y loger la tige de la
    # suspente sans qu'elle recouvre les boucles. Le nœud les chevauche, elles sont soudées.
    loop_l = circle(-0.17 * s, 0.80 * s, 0.12 * s)
    loop_r = circle(0.17 * s, 0.80 * s, 0.12 * s)
    knot = circle(0.0, 0.76 * s, 0.075 * s)
    cuts: List[Polygon] = []
    if 0.07 * s >= MIN_DETAIL_MM:
        cuts.append(rect(-0.035 * s, 0.05 * s, 0.035 * s, 0.55 * s))
    if (0.12 - 0.05) * s >= MIN_DETAIL_MM:
        cuts += [circle(-0.17 * s, 0.80 * s, 0.05 * s), circle(0.17 * s, 0.80 * s, 0.05 * s)]
    return MotifShape([box, lid, loop_l, loop_r, knot], cuts)


# ---------------------------------------------------------------------------------------------------------
# Croissant de lune, houx, bougie, cloche
# ---------------------------------------------------------------------------------------------------------

def _arc(cx, cy, r, a0, a1, n=40):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def moon_shape(h) -> MotifShape:
    """Croissant de lune de hauteur `h`, ouvert vers la droite, pied en (0, 0). Les deux pointes sont
    émoussées (arrêtées avant le point de rencontre des cercles) pour ne pas casser."""
    big = h / 2.0
    inner, dx = 0.82 * big, 0.42 * big
    # Les deux cercles se coupent en x = (R² - r² + dx²) / (2 dx).
    x_cut = (big * big - inner * inner + dx * dx) / (2.0 * dx)
    y_cut = math.sqrt(max(big * big - x_cut * x_cut, 0.0))
    a_out = math.degrees(math.atan2(y_cut, x_cut))
    a_in = math.degrees(math.atan2(y_cut, x_cut - dx))
    outer_arc = _arc(0.0, big, big, a_out, 360.0 - a_out)        # grand arc, par la gauche
    # Le petit arc s'arrête 5° avant les pointes : elles sont émoussées au lieu de finir en lame de 0 mm.
    inner_arc = _arc(dx, big, inner, 360.0 - a_in + 5.0, a_in - 5.0)  # petit arc, retour par la gauche
    return MotifShape([outer_arc + inner_arc])


def _holly_leaf(length, width, lobes=3) -> Polygon:
    """Feuille de houx le long de +Y : base en (0, 0), pointe en (0, length), `lobes` pointes de chaque côté."""
    n = 36
    side = []
    for i in range(n + 1):
        t = i / n
        envelope = math.sin(math.pi * t) ** 0.75
        teeth = 0.62 + 0.38 * (1.0 - abs(math.sin(lobes * math.pi * t)))   # pointes vives, creux arrondis
        side.append((width / 2.0 * envelope * teeth, length * t))
    return [(-x, y) for x, y in side] + [(x, y) for x, y in reversed(side[1:-1])]


def holly_shape(h, style="Trio") -> MotifShape:
    """Houx de hauteur `h`, baies en bas : trois feuilles (« Trio », la centrale droite) ou deux (« Duo »)."""
    leaf_len, leaf_w = 0.82 * h, 0.34 * h
    leaves = []
    angles = (-42.0, 0.0, 42.0) if style != "Duo" else (-30.0, 30.0)
    for a in angles:
        scale = 1.0 if abs(a) < 1 else 0.82
        leaf = _holly_leaf(leaf_len * scale, leaf_w * scale)
        t = math.radians(a)
        leaves.append([(x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t) + 0.10 * h)
                       for x, y in leaf])
    r = 0.095 * h
    berries = [circle(-0.8 * r, 0.10 * h, r), circle(0.8 * r, 0.10 * h, r), circle(0.0, 0.10 * h + 1.1 * r, r)]
    shape = MotifShape(leaves + berries)
    # Le bas des baies est le point le plus bas : on remet le pied en y = 0.
    low = min(p[1] for poly in shape.solids for p in poly)
    return shape.transformed(0.0, 0.0, -low)


def candle_shape(h) -> MotifShape:
    """Bougie de hauteur `h`, pied en (0, 0) : soucoupe, corps, flamme en goutte soudée au corps ; la flamme est
    évidée quand elle est assez grande."""
    s = h
    body_w = max(0.22 * s, 2 * MIN_DETAIL_MM)
    dish_h = max(0.06 * s, MIN_DETAIL_MM)
    dish = rect(-0.18 * s, 0.0, 0.18 * s, dish_h)
    body = rect(-body_w / 2.0, dish_h - 0.5, body_w / 2.0, 0.68 * s)
    flame_r = 0.075 * s
    cy = 0.74 * s
    flame = [(0.0, 0.97 * s)]                                    # pointe
    for i in range(1, 24):                                       # rond de la goutte : du côté droit au côté gauche, par le bas
        a = math.radians(35.0 - 250.0 * i / 23)
        flame.append((flame_r * 1.15 * math.cos(a), cy + flame_r * math.sin(a)))
    cuts: List[Polygon] = []
    if (flame_r * 1.15 - 0.45 * flame_r) * 2 >= MIN_DETAIL_MM and flame_r * 0.9 >= MIN_DETAIL_MM:
        cuts.append(ellipse(0.0, cy + 0.12 * flame_r, 0.42 * flame_r, 0.55 * flame_r, 24))
    return MotifShape([dish, body, flame], cuts)


def _chaikin(points, iterations=2):
    for _ in range(iterations):
        out = [points[0]]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        out.append(points[-1])
        points = out
    return points


def bell_shape(h) -> MotifShape:
    """Cloche de hauteur `h`, pied (bas du battant) en (0, 0) : bouton, dôme évasé, rebord, battant."""
    s = h
    half = [(0.0, 0.88), (0.07, 0.86), (0.12, 0.80), (0.15, 0.68), (0.17, 0.54), (0.20, 0.40), (0.25, 0.26),
            (0.31, 0.17), (0.34, 0.14), (0.34, 0.10)]
    half = _chaikin([(x * s, (y * 0.9 + 0.05) * s) for x, y in half], 2)
    right = half + [(0.0, half[-1][1])]
    body = right + [(-x, y) for x, y in reversed(right[1:-1])]
    # Le bouton s'enfonce dans le haut du dôme (sommet à 0,842 h) : sans chevauchement il flotterait au-dessus.
    knob = circle(0.0, 0.875 * s, 0.055 * s, 24)
    clapper = circle(0.0, 0.07 * s, 0.075 * s, 32)
    # Une tige relie le battant à l'intérieur de la cloche : sans elle, il ne toucherait le rebord que d'un point.
    stem_w = max(MIN_DETAIL_MM, 0.06 * s)
    stem = rect(-stem_w / 2.0, 0.07 * s, stem_w / 2.0, 0.24 * s)
    return MotifShape([body, knob, clapper, stem])


def bulb_shape(h) -> MotifShape:
    """Ampoule de guirlande de hauteur `h`, la douille en haut (point d'accroche), pied de l'ampoule en y = 0."""
    s = h
    return MotifShape([circle(0.0, 0.42 * s, 0.34 * s, 40), rect(-0.13 * s, 0.66 * s, 0.13 * s, s)])


UPRIGHT_BUILDERS = {
    "Sapins": lambda h, style: tree_shape(h, style),
    "Père Noël": lambda h, style: santa_shape(h),
    "Bonhomme de neige": lambda h, style: snowman_shape(h),
    "Cadeaux": lambda h, style: gift_shape(h),
    "Lune": lambda h, style: moon_shape(h),
    "Houx": lambda h, style: holly_shape(h, style),
    "Bougie": lambda h, style: candle_shape(h),
    "Cloche": lambda h, style: bell_shape(h),
}
