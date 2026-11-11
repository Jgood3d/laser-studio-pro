"""Fenêtre du générateur de boîte à encoches.

Utilisation :

    from laser_studio.ui.dialogs.box_generator import BoxGeneratorDialog, error_message

    dialog = BoxGeneratorDialog(self, layers, bed_w_mm, bed_h_mm, initial)
"""

from laser_studio.ui.dialogs.box_generator.dialog import BoxGeneratorDialog, error_message

__all__ = ["BoxGeneratorDialog", "error_message"]
