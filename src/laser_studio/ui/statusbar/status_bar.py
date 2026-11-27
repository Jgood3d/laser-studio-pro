"""Barre d'état de la fenêtre principale : messages, progression, durée estimée et état du graveur."""

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QProgressBar, QSizePolicy, QStatusBar

from laser_studio.core.constants import STATUS_BAR_MESSAGE_DURATION
from laser_studio.i18n import tr
from laser_studio.ui.machine.status.state import STATE_COLORS, UNKNOWN_STATE_COLOR, state_text
from laser_studio.ui.widgets import AutoHideLabel

# Repères en tête des anciens messages de console : inutiles dans la barre d'état.
CONSOLE_MARKERS = (">>>", "!!!", ";")


# Repère orange devant « G-Code à régénérer » (balisage seulement, le texte est traduit).
STALE_MARK = '<span style="color:#e6a700">⚠</span>&nbsp;'

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
        window.statusBar().show_log(">>> Connecté sur COM3")   # texte de journal : « Connecté sur COM3 »
        window.statusBar().show_progress(40, "Génération en cours… 40%")
        window.statusBar().hide_progress(delay_ms=1500)
        window.statusBar().set_duration("Temps Estimé: 12 min 30 s")    # None : rien
        window.statusBar().set_machine("Idle", 12.5, 30.0)                 # None : déconnecté
    """

    # Clic sur la pastille du graveur : la fenêtre ouvre l'onglet « Graveur » du panneau du bas.
    machine_clicked = pyqtSignal()
    # Clic sur « G-Code à régénérer » : la fenêtre relance la génération.
    regenerate_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message_label = self._message_label()
        self.progress_label = AutoHideLabel("")
        self.progress_bar = self._progress_bar()
        self.addWidget(self.message_label, 1)
        self.addWidget(self.progress_label)
        self.addWidget(self.progress_bar, 1)
        self.duration_label = QLabel()
        self.duration_label.setVisible(False)
        self.addPermanentWidget(self.duration_label)
        self.stale_label = QLabel()
        self.stale_label.setText(STALE_MARK + tr("status.gcode_stale"))
        self.stale_label.setToolTip(tr("status.gcode_stale_tip"))
        self.stale_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stale_label.installEventFilter(self)
        self.stale_label.setVisible(False)
        self.addPermanentWidget(self.stale_label)
        self.machine_label = QLabel()
        self.machine_label.setToolTip(tr("status.machine_tip"))
        self.machine_label.installEventFilter(self)
        self.addPermanentWidget(self.machine_label)
        self.set_machine(None)
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

    def show_log(self, text):
        """Message d'une action écrit pour un journal (plusieurs lignes, repères « >>> », « ; »,
        cadres « --- ») : une ligne dans la barre (status_text), le texte complet en infobulle.
        Rien n'est affiché s'il ne reste aucun texte."""
        short = status_text(text)
        if short:
            self.show_info(short, str(text).strip())

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

    def set_duration(self, text):
        """Durée estimée du dernier G-Code généré (texte prêt à afficher) ; None la masque."""
        self.duration_label.setText(text or "")
        self.duration_label.setVisible(bool(text))

    def set_gcode_stale(self, stale):
        """« G-Code à régénérer » : le G-Code affiché ne correspond plus aux réglages (JobController)."""
        self.stale_label.setVisible(bool(stale))

    def set_machine(self, state, x=None, y=None):
        """Pastille de l'état GRBL (couleurs du panneau machine) et position de la tête ; `state` None :
        graveur déconnecté."""
        color = STATE_COLORS.get(state, UNKNOWN_STATE_COLOR)
        text = tr("status.disconnected") if state is None else state_text(state)
        if state is not None and x is not None and y is not None:
            text += f"  ·  X {x:.2f}  Y {y:.2f}"
        self.machine_label.setText(f'<span style="color:{color}">●</span>&nbsp;{text}')

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonRelease and watched in (self.machine_label, self.stale_label):
            (self.machine_clicked if watched is self.machine_label else self.regenerate_clicked).emit()
            return True
        return super().eventFilter(watched, event)

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
