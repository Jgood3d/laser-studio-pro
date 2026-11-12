"""Barre d'état de la fenêtre principale : messages et progression."""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QProgressBar, QSizePolicy, QStatusBar

from laser_studio.core.constants import STATUS_BAR_MESSAGE_DURATION
from laser_studio.ui.widgets import AutoHideLabel

# Repères en tête des anciens messages de console : inutiles dans la barre d'état.
CONSOLE_MARKERS = (">>>", "!!!", ";")


def status_text(text):
    """Message sur une ligne pour la barre d'état : repères de console
    (« >>> », « !!! », « ; ») et cadres « --- … --- » retirés, lignes
    jointes par « — »."""
    lines = []
    for line in str(text).splitlines():
        line = line.strip()
        for marker in CONSOLE_MARKERS:
            if line.startswith(marker):
                line = line[len(marker):].strip()
                break
        if line.startswith("---") and line.endswith("---"):
            line = line.strip("-").strip()
        if line:
            lines.append(line)
    return " — ".join(lines)


class StatusBar(QStatusBar):
    """Barre d'état : messages d'information et progression de la génération.

    Les messages passent par un libellé à part, et non par showMessage() de
    Qt, qui masquerait la progression. Utilisation :

        window.setStatusBar(StatusBar(window))
        window.statusBar().show_info("Image chargée", "/chemin/image.png")
        window.statusBar().show_progress(40, "Génération en cours… 40%")
        window.statusBar().hide_progress(delay_ms=1500)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message_label = self._message_label()
        self.progress_label = AutoHideLabel("")
        self.progress_bar = self._progress_bar()
        self.addWidget(self.message_label, 1)
        self.addWidget(self.progress_label)
        self.addWidget(self.progress_bar, 1)
        self.message_timer = self._message_timer()
        self.progress_hide_timer = self._progress_hide_timer()

    def show_info(self, text, tooltip=None):
        """Affiche `text` pendant STATUS_BAR_MESSAGE_DURATION millisecondes.

        L'infobulle donne `tooltip` (texte complet, par exemple avec le
        chemin du fichier) ou, à défaut, `text`.
        """
        self.message_label.setText(text)
        self.message_label.setToolTip(tooltip or text)
        if text:
            self.message_timer.start(STATUS_BAR_MESSAGE_DURATION)

    def show_progress(self, percent, text):
        """Affiche la progression : barre à `percent` %, libellé `text`.

        Annule un masquage encore en attente (hide_progress avec délai) :
        une nouvelle génération lancée juste après la précédente reste
        visible.
        """
        self.progress_hide_timer.stop()
        self.progress_bar.setValue(percent)
        self.progress_bar.setVisible(True)
        self.progress_label.setText(text)

    def hide_progress(self, delay_ms=0):
        """Masque la progression, tout de suite ou après `delay_ms` ms."""
        if delay_ms:
            self.progress_hide_timer.start(delay_ms)
        else:
            self.progress_hide_timer.stop()
            self._hide_progress_now()

    def _hide_progress_now(self):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")

    def _message_label(self):
        """Libellé des messages : il prend la place libre, quitte à rogner."""
        label = AutoHideLabel("")
        label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        return label

    def _progress_bar(self):
        """Barre de progression, masquée hors génération."""
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setVisible(False)
        bar.setMaximumHeight(16)
        return bar

    def _message_timer(self):
        """Minuterie qui efface le message une fois le délai écoulé."""
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.show_info(""))
        return timer

    def _progress_hide_timer(self):
        """Minuterie du masquage différé de la progression (annulable)."""
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._hide_progress_now)
        return timer
