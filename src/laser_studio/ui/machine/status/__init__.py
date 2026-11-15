"""État et position de la machine, reçus du graveur.

Utilisation :

    from laser_studio.ui.machine.status import AxisPositionRow, MachineStateView

    state = MachineStateView()          # dans le panneau Connexion
    state.unlock_requested.connect(self.unlock_alarm)
    state.set_state("Idle")
    position = AxisPositionRow()        # en bas du panneau de pilotage
    position.set_position(12.5, 30.0, 0.0)
"""

from laser_studio.ui.machine.status.position import AxisPositionRow
from laser_studio.ui.machine.status.state import MachineStateView

__all__ = ["AxisPositionRow", "MachineStateView"]
