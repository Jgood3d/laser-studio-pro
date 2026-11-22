"""Boîte d'insertion et de modification d'une forme (ShapeInsertDialog)."""
from PyQt6.QtWidgets import (
    QHBoxLayout, QFormLayout, QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QDialog, QDialogButtonBox,
)
from laser_studio.i18n import tr
from laser_studio.models.layers import LayersModel, layer_label
from laser_studio.models.vector_objects import ShapeObject

# Ancien nom du modèle des calques (models/layers.py).
LayerManager = LayersModel


class ShapeInsertDialog(QDialog):
    """Boîte de dialogue pour insérer OU modifier une forme géométrique."""

    def __init__(self, layer_manager: LayerManager, shape_obj: "ShapeObject" = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("vector.dlg.shape_title_new") if shape_obj is None else tr("vector.dlg.shape_title_edit"))
        self.layer_manager = layer_manager
        self.editing = shape_obj

        layout = QFormLayout(self)

        self.combo_type = QComboBox()
        self.combo_type.addItems(ShapeObject.SHAPE_TYPES)
        if shape_obj:
            self.combo_type.setCurrentText(shape_obj.shape_type)
        layout.addRow(tr("vector.dlg.shape_type"), self.combo_type)

        self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(0.5, 1000.0)
        self.spin_w.setValue(shape_obj.width_mm if shape_obj else 20.0); self.spin_w.setSuffix(" mm")
        self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(0.5, 1000.0)
        self.spin_h.setValue(shape_obj.height_mm if shape_obj else 15.0); self.spin_h.setSuffix(" mm")
        layout.addRow(tr("vector.dlg.width"), self.spin_w)
        layout.addRow(tr("vector.dlg.height"), self.spin_h)

        self.spin_sides = QSpinBox(); self.spin_sides.setRange(3, 24)
        self.spin_sides.setValue(shape_obj.sides if shape_obj else 6)
        layout.addRow(tr("vector.dlg.sides"), self.spin_sides)

        self.combo_layer = QComboBox()
        for l in self.layer_manager.layers:
            self.combo_layer.addItem(layer_label(l), l.id)
        if shape_obj and shape_obj.layer_id:
            idx = self.combo_layer.findData(shape_obj.layer_id)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        layout.addRow(tr("ui.vector_layer"), self.combo_layer)

        pos_row = QHBoxLayout()
        self.spin_x = QDoubleSpinBox(); self.spin_x.setRange(-1000.0, 1000.0)
        self.spin_x.setDecimals(2); self.spin_x.setSuffix(" mm")
        self.spin_x.setValue(shape_obj.x_mm if shape_obj else 10.0)
        self.spin_y = QDoubleSpinBox(); self.spin_y.setRange(-1000.0, 1000.0)
        self.spin_y.setDecimals(2); self.spin_y.setSuffix(" mm")
        self.spin_y.setValue(shape_obj.y_mm if shape_obj else 10.0)
        pos_row.addWidget(QLabel("X :")); pos_row.addWidget(self.spin_x)
        pos_row.addWidget(QLabel("Y :")); pos_row.addWidget(self.spin_y)
        layout.addRow(tr("vector.dlg.corner_pos"), pos_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_object(self) -> ShapeObject:
        layer_id = self.combo_layer.currentData()
        if self.editing:
            obj = self.editing
        else:
            obj = ShapeObject(layer_id=layer_id)
        obj.shape_type = self.combo_type.currentText()
        obj.width_mm = self.spin_w.value()
        obj.height_mm = self.spin_h.value()
        obj.sides = self.spin_sides.value()
        obj.layer_id = layer_id
        obj.x_mm = self.spin_x.value()
        obj.y_mm = self.spin_y.value()
        return obj
