"""Barre d'outils en tête d'un onglet."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSizePolicy, QToolBar, QWidget


class TabToolBar(QToolBar):
    """Barre d'outils d'un onglet (« Graver une image »).

    À gauche : `left_actions`, des tuples (icône, libellé, infobulle,
    slot), puis `left_widgets`. Alignés à droite : `right_widgets`. Le
    plein écran, commun à tous les onglets, est dans la barre d'outils
    principale (AppActions.fullscreen).
    """

    def __init__(
        self, parent=None, left_actions=(), left_widgets=(), right_widgets=()
    ):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        for icon, label, tooltip, slot in left_actions:
            action = self.addAction(icon, label, slot)
            if tooltip:
                action.setToolTip(tooltip)
        for widget in left_widgets:
            self.addWidget(widget)
        self.addWidget(self._spacer())
        for widget in right_widgets:
            self.addWidget(widget)

    @staticmethod
    def _spacer():
        """Espace extensible qui pousse la suite de la barre à droite."""
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        return spacer
