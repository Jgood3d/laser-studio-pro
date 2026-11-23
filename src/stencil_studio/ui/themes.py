"""Couleurs de la page Stencil Studio : dictionnaire {bg, panel, panel2,
line, fg, mut, acc, acc2, onacc} passé à window.setTheme() de la page.

Dans Laser Studio Pro, ces couleurs viennent du thème de LSP
(laser_studio.ui.app.theme.page_colors) ; ici, seulement le thème par
défaut et un repli calculé d'après la palette Qt.
"""
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# Thème sombre de LSP : couleurs par défaut de la fenêtre.
DEFAULT_THEME = {
    "bg": "#232323", "panel": "#303030", "panel2": "#3b3b3b", "line": "#4d4d4d",
    "fg": "#f2f2f2", "mut": "#a8a8a8", "acc": "#3a5b89", "acc2": "#6dbef9", "onacc": "#ffffff",
}
LIGHT_THEME = {
    "bg": "#f3f3f3", "panel": "#ffffff", "panel2": "#f0f0f0", "line": "#d0d0d0",
    "fg": "#1a1a1a", "mut": "#666666", "acc": "#0078d4", "acc2": "#4aa3e8", "onacc": "#ffffff",
}

LOADING_TEXT = {"fr": "Chargement de Stencil Studio…", "en": "Loading Stencil Studio…",
                "de": "Stencil Studio wird geladen…", "es": "Cargando Stencil Studio…"}


def loading_text(language):
    """Texte affiché pendant que la page web se charge."""
    return LOADING_TEXT.get(language, "Stencil Studio…")


def theme_from_palette(pal=None):
    """Couleurs de la page déduites de la palette Qt (fenêtre, texte, accent...)."""
    app = QApplication.instance()
    pal = pal or (app.palette() if app else None)
    if pal is None:
        return dict(DEFAULT_THEME)
    R = QPalette.ColorRole

    def mix(a, b, t):
        return QColor(int(a.red() * (1 - t) + b.red() * t), int(a.green() * (1 - t) + b.green() * t),
                      int(a.blue() * (1 - t) + b.blue() * t))

    win, base, btn = pal.color(R.Window), pal.color(R.Base), pal.color(R.Button)
    fg, acc = pal.color(R.WindowText), pal.color(R.Highlight)
    if win.lightness() > 140:
        return dict(LIGHT_THEME)
    lum = 0.299 * acc.red() + 0.587 * acc.green() + 0.114 * acc.blue()
    return {
        "bg": (base if base.lightness() <= win.lightness() else win.darker(115)).name(),
        "panel": win.name(),
        "panel2": btn.name(),
        "line": mix(win, fg, 0.18).name(),
        "fg": fg.name(),
        "mut": mix(win, fg, 0.58).name(),
        "acc": acc.name(),
        "acc2": acc.lighter(130).name(),
        "onacc": "#111111" if lum > 140 else "#ffffff",
    }
