"""Ponts de maintien (micro-joints) des découpes, sans Qt.

Un pont est un court tronçon du contour que le laser ne coupe pas : la pièce reste attachée à la plaque
jusqu'à la fin du job, puis se détache d'un geste (un coup de cutter ou de pince). Sans pont, une pièce
détachée peut bouger, basculer ou tomber dans le nid d'abeille, et le laser qui passe ensuite la brûle ou
la déplace.

Règles :
  * seuls les contours FERMÉS sont concernés (un tracé ouvert n'enferme aucune pièce) ;
  * `count` ponts, répartis à égale distance le long du contour ; la largeur `width` (mm) se mesure le
    long du tracé ;
  * un contour trop court pour porter ses ponts en garde moins (voir `effective_count`), voire aucun : on
    préfère couper complètement une petite pièce plutôt que de la laisser tenir par un pont plus large que
    ce qui reste coupé ;
  * le résultat est la liste des tronçons À COUPER (les ponts en sont exclus).
"""
import math

# Longueur minimale de coupe (en nombre de largeurs de pont) entre deux ponts : en dessous, les ponts se
# touchent presque et la pièce n'est plus vraiment découpée.
MIN_CUT_RUN_FACTOR = 2.0

# Écart (mm) sous lequel le dernier point d'un tracé est confondu avec le premier.
CLOSED_TOLERANCE_MM = 0.01


def is_closed(poly, tolerance=CLOSED_TOLERANCE_MM):
    """True si le tracé revient à son point de départ (au plus `tolerance` mm d'écart)."""
    if len(poly) < 3:
        return False
    return math.hypot(poly[0][0] - poly[-1][0], poly[0][1] - poly[-1][1]) <= tolerance


def closed_points(poly):
    """Points du contour fermé, premier point répété à la fin, sans doublon consécutif."""
    pts = [tuple(poly[0])]
    for p in poly[1:]:
        if math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-9:
            pts.append(tuple(p))
    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 1e-9:
        pts.append(pts[0])
    return pts


def perimeter(poly):
    """Longueur (mm) du contour fermé `poly`."""
    pts = closed_points(poly)
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def effective_count(total_length, count, width):
    """Nombre de ponts réellement posés sur un contour de longueur `total_length`.

    Chaque tronçon coupé entre deux ponts doit faire au moins MIN_CUT_RUN_FACTOR fois la largeur d'un
    pont. Renvoie 0 quand même un seul pont ne respecte pas cette règle (petite pièce) ou quand les
    réglages n'ont pas de sens (nombre ou largeur nuls)."""
    if count <= 0 or width <= 0 or total_length <= 0:
        return 0
    # N ponts : N tronçons coupés de (total_length / N - width) chacun.
    n = int(count)
    while n >= 1 and total_length / n - width < MIN_CUT_RUN_FACTOR * width:
        n -= 1
    return max(n, 0)


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _slice(pts2, cum2, a, b):
    """Points du tracé entre les abscisses curvilignes a < b (tracé « doublé » : le contour deux fois de
    suite, pour pouvoir passer par le point de départ sans cas particulier)."""
    out = []
    n = len(pts2)
    for i in range(n - 1):
        s0, s1 = cum2[i], cum2[i + 1]
        if s1 <= a or s0 >= b or s1 - s0 <= 1e-12:
            continue
        lo, hi = max(a, s0), min(b, s1)
        p_lo = _lerp(pts2[i], pts2[i + 1], (lo - s0) / (s1 - s0))
        p_hi = _lerp(pts2[i], pts2[i + 1], (hi - s0) / (s1 - s0))
        if not out:
            out.append(p_lo)
        out.append(p_hi)
    return out


def cut_runs(poly, count, width, offset_fraction=0.5):
    """Tronçons À COUPER d'un contour fermé auquel on pose `count` ponts de `width` mm.

    Renvoie une liste de tracés (liste de points (x, y)), dans le sens du contour. Si aucun pont ne peut
    être posé (tracé ouvert, contour trop court, réglages nuls), renvoie `[poly]` : le tracé d'origine,
    inchangé.

    offset_fraction : place le centre du premier pont à cette fraction de l'écart entre deux ponts (0,5 :
    ponts centrés entre le point de départ et le suivant, donc jamais sur le point de départ du tracé)."""
    if not is_closed(poly):
        return [poly]
    pts = closed_points(poly)
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
    total = cum[-1]
    n = effective_count(total, count, width)
    if n == 0:
        return [poly]

    # Le contour deux fois de suite : un tronçon qui passe par le point de départ n'est plus un cas à part.
    pts2 = pts[:-1] + pts
    cum2 = cum[:-1] + [c + total for c in cum]
    pitch = total / n
    runs = []
    for k in range(n):
        centre = (k + offset_fraction) * pitch
        start = centre + width / 2.0            # fin du pont k
        end = centre + pitch - width / 2.0      # début du pont k + 1
        run = _slice(pts2, cum2, start, end)
        if len(run) >= 2:
            runs.append(run)
    return runs or [poly]


def tab_positions(poly, count, width, offset_fraction=0.5):
    """Centres (x, y) des ponts posés sur `poly` (pour un aperçu ou un test) ; liste vide si aucun."""
    if not is_closed(poly):
        return []
    pts = closed_points(poly)
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
    total = cum[-1]
    n = effective_count(total, count, width)
    if n == 0:
        return []
    pts2 = pts[:-1] + pts
    cum2 = cum[:-1] + [c + total for c in cum]
    out = []
    for k in range(n):
        s = ((k + offset_fraction) * total / n)
        for i in range(len(pts2) - 1):
            if cum2[i] <= s <= cum2[i + 1] and cum2[i + 1] - cum2[i] > 1e-12:
                out.append(_lerp(pts2[i], pts2[i + 1], (s - cum2[i]) / (cum2[i + 1] - cum2[i])))
                break
    return out
