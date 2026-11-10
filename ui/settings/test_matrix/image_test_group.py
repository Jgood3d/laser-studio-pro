"""Cadre « Test à partir d'une image » de la page Matrice de test."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from i18n import tr
from image import matrix as matrix_image
from ui.settings.test_matrix.tile_picker import TilePicker

HINT_STYLE = "color: #888888;"


class ImageTestGroup(QGroupBox):
    """Cadre cochable : chaque case de la matrice grave une zone d'image.

    Choix de l'image (fichier, ou image de « Graver une image »), taille
    réelle de l'image, taille de la zone, et aperçu où l'on place la zone
    (TilePicker). Les boutons émettent des signaux ; l'image est reçue par
    set_source_image, et la zone lue par tile_settings().
    """

    choose_image_requested = pyqtSignal()
    use_loaded_image_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(tr("ui.mat_image_group"), parent)
        self.source_image = None  # image source en niveaux de gris (PIL)
        self.setCheckable(True)
        self.setChecked(False)
        layout = QFormLayout(self)

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

    @staticmethod
    def _mm_spin(low, high, value):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setValue(value)
        spin.setSuffix(" mm")
        return spin

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

    def tile_settings(self):
        """Zone d'image de chaque case : (largeur réelle de l'image en mm,
        largeur et hauteur de la zone en mm, centre choisi dans l'aperçu)."""
        return (
            self.image_width_spin.value(),
            self.tile_width_spin.value(),
            self.tile_height_spin.value(),
            *self.tile_picker.center(),
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
