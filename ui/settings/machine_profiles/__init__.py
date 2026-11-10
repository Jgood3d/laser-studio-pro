"""Page « Matériaux et connexion au graveur ».

Utilisation :

    from ui.settings.machine_profiles import MachineProfilesPage

    page = MachineProfilesPage(ports_model, material_names)
    page.connect_requested.connect(self.toggle_usb)
"""

from ui.settings.machine_profiles.page import MachineProfilesPage

__all__ = ["MachineProfilesPage"]
