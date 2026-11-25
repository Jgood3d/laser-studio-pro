"""Réglages de l'onglet « Graver une image » (panneau de gauche)."""

from PyQt6.QtCore import QPointF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QPen, QPolygonF, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.image.dithering import ALGORITHMS
from laser_studio.ui.binding import bind
from laser_studio.ui.utils import painted_icon
from laser_studio.ui.tabs.image.engrave_layer_combo import EngraveLayerComboBox
from laser_studio.ui.tabs.image.material_combo import MaterialComboBox
from laser_studio.ui.tabs.image.resolution_box import ResolutionBox
from laser_studio.ui.widgets import SliderWithButtons

# Filtres de la liste « Appliquer un filtre ».
FILTER_NONE = ""
FILTER_CARTOON = "cartoon"

# Hauteur du bouton « Charger Image » (px) : la cible la plus utilisée de l'onglet.
LOAD_BUTTON_HEIGHT = 84


class ImageSettingsPanel(QWidget):
    """Taille et décalage de l'image, réglages photo, matière, tramage et
    résolution.

    Il ne traite pas l'image : ses champs émettent des signaux, auxquels
    ImageController s'abonne, et les réglages du tramage sont liés au modèle
    ImageSettings (bind_settings) :

        panel = ImageSettingsPanel()
        panel.bind_settings(image_settings)
        panel.size_changed.connect(image.dimension_changed)

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
    # Calque de gravure choisi par l'utilisateur : son identifiant (jamais émis quand la fenêtre
    # remplit la liste, voir EngraveLayerComboBox).
    engrave_layer_changed = pyqtSignal(str)
    # Taille de l'image modifiée : axe ("w" ou "h") et valeur en mm.
    size_changed = pyqtSignal(str, float)
    # Résolution réellement utilisée, en lignes/mm (voir ResolutionBox).
    resolution_changed = pyqtSignal(float)
    configure_focal_requested = pyqtSignal()
    # Filtre choisi dans la liste « Appliquer un filtre » par l'utilisateur : FILTER_NONE ou FILTER_CARTOON.
    filter_requested = pyqtSignal(str)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        # Grande cible : image dessinée au-dessus du libellé, sur toute la largeur du panneau.
        load_button = QToolButton()
        load_button.setText(tr("img.load"))
        load_button.setIcon(self._picture_icon())
        load_button.setIconSize(QSize(32, 32))
        load_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        load_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        load_button.setMinimumHeight(LOAD_BUTTON_HEIGHT)
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
        layout.addRow(tr("img.filter"), self._filter_combo())
        layout.addRow(tr("img.material_bg"), self._material_combo())
        layout.addRow("", self.invert_check)
        layout.addRow(tr("img.algorithm"), self._algorithm_combo())
        layout.addRow(self.as_is_check)  # toute la largeur du panneau
        layout.addRow(tr("img.resolution"), self._resolution_box())
        layout.addRow(tr("img.engrave_layer"), self._engrave_layer_combo())
        self._shortcut(QKeySequence.StandardKey.Undo, self.undo_requested)
        self._shortcut(QKeySequence.StandardKey.Redo, self.redo_requested)

    def _picture_icon(self):
        """Icône « image » : cadre, montagnes et soleil, dans la couleur du texte du thème."""
        def draw(painter, color):
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(3, 5, 26, 22, 3, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(22, 12), 3, 3)
            painter.drawPolygon(QPolygonF([QPointF(5, 25), QPointF(13, 14), QPointF(19, 21), QPointF(22, 18),
                                           QPointF(27, 25)]))
        return painted_icon(self.palette(), draw)

    def bind_settings(self, settings):
        """Lie les champs du tramage (curseurs, négatif, matière, algorithme)
        au modèle `settings` (ImageSettings). Les miroirs, dans la barre
        d'outils de la fenêtre, sont liés par elle."""
        for widget, field in (
            (self.brightness_slider, "brightness"),
            (self.contrast_slider, "contrast"),
            (self.gamma_slider, "gamma"),
            (self.sharpness_slider, "sharpness"),
            (self.invert_check, "invert"),
            (self.as_is_check, "as_is"),
        ):
            bind(widget, settings, field)
        # Liste des filtres : affiche « Effet BD » tant que l'effet est actif (projet ouvert, annuler…).
        settings.changed.connect(lambda changes: self.show_filter(settings.cartoon_radius > 0)
                                 if "cartoon_radius" in changes else None)
        self.show_filter(settings.cartoon_radius > 0)
        combo = self.material_combo
        bind(combo, settings, "material_bg",
             to_widget=lambda key: combo.findData(key),
             from_widget=lambda index: combo.itemData(index) or "light")
        algo = self.algorithm_combo
        bind(algo, settings, "algorithm",
             to_widget=lambda name: algo.findText(name),
             from_widget=lambda index: algo.itemText(index))

    def set_size(self, w_mm, h_mm):
        """Largeur et hauteur de l'image (mm). Les signaux des champs partent
        normalement : ceux qui suivent la taille (cadre du job, éditeur) la voient."""
        self.width_spin.setValue(w_mm)
        self.height_spin.setValue(h_mm)

    def size_mm(self):
        return self.width_spin.value(), self.height_spin.value()

    def set_offset(self, x_mm, y_mm):
        """Décalage de l'image (mm) par rapport à l'origine du job."""
        self.offset_x_spin.setValue(x_mm)
        self.offset_y_spin.setValue(y_mm)

    def offset_mm(self):
        return self.offset_x_spin.value(), self.offset_y_spin.value()

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
            "as_is": self.as_is_check.isChecked(),
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
        # Image déjà tramée : gravée telle quelle (les réglages de tons et le tramage sont alors grisés).
        self.as_is_check = QCheckBox(tr("img.as_is"))
        self.as_is_check.setToolTip(tr("img.as_is_tip"))
        self.as_is_check.stateChanged.connect(self.processing_changed)
        self.as_is_check.toggled.connect(self._as_is_toggled)

    def _as_is_toggled(self, checked):
        """Réglages sans effet sur une image gravée telle quelle : grisés."""
        for row in (self._brightness_row, self._contrast_row, self._gamma_row, self._sharpness_row):
            row.setEnabled(not checked)
        self.filter_combo.setEnabled(not checked)
        self.algorithm_combo.setEnabled(not checked)

    def _filter_combo(self):
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(tr("img.filter_none"), FILTER_NONE)
        self.filter_combo.addItem(tr("img.filter_cartoon"), FILTER_CARTOON)
        self.filter_combo.setToolTip(tr("img.filter_tip"))
        # activated : choix de l'utilisateur, même s'il reprend le filtre déjà actif (pour le régler).
        self.filter_combo.activated.connect(lambda index: self.filter_requested.emit(self.filter_combo.itemData(index)))
        return self.filter_combo

    def show_filter(self, cartoon_active):
        """Filtre affiché dans la liste, sans émettre de demande."""
        blocked = self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(self.filter_combo.findData(FILTER_CARTOON if cartoon_active else FILTER_NONE))
        self.filter_combo.blockSignals(blocked)

    def _material_combo(self):
        self.material_combo = MaterialComboBox()
        self.material_combo.material_changed.connect(self.material_changed)
        return self.material_combo

    def _engrave_layer_combo(self):
        self.engrave_layer_combo = EngraveLayerComboBox()
        self.engrave_layer_combo.layer_selected.connect(self.engrave_layer_changed)
        return self.engrave_layer_combo

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
        box.resolution_changed.connect(self.resolution_changed)
        box.configure_focal_requested.connect(self.configure_focal_requested)
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
