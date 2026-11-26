"""Page « Configuration GRBL », ouverte depuis le menu Paramètres."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.models.grbl import LASER_COMMANDS, ROTARY_AXES, ROTARY_DRIVES
from laser_studio.ui.binding import bind
from laser_studio.ui.settings.grbl_config.settings_box import GrblSettingsBox


class GrblConfigPage(QWidget):
    """Commande laser, surbalayage, décalage aller/retour, G-Code de début
    et de fin, réglages GRBL complets ($$).

    Simple vue : ses champs sont liés au modèle GrblConfig
    (models/grbl.py, voir ui/binding.py), qui porte les valeurs et leur
    enregistrement dans les profils machine. Elle ne parle pas au graveur :
    ses boutons et le décalage émettent des signaux, auxquels la fenêtre
    s'abonne :

        page = GrblConfigPage()
        page.read_settings_requested.connect(self.read_grbl_settings)
        page.scan_offset_changed.connect(self._schedule_layer_persist)

    Les champs restent lisibles directement (laser_cmd_combo, smax_spin,
    homing_check, overscan_check, safe_cut_order_check,
    overscan_mode_combo, overscan_dist_spin, overscan_pct_spin,
    scan_offset_spin, start_gcode_edit, end_gcode_edit,
    grbl_settings_edit, rotary_check, rotary_axis_combo, rotary_drive_combo, rotary_object_spin,
    rotary_roller_spin, rotary_turn_spin). La page affiche elle-même la valeur du
    surbalayage qui correspond au mode choisi (distance ou pourcentage).
    """

    bidir_test_requested = pyqtSignal()
    # Décalage des lignes retour, en mm.
    scan_offset_changed = pyqtSignal(float)
    # « Inclure $H » coché / décoché (à la main, ou d'office à la connexion
    # d'un graveur sans homing) : à mémoriser dans le profil de la machine.
    homing_changed = pyqtSignal(bool)
    read_settings_requested = pyqtSignal()
    send_settings_requested = pyqtSignal()
    export_settings_requested = pyqtSignal()
    import_settings_requested = pyqtSignal()
    link_settings_to_profile_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self._build_fields()
        self._build_rotary_fields()
        layout.addRow(tr("ui.gcode_laser_cmd"), self.laser_cmd_combo)
        layout.addRow(tr("ui.gcode_smax"), self.smax_spin)
        layout.addRow(tr("ui.frame_power_label"), self._frame_power_spin())
        layout.addRow("", self.homing_check)
        layout.addRow("", self.overscan_check)
        layout.addRow("", self._safe_cut_order_check())
        layout.addRow(tr("ui.overscan_mode_label"), self.overscan_mode_combo)
        layout.addRow(tr("ui.overscan_value_label"), self._overscan_stack)
        layout.addRow(tr("ui.scan_offset_label"), self._scan_offset_spin())
        layout.addRow("", self._bidir_test_button())
        layout.addRow("", self.rotary_check)
        layout.addRow(tr("ui.rotary_axis_label"), self.rotary_axis_combo)
        layout.addRow(tr("ui.rotary_drive_label"), self.rotary_drive_combo)
        layout.addRow(tr("ui.rotary_object_label"), self.rotary_object_spin)
        layout.addRow(tr("ui.rotary_roller_label"), self.rotary_roller_spin)
        layout.addRow(tr("ui.rotary_turn_label"), self.rotary_turn_spin)
        layout.addRow(tr("ui.gcode_start"), self.start_gcode_edit)
        layout.addRow(tr("ui.gcode_end"), self.end_gcode_edit)
        layout.addRow(self._grbl_settings_box())

    # -- construction

    def _build_fields(self):
        """Champs de la commande laser, du surbalayage et du G-Code de
        début et de fin."""
        self.laser_cmd_combo = QComboBox()
        self.laser_cmd_combo.addItems(
            ["M4 (Dynamic Power)", "M3 (Constant Power)"]
        )
        self.smax_spin = QSpinBox()
        self.smax_spin.setRange(1, 10000)
        self.smax_spin.setValue(1000)
        self.homing_check = QCheckBox(tr("ui.grbl_homing"))
        # Homing automatique au démarrage du job : activé d'office.
        self.homing_check.setChecked(True)
        self.homing_check.toggled.connect(self.homing_changed)
        self.overscan_check = QCheckBox(tr("ui.overscan_enabled"))
        self.overscan_check.setChecked(True)

        self.overscan_mode_combo = QComboBox()
        self.overscan_mode_combo.addItems(
            [tr("ui.overscan_mode_fixed"), tr("ui.overscan_mode_pct")]
        )
        self.overscan_mode_combo.currentIndexChanged.connect(
            self._show_overscan_value
        )
        self.overscan_dist_spin = self._overscan_spin(2.5, " mm")
        self.overscan_pct_spin = self._overscan_spin(5.0, " %")
        self._overscan_stack = QStackedWidget()
        self._overscan_stack.addWidget(self.overscan_dist_spin)
        self._overscan_stack.addWidget(self.overscan_pct_spin)
        self._overscan_stack.setFixedHeight(28)

        self.start_gcode_edit = self._gcode_edit(
            "G21 ; Unités mm\nG90 ; Absolu"
        )
        self.end_gcode_edit = self._gcode_edit(
            "M5 ; Extinction Laser\nG0 X0 Y0 ; Retour origine"
        )

    def _build_rotary_fields(self):
        """Axe rotatif (gcode/rotary.py) : activation, axe, entraînement et dimensions."""
        self.rotary_check = QCheckBox(tr("ui.rotary_enabled"))
        self.rotary_check.setToolTip(tr("ui.rotary_tip"))
        self.rotary_axis_combo = QComboBox()
        self.rotary_axis_combo.addItems([tr("ui.rotary_axis_y"), tr("ui.rotary_axis_a")])
        self.rotary_drive_combo = QComboBox()
        self.rotary_drive_combo.addItems([tr("ui.rotary_drive_chuck"), tr("ui.rotary_drive_roller")])
        self.rotary_object_spin = self._rotary_spin(1.0, 2000.0, 60.0, 1)
        self.rotary_roller_spin = self._rotary_spin(1.0, 500.0, 20.0, 1)
        self.rotary_turn_spin = self._rotary_spin(1.0, 100000.0, 360.0, 2)
        self.rotary_turn_spin.setToolTip(tr("ui.rotary_turn_tip"))
        self.rotary_check.toggled.connect(self._update_rotary_fields)
        self.rotary_axis_combo.currentIndexChanged.connect(self._update_rotary_fields)
        self.rotary_drive_combo.currentIndexChanged.connect(self._update_rotary_fields)
        self._update_rotary_fields()

    @staticmethod
    def _rotary_spin(minimum, maximum, value, decimals):
        """Dimension de l'axe rotatif, en mm."""
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.setSuffix(" mm")
        return spin

    def _update_rotary_fields(self, *_args):
        """Les réglages du rotatif ne servent que s'il est activé ; le diamètre des rouleaux seulement
        avec des rouleaux, la course par tour seulement sur l'axe Y (un axe A est en degrés)."""
        on = self.rotary_check.isChecked()
        self.rotary_axis_combo.setEnabled(on)
        self.rotary_drive_combo.setEnabled(on)
        self.rotary_object_spin.setEnabled(on)
        self.rotary_roller_spin.setEnabled(on and self.rotary_drive_combo.currentIndex() == 1)
        self.rotary_turn_spin.setEnabled(on and self.rotary_axis_combo.currentIndex() == 0)

    @staticmethod
    def _overscan_spin(value, suffix):
        """Valeur du surbalayage : distance (mm) ou part de la largeur (%)."""
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 50.0)
        spin.setSingleStep(0.1)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    @staticmethod
    def _gcode_edit(text):
        """Zone de G-Code ajouté au début ou à la fin du job."""
        edit = QTextEdit()
        edit.setMaximumHeight(45)
        edit.setPlainText(text)
        return edit

    def _safe_cut_order_check(self):
        self.safe_cut_order_check = QCheckBox(tr("ui.safe_cut_order"))
        self.safe_cut_order_check.setChecked(True)
        self.safe_cut_order_check.setToolTip(tr("ui.safe_cut_order_tip"))
        return self.safe_cut_order_check

    def _frame_power_spin(self):
        """Puissance du laser pendant le cadrage (% du S-Max), propre à la machine (mémorisée dans son
        profil) : une diode qui ne s'allume pas à 0,5 % se règle plus haut."""
        self.frame_power_spin = QDoubleSpinBox()
        self.frame_power_spin.setRange(0.0, 5.0)
        self.frame_power_spin.setSingleStep(0.1)
        self.frame_power_spin.setDecimals(1)
        self.frame_power_spin.setSuffix(" %")
        self.frame_power_spin.setToolTip(tr("ui.frame_power_tip"))
        return self.frame_power_spin

    def _scan_offset_spin(self):
        """Décalage aller/retour : compense le jeu mécanique et le délai
        d'allumage du laser entre les lignes gravées dans un sens et dans
        l'autre (propre à la machine, mémorisé dans son profil)."""
        self.scan_offset_spin = QDoubleSpinBox()
        self.scan_offset_spin.setRange(-2.0, 2.0)
        self.scan_offset_spin.setSingleStep(0.01)
        self.scan_offset_spin.setDecimals(2)
        self.scan_offset_spin.setValue(0.0)
        self.scan_offset_spin.setSuffix(" mm")
        self.scan_offset_spin.setToolTip(tr("ui.scan_offset_tip"))
        self.scan_offset_spin.valueChanged.connect(self.scan_offset_changed)
        return self.scan_offset_spin

    def _bidir_test_button(self):
        """Bouton du motif de test, pour trouver le bon décalage."""
        button = QPushButton(tr("ui.bidir_test_btn"))
        button.setToolTip(tr("ui.scan_offset_tip"))
        button.clicked.connect(self.bidir_test_requested)
        return button

    def _grbl_settings_box(self):
        """Réglages GRBL complets : ses signaux sont relayés par la page."""
        box = GrblSettingsBox()
        box.read_requested.connect(self.read_settings_requested)
        box.send_requested.connect(self.send_settings_requested)
        box.export_requested.connect(self.export_settings_requested)
        box.import_requested.connect(self.import_settings_requested)
        box.link_to_profile_requested.connect(
            self.link_settings_to_profile_requested
        )
        self.grbl_settings_edit = box.text_edit
        return box

    # -- affichage

    def _show_overscan_value(self, mode):
        """Affiche la distance (mode fixe) ou le pourcentage."""
        self._overscan_stack.setCurrentIndex(mode)

    def bind_settings(self, grbl):
        """Champs liés au modèle de la configuration GRBL (GrblConfig), que lit la logique."""
        bind(self.laser_cmd_combo, grbl, "laser_cmd",
             to_widget=LASER_COMMANDS.index, from_widget=lambda i: LASER_COMMANDS[max(i, 0)])
        for widget, field in ((self.smax_spin, "smax"), (self.homing_check, "homing_enabled"),
                              (self.overscan_check, "overscan_enabled"),
                              (self.safe_cut_order_check, "safe_cut_order"),
                              (self.overscan_mode_combo, "overscan_mode"),
                              (self.overscan_dist_spin, "overscan_dist_mm"),
                              (self.overscan_pct_spin, "overscan_pct"),
                              (self.scan_offset_spin, "scan_offset_mm"),
                              (self.frame_power_spin, "frame_power_pct"),
                              (self.start_gcode_edit, "start_gcode"),
                              (self.end_gcode_edit, "end_gcode"),
                              (self.grbl_settings_edit, "grbl_settings")):
            bind(widget, grbl, field)
        bind(self.rotary_axis_combo, grbl, "rotary_axis",
             to_widget=ROTARY_AXES.index, from_widget=lambda i: ROTARY_AXES[max(i, 0)])
        bind(self.rotary_drive_combo, grbl, "rotary_drive",
             to_widget=ROTARY_DRIVES.index, from_widget=lambda i: ROTARY_DRIVES[max(i, 0)])
        for widget, field in ((self.rotary_check, "rotary_enabled"), (self.rotary_object_spin, "rotary_object_mm"),
                              (self.rotary_roller_spin, "rotary_roller_mm"),
                              (self.rotary_turn_spin, "rotary_mm_per_turn")):
            bind(widget, grbl, field)
        self._update_rotary_fields()
