"""Onglet « Visualisation 2D G-Code » : aperçu du G-Code et ses options.

Utilisation :

    from ui.tabs.preview_2d import Preview2DTab

    tab = Preview2DTab()
    tab.plot_clicked.connect(self._on_plot_clicked)
"""

from ui.tabs.preview_2d.tab import Preview2DTab

__all__ = ["Preview2DTab"]
