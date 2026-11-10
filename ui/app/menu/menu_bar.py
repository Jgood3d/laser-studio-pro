"""Barre de menus de la fenêtre principale."""

from PyQt6.QtWidgets import QMenuBar

from ui.app.menu.file_menu import FileMenu
from ui.app.menu.help_menu import HelpMenu
from ui.app.menu.settings_menu import SettingsMenu
from ui.app.menu.tools_menu import ToolsMenu


class AppMenuBar(QMenuBar):
    """Barre de menus : Fichier, Paramètres, Outils et Aide.

    Elle ne fait que ranger les actions de AppActions, qui émet les signaux.
    """

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.file_menu = FileMenu(actions, self)
        self.settings_menu = SettingsMenu(actions, self)
        self.tools_menu = ToolsMenu(actions, self)
        self.help_menu = HelpMenu(actions, self)
        for menu in (
            self.file_menu,
            self.settings_menu,
            self.tools_menu,
            self.help_menu,
        ):
            self.addMenu(menu)
