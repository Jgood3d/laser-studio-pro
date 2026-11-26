"""Arcs d'entrée et de sortie des découpes, sans Qt.

Le laser qui s'allume sur le contour même laisse une marque : un point plus profond (le perçage), parfois
une brûlure ou un décalage là où la tête démarre et s'arrête. Pour que cette marque tombe dans la chute et
non sur le bord de la pièce, le laser s'allume à côté du contour, sur la chute, et rejoint le point de
départ par un quart de cercle TANGENT au tracé (entrée en arc) ; une fois le contour refermé, il repart de
la même façon vers la chute (sortie en arc) avant de s'éteindre.

La chute est :
  * à l'extérieur d'un contour extérieur (une pièce) ;
  * à l'intérieur d'un trou.
Même règle que pour le kerf et les ponts : profondeur d'imbrication paire ou impaire (`order.nesting_depths`).

Un arc n'est posé que s'il a la place : il ne doit ni croiser un contour, ni toucher la matière d'une pièce
voisine. Sinon son rayon est réduit (moitié, quart), puis le contour est coupé sans arc et compté à part,
pour que l'appelant le signale. Un tracé ouvert (ligne, fente) n'a pas de côté « chute » : il est laissé tel
quel.
"""
import math

import numpy as np

from laser_studio.vector.kerf import signed_area
from laser_studio.vector.order import nesting_depths
from laser_studio.vector.tabs import closed_points, is_closed

# Rayons d'essai, en fractions du rayon demandé, et plus petit rayon posé (mm) : en dessous, l'arc n'a plus
# d'intérêt et le contour est coupé sans arc.
RADIUS_FRACTIONS = (1.0, 0.5, 0.25)
MIN_RADIUS_MM = 0.2

# Points d'un quart de cercle (sans compter le point de départ du contour).
ARC_STEPS = 6

_EPS = 1e-9


def _edges(closed_polys):
    """Côtés (x0, y0, x1, y1) de tous les contours fermés, en tableaux numpy ; None s'il n'y en a pas."""
    chunks = []
    for poly in closed_polys:
        pts = np.asarray(closed_points(poly), dtype=float)
        if len(pts) >= 2:
            chunks.append(np.hstack([pts[:-1], pts[1:]]))
    if not chunks:
        return None
    e = np.vstack(chunks)
    return e[:, 0], e[:, 1], e[:, 2], e[:, 3]


def _on_material(x, y, edges):
    """True si (x, y) est sur de la matière : contenu dans un nombre impair de contours fermés (règle
    pair-impair, comme le remplissage). Lancer de rayon vers +x sur l'ensemble des côtés."""
    if edges is None:
        return False
    x0, y0, x1, y1 = edges
    straddles = (y0 > y) != (y1 > y)
    dy = np.where(straddles, y1 - y0, 1.0)
    x_cross = x0 + (y - y0) * (x1 - x0) / dy
    return int(np.count_nonzero(straddles & (x < x_cross))) % 2 == 1


def _crosses(points, edges):
    """True si la ligne brisée `points` coupe franchement un des côtés (un simple contact en un point,
    comme l'arrivée de l'arc sur le contour, n'est pas un croisement)."""
    if edges is None:
        return False
    ex0, ey0, ex1, ey1 = edges
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        d1 = (bx - ax) * (ey0 - ay) - (by - ay) * (ex0 - ax)
        d2 = (bx - ax) * (ey1 - ay) - (by - ay) * (ex1 - ax)
        d3 = (ex1 - ex0) * (ay - ey0) - (ey1 - ey0) * (ax - ex0)
        d4 = (ex1 - ex0) * (by - ey0) - (ey1 - ey0) * (bx - ex0)
        if np.any((d1 * d2 < 0) & (d3 * d4 < 0)):
            return True
    return False


def _arc(p0, tangent, waste_dir, radius, theta_from, theta_to):
    """Points du quart de cercle tangent à `tangent` en `p0`, du côté `waste_dir` (vecteurs unitaires),
    de l'angle theta_from à theta_to. Le cercle est centré à `radius` de `p0`, vers la chute ; à
    theta = 0 on est en `p0` et on avance dans le sens `tangent`."""
    cx, cy = p0[0] + radius * waste_dir[0], p0[1] + radius * waste_dir[1]
    out = []
    for k in range(ARC_STEPS + 1):
        theta = theta_from + (theta_to - theta_from) * k / ARC_STEPS
        c, s = math.cos(theta), math.sin(theta)
        out.append((cx - c * radius * waste_dir[0] + s * radius * tangent[0],
                    cy - c * radius * waste_dir[1] + s * radius * tangent[1]))
    return out


