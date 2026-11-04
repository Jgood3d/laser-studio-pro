"""Petits utilitaires partagés par les éléments d'interface."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPalette, QPixmap


def painted_icon(palette, draw):
    """Icône dessinée (32 px) dans la couleur du texte de `palette`.

    Elle suit ainsi le thème clair ou sombre. `draw(painter, color)`
    dessine le contenu de l'icône.
    """
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = palette.color(QPalette.ColorRole.WindowText)
    draw(painter, color)
    painter.end()
    return QIcon(pixmap)
