"""Boîte de dialogue « Rejoindre la communauté WhatsApp » : QR code à scanner et lien cliquable."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from laser_studio.core.paths import find_resource
from laser_studio.i18n import tr

COMMUNITY_URL = "https://chat.whatsapp.com/K18EOe4eTd3C312VQeDhnN"
QR_IMAGE = "whatsapp_community_qr.png"      # même lien que COMMUNITY_URL
QR_SIZE = 260                               # côté du QR code affiché (px)


class CommunityDialog(QDialog):
    """Communauté WhatsApp, à ouvrir avec exec().

    CommunityDialog(self).exec()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ui.community_title"))
        layout = QVBoxLayout(self)
        layout.addWidget(self._centered_label(tr("ui.community_scan")))
        self.qr_label = self._qr_label()
        layout.addWidget(self.qr_label)
        self.link_label = self._centered_label(
            tr("ui.community_link").format(url=COMMUNITY_URL)
        )
        self.link_label.setWordWrap(False)          # l'adresse reste sur une ligne
        self.link_label.setOpenExternalLinks(True)
        self.link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(self.link_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _centered_label(text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        return label

    @staticmethod
    def _qr_label():
        """QR code ; s'il manque (paquet incomplet), le lien en dessous suffit."""
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAccessibleName(tr("ui.community_qr_name"))
        path = find_resource(QR_IMAGE)
        if path:
            label.setPixmap(QPixmap(path).scaled(
                QR_SIZE, QR_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        return label
