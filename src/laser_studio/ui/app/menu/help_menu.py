"""Menu Aide : version, documentation, à propos, support, communauté et soutien."""

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class HelpMenu(QMenu):
    """Menu Aide : version (non cliquable), puis les boîtes de dialogue."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.help"), parent)
        self.addAction(actions.version)
        self.addSeparator()
        self.addAction(actions.documentation)
        self.addAction(actions.first_steps)
        self.addAction(actions.about)
        self.addAction(actions.support)
        self.addAction(actions.community)
        self.addAction(actions.coffee)
