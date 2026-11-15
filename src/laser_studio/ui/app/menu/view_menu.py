"""Menu Affichage : onglets facultatifs de la fenêtre."""

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class ViewMenu(QMenu):
    """Menu Affichage : afficher ou masquer la console G-Code et la file
    d'attente (cases à cocher, état mémorisé)."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.view"), parent)
        self.addAction(actions.gcode_console)
        self.addAction(actions.job_queue)
