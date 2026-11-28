"""Générateur de porte-clés personnalisés (prénom + base dilatée + anneau), façon NameKey.

Repère LSP : Y vers le haut, en mm, coin bas-gauche de la pièce ramené à (0, 0).

Supporte un ou plusieurs prénoms (un par ligne dans `params.text`).

Produit des ensembles de polygones fermés :
  - base_contours : contour(s) extérieur(s) de la/les base(s) + trou anneau (calque Découpe)
  - text_contours : tracé vectoriel du/des texte(s)
      * mode classique → calque Gravure (remplissage)
      * mode 2 couches → lettres solides de la pièce de droite (calque Découpe)
      * mode lettres à coller → calque Gravure (remplissage) : repère de placement des lettres
  - outline_contours : contours des lettres (mode 2 couches, guide de collage en Gravure)
  - top_base_contours / top_text_contours : pièce de droite en mode 2 couches ; en mode lettres à coller,
    `top_text_contours` seul : les lettres découpées à part, à droite de la plaque (`top_base_contours` vide)
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainterPath, QPainterPathStroker, QTransform

Point = Tuple[float, float]
Polygon = List[Point]

RING_POSITIONS = ("Gauche", "Droite", "Haut", "Aucun")

TEXT_REF_PX = 200.0
FLATTEN_SCALE = 20.0

class KeychainError(ValueError):
    """Paramètres invalides (le code sert de clé de traduction `keychain.err.<code>`)."""

    def __init__(self, code: str, **info):
        super().__init__(code)
        self.code = code
        self.info = info


class KeychainParams:
    def __init__(
        self,
        text: str = "Emma",
        text_height_mm: float = 14.0,
        letter_spacing: float = 100.0,
        margin_mm: float = 3.0,
        ring_position: str = "Gauche",
        ring_outer_d: float = 9.0,
        ring_hole_d: float = 4.0,
        ring_overlap_mm: float = 2.0,
        bridge_isolated: bool = True,
        two_layers: bool = False,
        glue_letters: bool = False,
    ):
        self.text = text or ""
        self.text_height_mm = float(text_height_mm)
        self.letter_spacing = float(letter_spacing)  # en % (100 = normal)
        self.margin_mm = float(margin_mm)
        self.ring_position = ring_position
        self.ring_outer_d = float(ring_outer_d)
        self.ring_hole_d = float(ring_hole_d)
        self.ring_overlap_mm = float(ring_overlap_mm)
        self.bridge_isolated = bool(bridge_isolated)
        # Lettres à coller : plaque gravée du prénom + lettres découpées à part. Exclusif avec « 2 couches »
        self.glue_letters = bool(glue_letters)
        self.two_layers = bool(two_layers) and not self.glue_letters


class KeychainResult:
    def __init__(
        self,
        base_contours: List[Polygon],
        text_contours: List[Polygon],
        width: float,
        height: float,
        outline_contours: Optional[List[Polygon]] = None,
        two_layers: bool = False,
        top_base_contours: Optional[List[Polygon]] = None,
        top_text_contours: Optional[List[Polygon]] = None,
        pieces: Optional[List["KeychainResult"]] = None,
        glue_letters: bool = False,
    ):
        self.base_contours = base_contours
        self.text_contours = text_contours
        self.outline_contours = outline_contours or []
        self.width = width
        self.height = height
        self.two_layers = bool(two_layers)
        self.glue_letters = bool(glue_letters)
        # Pièce de droite (couche dessus) — mode 2 couches ; lettres à coller : `top_text_contours` seul
        self.top_base_contours = top_base_contours or []
        self.top_text_contours = top_text_contours or []
        # Lot : une entrée par prénom (chacune est un KeychainResult "simple")
        self.pieces = pieces or []


def _validate(params: KeychainParams) -> None:
    if not params.text.strip():
        raise KeychainError("empty_text")
    if not (4.0 <= params.text_height_mm <= 150.0):
        raise KeychainError("text_height", value=params.text_height_mm)
    if not (1.0 <= params.margin_mm <= 30.0):
        raise KeychainError("margin", value=params.margin_mm)
    if params.ring_position not in RING_POSITIONS:
        raise KeychainError("ring_position", value=params.ring_position)
    if params.ring_position != "Aucun":
        if not (4.0 <= params.ring_outer_d <= 40.0):
            raise KeychainError("ring_outer", value=params.ring_outer_d)
        if not (1.5 <= params.ring_hole_d <= params.ring_outer_d - 2.0):
            raise KeychainError("ring_hole", value=params.ring_hole_d)


def _circle_path(cx: float, cy: float, radius: float, n: int = 120) -> QPainterPath:
    path = QPainterPath()
    for i in range(n):
        angle = 2.0 * math.pi * i / n
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    path.setFillRule(Qt.FillRule.WindingFill)
    return path


def _build_raw_text_path(
    text: str,
    family: str,
    bold: bool,
    italic: bool,
    letter_spacing: float,
) -> QPainterPath:
    """Construit le tracé du texte en Y vers le haut, centré horizontalement autour de x=0."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return QPainterPath()

    font = QFont(family)
    font.setPixelSize(int(TEXT_REF_PX))
    font.setBold(bold)
    font.setItalic(italic)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, letter_spacing)

    full_path = QPainterPath()
    full_path.setFillRule(Qt.FillRule.WindingFill)
    line_step = TEXT_REF_PX * 1.15

    for idx, line in enumerate(lines):
        line_path = QPainterPath()
        line_path.addText(0.0, 0.0, font, line)
        # Repère Y vers le haut
        line_path = QTransform(1, 0, 0, -1, 0, 0).map(line_path)
        rect = line_path.boundingRect()
        if rect.isEmpty():
            continue
        dx = -rect.center().x()
        dy = -idx * line_step
        line_path = QTransform.fromTranslate(dx, dy).map(line_path)
        full_path.addPath(line_path)

    return full_path.simplified()


