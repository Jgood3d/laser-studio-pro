"""Page « Paramètres du graveur », ouverte depuis le menu Paramètres."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from i18n import tr


class MachineParamsPageMixin:
    def _build_machine_params_page(self):
        """Page « Paramètres du graveur », ouverte depuis le menu."""
        tab_machine_params_content = QWidget()
        layout_machine_params = QVBoxLayout(tab_machine_params_content)

        machine_profiles_box = QGroupBox(tr("mach.profiles_box"))
        machine_profiles_layout = QVBoxLayout()
        self.combo_machine_profile = QComboBox()
        self.combo_machine_profile.currentIndexChanged.connect(
            self._on_machine_profile_selected
        )
        machine_profiles_layout.addWidget(self.combo_machine_profile)
        profile_btn_row = QHBoxLayout()
        btn_new_machine = QPushButton(tr("mach.new_machine"))
        btn_new_machine.clicked.connect(self._add_machine_profile)
        btn_update_machine = QPushButton(tr("mach.update"))
        btn_update_machine.clicked.connect(self._update_machine_profile)
        btn_del_machine = QPushButton(tr("mach.delete"))
        btn_del_machine.clicked.connect(self._delete_machine_profile)
        profile_btn_row.addWidget(btn_new_machine)
        profile_btn_row.addWidget(btn_update_machine)
        profile_btn_row.addWidget(btn_del_machine)
        machine_profiles_layout.addLayout(profile_btn_row)
        lbl_profile_info = QLabel(tr("mach.profile_info"))
        lbl_profile_info.setWordWrap(True)
        machine_profiles_layout.addWidget(lbl_profile_info)
        machine_profiles_box.setLayout(machine_profiles_layout)
        layout_machine_params.addWidget(machine_profiles_box)

        machine_bed_box = QGroupBox(tr("mach.bed_box"))
        machine_bed_layout = QFormLayout()
        self.spin_machine_w = QDoubleSpinBox()
        self.spin_machine_w.setRange(1.0, 5000.0)
        self.spin_machine_w.setValue(300.0)
        self.spin_machine_w.setSuffix(" mm")
        self.spin_machine_w.valueChanged.connect(self.update_vector_work_area)
        self.spin_machine_h = QDoubleSpinBox()
        self.spin_machine_h.setRange(1.0, 5000.0)
        self.spin_machine_h.setValue(200.0)
        self.spin_machine_h.setSuffix(" mm")
        self.spin_machine_h.valueChanged.connect(self.update_vector_work_area)
        machine_bed_layout.addRow(tr("mach.bed_w"), self.spin_machine_w)
        machine_bed_layout.addRow(tr("mach.bed_h"), self.spin_machine_h)
        lbl_machine_info = QLabel(tr("mach.bed_info"))
        lbl_machine_info.setWordWrap(True)
        machine_bed_layout.addRow(lbl_machine_info)
        machine_bed_box.setLayout(machine_bed_layout)
        layout_machine_params.addWidget(machine_bed_box)

        machine_laser_box = QGroupBox(tr("mach.laser_box"))
        machine_laser_layout = QFormLayout()
        self.spin_machine_focal = QDoubleSpinBox()
        self.spin_machine_focal.setRange(0.01, 2.0)
        self.spin_machine_focal.setSingleStep(0.01)
        self.spin_machine_focal.setDecimals(3)
        self.spin_machine_focal.setValue(0.10)
        self.spin_machine_focal.setSuffix(" mm")
        self.spin_machine_focal.valueChanged.connect(
            self._on_machine_focal_changed
        )
        machine_laser_layout.addRow(
            tr("mach.focal_size"), self.spin_machine_focal
        )
        lbl_focal_help = QLabel(tr("mach.focal_help"))
        lbl_focal_help.setWordWrap(True)
        machine_laser_layout.addRow(lbl_focal_help)
        machine_laser_box.setLayout(machine_laser_layout)
        layout_machine_params.addWidget(machine_laser_box)

        machine_limits_box = QGroupBox(tr("mach.limits_box"))
        machine_limits_layout = QFormLayout()
        self.spin_machine_max_speed = QDoubleSpinBox()
        self.spin_machine_max_speed.setRange(1.0, 50000.0)
        self.spin_machine_max_speed.setValue(6000.0)
        self.spin_machine_max_speed.setSuffix(" mm/min")
        self.spin_machine_accel = QDoubleSpinBox()
        self.spin_machine_accel.setRange(1.0, 20000.0)
        self.spin_machine_accel.setValue(500.0)
        self.spin_machine_accel.setSuffix(" mm/s²")
        machine_limits_layout.addRow(
            tr("mach.max_speed"), self.spin_machine_max_speed
        )
        machine_limits_layout.addRow(tr("mach.accel"), self.spin_machine_accel)
        lbl_limits_info = QLabel(tr("mach.limits_info"))
        lbl_limits_info.setWordWrap(True)
        machine_limits_layout.addRow(lbl_limits_info)
        machine_limits_box.setLayout(machine_limits_layout)
        layout_machine_params.addWidget(machine_limits_box)
        layout_machine_params.addStretch()

        tab_machine_params = QScrollArea()
        tab_machine_params.setWidget(tab_machine_params_content)
        tab_machine_params.setWidgetResizable(True)
        tab_machine_params.setFrameShape(QScrollArea.Shape.NoFrame)
        # Affichée dans une fenêtre du menu (show_settings_window)
        self.tab_machine_params = tab_machine_params
        return layout_machine_params
