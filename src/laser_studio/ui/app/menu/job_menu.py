"""Menu Job : générer, cadrer (rectangle ou au plus près), envoyer au laser, pause et reprise, avec leurs
raccourcis clavier."""

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class JobMenu(QMenu):
    """Actions de AppActions.job_actions (F5 générer, F6 cadrer, Maj+F6 cadrer au plus près, Ctrl+Entrée
    envoyer, F7 pause, F8 reprise)."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.job"), parent)
        generate, frame, frame_contour, send, pause, resume = actions.job_actions
        self.addAction(generate)
        self.addSeparator()
        for action in (frame, frame_contour, send):
            self.addAction(action)
        self.addSeparator()
        for action in (pause, resume):
            self.addAction(action)
