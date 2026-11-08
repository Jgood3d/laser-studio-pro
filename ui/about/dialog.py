"""Boîte de dialogue « À propos » : bannière, texte et bouton OK."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from i18n import tr
from ui.about.banner_pixmap import AboutBannerPixmap
from ui.about.label import AboutLabel


class AboutDialog(QDialog):
    """Boîte de dialogue « À propos », à ouvrir avec exec().

    AboutDialog(self).exec()
    """

    BANNER_WIDTH = 420

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ui.about_title"))
        layout = QVBoxLayout(self)
        layout.addWidget(self._banner_label())
        layout.addWidget(AboutLabel())
        layout.addWidget(self._ok_button())

    def _banner_label(self):
        """La bannière, ou un message en rouge si elle est introuvable."""
        screen_owner = self.parentWidget() or self
        banner = AboutBannerPixmap(
            self.BANNER_WIDTH, screen_owner.devicePixelRatioF()
        )
        label = QLabel()
        error = banner.error_message()
        if error is None:
            label.setPixmap(banner)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            label.setText(error)
            label.setStyleSheet("color: #cc6666;")
            label.setWordWrap(True)
        return label

    def _ok_button(self):
        """Bouton OK qui ferme la boîte de dialogue."""
        button = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button.accepted.connect(self.accept)
        return button
