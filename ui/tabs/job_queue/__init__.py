"""Onglet « File d'attente » : jobs à enchaîner et G-Code envoyé.

Utilisation :

    from ui.tabs.job_queue import JobQueueTab

    tab = JobQueueTab()
    tab.run_requested.connect(queue.run)
"""

from ui.tabs.job_queue.tab import JobQueueTab

__all__ = ["JobQueueTab"]
