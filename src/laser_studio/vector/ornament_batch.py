"""Boules de Noël en série : logique pure (sans Qt), testable seule.

Une ligne de la liste = une boule. Chaque boule est calculée séparément (`build_ornament_parts`), puis les
boules sont rangées en grille (4 par rangée au maximum) avec un petit écart. Les décalages sont calculés d'après
la boîte englobante réelle des contours de découpe, donc quelle que soit l'origine des coordonnées de la boule.
"""

MAX_BALLS = 100
GAP_MM = 5.0
MAX_COLS = 4
SHEET_MARGIN_MM = 10.0   # marge entre le bord du matériau et les boules (les boules démarrent à 10 mm)


def parse_names(text):
    """Une ligne = une boule. Lignes vides ignorées, espaces de début / fin retirés, 100 boules au maximum."""
    names = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return names[:MAX_BALLS]


def contours_bounds(contours):
    """(xmin, ymin, xmax, ymax) d'une liste de contours [(x, y), ...] ; None si elle est vide."""
    points = [pt for contour in contours for pt in contour]
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def columns_for_width(n, cell_w, max_width, gap=GAP_MM, default=MAX_COLS):
    """Nombre de colonnes qui tiennent dans `max_width` (au moins 1, au plus `n`). Sans largeur connue : `default`."""
    if not max_width or max_width <= 0 or cell_w <= 0:
        return max(1, min(default, n))
    fit = int((max_width + gap) // (cell_w + gap))
    return max(1, min(fit, n))


def grid_offsets(boxes, gap=GAP_MM, max_cols=MAX_COLS):
    """Décalage (dx, dy) à appliquer à chaque boule pour la ranger en grille, coin bas-gauche de la grille en
    (0, 0), lecture de gauche à droite, rangées vers le haut. `boxes` : boîtes englobantes (xmin, ymin, xmax, ymax).
    Renvoie (décalages, (largeur, hauteur) de l'ensemble)."""
    n = len(boxes)
    if n == 0:
        return [], (0.0, 0.0)
    cols = max(1, min(int(max_cols), n))
    rows = (n + cols - 1) // cols
    col_w = [0.0] * cols
    row_h = [0.0] * rows
    for i, b in enumerate(boxes):
        r, c = divmod(i, cols)
        col_w[c] = max(col_w[c], b[2] - b[0])
        row_h[r] = max(row_h[r], b[3] - b[1])
    xs = [0.0]
    for c in range(cols - 1):
        xs.append(xs[-1] + col_w[c] + gap)
    ys = [0.0]
    for r in range(rows - 1):
        ys.append(ys[-1] + row_h[r] + gap)
    offsets = []
    for i, b in enumerate(boxes):
        r, c = divmod(i, cols)
        offsets.append((xs[c] - b[0], ys[r] - b[1]))
    return offsets, (xs[-1] + col_w[-1], ys[-1] + row_h[-1])
