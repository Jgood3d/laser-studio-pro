"""Calque et taille d'un objet importé (AssignLayerDialog)."""
from PyQt6.QtWidgets import QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QDialog, QDialogButtonBox
from laser_studio.i18n import tr
from laser_studio.models.layers import LayersModel, layer_label

# Ancien nom du modèle des calques (models/layers.py).


class AssignLayerDialog(QDialog):
    """Boîte de dialogue pour un objet importé depuis un SVG : calque, et
    redimensionnement (largeur/hauteur en mm, avec conservation du ratio en
    option). Sa géométrie de base reste fixe — seuls son échelle, son calque,
    sa position et sa rotation sont modifiables (position/rotation via le
    panneau dédié de l'éditeur vectoriel)."""

    def __init__(self, layer_manager: LayersModel, svg_obj=None, current_layer_id=None,
                 title="Propriétés de l'élément SVG", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.svg_obj = svg_obj
        layout = QFormLayout(self)

        self.combo_layer = QComboBox()
        for l in layer_manager.layers:
            self.combo_layer.addItem(layer_label(l), l.id)
        lid = current_layer_id if current_layer_id is not None else (svg_obj.layer_id if svg_obj else None)
        if lid:
            idx = self.combo_layer.findData(lid)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        layout.addRow(tr("ui.vector_layer"), self.combo_layer)

        self.spin_w = None
        self.spin_h = None
        self._updating = False
        if svg_obj is not None:
            orig_bbox = svg_obj._local_path_data.boundingRect()
            self._orig_w = max(orig_bbox.width(), 1e-6)
            self._orig_h = max(orig_bbox.height(), 1e-6)
            cur_w = self._orig_w * getattr(svg_obj, "scale_x", 1.0)
            cur_h = self._orig_h * getattr(svg_obj, "scale_y", 1.0)
            self._ratio = cur_w / cur_h if cur_h > 0 else 1.0

            self.chk_keep_ratio = QCheckBox(tr("vector.dlg.keep_ratio"))
            self.chk_keep_ratio.setChecked(True)
            layout.addRow("", self.chk_keep_ratio)

            self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(0.1, 5000.0); self.spin_w.setDecimals(2)
            self.spin_w.setValue(cur_w); self.spin_w.setSuffix(" mm")
            self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(0.1, 5000.0); self.spin_h.setDecimals(2)
            self.spin_h.setValue(cur_h); self.spin_h.setSuffix(" mm")
            self.spin_w.valueChanged.connect(self._on_w_changed)
            self.spin_h.valueChanged.connect(self._on_h_changed)
            layout.addRow(tr("vector.dlg.width"), self.spin_w)
            layout.addRow(tr("vector.dlg.height"), self.spin_h)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_w_changed(self, val):
        if self._updating or not self.chk_keep_ratio.isChecked():
            return
        self._updating = True
        if self._ratio:
            self.spin_h.setValue(val / self._ratio)
        self._updating = False

    def _on_h_changed(self, val):
        if self._updating or not self.chk_keep_ratio.isChecked():
            return
        self._updating = True
        self.spin_w.setValue(val * self._ratio)
        self._updating = False

    def selected_layer_id(self):
        return self.combo_layer.currentData()

    def apply_to(self, svg_obj):
        """Applique le calque choisi et, si applicable, la nouvelle taille."""
        svg_obj.layer_id = self.selected_layer_id()
        if self.spin_w is not None:
            svg_obj.scale_x = self.spin_w.value() / self._orig_w
            svg_obj.scale_y = self.spin_h.value() / self._orig_h
