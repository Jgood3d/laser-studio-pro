"""Macros de l'utilisateur reliées au panneau des actions de job, au graveur et aux profils machine.

    macros = build_macros(panel.job_actions_panel, engraver, connection, machines, dialogs, parent=window)
    actions.macros_requested.connect(macros.manage)
"""
from laser_studio.controllers.macros import MacroController
from laser_studio.models.macros import MacrosModel
from laser_studio.ui.dialogs.macros import MacroEditorDialog


def build_macros(job_actions, engraver, connection, machines, dialogs, *, parent, model=None):
    """`job_actions` : JobActionsPanel (boutons des macros) ; `engraver` : EngraverController (envoi) ;
    `connection` : MachineConnection (job en cours ?) ; `machines` : MachineProfilesController (profil
    affiché, pour filtrer les macros). `model` : MacrosModel (par défaut, macros.yaml de l'utilisateur)."""
    model = model if model is not None else MacrosModel(parent=parent)
    controller = MacroController(
        model, engraver, connection, dialogs, profile_name=machines.current_name, profiles=machines.names,
        edit=lambda macros, profiles, read_file, write_file: MacroEditorDialog(
            macros, profiles, read_file, write_file, parent).run())

    def refresh():
        job_actions.set_macros([(index, macro.name, macro.tooltip, macro.fires_laser)
                                for index, macro in controller.visible()])

    job_actions.macro_requested.connect(controller.run)
    job_actions.manage_macros_requested.connect(controller.manage)
    model.changed.connect(refresh)
    machines.add_listener(refresh)
    refresh()
    return controller
