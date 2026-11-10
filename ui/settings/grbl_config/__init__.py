"""Page « Configuration GRBL » : commande laser, surbalayage, G-Code de
début et de fin, réglages GRBL complets.

Utilisation :

    from ui.settings.grbl_config import GrblConfigPage

    page = GrblConfigPage()
    page.read_settings_requested.connect(self.read_grbl_settings)
"""

from ui.settings.grbl_config.page import GrblConfigPage

__all__ = ["GrblConfigPage"]
