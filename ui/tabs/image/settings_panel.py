"""Réglages de l'onglet « Graver une image » (panneau de gauche)."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.widgets import AutoHideLabel

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
# Modes de saisie de la résolution, dans l'ordre de la liste (et des pages
# de resolution_stack).
RESOLUTION_LMM, RESOLUTION_DPI, RESOLUTION_FOCAL = 0, 1, 2


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
    # Mode de saisie de la résolution (RESOLUTION_LMM, _DPI ou _FOCAL).
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
        layout.addRow(
            tr("img.brightness"), self._slider_row(self.brightness_slider)
        )
        layout.addRow(
            tr("img.contrast"), self._slider_row(self.contrast_slider)
        )
        layout.addRow(
            tr("img.gamma"),
            self._slider_row(
                self.gamma_slider,
                step=10,
                formatter=lambda v: f"{v / 100.0:.2f}",
            ),
        )
        layout.addRow(
            tr("img.sharpness"), self._slider_row(self.sharpness_slider)
        )
        layout.addRow(tr("img.material_bg"), self._material_combo())
        layout.addRow("", self.invert_check)
        layout.addRow(tr("img.algorithm"), self._algorithm_combo())
        self._build_resolution_fields()
        layout.addRow(tr("img.resolution"), self.resolution_mode_combo)
        layout.addRow("", self.resolution_stack)
        layout.addRow("", self.resolution_quality_label)
        self._shortcut(QKeySequence.StandardKey.Undo, self.undo_requested)
        self._shortcut(QKeySequence.StandardKey.Redo, self.redo_requested)
        # Résolution calée sur la focale du laser au départ.
        self.resolution_mode_combo.setCurrentIndex(RESOLUTION_FOCAL)
        self.resolution_stack.setCurrentIndex(RESOLUTION_FOCAL)

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
        self.brightness_slider = self._slider(-100, 100, 0)
        self.contrast_slider = self._slider(-100, 100, 0)
        self.gamma_slider = self._slider(10, 300, 100)
        self.sharpness_slider = self._slider(0, 100, 0)
        self.sharpness_slider.setToolTip(tr("img.sharpness_tip"))
        self.invert_check = QCheckBox(tr("img.invert"))
        self.invert_check.stateChanged.connect(self.processing_changed)

    def _material_combo(self):
        """Matière : fond noir ou clair. Elle ne fait que cocher ou décocher
        « Inverser Couleurs » (voir la fenêtre) ; la case reste modifiable."""
        self.material_combo = QComboBox()
        self.material_combo.addItem(tr("img.bg_dark"), "dark")
        self.material_combo.addItem(tr("img.bg_light"), "light")
        # Fond clair = négatif désactivé (comportement historique).
        self.material_combo.setCurrentIndex(1)
        self.material_combo.setToolTip(tr("img.material_bg_tooltip"))
        # Les libellés sont longs (exemples de matières : 62 caractères en
        # français, 85 en allemand). Par défaut, une liste déroulante prend
        # la largeur de son élément le PLUS LONG comme largeur minimale. On
        # fixe donc une largeur minimale courte ; la liste ouverte, elle,
        # reste assez large pour tout lire.
        self.material_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.material_combo.setMinimumContentsLength(12)
        for i in range(self.material_combo.count()):
            self.material_combo.setItemData(
                i, self.material_combo.itemText(i), Qt.ItemDataRole.ToolTipRole
            )
        popup = self.material_combo.view()
        popup.setMinimumWidth(popup.sizeHintForColumn(0) + 24)
        self.material_combo.currentIndexChanged.connect(
            lambda _index: self.material_changed.emit(
                self.material_combo.currentData()
            )
        )
        return self.material_combo

    def _algorithm_combo(self):
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(ALGORITHMS)
        self.algorithm_combo.currentIndexChanged.connect(
            self.processing_changed
        )
        return self.algorithm_combo

    def _build_resolution_fields(self):
        """Résolution : en lignes/mm, en DPI, ou calée sur la focale du
        laser. Une page par mode dans resolution_stack."""
        self.lines_per_mm_spin = self._spin(1.0, 50.0, 10.0)
        self.lines_per_mm_spin.valueChanged.connect(self.processing_changed)
        self.lines_per_mm_spin.valueChanged.connect(self.lines_per_mm_changed)

        self.resolution_mode_combo = QComboBox()
        self.resolution_mode_combo.addItems(
            [tr("img.mode_lmm"), "DPI", tr("img.mode_focal")]
        )
        self.resolution_mode_combo.currentIndexChanged.connect(
            self.resolution_mode_changed
        )

        self.dpi_spin = self._spin(10.0, 2000.0, 254.0)
        self.dpi_spin.setDecimals(0)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.valueChanged.connect(self.dpi_changed)

        self.focal_info_label = QLabel()
        self.focal_info_label.setStyleSheet("color: #888888;")
        configure_button = QPushButton(tr("img.configure_focal"))
        configure_button.clicked.connect(self.configure_focal_requested)

        self.resolution_stack = QStackedWidget()
        # Hauteur de son contenu, sans s'étirer : sinon la place libre de
        # l'onglet allait dans la pile et écartait la liste « Résolution »,
        # le champ DPI et « Enregistrer comme focale ».
        self.resolution_stack.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.resolution_stack.addWidget(
            self._page(self.lines_per_mm_spin, self._save_as_focal_button())
        )
        self.resolution_stack.addWidget(
            self._page(self.dpi_spin, self._save_as_focal_button())
        )
        self.resolution_stack.addWidget(
            self._page(self.focal_info_label, configure_button)
        )

        self.resolution_quality_label = AutoHideLabel()
        self.resolution_quality_label.setWordWrap(True)

    def _save_as_focal_button(self):
        button = QPushButton(tr("img.save_as_focal"))
        button.clicked.connect(self.save_as_focal_requested)
        return button

    @staticmethod
    def _page(*widgets):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            layout.addWidget(widget)
        return page

    @staticmethod
    def _spin(minimum, maximum, value):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def _slider(self, minimum, maximum, value):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(self.processing_changed)
        return slider

    @staticmethod
    def _slider_row(slider, step=5, formatter=None):
        """Curseur entre deux boutons « - » / « + », et sa valeur."""
        layout = QHBoxLayout()
        minus = QPushButton("-")
        minus.setFixedWidth(30)
        plus = QPushButton("+")
        plus.setFixedWidth(30)
        minus.clicked.connect(lambda: slider.setValue(slider.value() - step))
        plus.clicked.connect(lambda: slider.setValue(slider.value() + step))
        value_label = QLabel()
        value_label.setFixedWidth(45)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formatter = formatter or str

        def refresh(value):
            value_label.setText(formatter(value))

        slider.valueChanged.connect(refresh)
        refresh(slider.value())
        layout.addWidget(minus)
        layout.addWidget(slider)
        layout.addWidget(plus)
        layout.addWidget(value_label)
        return layout

    def _shortcut(self, key, signal):
        """Raccourci actif quand le panneau ou l'un de ses champs a le
        focus."""
        shortcut = QShortcut(key, self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(signal)
