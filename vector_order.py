"""Ordre d'exécution sûr des découpes (sans Qt) : graver avant de découper, et couper l'intérieur
avant l'extérieur.

Une pièce découpée peut bouger ou basculer dès que son contour extérieur est coupé : tout ce qui doit
encore être gravé ou découpé À L'INTÉRIEUR (détails, trous) doit donc l'être avant. Deux règles :
  1. les calques de gravure et de marquage passent avant les calques de découpe ;
  2. dans un calque de découpe, un contour contenu dans un autre est coupé avant lui (les plus
     imbriqués d'abord).
"""
CUT_MODE = "Découpe"


def polygon_area(poly):
    """Aire absolue (formule du lacet) ; polygone ouvert ou fermé indifféremment."""
    n = len(poly)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def point_in_polygon(x, y, poly):
    """Lancer de rayon (règle pair-impair)."""
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        if (y0 > y) != (y1 > y):
            if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
    return inside


def _bbox(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _samples(poly, count=6):
    """Quelques points répartis sur le contour (plus fiable qu'un seul sommet)."""
    n = len(poly)
    if n <= count:
        return list(poly)
    return [poly[(i * n) // count] for i in range(count)]


def nesting_depths(polygons, eps=1e-9):
    """Pour chaque polygone, le nombre d'AUTRES polygones qui le contiennent.

    Un polygone en contient un autre si son aire est strictement plus grande, si son rectangle englobant
    contient celui de l'autre et si tous les points d'échantillon de l'autre sont à l'intérieur. Les
    tracés de moins de 3 points (simples lignes) ne contiennent rien."""
    n = len(polygons)
    boxes = [_bbox(p) if len(p) >= 1 else (0, 0, 0, 0) for p in polygons]
    areas = [polygon_area(p) for p in polygons]
    samples = [_samples(p) if len(p) >= 1 else [] for p in polygons]
    depths = [0] * n
    for i in range(n):
        if not samples[i]:
            continue
        bi = boxes[i]
        for j in range(n):
            if i == j or len(polygons[j]) < 3 or areas[j] <= areas[i] * (1 + eps) + eps:
                continue
            bj = boxes[j]
            if bi[0] < bj[0] - eps or bi[1] < bj[1] - eps or bi[2] > bj[2] + eps or bi[3] > bj[3] + eps:
                continue
            if all(point_in_polygon(x, y, polygons[j]) for x, y in samples[i]):
                depths[i] += 1
    return depths


def order_polygons_inner_first(polygons):
    """Nouvelle liste : les contours les plus imbriqués d'abord. À profondeur égale, l'ordre d'origine."""
    depths = nesting_depths(polygons)
    order = sorted(range(len(polygons)), key=lambda i: (-depths[i], i))
    return [polygons[i] for i in order]


def order_layers_for_cutting(items):
    """items : [(id, données)] où données["layer"]["mode"] est le mode du calque.
    Renvoie les calques de gravure / marquage d'abord, puis les calques de découpe, chaque groupe gardant
    l'ordre choisi par l'utilisateur."""
    non_cut = [it for it in items if it[1]["layer"]["mode"] != CUT_MODE]
    cut = [it for it in items if it[1]["layer"]["mode"] == CUT_MODE]
    return non_cut + cut
