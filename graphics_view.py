"""Vue graphique zoomable/déplaçable utilisée pour l'aperçu image et le raster."""
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QWheelEvent, QAction


class ZoomableGraphicsView(QGraphicsView):
    """Vue graphique personnalisée permettant un zoom fluide à la molette, un déplacement (pan) fluide et un menu contextuel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.pixmap_item = QGraphicsPixmapItem()
        # Activation du lissage pour un rendu visuel net et sans artéfacts de moiré sur le tramage
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
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
        self._is_move_mode = False  # État du mode Déplacer activé via le clic droit

        # Activation du menu contextuel personnalisé
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

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
        self.viewport().update()

    def show_context_menu(self, pos):
        """Affiche le menu contextuel au clic droit avec l'option Déplacer."""
        menu = QMenu(self)
        
        move_action = QAction("Déplacer", self)
        move_action.setCheckable(True)
        move_action.setChecked(self._is_move_mode)
        move_action.triggered.connect(self.toggle_move_mode)
        menu.addAction(move_action)
        
        menu.addSeparator()
        
        reset_action = QAction("Réinitialiser la vue", self)
        reset_action.triggered.connect(lambda: self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio))
        menu.addAction(reset_action)

        menu.exec(self.mapToGlobal(pos))

    def toggle_move_mode(self, enabled):
        """Active ou désactive le mode Déplacer (Pan) de la vue."""
        self._is_move_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.unsetCursor()

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1.0 / self.zoom_factor, 1.0 / self.zoom_factor)

    def mousePressEvent(self, event):
        if self._is_move_mode or event.button() == Qt.MouseButton.MiddleButton:
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
            if self._is_move_mode:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Permet de déplacer la vue (Pan) avec les flèches du clavier (plus rapide avec Shift)."""
        step = 20 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 5
        
        h_bar = self.horizontalScrollBar()
        v_bar = self.verticalScrollBar()
        
        dx, dy = 0, 0
        if event.key() == Qt.Key.Key_Left:
            dx = step
        elif event.key() == Qt.Key.Key_Right:
            dx = -step
        elif event.key() == Qt.Key.Key_Up:
            dy = step
        elif event.key() == Qt.Key.Key_Down:
            dy = -step
        else:
            super().keyPressEvent(event)
            return

        if dx != 0 or dy != 0:
            h_bar.setValue(h_bar.value() - dx)
            v_bar.setValue(v_bar.value() - dy)
            event.accept()