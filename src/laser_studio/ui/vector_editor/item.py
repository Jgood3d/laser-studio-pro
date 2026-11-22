"""Élément graphique d'un objet vectoriel sur le canevas (VectorGraphicsItem)."""
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen, QBrush, QTransform
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from laser_studio.models.layers import LayersModel
from laser_studio.models.vector_objects import VectorObject

if TYPE_CHECKING:  # annotation seulement : canvas importe ce module
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView  # noqa: F401

# Ancien nom du modèle des calques (models/layers.py).
LayerManager = LayersModel


class VectorGraphicsItem(QGraphicsPathItem):
    """QGraphicsItem qui représente un VectorObject sur le canevas (échelle px/mm).

    Le repère "monde" (VectorObject.world_transform) est bas-gauche / Y-haut,
    utilisé tel quel pour le G-Code. La scène Qt, elle, reste nativement
    Y-descendant (aucun flip au niveau de la QGraphicsView : fitInView() peut
    silencieusement annuler un flip posé sur la vue, ce qui cassait
    l'affichage). La conversion "monde -> écran" est donc calculée ici,
    objet par objet, directement dans la matrice de chaque item.
    """

    def __init__(self, obj: VectorObject, layer_manager: LayerManager, canvas: "VectorCanvasView"):
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
        self.refresh()

    def mouseDoubleClickEvent(self, event):
        if self.double_click_callback:
            self.double_click_callback()
        super().mouseDoubleClickEvent(event)

    def refresh(self):
        """Recalcule la forme affichée (mm -> px, repère écran) à partir du VectorObject."""
        s = self.canvas.px_per_mm
        work_h_px = self.canvas.work_h_mm * s

        local_path_px = QTransform().scale(s, s).map(self.obj.local_path())
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

        layer = self.layer_manager.get(self.obj.layer_id)
        color = QColor(layer.color) if layer else QColor("#dddddd")
        pen = QPen(color, 1.4)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged:
            pass
        return super().itemChange(change, value)

    def sync_position_from_scene(self):
        """À appeler après un déplacement souris : remet x_mm/y_mm à jour à
        partir de la position écran (en tenant compte du flip Y bas-gauche)."""
        pos = self.scenePos()
        s = self.canvas.px_per_mm
        work_h_px = self.canvas.work_h_mm * s
        self.obj.x_mm = pos.x() / s
        self.obj.y_mm = (work_h_px - pos.y()) / s
