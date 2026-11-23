"""Page « Paramètres du graveur » et sa logique (profils machine), reliées.

    page, machines = build_machine_params_page(machine, state, dialogs, parent,
                                               link_layers_to_focal=..., focal_changed=...)
"""
from laser_studio.controllers.machine_profiles import MachineProfilesController, ProfileFields
from laser_studio.ui.settings.machine_params.page import MachineParamsPage


def build_machine_params_page(machine, state, dialogs, parent, *, link_layers_to_focal, focal_changed):
    """Page liée à `machine` (MachineConfig) ; profils lus et réappliqués par `state` (WindowState).
    `link_layers_to_focal()` : calques liés à la focale recalés ; `focal_changed(focale)` : focale saisie.
    Renvoie (page, MachineProfilesController)."""
    page = MachineParamsPage()
    machines = MachineProfilesController(
        parent,
        page.profile_combo,
        ProfileFields(
            capture=state.capture_machine_profile,
            apply=state.apply_machine_profile,
            apply_layers=state.apply_profile_layers,
            memory=state.machine_memory,
            profile_selected=state.after_machine_profile_selected,
            link_layers_to_focal=link_layers_to_focal,
        ),
        save_settings=state.save_machine_settings,
        dialogs=dialogs,
    )
    page.profile_selected.connect(machines.on_selected)
    page.new_profile_requested.connect(machines.new_profile)
    page.update_profile_requested.connect(machines.update_profile)
    page.delete_profile_requested.connect(machines.delete_profile)
    page.focal_changed.connect(focal_changed)
    page.bind_settings(machine)
    return page, machines
