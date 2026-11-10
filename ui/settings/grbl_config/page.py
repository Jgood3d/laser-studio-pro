"""Page « Configuration GRBL », ouverte depuis le menu Paramètres."""

from PyQt6.QtCore import pyqtSignal
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


class GrblConfigPage(QWidget):
    """Commande laser, surbalayage, décalage aller/retour, G-Code de début
    et de fin, réglages GRBL complets ($$).

    Elle ne parle pas au graveur : ses boutons et le décalage émettent des
    signaux, auxquels la fenêtre (plus tard un contrôleur) s'abonne :

        page = GrblConfigPage()
        page.read_settings_requested.connect(self.read_grbl_settings)
        page.scan_offset_changed.connect(self._schedule_layer_persist)

    Les champs restent lisibles directement (laser_cmd_combo, smax_spin,
    homing_check, overscan_check, safe_cut_order_check,
    overscan_mode_combo, overscan_dist_spin, overscan_pct_spin,
    scan_offset_spin, start_gcode_edit, end_gcode_edit,
    grbl_settings_edit). La page affiche elle-même la valeur du
    surbalayage qui correspond au mode choisi (distance ou pourcentage).
    """

    bidir_test_requested = pyqtSignal()
    # Décalage des lignes retour, en mm.
    scan_offset_changed = pyqtSignal(float)
    read_settings_requested = pyqtSignal()
    send_settings_requested = pyqtSignal()
    export_settings_requested = pyqtSignal()
    import_settings_requested = pyqtSignal()
    link_settings_to_profile_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self._build_fields()
        layout.addRow(tr("ui.gcode_laser_cmd"), self.laser_cmd_combo)
        layout.addRow(tr("ui.gcode_smax"), self.smax_spin)
        layout.addRow("", self.homing_check)
        layout.addRow("", self.overscan_check)
        layout.addRow("", self._safe_cut_order_check())
        layout.addRow(tr("ui.overscan_mode_label"), self.overscan_mode_combo)
        layout.addRow(tr("ui.overscan_value_label"), self._overscan_stack)
        layout.addRow(tr("ui.scan_offset_label"), self._scan_offset_spin())
        layout.addRow("", self._bidir_test_button())
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
        """Réglages GRBL complets ($$) : lire, envoyer, exporter, importer,
        lier au profil machine."""
        box = QGroupBox(tr("ui.grbl_settings_box"))
        layout = QVBoxLayout()
        self.grbl_settings_edit = QTextEdit()
        self.grbl_settings_edit.setPlaceholderText(
            tr("ui.grbl_settings_placeholder")
        )
        self.grbl_settings_edit.setMaximumHeight(140)
        self.grbl_settings_edit.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.grbl_settings_edit)

        buttons = QHBoxLayout()
        for key, signal in (
            ("ui.grbl_read", self.read_settings_requested),
            ("ui.grbl_send", self.send_settings_requested),
            ("ui.grbl_export", self.export_settings_requested),
            ("ui.grbl_import", self.import_settings_requested),
        ):
            buttons.addWidget(self._button(key, signal))
        layout.addLayout(buttons)
        layout.addWidget(
            self._button(
                "ui.grbl_link_profile", self.link_settings_to_profile_requested
            )
        )
        box.setLayout(layout)
        return box

    @staticmethod
    def _button(key, signal):
        button = QPushButton(tr(key))
        button.clicked.connect(signal)
        return button

    # -- affichage

    def _show_overscan_value(self, mode):
        """Affiche la distance (mode fixe) ou le pourcentage."""
        self._overscan_stack.setCurrentIndex(mode)
