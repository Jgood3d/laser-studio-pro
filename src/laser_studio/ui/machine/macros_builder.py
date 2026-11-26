"""Macros de l'utilisateur reliées au panneau des actions de job, au graveur et aux profils machine.

    macros = build_macros(panel.job_actions_panel, engraver, machines, dialogs, parent=window,
                          manage=lambda: window_controller.show_settings_window("macros"))
    page = MacrosPage(lambda: MacroEditorDialog(*macros.editor_args()), macros.save)   # fenêtre Paramètres
"""
from laser_studio.controllers.macros import MacroController
from laser_studio.models.macros import MacrosModel


def build_macros(job_actions, engraver, machines, dialogs, *, parent, manage=lambda: None, model=None):
    """`job_actions` : JobActionsPanel (boutons des macros) ; `engraver` : EngraverController (envoi, état du
    graveur) ; `machines` : MachineProfilesController (profil
    affiché, pour filtrer les macros). `manage()` : ouvre l'éditeur (page « Macros » des Paramètres).
    `model` : MacrosModel (par défaut, macros.yaml de l'utilisateur)."""
    model = model if model is not None else MacrosModel(parent=parent)
    controller = MacroController(
        model, engraver, dialogs, profile_name=machines.current_name, profiles=machines.names)

    def refresh():
        job_actions.set_macros([(index, macro.name, macro.tooltip, macro.fires_laser)
                                for index, macro in controller.visible()])

    job_actions.macro_requested.connect(controller.run)
    job_actions.manage_macros_requested.connect(manage)
    model.changed.connect(refresh)
    machines.add_listener(refresh)
    refresh()
    return controller
