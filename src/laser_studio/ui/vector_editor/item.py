"""Élément graphique d'un objet vectoriel sur le canevas (VectorGraphicsItem)."""
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen, QBrush, QTransform
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from laser_studio.models.layers import LayersModel
from laser_studio.models.vector_objects import VectorObject
from laser_studio.ui.app.theme import theme_color

if TYPE_CHECKING:  # annotation seulement : canvas importe ce module
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView  # noqa: F401

# Ancien nom du modèle des calques (models/layers.py).


class VectorGraphicsItem(QGraphicsPathItem):
    """QGraphicsItem qui représente un VectorObject sur le canevas (échelle px/mm).

    Le repère "monde" (VectorObject.world_transform) est bas-gauche / Y-haut,
    utilisé tel quel pour le G-Code. La scène Qt, elle, reste nativement
    Y-descendant (aucun flip au niveau de la QGraphicsView : fitInView() peut
    silencieusement annuler un flip posé sur la vue, ce qui cassait
    l'affichage). La conversion "monde -> écran" est donc calculée ici,
    objet par objet, directement dans la matrice de chaque item.
    """

    def __init__(self, obj: VectorObject, layer_manager: LayersModel, canvas: "VectorCanvasView"):
        super().__init__()
        self.obj = obj
        self.layer_manager = layer_manager
        self.canvas = canvas
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.double_click_callback = None  # défini par VectorCanvasView.add_object
        self._parts = []
        self._ghost = None
        self.inactive = False
        self.refresh()

    def mouseDoubleClickEvent(self, event):
        if self.double_click_callback:
            self.double_click_callback()
        super().mouseDoubleClickEvent(event)

    def refresh(self):
        """Recalcule la forme affichée (mm -> px, repère écran) à partir du VectorObject."""
        s = self.canvas.px_per_mm
        work_h_px = self.canvas.work_h_mm * s

        # Tracé affiché : un groupe n'y met pas ses objets masqués d'un œil.
        shown = getattr(self.obj, "display_local_path", self.obj.local_path)()
        local_path_px = QTransform().scale(s, s).map(shown)
        self.prepareGeometryChange()
        self.setPath(local_path_px)

        sx = -1.0 if self.obj.mirror_h else 1.0
        sy = 1.0 if self.obj.mirror_v else -1.0

        # Construit, dans une seule matrice, la transformation monde (position,
        # rotation, miroir) PUIS le passage bas-gauche/Y-haut -> écran Qt
        # Y-descendant. Avec QTransform, des appels .translate()/.rotate()/
        # .scale() enchaînés s'appliquent à un point dans l'ordre INVERSE des
        # appels : ci-dessous, un point est donc d'abord mis à l'échelle
        # (miroir), puis pivoté, puis positionné (repère monde), puis
        # seulement là le flip écran + décalage de hauteur sont appliqués.
        t = QTransform()
        t.translate(0, work_h_px)         # 5) décale pour repère écran Qt
        t.scale(1, -1)                    # 4) inverse Y : monde Y-haut -> écran Y-bas
        t.translate(self.obj.x_mm * s, self.obj.y_mm * s)  # 3) position (repère monde)
        t.rotate(self.obj.rotation_deg)   # 2) rotation
        t.scale(sx, sy)                   # 1) miroir éventuel
        self.setTransform(t)
        self.setPos(0, 0)
        # Masqué (œil) ou sur le calque « Ignoré » : plus dessiné, et la souris le traverse (shape vide) ; il
        # reste sélectionnable depuis la liste des objets, pour changer son calque (contour gris en pointillés).
        self.inactive = self.obj.is_hidden() or self.obj.is_ignored()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not self.inactive)
        self._ghost = None
        if self.inactive:
            full = getattr(self.obj, "full_local_path", self.obj.local_path)()
            self._ghost = QTransform().scale(s, s).map(full)

        pen = self._layer_pen(self.obj.layer_id)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        # Simple groupe : chaque objet dans la couleur de son calque (paint).
        parts = getattr(self.obj, "local_parts", lambda: [])()
        scale = QTransform().scale(s, s)
        self._parts = [(scale.map(path), self._layer_pen(layer)) for layer, path in parts]

    def _layer_pen(self, layer_id):
        layer = self.layer_manager.get(layer_id)
        pen = QPen(QColor(layer.color) if layer else QColor("#dddddd"), 1.4)
        pen.setCosmetic(True)
        return pen

    def shape(self):
        if self.inactive:
            return QPainterPath()
        return super().shape()

    def boundingRect(self):
        rect = super().boundingRect()
        return rect.united(self._ghost.boundingRect()) if self._ghost is not None else rect

    def paint(self, painter, option, widget=None):
        if self.inactive:
            if self.isSelected() and self._ghost is not None:
                ghost = QPen(QColor("#9a9a9a"), 1.2, Qt.PenStyle.DashLine)
                ghost.setCosmetic(True)
                painter.setPen(ghost)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(self._ghost)
            return
        if not self._parts:
            super().paint(painter, option, widget)
            return
        for path, pen in self._parts:
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        if self.isSelected():
            # Cadre de sélection, comme QGraphicsPathItem.
            selection = QPen(theme_color("canvas_selection", "#ffffff"), 1, Qt.PenStyle.DashLine)
            selection.setCosmetic(True)
            painter.setPen(selection)
            painter.drawRect(self.boundingRect())

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged:
            pass
        return super().itemChange(change, value)