def _path_to_polygons(path: QPainterPath, dx: float, dy: float) -> List[Polygon]:
    out: List[Polygon] = []
    if path.isEmpty():
        return out
    for poly in path.toSubpathPolygons(QTransform.fromScale(FLATTEN_SCALE, FLATTEN_SCALE)):
        pts: Polygon = []
        for p in poly:
            q = (p.x() / FLATTEN_SCALE + dx, p.y() / FLATTEN_SCALE + dy)
            if not pts or q != pts[-1]:
                pts.append(q)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        if len(pts) >= 3:
            out.append(pts)
    return out


def _remove_interior_voids(path: QPainterPath) -> QPainterPath:
    """Supprime les petits trous intérieurs de la base dilatée (ex. entre deux lettres)
    en ne conservant que l'enveloppe extérieure pleine de chaque îlot."""
    polys = _path_to_polygons(path, 0.0, 0.0)
    if not polys:
        return path
    solid = QPainterPath()
    solid.setFillRule(Qt.FillRule.WindingFill)
    for pts in polys:
        sub = QPainterPath()
        sub.moveTo(*pts[0])
        for x, y in pts[1:]:
            sub.lineTo(x, y)
        sub.closeSubpath()
        solid.addPath(sub)
    return solid.simplified()


def _offset_polys(polys: List[Polygon], ox: float, oy: float = 0.0) -> List[Polygon]:
    return [[(x + ox, y + oy) for x, y in poly] for poly in polys]


