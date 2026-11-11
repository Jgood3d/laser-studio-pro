"""Onglet « Séparation Couleur / Verre » : réglages et aperçus."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.widgets import TabToolBar, ZoomableGraphicsView

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")
HINT_STYLE = "color: #888888;"
# Préréglages du calque couleur par support (index de la liste) :
# (saturation %, clarté %, diffusion en 1/100 mm), à calibrer à l'œil.
SUPPORT_PRESETS = {0: (140, 100, 15), 1: (170, 90, 60)}
# Aperçus, dans l'ordre des onglets.
PREVIEW_KEYS = (
    "sep.tab_original",
    "sep.tab_engraving",
    "sep.tab_print",
    "sep.tab_simulation",
)


class SeparationTab(QWidget):
    """Réglages de la séparation à gauche (plaque, recadrage, calque noir,
    calque couleur, simulation), aperçus à droite. Accepte le
    glisser-déposer d'une image.

    Elle ne calcule rien : ses réglages émettent des signaux, auxquels la
    fenêtre s'abonne :

        tab = SeparationTab()
        tab.tone_changed.connect(...)       # calque noir à recalculer
        tab.preview_changed.connect(...)    # aperçus à redessiner

    La vue gère elle-même les proportions de la plaque (d'après celles de
    l'image, set_image_ratio), le recadrage actif ou non et les préréglages
    des supports. Les champs restent lisibles (plate_width_spin,
    saturation_slider...), et frame_args() donne le cadrage appliqué.
    """

    load_requested = pyqtSignal()
    # Chemin d'une image déposée sur l'onglet.
    image_dropped = pyqtSignal(str)
    # Plaque, recadrage ou gain changés : la tonalité est à renvoyer.
    tone_changed = pyqtSignal()
    # Réglage d'un aperçu changé : les aperçus sont à redessiner.
    preview_changed = pyqtSignal()
    gain_test_requested = pyqtSignal()
    export_requested = pyqtSignal()
    # Onglet d'aperçu affiché (index de PREVIEW_KEYS).
    preview_tab_changed = pyqtSignal(int)
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_ratio = None  # largeur / hauteur de l'image chargée
        self._block = False  # évite les boucles entre largeur et hauteur
        self.setAcceptDrops(True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        toolbar = TabToolBar(self)
        toolbar.fullscreen_requested.connect(self.fullscreen_requested)
        self._fullscreen_control = toolbar.fullscreen_action
        outer.addWidget(toolbar)

        body = QHBoxLayout()
        outer.addLayout(body, 1)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        load_button = QPushButton(tr("sep.load_image_btn"))
        load_button.clicked.connect(self.load_requested)
        layout.addWidget(load_button)
        layout.addWidget(self._hint("sep.drag_drop_hint", wrap=False))
        self.file_label = QLabel(tr("sep.no_image_loaded"))
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)
        layout.addWidget(self._plate_box())
        layout.addWidget(self._crop_box())
        self._update_crop_enabled()
        layout.addWidget(self._black_layer_box())
        layout.addWidget(self._color_layer_box())
        layout.addWidget(self._backlight_box())
        export_button = QPushButton(tr("sep.export_btn"))
        export_button.clicked.connect(self.export_requested)
        layout.addWidget(export_button)
        layout.addWidget(self._hint("sep.tip"))
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(360)
        body.addWidget(scroll)
        body.addWidget(self._previews(), 1)

    # -- construction

    @staticmethod
    def _hint(key, wrap=True):
        label = QLabel(tr(key))
        label.setWordWrap(wrap)
        label.setStyleSheet(HINT_STYLE)
        return label

    def _plate_box(self):
        """Plaque de verre : taille, résolution d'impression, cadrage."""
        box = QGroupBox(tr("sep.plate_title"))
        form = QFormLayout(box)
        self.plate_width_spin = QDoubleSpinBox()
        self.plate_width_spin.setRange(5, 2000)
        self.plate_width_spin.setValue(150)
        self.plate_height_spin = QDoubleSpinBox()
        self.plate_height_spin.setRange(5, 2000)
        self.plate_height_spin.setValue(100)
        self.print_dpi_spin = QSpinBox()
        self.print_dpi_spin.setRange(72, 1200)
        self.print_dpi_spin.setValue(300)
        self.framing_combo = QComboBox()
        self.framing_combo.addItems([tr("sep.crop_fit"), tr("sep.stretch")])
        self.keep_ratio_check = QCheckBox(tr("sep.keep_ratio"))
        self.keep_ratio_check.setChecked(True)
        self.plate_width_spin.valueChanged.connect(
            lambda _v: self._on_plate_changed("w")
        )
        self.plate_height_spin.valueChanged.connect(
            lambda _v: self._on_plate_changed("h")
        )
        self.keep_ratio_check.toggled.connect(self._on_keep_ratio)
        self.framing_combo.currentIndexChanged.connect(
            self._on_framing_changed
        )
        form.addRow(self.keep_ratio_check)
        form.addRow(tr("sep.width"), self.plate_width_spin)
        form.addRow(tr("sep.height"), self.plate_height_spin)
        form.addRow(tr("sep.print_dpi"), self.print_dpi_spin)
        form.addRow(tr("sep.framing"), self.framing_combo)
        self.engrave_dpi_label = QLabel()
        self.engrave_dpi_label.setWordWrap(True)
        form.addRow(self.engrave_dpi_label)
        form.addRow(self._hint("sep.sync_note"))
        return box

    def _crop_box(self):
        """Recadrage, quand la plaque a des proportions libres."""
        self.crop_box = QGroupBox(tr("sep.crop_title"))
        form = QFormLayout(self.crop_box)
        form.addRow(self._hint("sep.crop_hint"))
        percent = lambda v: f"{v} %"  # noqa: E731
        self.crop_zoom_slider = self._slider(
            form,
            "sep.crop_zoom",
            100,
            400,
            100,
            percent,
            self._on_crop_changed,
        )
        self.crop_x_slider = self._slider(
            form, "sep.crop_x", 0, 100, 50, percent, self._on_crop_changed
        )
        self.crop_y_slider = self._slider(
            form, "sep.crop_y", 0, 100, 50, percent, self._on_crop_changed
        )
        reset_button = QPushButton(tr("sep.crop_reset"))
        reset_button.clicked.connect(self.reset_crop)
        form.addRow(reset_button)
        return self.crop_box

    def _black_layer_box(self):
        """Calque noir : gain de point, et son test."""
        box = QGroupBox(tr("sep.black_layer_title"))
        form = QFormLayout(box)
        form.addRow(self._hint("sep.black_info"))
        self.gain_slider = self._slider(
            form,
            "sep.gain",
            0,
            20,
            0,
            str,
            self.tone_changed.emit,
            "sep.gain_tip",
        )
        gain_test_button = QPushButton(tr("sep.gain_test_btn"))
        gain_test_button.setToolTip(tr("sep.gain_test_tip"))
        gain_test_button.clicked.connect(self.gain_test_requested)
        form.addRow(gain_test_button)
        return box

    def _color_layer_box(self):
        """Calque couleur : support (préréglages), saturation, clarté,
        miroir à l'impression."""
        box = QGroupBox(tr("sep.color_layer_title"))
        form = QFormLayout(box)
        self.support_combo = QComboBox()
        self.support_combo.addItems(
            [
                tr("sep.transparent_film"),
                tr("sep.tracing_paper"),
                tr("sep.custom"),
            ]
        )
        self.support_combo.activated.connect(self._apply_support)
        form.addRow(tr("sep.support_medium"), self.support_combo)
        ratio = lambda v: f"{v / 100:.2f}"  # noqa: E731
        self.saturation_slider = self._slider(
            form,
            "sep.saturation",
            50,
            300,
            140,
            ratio,
            self.preview_changed.emit,
        )
        self.lightness_slider = self._slider(
            form,
            "sep.lightness",
            40,
            100,
            100,
            ratio,
            self.preview_changed.emit,
        )
        self.mirror_print_check = QCheckBox(tr("sep.mirror_print"))
        self.mirror_print_check.setToolTip(tr("sep.mirror_print_tip"))
        self.mirror_print_check.toggled.connect(
            lambda _checked: self.preview_changed.emit()
        )
        form.addRow(self.mirror_print_check)
        return box

    def _backlight_box(self):
        """Simulation du rétro-éclairage : diffusion et intensité."""
        box = QGroupBox(tr("sep.backlight_title"))
        form = QFormLayout(box)
        ratio = lambda v: f"{v / 100:.2f}"  # noqa: E731
        self.diffusion_slider = self._slider(
            form,
            "sep.light_diffusion",
            0,
            100,
            15,
            ratio,
            self.preview_changed.emit,
        )
        self.intensity_slider = self._slider(
            form,
            "sep.backlight_intensity",
            50,
            300,
            100,
            ratio,
            self.preview_changed.emit,
        )
        return box

    def _previews(self):
        """Aperçus : original, gravure, impression, simulation."""
        self.preview_tabs = QTabWidget()
        self.preview_views = []
        for key in PREVIEW_KEYS:
            view = ZoomableGraphicsView()
            self.preview_views.append(view)
            self.preview_tabs.addTab(view, tr(key))
        self.preview_tabs.setCurrentIndex(3)
        self.preview_tabs.currentChanged.connect(self.preview_tab_changed)
        return self.preview_tabs

    @staticmethod
    def _slider(
        form, label_key, low, high, value, fmt, on_change, tip_key=None
    ):
        """Curseur et sa valeur à droite, ajoutés au formulaire."""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high)
        slider.setValue(value)
        label = QLabel(fmt(value))
        label.setMinimumWidth(42)
        slider.valueChanged.connect(
            lambda v: (label.setText(fmt(v)), on_change())
        )
        row = QHBoxLayout()
        row.addWidget(slider, 1)
        row.addWidget(label)
        form.addRow(tr(label_key), row)
        if tip_key:
            slider.setToolTip(tr(tip_key))
        return slider

    # -- état reçu de la fenêtre

    def set_image_ratio(self, ratio):
        """Proportions (largeur / hauteur) de l'image chargée, ou None."""
        self._image_ratio = ratio

    def fit_plate_to_image(self):
        """Hauteur de la plaque d'après sa largeur et les proportions de
        l'image, si elles sont conservées."""
        if self.keep_ratio_check.isChecked():
            self._apply_ratio("w")

    def swap_plate_size(self):
        """Échange largeur et hauteur de la plaque (image pivotée)."""
        self._block = True
        try:
            width = self.plate_width_spin.value()
            self.plate_width_spin.setValue(self.plate_height_spin.value())
            self.plate_height_spin.setValue(width)
        finally:
            self._block = False

    def set_file_name(self, name):
        self.file_label.setText(name)

    def set_engrave_dpi(self, dpi):
        """Résolution de gravure, réglée dans « Graver une image »."""
        self.engrave_dpi_label.setText(tr("sep.engrave_dpi").format(dpi=dpi))

    def reset_crop(self):
        for slider, value in (
            (self.crop_zoom_slider, 100),
            (self.crop_x_slider, 50),
            (self.crop_y_slider, 50),
        ):
            slider.setValue(value)

    # -- valeurs lues par la fenêtre

    def frame_args(self):
        """(cadrage, zoom, ox, oy) réellement appliqués. Proportions de
        l'image conservées, ou mode « étirer » : zoom et décalage
        ignorés."""
        framing = self.framing_combo.currentIndex()
        keep = self.keep_ratio_check.isChecked()
        if keep or framing != 0:
            return (framing if not keep else 0, 1.0, 0.5, 0.5)
        return (
            0,
            self.crop_zoom_slider.value() / 100.0,
            self.crop_x_slider.value() / 100.0,
            self.crop_y_slider.value() / 100.0,
        )

    # -- réactions internes

    def _apply_ratio(self, driver="w"):
        """Recalcule la hauteur (driver « w ») ou la largeur (« h ») pour
        respecter les proportions de l'image."""
        if self._image_ratio is None:
            return
        self._block = True
        try:
            if driver == "w":
                self.plate_height_spin.setValue(
                    self.plate_width_spin.value() / self._image_ratio
                )
            else:
                self.plate_width_spin.setValue(
                    self.plate_height_spin.value() * self._image_ratio
                )
        finally:
            self._block = False

    def _on_plate_changed(self, which):
        if self._block:
            return
        if self.keep_ratio_check.isChecked():
            self._apply_ratio(which)
        self.tone_changed.emit()
        self.preview_changed.emit()

    def _on_keep_ratio(self, checked):
        if checked:
            self._apply_ratio("w")
        self._update_crop_enabled()
        self.tone_changed.emit()
        self.preview_changed.emit()

    def _on_framing_changed(self, *_args):
        self._update_crop_enabled()
        self.tone_changed.emit()
        self.preview_changed.emit()

    def _update_crop_enabled(self):
        free = not self.keep_ratio_check.isChecked()
        self.framing_combo.setEnabled(free)
        self.crop_box.setEnabled(
            free and self.framing_combo.currentIndex() == 0
        )

    def _on_crop_changed(self):
        self.tone_changed.emit()
        self.preview_changed.emit()

    def _apply_support(self, index):
        if index in SUPPORT_PRESETS:
            saturation, lightness, diffusion = SUPPORT_PRESETS[index]
            self.saturation_slider.setValue(saturation)
            self.lightness_slider.setValue(lightness)
            self.diffusion_slider.setValue(diffusion)

    # -- glisser-déposer

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(IMAGE_EXTENSIONS):
                event.acceptProposedAction()
                self.image_dropped.emit(path)
                return
