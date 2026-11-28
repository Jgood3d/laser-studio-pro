"""Page « Langue et thème » de la fenêtre Paramètres : listes déroulantes
langue / thème, et options d'alimentation (mise en veille).

    page = AppearancePage(actions.language_actions, actions.theme_actions,
                          power_controller=power_inhibit_controller)
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


class AppearancePage(QWidget):
    """`language_actions`, `theme_actions` : {code: QAction cochable}, dans l'ordre d'affichage.
    `power_controller` : PowerInhibitController (optionnel ; sans lui, les réglages
    d'alimentation ne sont pas affichés)."""

    def __init__(self, language_actions, theme_actions, power_controller=None, parent=None):
        super().__init__(parent)
        self._power = power_controller
        layout = QVBoxLayout(self)

        box = QGroupBox(tr("settings.appearance"))
        form = QFormLayout(box)
        self.language = self._combo(language_actions)
        self.theme = self._combo(theme_actions)
        form.addRow(tr("menu.language"), self.language)
        hint = QLabel(tr("settings.language_hint"))
        hint.setWordWrap(True)
        hint.setEnabled(False)                       # texte d'aide, en gris
        form.addRow("", hint)
        form.addRow(tr("menu.theme"), self.theme)
        layout.addWidget(box)

        if power_controller is not None:
            layout.addWidget(self._build_power_box())

        layout.addStretch()

    def _build_power_box(self):
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

        return box

    def _on_mode_changed(self, _index):
        if self._power is None:
            return
        self._power.set_mode(self.inhibit_mode.currentData())

    def _on_display_toggled(self, checked):
        if self._power is None:
            return
        self._power.set_keep_display(checked)

    @staticmethod
    def _combo(actions):
        """Liste des actions : choisir une entrée déclenche son action ; l'action cochée ailleurs (contrôleur)
        est reprise dans la liste."""
        combo = QComboBox()
        for code, action in actions.items():
            combo.addItem(action.text(), code)
            if action.isChecked():
                combo.setCurrentIndex(combo.count() - 1)

        def follow(code, checked):
            if checked and combo.currentData() != code:
                blocked = combo.blockSignals(True)
                combo.setCurrentIndex(combo.findData(code))
                combo.blockSignals(blocked)

        for code, action in actions.items():
            action.toggled.connect(lambda checked, c=code: follow(c, checked))
        combo.activated.connect(lambda index: actions[combo.itemData(index)].trigger())
        return combo
