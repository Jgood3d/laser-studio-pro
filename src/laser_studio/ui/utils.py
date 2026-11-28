"""Petits utilitaires partagés par les éléments d'interface."""

import os
from contextlib import contextmanager

from PyQt6.QtCore import QByteArray, QRect, QRectF, QSize, Qt
from PyQt6.QtGui import QIcon, QIconEngine, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton

from laser_studio.core.constants import JOG_BUTTON_SIZE
from laser_studio.core.paths import find_resource
from laser_studio.ui.app.theme import has_mono_drawing, mono_icons_active, monochrome_svg

# Couleur du texte dans les icônes Breeze (classe ColorScheme-Text).
BREEZE_TEXT_COLOR = "#232629"
BREEZE_DIR = os.path.join("icons", "breeze", "22x22")
BREEZE_CONTEXTS = ("actions", "categories", "apps", "devices", "preferences")


class _ThemedIconEngine(QIconEngine):
    """Icône dessinée à chaque affichage, dans la couleur du texte du thème en cours : elle suit un changement
    de thème à chaud (une icône figée garderait la couleur du thème de départ). `render(painter, rect, color)`
    dessine dans `rect` ; grisée, l'icône prend la couleur « désactivé » du thème."""

    def __init__(self, render):
        super().__init__()
        self._render = render

    def paint(self, painter, rect, mode, state):
        group = QPalette.ColorGroup.Disabled if mode == QIcon.Mode.Disabled else QPalette.ColorGroup.Normal
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._render(painter, QRectF(rect), QApplication.palette().color(group, QPalette.ColorRole.WindowText))
        painter.restore()

    def pixmap(self, size, mode, state):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRect(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pixmap

    def scaledPixmap(self, size, mode, state, scale):
        # Écran haute densité : dessinée en pixels réels, nette.
        pixmap = self.pixmap(QSize(round(size.width() * scale), round(size.height() * scale)), mode, state)
        pixmap.setDevicePixelRatio(scale)
        return pixmap

    def clone(self):
        return _ThemedIconEngine(self._render)


def painted_icon(palette, draw):
    """Icône dessinée (repère de 32 px) dans la couleur du texte du thème, redessinée à chaque affichage : elle
    suit le thème clair ou sombre, même changé à chaud. `draw(painter, color)` dessine le contenu de l'icône.
    (`palette` : gardé pour les appelants ; c'est la palette de l'application qui donne la couleur.)"""
    def render(painter, rect, color):
        painter.translate(rect.topLeft())
        painter.scale(rect.width() / 32.0, rect.height() / 32.0)
        draw(painter, color)
    return QIcon(_ThemedIconEngine(render))


def import_button(text, icon):
    """Gros bouton d'import en tête des onglets « Graver une image » et « Graver une image vectorielle » : même
    allure sur les deux (bouton principal du thème, icône à gauche, libellé sur deux lignes : « … (ou
    glisser-déposer) »). Le fichier déposé dessus est reçu par la fenêtre (FullLaserStudio.dropEvent)."""
    button = QPushButton(text)
    button.setIcon(icon)
    button.setIconSize(QSize(28, 28))
    button.setProperty("role", "primary")          # couleurs du thème (theme.py)
    button.setMinimumHeight(52)
    return button


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


def palette_icon(name, palette, fallback=None):
    """Icône `name` du pack Breeze embarqué (resources/icons/breeze),
    dessinée dans la couleur du texte de `palette`.

    Redessinée à chaque affichage (_ThemedIconEngine), elle reste lisible sur les thèmes clair et sombre,
    même changés à chaud, quel que soit le thème d'icônes du bureau (Adwaita n'a pas les icônes de nœuds,
    de dégroupage…). Les parties colorées de l'icône (rouge, bleu) sont gardées. `fallback` si l'icône manque.
    """
    path = next(
        (p for p in (find_resource(os.path.join(BREEZE_DIR, ctx, f"{name}.svg"))
                     for ctx in BREEZE_CONTEXTS) if p),
        None,
    )
    if path is None and not (mono_icons_active() and has_mono_drawing(name)):
        return fallback if fallback is not None else QIcon()
    svg = ""
    if path is not None:
        with open(path, encoding="utf-8") as f:
            svg = f.read()
    renderers = {}                          # (couleur, une seule couleur ?) -> QSvgRenderer, lu une fois

    def render(painter, rect, color):
        mono = mono_icons_active()          # lu à l'affichage : suit le thème changé à chaud
        if not svg and not mono:            # dessin propre aux thèmes d'une seule couleur, plus de mise
            if fallback is not None:
                fallback.paint(painter, rect.toRect())
            return
        key = (color.name(), mono)
        if key not in renderers:
            text = monochrome_svg(name, svg, key[0]) if mono else svg.replace(BREEZE_TEXT_COLOR, key[0])
            renderers[key] = QSvgRenderer(QByteArray(text.encode("utf-8")))
        renderers[key].render(painter, rect)

    return QIcon(_ThemedIconEngine(render))


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


@contextmanager
def busy_cursor():
    """Curseur d'attente pendant un calcul long (imbrication, série, export)."""
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def zoom_shortcuts(widget, zoom_in, zoom_out):
    """Ctrl++ (ou Ctrl+=, la touche « + » des claviers QWERTY) et Ctrl+- appellent `zoom_in()` /
    `zoom_out()` quand `widget` ou l'un de ses champs a le focus."""
    from PyQt6.QtGui import QKeySequence, QShortcut     # importé ici : seuls quelques onglets s'en servent

    for keys, slot in ((QKeySequence.StandardKey.ZoomIn, zoom_in), (QKeySequence("Ctrl+="), zoom_in),
                       (QKeySequence.StandardKey.ZoomOut, zoom_out)):
        shortcut = QShortcut(keys if isinstance(keys, QKeySequence) else QKeySequence(keys), widget)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(slot)
