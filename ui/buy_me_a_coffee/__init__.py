"""« Buy me a coffee » : boîte de dialogue et bouton de la barre d'outils.

Utilisation :

    from ui.buy_me_a_coffee import BuyMeACoffeeButton, BuyMeACoffeeDialog

    BuyMeACoffeeDialog(self).exec()
    toolbar.addWidget(BuyMeACoffeeButton(icon_size=24))
"""

from ui.buy_me_a_coffee.button import BuyMeACoffeeButton
from ui.buy_me_a_coffee.dialog import BuyMeACoffeeDialog

__all__ = ["BuyMeACoffeeButton", "BuyMeACoffeeDialog"]
