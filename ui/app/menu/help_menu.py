"""Menu Aide : version, à propos, support et soutien."""

from PyQt6.QtWidgets import QMenu

from i18n import tr


class HelpMenu(QMenu):
    """Menu Aide : version (non cliquable), puis les boîtes de dialogue."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.help"), parent)
        self.addAction(actions.version)
        self.addSeparator()
        self.addAction(actions.about)
        self.addAction(actions.support)
        self.addAction(actions.coffee)