def _restart_mid_longest_edge(pts):
    """Le même contour fermé, reparti du milieu de son plus long côté : un départ au milieu d'un côté droit
    laisse la place à l'arc des deux côtés (au coin d'un trou, l'arc d'entrée sortirait du trou)."""
    n = len(pts) - 1
    i = max(range(n), key=lambda k: math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]))
    mid = ((pts[i][0] + pts[i + 1][0]) / 2.0, (pts[i][1] + pts[i + 1][1]) / 2.0)
    body = [pts[(i + 1 + k) % n] for k in range(n)]          # de pts[i + 1] à pts[i], en faisant le tour
    return [mid] + body + [mid]


def _try_lead(pts, depth, radius, edges):
    """Arc d'entrée + contour + arc de sortie pour le contour fermé `pts` tel qu'il est parti, ou None."""
    orient = 1.0 if signed_area(pts[:-1]) > 0 else -1.0
    p0 = pts[0]
    dx, dy = pts[1][0] - p0[0], pts[1][1] - p0[1]
    length = math.hypot(dx, dy)
    if length < _EPS:
        return None
    tangent = (dx / length, dy / length)
    # Normale gauche du sens de parcours ; la chute est à droite d'un contour antihoraire extérieur.
    left = (-tangent[1], tangent[0])
    waste_side = -orient if depth % 2 == 0 else orient
    waste_dir = (waste_side * left[0], waste_side * left[1])

    for fraction in RADIUS_FRACTIONS:
        r = radius * fraction
        if r < MIN_RADIUS_MM:
            break
        lead_in = _arc(p0, tangent, waste_dir, r, -math.pi / 2, 0.0)
        lead_out = _arc(p0, tangent, waste_dir, r, 0.0, math.pi / 2)
        free = all(not _on_material(x, y, edges) for x, y in lead_in[:-1] + lead_out[1:])
        if free and not _crosses(lead_in, edges) and not _crosses(lead_out, edges):
            return lead_in[:-1] + pts + lead_out[1:]
    return None


def lead_path(poly, depth, radius, edges):
    """Contour fermé `poly` précédé de son arc d'entrée et suivi de son arc de sortie, ou None si l'arc n'a
    pas la place (même réduit). Le contour garde son point de départ ; s'il n'y a pas la place là (coin d'un
    trou, départ trop près d'une pièce voisine), il est repris du milieu de son plus long côté. `depth` :
    profondeur d'imbrication du contour ; `edges` : côtés de tous les contours du calque (voir `_edges`)."""
    pts = closed_points(poly)
    if len(pts) < 4:
        return None
    led = _try_lead(pts, depth, radius, edges)
    if led is None:
        led = _try_lead(_restart_mid_longest_edge(pts), depth, radius, edges)
    return led


def add_leads(paths, reference, radius, skip=None):
    """Ajoute l'arc d'entrée et de sortie aux contours fermés de `paths`.

    paths     : tracés à couper, dans l'ordre (liste de listes de points).
    reference : les contours du calque avant tout découpage en tronçons : c'est eux qui définissent la
                matière et la profondeur d'imbrication de chaque contour. Un tracé de `paths` n'est traité
                que s'il est l'un d'eux (même objet), les autres (tronçons de ponts) restent tels quels.
    radius    : rayon demandé (mm).
    skip      : indices de `paths` à laisser sans arc.

    Renvoie (nouveaux tracés dans le même ordre, nombre de contours munis d'arcs, nombre de contours sans
    arc faute de place)."""
    if radius <= 0:
        return list(paths), 0, 0
    closed_ref = [p for p in reference if is_closed(p)]
    depth_of = {id(p): d for p, d in zip(closed_ref, nesting_depths(closed_ref))}
    edges = _edges(closed_ref)
    result = list(paths)
    done = skipped = 0
    for i, path in enumerate(paths):
        if (skip and skip[i]) or id(path) not in depth_of:
            continue
        led = lead_path(path, depth_of[id(path)], radius, edges)
        if led is None:
            skipped += 1
        else:
            result[i] = led
            done += 1
    return result, done, skipped
