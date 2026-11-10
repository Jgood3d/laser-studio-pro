"""Petits utilitaires partagés par les éléments d'interface."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtWidgets import QToolButton

from app_constants import JOG_BUTTON_SIZE


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


def tool_button(icon, tooltip, color=None):
    """Bouton carré à icône des panneaux de la machine, libellé en infobulle.

    `color` : couleur de fond (boutons Pause, Reprise, Reset, Arrêt
    d'urgence et Envoyer). Sans couleur, le bouton est plat.
    """
    button = QToolButton()
    button.setIcon(icon)
    button.setIconSize(QSize(24, 24))
    button.setToolTip(tooltip)
    button.setFixedSize(JOG_BUTTON_SIZE, JOG_BUTTON_SIZE)
    button.setAutoRaise(color is None)
    if color:
        # Gris quand le bouton est désactivé (graveur non connecté) : sinon
        # sa couleur le ferait paraître actif.
        button.setStyleSheet(
            f"QToolButton {{ background-color: {color}; "
            "border-radius: 4px; }"
            "QToolButton:disabled { background-color: #b0b0b0; }"
        )
    return button


def themed_icon(widget, theme_icon, fallback):
    """Icône du thème du système, sinon icône standard du style Qt."""
    return QIcon.fromTheme(theme_icon, widget.style().standardIcon(fallback))
