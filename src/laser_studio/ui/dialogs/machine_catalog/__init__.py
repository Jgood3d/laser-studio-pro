"""Fenêtre « Catalogue des machines ».

    from laser_studio.ui.dialogs.machine_catalog import MachineCatalogDialog

    dialog = MachineCatalogDialog(models, window)
    dialog.accepted.connect(lambda: create_profile(dialog.chosen()))
    dialog.show()
"""

from laser_studio.ui.dialogs.machine_catalog.dialog import MachineCatalogDialog

__all__ = ["MachineCatalogDialog"]
