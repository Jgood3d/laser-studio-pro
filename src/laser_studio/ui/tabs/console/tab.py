"""Onglet « Console / G-Code »."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.widgets import TabToolBar


class ConsoleTab(QWidget):
    """Console : G-Code généré, et messages de l'application et du graveur.

    Toute l'application écrit dans `console_edit`. Les statistiques du job
    sont dans le panneau machine (JobStatsPanel), et l'enregistrement du
    G-Code dans le menu Fichier. L'onglet est masqué au démarrage
    (menu Affichage).

        tab = ConsoleTab()
        tab.fullscreen_requested.connect(self.toggle_fullscreen)
    """

    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._toolbar())
        layout.addWidget(QLabel(tr("ui.generated_console_label")))
        self.console_edit = QTextEdit()
        self.console_edit.setFontFamily("Courier")
        layout.addWidget(self.console_edit)

    # -- construction

    def _toolbar(self):
        toolbar = TabToolBar(self)
        toolbar.fullscreen_requested.connect(self.fullscreen_requested)
        self._fullscreen_control = toolbar.fullscreen_action
        return toolbar
