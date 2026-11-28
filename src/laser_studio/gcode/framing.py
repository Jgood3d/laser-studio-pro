"""Parcours du cadrage, sans Qt : le rectangle qui contient tout le job, ou le tour au plus près de ce qui
sera vraiment gravé ou découpé. Les deux partent des traits gravés du G-Code (gcode.preview, burn_segments :
segments où le laser est allumé), image et calques vectoriels confondus.

    paths = [box_path(burn_extent(segments))]     # X max, Y max, retour à X0, puis Y0
    paths = contour_paths(segments)               # le tour de chaque pièce, creux compris
"""
import numpy as np

# Écart (mm) en dessous duquel deux parties gravées sont cadrées ensemble (lettres d'un texte, lignes d'une
# image) ; c'est aussi la précision du tour.
FRAME_STEP_MM = 2.0
# Taille d'une case de la grille du contour (mm), agrandie pour un très grand job (au plus 4 000 cases de côté).
CONTOUR_CELL_MM = 0.5
CONTOUR_MAX_CELLS = 4000


def burn_extent(segments):
    """(x min, y min, x max, y max) des traits gravés, ou None s'il n'y en a pas."""
    seg = np.asarray(segments, dtype=np.float64).reshape(-1, 4)
    if not seg.size:
        return None
    xs, ys = seg[:, [0, 2]], seg[:, [1, 3]]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def box_path(extent):
    """Tour du rectangle `extent` (x min, y min, x max, y max) depuis son coin bas-gauche : jusqu'à X max,
    monte à Y max, revient à X min, redescend à Y min."""
    x0, y0, x1, y1 = extent
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _densify(seg, spacing):
    """Points le long des segments (N, 4), au plus `spacing` mm l'un de l'autre, extrémités comprises."""
    lengths = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
    parts = np.maximum(1, np.ceil(lengths / spacing).astype(np.int64))
    counts = parts + 1
    first = np.repeat(np.cumsum(counts) - counts, counts)
    t = (np.arange(int(counts.sum())) - first) / np.repeat(parts, counts)
    owner = np.repeat(np.arange(len(seg)), counts)
    x = seg[owner, 0] + t * (seg[owner, 2] - seg[owner, 0])
    y = seg[owner, 1] + t * (seg[owner, 3] - seg[owner, 1])
    return x, y


def contour_paths(segments, step=FRAME_STEP_MM):
    """Tour au plus près des traits gravés : une grille fine est remplie là où le laser grave, les écarts de
    moins de `step` mm sont refermés (lignes d'une image, lettres d'un texte), puis le bord extérieur de chaque
    pièce est suivi (les trous intérieurs ne comptent pas) et simplifié à `step` / 2 près. Suit les creux
    (pièce en L, étoile). Liste de tracés fermés [(x, y)…] en mm, du plus grand au plus petit ; None sans
    trait gravé."""
    import cv2   # ici : chargé au premier cadrage du contour, pas au démarrage
    seg = np.asarray(segments, dtype=np.float64).reshape(-1, 4)
    if not seg.size:
        return None
    x0, y0, x1, y1 = burn_extent(seg)
    cell = max(CONTOUR_CELL_MM, (x1 - x0) / CONTOUR_MAX_CELLS, (y1 - y0) / CONTOUR_MAX_CELLS)
    margin = int(np.ceil(step / cell)) + 1                   # place pour refermer sans toucher le bord
    width = int((x1 - x0) / cell) + 1 + 2 * margin
    height = int((y1 - y0) / cell) + 1 + 2 * margin
    grid = np.zeros((height, width), dtype=np.uint8)
    x, y = _densify(seg, cell / 2.0)
    grid[((y - y0) / cell).astype(np.int64) + margin, ((x - x0) / cell).astype(np.int64) + margin] = 255
    size = int(np.ceil(step / cell)) | 1
    grid = cv2.morphologyEx(grid, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    paths = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        points = cv2.approxPolyDP(contour, max(1.0, step / 2.0 / cell), True).reshape(-1, 2)
        path = [(round(float(x0 + (cx - margin) * cell), 3), round(float(y0 + (cy - margin) * cell), 3))
                for cx, cy in points]
        paths.append(path + [path[0]])
    return paths
