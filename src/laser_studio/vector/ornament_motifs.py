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
            if self.contains(0.0, y):
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

def santa_shape(h) -> MotifShape:
    """Tête de Père Noël de hauteur `h`, pied (bas de la barbe) en (0, 0) : bonnet à pompon, bandeau, barbe, visage
    évidé avec moustache et nez. Sous ~17 mm de haut, le visage serait trop fin : il reste une silhouette pleine."""
    s = h
    hat = [(-0.30 * s, 0.62 * s), (0.30 * s, 0.62 * s), (0.20 * s, 0.80 * s), (0.08 * s, 0.92 * s),
           (0.0, 0.93 * s), (-0.08 * s, 0.92 * s), (-0.20 * s, 0.80 * s)]
    pompom = circle(0.0, 0.95 * s, 0.075 * s)
    brim = rect(-0.34 * s, 0.56 * s, 0.34 * s, 0.66 * s)
    beard = [(-0.34 * s, 0.60 * s), (-0.36 * s, 0.45 * s), (-0.33 * s, 0.30 * s), (-0.24 * s, 0.14 * s),
             (-0.12 * s, 0.04 * s), (0.0, 0.0), (0.12 * s, 0.04 * s), (0.24 * s, 0.14 * s),
             (0.33 * s, 0.30 * s), (0.36 * s, 0.45 * s), (0.34 * s, 0.60 * s)]
    solids = [hat, pompom, brim, beard]
    cuts: List[Polygon] = []
    late: List[Polygon] = []
    if 0.09 * s >= MIN_DETAIL_MM and 0.07 * s >= MIN_DETAIL_MM:
        cuts.append(ellipse(0.0, 0.50 * s, 0.20 * s, 0.09 * s))
        late.append(ellipse(0.0, 0.43 * s, 0.17 * s, 0.05 * s))   # moustache, soudée à la barbe sous le visage
        late.append(circle(0.0, 0.50 * s, 0.05 * s))              # nez, posé sur la moustache
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
    loop_l = circle(-0.13 * s, 0.80 * s, 0.12 * s)
    loop_r = circle(0.13 * s, 0.80 * s, 0.12 * s)
    knot = circle(0.0, 0.76 * s, 0.06 * s)
    cuts: List[Polygon] = []
    if 0.07 * s >= MIN_DETAIL_MM:
        cuts.append(rect(-0.035 * s, 0.05 * s, 0.035 * s, 0.55 * s))
    if (0.12 - 0.05) * s >= MIN_DETAIL_MM:
        cuts += [circle(-0.13 * s, 0.80 * s, 0.05 * s), circle(0.13 * s, 0.80 * s, 0.05 * s)]
    return MotifShape([box, lid, loop_l, loop_r, knot], cuts)


UPRIGHT_BUILDERS = {
    "Sapins": lambda h, style: tree_shape(h, style),
    "Père Noël": lambda h, style: santa_shape(h),
    "Bonhomme de neige": lambda h, style: snowman_shape(h),
    "Cadeaux": lambda h, style: gift_shape(h),
}
