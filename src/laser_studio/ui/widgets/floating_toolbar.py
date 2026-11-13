"""Petite barre d'outils posée par-dessus une zone (aperçu, canevas, table)."""

from PyQt6.QtCore import QEvent, QPoint, QSize, Qt
from PyQt6.QtWidgets import QSplitter, QToolBar, QWidget

# Espace laissé entre la barre et le bord de la zone. En haut, il laisse
# visibles le titre du cadre ou la barre d'onglets de la zone.
DEFAULT_TOP_MARGIN = 26
DEFAULT_MARGIN = 8

ANCHORS = ("top", "bottom", "right")


class FloatingToolBar(QToolBar):
    """Barre flottante au-dessus du contenu de `host`, qui suit ses
    déplacements et changements de taille.

    `anchor` : "top" (centrée en haut, par défaut), "bottom" (centrée en
    bas) ou "right" (verticale, centrée sur le bord droit).

    `items` : des QAction existantes (même icône, libellé, infobulle et état
    actif / coché que partout ailleurs), des widgets (cases à cocher…), ou
    None pour un séparateur :

        FloatingToolBar([a.image_undo, a.image_redo, None, a.mirror_h], preview)
        FloatingToolBar(align_actions, canvas, anchor="right",
                        button_style=Qt.ToolButtonStyle.ToolButtonTextOnly)

    La barre est enfant du premier parent de `host` qui n'est pas un
    QSplitter : un séparateur l'adopterait comme une zone de plus.
    """

    def __init__(
        self,
        items,
        host,
        top_margin=DEFAULT_TOP_MARGIN,
        anchor="top",
        button_style=Qt.ToolButtonStyle.ToolButtonIconOnly,
        margin=DEFAULT_MARGIN,
    ):
        if anchor not in ANCHORS:
            raise ValueError(f"anchor : {ANCHORS}, pas {anchor!r}")
        parent = host.parentWidget()
        watched = [host]
        while isinstance(parent, QSplitter):
            watched.append(parent)
            parent = parent.parentWidget()
        super().__init__(parent)
        self._host = host
        self._anchor = anchor
        self._top_margin = top_margin
        self._margin = margin
        self.setObjectName("floating_toolbar")
        self.setOrientation(
            Qt.Orientation.Vertical
            if anchor == "right"
            else Qt.Orientation.Horizontal
        )
        self.setToolButtonStyle(button_style)
        self.setIconSize(QSize(20, 20))
        self.setMovable(False)
        self.setStyleSheet(
            "QToolBar#floating_toolbar { background: palette(window); "
            "border: 1px solid palette(mid); border-radius: 6px; "
            "padding: 2px; }"
        )
        for item in items:
            if item is None:
                self.addSeparator()
            elif isinstance(item, QWidget):
                self.addWidget(item)
            else:
                self.addAction(item)
        for widget in watched:
            widget.installEventFilter(self)
        self.adjustSize()
        self.place()
        self.raise_()

    def place(self):
        """Place la barre contre le bord choisi de la zone (coordonnées du
        parent)."""
        self.adjustSize()
        origin = self._host.mapTo(self.parentWidget(), QPoint(0, 0))
        width, height = self._host.width(), self._host.height()
        if self._anchor == "right":
            x = origin.x() + width - self.width() - self._margin
            y = origin.y() + max(0, (height - self.height()) // 2)
        else:
            x = origin.x() + max(0, (width - self.width()) // 2)
            if self._anchor == "top":
                y = origin.y() + self._top_margin
            else:
                y = origin.y() + height - self.height() - self._margin
        self.move(max(origin.x(), x), max(origin.y(), y))
        self.raise_()

    def eventFilter(self, watched, event):
        if event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        ):
            self.place()
        return super().eventFilter(watched, event)
