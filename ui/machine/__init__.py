"""Panneaux de la machine, sous les onglets : pilotage, actions de job…

Utilisation :

    from ui.machine import MachinePanel

    panel = MachinePanel(job_position_box, max_speed=6000)
    panel.jog_panel.jog_requested.connect(self.jog_move)
"""

from ui.machine.panel import MachinePanel

__all__ = ["MachinePanel"]
