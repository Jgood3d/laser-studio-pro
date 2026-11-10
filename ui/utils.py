"""Petits utilitaires partagés par les éléments d'interface."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtWidgets import QStyle, QToolButton

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


def fullscreen_icon(widget):
    """Icône « plein écran » du thème, sinon bouton d'agrandissement de Qt."""
    fallback = QStyle.StandardPixmap.SP_TitleBarMaxButton
    return QIcon.fromTheme(
        QIcon.ThemeIcon.ViewFullscreen, widget.style().standardIcon(fallback)
    )


def themed_icon(widget, theme_icon, fallback):
    """Icône du thème du système, sinon icône standard du style Qt."""
    return QIcon.fromTheme(theme_icon, widget.style().standardIcon(fallback))


def scaled_to_width_hidpi(pixmap, width, ratio):
    """Réduit `pixmap` pour l'afficher sur `width` pixels logiques, net sur
    un écran à l'échelle `ratio` (2.0 pour un écran haute résolution réglé
    à 200 %).

    Réduire à `width` pixels réels puis laisser Qt agrandir l'image ×ratio
    à l'affichage la rendrait floue : elle est donc réduite à width × ratio
    pixels réels, marqués comme tels."""
    ratio = max(1.0, ratio)
    scaled = pixmap.scaledToWidth(
        round(width * ratio), Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(ratio)
    return scaled
