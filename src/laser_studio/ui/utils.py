"""Petits utilitaires partagés par les éléments d'interface."""

import os

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QStyle, QToolButton

from laser_studio.core.constants import JOG_BUTTON_SIZE
from laser_studio.core.paths import find_resource

# Couleur du texte dans les icônes Breeze (classe ColorScheme-Text).
BREEZE_TEXT_COLOR = "#232629"
BREEZE_ACTIONS_DIR = os.path.join("icons", "breeze", "22x22", "actions")


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


def palette_icon(name, palette, fallback=None):
    """Icône `name` du pack Breeze embarqué (resources/icons/breeze),
    dessinée dans la couleur du texte de `palette`.

    Elle reste ainsi lisible sur les thèmes clair et sombre de
    l'application, quel que soit le thème d'icônes du bureau (Adwaita n'a
    pas les icônes de nœuds, de dégroupage…). Les parties colorées de
    l'icône (rouge, bleu) sont gardées. `fallback` si l'icône manque.
    """
    path = find_resource(os.path.join(BREEZE_ACTIONS_DIR, f"{name}.svg"))
    if path is None:
        return fallback if fallback is not None else QIcon()
    with open(path, encoding="utf-8") as f:
        svg = f.read()
    color = palette.color(QPalette.ColorRole.WindowText).name()
    renderer = QSvgRenderer(QByteArray(svg.replace(BREEZE_TEXT_COLOR, color).encode("utf-8")))
    icon = QIcon()
    for size in (22, 44):  # 44 : écrans haute résolution
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


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
