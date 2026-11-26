"""Cadre « Position du job sur le plateau », dans l'onglet Visualisation 2D : origine du repère et décalage."""

from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox

from laser_studio.core.constants import ORIGIN_BOTTOM_LEFT, ORIGIN_CENTER
from laser_studio.i18n import tr
from laser_studio.ui.binding import bind

# Code de chaque choix, dans l'ordre de la liste, et sa clé de traduction.
ORIGIN_CHOICES = (
    (ORIGIN_BOTTOM_LEFT, "ui.origin_bottom_left"),
    (ORIGIN_CENTER, "ui.origin_center"),
)


class JobPositionBox(QGroupBox):
    """Origine du repère du job (bas-gauche ou centre) et décalage X / Y, réunis là où l'on voit le job sur
    le plateau. Les champs sont liés au modèle JobPlacement, où le code les lit :

        box = JobPositionBox()
        box.bind_placement(placement)
    """

    def __init__(self, parent=None):
        super().__init__(tr("ui.job_position_box"), parent)
        layout = QFormLayout(self)
        self.origin_combo = QComboBox()
        for code, key in ORIGIN_CHOICES:
            self.origin_combo.addItem(tr(key), code)
        layout.addRow(tr("dim.origin"), self.origin_combo)
        self.offset_x_spin = self._spin()
        self.offset_y_spin = self._spin()
        layout.addRow(tr("dim.offset_x"), self.offset_x_spin)
        layout.addRow(tr("dim.offset_y"), self.offset_y_spin)

    @staticmethod
    def _spin():
        spin = QDoubleSpinBox()
        spin.setRange(-1000.0, 1000.0)
        return spin

    def bind_placement(self, placement):
        """Lie l'origine (par code, quelle que soit la langue affichée) et le décalage à `placement`."""
        combo = self.origin_combo
        bind(combo, placement, "origin", to_widget=combo.findData, from_widget=combo.itemData)
        bind(self.offset_x_spin, placement, "offset_x")
        bind(self.offset_y_spin, placement, "offset_y")
