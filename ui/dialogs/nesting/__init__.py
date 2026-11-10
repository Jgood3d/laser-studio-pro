"""Fenêtre de réglage de l'imbrication automatique.

Utilisation :

    from ui.dialogs.nesting import NestingDialog

    dialog = NestingDialog(self, bed_w_mm, bed_h_mm, n_selected, n_total)
"""

from ui.dialogs.nesting.dialog import NestingDialog

__all__ = ["NestingDialog"]
