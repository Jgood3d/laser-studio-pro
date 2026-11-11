"""Cadre « Position du job sur le plateau », dans le panneau machine."""

from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel

from laser_studio.i18n import tr


class JobPositionBox(QGroupBox):
    """Origine du repère du job (bas-gauche ou centre).

    Le décalage X / Y se règle dans l'onglet « Graver une image » : le
    cadre le rappelle. L'origine (origin_combo) est lue à la génération du
    G-Code.
    """

    def __init__(self, parent=None):
        super().__init__(tr("ui.job_position_box"), parent)
        layout = QFormLayout(self)
        self.origin_combo = QComboBox()
        self.origin_combo.addItems(
            [tr("ui.origin_bottom_left"), tr("ui.origin_center")]
        )
        layout.addRow(tr("dim.origin"), self.origin_combo)
        hint = QLabel(tr("ui.job_offset_in_image_tab"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888888;")
        layout.addRow(hint)

    def profile_values(self):
        """Origine du repère, enregistrée dans un profil machine."""
        return {"origin": self.origin_combo.currentText()}

    def apply_profile_values(self, profile):
        """Réapplique l'origine d'un profil, si elle existe dans la liste."""
        if "origin" in profile:
            index = self.origin_combo.findText(profile["origin"])
            if index >= 0:
                self.origin_combo.setCurrentIndex(index)
