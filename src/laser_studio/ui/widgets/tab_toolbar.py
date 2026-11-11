"""Barre d'outils en tête d'un onglet, avec le bouton « Plein écran »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QSizePolicy, QToolBar, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.utils import fullscreen_icon


class TabToolBar(QToolBar):
    """Barre d'outils d'un onglet (Images, PNG→SVG, Séparation, 2D, Console).

    À gauche : `left_actions`, des tuples (icône, libellé, infobulle,
    slot), puis `left_widgets`. Alignés à droite : `right_widgets`, puis
    le bouton « Plein écran », qui émet `fullscreen_requested`.

    `fullscreen_action` est le bouton « Plein écran » : la fenêtre le
    masque pendant que l'onglet est affiché en plein écran.
    """

    fullscreen_requested = pyqtSignal()

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
        self.fullscreen_action = self.addAction(
            fullscreen_icon(self), tr("ui.vector_fullscreen")
        )
        self.fullscreen_action.triggered.connect(self.fullscreen_requested)

    @staticmethod
    def _spacer():
        """Espace extensible qui pousse la suite de la barre à droite."""
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        return spacer
