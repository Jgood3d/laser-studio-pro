"""Menu Paramètres : réglages du graveur, langue et thème."""

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class SettingsMenu(QMenu):
    """Menu Paramètres : fenêtres de réglages, langue et thème.

    Les réglages propres à la machine s'ouvrent dans des fenêtres.
    """

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.settings"), parent)
        self.addAction(actions.machine_params_window)
        self.addAction(actions.machine_window)
        self.addAction(actions.grbl_window)
        self.addSeparator()
        language_menu = self.addMenu(
            actions.language_icon, tr("menu.language")
        )
        for action in actions.language_actions.values():
            language_menu.addAction(action)
        theme_menu = self.addMenu(actions.theme_icon, tr("menu.theme"))
        for action in actions.theme_actions.values():
            theme_menu.addAction(action)
        self.addSeparator()
