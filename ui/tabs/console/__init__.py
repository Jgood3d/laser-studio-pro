"""Onglet « Console / G-Code » : statistiques, export et console.

Utilisation :

    from ui.tabs.console import ConsoleTab

    tab = ConsoleTab()
    tab.export_requested.connect(self.export_gcode_with_ext)
"""

from ui.tabs.console.tab import ConsoleTab

__all__ = ["ConsoleTab"]
