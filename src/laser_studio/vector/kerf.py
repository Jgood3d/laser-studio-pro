"""Compensation du kerf (largeur de la saignée du laser), sans Qt.

Le faisceau enlève une bande de matière large de `kerf` mm, centrée sur le tracé : une pièce découpée sur
son contour exact est trop petite de kerf/2 sur chaque bord, un trou trop grand. Pour obtenir les cotes du
dessin, le tracé est décalé de kerf/2 :
  * contour extérieur (une pièce) : vers l'extérieur, la pièce garde ses cotes ;
  * contour intérieur (un trou, une lettre « o ») : vers l'intérieur du trou, le trou garde ses cotes.
Un contour est « extérieur » quand un nombre pair de contours le contiennent (même règle que les ponts de
maintien et l'ordre de coupe : `order.nesting_depths`).

Seuls les contours FERMÉS sont décalés : un tracé ouvert (ligne, fente) se coupe sur son axe.

Le décalage déplace chaque côté de kerf/2 le long de sa normale et rejoint les côtés voisins par leur
intersection (angle vif, « onglet »). Un angle très aigu est biseauté au-delà de MITER_LIMIT fois le
décalage, pour ne pas lancer une pointe. Le résultat est vérifié (même sens de parcours, aire dans le bon
sens, pas de boucle) ; un contour pour lequel le décalage n'a plus de sens (trou plus petit que le kerf,
détail très fin) est rendu inchangé et compté à part, pour que l'appelant le signale.
"""
import math

import numpy as np

from laser_studio.vector.order import nesting_depths
from laser_studio.vector.tabs import closed_points, is_closed

# Longueur maximale d'un coude, en multiples du décalage : au-delà (angle très aigu), le sommet est biseauté.
MITER_LIMIT = 2.0

# Au-delà de ce nombre de points, la recherche de boucles (quadratique) est sautée : on ne vérifie alors que
# le sens et l'aire.
MAX_POINTS_FOR_LOOP_CHECK = 1500

_EPS = 1e-9


def signed_area(pts):
    """Aire signée (positive si le contour tourne dans le sens trigonométrique) ; `pts` sans point répété."""
    n = len(pts)
    s = 0.0
    for i in range(n):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def _has_loop(pts):
    """True si deux côtés non voisins du contour fermé `pts` se croisent."""
    n = len(pts)
    if n < 4:
        return False
    p = np.asarray(pts, dtype=float)
    q = np.roll(p, -1, axis=0)                       # fin de chaque côté
    ax, ay = p[:, 0][:, None], p[:, 1][:, None]
    bx, by = q[:, 0][:, None], q[:, 1][:, None]
    cx, cy = p[:, 0][None, :], p[:, 1][None, :]
    dx, dy = q[:, 0][None, :], q[:, 1][None, :]
    d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
    d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
    d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
    crossing = (d1 * d2 < 0) & (d3 * d4 < 0)
    idx = np.arange(n)
    gap = np.abs(idx[:, None] - idx[None, :])
    neighbours = (gap <= 1) | (gap == n - 1)         # côtés qui se touchent par un sommet
    return bool(np.any(crossing & ~neighbours))


def offset_polygon(poly, distance):
    """Contour fermé `poly` décalé de `distance` mm : vers l'extérieur si positif, vers l'intérieur si
    négatif. Renvoie le nouveau contour fermé (premier point répété à la fin), ou None si le décalage n'est
    pas possible (contour dégénéré, détail plus fin que le décalage, boucle)."""
    if len(poly) < 3:
        return None
    pts = closed_points(poly)[:-1]
    n = len(pts)
    if n < 3:
        return None
    area = signed_area(pts)
    if abs(area) < _EPS:
        return None
    orient = 1.0 if area > 0 else -1.0

    # Normale sortante unitaire de chaque côté i (de pts[i] à pts[i + 1]).
    normals = []
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        length = math.hypot(x1 - x0, y1 - y0)
        if length < _EPS:
            return None
        normals.append((orient * (y1 - y0) / length, -orient * (x1 - x0) / length))

    out = []
    first_of, last_of = [], []                       # points de `out` créés pour chaque sommet
    for i in range(n):
        first_of.append(len(out))
        n0 = normals[i - 1]                          # côté qui arrive au sommet
        n1 = normals[i]                              # côté qui en repart
        x, y = pts[i]
        dot = n0[0] * n1[0] + n0[1] * n1[1]
        x_prev, y_prev = pts[i - 1]
        x_next, y_next = pts[(i + 1) % n]
        cross = (x - x_prev) * (y_next - y) - (y - y_prev) * (x_next - x)
        convex = cross * orient > _EPS
        opens_up = convex == (distance > 0)          # les côtés décalés s'écartent : il faut les relier
        if 1.0 + dot < 1e-6:                         # demi-tour : pointe de largeur nulle
            return None
        miter = math.sqrt(2.0 / (1.0 + dot))         # longueur du coude / décalage
        if opens_up and miter > MITER_LIMIT:
            out.append((x + n0[0] * distance, y + n0[1] * distance))
            out.append((x + n1[0] * distance, y + n1[1] * distance))
        else:
            k = distance / (1.0 + dot)
            out.append((x + (n0[0] + n1[0]) * k, y + (n0[1] + n1[1]) * k))
        last_of.append(len(out) - 1)

    # Un côté décalé doit garder le sens de son côté d'origine : s'il est retourné, le détail s'est effondré
    # (carré plus petit que le décalage, mur plus fin que lui) et le résultat serait une figure inversée.
    for i in range(n):
        sx, sy = out[last_of[i]]
        ex, ey = out[first_of[(i + 1) % n]]
        ox, oy = pts[i]
        nx, ny = pts[(i + 1) % n]
        if (ex - sx) * (nx - ox) + (ey - sy) * (ny - oy) <= _EPS:
            return None

    new_area = signed_area(out)
    # Même sens de parcours ; l'aire grandit en grossissant et diminue en rétrécissant.
    if new_area * orient <= _EPS:
        return None
    if (distance > 0 and abs(new_area) <= abs(area)) or (distance < 0 and abs(new_area) >= abs(area)):
        return None
    if len(out) <= MAX_POINTS_FOR_LOOP_CHECK and _has_loop(out):
        return None
    return out + [out[0]]


def compensate_kerf(polygons, kerf_mm):
    """Décale les contours fermés de `polygons` de kerf/2 (voir le module).

    Renvoie (nouveaux tracés dans le même ordre, nombre de contours décalés, nombre de contours laissés
    inchangés parce que le décalage n'avait plus de sens). Les tracés ouverts ne changent pas."""
    if kerf_mm <= 0:
        return list(polygons), 0, 0
    half = kerf_mm / 2.0
    closed_idx = [i for i, poly in enumerate(polygons) if is_closed(poly)]
    depths = nesting_depths([polygons[i] for i in closed_idx])
    result = list(polygons)
    done = failed = 0
    for i, depth in zip(closed_idx, depths):
        shifted = offset_polygon(polygons[i], half if depth % 2 == 0 else -half)
        if shifted is None:
            failed += 1
        else:
            result[i] = shifted
            done += 1
    return result, done, failed
