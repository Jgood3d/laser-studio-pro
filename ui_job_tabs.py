"""Onglets « Console / G-Code » et « File d'attente »."""

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from i18n import tr
from ui.widgets import TabToolBar


class JobTabsMixin:
    def _build_console_tab(self):
        """Onglet « Console G-Code »."""
        tab_console_gcode = QWidget()
        layout_console_gcode = QVBoxLayout(tab_console_gcode)
        layout_console_gcode.setContentsMargins(6, 6, 6, 6)

        toolbar_console_gcode = TabToolBar(tab_console_gcode)
        toolbar_console_gcode.fullscreen_requested.connect(
            lambda: self._toggle_fullscreen_tab(
                "tab_console_gcode", "ui.tab_console_gcode"
            )
        )
        tab_console_gcode._fullscreen_control = (
            toolbar_console_gcode.fullscreen_action
        )
        layout_console_gcode.addWidget(toolbar_console_gcode)

        stats_box = QGroupBox(tr("ui.job_stats_box"))
        stats_layout = QVBoxLayout()
        self.lbl_stat_lines = QLabel(tr("ui.job_lines"))
        self.lbl_stat_power = QLabel(tr("ui.job_avg_power"))
        self.lbl_stat_time = QLabel(tr("ui.job_estimated_time"))
        stats_layout.addWidget(self.lbl_stat_lines)
        stats_layout.addWidget(self.lbl_stat_power)
        stats_layout.addWidget(self.lbl_stat_time)
        stats_box.setLayout(stats_layout)
        layout_console_gcode.addWidget(stats_box)

        export_box = QGroupBox(tr("ui.gcode_export_box"))
        export_layout = QHBoxLayout()

        btn_exp_gcode = QPushButton("Export .gcode")
        btn_exp_gcode.setStyleSheet(
            "background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        btn_exp_gcode.clicked.connect(
            lambda: self.export_gcode_with_ext(".gcode")
        )

        btn_exp_nc = QPushButton("Export .nc")
        btn_exp_nc.setStyleSheet(
            "background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        btn_exp_nc.clicked.connect(lambda: self.export_gcode_with_ext(".nc"))

        btn_exp_gc = QPushButton("Export .gc")
        btn_exp_gc.setStyleSheet(
            "background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        btn_exp_gc.clicked.connect(lambda: self.export_gcode_with_ext(".gc"))

        export_layout.addWidget(btn_exp_gcode)
        export_layout.addWidget(btn_exp_nc)
        export_layout.addWidget(btn_exp_gc)
        export_box.setLayout(export_layout)
        layout_console_gcode.addWidget(export_box)

        layout_console_gcode.addWidget(
            QLabel(tr("ui.generated_console_label"))
        )
        self.txt_console = QTextEdit()
        self.txt_console.setFontFamily("Courier")
        layout_console_gcode.addWidget(self.txt_console)

        self.main_tabs_view.addTab(
            tab_console_gcode, tr("ui.tab_console_gcode")
        )
        self.tab_console_gcode = tab_console_gcode

    def _build_job_queue_tab(self):
        """Onglet « File d'attente », avec le suivi du G-Code envoyé."""
        tab_job_queue = QWidget()
        layout_tab_job_queue = QVBoxLayout(tab_job_queue)
        layout_tab_job_queue.setContentsMargins(6, 6, 6, 6)
        # Deux moitiés réglables : la file à gauche, le G-Code envoyé à droite.
        queue_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout_tab_job_queue.addWidget(queue_splitter)
        queue_left = QWidget()
        layout_job_queue = QVBoxLayout(queue_left)
        layout_job_queue.setContentsMargins(0, 0, 0, 0)
        queue_splitter.addWidget(queue_left)

        self.list_job_queue = QListWidget()
        self.list_job_queue.setDragDropMode(
            QListWidget.DragDropMode.InternalMove
        )
        self.list_job_queue.model().rowsMoved.connect(self._on_queue_reordered)
        layout_job_queue.addWidget(self.list_job_queue)

        queue_btn_row1 = QHBoxLayout()
        btn_queue_add = QPushButton(tr("ui.queue_add_current"))
        btn_queue_add.clicked.connect(self.add_current_gcode_to_queue)
        btn_queue_remove = QPushButton(tr("ui.queue_remove_selected"))
        btn_queue_remove.clicked.connect(self.remove_selected_from_queue)
        btn_queue_clear = QPushButton(tr("ui.queue_clear"))
        btn_queue_clear.clicked.connect(self.clear_job_queue)
        queue_btn_row1.addWidget(btn_queue_add)
        queue_btn_row1.addWidget(btn_queue_remove)
        queue_btn_row1.addWidget(btn_queue_clear)
        layout_job_queue.addLayout(queue_btn_row1)

        self.btn_run_queue = QPushButton(tr("ui.queue_run"))
        self.btn_run_queue.setStyleSheet(
            "background-color: #8e44ad; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        self.btn_run_queue.clicked.connect(self.run_job_queue)
        layout_job_queue.addWidget(self.btn_run_queue)

        self.lbl_queue_status = QLabel(tr("ui.queue_empty"))
        layout_job_queue.addWidget(self.lbl_queue_status)

        # Suivi de l'envoi : chaque ligne de G-Code s'ajoute ici au moment où
        # elle part vers la machine (GCodeStreamerThread.lines_sent), pour la
        # file comme pour « Envoyer au laser ».
        sent_box = QGroupBox(tr("queue.sent_log_title"))
        sent_layout = QVBoxLayout(sent_box)
        self.txt_sent_gcode = QPlainTextEdit()
        self.txt_sent_gcode.setReadOnly(True)
        # Garde les 20 000 dernières lignes.
        self.txt_sent_gcode.setMaximumBlockCount(20000)
        self.txt_sent_gcode.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.txt_sent_gcode.setStyleSheet("font-family: monospace;")
        self.txt_sent_gcode.setPlaceholderText(
            tr("queue.sent_log_placeholder")
        )
        sent_layout.addWidget(self.txt_sent_gcode)
        queue_splitter.addWidget(sent_box)
        # Moitié / moitié au départ, puis à chaque redimensionnement de la
        # fenêtre. Des tailles égales et grandes : Qt les ramène à la largeur
        # réelle en gardant la proportion.
        queue_splitter.setStretchFactor(0, 1)
        queue_splitter.setStretchFactor(1, 1)
        queue_splitter.setSizes([100000, 100000])

        self.main_tabs_view.addTab(tab_job_queue, tr("ui.tab_job_queue"))
        self.tab_job_queue = tab_job_queue
