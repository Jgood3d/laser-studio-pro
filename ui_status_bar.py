"""Barre d'état : messages d'information et progression de la génération."""

from PyQt6.QtWidgets import QProgressBar, QSizePolicy
from PyQt6.QtCore import QTimer
from widgets_extra import AutoHideLabel


class StatusBarMixin:
    STATUS_MESSAGE_MS = (
        8000  # durée d'affichage d'un message de la barre d'état
    )

    def show_status_message(self, text, tooltip=None):
        """Affiche `text` dans la barre d'état pendant STATUS_MESSAGE_MS.

        L'infobulle donne `tooltip` (texte complet, ex. avec le chemin du
        fichier) ou, à défaut, `text`.
        """
        self.lbl_status_message.setText(text)
        self.lbl_status_message.setToolTip(tooltip or text)
        if text:
            self._status_message_timer.start(self.STATUS_MESSAGE_MS)

    def _build_status_bar(self):
        """Barre d'état : messages et progression de la génération."""
        self.lbl_gen_progress_main = AutoHideLabel("")
        self.gen_progress_bar_main = QProgressBar()
        self.gen_progress_bar_main.setRange(0, 100)
        self.gen_progress_bar_main.setValue(0)
        self.gen_progress_bar_main.setVisible(False)
        self.gen_progress_bar_main.setMaximumHeight(16)
        # Messages d'information (image chargée, SVG chargé…) : dans la barre
        # d'état, effacés au bout de STATUS_MESSAGE_MS (voir
        # show_status_message) ; la console reste réservée au graveur. Libellé
        # à part plutôt que statusBar().showMessage(), qui masquerait la
        # progression.
        self.lbl_status_message = AutoHideLabel("")
        self.lbl_status_message.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._status_message_timer = QTimer(self)
        self._status_message_timer.setSingleShot(True)
        self._status_message_timer.timeout.connect(
            lambda: self.show_status_message("")
        )
        self.statusBar().addWidget(self.lbl_status_message, 1)
        # Progression de la génération : dans la barre d'état, en bas de la
        # fenêtre.
        self.statusBar().addWidget(self.lbl_gen_progress_main)
        self.statusBar().addWidget(self.gen_progress_bar_main, 1)
