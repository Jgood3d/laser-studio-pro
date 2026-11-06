"""Panneau machine sous les onglets (DRO, jog, console directe)."""

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from i18n import tr
from widgets_extra import HistoryLineEdit


class MachinePanelMixin:
    def _build_machine_panel(self):
        """Panneau machine sous les onglets (DRO, jog, console directe)."""
        center_bottom_widget = QWidget()
        center_bottom_layout = QVBoxLayout(center_bottom_widget)
        center_bottom_layout.setContentsMargins(0, 0, 0, 0)

        dro_box = QGroupBox(tr("ui.dro_box"))
        dro_layout = QVBoxLayout()
        self.lbl_dro_state = QLabel(tr("ui.dro_state").format(value="—"))
        self.lbl_dro_x = QLabel(tr("ui.dro_x").format(value="—"))
        self.lbl_dro_y = QLabel(tr("ui.dro_y").format(value="—"))
        self.lbl_dro_z = QLabel(tr("ui.dro_z").format(value="—"))
        for lbl in (
            self.lbl_dro_state,
            self.lbl_dro_x,
            self.lbl_dro_y,
            self.lbl_dro_z,
        ):
            lbl.setStyleSheet("font-family: monospace; font-size: 13px;")

        self.btn_unlock_alarm = QPushButton(tr("ui.unlock_alarm"))
        self.btn_unlock_alarm.setStyleSheet(
            "background-color: #c0392b; color: white; "
            "font-weight: bold; padding: 3px 10px;"
        )
        self.btn_unlock_alarm.clicked.connect(self.unlock_alarm)
        self.btn_unlock_alarm.setVisible(False)
        dro_layout.addWidget(self.lbl_dro_state)
        dro_layout.addWidget(self.btn_unlock_alarm)
        dro_layout.addWidget(self.lbl_dro_x)
        dro_layout.addWidget(self.lbl_dro_y)
        dro_layout.addWidget(self.lbl_dro_z)
        dro_layout.addStretch()
        dro_box.setLayout(dro_layout)

        jog_box = self._build_jog_box()

        # Trois parties côte à côte : position du job à gauche, jog au centre,
        # DRO à droite.
        machine_row = QHBoxLayout()
        machine_row.addWidget(self.job_position_box)
        machine_row.addWidget(jog_box, 1)
        machine_row.addWidget(dro_box)
        center_bottom_layout.addLayout(machine_row)
        self.jog_box = jog_box

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        center_bottom_layout.addWidget(self.progress_bar)

        cmd_box = QGroupBox(tr("ui.direct_console_box"))
        cmd_layout = QHBoxLayout()
        self.txt_manual_cmd = HistoryLineEdit()
        self.txt_manual_cmd.setPlaceholderText(
            tr("ui.manual_grbl_placeholder")
        )
        self.txt_manual_cmd.returnPressed.connect(self.send_manual_cmd)

        btn_send_cmd = QPushButton(tr("ui.manual_send"))
        btn_send_cmd.clicked.connect(self.send_manual_cmd)

        cmd_layout.addWidget(self.txt_manual_cmd)
        cmd_layout.addWidget(btn_send_cmd)
        cmd_box.setLayout(cmd_layout)
        center_bottom_layout.addWidget(cmd_box)
        self.direct_console_box = cmd_box
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
