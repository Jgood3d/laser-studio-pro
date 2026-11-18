"""Générateur de porte-clés personnalisés (prénom + base dilatée + anneau), façon NameKey.

Repère LSP : Y vers le haut, en mm, coin bas-gauche de la pièce ramené à (0, 0).
Produit deux ensembles de polygones fermés :
  - base_contours : contour extérieur de la base soudée à l'anneau + trou de l'anneau (calque Découpe)
  - text_contours : tracé vectoriel du texte centré sur la base (calque Gravure)
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


class KeychainResult:
    def __init__(
        self,
        base_contours: List[Polygon],
        text_contours: List[Polygon],
        width: float,
        height: float,
    ):
        self.base_contours = base_contours
        self.text_contours = text_contours
        self.width = width
        self.height = height


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


def build_keychain(
    params: KeychainParams,
    family: str = "Sans Serif",
    bold: bool = True,
    italic: bool = False,
) -> KeychainResult:
    """Génère les contours de découpe (base + trou) et de gravure (texte) du porte-clés."""
    _validate(params)

    raw_text = _build_raw_text_path(
        params.text, family, bold, italic, params.letter_spacing
    )
    if raw_text.isEmpty():
        raise KeychainError("empty_text")

    raw_rect = raw_text.boundingRect()
    if raw_rect.height() <= 0 or raw_rect.width() <= 0:
        raise KeychainError("empty_text")

    # Mise à l'échelle pour atteindre la hauteur demandée en mm, centré en (0, 0)
    scale = params.text_height_mm / raw_rect.height()
    cx_raw = raw_rect.center().x()
    cy_raw = raw_rect.center().y()
    text_path = QTransform(
        scale, 0.0, 0.0, scale, -cx_raw * scale, -cy_raw * scale
    ).map(raw_text)
    text_path.setFillRule(Qt.FillRule.WindingFill)
    text_path = text_path.simplified()

    # Dilatation du texte pour créer la base (contour extérieur arrondi)
    stroker = QPainterPathStroker()
    stroker.setWidth(params.margin_mm * 2.0)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    stroke_halo = stroker.createStroke(text_path)

    base_path = text_path.united(stroke_halo).simplified()
    base_path = _remove_interior_voids(base_path)

    # Si un point sur un 'i' ou un accent forme un îlot séparé, on le relie au corps principal
    if params.bridge_isolated:
        sub_polys = _path_to_polygons(base_path, 0.0, 0.0)
        if len(sub_polys) > 1:
            # Pont vertical/horizontal minimal vers le centre du texte
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

    # Ajout de l'anneau d'accroche
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
        else:  # "Haut"
            ring_cx = base_rect.center().x()
            ring_cy = base_rect.bottom() + r_out - overlap  # Y vers le haut : bottom() est le haut géométrique

        ring_outer = _circle_path(ring_cx, ring_cy, r_out)
        ring_hole = _circle_path(ring_cx, ring_cy, r_in)
        base_path = base_path.united(ring_outer).subtracted(ring_hole).simplified()

    final_rect = base_path.boundingRect()
    dx = -final_rect.left()
    dy = -final_rect.top()

    base_contours = _path_to_polygons(base_path, dx, dy)
    text_contours = _path_to_polygons(text_path, dx, dy)

    # Trie la base pour que le contour extérieur soit toujours en index 0
    base_contours.sort(
        key=lambda c: -(
            (max(p[0] for p in c) - min(p[0] for p in c))
            * (max(p[1] for p in c) - min(p[1] for p in c))
        )
    )

    return KeychainResult(
        base_contours=base_contours,
        text_contours=text_contours,
        width=final_rect.width(),
        height=final_rect.height(),
    )