"""Perforation (découpe en pointillé), sans Qt.

Un calque en mode Perforation coupe son tracé par traits séparés de vides : les traits de `dash` mm, les
vides de `gap` mm. La matière reste tenue par les vides : ligne de pliage, ligne à déchirer, pièce qui
doit rester attachée.

Le motif est ajusté à la longueur du tracé pour finir juste :
  * tracé fermé : un nombre entier de périodes (trait + vide), donc le dernier vide rejoint le premier
    trait sans trait coupé en deux ni vide doublé ;
  * tracé ouvert : il commence et finit par un trait, avec un nombre entier de traits.
Les longueurs demandées sont mises à l'échelle (au plus d'une demi-période) pour que le motif tienne ; leur
rapport trait / vide est conservé. Un tracé plus court qu'un trait est coupé en entier.
"""
import math

from laser_studio.vector.tabs import closed_points, is_closed

_EPS = 1e-9


def _cumulative(pts):
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
    return cum


def _slice(pts, cum, a, b):
    """Points du tracé entre les abscisses curvilignes a < b."""
    out = []
    for i in range(len(pts) - 1):
        s0, s1 = cum[i], cum[i + 1]
        if s1 <= a or s0 >= b or s1 - s0 <= _EPS:
            continue
        lo, hi = max(a, s0), min(b, s1)
        t_lo, t_hi = (lo - s0) / (s1 - s0), (hi - s0) / (s1 - s0)
        p_lo = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t_lo, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t_lo)
        p_hi = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t_hi, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t_hi)
        if not out:
            out.append(p_lo)
        out.append(p_hi)
    return out


def pattern(length, dash, gap, closed):
    """(nombre de traits, trait ajusté, vide ajusté) d'un tracé de `length` mm ; (1, length, 0.0) quand le
    tracé tient dans un seul trait (ou si les réglages n'ont pas de sens)."""
    if length <= 0 or dash <= 0 or gap <= 0:
        return 1, length, 0.0
    if closed:
        n = max(1, int(length / (dash + gap) + 0.5))
        scale = length / (n * (dash + gap))
    else:
        if length <= dash:
            return 1, length, 0.0
        n = max(1, int((length + gap) / (dash + gap) + 0.5))
        if n == 1:
            return 1, length, 0.0
        scale = length / (n * dash + (n - 1) * gap)
    return n, dash * scale, gap * scale


def dashes(poly, dash, gap):
    """Traits à couper d'un tracé perforé : liste de tracés (listes de points), dans le sens du tracé.
    Un tracé qui tient dans un seul trait, ou des réglages nuls, rendent `[poly]` inchangé."""
    if len(poly) < 2 or dash <= 0 or gap <= 0:
        return [poly]
    closed = is_closed(poly)
    pts = closed_points(poly) if closed else [tuple(p) for p in poly]
    cum = _cumulative(pts)
    length = cum[-1]
    n, d, g = pattern(length, dash, gap, closed)
    if n == 1 and g == 0.0 and not closed:
        return [poly]
    out = []
    for k in range(n):
        start = k * (d + g)
        run = _slice(pts, cum, start, min(start + d, length))
        if len(run) >= 2:
            out.append(run)
    return out or [poly]


def perforate(polygons, dash, gap):
    """Tous les tracés de `polygons` en pointillé : (nouveaux tracés, nombre de traits)."""
    result = []
    for poly in polygons:
        result.extend(dashes(poly, dash, gap))
    return result, len(result)
