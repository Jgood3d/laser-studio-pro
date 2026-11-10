"""Commandes temps réel du panneau de pilotage, et l'envoi du job."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QGridLayout, QStyle, QWidget

from i18n import tr
from ui.utils import themed_icon, tool_button


class RealtimeCommands(QWidget):
    """Pause, reprise, reset et arrêt d'urgence sur une ligne, l'envoi du
    job dessous. Chaque bouton émet son signal ; l'envoi se désactive
    pendant un envoi en cours (set_send_enabled)."""

    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    emergency_stop_requested = pyqtSignal()
    send_job_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        commands = (
            (
                QIcon.ThemeIcon.MediaPlaybackPause,
                QStyle.StandardPixmap.SP_MediaPause,
                "ui.pause",
                "#e67e22",
                self.pause_requested,
            ),
            (
                QIcon.ThemeIcon.MediaPlaybackStart,
                QStyle.StandardPixmap.SP_MediaPlay,
                "ui.resume",
                "#27ae60",
                self.resume_requested,
            ),
            (
                QIcon.ThemeIcon.SystemReboot,
                QStyle.StandardPixmap.SP_BrowserReload,
                "ui.reset",
                "#c0392b",
                self.reset_requested,
            ),
            (
                QIcon.ThemeIcon.ProcessStop,
                QStyle.StandardPixmap.SP_BrowserStop,
                "ui.kill",
                "#ff0000",
                self.emergency_stop_requested,
            ),
        )
        for col, (icon, fallback, key, color, signal) in enumerate(commands):
            button = tool_button(
                themed_icon(self, icon, fallback), tr(key), color
            )
            button.clicked.connect(signal)
            grid.addWidget(button, 0, col)
        # Envoi du job : ligne à part, sous les commandes temps réel.
        self.send_button = tool_button(
            themed_icon(
                self,
                QIcon.ThemeIcon.DocumentSend,
                QStyle.StandardPixmap.SP_ArrowForward,
            ),
            tr("ui.send_to_laser"),
            "#2980b9",
        )
        self.send_button.clicked.connect(self.send_job_requested)
        grid.addWidget(self.send_button, 1, 0)
        # Boutons en haut, place libre en dessous.
        grid.setRowStretch(2, 1)

    def set_send_enabled(self, enabled):
        self.send_button.setEnabled(enabled)
