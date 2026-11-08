"""Texte de « Support » : comment contacter l'équipe."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from i18n import tr


class SupportLabel(QLabel):
    """Message de contact, centré, avec un lien e-mail cliquable."""

    def __init__(self, parent=None):
        super().__init__(tr("ui.support_body"), parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
