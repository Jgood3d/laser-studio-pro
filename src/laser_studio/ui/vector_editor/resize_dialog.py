"""Boîte « Redimensionner… » du menu contextuel : nouvelle largeur et hauteur du groupe sélectionné, en mm,
proportions liées ou non."""
from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel

from laser_studio.i18n import tr


class GroupResizeDialog(QDialog):
    def __init__(self, width_mm, height_mm, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("vector.dlg.resize_title"))
        layout = QFormLayout(self)
        layout.addRow(QLabel(tr("vector.dlg.group_size").format(w=width_mm, h=height_mm)))

        self.keep_ratio = QCheckBox(tr("vector.dlg.keep_ratio"))
        self.keep_ratio.setChecked(True)
        layout.addRow("", self.keep_ratio)

        self.spin_w = self._spin(width_mm)
        self.spin_h = self._spin(height_mm)
        layout.addRow(tr("vector.dlg.new_width"), self.spin_w)
        layout.addRow(tr("vector.dlg.new_height"), self.spin_h)

        self._ratio = width_mm / height_mm if height_mm else 1.0
        self._updating = False
        self.spin_w.valueChanged.connect(self._width_changed)
        self.spin_h.valueChanged.connect(self._height_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @staticmethod
    def _spin(value):
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 5000.0)
        spin.setDecimals(2)
        spin.setValue(value)
        spin.setSuffix(" mm")
        return spin

    def _width_changed(self, value):
        if self._updating or not self.keep_ratio.isChecked():
            return
        self._updating = True
        self.spin_h.setValue(value / self._ratio if self._ratio else value)
        self._updating = False

    def _height_changed(self, value):
        if self._updating or not self.keep_ratio.isChecked():
            return
        self._updating = True
        self.spin_w.setValue(value * self._ratio)
        self._updating = False

    def size_mm(self):
        return self.spin_w.value(), self.spin_h.value()