def _build_keychain_core(
    params: KeychainParams,
    family: str = "Sans Serif",
    bold: bool = True,
    italic: bool = False,
) -> KeychainResult:
    """Cœur de génération pour UN prénom."""
    _validate(params)

    raw_text = _build_raw_text_path(
        params.text, family, bold, italic, params.letter_spacing
    )
    if raw_text.isEmpty():
        raise KeychainError("empty_text")

    raw_rect = raw_text.boundingRect()
    if raw_rect.height() <= 0 or raw_rect.width() <= 0:
        raise KeychainError("empty_text")

    scale = params.text_height_mm / raw_rect.height()
    cx_raw = raw_rect.center().x()
    cy_raw = raw_rect.center().y()
    text_path = QTransform(
        scale, 0.0, 0.0, scale, -cx_raw * scale, -cy_raw * scale
    ).map(raw_text)
    text_path.setFillRule(Qt.FillRule.WindingFill)
    text_path = text_path.simplified()

    stroker = QPainterPathStroker()
    stroker.setWidth(params.margin_mm * 2.0)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    stroke_halo = stroker.createStroke(text_path)

    base_path = text_path.united(stroke_halo).simplified()
    base_path = _remove_interior_voids(base_path)

    if params.bridge_isolated:
        sub_polys = _path_to_polygons(base_path, 0.0, 0.0)
        if len(sub_polys) > 1:
            main_rect = text_path.boundingRect()
            for pts in sub_polys:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bx, by = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
                bridge = QPainterPath()
                bridge.moveTo(bx, by)
                bridge.lineTo(bx, main_rect.center().y())
                bridge_stroker = QPainterPathStroker()
                bridge_stroker.setWidth(max(2.0, params.margin_mm * 1.2))
                bridge_stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
                base_path = base_path.united(bridge_stroker.createStroke(bridge)).simplified()
            base_path = _remove_interior_voids(base_path)

    base_rect = base_path.boundingRect()
    if params.ring_position != "Aucun":
        r_out = params.ring_outer_d / 2.0
        r_in = params.ring_hole_d / 2.0
        overlap = min(params.ring_overlap_mm, r_out * 0.9)

        if params.ring_position == "Gauche":
            ring_cx = base_rect.left() - r_out + overlap
            ring_cy = base_rect.center().y()
        elif params.ring_position == "Droite":
            ring_cx = base_rect.right() + r_out - overlap
            ring_cy = base_rect.center().y()
        else:
            ring_cx = base_rect.center().x()
            ring_cy = base_rect.bottom() + r_out - overlap

        ring_outer = _circle_path(ring_cx, ring_cy, r_out)
        ring_hole = _circle_path(ring_cx, ring_cy, r_in)
        base_path = base_path.united(ring_outer).subtracted(ring_hole).simplified()

    final_rect = base_path.boundingRect()
    dx = -final_rect.left()
    dy = -final_rect.top()

    base_contours = _path_to_polygons(base_path, dx, dy)
    text_contours = _path_to_polygons(text_path, dx, dy)

    base_contours.sort(
        key=lambda c: -(
            (max(p[0] for p in c) - min(p[0] for p in c))
            * (max(p[1] for p in c) - min(p[1] for p in c))
        )
    )

    outline_contours: List[Polygon] = []
    top_base_contours: List[Polygon] = []
    top_text_contours: List[Polygon] = []

    if params.two_layers:
        outline_contours = text_contours
        gap = 5.0
        offset_x = final_rect.width() + gap
        top_base_contours = _offset_polys(base_contours, offset_x)
        top_text_contours = _offset_polys(text_contours, offset_x)
        total_width = final_rect.width() * 2 + gap
        total_height = final_rect.height()
    elif params.glue_letters:
        # Gauche : la plaque, prénom gravé (placement). Droite : les lettres seules, découpées, à coller dessus.
        gap = 5.0
        top_text_contours = _offset_polys(text_contours, final_rect.width() + gap)
        total_width = final_rect.width() * 2 + gap
        total_height = final_rect.height()
    else:
        total_width = final_rect.width()
        total_height = final_rect.height()

    return KeychainResult(
        base_contours=base_contours,
        text_contours=text_contours,
        width=total_width,
        height=total_height,
        outline_contours=outline_contours,
        two_layers=params.two_layers,
        top_base_contours=top_base_contours,
        top_text_contours=top_text_contours,
        glue_letters=params.glue_letters,
    )


