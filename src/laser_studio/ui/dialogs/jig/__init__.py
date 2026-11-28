"""Fenêtre « Gabarit de placement » de l'éditeur vectoriel.

Utilisation :

    from laser_studio.ui.dialogs.jig import JigDialog, error_message

    dialog = JigDialog(self, layers, obj_w, obj_h, has_selection, bed_w, bed_h, initial)
"""

from laser_studio.ui.dialogs.jig.dialog import JigDialog, error_message

__all__ = ["JigDialog", "error_message"]
