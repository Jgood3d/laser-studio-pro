"""Panneau des propriétés de la sélection, sous le canevas de l'éditeur
vectoriel : description, position X / Y, rotation, calque, et pour une forme
seule largeur / hauteur avec point d'ancrage.

Les widgets sont construits par la fenêtre ; ce panneau les remplit d'après
la sélection (refresh) et transmet les saisies au contrôleur de l'éditeur
(VectorEditorController), qui modifie le document.

    panel = VectorPropertiesPanel(widgets, layers, canvas, editor)
    canvas.selection_changed.connect(panel.refresh)
"""
from dataclasses import dataclass

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QLabel, QWidget

from laser_studio.i18n import tr
from laser_studio.models.layers import layer_label
from laser_studio.models.vector_objects import GroupObject, SvgPathObject, TextObject
from laser_studio.vector import arrange


@dataclass
class PropertiesWidgets:
    """Widgets du panneau, construits par la fenêtre."""
    label: QLabel                 # description de la sélection
    box: QWidget                  # cadre « Position », masqué sans sélection
    x: QDoubleSpinBox
    y: QDoubleSpinBox
    rotation: QDoubleSpinBox
    layer: QComboBox
    size_row: QWidget             # largeur / hauteur / ancrage (forme seule)
    width: QDoubleSpinBox
    height: QDoubleSpinBox
    anchor_lock: QCheckBox
    anchor: QComboBox


class VectorPropertiesPanel(QObject):
    """Remplit le panneau d'après la sélection du canevas et transmet les
    saisies au contrôleur de l'éditeur."""

    def __init__(self, widgets, layers, canvas, editor, parent=None):
        super().__init__(parent)
        self.w = widgets
        self.layers = layers
        self.canvas = canvas
        self.editor = editor
        widgets.x.valueChanged.connect(self.on_position_changed)
        widgets.y.valueChanged.connect(self.on_position_changed)
        widgets.rotation.valueChanged.connect(self.on_position_changed)
        widgets.layer.currentIndexChanged.connect(self.on_layer_changed)
        widgets.width.valueChanged.connect(self.on_size_changed)
        widgets.height.valueChanged.connect(self.on_size_changed)
        canvas.selection_changed.connect(self.refresh)
        canvas.object_moved.connect(self.on_object_moved)
        editor.properties_changed.connect(self.refresh)

    @staticmethod
    def _set_quietly(spin, value):
        spin.blockSignals(True)
        spin.setValue(value)
        spin.blockSignals(False)

    def refresh(self, _obj=None):
        """Remet le panneau d'accord avec la sélection du canevas."""
        w = self.w
        objects = [item.obj for item in self.canvas.selected_items_vector()]
        if not objects:
            w.label.setText(tr("ui.no_selection_label"))
            w.box.setEnabled(False)
            w.box.setVisible(False)
            w.size_row.setVisible(False)
            return

        group_left, group_bottom, group_right, group_top = arrange.group_bounds(objects)
        if len(objects) > 1:
            desc = (
                f"{len(objects)} objets sélectionnés — "
                f"Zone : {group_right - group_left:.2f} × "
                f"{group_top - group_bottom:.2f} mm"
            )
        else:
            obj = objects[0]
            layer = self.layers.get(obj.layer_id)
            layer_name = layer.name if layer else "?"
            if isinstance(obj, TextObject):
                desc = (
                    f"Texte : « {obj.text} » — "
                    f"police {obj.font_family}, {obj.size_mm:.1f} mm — "
                    f"Calque : {layer_name}"
                )
            elif isinstance(obj, GroupObject):
                desc = tr("objects.group_desc").format(
                    operation=tr(f"objects.op.{obj.operation}"), n=len(obj.children), layer=layer_name)
            elif isinstance(obj, SvgPathObject):
                desc = f"Élément SVG importé ({obj.source_tag}) — Calque : {layer_name}"
            else:
                desc = (
                    f"Forme : {obj.shape_type} "
                    f"({obj.width_mm:.1f} × {obj.height_mm:.1f} mm) — "
                    f"Calque : {layer_name}"
                )
        w.label.setText(desc)
        w.box.setEnabled(True)
        w.box.setVisible(True)

        spins = (w.x, w.y, w.rotation, w.width, w.height)
        for spin in spins:
            spin.blockSignals(True)
        # X/Y : coin inférieur gauche du groupe
        w.x.setValue(group_left)
        w.y.setValue(group_bottom)
        w.rotation.setValue(objects[0].rotation_deg)
        # Largeur / hauteur / ancrage : uniquement pour une forme (pas SVG ni texte)
        can_size = (
            len(objects) == 1
            and hasattr(objects[0], "width_mm")
            and hasattr(objects[0], "height_mm")
            and getattr(objects[0], "kind", None) == "shape"
        )
        w.size_row.setVisible(can_size)
        if can_size:
            w.width.setValue(float(objects[0].width_mm))
            w.height.setValue(float(objects[0].height_mm))
        for spin in spins:
            spin.blockSignals(False)

        w.layer.blockSignals(True)
        w.layer.clear()
        for layer in self.layers.layers:
            w.layer.addItem(layer_label(layer), layer.id)
        if len(objects) == 1:
            idx = w.layer.findData(objects[0].layer_id)
            if idx >= 0:
                w.layer.setCurrentIndex(idx)
        w.layer.blockSignals(False)

    def on_layer_changed(self, _index):
        self.editor.set_selected_layer(self.w.layer.currentData())

    def on_object_moved(self, obj):
        """Objet déplacé à la souris : X / Y mis à jour sans redéclencher
        on_position_changed (boucle de signaux)."""
        if self.w.box.isEnabled():
            self._set_quietly(self.w.x, obj.x_mm)
            self._set_quietly(self.w.y, obj.y_mm)

    def on_position_changed(self, _value):
        """Déplace l'objet ou le groupe sélectionné vers la position saisie."""
        self.editor.move_selection_to(self.w.x.value(), self.w.y.value(), self.w.rotation.value())

    def on_size_changed(self, _value):
        """Largeur / hauteur d'une forme ; avec l'ancrage verrouillé, le coin
        choisi (ou l'origine = 1er point) reste fixe."""
        w = self.w
        anchor_id = None
        if w.anchor_lock.isChecked():
            anchor_id = w.anchor.currentData() or "origin"
        obj = self.editor.resize_selected_shape(w.width.value(), w.height.value(), anchor_id)
        if obj is not None:
            # X / Y affichés sans reboucler sur les champs de taille
            self._set_quietly(w.x, obj.x_mm)
            self._set_quietly(w.y, obj.y_mm)
