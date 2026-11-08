"""Boîte de dialogue « Buy me a coffee » : message de soutien et bouton OK."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from i18n import tr
from ui.buy_me_a_coffee.label import BuyMeACoffeeLabel


class BuyMeACoffeeDialog(QDialog):
    """Boîte de dialogue « Buy me a coffee », à ouvrir avec exec().

    BuyMeACoffeeDialog(self).exec()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ui.coffee_title"))
        layout = QVBoxLayout(self)
        layout.addWidget(BuyMeACoffeeLabel())
        layout.addWidget(self._ok_button())

    def _ok_button(self):
        """Bouton OK qui ferme la boîte de dialogue."""
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        return buttons
