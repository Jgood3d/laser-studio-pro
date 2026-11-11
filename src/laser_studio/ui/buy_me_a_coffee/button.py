"""Bouton « Buy me a coffee » : ouvre la page ko-fi du projet."""

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import QPushButton

from laser_studio.core.constants import KOFI_URL
from laser_studio.core.paths import find_resource
from laser_studio.i18n import tr

ICON_FILENAME = "buy_me_a_coffee.png"


class BuyMeACoffeeButton(QPushButton):
    """Bouton rond et plat, à l'icône de tasse, qui ouvre la page ko-fi.

    Sans l'image (ressource absente), il affiche « ☕ » :

        toolbar.addWidget(BuyMeACoffeeButton(icon_size=24))
    """

    def __init__(self, icon_size=40, parent=None):
        super().__init__(parent)
        button_size = icon_size + 4
        self.setFlat(True)
        self.setFixedSize(button_size, button_size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tr("ui.support_button_tooltip"))
        self.setStyleSheet(
            "QPushButton { border: none; border-radius: %dpx; "
            "background-color: transparent; }"
            "QPushButton:hover { background-color: rgba(255, 221, 0, 45); }"
            % (button_size // 2)
        )
        icon_path = find_resource(ICON_FILENAME)
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(icon_size, icon_size))
        else:
            self.setText("☕")
        self.clicked.connect(self.open_kofi_page)

    @staticmethod
    def open_kofi_page():
        """Ouvre la page ko-fi dans le navigateur."""
        QDesktopServices.openUrl(QUrl(KOFI_URL))
