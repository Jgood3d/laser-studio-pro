"""Vue graphique zoomable/déplaçable utilisée pour l'aperçu image et le raster."""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QWheelEvent


class ZoomableGraphicsView(QGraphicsView):
    """Vue graphique personnalisée permettant un zoom fluide à la molette et un déplacement (pan) fluide de l'image."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.pixmap_item = QGraphicsPixmapItem()
        # Activation du lissage pour un rendu visuel net et sans artéfacts de moiré sur le tramage
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        # PAS de CacheMode.DeviceCoordinateCache ici : ce widget affiche un
        # aperçu qui change de CONTENU en permanence (tramage recalculé à
        # chaque réglage), pas seulement de zoom/pan sur une image fixe. Un
        # cache par coordonnées appareil doit être reconstruit entièrement à
        # chaque nouveau pixmap — ça ajoute une passe de rendu complète en
        # plus à chaque mise à jour au lieu d'économiser du travail, d'où le
        # ralentissement (constaté aussi bien en plein écran que dans
        # l'onglet normal une fois ce cache activé).
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.scene_obj.addItem(self.pixmap_item)
        
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)
        self.zoom_factor = 1.15
        
        self._dragging = False
        self._last_mouse_pos = None

    def set_image(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.pixmap_item.setPixmap(pixmap)
        if self.scene_obj.sceneRect().size().isEmpty():
            self.setSceneRect(QRectF(pixmap.rect()))
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear_image(self):
        self.pixmap_item.setPixmap(QPixmap())
        self.setSceneRect(QRectF())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Force un repaint complet du viewport au redimensionnement : sans ça,
        # la bascule plein écran <-> normal pouvait laisser d'anciens pixels
        # affichés ("superposition") jusqu'à ce qu'un autre événement (ex.
        # changement d'onglet, qui cache/affiche le widget) déclenche un
        # repaint complet.
        self.viewport().update()

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1.0 / self.zoom_factor, 1.0 / self.zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton or event.button() == Qt.MouseButton.MiddleButton:
            self._dragging = True
            self._last_mouse_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_mouse_pos is not None:
            delta = event.position().toPoint() - self._last_mouse_pos
            self._last_mouse_pos = event.position().toPoint()
            
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and (event.button() == Qt.MouseButton.LeftButton or event.button() == Qt.MouseButton.MiddleButton):
            self._dragging = False
            self._last_mouse_pos = None
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
