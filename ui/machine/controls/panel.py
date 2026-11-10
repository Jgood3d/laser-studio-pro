"""Panneau de pilotage de la machine : déplacements et commandes temps réel."""

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPolygonF
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QVBoxLayout,
)

from app_constants import (
    JOG_DEFAULT_SPEED,
    JOG_DEFAULT_STEP_MM,
    JOG_SPEED_MIN,
    JOG_STEPS_MM,
)
from i18n import tr
from ui.utils import painted_icon, themed_icon, tool_button

# Flèches : (ligne, colonne, dx, dy, angle de la flèche en degrés), avec
# 0 degré vers le haut. Le homing occupe le centre (ligne 1, colonne 1).
ARROWS = (
    (0, 0, -1, 1, -45),
    (0, 1, 0, 1, 0),
    (0, 2, 1, 1, 45),
    (1, 0, -1, 0, -90),
    (1, 2, 1, 0, 90),
    (2, 0, -1, -1, -135),
    (2, 1, 0, -1, 180),
    (2, 2, 1, -1, 135),
)


class JogControlPanel(QGroupBox):
    """Déplacements manuels (jog), homing, commandes temps réel et envoi.

    Le panneau ne pilote pas la machine : il émet des signaux qui décrivent
    la demande de l'utilisateur, avec des valeurs métier (mm, mm/min). La
    fenêtre, et plus tard un contrôleur, s'y abonne :

        panel = JogControlPanel(max_speed=6000)
        panel.jog_requested.connect(laser.jog_move)
        panel.home_requested.connect(laser.home_machine)

    Il reçoit l'état de la machine par set_connected() et set_max_speed().
    """

    # Déplacement relatif demandé : dx et dy en mm, vitesse en mm/min.
    jog_requested = pyqtSignal(float, float, int)
    home_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    emergency_stop_requested = pyqtSignal()
    # Envoi du G-code généré au graveur.
    send_job_requested = pyqtSignal()

    def __init__(self, max_speed, parent=None):
        super().__init__(tr("ui.jog_box"), parent)
        self.step_slider = self._step_slider()
        self.speed_slider = self._speed_slider(max_speed)
        layout = QHBoxLayout(self)
        layout.addLayout(self._arrows())
        layout.addLayout(
            self._slider_column(
                self.step_slider, "ui.jog_step_label", self._step_text
            )
        )
        layout.addLayout(
            self._slider_column(self.speed_slider, "ui.jog_speed_label", str)
        )
        layout.addSpacing(12)
        layout.addLayout(self._realtime_commands())
        layout.addStretch()

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Déverrouille les commandes si le graveur est connecté."""
        self.setEnabled(connected)

    def set_send_enabled(self, enabled):
        """Active l'envoi du job (désactivé pendant un envoi en cours)."""
        self.send_button.setEnabled(enabled)

    def set_max_speed(self, max_speed):
        """Limite le curseur de vitesse à la vitesse maximale du graveur.

        Si la valeur choisie la dépasse (profil plus lent), elle est ramenée
        à ce maximum.
        """
        self._limit_speed(self.speed_slider, max_speed)

    # -- valeurs choisies

    def step_mm(self):
        """Pas de déplacement choisi, en mm."""
        return JOG_STEPS_MM[self.step_slider.value()]

    def speed(self):
        """Vitesse de déplacement choisie, en mm/min."""
        return self.speed_slider.value()

    # -- construction

    def _arrows(self):
        """Croix des 8 flèches, avec le homing au centre."""
        grid = QGridLayout()
        grid.setSpacing(4)
        for row, col, dx, dy, angle in ARROWS:
            button = tool_button(
                self._arrow_icon(angle), self._axes_text(dx, dy)
            )
            button.clicked.connect(
                lambda _checked=False, x=dx, y=dy: self._request_jog(x, y)
            )
            grid.addWidget(button, row, col)
        home = tool_button(
            themed_icon(
                self,
                QIcon.ThemeIcon.GoHome,
                QStyle.StandardPixmap.SP_DirHomeIcon,
            ),
            tr("ui.homing_cmd"),
        )
        home.clicked.connect(self.home_requested)
        grid.addWidget(home, 1, 1)
        return grid

    def _realtime_commands(self):
        """Pause, reprise, reset et arrêt d'urgence, puis l'envoi du job."""
        grid = QGridLayout()
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
        return grid

    def _step_slider(self):
        """Curseur vertical du pas : un cran par valeur de JOG_STEPS_MM."""
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setRange(0, len(JOG_STEPS_MM) - 1)
        slider.setPageStep(1)
        slider.setValue(JOG_STEPS_MM.index(JOG_DEFAULT_STEP_MM))
        slider.setTickPosition(QSlider.TickPosition.TicksRight)
        slider.setToolTip(tr("ui.jog_step_label"))
        return slider

    def _speed_slider(self, max_speed):
        """Curseur vertical de la vitesse, borné par `max_speed`."""
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setSingleStep(100)
        slider.setPageStep(500)
        self._limit_speed(slider, max_speed)
        slider.setValue(min(JOG_DEFAULT_SPEED, slider.maximum()))
        return slider

    @staticmethod
    def _slider_column(slider, title_key, formatter):
        """Curseur avec son titre au-dessus et sa valeur en dessous."""
        column = QVBoxLayout()
        title = QLabel(tr(title_key))
        value = QLabel(formatter(slider.value()))
        for label in (title, value):
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        slider.valueChanged.connect(lambda v: value.setText(formatter(v)))
        column.addWidget(title)
        column.addWidget(slider, 1, Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(value)
        return column

    @staticmethod
    def _limit_speed(slider, max_speed):
        """Plage du curseur de vitesse : de JOG_SPEED_MIN à `max_speed`."""
        top = max(int(max_speed), JOG_SPEED_MIN)
        slider.setRange(JOG_SPEED_MIN, top)
        slider.setToolTip(
            tr("ui.jog_speed_range").format(min=JOG_SPEED_MIN, max=top)
        )

    # -- signaux

    def _request_jog(self, dx, dy):
        """Émet jog_requested : direction (dx, dy) multipliée par le pas."""
        step = self.step_mm()
        self.jog_requested.emit(dx * step, dy * step, self.speed())

    # -- icônes et libellés

    @staticmethod
    def _step_text(index):
        return f"{JOG_STEPS_MM[index]:g} mm"

    @staticmethod
    def _axes_text(dx, dy):
        """Infobulle d'une flèche, par exemple « X+ Y- »."""
        return " ".join(
            f"{axis}{'+' if d > 0 else '-'}"
            for axis, d in (("X", dx), ("Y", dy))
            if d
        )

    def _arrow_icon(self, angle):
        """Flèche tournée de `angle` degrés (0 = haut, sens horaire)."""

        def draw(painter, color):
            painter.translate(16, 16)
            painter.rotate(angle)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(0, -12),
                        QPointF(10, 0),
                        QPointF(4, 0),
                        QPointF(4, 11),
                        QPointF(-4, 11),
                        QPointF(-4, 0),
                        QPointF(-10, 0),
                    ]
                )
            )

        return painted_icon(self.palette(), draw)
