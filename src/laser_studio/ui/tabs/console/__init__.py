"""Onglet « Console / G-Code » : G-Code généré et messages.

Utilisation :

    from laser_studio.ui.tabs.console import ConsoleTab

    tab = ConsoleTab()
    tab.console_edit.append(">>> Connecté")
"""

from laser_studio.ui.tabs.console.tab import ConsoleTab

__all__ = ["ConsoleTab"]
