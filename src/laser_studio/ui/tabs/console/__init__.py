"""Onglet « Console / G-Code » : G-Code généré ou importé.

Utilisation :

    from laser_studio.ui.tabs.console import ConsoleTab

    tab = ConsoleTab()
    tab.set_gcode(gcode)
"""

from laser_studio.ui.tabs.console.tab import ConsoleTab

__all__ = ["ConsoleTab"]
