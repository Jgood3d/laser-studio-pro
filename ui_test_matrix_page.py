"""Page « Matrice de test », ouverte depuis le menu Outils."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)
from i18n import tr


class TestMatrixPageMixin:
    def _lines_mm_row(self, spin_box):
        row_layout = QHBoxLayout()
        lbl_dpi = QLabel()
        lbl_dpi.setStyleSheet("color: #888888;")

        def refresh_dpi(value, _lbl=lbl_dpi):
            _lbl.setText(f"≈ {value * 25.4:.0f} DPI")

        spin_box.valueChanged.connect(refresh_dpi)
        refresh_dpi(spin_box.value())

        row_layout.addWidget(spin_box)
        row_layout.addWidget(lbl_dpi)
        spin_box.dpi_label = lbl_dpi
        spin_box.dpi_row_layout = row_layout
        return row_layout

    def _build_test_matrix_page(self):
        """Page « Matrice de test », ouverte depuis le menu Outils."""
        tab_matrix = QWidget()
        self.form_matrix = QFormLayout(tab_matrix)

        self.combo_mat_mode = QComboBox()
        self.combo_mat_mode.addItems(
            [
                tr("ui.material_mode_engraving"),
                tr("ui.material_mode_cutting"),
            ]
        )
        self.combo_mat_mode.currentIndexChanged.connect(
            self.on_mat_mode_changed
        )

        self.spin_mat_off_x = QDoubleSpinBox()
        self.spin_mat_off_x.setRange(-1000.0, 1000.0)
        self.spin_mat_off_x.setValue(0.0)
        self.spin_mat_off_y = QDoubleSpinBox()
        self.spin_mat_off_y.setRange(-1000.0, 1000.0)
        self.spin_mat_off_y.setValue(0.0)

        self.lbl_mat_p1 = QLabel(tr("ui.mat_min_power"))
        self.spin_mat_min_p = QSpinBox()
        self.spin_mat_min_p.setRange(5, 100)
        self.spin_mat_min_p.setValue(10)

        self.spin_mat_max_p = QSpinBox()
        self.spin_mat_max_p.setRange(5, 100)
        self.spin_mat_max_p.setValue(80)
        self.spin_mat_steps_p = QSpinBox()
        self.spin_mat_steps_p.setRange(2, 20)
        self.spin_mat_steps_p.setValue(5)

        self.spin_mat_min_passes = QSpinBox()
        self.spin_mat_min_passes.setRange(1, 20)
        self.spin_mat_min_passes.setValue(1)
        self.spin_mat_max_passes = QSpinBox()
        self.spin_mat_max_passes.setRange(1, 20)
        self.spin_mat_max_passes.setValue(5)
        self.spin_mat_steps_passes = QSpinBox()
        self.spin_mat_steps_passes.setRange(2, 20)
        self.spin_mat_steps_passes.setValue(5)

        self.spin_mat_min_s = QSpinBox()
        self.spin_mat_min_s.setRange(100, 20000)
        self.spin_mat_min_s.setValue(1000)
        self.spin_mat_max_s = QSpinBox()
        self.spin_mat_max_s.setRange(100, 20000)
        self.spin_mat_max_s.setValue(5000)
        self.spin_mat_steps_s = QSpinBox()
        self.spin_mat_steps_s.setRange(2, 20)
        self.spin_mat_steps_s.setValue(5)

        self.spin_mat_size = QDoubleSpinBox()
        self.spin_mat_size.setRange(2.0, 50.0)
        self.spin_mat_size.setValue(10.0)
        self.spin_mat_gap = QDoubleSpinBox()
        self.spin_mat_gap.setRange(0.5, 20.0)
        self.spin_mat_gap.setValue(3.0)

        self.spin_mat_lmm = QDoubleSpinBox()
        self.spin_mat_lmm.setRange(1.0, 50.0)
        self.spin_mat_lmm.setValue(self.spin_lmm.value())
        self.spin_mat_lmm.setEnabled(False)
        self.spin_mat_lmm.setToolTip(tr("ui.mat_lmm_auto_tooltip"))

        self.combo_mat_laser_cmd = QComboBox()
        self.combo_mat_laser_cmd.addItems(
            ["M4 (Dynamic Power)", "M3 (Constant Power)"]
        )

        self.chk_mat_homing = QCheckBox(tr("ui.mat_homing"))
        self.chk_mat_homing.setChecked(False)

        btn_gen_matrix = QPushButton(tr("ui.gen_test_matrix"))
        btn_gen_matrix.setStyleSheet(
            "background-color: #d35400; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        btn_gen_matrix.clicked.connect(self.generate_test_matrix)

        self.form_matrix.addRow(tr("ui.test_mode"), self.combo_mat_mode)
        self.form_matrix.addRow(tr("ui.mat_offset_x"), self.spin_mat_off_x)
        self.form_matrix.addRow(tr("ui.mat_offset_y"), self.spin_mat_off_y)
        self.form_matrix.addRow(self.lbl_mat_p1, self.spin_mat_min_p)
        self.form_matrix.addRow(tr("ui.mat_max_power"), self.spin_mat_max_p)
        self.form_matrix.addRow(tr("ui.mat_power_step"), self.spin_mat_steps_p)
        self.form_matrix.addRow(
            tr("ui.mat_min_passes"), self.spin_mat_min_passes
        )
        self.form_matrix.addRow(
            tr("ui.mat_max_passes"), self.spin_mat_max_passes
        )
        self.form_matrix.addRow(
            tr("ui.mat_passes_step"), self.spin_mat_steps_passes
        )
        self.form_matrix.addRow(tr("ui.mat_min_speed"), self.spin_mat_min_s)
        self.form_matrix.addRow(tr("ui.mat_max_speed"), self.spin_mat_max_s)
        self.form_matrix.addRow(tr("ui.mat_speed_step"), self.spin_mat_steps_s)
        self.form_matrix.addRow(tr("ui.mat_square_size"), self.spin_mat_size)
        self.form_matrix.addRow(tr("ui.mat_spacing"), self.spin_mat_gap)
        self.form_matrix.addRow(
            tr("ui.mat_lmm"), self._lines_mm_row(self.spin_mat_lmm)
        )
        self.form_matrix.addRow(
            tr("ui.mat_laser_cmd"), self.combo_mat_laser_cmd
        )
        self.form_matrix.addRow("", self.chk_mat_homing)
        self.form_matrix.addRow("", btn_gen_matrix)
        # Affichée dans une fenêtre du menu (show_settings_window)
        self.tab_matrix = tab_matrix

        self.on_mat_mode_changed(0)
