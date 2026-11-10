"""Page « Matrice de test », ouverte depuis le menu Outils."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)

from image import matrix as matrix_image
from i18n import tr
from ui.settings.test_matrix.tile_picker import TilePicker

HINT_STYLE = "color: #888888;"
ENGRAVING, CUTTING = 0, 1


class TestMatrixPage(QWidget):
    """Réglages de la matrice de test : puissances, passes, vitesses, cases.

    En gravure, elle propose aussi un test à partir d'une image : chaque
    case grave la même zone de l'image, choisie dans un aperçu. Elle ne
    génère rien et ne charge aucun fichier : ses boutons émettent des
    signaux, et la fenêtre lui transmet l'image source :

        page = TestMatrixPage(lines_mm=10.0)
        page.generate_requested.connect(self.generate_test_matrix)
        page.choose_image_requested.connect(self._mat_choose_image)
        page.set_source_image(gray_image, "photo.png", width_mm=120.0)
        params = page.matrix_params()
    """

    generate_requested = pyqtSignal()
    choose_image_requested = pyqtSignal()
    use_loaded_image_requested = pyqtSignal()
    # Test à partir d'une image coché (True) ou décoché.
    image_test_toggled = pyqtSignal(bool)

    def __init__(self, lines_mm, parent=None):
        super().__init__(parent)
        self.source_image = None  # image source en niveaux de gris (PIL)
        self._form = QFormLayout(self)
        self._build_fields(lines_mm)
        self._image_group = self._build_image_group()
        self._form.addRow(self._image_group)
        self._form.addRow("", self._generate_button())
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed(ENGRAVING)

    # -- état reçu de la fenêtre / du contrôleur

    def set_lines_mm(self, value):
        """Lignes/mm de la gravure, reprises de « Graver une image »."""
        self.lines_mm_spin.setValue(value)

    def set_source_image(self, gray_image, name, width_mm=None):
        """Image du test : `gray_image` (PIL, niveaux de gris), son nom
        affiché et, si connue, sa largeur réelle en mm."""
        self.source_image = gray_image
        self.image_name_label.setText(name)
        if width_mm and width_mm > 0:
            self.image_width_spin.blockSignals(True)
            self.image_width_spin.setValue(min(max(width_mm, 1.0), 5000.0))
            self.image_width_spin.blockSignals(False)
        self.tile_picker.set_image(gray_image)
        self._update_tile()

    def set_image_test_checked(self, checked):
        """Coche ou décoche le test à partir d'une image."""
        self._image_group.setChecked(checked)

    # -- valeurs lues par la fenêtre / le contrôleur

    def is_engraving(self):
        """Vrai en mode gravure, faux en mode découpe."""
        return self.mode_combo.currentIndex() == ENGRAVING

    def image_test_enabled(self):
        """Vrai si chaque case doit graver une zone de l'image."""
        group = self._image_group
        return group.isEnabled() and group.isChecked()

    def tile_settings(self):
        """Zone d'image de chaque case : (largeur réelle de l'image en mm,
        largeur et hauteur de la zone en mm, centre choisi dans l'aperçu)."""
        return (
            self.image_width_spin.value(),
            self.tile_width_spin.value(),
            self.tile_height_spin.value(),
            *self.tile_picker.center(),
        )

    def matrix_params(self):
        """Réglages de la matrice, en valeurs métier (%, mm, mm/min)."""
        return {
            "min_power": self.min_power_spin.value(),
            "max_power": self.max_power_spin.value(),
            "steps_power": self.power_steps_spin.value(),
            "single_power": self.min_power_spin.value(),
            "min_passes": self.min_passes_spin.value(),
            "max_passes": self.max_passes_spin.value(),
            "steps_passes": self.passes_steps_spin.value(),
            "min_speed": self.min_speed_spin.value(),
            "max_speed": self.max_speed_spin.value(),
            "steps_speed": self.speed_steps_spin.value(),
            "size_square": self.square_size_spin.value(),
            "gap": self.gap_spin.value(),
            "lines_mm": self.lines_mm_spin.value(),
            "matrix_offset_x": self.offset_x_spin.value(),
            "matrix_offset_y": self.offset_y_spin.value(),
            "laser_cmd": self.laser_cmd_combo.currentText().split()[0],
            "homing": self.homing_check.isChecked(),
        }

    # -- construction

    def _build_fields(self, lines_mm):
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                tr("ui.material_mode_engraving"),
                tr("ui.material_mode_cutting"),
            ]
        )
        self.offset_x_spin = self._double_spin(-1000.0, 1000.0, 0.0)
        self.offset_y_spin = self._double_spin(-1000.0, 1000.0, 0.0)
        self._min_power_label = QLabel(tr("ui.mat_min_power"))
        self.min_power_spin = self._spin(5, 100, 10)
        self.max_power_spin = self._spin(5, 100, 80)
        self.power_steps_spin = self._spin(2, 20, 5)
        self.min_passes_spin = self._spin(1, 20, 1)
        self.max_passes_spin = self._spin(1, 20, 5)
        self.passes_steps_spin = self._spin(2, 20, 5)
        self.min_speed_spin = self._spin(100, 20000, 1000)
        self.max_speed_spin = self._spin(100, 20000, 5000)
        self.speed_steps_spin = self._spin(2, 20, 5)
        self.square_size_spin = self._double_spin(2.0, 50.0, 10.0)
        self.gap_spin = self._double_spin(0.5, 20.0, 3.0)
        self.lines_mm_spin = self._double_spin(1.0, 50.0, lines_mm)
        # Repris de « Graver une image » (set_lines_mm), pas modifiable ici.
        self.lines_mm_spin.setEnabled(False)
        self.lines_mm_spin.setToolTip(tr("ui.mat_lmm_auto_tooltip"))
        self.laser_cmd_combo = QComboBox()
        self.laser_cmd_combo.addItems(
            ["M4 (Dynamic Power)", "M3 (Constant Power)"]
        )
        self.homing_check = QCheckBox(tr("ui.mat_homing"))
        self.homing_check.setChecked(False)

        form = self._form
        form.addRow(tr("ui.test_mode"), self.mode_combo)
        form.addRow(tr("ui.mat_offset_x"), self.offset_x_spin)
        form.addRow(tr("ui.mat_offset_y"), self.offset_y_spin)
        form.addRow(self._min_power_label, self.min_power_spin)
        form.addRow(tr("ui.mat_max_power"), self.max_power_spin)
        form.addRow(tr("ui.mat_power_step"), self.power_steps_spin)
        form.addRow(tr("ui.mat_min_passes"), self.min_passes_spin)
        form.addRow(tr("ui.mat_max_passes"), self.max_passes_spin)
        form.addRow(tr("ui.mat_passes_step"), self.passes_steps_spin)
        form.addRow(tr("ui.mat_min_speed"), self.min_speed_spin)
        form.addRow(tr("ui.mat_max_speed"), self.max_speed_spin)
        form.addRow(tr("ui.mat_speed_step"), self.speed_steps_spin)
        form.addRow(tr("ui.mat_square_size"), self.square_size_spin)
        form.addRow(tr("ui.mat_spacing"), self.gap_spin)
        form.addRow(tr("ui.mat_lmm"), self._lines_mm_row())
        form.addRow(tr("ui.mat_laser_cmd"), self.laser_cmd_combo)
        form.addRow("", self.homing_check)

    def _lines_mm_row(self):
        """Lignes/mm, suivies de leur équivalent en DPI."""
        self._lines_mm_row_layout = QHBoxLayout()
        self._dpi_label = QLabel()
        self._dpi_label.setStyleSheet(HINT_STYLE)
        self.lines_mm_spin.valueChanged.connect(self._refresh_dpi)
        self._refresh_dpi(self.lines_mm_spin.value())
        self._lines_mm_row_layout.addWidget(self.lines_mm_spin)
        self._lines_mm_row_layout.addWidget(self._dpi_label)
        return self._lines_mm_row_layout

    def _build_image_group(self):
        """Cadre « Test à partir d'une image » : choix de l'image, taille
        de la zone, aperçu."""
        group = QGroupBox(tr("ui.mat_image_group"))
        group.setCheckable(True)
        group.setChecked(False)
        layout = QFormLayout(group)

        hint = QLabel(tr("ui.mat_image_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_STYLE)
        layout.addRow(hint)

        choose_button = QPushButton(tr("ui.mat_image_choose"))
        choose_button.clicked.connect(self.choose_image_requested)
        loaded_button = QPushButton(tr("ui.mat_image_use_loaded"))
        loaded_button.setToolTip(tr("ui.mat_image_use_loaded_tip"))
        loaded_button.clicked.connect(self.use_loaded_image_requested)
        buttons = QHBoxLayout()
        buttons.addWidget(choose_button)
        buttons.addWidget(loaded_button)
        layout.addRow(buttons)

        self.image_name_label = QLabel(tr("ui.mat_image_none"))
        self.image_name_label.setWordWrap(True)
        layout.addRow(self.image_name_label)

        self.image_width_spin = self._mm_spin(1.0, 5000.0, 100.0)
        self.image_width_spin.setToolTip(tr("ui.mat_image_width_tip"))
        self.tile_width_spin = self._mm_spin(1.0, 200.0, 15.0)
        self.tile_height_spin = self._mm_spin(1.0, 200.0, 15.0)
        layout.addRow(tr("ui.mat_image_width"), self.image_width_spin)
        layout.addRow(tr("ui.mat_tile_width"), self.tile_width_spin)
        layout.addRow(tr("ui.mat_tile_height"), self.tile_height_spin)

        self.tile_picker = TilePicker()
        layout.addRow(self.tile_picker)
        self.tile_info_label = QLabel()
        self.tile_info_label.setWordWrap(True)
        self.tile_info_label.setStyleSheet(HINT_STYLE)
        layout.addRow(self.tile_info_label)

        for spin in (
            self.image_width_spin,
            self.tile_width_spin,
            self.tile_height_spin,
        ):
            spin.valueChanged.connect(self._update_tile)
        group.toggled.connect(self._on_image_test_toggled)
        return group

    def _generate_button(self):
        """Bouton orange « Générer la matrice de test »."""
        button = QPushButton(tr("ui.gen_test_matrix"))
        button.setStyleSheet(
            "background-color: #d35400; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        button.clicked.connect(self.generate_requested)
        return button

    @staticmethod
    def _spin(low, high, value):
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setValue(value)
        return spin

    @staticmethod
    def _double_spin(low, high, value):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setValue(value)
        return spin

    @classmethod
    def _mm_spin(cls, low, high, value):
        spin = cls._double_spin(low, high, value)
        spin.setSuffix(" mm")
        return spin

    # -- réactions internes

    def _refresh_dpi(self, value):
        self._dpi_label.setText(f"≈ {value * 25.4:.0f} DPI")

    def _on_mode_changed(self, index):
        """Gravure : plage de puissances. Découpe : une puissance et une
        plage de passes. Le test à partir d'une image n'existe qu'en
        gravure."""
        engraving = index == ENGRAVING
        self._min_power_label.setText(
            tr("ui.mat_min_power") if engraving else tr("ui.mat_unique_power")
        )
        for field in (self.max_power_spin, self.power_steps_spin):
            self._set_row_visible(field, engraving)
        for field in (
            self.min_passes_spin,
            self.max_passes_spin,
            self.passes_steps_spin,
        ):
            self._set_row_visible(field, not engraving)
        self.lines_mm_spin.setVisible(engraving)
        self._dpi_label.setVisible(engraving)
        self._form.labelForField(self._lines_mm_row_layout).setVisible(
            engraving
        )
        self._update_image_test_state()

    def _set_row_visible(self, field, visible):
        field.setVisible(visible)
        self._form.labelForField(field).setVisible(visible)

    def _on_image_test_toggled(self, checked):
        self.image_test_toggled.emit(checked)
        self._update_image_test_state()

    def _update_image_test_state(self):
        engraving = self.is_engraving()
        self._image_group.setEnabled(engraving)
        use_image = engraving and self._image_group.isChecked()
        # La taille des cases vient alors de la zone d'image.
        self.square_size_spin.setEnabled(not use_image)
        self.square_size_spin.setToolTip(
            tr("ui.mat_size_from_image_tip") if use_image else ""
        )

    def _update_tile(self, *_args):
        """Cadre de la zone dans l'aperçu, et sa taille réelle."""
        src = self.source_image
        if src is None:
            self.tile_info_label.setText("")
            return
        image_w, tile_w, tile_h = self.tile_settings()[:3]
        args = (src.width, src.height, image_w, tile_w, tile_h)
        try:
            fw, fh = matrix_image.frame_fraction(*args)
            eff_w, eff_h = matrix_image.effective_tile_mm(*args)
        except ValueError:
            return
        self.tile_picker.set_frame_fraction(fw, fh)
        text = tr("ui.mat_tile_info").format(w=eff_w, h=eff_h, pct=fw * 100.0)
        if eff_w < tile_w - 1e-6 or eff_h < tile_h - 1e-6:
            text += "\n" + tr("ui.mat_tile_clipped").format(w=eff_w, h=eff_h)
        self.tile_info_label.setText(text)
