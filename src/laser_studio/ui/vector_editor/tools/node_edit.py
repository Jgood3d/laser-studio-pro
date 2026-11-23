"""Édition des nœuds d'un tracé (SvgPathObject) : poignées sur chaque sommet, glisser un sommet,
double-clic sur un segment pour en ajouter un, Suppr pour le retirer, Échap pour sortir. Une forme ou
un texte est d'abord converti en tracé."""
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QPen, QTransform
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem

from laser_studio.models.vector_objects import SvgPathObject
from laser_studio.vector import path_ops


class NodeEditor:
    """`canvas` : VectorCanvasView. `active` : mode nœuds en cours, sur `target_item`."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.active = False
        self.target_item = None
        self.handles = []
        self.polylines = []         # list[list[QPointF]] en coordonnées locales objet
        self.drag_index = None      # (poly_idx, pt_idx) pendant un drag
        self.drag_pushed_undo = False

    def enter(self, item=None):
        """Active le mode nœuds sur l'item donné (ou la sélection unique)."""
        canvas = self.canvas
        canvas.set_draw_tool(None)
        if item is None:
            selected = canvas.selected_items_vector()
            if len(selected) != 1:
                return False
            item = selected[0]
        item = canvas._ensure_svg_path_object(item)
        if item is None or not isinstance(item.obj, SvgPathObject):
            return False

        self.exit()
        self.active = True
        self.target_item = item
        canvas.scene_obj.clearSelection()
        item.setSelected(True)
        # Désactive le déplacement de l'objet pendant l'édition de nœuds
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.rebuild_handles()
        canvas.setCursor(Qt.CursorShape.CrossCursor)
        return True

    def exit(self):
        if self.target_item is not None:
            try:
                self.target_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            except RuntimeError:
                pass
        self.clear_handles()
        self.active = False
        self.target_item = None
        self.polylines = []
        self.drag_index = None
        self.drag_pushed_undo = False
        if not self.canvas.draw_tool:
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    def clear_handles(self):
        for h in self.handles:
            try:
                self.canvas.scene_obj.removeItem(h)
            except RuntimeError:
                pass
        self.handles = []

    def local_to_scene(self, local_pt: QPointF):
        """Point local objet (Y Qt descendant dans local_path) -> scène."""
        item = self.target_item
        if item is None:
            return local_pt
        s = self.canvas.px_per_mm
        # Même pipeline que VectorGraphicsItem.refresh : scale mm->px puis transform item
        return item.mapToScene(QPointF(local_pt.x() * s, local_pt.y() * s))

    def scene_to_local(self, scene_pt: QPointF):
        item = self.target_item
        if item is None:
            return scene_pt
        s = self.canvas.px_per_mm
        p_item = item.mapFromScene(scene_pt)
        return QPointF(p_item.x() / s, p_item.y() / s)

    def _handle_radius(self):
        """Rayon (coords scène) d'une poignée : taille constante à l'écran, quel que soit le zoom."""
        return 5.0 / max(self.canvas.transform().m11(), 0.01)

    def rebuild_handles(self):
        self.clear_handles()
        item = self.target_item
        if item is None or not isinstance(item.obj, SvgPathObject):
            return
        # Polylignes en coords locales (avec scale_x/y déjà appliqué via local_path)
        self.polylines = path_ops.path_to_polylines(item.obj.local_path())
        for pi, pts in enumerate(self.polylines):
            for vi, pt in enumerate(pts):
                scene_pt = self.local_to_scene(pt)
                r = self._handle_radius()
                handle = QGraphicsEllipseItem(scene_pt.x() - r, scene_pt.y() - r, 2 * r, 2 * r)
                handle.setBrush(QBrush(QColor("#ffcc00")))
                handle.setPen(QPen(QColor("#222222"), 0))
                handle.setZValue(2000)
                handle.setData(0, ("node", pi, vi))
                handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                self.canvas.scene_obj.addItem(handle)
                self.handles.append(handle)

    def _store_polylines(self):
        """Polylignes -> tracé de l'objet. Si scale_x/y != 1, local_path applique le scale : on stocke le
        tracé « non scalé »."""
        item = self.target_item
        path = path_ops.polylines_to_path(self.polylines)
        sx = getattr(item.obj, "scale_x", 1.0) or 1.0
        sy = getattr(item.obj, "scale_y", 1.0) or 1.0
        if abs(sx - 1.0) > 1e-9 or abs(sy - 1.0) > 1e-9:
            t = QTransform()
            t.scale(1.0 / sx, 1.0 / sy)
            path = t.map(path)
        item.obj._local_path_data = path
        item.refresh()

    def apply_polylines(self):
        item = self.target_item
        if item is None or not isinstance(item.obj, SvgPathObject):
            return
        self._store_polylines()
        self.rebuild_handles()

    def hit_handle(self, scene_pos):
        hit_r = 8.0 / max(self.canvas.transform().m11(), 0.01)
        best = None
        best_d = hit_r * hit_r
        for h in self.handles:
            data = h.data(0)
            if not data or data[0] != "node":
                continue
            c = h.rect().center()
            # rect is in item coords = scene for these items
            d = (c.x() - scene_pos.x()) ** 2 + (c.y() - scene_pos.y()) ** 2
            if d <= best_d:
                best_d = d
                best = (data[1], data[2])
        return best

    def hit_segment(self, scene_pos):
        """Renvoie (poly_idx, insert_after_idx, local_point) si proche d'un segment."""
        if not self.polylines:
            return None
        max_dist_scene = 8.0 / max(self.canvas.transform().m11(), 0.01)
        local_pos = self.scene_to_local(scene_pos)
        best = None
        best_d = max_dist_scene / max(self.canvas.px_per_mm, 1e-6)
        best_d = best_d * best_d
        for pi, pts in enumerate(self.polylines):
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                # Projection du point sur le segment
                abx, aby = b.x() - a.x(), b.y() - a.y()
                len2 = abx * abx + aby * aby
                if len2 < 1e-12:
                    continue
                t = ((local_pos.x() - a.x()) * abx + (local_pos.y() - a.y()) * aby) / len2
                t = max(0.0, min(1.0, t))
                proj = QPointF(a.x() + t * abx, a.y() + t * aby)
                dx, dy = local_pos.x() - proj.x(), local_pos.y() - proj.y()
                d = dx * dx + dy * dy
                if d < best_d:
                    best_d = d
                    best = (pi, i, proj)
        return best

    def delete_selected_node(self):
        """Supprime le nœud cliqué (drag_index) ; une polyligne de deux points disparaît entière, et
        l'objet s'il ne lui reste rien."""
        canvas = self.canvas
        if not self.active or self.drag_index is None:
            return False
        pi, vi = self.drag_index
        if pi >= len(self.polylines):
            return False
        pts = self.polylines[pi]
        if len(pts) <= 2:
            # Trop peu de points : supprimer toute la polyligne
            canvas.push_undo_snapshot()
            self.polylines.pop(pi)
            if not self.polylines:
                # Plus rien : supprimer l'objet
                item = self.target_item
                self.exit()
                if item is not None:
                    canvas.document.remove(item.obj)
                return True
            self.apply_polylines()
            return True
        canvas.push_undo_snapshot()
        pts.pop(vi)
        self.drag_index = None
        self.apply_polylines()
        return True

    # -- événements (mode nœuds actif)

    def press(self, event):
        """Clic gauche : début du glisser d'un sommet (un clic sur un segment ne fait rien)."""
        hit = self.hit_handle(self.canvas.mapToScene(event.position().toPoint()))
        if hit is not None:
            self.drag_index = hit
            self.drag_pushed_undo = False
        event.accept()

    def move(self, event):
        """Glisser d'un sommet. Renvoie True si l'événement est traité."""
        if not (self.active and self.drag_index is not None and event.buttons() & Qt.MouseButton.LeftButton):
            return False
        canvas = self.canvas
        if not self.drag_pushed_undo:
            canvas.push_undo_snapshot()
            self.drag_pushed_undo = True
        local = self.scene_to_local(canvas.mapToScene(event.position().toPoint()))
        pi, vi = self.drag_index
        if pi < len(self.polylines) and vi < len(self.polylines[pi]):
            self.polylines[pi][vi] = local
            # Mise à jour légère : tracé de l'objet + seule la poignée concernée
            item = self.target_item
            if item is not None and isinstance(item.obj, SvgPathObject):
                self._store_polylines()
                for h in self.handles:
                    data = h.data(0)
                    if data and data[0] == "node" and data[1] == pi and data[2] == vi:
                        r = self._handle_radius()
                        sp = self.local_to_scene(local)
                        h.setRect(sp.x() - r, sp.y() - r, 2 * r, 2 * r)
                        break
        event.accept()
        return True

    def release(self, event):
        if self.drag_index is not None:
            self.rebuild_handles()
            self.drag_index = None
            self.drag_pushed_undo = False
        event.accept()

    def double_click(self, event):
        """Double-clic sur un segment (pas sur un sommet) : ajoute un sommet. Renvoie True si traité."""
        if not (self.active and event.button() == Qt.MouseButton.LeftButton):
            return False
        scene_pos = self.canvas.mapToScene(event.position().toPoint())
        if self.hit_handle(scene_pos) is not None:
            return False
        hit = self.hit_segment(scene_pos)
        if hit is None:
            return False
        pi, after_i, proj = hit
        self.canvas.push_undo_snapshot()
        self.polylines[pi].insert(after_i + 1, proj)
        self.apply_polylines()
        event.accept()
        return True

    def delete_key(self):
        """Suppr / Retour arrière : supprime le sommet en cours de glisser, ou celui sous la souris."""
        if self.drag_index is not None:
            self.delete_selected_node()
            return
        scene_pos = self.canvas.mapToScene(self.canvas.mapFromGlobal(QCursor.pos()))
        hit = self.hit_handle(scene_pos)
        if hit is not None:
            self.drag_index = hit
            self.delete_selected_node()
