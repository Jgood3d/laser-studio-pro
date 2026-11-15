"""Cadre « Position du job sur le plateau », dans le panneau machine."""

from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel

from laser_studio.core.constants import ORIGIN_BOTTOM_LEFT, ORIGIN_CENTER
from laser_studio.i18n import TRANSLATIONS, tr

# Code de chaque choix, dans l'ordre de la liste, et sa clé de traduction.
ORIGIN_CHOICES = (
    (ORIGIN_BOTTOM_LEFT, "ui.origin_bottom_left"),
    (ORIGIN_CENTER, "ui.origin_center"),
)


class JobPositionBox(QGroupBox):
    """Origine du repère du job (bas-gauche ou centre).

    Le décalage X / Y se règle dans l'onglet « Graver une image » : le
    cadre le rappelle. La liste affiche des libellés traduits, mais
    l'origine se lit et s'écrit par code (ORIGIN_BOTTOM_LEFT,
    ORIGIN_CENTER), le même quelle que soit la langue :

        box = JobPositionBox()
        params["origin_pos"] = box.origin()
        box.set_origin(project.get("origin_pos"))
    """

    def __init__(self, parent=None):
        super().__init__(tr("ui.job_position_box"), parent)
        layout = QFormLayout(self)
        self.origin_combo = QComboBox()
        for code, key in ORIGIN_CHOICES:
            self.origin_combo.addItem(tr(key), code)
        layout.addRow(tr("dim.origin"), self.origin_combo)
        hint = QLabel(tr("ui.job_offset_in_image_tab"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888888;")
        layout.addRow(hint)

    def origin(self):
        """Code de l'origine choisie : ORIGIN_BOTTOM_LEFT ou ORIGIN_CENTER."""
        return self.origin_combo.currentData()

    def set_origin(self, value):
        """Choisit l'origine `value` : un code, ou un libellé enregistré par
        une version précédente (texte affiché, dans n'importe quelle langue).
        Une valeur inconnue laisse le choix actuel."""
        for index, (code, key) in enumerate(ORIGIN_CHOICES):
            if value == code or value in TRANSLATIONS[key].values():
                self.origin_combo.setCurrentIndex(index)
                return

    def profile_values(self):
        """Origine du repère, enregistrée dans un profil machine."""
        return {"origin": self.origin()}

    def apply_profile_values(self, profile):
        """Réapplique l'origine d'un profil, si elle est reconnue."""
        if "origin" in profile:
            self.set_origin(profile["origin"])
