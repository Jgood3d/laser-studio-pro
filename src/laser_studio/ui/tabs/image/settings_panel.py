"""Réglages de l'onglet « Graver une image » (panneau de gauche)."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.tabs.image.material_combo import MaterialComboBox
from laser_studio.ui.tabs.image.resolution_box import ResolutionBox
from laser_studio.ui.widgets import SliderWithButtons

# Algorithmes de tramage, dans l'ordre de la liste.
ALGORITHMS = (
    "Floyd-Steinberg",
    "Jarvis, Judice & Ninke",
    "Stucki",
    "Atkinson",
    "Sierra",
    "Sierra Lite (rapide)",
    "Burkes",
    "Bayer 2x2 (ordonné)",
    "Bayer 4x4 (ordonné)",
    "Bayer 8x8 (ordonné)",
    "Seuil Simple (Binaire)",
    "Niveaux de Gris",
)


class ImageSettingsPanel(QWidget):
    """Taille et décalage de l'image, réglages photo, matière, tramage et
    résolution.

    Il ne traite pas l'image : ses champs émettent des signaux, auxquels la
    fenêtre (plus tard un contrôleur) s'abonne :

        panel = ImageSettingsPanel()
        panel.processing_changed.connect(self.update_image_processing)
        panel.size_changed.connect(self.on_dimension_changed)

    Les champs restent lisibles directement (width_spin, brightness_slider,
    algorithm_combo, lines_per_mm_spin...). Ctrl+Z / Ctrl+Y, dans le
    panneau, émettent undo_requested / redo_requested.
    """

    load_requested = pyqtSignal()
    # Un réglage du tramage a changé (luminosité, contraste, gamma,
    # netteté, négatif, algorithme, lignes/mm) : l'image est à retraiter.
    processing_changed = pyqtSignal()
    # Matière choisie : "dark" (fond noir) ou "light" (fond clair).
    material_changed = pyqtSignal(str)
    # Taille de l'image modifiée : axe ("w" ou "h") et valeur en mm.
    size_changed = pyqtSignal(str, float)
    # Mode de saisie de la résolution (voir ResolutionBox).
    resolution_mode_changed = pyqtSignal(int)
    # Résolution en lignes/mm, et en DPI.
    lines_per_mm_changed = pyqtSignal(float)
    dpi_changed = pyqtSignal(float)
    configure_focal_requested = pyqtSignal()
    save_as_focal_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        load_button = QPushButton(tr("img.load"))
        load_button.clicked.connect(self.load_requested)
        layout.addRow(load_button)  # toute la largeur du panneau
        self._build_size_fields()
        layout.addRow(tr("dim.width"), self.width_spin)
        layout.addRow(tr("dim.height"), self.height_spin)
        layout.addRow(self.keep_ratio_check)  # toute la largeur du panneau
        # Décalage X / Y du job sur le plateau.
        layout.addRow(tr("dim.offset_x"), self.offset_x_spin)
        layout.addRow(tr("dim.offset_y"), self.offset_y_spin)
        self._build_photo_fields()
        layout.addRow(tr("img.brightness"), self._brightness_row)
        layout.addRow(tr("img.contrast"), self._contrast_row)
        layout.addRow(tr("img.gamma"), self._gamma_row)
        layout.addRow(tr("img.sharpness"), self._sharpness_row)
        layout.addRow(tr("img.material_bg"), self._material_combo())
        layout.addRow("", self.invert_check)
        layout.addRow(tr("img.algorithm"), self._algorithm_combo())
        layout.addRow(tr("img.resolution"), self._resolution_box())
        self._shortcut(QKeySequence.StandardKey.Undo, self.undo_requested)
        self._shortcut(QKeySequence.StandardKey.Redo, self.redo_requested)

    def processing_settings(self):
        """Réglages du tramage, en valeurs : luminosité, contraste, gamma
        (× 100), netteté, négatif et algorithme."""
        return {
            "bright": self.brightness_slider.value(),
            "contrast": self.contrast_slider.value(),
            "gamma": self.gamma_slider.value(),
            "sharp": self.sharpness_slider.value(),
            "invert": self.invert_check.isChecked(),
            "algo": self.algorithm_combo.currentText(),
        }

    # -- construction

    def _build_size_fields(self):
        self.width_spin = self._spin(0.1, 2000.0, 100.0)
        self.width_spin.valueChanged.connect(
            lambda v: self.size_changed.emit("w", v)
        )
        self.height_spin = self._spin(0.1, 2000.0, 100.0)
        self.height_spin.valueChanged.connect(
            lambda v: self.size_changed.emit("h", v)
        )
        self.keep_ratio_check = QCheckBox(tr("dim.keep_ratio"))
        self.keep_ratio_check.setChecked(True)
        self.offset_x_spin = self._spin(-1000.0, 1000.0, 0.0)
        self.offset_y_spin = self._spin(-1000.0, 1000.0, 0.0)

    def _build_photo_fields(self):
        self._brightness_row = self._slider_row(-100, 100, 0)
        self._contrast_row = self._slider_row(-100, 100, 0)
        self._gamma_row = self._slider_row(
            10, 300, 100, step=10, formatter=lambda v: f"{v / 100.0:.2f}"
        )
        self._sharpness_row = self._slider_row(0, 100, 0)
        self.brightness_slider = self._brightness_row.slider
        self.contrast_slider = self._contrast_row.slider
        self.gamma_slider = self._gamma_row.slider
        self.sharpness_slider = self._sharpness_row.slider
        self.sharpness_slider.setToolTip(tr("img.sharpness_tip"))
        self.invert_check = QCheckBox(tr("img.invert"))
        self.invert_check.stateChanged.connect(self.processing_changed)

    def _material_combo(self):
        self.material_combo = MaterialComboBox()
        self.material_combo.material_changed.connect(self.material_changed)
        return self.material_combo

    def _algorithm_combo(self):
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(ALGORITHMS)
        self.algorithm_combo.currentIndexChanged.connect(
            self.processing_changed
        )
        return self.algorithm_combo

    def _resolution_box(self):
        """Résolution : ses signaux sont relayés par le panneau, et ses
        champs gardent leur nom ici (lines_per_mm_spin, dpi_spin...)."""
        box = ResolutionBox()
        box.lines_per_mm_changed.connect(self.processing_changed)
        box.lines_per_mm_changed.connect(self.lines_per_mm_changed)
        box.mode_changed.connect(self.resolution_mode_changed)
        box.dpi_changed.connect(self.dpi_changed)
        box.configure_focal_requested.connect(self.configure_focal_requested)
        box.save_as_focal_requested.connect(self.save_as_focal_requested)
        self.resolution_box = box
        self.lines_per_mm_spin = box.lines_per_mm_spin
        self.resolution_mode_combo = box.mode_combo
        self.dpi_spin = box.dpi_spin
        self.focal_info_label = box.focal_info_label
        self.resolution_stack = box.stack
        self.resolution_quality_label = box.quality_label
        return box

    @staticmethod
    def _spin(minimum, maximum, value):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def _slider_row(self, minimum, maximum, value, **options):
        """Curseur du tramage : tout changement est à retraiter."""
        row = SliderWithButtons(minimum, maximum, value, **options)
        row.value_changed.connect(self.processing_changed)
        return row

    def _shortcut(self, key, signal):
        """Raccourci actif quand le panneau ou l'un de ses champs a le
        focus."""
        shortcut = QShortcut(key, self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(signal)
