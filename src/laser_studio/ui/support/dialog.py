"""Boîte de dialogue « Support » : message de contact et bouton OK."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from laser_studio.i18n import tr
from laser_studio.ui.support.label import SupportLabel


class SupportDialog(QDialog):
    """Boîte de dialogue « Support », à ouvrir avec exec().

    SupportDialog(self).exec()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ui.support_title"))
        layout = QVBoxLayout(self)
        layout.addWidget(SupportLabel())
        layout.addWidget(self._ok_button())

    def _ok_button(self):
        """Bouton OK qui ferme la boîte de dialogue."""
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        return buttons
