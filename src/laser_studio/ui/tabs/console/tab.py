"""Onglet « Console / G-Code »."""

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from laser_studio.i18n import tr

# Lignes ajoutées à chaque tour de la boucle d'événements quand la console se remplit d'un gros G-Code
# (~35 ms par paquet) : 500 000 lignes d'un coup figeaient l'interface près d'une seconde.
FILL_CHUNK_LINES = 20_000


class ConsoleTab(QWidget):
    """Console : G-Code généré (ou importé), et rien d'autre.

    `console_edit` est relu par l'export et la file d'attente : les messages
    des actions vont dans la barre d'état (log_message). Les statistiques du job
    sont à droite de l'aperçu 2D (JobStatsPanel), et l'enregistrement du
    G-Code dans le menu Fichier. L'onglet est masqué au démarrage
    (menu Affichage). Le plein écran est celui de la barre principale.

    Un gros G-Code remplit la console par paquets, en tâche de fond, sans figer l'interface ; pendant ce
    temps elle est en lecture seule et gcode() rend déjà le texte complet.

        tab = ConsoleTab()
        tab.set_gcode(gcode)
        tab.gcode()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(QLabel(tr("ui.generated_console_label")))
        self.console_edit = QPlainTextEdit()
        self.console_edit.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.console_edit)
        self._filling = None              # (texte complet, paquets restants) pendant un remplissage
        self._fill_timer = QTimer(self)
        self._fill_timer.setInterval(0)
        self._fill_timer.timeout.connect(self._fill_next)

    def gcode(self):
        """G-Code affiché (relu par l'export, la file d'attente et l'envoi au laser), complet même pendant
        que la console se remplit."""
        if self._filling is not None:
            return self._filling[0]
        return self.console_edit.toPlainText()

    def set_gcode(self, text):
        self._fill_timer.stop()
        lines = text.split("\n")
        if len(lines) <= FILL_CHUNK_LINES:
            self._filling = None
            self.console_edit.setReadOnly(False)
            self.console_edit.setPlainText(text)
            return
        chunks = ["\n".join(lines[i:i + FILL_CHUNK_LINES]) for i in range(0, len(lines), FILL_CHUNK_LINES)]
        chunks.reverse()                  # pop() depuis la fin : le premier paquet d'abord
        self._filling = (text, chunks)
        self.console_edit.setReadOnly(True)
        self.console_edit.setPlainText(chunks.pop())
        self._fill_timer.start()

    def is_filling(self):
        return self._filling is not None

    def _fill_next(self):
        _text, chunks = self._filling
        self.console_edit.appendPlainText(chunks.pop())
        if not chunks:
            self._fill_timer.stop()
            self._filling = None
            self.console_edit.setReadOnly(False)
