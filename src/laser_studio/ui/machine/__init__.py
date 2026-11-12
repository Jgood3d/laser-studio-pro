"""Panneaux de la machine, sous les onglets : pilotage, actions de job…

Utilisation :

    from laser_studio.ui.machine import MachinePanel

    panel = MachinePanel(ports_model, max_speed=6000)
    panel.jog_panel.jog_requested.connect(self.jog_move)
"""

from laser_studio.ui.machine.panel import MachinePanel

__all__ = ["MachinePanel"]
