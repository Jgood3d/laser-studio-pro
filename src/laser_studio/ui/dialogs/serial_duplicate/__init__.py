"""Fenêtre « Dupliquer en série » de l'éditeur vectoriel.

Utilisation :

    from laser_studio.ui.dialogs.serial_duplicate import SerialDuplicateDialog

    dialog = SerialDuplicateDialog(self, texts, n_objects, set_w, set_h, bed_w, bed_h, initial)
"""

from laser_studio.ui.dialogs.serial_duplicate.dialog import SerialDuplicateDialog

__all__ = ["SerialDuplicateDialog"]
