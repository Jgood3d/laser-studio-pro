"""Barre d'état de la fenêtre principale.

Utilisation :

    from laser_studio.ui.statusbar import StatusBar

    self.setStatusBar(StatusBar(self))
    self.statusBar().show_info("Image chargée")
"""

from laser_studio.ui.statusbar.status_bar import StatusBar

__all__ = ["StatusBar"]
