"""Fonds de la scène du canevas, sous les objets : le plateau et sa grille graduée (WorkAreaLayer), l'image de
la caméra posée sur le plateau (CameraLayer). Chacun possède ses éléments graphiques et sait les remplacer ou
les retirer ; la géométrie vient de vector.work_area.WorkArea.

    grid = WorkAreaLayer(scene)
    grid.show(WorkArea(300, 200))        # plateau, graduations, repères chiffrés
    camera = CameraLayer(scene)
    camera.show(image_bgr, 300, 200, area)   # photo redressée, à l'échelle du plateau de la caméra
"""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPen, QPixmap, QTransform
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem

from laser_studio.ui.app.theme import theme_color

# Empilement des fonds (les objets sont à 0 et au-dessus, voir DocumentItems) : plateau, caméra, grille
# secondaire, grille principale, chiffres.
Z_WORK_AREA = -100
Z_CAMERA = -97
Z_GRID_MINOR = -95
Z_GRID_MAJOR = -90
Z_LABELS = -80
ORIGIN_LABEL = "0,0 (origine)"
ORIGIN_COLOR = "#ff8844"


def _cosmetic_pen(color):
    pen = QPen(color, 0)
    pen.setCosmetic(True)                  # même épaisseur à l'écran quel que soit le zoom
    return pen


class WorkAreaLayer:
    """Plateau (cadre) et grille graduée : graduations secondaires, principales chiffrées le long des bords
    bas et gauche, et l'origine (coin bas-gauche). Couleurs du thème, relues à chaque show()."""

    def __init__(self, scene):
        self.scene = scene
        self.items = []
        self.rect_item = None

    def show(self, area):
        """Remplace le plateau et la grille par ceux de `area` (WorkArea)."""
        self.clear()
        rect = QRectF(0, 0, area.width_px, area.height_px)
        self.rect_item = QGraphicsRectItem(rect)
        pen = QPen(theme_color("canvas_edge", "#666666"), 1)
        pen.setCosmetic(True)
        self.rect_item.setPen(pen)
        self.rect_item.setZValue(Z_WORK_AREA)
        self.scene.addItem(self.rect_item)
        self._draw_grid(area)

    def clear(self):
        for item in self.items + ([self.rect_item] if self.rect_item is not None else []):
            self.scene.removeItem(item)
        self.items, self.rect_item = [], None

    def bounds(self):
        """Rectangle du plateau dans la scène, ou un rectangle nul avant le premier show()."""
        return self.rect_item.sceneBoundingRect() if self.rect_item is not None else QRectF()

    def _draw_grid(self, area):
        grid, s, bottom = area.grid(), area.px_per_mm, area.height_px
        minor_pen = _cosmetic_pen(theme_color("canvas_minor", "#262626"))
        major_pen = _cosmetic_pen(theme_color("canvas_grid", "#333333"))
        label_color = theme_color("canvas_label", "#999999")
        for x in grid.minor_x:
            self._line(x * s, 0, x * s, bottom, minor_pen, Z_GRID_MINOR)
        for y in grid.minor_y:
            self._line(0, bottom - y * s, area.width_px, bottom - y * s, minor_pen, Z_GRID_MINOR)
        for x in grid.major_x:
            self._line(x * s, 0, x * s, bottom, major_pen, Z_GRID_MAJOR)
            self._label(f"{x:g}", label_color, x * s + 2, bottom - 16)
        for y in grid.major_y:
            screen_y = bottom - y * s
            self._line(0, screen_y, area.width_px, screen_y, major_pen, Z_GRID_MAJOR)
            self._label(f"{y:g}", label_color, 2, screen_y - 16)
        self._label(ORIGIN_LABEL, QColor(ORIGIN_COLOR), 2, bottom - 32)

    def _line(self, x1, y1, x2, y2, pen, z):
        line = self.scene.addLine(x1, y1, x2, y2, pen)
        line.setZValue(z)
        self.items.append(line)

    def _label(self, text, color, x, y):
        label = self.scene.addSimpleText(text)
        label.setBrush(color)
        label.setPos(x, y)
        label.setZValue(Z_LABELS)
        self.items.append(label)


class CameraLayer:
    """Image de la caméra, déjà redressée sur le plateau (haut de l'image = Y max), posée sous la grille et
    sous les objets à l'échelle du plateau, pour placer ce qu'on grave sur la vraie matière. La souris la
    traverse : elle ne gêne ni la sélection ni les outils."""

    MIN_OPACITY = 0.05

    def __init__(self, scene):
        self.scene = scene
        self.item = None
        self.opacity = 0.7

    def show(self, image_bgr, bed_w_mm, bed_h_mm, area):
        """Pose `image_bgr` (BGR ou niveaux de gris, numpy) sur le plateau de `bed_w_mm` × `bed_h_mm` vu par la
        caméra, dans le repère de `area` (WorkArea) ; une image vide retire la précédente."""
        import cv2   # ici : OpenCV n'est chargé qu'au premier fond caméra
        import numpy as np
        self.clear()
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return
        code = cv2.COLOR_GRAY2RGB if image_bgr.ndim == 2 else cv2.COLOR_BGR2RGB
        rgb = np.ascontiguousarray(cv2.cvtColor(image_bgr, code))
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        item = QGraphicsPixmapItem(QPixmap.fromImage(qimg))
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        s = area.px_per_mm
        item.setTransform(QTransform.fromScale(bed_w_mm * s / w, bed_h_mm * s / h))
        item.setPos(QPointF(*area.to_scene(0.0, bed_h_mm)))   # coin haut-gauche du plateau
        item.setZValue(Z_CAMERA)
        item.setOpacity(self.opacity)
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.scene.addItem(item)
        self.item = item

    def clear(self):
        item, self.item = self.item, None
        if item is not None:
            try:
                self.scene.removeItem(item)
            except RuntimeError:                       # déjà détruite avec la scène
                pass

    def set_opacity(self, value):
        """Opacité de l'image, de MIN_OPACITY à 1."""
        self.opacity = max(self.MIN_OPACITY, min(1.0, float(value)))
        if self.item is not None:
            try:
                self.item.setOpacity(self.opacity)
            except RuntimeError:
                self.item = None
