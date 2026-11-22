"""Textes d'une médaille, en haut et en bas d'un contour fermé (MedalTextDialog)."""
from PyQt6.QtWidgets import (
    QHBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QDialog, QDialogButtonBox, QLineEdit,
    QFontComboBox,
)
from laser_studio.i18n import tr
from laser_studio.models.layers import LayersModel, layer_label

# Ancien nom du modèle des calques (models/layers.py).
LayerManager = LayersModel


class MedalTextDialog(QDialog):
    """Texte de médaille : un texte en haut et un en bas, à l'intérieur du contour fermé sélectionné."""

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("vector.medal_title"))
        layout = QFormLayout(self)
        self.edit_top = QLineEdit()
        layout.addRow(tr("vector.medal.top"), self.edit_top)
        self.edit_bottom = QLineEdit()
        layout.addRow(tr("vector.medal.bottom"), self.edit_bottom)
        self.combo_font = QFontComboBox()
        layout.addRow(tr("vector.dlg.font"), self.combo_font)
        style_row = QHBoxLayout()
        self.chk_bold = QCheckBox(tr("vector.dlg.bold"))
        self.chk_italic = QCheckBox(tr("vector.dlg.italic"))
        style_row.addWidget(self.chk_bold); style_row.addWidget(self.chk_italic)
        layout.addRow(tr("vector.dlg.style"), style_row)
        self.spin_size = QDoubleSpinBox(); self.spin_size.setRange(1.0, 200.0)
        self.spin_size.setValue(6.0); self.spin_size.setSuffix(" mm")
        layout.addRow(tr("vector.dlg.size_height"), self.spin_size)
        self.spin_margin = QDoubleSpinBox(); self.spin_margin.setRange(0.0, 50.0)
        self.spin_margin.setDecimals(1); self.spin_margin.setValue(2.0); self.spin_margin.setSuffix(" mm")
        layout.addRow(tr("vector.medal.margin"), self.spin_margin)
        self.combo_layer = QComboBox()
        for l in layer_manager.layers:
            self.combo_layer.addItem(layer_label(l), l.id)
        engrave = layer_manager.engrave_layer()
        idx = self.combo_layer.findData(engrave.id) if engrave is not None else -1
        if idx >= 0:
            self.combo_layer.setCurrentIndex(idx)
        layout.addRow(tr("ui.vector_layer"), self.combo_layer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_text)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _accept_if_text(self):
        if self.edit_top.text().strip() or self.edit_bottom.text().strip():
            self.accept()

    def values(self):
        """Arguments de VectorCanvasView.make_medal_texts."""
        return dict(top_text=self.edit_top.text(), bottom_text=self.edit_bottom.text(),
                    font_family=self.combo_font.currentFont().family(), size_mm=self.spin_size.value(),
                    margin_mm=self.spin_margin.value(), layer_id=self.combo_layer.currentData(),
                    bold=self.chk_bold.isChecked(), italic=self.chk_italic.isChecked())
