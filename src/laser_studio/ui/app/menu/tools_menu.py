"""Menu Outils : assistants ponctuels, hors du flux principal d'un job."""

from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr


class ToolsMenu(QMenu):
    """Menu Outils : matrice de test, Stencil Studio, onglets annexes, puis
    les outils de l'éditeur vectoriel (import, boîte, puzzle)."""

    def __init__(self, actions, parent=None):
        super().__init__(tr("menu.tools"), parent)
        for action in (*actions.tool_actions, *actions.vector_tool_actions):
            self.addAction(action)
