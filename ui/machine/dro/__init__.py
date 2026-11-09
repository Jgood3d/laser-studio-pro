"""Position de la machine (DRO) : état GRBL et coordonnées X, Y, Z.

Utilisation :

    from ui.machine.dro import DroPanel

    panel = DroPanel()
    panel.unlock_requested.connect(self.unlock_alarm)
    panel.set_status("Idle", 12.5, 30.0, 0.0)
"""

from ui.machine.dro.panel import DroPanel

__all__ = ["DroPanel"]
