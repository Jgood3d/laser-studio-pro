"""Panneau des actions de job : cadrage, zéro, aller au zéro, répétition.

Utilisation :

    from laser_studio.ui.machine.job_actions import JobActionsPanel

    panel = JobActionsPanel()
    panel.frame_requested.connect(self.run_frame)
"""

from laser_studio.ui.machine.job_actions.panel import JobActionsPanel

__all__ = ["JobActionsPanel"]
