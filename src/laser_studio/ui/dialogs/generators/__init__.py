"""Fenêtre unique des générateurs de l'éditeur vectoriel (boîte, puzzle, boule de Noël, porte-clés).

Utilisation :

    from laser_studio.ui.dialogs.generators import GeneratorsDialog

    dialog = GeneratorsDialog(parent, [("box", "Boîte", icon, make_box_dialog), ...], start="box")
    if dialog.exec():
        kind, page = dialog.chosen, dialog.page(dialog.chosen)
"""

from laser_studio.ui.dialogs.generators.dialog import GeneratorsDialog

__all__ = ["GeneratorsDialog"]
