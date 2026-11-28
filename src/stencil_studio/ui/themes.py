"""Couleurs de la page Stencil Studio : dictionnaire {bg, panel, panel2,
line, fg, mut, acc, acc2, onacc} passé à window.setTheme() de la page.

Dans Laser Studio Pro, ces couleurs viennent du thème de LSP
(laser_studio.ui.app.theme.page_colors) ; ici, seulement le thème par
défaut, celui du Studio lancé seul.
"""

# Thème sombre de LSP : couleurs par défaut de la fenêtre.
DEFAULT_THEME = {
    "bg": "#232323", "panel": "#303030", "panel2": "#3b3b3b", "line": "#4d4d4d",
    "fg": "#f2f2f2", "mut": "#a8a8a8", "acc": "#3a5b89", "acc2": "#6dbef9", "onacc": "#ffffff",
}

LOADING_TEXT = {"fr": "Chargement de Stencil Studio…", "en": "Loading Stencil Studio…",
                "de": "Stencil Studio wird geladen…", "es": "Cargando Stencil Studio…"}


def loading_text(language):
    """Texte affiché pendant que la page web se charge."""
    return LOADING_TEXT.get(language, "Stencil Studio…")

