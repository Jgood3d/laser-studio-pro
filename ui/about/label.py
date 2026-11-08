"""Texte de « À propos » : nom, version et description."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from app_utils import APP_VERSION
from i18n import tr


class AboutLabel(QLabel):
    """Nom, version et description de l'application, centrés."""

    def __init__(self, parent=None):
        super().__init__(
            f"<b>Laser Studio Pro</b> — {tr('menu.help.version')} "
            f"{APP_VERSION}<br>" + tr("dialog.about.description"),
            parent,
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
