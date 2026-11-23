"""Page « Paramètres du graveur » : profils machine, lit, laser, limites.

Utilisation :

    from laser_studio.ui.settings.machine_params import MachineParamsPage

    page = MachineParamsPage()
    page.focal_changed.connect(window_controller.machine_focal_changed)
"""

from laser_studio.ui.settings.machine_params.page import MachineParamsPage

__all__ = ["MachineParamsPage"]
