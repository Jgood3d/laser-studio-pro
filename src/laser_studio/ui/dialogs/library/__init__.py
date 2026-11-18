"""Fenêtre « Bibliothèque » : modèles prêts à graver ou découper.

Utilisation :

    from laser_studio.ui.dialogs.library import LibraryDialog

    dialog = LibraryDialog(self, categories, icon_size=160)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        item, variants = dialog.chosen()
"""

from laser_studio.ui.dialogs.library.dialog import LibraryDialog, LibraryItemDialog

__all__ = ["LibraryDialog", "LibraryItemDialog"]
