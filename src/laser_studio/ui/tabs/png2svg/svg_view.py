"""Aperçu SVG zoomable de l'onglet « Vectorisation d'image »."""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

try:
    from PyQt6.QtSvgWidgets import QGraphicsSvgItem
    from PyQt6.QtSvg import QSvgRenderer

    HAS_SVG_WIDGET = True
except ImportError:  # sans QtSvgWidgets, le widget affiche un simple QLabel
    HAS_SVG_WIDGET = False


class ZoomableSvgView(QGraphicsView):
    """Aperçu SVG avec zoom (molette ou boutons) et déplacement (glisser)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._svg_item = QGraphicsSvgItem()
        self._renderer: QSvgRenderer | None = None
        self._scene.addItem(self._svg_item)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setBackgroundBrush(Qt.GlobalColor.white)
        self._has_content = False

    def load_svg_bytes(self, svg_bytes: bytes):
        self._renderer = QSvgRenderer(QByteArray(svg_bytes))
        self._svg_item.setSharedRenderer(self._renderer)
        rect = self._svg_item.boundingRect()
        if rect.isEmpty():
            rect = QRectF(0, 0, 1, 1)
        self._scene.setSceneRect(rect)
        was_empty = not self._has_content
        self._has_content = True
        if was_empty:
            self.zoom_fit()

    def clear(self):
        """Vide l'aperçu (même nom que QLabel.clear, utilisé quand QtSvgWidgets manque)."""
        self._renderer = QSvgRenderer()
        self._svg_item.setSharedRenderer(self._renderer)
        self._has_content = False

    def zoom_fit(self):
        if self._scene.sceneRect().isEmpty():
            return
        self.resetTransform()
        self.fitInView(
            self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self.scale(0.8, 0.8)

    def wheelEvent(self, event):
        if not self._has_content:
            return
        factor = 1.15 if event.angleDelta().y() > 0 else (1 / 1.15)
        self.scale(factor, factor)
