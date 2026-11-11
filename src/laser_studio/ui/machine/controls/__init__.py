"""Panneau de pilotage : déplacements (jog), homing, commandes temps réel.

Utilisation :

    from laser_studio.ui.machine.controls import JogControlPanel

    panel = JogControlPanel(max_speed=6000)
    panel.jog_requested.connect(self.jog_move)
"""

from laser_studio.ui.machine.controls.panel import JogControlPanel

__all__ = ["JogControlPanel"]
