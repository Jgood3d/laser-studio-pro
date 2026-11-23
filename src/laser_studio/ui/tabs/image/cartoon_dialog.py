"""Fenêtre « Effet BD » de l'onglet « Graver une image » : rayon du masque et pourcentage de noir.

Chaque mouvement d'un curseur met à jour le modèle (ImageSettings), donc l'aperçu tramé, en direct.
« Annuler » remet les réglages d'avant l'ouverture ; « OK » garde l'effet.

    if CartoonFilterDialog(image_settings, window).exec():
        ...   # effet appliqué
"""
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel

from laser_studio.i18n import tr
from laser_studio.ui.widgets import SliderWithButtons

# Rayon proposé à l'ouverture quand l'effet n'est pas encore actif (dixièmes de mm : 1,5 mm).
DEFAULT_RADIUS = 15
RADIUS_MAX = 50          # 5 mm


class CartoonFilterDialog(QDialog):
    """`settings` : ImageSettings (champs cartoon_radius et cartoon_black)."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("img.cartoon_title"))
        self._settings = settings
        self._before = (settings.cartoon_radius, settings.cartoon_black)
        layout = QFormLayout(self)
        intro = QLabel(tr("img.cartoon_intro"))
        intro.setWordWrap(True)
        layout.addRow(intro)
        radius = settings.cartoon_radius or DEFAULT_RADIUS
        self.radius = SliderWithButtons(1, RADIUS_MAX, radius, formatter=lambda v: f"{v / 10.0:.1f} mm")
        self.radius.slider.setToolTip(tr("img.cartoon_radius_tip"))
        self.black = SliderWithButtons(0, 100, settings.cartoon_black, formatter=lambda v: f"{v} %")
        self.black.slider.setToolTip(tr("img.cartoon_black_tip"))
        layout.addRow(tr("img.cartoon_radius"), self.radius)
        layout.addRow(tr("img.cartoon_black"), self.black)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.radius.value_changed.connect(self._apply)
        self.black.value_changed.connect(self._apply)
        self.setMinimumWidth(420)
        self._apply()                        # aperçu avec l'effet dès l'ouverture

    def _apply(self, *_args):
        self._settings.update(cartoon_radius=self.radius.slider.value(), cartoon_black=self.black.slider.value())

    def reject(self):
        """Annuler : l'image revient aux réglages d'avant l'ouverture."""
        radius, black = self._before
        self._settings.update(cartoon_radius=radius, cartoon_black=black)
        super().reject()
