"""Texte le long d'un tracé quelconque : position et rotation de chaque lettre (sans Qt).

Repère : mathématique, Y vers le haut, en mm. Le tracé est une suite de points (polyligne) ; l'appelant
l'obtient en aplatissant le contour d'un objet existant (cercle, ellipse, courbe, rectangle...).

Le texte se lit dans le sens du tracé, la ligne de base posée dessus, le haut des lettres à GAUCHE du sens de
marche. Pour un contour fermé orienté dans le sens horaire (voir `orient_path`), c'est donc du texte à
l'extérieur, lu dans le sens des aiguilles d'une montre. Inverser le sens (`reverse`) met le texte de l'autre
côté du trait.
"""
import math

CLOSE_TOL_MM = 0.02


def is_closed(points, tol=CLOSE_TOL_MM):
    """Vrai si le premier et le dernier point coïncident (contour fermé)."""
    return len(points) > 2 and math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= tol


def signed_area(points):
    """Aire signée (formule du lacet) : > 0 pour un contour anti-horaire en Y vers le haut."""
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _cumulative(points):
    cum = [0.0]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        cum.append(cum[-1] + math.hypot(x2 - x1, y2 - y1))
    return cum


def path_length(points):
    return _cumulative(points)[-1] if len(points) > 1 else 0.0


def orient_path(points):
    """Sens de lecture naturel : un contour fermé est mis dans le sens horaire, un tracé ouvert va de la
    gauche vers la droite (à largeur égale, du bas vers le haut). Renvoie une nouvelle liste."""
    pts = [tuple(p) for p in points]
    if len(pts) < 2:
        return pts
    if is_closed(pts):
        return pts[::-1] if signed_area(pts[:-1]) > 0 else pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    if x1 < x0 - 1e-9 or (abs(x1 - x0) <= 1e-9 and y1 < y0):
        return pts[::-1]
    return pts


SIDES = ("top", "bottom", "left", "right")
_SIDE_TOL_MM = 0.01


def side_center_fraction(points, side):
    """Fraction (0 à 1) de la longueur du tracé au point le plus haut / bas / à gauche / à droite
    (`side` : "top", "bottom", "left", "right"). Plusieurs sommets à égalité (côté plat) : le milieu de la
    série. Sert à poser le texte « en haut », « en bas »... d'un contour."""
    if side not in SIDES:
        raise ValueError(side)
    pts = [tuple(p) for p in points]
    if len(pts) < 2:
        return 0.5
    closed = is_closed(pts)
    cum = _cumulative(pts)
    total = cum[-1]
    if total <= 0:
        return 0.5
    n = len(pts) - 1 if closed else len(pts)
    axis = 1 if side in ("top", "bottom") else 0
    pick = max if side in ("top", "right") else min
    best = pick(p[axis] for p in pts[:n])
    spots = [cum[i] for i in range(n) if abs(pts[i][axis] - best) <= _SIDE_TOL_MM]
    if closed:
        # Série à cheval sur le départ du contour : on ramène les positions de la fin avant 0.
        if min(spots) < total / 4 and max(spots) > 3 * total / 4:
            spots = [x - total if x > total / 2 else x for x in spots]
        return ((min(spots) + max(spots)) / 2.0 / total) % 1.0
    return min(1.0, max(0.0, (min(spots) + max(spots)) / 2.0 / total))


def place_for_fraction(points, fraction, tol=0.002):
    """Nom du côté ("top"...) dont la fraction correspond à `fraction` (à `tol` près, circulaire si fermé),
    sinon None : c'est le choix « position libre »."""
    closed = is_closed([tuple(p) for p in points])
    for side in SIDES:
        d = abs(side_center_fraction(points, side) - fraction)
        if closed:
            d = min(d, 1.0 - d)
        if d <= tol:
            return side
    return None


def default_center_fraction(points, inside=False):
    """Fraction (0 à 1) de la longueur où centrer le texte par défaut : le point le plus haut d'un contour
    fermé (légende du haut d'une médaille), le milieu d'un tracé ouvert.

    `inside` (texte de l'autre côté du trait) : le point le plus BAS d'un contour fermé. Le haut des
    lettres est alors tourné vers le centre, donc le texte n'est à l'endroit qu'en bas (légende du bas
    d'une médaille) ; en haut il serait à l'envers."""
    if len(points) < 2 or not is_closed(points):
        return 0.5
    return side_center_fraction(points, "bottom" if inside else "top")


def _locate(points, cum, closed, s):
    """Point du tracé à l'abscisse curviligne `s` : (x, y). Un tracé fermé boucle ; un tracé ouvert se
    prolonge en ligne droite au-delà de ses extrémités."""
    total = cum[-1]
    if closed:
        s %= total
    n = len(points)
    if s <= 0:
        i = 0
    elif s >= total:
        i = n - 2
    else:
        lo, hi = 0, n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        i = lo
    (x1, y1), (x2, y2) = points[i], points[i + 1]
    seg = cum[i + 1] - cum[i]
    if seg <= 1e-12:
        return x1, y1
    t = (s - cum[i]) / seg      # < 0 ou > 1 hors du tracé ouvert : prolongement
    return x1 + (x2 - x1) * t, y1 + (y2 - y1) * t


def path_placements(advances_mm, points, center_fraction=None, spacing_mm=0.0, reverse=False, gap_mm=0.0):
    """Pour chaque lettre : (x, y, rotation_deg), comme `text_on_arc.arc_placements`.

    (x, y) est le milieu de la ligne de base de la lettre, posé sur le tracé ; rotation_deg la rotation à
    appliquer à la lettre (dessinée de gauche à droite, ligne de base sur l'axe X, centrée sur son origine).
    Le texte entier est centré sur `center_fraction` de la longueur du tracé (`default_center_fraction` si
    None). `reverse` lit le tracé à l'envers ; `gap_mm` décale les lettres du tracé, vers le haut des lettres
    si positif."""
    pts = [tuple(p) for p in points]
    if len(pts) < 2:
        raise ValueError("path")
    closed = is_closed(pts)
    if center_fraction is None:
        center_fraction = default_center_fraction(pts)
    if reverse:
        pts = pts[::-1]
        center_fraction = 1.0 - center_fraction
    cum = _cumulative(pts)
    total = cum[-1]
    if total <= 1e-9:
        raise ValueError("path")

    text_len = (float(sum(advances_mm)) + spacing_mm * (len(advances_mm) - 1)) if advances_mm else 0.0
    placements = []
    cursor = 0.0
    for adv in advances_mm:
        s = center_fraction * total + cursor + adv / 2.0 - text_len / 2.0
        half = max(adv / 2.0, 1e-3)
        # Direction : corde sous la largeur de la lettre, plus stable qu'une tangente sur un tracé aplati.
        xa, ya = _locate(pts, cum, closed, s - half)
        xb, yb = _locate(pts, cum, closed, s + half)
        x, y = _locate(pts, cum, closed, s)
        angle = math.atan2(yb - ya, xb - xa)
        if gap_mm:
            x += -math.sin(angle) * gap_mm
            y += math.cos(angle) * gap_mm
        placements.append((x, y, math.degrees(angle)))
        cursor += adv + spacing_mm
    return placements


def relative_points(points, origin):
    """Points décalés de `origin` (x, y) : le tracé est mémorisé relativement à l'objet texte."""
    ox, oy = origin
    return [(x - ox, y - oy) for x, y in points]


def scaled_points(points, factor_x, factor_y):
    return [(x * factor_x, y * factor_y) for x, y in points]
