"""Onglet « Visualisation 2D G-Code » : aperçu du G-Code, ses options, et
les statistiques du job à droite.

Utilisation :

    from laser_studio.ui.tabs.preview_2d import Preview2DTab

    tab = Preview2DTab()
    tab.plot_clicked.connect(self._on_plot_clicked)
    tab.job_stats_panel.set_stats("Lignes : 4", "Puissance : 12 %", "Temps : 1 min")
"""

from laser_studio.ui.tabs.preview_2d.job_stats_panel import JobStatsPanel
from laser_studio.ui.tabs.preview_2d.tab import Preview2DTab

__all__ = ["JobStatsPanel", "Preview2DTab"]
