"""Accroche aux extrémités (et sommets) des tracés pendant le dessin et la mesure."""
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QBrush, QColor, QPen, QTransform
from PyQt6.QtWidgets import QGraphicsEllipseItem

from laser_studio.ui.vector_editor.item import VectorGraphicsItem


class EndpointSnap:
    """`canvas` : VectorCanvasView. `enabled`, `radius_px` : accroche active, rayon en pixels écran."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.enabled = True
        self.radius_px = 12.0
        self._indicator = None  # marqueur visuel du point d'accroche

    def _points(self):
        """Extrémités (et coins) de tous les objets vectoriels, en coords scène."""
        canvas = self.canvas
        pts = []
        for item in canvas.scene_obj.items():
            if not isinstance(item, VectorGraphicsItem):
                continue
            try:
                world = item.obj.world_path()
            except Exception:   # objet sans tracé calculable : rien à accrocher
                continue
            for poly in world.toSubpathPolygons(QTransform()):
                if poly.count() < 1:
                    continue
                # Extrémités de polyligne
                for idx in (0, poly.count() - 1):
                    p = poly.at(idx)
                    # world_path est déjà en mm monde Y-haut
                    pts.append(canvas.mm_to_scene(p.x(), p.y()))
                # Tous les sommets (utile pour repartir d'un coin d'encoche)
                for i in range(poly.count()):
                    p = poly.at(i)
                    pts.append(canvas.mm_to_scene(p.x(), p.y()))
        return pts

    def snap(self, scene_pos):
        """(position, accrochée ?) : scene_pos accrochée à l'extrémité / sommet le plus proche si dans le rayon."""
        if not self.enabled:
            return scene_pos, False
        view_scale = max(abs(self.canvas.transform().m11()), 0.01)
        max_d = self.radius_px / view_scale
        best = None
        best_d2 = max_d * max_d
        for p in self._points():
            dx = p.x() - scene_pos.x()
            dy = p.y() - scene_pos.y()
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = p
        if best is not None:
            return QPointF(best), True
        return scene_pos, False

    def show(self, scene_pos):
        view_scale = max(abs(self.canvas.transform().m11()), 0.01)
        r = 6.0 / view_scale
        if self._indicator is None:
            self._indicator = QGraphicsEllipseItem()
            self._indicator.setBrush(QBrush(QColor(255, 200, 0, 180)))
            self._indicator.setPen(QPen(QColor("#222222"), 0))
            self._indicator.setZValue(3000)
            self.canvas.scene_obj.addItem(self._indicator)
        self._indicator.setRect(scene_pos.x() - r, scene_pos.y() - r, 2 * r, 2 * r)
        self._indicator.setVisible(True)

    def hide(self):
        if self._indicator is not None:
            self._indicator.setVisible(False)

    def follow(self, scene_pos):
        """Position accrochée de scene_pos, repère montré si accrochée, caché sinon (survol, glissé)."""
        pos, snapped = self.snap(scene_pos)
        if snapped:
            self.show(pos)
        else:
            self.hide()
        return pos
