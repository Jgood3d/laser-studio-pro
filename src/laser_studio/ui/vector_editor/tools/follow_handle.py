"""Poignée d'un texte posé sur un contour : un rond affiché sur le texte sélectionné, qu'on fait glisser pour
déplacer le texte le long de son contour (point du contour le plus proche de la souris)."""
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem

from laser_studio.i18n import tr
from laser_studio.vector.text_follow import follows_a_path
from laser_studio.vector.text_on_path import point_at_fraction, project_fraction

# Distance (pixels écran) sous laquelle un clic attrape la poignée.
HIT_PX = 14


class FollowHandle:
    """`canvas` : VectorCanvasView."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.handle = None      # QGraphicsEllipseItem affiché, ou None
        self.item = None        # élément texte auquel la poignée est attachée
        self.dragging = False
        self._undo_pushed = False

    def _text_item(self):
        """L'élément texte sélectionné s'il suit un contour (et seul), sinon None."""
        items = self.canvas.selected_items_vector()
        if len(items) == 1 and follows_a_path(items[0].obj) and not items[0].obj.vertical:
            return items[0]
        return None

    def _scene_pos(self, item):
        obj = item.obj
        x, y = point_at_fraction(obj.follow_points, float(getattr(obj, "follow_center", 0.5)))
        s = self.canvas.px_per_mm
        # Le chemin local du texte est en Y vers le bas : même passage mm -> px que VectorGraphicsItem.
        return item.mapToScene(QPointF(x * s, -y * s))

    def _remove(self):
        if self.handle is not None:
            try:
                self.canvas.scene_obj.removeItem(self.handle)
            except RuntimeError:
                pass
        self.handle = None

    def sync(self):
        """Crée, déplace ou retire la poignée selon la sélection (un texte posé sur un contour)."""
        item = self._text_item()
        if item is None:
            self._remove()
            self.item = None
            return
        if self.handle is None or self.item is not item:
            self._remove()
            handle = QGraphicsEllipseItem(-6.0, -6.0, 12.0, 12.0)
            handle.setBrush(QBrush(QColor("#00d4ff")))
            handle.setPen(QPen(QColor("#102030"), 1))
            handle.setZValue(2100)
            # Taille constante à l'écran, quel que soit le zoom.
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            handle.setToolTip(tr("vector.follow_handle_tip"))
            self.canvas.scene_obj.addItem(handle)
            self.handle = handle
            self.item = item
        self.handle.setPos(self._scene_pos(item))

    def hit(self, view_pos):
        if self.handle is None:
            return False
        center = self.canvas.mapFromScene(self.handle.pos())
        return (view_pos - center).manhattanLength() <= HIT_PX

    # -- événements

    def press(self, event):
        """Clic gauche sur la poignée : début du glissé. Renvoie True si l'événement est traité."""
        if not self.hit(event.position().toPoint()):
            return False
        self.dragging = True
        self._undo_pushed = False
        event.accept()
        return True

    def move(self, event):
        if not (self.dragging and event.buttons() & Qt.MouseButton.LeftButton):
            return False
        self.drag(event.position().toPoint())
        event.accept()
        return True

    def release(self, event):
        if not (self.dragging and event.button() == Qt.MouseButton.LeftButton):
            return False
        self.dragging = False
        self._undo_pushed = False
        event.accept()
        return True

    def drag(self, view_pos):
        """Le texte suit la souris le long de son contour (point le plus proche)."""
        item = self.item
        if item is None:
            return
        s = self.canvas.px_per_mm
        local = item.mapFromScene(self.canvas.mapToScene(view_pos))
        point = (local.x() / s, -local.y() / s)
        if not self._undo_pushed:
            self.canvas.push_undo_snapshot()
            self._undo_pushed = True
        item.obj.follow_center = project_fraction(item.obj.follow_points, point)
        item.refresh()
        self.handle.setPos(self._scene_pos(item))
