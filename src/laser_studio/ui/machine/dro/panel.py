"""Position de la machine (DRO) : état GRBL et coordonnées X, Y, Z."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout

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

# Style des valeurs : chasse fixe, pour que les chiffres restent alignés.
VALUE_STYLE = "font-family: monospace; font-size: 13px;"
NO_VALUE = "—"


class DroPanel(QGroupBox):
    """Affichage de l'état de la machine et de sa position (DRO).

    Il ne lit pas la machine : la fenêtre (plus tard un contrôleur) lui
    transmet chaque état reçu par set_status(). Le bouton « Déverrouiller »
    n'apparaît qu'en alarme, et émet unlock_requested :

        panel = DroPanel()
        panel.unlock_requested.connect(laser.unlock_alarm)
        panel.set_status("Idle", 12.5, 30.0, 0.0)
    """

    unlock_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(tr("ui.dro_box"), parent)
        self.state_label = self._value_label(tr("ui.dro_state"))
        self.x_label = self._value_label(tr("ui.dro_x"))
        self.y_label = self._value_label(tr("ui.dro_y"))
        self.z_label = self._value_label(tr("ui.dro_z"))
        self.unlock_button = self._unlock_button()
        layout = QVBoxLayout(self)
        layout.addWidget(self.state_label)
        layout.addWidget(self.unlock_button)
        layout.addWidget(self.x_label)
        layout.addWidget(self.y_label)
        layout.addWidget(self.z_label)
        layout.addStretch()

    # -- état reçu de la fenêtre / du contrôleur

    def set_status(self, state, x=0.0, y=0.0, z=0.0):
        """Affiche l'état GRBL et la position, en mm.

        `state` à None (graveur déconnecté) : plus de position connue, des
        tirets s'affichent à la place des valeurs.
        """
        if state is None:
            self.state_label.setText(tr("ui.dro_state").format(value=NO_VALUE))
            for label, key in self._axes():
                label.setText(tr(key).format(value=NO_VALUE))
            self.unlock_button.setVisible(False)
            # Plus d'état connu : gris, comme un état inconnu.
            self.state_label.setStyleSheet(
                f"color: {UNKNOWN_STATE_COLOR}; font-weight: bold;"
            )
            return
        self.state_label.setText(tr("ui.dro_state").format(value=state))
        for (label, key), value in zip(self._axes(), (x, y, z)):
            label.setText(tr(key).format(value=f"{value:.3f}"))
        # Le bouton apparaît de lui-même dès que l'état Alarm est détecté
        # (ex. fin de course déclenchée) et disparaît dès que l'état change :
        # jamais de déverrouillage automatique sans action volontaire.
        self.unlock_button.setVisible(state == "Alarm")
        color = STATE_COLORS.get(state, UNKNOWN_STATE_COLOR)
        self.state_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def minimum_content_width(self):
        """Largeur de la plus longue valeur, ex. « X : -1000.000 mm »."""
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPixelSize(13)
        return (
            QFontMetrics(mono).horizontalAdvance(
                tr("ui.dro_x").format(value="-1000.000")
            )
            + 40
        )

    # -- construction

    def _axes(self):
        return (
            (self.x_label, "ui.dro_x"),
            (self.y_label, "ui.dro_y"),
            (self.z_label, "ui.dro_z"),
        )

    @staticmethod
    def _value_label(template):
        """Libellé à chasse fixe, sans valeur au départ."""
        label = QLabel(template.format(value=NO_VALUE))
        label.setStyleSheet(VALUE_STYLE)
        return label

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
