"""Menu et barre d'outils de la fenêtre principale.

Utilisation :

    from laser_studio.ui.app.menu import AppActions, AppMenuBar, AppToolBar

    actions = AppActions(self)
    self.setMenuBar(AppMenuBar(actions))
    self.addToolBar(AppToolBar(actions, self))
    actions.save_project_requested.connect(self.project.save)
"""

from laser_studio.ui.app.menu.actions import AppActions
from laser_studio.ui.app.menu.menu_bar import AppMenuBar
from laser_studio.ui.app.menu.toolbar import AppToolBar

__all__ = ["AppActions", "AppMenuBar", "AppToolBar"]
