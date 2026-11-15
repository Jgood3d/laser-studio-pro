"""Console directe : envoi d'une commande GRBL tapée à la main."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.widgets import HistoryLineEdit


class DirectConsolePanel(QWidget):
    """Champ de commande GRBL avec historique, et bouton « Envoyer ».

    Sans cadre : il est placé dans le panneau « Connexion », sous l'état
    de la machine.

    Il n'envoie rien à la machine : à l'appui sur Entrée ou au clic, il
    émet command_submitted avec la commande (sans espaces autour, jamais
    vide), l'ajoute à l'historique (flèches Haut / Bas) et vide le champ.

        panel = DirectConsolePanel()
        panel.command_submitted.connect(laser.send_console_command)
    """

    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_edit = self._command_edit()
        send_button = QPushButton(tr("ui.manual_send"))
        send_button.clicked.connect(self._submit)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.command_edit)
        layout.addWidget(send_button)

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Déverrouille la console si le graveur est connecté."""
        self.setEnabled(connected)

    # -- construction et signaux

    def _command_edit(self):
        edit = HistoryLineEdit()
        edit.setPlaceholderText(tr("ui.manual_grbl_placeholder"))
        edit.returnPressed.connect(self._submit)
        return edit

    def _submit(self):
        """Émet la commande saisie ; une saisie vide ne fait rien."""
        command = self.command_edit.text().strip()
        if not command:
            return
        self.command_edit.add_to_history(command)
        self.command_edit.clear()
        self.command_submitted.emit(command)
