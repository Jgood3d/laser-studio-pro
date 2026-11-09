"""Panneau machine sous les onglets (DRO, jog, console directe)."""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontMetrics
from ui.machine.console import DirectConsolePanel
from ui.machine.controls import JogControlPanel
from ui.machine.dro import DroPanel
from ui.machine.job_actions import JobActionsPanel


class MachinePanelMixin:
    @staticmethod
    def _fit_box_width(box, content_px=0):
        """Largeur minimale d'un cadre : son titre en entier, au moins.

        `content_px` : largeur demandée par le contenu. Le thème met les
        titres de cadre en gras et les décale (marge gauche + marges
        internes), ce que Qt ne compte pas dans la taille minimale du cadre :
        sans cette largeur, un cadre étroit (le DRO) voit son titre coupé à
        droite.
        """
        font = QFont(box.font())
        font.setBold(True)
        title_px = QFontMetrics(font).horizontalAdvance(box.title()) + 44
        box.setMinimumWidth(
            max(box.minimumSizeHint().width(), title_px, content_px)
        )

    def _build_jog_panel(self):
        """Panneau de pilotage, abonné à la logique de la machine.

        Le panneau émet les demandes de l'utilisateur ; la fenêtre les
        transmet aux méthodes de LaserControlMixin. La vitesse maximale du
        graveur (`spin_machine_max_speed`, qui doit déjà exister) borne son
        curseur de vitesse.
        """
        panel = JogControlPanel(self.spin_machine_max_speed.value())
        panel.jog_requested.connect(self.jog_move)
        panel.home_requested.connect(self.send_homing)
        panel.pause_requested.connect(self.send_pause)
        panel.resume_requested.connect(self.send_resume)
        panel.reset_requested.connect(self.send_reset)
        panel.emergency_stop_requested.connect(self.send_kill)
        panel.send_job_requested.connect(self.send_to_laser)
        self.spin_machine_max_speed.valueChanged.connect(panel.set_max_speed)
        return panel

    def _build_job_actions_panel(self):
        """Panneau des actions de job, abonné à la logique de la machine."""
        panel = JobActionsPanel()
        panel.frame_requested.connect(self.run_frame)
        panel.set_work_zero_requested.connect(self.set_work_zero)
        panel.go_to_work_zero_requested.connect(self.go_to_work_zero)
        panel.repeat_job_requested.connect(self.repeat_last_job)
        return panel

    def _build_machine_panel(self):
        """Panneau machine sous les onglets (DRO, jog, console directe)."""
        center_bottom_widget = QWidget()
        center_bottom_layout = QVBoxLayout(center_bottom_widget)
        center_bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.dro_panel = DroPanel()
        self.dro_panel.unlock_requested.connect(self.unlock_alarm)
        self._fit_box_width(
            self.dro_panel, self.dro_panel.minimum_content_width()
        )

        self.jog_panel = self._build_jog_panel()
        self.job_actions_panel = self._build_job_actions_panel()

        # Quatre parties côte à côte : position du job à gauche, puis le
        # pilotage et les actions de job, et le DRO à droite. Le pilotage et
        # les actions gardent leur taille naturelle (leurs boutons ne
        # grandissent pas) ; la place libre est partagée entre la position
        # du job et le DRO, qui sinon serait coupé.
        self._fit_box_width(self.job_position_box)
        self._fit_box_width(self.jog_panel)
        self._fit_box_width(self.job_actions_panel)
        machine_row = QHBoxLayout()
        machine_row.addWidget(self.job_position_box, 1)
        machine_row.addWidget(self.jog_panel, 0)
        machine_row.addWidget(self.job_actions_panel, 0)
        machine_row.addWidget(self.dro_panel, 1)
        center_bottom_layout.addLayout(machine_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        center_bottom_layout.addWidget(self.progress_bar)

        self.console_panel = DirectConsolePanel()
        self.console_panel.command_submitted.connect(self.send_manual_cmd)
        center_bottom_layout.addWidget(self.console_panel)
        # Commandes verrouillées tant que non connecté
        self.update_connection_widgets()
        # Place libre en bas, pas dans les cadres
        center_bottom_layout.addStretch()

        self.main_tabs_view.setMinimumHeight(150)
        # Le panneau machine (DRO, jog, console directe) demande ~400 px.
        # Réduit plus bas avec le séparateur, il défile au lieu d'écraser ses
        # cadres jusqu'à n'en laisser que les titres.
        center_bottom_scroll = QScrollArea()
        center_bottom_scroll.setWidget(center_bottom_widget)
        center_bottom_scroll.setWidgetResizable(True)
        center_bottom_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        center_bottom_scroll.setMinimumHeight(100)
        self.center_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_v_splitter.addWidget(self.main_tabs_view)
        self.center_v_splitter.addWidget(center_bottom_scroll)
        self.center_v_splitter.setStretchFactor(0, 3)
        self.center_v_splitter.setStretchFactor(1, 1)
        return center_bottom_scroll
