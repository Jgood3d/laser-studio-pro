"""Petite barre d'outils posée par-dessus une zone (aperçu d'image)."""

from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtWidgets import QToolBar

# Espace laissé au-dessus de la barre : le titre du cadre ou la barre
# d'onglets de la zone restent visibles.
DEFAULT_TOP_MARGIN = 26


class FloatingToolBar(QToolBar):
    """Barre d'icônes flottante, centrée en haut de `host`, au-dessus de son
    contenu. Elle suit les déplacements et changements de taille de `host`.

    Elle est enfant du parent de `host`, pas de `host` lui-même : un
    QSplitter adopterait la barre comme une zone de plus.

    Elle reprend des QAction existantes (même icône, infobulle et état
    actif / coché que partout ailleurs) ; None dans la liste ajoute un
    séparateur :

        FloatingToolBar([a.image_undo, a.image_redo, None, a.mirror_h], preview)
    """

    def __init__(self, actions, host, top_margin=DEFAULT_TOP_MARGIN):
        super().__init__(host.parentWidget())
        self._host = host
        self._top_margin = top_margin
        self.setObjectName("floating_toolbar")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setIconSize(QSize(20, 20))
        self.setMovable(False)
        self.setStyleSheet(
            "QToolBar#floating_toolbar { background: palette(window); "
            "border: 1px solid palette(mid); border-radius: 6px; "
            "padding: 2px; }"
        )
        for action in actions:
            if action is None:
                self.addSeparator()
            else:
                self.addAction(action)
        host.installEventFilter(self)
        self.adjustSize()
        self.place()
        self.raise_()

    def place(self):
        """Centre la barre en haut de la zone (coordonnées du parent)."""
        self.adjustSize()
        area = self._host.geometry()
        x = area.x() + max(0, (area.width() - self.width()) // 2)
        self.move(x, area.y() + self._top_margin)
        self.raise_()

    def eventFilter(self, watched, event):
        if watched is self._host and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        ):
            self.place()
        return super().eventFilter(watched, event)