def build_keychain(
    params: KeychainParams,
    family: str = "Sans Serif",
    bold: bool = True,
    italic: bool = False,
) -> KeychainResult:
    """Génère un ou plusieurs porte-clés.

    - Un seul prénom → comportement historique.
    - Plusieurs prénoms (un par ligne) → grille (max 4 par rangée), 5 mm d'écart.
    """
    names = [ln.strip() for ln in (params.text or "").splitlines() if ln.strip()]
    if not names:
        raise KeychainError("empty_text")

    if len(names) == 1:
        single = KeychainParams(
            text=names[0],
            text_height_mm=params.text_height_mm,
            letter_spacing=params.letter_spacing,
            margin_mm=params.margin_mm,
            ring_position=params.ring_position,
            ring_outer_d=params.ring_outer_d,
            ring_hole_d=params.ring_hole_d,
            ring_overlap_mm=params.ring_overlap_mm,
            bridge_isolated=params.bridge_isolated,
            two_layers=params.two_layers,
            glue_letters=params.glue_letters,
        )
        return _build_keychain_core(single, family, bold, italic)

    # Plusieurs noms
    results: List[KeychainResult] = []
    for name in names:
        single = KeychainParams(
            text=name,
            text_height_mm=params.text_height_mm,
            letter_spacing=params.letter_spacing,
            margin_mm=params.margin_mm,
            ring_position=params.ring_position,
            ring_outer_d=params.ring_outer_d,
            ring_hole_d=params.ring_hole_d,
            ring_overlap_mm=params.ring_overlap_mm,
            bridge_isolated=params.bridge_isolated,
            two_layers=params.two_layers,
            glue_letters=params.glue_letters,
        )
        results.append(_build_keychain_core(single, family, bold, italic))

    gap = 5.0
    cols = min(4, len(results))
    n = len(results)
    rows = (n + cols - 1) // cols

    col_widths = [0.0] * cols
    row_heights: List[float] = []
    for r in range(rows):
        row_h = 0.0
        for c in range(cols):
            i = r * cols + c
            if i >= n:
                break
            col_widths[c] = max(col_widths[c], results[i].width)
            row_h = max(row_h, results[i].height)
        row_heights.append(row_h)

    x_offsets = [0.0]
    for c in range(cols - 1):
        x_offsets.append(x_offsets[-1] + col_widths[c] + gap)
    y_offsets = [0.0]
    for r in range(rows - 1):
        y_offsets.append(y_offsets[-1] + row_heights[r] + gap)

    all_base: List[Polygon] = []
    all_text: List[Polygon] = []
    all_outline: List[Polygon] = []
    all_top_base: List[Polygon] = []
    all_top_text: List[Polygon] = []
    placed_pieces: List[KeychainResult] = []

    for i, res in enumerate(results):
        r, c = divmod(i, cols)
        ox = x_offsets[c]
        oy = y_offsets[r]
        all_base.extend(_offset_polys(res.base_contours, ox, oy))
        all_text.extend(_offset_polys(res.text_contours, ox, oy))
        all_outline.extend(_offset_polys(res.outline_contours, ox, oy))
        all_top_base.extend(_offset_polys(res.top_base_contours, ox, oy))
        all_top_text.extend(_offset_polys(res.top_text_contours, ox, oy))

        # Copie décalée pour l'import : chaque pièce garde sa position dans la grille
        placed_pieces.append(KeychainResult(
            base_contours=_offset_polys(res.base_contours, ox, oy),
            text_contours=_offset_polys(res.text_contours, ox, oy),
            width=res.width,
            height=res.height,
            outline_contours=_offset_polys(res.outline_contours, ox, oy),
            two_layers=res.two_layers,
            top_base_contours=_offset_polys(res.top_base_contours, ox, oy),
            top_text_contours=_offset_polys(res.top_text_contours, ox, oy),
            glue_letters=res.glue_letters,
        ))

    total_w = x_offsets[-1] + col_widths[min(cols, n) - 1] if n else 0.0
    total_h = y_offsets[-1] + row_heights[-1] if rows else 0.0

    return KeychainResult(
        base_contours=all_base,
        text_contours=all_text,
        width=total_w,
        height=total_h,
        outline_contours=all_outline,
        two_layers=params.two_layers,
        top_base_contours=all_top_base,
        top_text_contours=all_top_text,
        pieces=placed_pieces,
        glue_letters=params.glue_letters,
    )
