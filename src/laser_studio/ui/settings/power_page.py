"""Page « Alimentation » de la fenêtre Paramètres : empêcher la mise en veille.

    page = PowerPage(power_controller)
"""
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from laser_studio.controllers.power_inhibit import (
    MODE_DURING_JOB,
    MODE_NEVER,
    MODE_WHILE_CONNECTED,
)
from laser_studio.i18n import tr


class PowerPage(QWidget):
    """`power_controller` : PowerInhibitController."""

    def __init__(self, power_controller, parent=None):
        super().__init__(parent)
        self._power = power_controller

        box = QGroupBox(tr("settings.power"))
        form = QFormLayout(box)

        self.inhibit_mode = QComboBox()
        modes = [
            (MODE_DURING_JOB, tr("settings.power.during_job")),
            (MODE_WHILE_CONNECTED, tr("settings.power.while_connected")),
            (MODE_NEVER, tr("settings.power.never")),
        ]
        for code, label in modes:
            self.inhibit_mode.addItem(label, code)
        current = self._power.mode()
        idx = self.inhibit_mode.findData(current)
        if idx >= 0:
            self.inhibit_mode.setCurrentIndex(idx)
        self.inhibit_mode.setToolTip(tr("settings.power.mode_tip"))
        self.inhibit_mode.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow(tr("settings.power.inhibit"), self.inhibit_mode)

        mode_hint = QLabel(tr("settings.power.mode_hint"))
        mode_hint.setWordWrap(True)
        mode_hint.setEnabled(False)
        form.addRow("", mode_hint)

        self.keep_display = QCheckBox(tr("settings.power.keep_display"))
        self.keep_display.setChecked(self._power.keep_display())
        self.keep_display.setToolTip(tr("settings.power.keep_display_tip"))
        self.keep_display.toggled.connect(self._on_display_toggled)
        form.addRow("", self.keep_display)

        layout = QVBoxLayout(self)
        layout.addWidget(box)
        layout.addStretch()

    def _on_mode_changed(self, _index):
        self._power.set_mode(self.inhibit_mode.currentData())

    def _on_display_toggled(self, checked):
        self._power.set_keep_display(checked)
