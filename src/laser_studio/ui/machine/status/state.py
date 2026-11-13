"""État GRBL de la machine, et déverrouillage en alarme."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from laser_studio.i18n import tr

# Couleur du libellé d'état selon l'état GRBL, gris pour un état inconnu.
STATE_COLORS = {
    "Idle": "#2ecc71",
    "Run": "#3498db",
    "Hold": "#e67e22",
    "Alarm": "#e74c3c",
    "Home": "#9b59b6",
    "Jog": "#1abc9c",
}
UNKNOWN_STATE_COLOR = "#cccccc"
NO_VALUE = "—"


class MachineStateView(QWidget):
    """Libellé de l'état GRBL (« État : Idle »), coloré selon l'état.

    Il ne lit pas la machine : la fenêtre (plus tard un contrôleur) lui
    transmet chaque état reçu par set_state(). Le bouton « Déverrouiller »
    n'apparaît qu'en alarme, et émet unlock_requested :

        view = MachineStateView()
        view.unlock_requested.connect(laser.unlock_alarm)
        view.set_state("Alarm")
    """

    unlock_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_label = QLabel()
        self.unlock_button = self._unlock_button()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.state_label)
        layout.addWidget(self.unlock_button)
        self.set_state(None)

    def set_state(self, state):
        """Affiche l'état GRBL ; None (graveur déconnecté) : un tiret gris."""
        self.state_label.setText(
            tr("ui.dro_state").format(value=NO_VALUE if state is None else state)
        )
        color = STATE_COLORS.get(state, UNKNOWN_STATE_COLOR)
        self.state_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        # Le bouton apparaît de lui-même dès que l'état Alarm est détecté
        # (ex. fin de course déclenchée) et disparaît dès que l'état change :
        # jamais de déverrouillage automatique sans action volontaire.
        self.unlock_button.setVisible(state == "Alarm")

    def _unlock_button(self):
        """Bouton rouge « Déverrouiller », masqué hors alarme."""
        button = QPushButton(tr("ui.unlock_alarm"))
        button.setStyleSheet(
            "background-color: #c0392b; color: white; "
            "font-weight: bold; padding: 3px 10px;"
        )
        button.clicked.connect(self.unlock_requested)
        button.setVisible(False)
        return button
