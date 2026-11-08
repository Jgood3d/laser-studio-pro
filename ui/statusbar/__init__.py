"""Barre d'état de la fenêtre principale.

Utilisation :

    from ui.statusbar import StatusBar

    self.setStatusBar(StatusBar(self))
    self.statusBar().show_info("Image chargée")
"""

from ui.statusbar.status_bar import StatusBar

__all__ = ["StatusBar"]
