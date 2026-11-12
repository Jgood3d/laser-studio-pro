"""Menu Affichage : onglets facultatifs de la fenêtre."""

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class ViewMenu(QMenu):
    """Menu Affichage : afficher ou masquer la console G-Code (case à
    cocher, décochée au démarrage)."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.view"), parent)
        self.addAction(actions.gcode_console)
