"""Duplication en série dans l'éditeur vectoriel : logique pure (sans Qt), testable seule.

Un « exemplaire » est la liste des objets sélectionnés (contour de découpe, gravure, texte...). L'exemplaire 0
est l'original, les autres en sont des clones. Chaque exemplaire peut recevoir son propre texte (un prénom),
puis les exemplaires sont rangés en grille (voir `layout_grid`) ou par imbrication automatique
(voir vector/nesting_apply.py et controllers/vector_editor.py, open_serial_duplicate).

Les fonctions reçoivent `clone(obj)` et `bounds(obj)` en paramètres : `bounds` renvoie le rectangle englobant
monde (xmin, ymin, xmax, ymax), Y vers le haut, ou None si l'objet n'a aucun tracé.
"""
import math

MAX_COPIES = 500
_EPS = 0.01          # tolérance (mm) pour décider qu'un texte dépasse du contour


def parse_names(text):
    """Une ligne = un exemplaire. Les lignes vides sont ignorées, les espaces de début / fin retirés."""
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def copy_count(names, count):
    """Nombre d'exemplaires : celui de la liste de noms si elle n'est pas vide, sinon `count`."""
    n = len(names) if names else int(count)
    return max(1, min(n, MAX_COPIES))


def default_columns(n):
    """Colonnes d'une grille à peu près carrée."""
    return max(1, int(math.ceil(math.sqrt(max(1, n)))))


def union_bounds(boxes):
    """Rectangle englobant de plusieurs rectangles (les None sont ignorés) ; None s'il n'y en a aucun."""
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def grid_extent(n, cols, cell_w, cell_h, gap_x, gap_y):
    """(largeur, hauteur) occupées par `n` cellules rangées sur `cols` colonnes."""
    cols = max(1, min(int(cols), n))
    rows = int(math.ceil(n / cols))
    return (cols * cell_w + (cols - 1) * gap_x, rows * cell_h + (rows - 1) * gap_y)


def set_text(obj, text, bounds, keep_center=True):
    """Remplace le texte de `obj`. Avec keep_center, le centre du texte reste à sa place (le texte est ancré
    par son coin bas-gauche : sans cela, un nom plus long dépasserait vers la droite)."""
    before = bounds(obj)
    obj.text = text
    if not keep_center or before is None:
        return
    after = bounds(obj)
    if after is None:
        return
    obj.x_mm += (before[0] + before[2]) / 2.0 - (after[0] + after[2]) / 2.0
    obj.y_mm += (before[1] + before[3]) / 2.0 - (after[1] + after[3]) / 2.0


def build_copies(objects, count, *, clone, bounds, text_index=None, names=None, keep_center=True):
    """Liste d'exemplaires ; `copies[0]` est la liste des objets d'origine (le texte est modifié en place).

    text_index : position, dans `objects`, du texte à personnaliser (None = pas de personnalisation).
    names      : un texte par exemplaire (voir parse_names)."""
    objects = list(objects)
    names = list(names or [])
    if text_index is None:
        names = []
    copies = [objects]
    for _ in range(copy_count(names, count) - 1):
        copies.append([clone(o) for o in objects])
    for copy, name in zip(copies, names):
        set_text(copy[text_index], name, bounds, keep_center)
    return copies


def copy_bounds(copy, bounds):
    return union_bounds([bounds(o) for o in copy])


def layout_grid(copies, bounds, cols, gap_x, gap_y, upward=True):
    """Range les exemplaires en grille, lecture de gauche à droite. Le premier reste en place ; les rangées
    suivantes vont vers le haut (Y croissant) ou vers le bas. Chaque cellule a la taille du plus grand
    exemplaire. Déplace les objets (x_mm, y_mm) et renvoie (largeur, hauteur) occupées."""
    boxes = [copy_bounds(c, bounds) for c in copies]
    sized = [b for b in boxes if b is not None]
    if not sized:
        return (0.0, 0.0)
    cell_w = max(b[2] - b[0] for b in sized)
    cell_h = max(b[3] - b[1] for b in sized)
    x0, y0 = boxes[0][0], boxes[0][1]
    n = len(copies)
    cols = max(1, min(int(cols), n))
    for i, (copy, box) in enumerate(zip(copies, boxes)):
        if box is None:
            continue
        row, col = divmod(i, cols)
        target_x = x0 + col * (cell_w + gap_x)
        target_y = y0 + (row if upward else -row) * (cell_h + gap_y)
        dx, dy = target_x - box[0], target_y - box[1]
        for obj in copy:
            obj.x_mm += dx
            obj.y_mm += dy
    return grid_extent(n, cols, cell_w, cell_h, gap_x, gap_y)


def overflowing(copies, text_index, bounds):
    """Indices des exemplaires dont le texte dépasse du reste du motif (le contour, typiquement).
    Sans autre objet que le texte, rien à comparer : liste vide."""
    result = []
    for i, copy in enumerate(copies):
        frame = union_bounds([bounds(o) for j, o in enumerate(copy) if j != text_index])
        text = bounds(copy[text_index])
        if frame is None or text is None:
            continue
        if (text[0] < frame[0] - _EPS or text[1] < frame[1] - _EPS
                or text[2] > frame[2] + _EPS or text[3] > frame[3] + _EPS):
            result.append(i)
    return result
