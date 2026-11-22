"""Feuilles à imprimer pour la calibration de la caméra, à l'échelle réelle.

Sans Qt : ce module ne fait que placer des éléments en millimètres sur des
pages (origine en haut à gauche, Y vers le bas) ; l'impression elle-même est
dans ui/dialogs/camera/printing.py.

Éléments d'une page (tuples) :
    ("rect", x, y, w, h)            rectangle plein noir
    ("frame", x, y, w, h)           cadre fin pointillé (repère de découpe)
    ("line", x1, y1, x2, y2)        trait fin
    ("text", x, y, w, texte, pt)    texte centré dans la largeur w, sous y
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Sequence, Tuple

from laser_studio.camera.workspace_alignment import AlignmentTarget, apriltag_engrave_polygons

PAGE_MARGIN_MM = 10.0
TAG_QUIET_MM = 6.0          # zone claire autour d'un tag (nécessaire à sa détection)
TAG_LABEL_MM = 12.0         # hauteur du texte sous chaque tag
TICK_MM = 3.0               # repères au milieu de chaque côté du tag
MAX_SQUARE_MM = 30.0


@dataclass
class Page:
    items: List[tuple] = field(default_factory=list)


def chessboard_pages(
    pattern_size: Tuple[int, int],
    page_w_mm: float,
    page_h_mm: float,
    caption: Callable[[float], str],
) -> Tuple[List[Page], float]:
    """Une page : le damier (coins intérieurs `pattern_size`), centré, aussi
    grand que possible (cases de MAX_SQUARE_MM au plus, arrondies au demi-mm
    inférieur). `caption(case_mm)` donne la légende en bas de page.
    Renvoie (pages, côté d'une case en mm)."""
    cols, rows = pattern_size[0] + 1, pattern_size[1] + 1
    legend_h = 12.0
    avail_w = page_w_mm - 2 * PAGE_MARGIN_MM
    avail_h = page_h_mm - 2 * PAGE_MARGIN_MM - legend_h
    square = min(avail_w / cols, avail_h / rows, MAX_SQUARE_MM)
    if square < 5.0:
        raise ValueError("Page trop petite pour le damier")
    square = int(square * 2) / 2.0
    board_w, board_h = cols * square, rows * square
    x0 = (page_w_mm - board_w) / 2.0
    y0 = (page_h_mm - legend_h - board_h) / 2.0
    page = Page()
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2 == 0:
                page.items.append(("rect", x0 + c * square, y0 + r * square, square, square))
    page.items.append(("text", x0, y0 + board_h + 3.0, board_w, caption(square), 10))
    return [page], square


def apriltag_pages(
    targets: Sequence[AlignmentTarget],
    page_w_mm: float,
    page_h_mm: float,
    label: Callable[[AlignmentTarget], str],
    footer: Callable[[AlignmentTarget], str],
) -> List[Page]:
    """Les AprilTags à découper puis poser sur le plateau, à leur taille réelle
    (`target.size_mm`), répartis en grille sur autant de pages que nécessaire.

    Chaque tag a sa zone claire, un cadre de découpe, des repères au milieu de
    ses côtés (pour le centrer sur sa position) et sa légende (identifiant et
    position du centre sur le plateau, `label(target)`). `footer(tag)` : ligne
    de bas de page (rappel d'imprimer à 100 %)."""
    if not targets:
        return []
    size = targets[0].size_mm
    cell_w = size + 2 * TAG_QUIET_MM
    cell_h = size + 2 * TAG_QUIET_MM + TAG_LABEL_MM
    footer_h = 8.0
    n_cols = int((page_w_mm - 2 * PAGE_MARGIN_MM) // cell_w)
    n_rows = int((page_h_mm - 2 * PAGE_MARGIN_MM - footer_h) // cell_h)
    if n_cols < 1 or n_rows < 1:
        raise ValueError("Page trop petite pour la taille de tag demandée")
    per_page = n_cols * n_rows
    grid_w = n_cols * cell_w
    left = (page_w_mm - grid_w) / 2.0

    pages: List[Page] = []
    for start in range(0, len(targets), per_page):
        page = Page()
        for k, target in enumerate(targets[start:start + per_page]):
            col, row = k % n_cols, k // n_cols
            cx = left + col * cell_w + cell_w / 2.0
            cy_top = PAGE_MARGIN_MM + row * cell_h
            cy = cy_top + TAG_QUIET_MM + size / 2.0
            _add_tag(page, target, cx, cy, left + col * cell_w, cy_top, cell_w, cell_h, label(target))
        page.items.append(("text", PAGE_MARGIN_MM, page_h_mm - PAGE_MARGIN_MM - 4.0,
                           page_w_mm - 2 * PAGE_MARGIN_MM, footer(targets[0]), 9))
        pages.append(page)
    return pages


def _add_tag(page, target, cx, cy, cell_x, cell_y, cell_w, cell_h, text):
    """Un tag centré en (cx, cy) dans la cellule (cell_x, cell_y, cell_w, cell_h)."""
    half = target.size_mm / 2.0
    local = AlignmentTarget(target.tag_id, 0.0, 0.0, target.size_mm)
    for polygon in apriltag_engrave_polygons(local):
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        # Repère du motif : Y vers le haut, centré ; la page a Y vers le bas.
        page.items.append(("rect", cx + min(xs), cy - max(ys), max(xs) - min(xs), max(ys) - min(ys)))
    page.items.append(("frame", cell_x + 1.0, cell_y, cell_w - 2.0, cell_h - 1.0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        x1, y1 = cx + dx * half, cy + dy * half
        page.items.append(("line", x1, y1, x1 + dx * TICK_MM, y1 + dy * TICK_MM))
    page.items.append(("text", cell_x, cy + half + TAG_QUIET_MM, cell_w, text, 8))
