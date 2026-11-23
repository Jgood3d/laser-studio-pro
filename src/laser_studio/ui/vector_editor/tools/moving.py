"""Déplacement de la vue et des objets : panoramique au bouton du milieu, déplacement groupé de la
sélection à la souris (Ctrl + clic ajoute ou retire un objet), calé sur la grille magnétique si elle
est active."""
from PyQt6.QtCore import Qt

from laser_studio.ui.vector_editor.item import VectorGraphicsItem


class MoveTool:
    """`canvas` : VectorCanvasView (grille : canvas.snap_enabled, canvas.snap_step_mm)."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.pan_last_pos = None
        self.drag_items = []
        self.drag_last_scene_pos = None
        self.drag_anchor_item = None

    # -- panoramique (bouton du milieu)

    def press_pan(self, event):
        if event.button() != Qt.MouseButton.MiddleButton:
            return False
        self.pan_last_pos = event.position().toPoint()
        self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()
        return True

    def move_pan(self, event):
        if self.pan_last_pos is None or not event.buttons() & Qt.MouseButton.MiddleButton:
            return False
        canvas = self.canvas
        new_pos = event.position().toPoint()
        delta = new_pos - self.pan_last_pos
        self.pan_last_pos = new_pos
        canvas.horizontalScrollBar().setValue(canvas.horizontalScrollBar().value() - delta.x())
        canvas.verticalScrollBar().setValue(canvas.verticalScrollBar().value() - delta.y())
        event.accept()
        return True

    def release_pan(self, event):
        if event.button() != Qt.MouseButton.MiddleButton:
            return False
        self.pan_last_pos = None
        self.canvas.setCursor(Qt.CursorShape.CrossCursor if self.canvas.draw_tool else Qt.CursorShape.ArrowCursor)
        event.accept()
        return True

    # -- déplacement de la sélection

    def press_select(self, event):
        """Clic gauche sans outil : sélection de l'objet cliqué et début du déplacement groupé. Renvoie
        True si l'événement est traité (sinon : cadre de sélection de Qt)."""
        canvas = self.canvas
        item_at = canvas.itemAt(event.position().toPoint())
        if not isinstance(item_at, VectorGraphicsItem):
            return False
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl + clic : ajoute l'objet à la sélection (ou le retire s'il en faisait déjà partie), sans
            # toucher au reste de la sélection.
            new_state = not item_at.isSelected()
            item_at.setSelected(new_state)
            if not new_state:
                # Objet désélectionné : simple bascule, pas de déplacement groupé à démarrer.
                event.accept()
                return True
        elif not item_at.isSelected():
            # Sans Ctrl : si l'objet cliqué ne fait pas déjà partie de la sélection, il devient l'unique
            # objet sélectionné.
            canvas.scene_obj.clearSelection()
            item_at.setSelected(True)

        selected = canvas.selected_items_vector()
        if not selected:
            return False
        canvas.push_undo_snapshot()
        self.drag_items = selected
        self.drag_anchor_item = item_at
        self.drag_last_scene_pos = canvas.mapToScene(event.position().toPoint())
        event.accept()
        return True

    def move_drag(self, event):
        """Déplacement groupé des objets sélectionnés. Renvoie True si l'événement est traité."""
        if not (self.drag_items and event.buttons() & Qt.MouseButton.LeftButton
                and self.drag_last_scene_pos is not None):
            return False
        canvas = self.canvas
        current_scene_pos = canvas.mapToScene(event.position().toPoint())
        delta = current_scene_pos - self.drag_last_scene_pos
        if delta.x() or delta.y():
            delta_x_mm = delta.x() / canvas.px_per_mm
            delta_y_mm = -delta.y() / canvas.px_per_mm
            for item in self.drag_items:
                item.obj.x_mm += delta_x_mm
                item.obj.y_mm += delta_y_mm
            # Accroche à la grille : on ne recale QUE l'objet réellement cliqué (l'ancre) sur le pas de
            # grille, puis on répercute le même petit correctif sur le reste de la sélection — plutôt que
            # d'accrocher chaque objet indépendamment, ce qui déformerait l'agencement relatif d'une
            # sélection multiple.
            step = canvas.snap_step_mm
            if canvas.snap_enabled and step > 0 and self.drag_anchor_item is not None:
                anchor = self.drag_anchor_item
                corr_x = round(anchor.obj.x_mm / step) * step - anchor.obj.x_mm
                corr_y = round(anchor.obj.y_mm / step) * step - anchor.obj.y_mm
                if corr_x or corr_y:
                    for item in self.drag_items:
                        item.obj.x_mm += corr_x
                        item.obj.y_mm += corr_y
            for item in self.drag_items:
                item.refresh()
            self.drag_last_scene_pos = current_scene_pos
        event.accept()
        return True

    def release_drag(self, event):
        """Fin du déplacement : chaque objet déplacé est annoncé (canvas.object_moved)."""
        if event.button() != Qt.MouseButton.LeftButton or not self.drag_items:
            return False
        moved_items = list(self.drag_items)
        self.drag_items = []
        self.drag_last_scene_pos = None
        self.drag_anchor_item = None
        for item in moved_items:
            self.canvas.object_moved.emit(item.obj)
        event.accept()
        return True
