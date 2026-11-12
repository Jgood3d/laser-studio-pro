"""Menu Fichier : projets (enregistrer, ouvrir, récents), enregistrement
du G-Code et quitter."""

import os

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class FileMenu(QMenu):
    """Menu Fichier, construit à partir des actions de AppActions."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.file"), parent)
        self._actions = actions
        self.addAction(actions.save_project)
        self.addAction(actions.open_project)
        self.recent_projects_menu = self.addMenu(
            actions.recent_projects_icon, tr("menu.file.recent_projects")
        )
        self.set_recent_projects([])
        self.addSeparator()
        # Une entrée par extension ; le sous-menu reste grisé tant qu'aucun
        # G-Code n'a été généré (AppActions.set_gcode_export_enabled).
        self.gcode_export_menu = self.addMenu(
            actions.gcode_export_icon, tr("menu.file.save_gcode")
        )
        for action in actions.gcode_export_actions.values():
            self.gcode_export_menu.addAction(action)
        self.gcode_export_menu.setEnabled(False)
        actions.gcode_export_enabled_changed.connect(
            self.gcode_export_menu.setEnabled
        )
        self.addSeparator()
        self.addAction(actions.quit)

    def set_recent_projects(self, paths):
        """Remplit le sous-menu des projets récents.

        Un clic émet AppActions.recent_project_requested(chemin).
        """
        menu = self.recent_projects_menu
        menu.clear()
        if not paths:
            menu.addAction(tr("project.no_recent")).setEnabled(False)
            return
        for path in paths:
            action = menu.addAction(os.path.basename(path))
            action.setToolTip(path)
            action.triggered.connect(
                lambda _checked=False, p=path: (
                    self._actions.recent_project_requested.emit(p)
                )
            )
