"""Fenêtre « Macros » : liste des macros de l'utilisateur et leur détail.

Utilisation :

    from laser_studio.ui.dialogs.macros import MacroEditorDialog

    macros = MacroEditorDialog(macros, profiles, read_file, write_file, parent).run()   # liste, ou None
"""

from laser_studio.ui.dialogs.macros.dialog import MacroEditorDialog

__all__ = ["MacroEditorDialog"]
