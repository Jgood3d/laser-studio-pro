"""Page « Configuration GRBL », ouverte depuis le menu Paramètres."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from i18n import tr


class GrblConfigPageMixin:
    def _build_grbl_config_page(self):
        """Page « Configuration GRBL », ouverte depuis le menu Paramètres."""
        tab_gcode_cfg = QWidget()
        layout_gcode_cfg = QFormLayout(tab_gcode_cfg)

        self.combo_laser_cmd = QComboBox()
        self.combo_laser_cmd.addItems(
            ["M4 (Dynamic Power)", "M3 (Constant Power)"]
        )
        self.spin_smax = QSpinBox()
        self.spin_smax.setRange(1, 10000)
        self.spin_smax.setValue(1000)
        self.chk_homing = QCheckBox(tr("ui.grbl_homing"))
        # Homing automatique au démarrage du job : activé d'office.
        self.chk_homing.setChecked(True)
        self.chk_overscan = QCheckBox(tr("ui.overscan_enabled"))
        self.chk_overscan.setChecked(True)

        self.combo_overscan_mode = QComboBox()
        self.combo_overscan_mode.addItems(
            [tr("ui.overscan_mode_fixed"), tr("ui.overscan_mode_pct")]
        )
        self.combo_overscan_mode.currentIndexChanged.connect(
            self.on_overscan_mode_changed
        )

        self.spin_overscan_dist = QDoubleSpinBox()
        self.spin_overscan_dist.setRange(0.0, 50.0)
        self.spin_overscan_dist.setSingleStep(0.1)
        self.spin_overscan_dist.setDecimals(1)
        self.spin_overscan_dist.setValue(2.5)
        self.spin_overscan_dist.setSuffix(" mm")

        self.spin_overscan_pct = QDoubleSpinBox()
        self.spin_overscan_pct.setRange(0.0, 50.0)
        self.spin_overscan_pct.setSingleStep(0.1)
        self.spin_overscan_pct.setDecimals(1)
        self.spin_overscan_pct.setValue(5.0)
        self.spin_overscan_pct.setSuffix(" %")

        self.overscan_stacked = QStackedWidget()
        self.overscan_stacked.addWidget(self.spin_overscan_dist)
        self.overscan_stacked.addWidget(self.spin_overscan_pct)
        self.overscan_stacked.setFixedHeight(28)

        self.txt_start_gcode = QTextEdit()
        self.txt_start_gcode.setMaximumHeight(45)
        self.txt_start_gcode.setPlainText("G21 ; Unités mm\nG90 ; Absolu")

        self.txt_end_gcode = QTextEdit()
        self.txt_end_gcode.setMaximumHeight(45)
        self.txt_end_gcode.setPlainText(
            "M5 ; Extinction Laser\nG0 X0 Y0 ; Retour origine"
        )

        layout_gcode_cfg.addRow(tr("ui.gcode_laser_cmd"), self.combo_laser_cmd)
        layout_gcode_cfg.addRow(tr("ui.gcode_smax"), self.spin_smax)
        layout_gcode_cfg.addRow("", self.chk_homing)
        layout_gcode_cfg.addRow("", self.chk_overscan)
        self.chk_safe_cut_order = QCheckBox(tr("ui.safe_cut_order"))
        self.chk_safe_cut_order.setChecked(True)
        self.chk_safe_cut_order.setToolTip(tr("ui.safe_cut_order_tip"))
        layout_gcode_cfg.addRow("", self.chk_safe_cut_order)
        layout_gcode_cfg.addRow(
            tr("ui.overscan_mode_label"), self.combo_overscan_mode
        )
        layout_gcode_cfg.addRow(
            tr("ui.overscan_value_label"), self.overscan_stacked
        )

        # Décalage aller/retour : compense le jeu mécanique et le délai
        # d'allumage du laser entre les lignes gravées dans un sens et dans
        # l'autre (propre à la machine).
        self.spin_scan_offset = QDoubleSpinBox()
        self.spin_scan_offset.setRange(-2.0, 2.0)
        self.spin_scan_offset.setSingleStep(0.01)
        self.spin_scan_offset.setDecimals(2)
        self.spin_scan_offset.setValue(0.0)
        self.spin_scan_offset.setSuffix(" mm")
        self.spin_scan_offset.setToolTip(tr("ui.scan_offset_tip"))
        btn_bidir_test = QPushButton(tr("ui.bidir_test_btn"))
        btn_bidir_test.setToolTip(tr("ui.scan_offset_tip"))
        btn_bidir_test.clicked.connect(self.generate_bidir_test)
        # Mémorisé dans le profil de la machine.
        self.spin_scan_offset.valueChanged.connect(
            self._schedule_layer_persist
        )
        layout_gcode_cfg.addRow(
            tr("ui.scan_offset_label"), self.spin_scan_offset
        )
        layout_gcode_cfg.addRow("", btn_bidir_test)
        layout_gcode_cfg.addRow(tr("ui.gcode_start"), self.txt_start_gcode)
        layout_gcode_cfg.addRow(tr("ui.gcode_end"), self.txt_end_gcode)

        grbl_settings_box = QGroupBox(tr("ui.grbl_settings_box"))
        grbl_settings_layout = QVBoxLayout()

        self.txt_grbl_settings = QTextEdit()
        self.txt_grbl_settings.setPlaceholderText(
            tr("ui.grbl_settings_placeholder")
        )
        self.txt_grbl_settings.setMaximumHeight(140)
        self.txt_grbl_settings.setStyleSheet("font-family: monospace;")
        grbl_settings_layout.addWidget(self.txt_grbl_settings)

        grbl_settings_btn_row = QHBoxLayout()
        btn_grbl_read = QPushButton(tr("ui.grbl_read"))
        btn_grbl_read.clicked.connect(self.read_grbl_settings)
        btn_grbl_send = QPushButton(tr("ui.grbl_send"))
        btn_grbl_send.clicked.connect(self.send_grbl_settings)
        btn_grbl_export = QPushButton(tr("ui.grbl_export"))
        btn_grbl_export.clicked.connect(self.export_grbl_settings)
        btn_grbl_import = QPushButton(tr("ui.grbl_import"))
        btn_grbl_import.clicked.connect(self.import_grbl_settings)
        for b in (
            btn_grbl_read,
            btn_grbl_send,
            btn_grbl_export,
            btn_grbl_import,
        ):
            grbl_settings_btn_row.addWidget(b)
        grbl_settings_layout.addLayout(grbl_settings_btn_row)

        btn_grbl_link_profile = QPushButton(tr("ui.grbl_link_profile"))
        btn_grbl_link_profile.clicked.connect(
            self.save_grbl_settings_to_profile
        )
        grbl_settings_layout.addWidget(btn_grbl_link_profile)

        grbl_settings_box.setLayout(grbl_settings_layout)
        layout_gcode_cfg.addRow(grbl_settings_box)

        # Page affichée dans une fenêtre du menu (voir show_settings_window),
        # plus dans un onglet.
        self.tab_grbl_config = tab_gcode_cfg
