"""Panneau de pilotage (jog).

Croix de déplacement, curseurs de pas et de vitesse, boutons de commande.
"""

from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
)
from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import QIcon, QPen, QPolygonF
from i18n import tr
from ui_utils import painted_icon


class JogMixin:
    # Valeurs du curseur « Pas » du panneau de pilotage
    JOG_STEPS_MM = (0.1, 1.0, 10.0, 100.0)
    JOG_BUTTON_SIZE = 40

    JOG_SPEED_MIN = 100  # mm/min, bas du curseur « Vitesse »

    def _apply_jog_speed_limit(self, max_speed):
        """Limite le curseur de vitesse à la vitesse maximale de la machine.

        Si la valeur choisie la dépasse (nouveau profil plus lent), elle est
        ramenée à ce maximum.
        """
        top = max(int(max_speed), self.JOG_SPEED_MIN)
        self.slider_jog_speed.setRange(self.JOG_SPEED_MIN, top)
        self.slider_jog_speed.setToolTip(
            tr("ui.jog_speed_range").format(min=self.JOG_SPEED_MIN, max=top)
        )

    def _jog_tool_button(self, icon, tooltip, color=None):
        """Bouton carré à icône du panneau ; libellé en infobulle.

        `color` : fond (couleurs historiques des boutons Pause, Reprise,
        Reset, Arrêt d'urgence et Envoyer).
        """
        button = QToolButton()
        button.setIcon(icon)
        button.setIconSize(QSize(24, 24))
        button.setToolTip(tooltip)
        button.setFixedSize(self.JOG_BUTTON_SIZE, self.JOG_BUTTON_SIZE)
        button.setAutoRaise(color is None)
        if color:
            # Gris quand le bouton est désactivé (graveur non connecté) :
            # sinon sa couleur le ferait paraître actif.
            button.setStyleSheet(
                f"QToolButton {{ background-color: {color}; "
                "border-radius: 4px; }"
                "QToolButton:disabled { background-color: #b0b0b0; }"
            )
        return button

    def _arrow_icon(self, angle):
        """Flèche du jog, tournée de `angle` degrés.

        0 = vers le haut, sens horaire.
        """

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

    def _frame_icon(self):
        """Cadrage : rectangle en pointillés avec ses quatre coins marqués."""

        def draw(painter, color):
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawRect(6, 6, 20, 20)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for x, y in ((3, 3), (23, 3), (3, 23), (23, 23)):
                painter.drawRect(x, y, 6, 6)

        return painted_icon(self.palette(), draw)

    def _crosshair_icon(self, with_arrow=False):
        """Origine de travail : viseur.

        `with_arrow` : petite flèche qui y va (« Go zéro »).
        """

        def draw(painter, color):
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = 20 if with_arrow else 16
            painter.drawEllipse(QPointF(center, center), 7, 7)
            painter.drawLine(
                QPointF(center - 11, center), QPointF(center + 11, center)
            )
            painter.drawLine(
                QPointF(center, center - 11), QPointF(center, center + 11)
            )
            if with_arrow:
                painter.drawLine(QPointF(2, 2), QPointF(11, 11))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawPolygon(
                    QPolygonF(
                        [QPointF(13, 13), QPointF(5, 11), QPointF(11, 5)]
                    )
                )

        return painted_icon(self.palette(), draw)

    def _build_jog_box(self):
        """Construit le cadre du panneau de pilotage.

        `spin_machine_max_speed` doit déjà exister.
        """
        # Panneau de pilotage compact : croix de déplacement (homing au
        # centre), curseurs de pas et de vitesse, puis boutons à icône
        # (libellé en infobulle), dans l'ordre d'utilisation.
        jog_box = QGroupBox(tr("ui.jog_box"))
        jog_layout = QHBoxLayout(jog_box)

        arrows = QGridLayout()
        arrows.setSpacing(4)
        # (ligne, colonne, dx, dy, angle de la flèche en degrés,
        # 0 = vers le haut)
        for row, col, dx, dy, angle in (
            (0, 0, -1, 1, -45),
            (0, 1, 0, 1, 0),
            (0, 2, 1, 1, 45),
            (1, 0, -1, 0, -90),
            (1, 2, 1, 0, 90),
            (2, 0, -1, -1, -135),
            (2, 1, 0, -1, 180),
            (2, 2, 1, -1, 135),
        ):
            axes = " ".join(
                f"{axis}{'+' if d > 0 else '-'}"
                for axis, d in (("X", dx), ("Y", dy))
                if d
            )
            button = self._jog_tool_button(self._arrow_icon(angle), axes)
            button.clicked.connect(
                lambda _checked=False, x=dx, y=dy: self.jog_move(x, y)
            )
            arrows.addWidget(button, row, col)
        btn_homing_now = self._jog_tool_button(
            QIcon.fromTheme(
                QIcon.ThemeIcon.GoHome,
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_DirHomeIcon
                ),
            ),
            tr("ui.homing_cmd"),
        )
        btn_homing_now.clicked.connect(self.send_homing)
        arrows.addWidget(btn_homing_now, 1, 1)
        jog_layout.addLayout(arrows)

        # Curseurs verticaux : pas du déplacement (valeurs de JOG_STEPS_MM)
        # et vitesse (mm/min).
        self.slider_jog_step = QSlider(Qt.Orientation.Vertical)
        self.slider_jog_step.setRange(0, len(self.JOG_STEPS_MM) - 1)
        self.slider_jog_step.setPageStep(1)
        self.slider_jog_step.setValue(self.JOG_STEPS_MM.index(10.0))
        self.slider_jog_step.setTickPosition(QSlider.TickPosition.TicksRight)
        self.slider_jog_speed = QSlider(Qt.Orientation.Vertical)
        self.slider_jog_speed.setSingleStep(100)
        self.slider_jog_speed.setPageStep(500)
        # Jamais plus vite que la vitesse maximale de la machine
        # (Paramètres du graveur, profil).
        self._apply_jog_speed_limit(self.spin_machine_max_speed.value())
        self.slider_jog_speed.setValue(
            min(3000, self.slider_jog_speed.maximum())
        )
        self.spin_machine_max_speed.valueChanged.connect(
            self._apply_jog_speed_limit
        )
        for slider, title_key, formatter in (
            (
                self.slider_jog_step,
                "ui.jog_step_label",
                lambda v: f"{self.JOG_STEPS_MM[v]:g} mm",
            ),
            (self.slider_jog_speed, "ui.jog_speed_label", lambda v: f"{v}"),
        ):
            column = QVBoxLayout()
            title = QLabel(tr(title_key))
            value = QLabel(formatter(slider.value()))
            for label in (title, value):
                label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            slider.valueChanged.connect(
                lambda v, lbl=value, fmt=formatter: lbl.setText(fmt(v))
            )
            # La vitesse a déjà son infobulle (plage autorisée).
            if not slider.toolTip():
                slider.setToolTip(tr(title_key))
            column.addWidget(title)
            column.addWidget(slider, 1, Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(value)
            jog_layout.addLayout(column)
        jog_layout.addSpacing(12)

        def themed(theme_icon, fallback):
            return QIcon.fromTheme(
                theme_icon, self.style().standardIcon(fallback)
            )

        btn_pause = self._jog_tool_button(
            themed(
                QIcon.ThemeIcon.MediaPlaybackPause,
                QStyle.StandardPixmap.SP_MediaPause,
            ),
            tr("ui.pause"),
            "#e67e22",
        )
        btn_pause.clicked.connect(self.send_pause)
        btn_resume = self._jog_tool_button(
            themed(
                QIcon.ThemeIcon.MediaPlaybackStart,
                QStyle.StandardPixmap.SP_MediaPlay,
            ),
            tr("ui.resume"),
            "#27ae60",
        )
        btn_resume.clicked.connect(self.send_resume)
        btn_reset = self._jog_tool_button(
            themed(
                QIcon.ThemeIcon.SystemReboot,
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("ui.reset"),
            "#c0392b",
        )
        btn_reset.clicked.connect(self.send_reset)
        btn_kill = self._jog_tool_button(
            themed(
                QIcon.ThemeIcon.ProcessStop,
                QStyle.StandardPixmap.SP_BrowserStop,
            ),
            tr("ui.kill"),
            "#ff0000",
        )
        btn_kill.clicked.connect(self.send_kill)
        btn_frame = self._jog_tool_button(self._frame_icon(), tr("ui.frame"))
        btn_frame.clicked.connect(self.run_frame)
        btn_zero_xy = self._jog_tool_button(
            self._crosshair_icon(), tr("ui.zero_work")
        )
        btn_zero_xy.clicked.connect(
            lambda: self.send_manual_direct_cmd("G92 X0 Y0")
        )
        btn_go_zero = self._jog_tool_button(
            self._crosshair_icon(with_arrow=True), tr("ui.go_zero")
        )
        btn_go_zero.clicked.connect(
            lambda: self.send_manual_direct_cmd("G0 X0 Y0")
        )
        self.btn_send = self._jog_tool_button(
            themed(
                QIcon.ThemeIcon.DocumentSend,
                QStyle.StandardPixmap.SP_ArrowForward,
            ),
            tr("ui.send_to_laser"),
            "#2980b9",
        )
        self.btn_send.clicked.connect(self.send_to_laser)
        self.btn_repeat_last_job = self._jog_tool_button(
            themed(
                QIcon.ThemeIcon.MediaPlaylistRepeat,
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("ui.repeat_last_job"),
        )
        self.btn_repeat_last_job.clicked.connect(self.repeat_last_job)
        self.btn_repeat_last_job.setEnabled(False)

        commands = QGridLayout()
        commands.setSpacing(4)
        # Ligne 1 : commandes temps réel de la machine.
        # Ligne 2 : position, puis envoi du job.
        for col, button in enumerate(
            (btn_pause, btn_resume, btn_reset, btn_kill)
        ):
            commands.addWidget(button, 0, col)
        for col, button in enumerate(
            (
                btn_frame,
                btn_zero_xy,
                btn_go_zero,
                self.btn_send,
                self.btn_repeat_last_job,
            )
        ):
            commands.addWidget(button, 1, col)
        commands.setRowStretch(2, 1)
        jog_layout.addLayout(commands)
        jog_layout.addStretch()
        return jog_box
