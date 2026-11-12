"""Statistiques du job généré : lignes, puissance moyenne, temps estimé.

Utilisation :

    from laser_studio.ui.machine.job_stats import JobStatsPanel

    panel = JobStatsPanel()
    panel.set_stats("Lignes : 4", "Puissance : 12 %", "Temps : 1 min")
"""

from laser_studio.ui.machine.job_stats.panel import JobStatsPanel

__all__ = ["JobStatsPanel"]
