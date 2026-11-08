"""Texte de « Buy me a coffee » : invitation à soutenir le projet."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from i18n import tr
from app_constants import KOFI_URL


class BuyMeACoffeeLabel(QLabel):
    """Message de soutien, centré, avec le lien ko-fi cliquable."""

    def __init__(self, parent=None):
        super().__init__(
            tr("ui.coffee_body").format(link=self._link()), parent
        )
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )

    @staticmethod
    def _link():
        """Lien HTML vers la page ko-fi, affiché sans « https:// »."""
        return f'<a href="{KOFI_URL}">{KOFI_URL.removeprefix("https://")}</a>'
