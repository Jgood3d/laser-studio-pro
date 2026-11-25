"""Page « Langue et thème » de la fenêtre Paramètres : deux listes déroulantes, reliées aux actions de langue et
de thème d'AppActions (qui émettent `language_selected` / `theme_selected` et restent cochées sur le choix en
cours ; WindowController.change_theme et select_language les mettent à jour).

    page = AppearancePage(actions.language_actions, actions.theme_actions)
"""
from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from laser_studio.i18n import tr


class AppearancePage(QWidget):
    """`language_actions`, `theme_actions` : {code: QAction cochable}, dans l'ordre d'affichage."""

    def __init__(self, language_actions, theme_actions, parent=None):
        super().__init__(parent)
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
        layout = QVBoxLayout(self)
        layout.addWidget(box)
        layout.addStretch()

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
