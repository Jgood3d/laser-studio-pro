"""Thèmes de Laser Studio Pro (palette + feuille de style) : clair, sombre, Dusk, New Dusk, New Dawn, Warm dim, Neon,
Retro 80, Jarvis."""
import re
import shutil
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPalette

from laser_studio.core.paths import resource_candidates
from laser_studio.core.preferences import ui_preferences


# ---------------------------------------------------------------------------
# Définition des thèmes
# ---------------------------------------------------------------------------

THEMES = {
    "dark": {
        "label_key": "theme.dark",
        "window": "#1e1e1e",
        "base": "#121212",
        "alt": "#2d2d2d",
        "button": "#2d2d2d",
        "button_hover": "#3a3a3a",
        "border": "#555555",
        "text": "#dcdcdc",
        "muted": "#888888",
        "accent": "#2b5c8f",
        "accent_hover": "#4a8ad4",
        "on_accent": "#ffffff",
        "tooltip_bg": "#2d2d2d",
        "tooltip_fg": "#dcdcdc",
        "link": "#5aa9ff",
        "group_bg": "#2a2a2a",
        "input_bg": "#121212",
        "toolbar_bg": "#252525",
        "tab_bg": "#2a2a2a",
        "tab_selected": "#1e1e1e",
        "menu_bg": "#2a2a2a",
        "menu_sel": "#2b5c8f",
        "scroll": "#3a3a3a",
        "disabled": "#777777",
    },
    "light": {
        "label_key": "theme.light",
        "window": "#f3f3f3",
        "base": "#ffffff",
        "alt": "#f5f5f5",
        "button": "#ffffff",
        "button_hover": "#e5f1fb",
        "border": "#adadad",
        "text": "#1a1a1a",
        "muted": "#666666",
        "accent": "#0078d4",
        "accent_hover": "#4aa3e8",
        "on_accent": "#ffffff",
        "tooltip_bg": "#ffffff",
        "tooltip_fg": "#1a1a1a",
        "link": "#0066cc",
        "group_bg": "#ffffff",
        "input_bg": "#ffffff",
        "toolbar_bg": "#f9f9f9",
        "tab_bg": "#ebebeb",
        "tab_selected": "#ffffff",
        "menu_bg": "#ffffff",
        "menu_sel": "#e5f1fb",
        "scroll": "#c0c0c0",
        "disabled": "#a0a0a0",
    },
    # Gris-bleu doux (type Nord) — confortable pour de longues sessions
    "dusk": {
        "label_key": "theme.dusk",
        "window": "#2b303b",
        "base": "#232831",
        "alt": "#353b4a",
        "button": "#3d4455",
        "button_hover": "#4a5266",
        "border": "#4f5666",
        "text": "#d8dee9",
        "muted": "#9aa3b5",
        "accent": "#88c0d0",
        "accent_hover": "#8fbcbb",
        "on_accent": "#2b303b",
        "tooltip_bg": "#353b4a",
        "tooltip_fg": "#d8dee9",
        "link": "#88c0d0",
        "group_bg": "#353b4a",
        "input_bg": "#232831",
        "toolbar_bg": "#2f3542",
        "tab_bg": "#353b4a",
        "tab_selected": "#2b303b",
        "menu_bg": "#353b4a",
        "menu_sel": "#434c5e",
        "scroll": "#4f5666",
        "disabled": "#6a7385",
    },
    # New Dusk : Dusk modernisé, sur les couleurs du thème Solarized Dark de VS Code (bleu pétrole profond,
    # panneaux plus sombres que la zone de travail, accent bleu, boutons sarcelle). Style « modern » : à plat,
    # coins arrondis, onglets soulignés, barres de défilement fines (voir _modern_stylesheet).
    "new_dusk": {
        "label_key": "theme.new_dusk",
        "mono_icons": True,             # icônes d'une seule couleur, comme VS Code (voir monochrome_svg)
        "modern": True,
        "window": "#002b36",
        "base": "#00212b",
        "alt": "#073642",
        "button": "#0a3d4a",
        "button_hover": "#0f4c5c",
        "border": "#0e4b5b",
        "text": "#cdd8da",
        "muted": "#7e9ca2",
        "accent": "#047aa6",
        "accent_hover": "#1b93c0",
        "on_accent": "#ffffff",
        "tooltip_bg": "#073642",
        "tooltip_fg": "#cdd8da",
        "link": "#3b9be0",
        "group_bg": "#04303c",
        "input_bg": "#003847",
        "toolbar_bg": "#00212b",
        "tab_bg": "#004052",
        "tab_separator": "#003948",
        "sidebar": "#00212b",
        "panel_border": "#0e2931",
        "tab_selected": "#002b36",
        "menu_bg": "#073642",
        "menu_sel": "#005a70",
        "scroll": "#0f5466",
        "disabled": "#5a7278",
        "primary": "#15706d",
        "primary_hover": "#1d8a86",
        # Zones de dessin (canevas vectoriel, aperçus) : voir theme_color.
        "canvas": "#00212b",
        "canvas_minor": "#03303c",
        "canvas_grid": "#0a4050",
        "canvas_edge": "#2f7a8a",
        "canvas_label": "#6a949b",
    },
    # Version claire de New Dusk, d'après le thème « Light Modern » de VS Code : blanc, gris neutres, bleu.
    "new_dawn": {
        "label_key": "theme.new_dawn",
        "mono_icons": True,
        "modern": True,
        "window": "#ffffff",
        "base": "#ffffff",
        "alt": "#f3f3f3",
        "button": "#ededed",
        "button_hover": "#e1e1e1",
        "border": "#d4d4d4",
        "text": "#3b3b3b",
        "muted": "#6e6e6e",
        "accent": "#005fb8",
        "accent_hover": "#0258a8",
        "on_accent": "#ffffff",
        "tooltip_bg": "#f8f8f8",
        "tooltip_fg": "#3b3b3b",
        "link": "#005fb8",
        "group_bg": "#fbfbfb",
        "input_bg": "#ffffff",
        "toolbar_bg": "#f8f8f8",
        "tab_bg": "#f8f8f8",
        "tab_separator": "#e5e5e5",
        "sidebar": "#f8f8f8",
        "panel_border": "#e5e5e5",
        "tab_selected": "#ffffff",
        "menu_bg": "#ffffff",
        "menu_sel": "#dbe8f5",
        "scroll": "#c4c4c4",
        "disabled": "#a6a6a6",
        "primary": "#0f7b6c",
        "primary_hover": "#0b6559",
        "canvas": "#ffffff",
        "canvas_minor": "#f2f2f2",
        "canvas_grid": "#e2e2e2",
        "canvas_edge": "#9a9a9a",
        "canvas_label": "#767676",
        "canvas_selection": "#3b3b3b",   # contour de sélection (blanc, invisible sur fond clair)
    },
    # Gris chaud ambré — ambiance atelier / bois
    "warm": {
        "label_key": "theme.warm",
        "window": "#2c2825",
        "base": "#241f1c",
        "alt": "#3a3530",
        "button": "#403a34",
        "button_hover": "#4e463f",
        "border": "#5a524a",
        "text": "#e8e0d5",
        "muted": "#a89c8e",
        "accent": "#d4a574",
        "accent_hover": "#e0b88a",
        "on_accent": "#2c2825",
        "tooltip_bg": "#3a3530",
        "tooltip_fg": "#e8e0d5",
        "link": "#d4a574",
        "group_bg": "#3a3530",
        "input_bg": "#241f1c",
        "toolbar_bg": "#322d29",
        "tab_bg": "#3a3530",
        "tab_selected": "#2c2825",
        "menu_bg": "#3a3530",
        "menu_sel": "#4a433c",
        "scroll": "#5a524a",
        "disabled": "#7a6e62",
    },
    # Neon laser — fun, cyber, accents cyan + magenta
    "neon": {
        "label_key": "theme.neon",
        "window": "#0d0b14",
        "base": "#120f1c",
        "alt": "#1a1628",
        "button": "#1f1a30",
        "button_hover": "#2a2340",
        "border": "#3d3560",
        "text": "#e8e6f2",
        "muted": "#9b93b8",
        "accent": "#00e5c3",
        "accent_hover": "#5dffe0",
        "on_accent": "#0d0b14",
        "tooltip_bg": "#1a1628",
        "tooltip_fg": "#e8e6f2",
        "link": "#ff4ecd",
        "group_bg": "#1a1628",
        "input_bg": "#120f1c",
        "toolbar_bg": "#14101f",
        "tab_bg": "#1a1628",
        "tab_selected": "#0d0b14",
        "menu_bg": "#1a1628",
        "menu_sel": "#2a2340",
        "scroll": "#3d3560",
        "disabled": "#6a6288",
    },
    # Rétro années 80 — synthwave / vaporwave
    "retro80": {
        "label_key": "theme.retro80",
        "window": "#1a0a2e",
        "base": "#12061f",
        "alt": "#2a1450",
        "button": "#2d1b4e",
        "button_hover": "#3d2868",
        "border": "#7b2cbf",
        "text": "#f0e6ff",
        "muted": "#b8a0d0",
        "accent": "#ff2a6d",
        "accent_hover": "#ff6b9d",
        "on_accent": "#1a0a2e",
        "tooltip_bg": "#2a1450",
        "tooltip_fg": "#f0e6ff",
        "link": "#05d9e8",
        "group_bg": "#2a1450",
        "input_bg": "#12061f",
        "toolbar_bg": "#1f0f38",
        "tab_bg": "#2a1450",
        "tab_selected": "#1a0a2e",
        "menu_bg": "#2a1450",
        "menu_sel": "#3d2868",
        "scroll": "#7b2cbf",
        "disabled": "#6a5080",
    },
    # Jarvis — HUD sombre, cyan froid type interface d'assistance
    "jarvis": {
        "label_key": "theme.jarvis",
        "window": "#0a1218",
        "base": "#060d12",
        "alt": "#12202a",
        "button": "#152836",
        "button_hover": "#1c3548",
        "border": "#1e4a5c",
        "text": "#d4eef5",
        "muted": "#6a9aab",
        "accent": "#00c8e0",
        "accent_hover": "#5de8f5",
        "on_accent": "#061018",
        "tooltip_bg": "#12202a",
        "tooltip_fg": "#d4eef5",
        "link": "#7fd4ff",
        "group_bg": "#0f1a22",
        "input_bg": "#060d12",
        "toolbar_bg": "#0c1620",
        "tab_bg": "#12202a",
        "tab_selected": "#0a1218",
        "menu_bg": "#0f1a22",
        "menu_sel": "#1c3548",
        "scroll": "#1e4a5c",
        "disabled": "#4a6a78",
    },
}


def page_colors(theme_name):
    """Couleurs d'une page web intégrée (Stencil Studio) pour le thème `theme_name` :
    {bg, panel, panel2, line, fg, mut, acc, acc2, onacc}."""
    c = THEMES[normalize_theme_name(theme_name)]
    return {"bg": c["base"], "panel": c["window"], "panel2": c["alt"], "line": c["border"], "fg": c["text"],
            "mut": c["muted"], "acc": c["accent"], "acc2": c["accent_hover"], "onacc": c["on_accent"]}


def theme_color(key, default):
    """Couleur `key` du thème choisi (zones de dessin : « canvas », « canvas_grid »…), ou `default` pour un thème
    qui ne la définit pas : ces thèmes gardent leurs couleurs d'origine."""
    return QColor(THEMES[current_theme_name()].get(key, default))


def _qcolor(hex_color: str) -> QColor:
    return QColor(hex_color)


def _build_palette(c: dict) -> QPalette:
    pal = QPalette()
    win, base, alt = _qcolor(c["window"]), _qcolor(c["base"]), _qcolor(c["alt"])
    text, btn, accent = _qcolor(c["text"]), _qcolor(c["button"]), _qcolor(c["accent"])
    on_acc, muted = _qcolor(c["on_accent"]), _qcolor(c["muted"])
    tip_bg, tip_fg = _qcolor(c["tooltip_bg"]), _qcolor(c["tooltip_fg"])
    link, disabled = _qcolor(c["link"]), _qcolor(c["disabled"])

    pal.setColor(QPalette.ColorRole.Window, win)
    pal.setColor(QPalette.ColorRole.WindowText, text)
    pal.setColor(QPalette.ColorRole.Base, base)
    pal.setColor(QPalette.ColorRole.AlternateBase, alt)
    pal.setColor(QPalette.ColorRole.ToolTipBase, tip_bg)
    pal.setColor(QPalette.ColorRole.ToolTipText, tip_fg)
    pal.setColor(QPalette.ColorRole.Text, text)
    pal.setColor(QPalette.ColorRole.Button, btn)
    pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    pal.setColor(QPalette.ColorRole.Link, link)
    pal.setColor(QPalette.ColorRole.Highlight, accent)
    # Texte sur sélection : sombre si accent clair (dusk/warm), blanc sinon
    lum = 0.299 * accent.red() + 0.587 * accent.green() + 0.114 * accent.blue()
    pal.setColor(QPalette.ColorRole.HighlightedText, on_acc if lum > 140 else QColor(255, 255, 255))
    pal.setColor(QPalette.ColorRole.PlaceholderText, muted)
    pal.setColor(QPalette.ColorRole.Light, alt)
    pal.setColor(QPalette.ColorRole.Midlight, btn)
    pal.setColor(QPalette.ColorRole.Mid, _qcolor(c["border"]))
    pal.setColor(QPalette.ColorRole.Dark, _qcolor(c["border"]))
    pal.setColor(QPalette.ColorRole.Shadow, QColor(0, 0, 0))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        pal.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, alt)
    return pal


# Icônes Breeze à plusieurs teintes, illisibles d'une seule couleur : remplacées par ces dessins au trait (22 px).
_MONO_STROKE = 'fill="none" stroke="#232629" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
_MONO_DRAWINGS = {
    "color-management": '<circle cx="8" cy="8.5" r="5"/><circle cx="14" cy="8.5" r="5"/><circle cx="11" cy="13.5" r="5"/>',
    "preferences-system": '<path d="M3 6h3M10 6h9M3 11h9M16 11h3M3 16h1M8 16h11"/><circle cx="8" cy="6" r="2"/>'
                          '<circle cx="14" cy="11" r="2"/><circle cx="6" cy="16" r="2"/>',
    "utilities-terminal": '<rect x="2.75" y="3.75" width="16.5" height="14.5" rx="2"/><path d="M6 9l3 2.5L6 14M11 14h5"/>',
    "applications-graphics": '<rect x="2.75" y="2.75" width="16.5" height="16.5" rx="2"/><circle cx="8" cy="8.5" r="2.5"/>'
                             '<path d="M10.5 16l3.5-6 3.5 6z"/>',
    "preferences-desktop-locale": '<circle cx="11" cy="11" r="8"/><ellipse cx="11" cy="11" rx="3.5" ry="8"/>'
                                  '<path d="M3 11h16M4.5 7h13M4.5 15h13"/>',
    "preferences-desktop-theme": '<circle cx="11" cy="11" r="8"/><path d="M11 3a8 8 0 0 1 0 16z" fill="#232629"/>',
    # Absentes du pack embarqué (icône du système sinon) :
    "camera-photo": '<path d="M2.75 7.5a1.5 1.5 0 0 1 1.5-1.5h2.5l1.5-2h5.5l1.5 2h2.5a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1'
                    '-1.5 1.5h-13.5a1.5 1.5 0 0 1-1.5-1.5z"/><circle cx="11" cy="11.5" r="3.5"/>',
    "document-properties": '<path d="M5 2.75h8l4 4v12.5h-12z"/><path d="M13 2.75v4h4M8 11h6M8 14h6M8 17h4"/>',
}
_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def has_mono_drawing(name):
    """L'icône `name` a-t-elle son propre dessin au trait pour les thèmes aux icônes d'une seule couleur ?"""
    return name in _MONO_DRAWINGS


def mono_icons_active():
    """Le thème choisi veut-il des icônes d'une seule couleur ?"""
    return bool(THEMES[current_theme_name()].get("mono_icons"))


def monochrome_svg(name, svg, color):
    """Icône Breeze `name` (texte SVG `svg`) entièrement dans la couleur `color` : chaque couleur du dessin la
    prend, sauf pour les icônes à plusieurs teintes, redessinées au trait (_MONO_DRAWINGS)."""
    drawing = _MONO_DRAWINGS.get(name)
    if drawing:
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 22 22">'
               f'<g {_MONO_STROKE}>{drawing}</g></svg>')
    return _HEX_COLOR.sub(color, svg)


def _mono_icon_theme(color):
    """Copie du pack Breeze embarqué, d'une seule couleur `color`, écrite une fois dans le dossier temporaire ;
    renvoie le dossier qui la contient (à ajouter aux chemins des thèmes d'icônes) et son nom, ou None."""
    source = next((Path(b) / "breeze" for b in resource_candidates("icons")
                   if (Path(b) / "breeze" / "index.theme").is_file()), None)
    if source is None:
        return None
    name = f"mono-{color.lstrip('#')}"
    root = Path(tempfile.gettempdir()) / "laser-studio-theme" / "icons"
    target = root / name
    try:
        if not (target / "index.theme").is_file():
            for svg in source.rglob("*.svg"):
                out = target / svg.relative_to(source)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(monochrome_svg(svg.stem, svg.read_text(encoding="utf-8"), color), encoding="utf-8")
            index = (source / "index.theme").read_text(encoding="utf-8")
            (target / "index.theme").write_text(re.sub(r"(?m)^Name=.*$", f"Name={name}", index), encoding="utf-8")
    except OSError:
        shutil.rmtree(target, ignore_errors=True)    # copie incomplète : on garde les icônes Breeze
        return None
    return str(root), name


def _switch(on, track, knob):
    """Chemin d'un interrupteur SVG (30 × 16 px) : piste `track`, bouton `knob` à droite si `on`. Écrit une fois
    dans le dossier temporaire, comme les chevrons (_chevron)."""
    x = 22 if on else 8
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="30" height="16" viewBox="0 0 30 16">'
           f'<rect x="0.5" y="0.5" width="29" height="15" rx="7.5" fill="{track}"/>'
           f'<circle cx="{x}" cy="8" r="5.5" fill="{knob}"/></svg>')
    return _temp_svg(f"switch-{int(on)}-{track.lstrip('#')}-{knob.lstrip('#')}", svg)


def _temp_svg(name, svg):
    """Fichier `name`.svg du dossier temporaire (écrit s'il manque), pour url() d'une feuille de style ; "" si
    l'écriture échoue (l'élément s'affiche alors sans image plutôt qu'une erreur au démarrage)."""
    folder = Path(tempfile.gettempdir()) / "laser-studio-theme"
    path = folder / f"{name}.svg"
    try:
        if not path.exists():
            folder.mkdir(exist_ok=True)
            path.write_text(svg, encoding="utf-8")
    except OSError:
        return ""
    return path.as_posix()


def _cross(color):
    """Chemin d'une petite croix SVG (fermeture d'un onglet) de couleur `color` (_temp_svg)."""
    return _temp_svg(f"cross-{color.lstrip('#')}",
                     f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
                     f'<path d="M3 3l6 6M9 3l-6 6" stroke="{color}" stroke-width="1.4" stroke-linecap="round"/></svg>')


def _chevron(direction, color):
    """Chemin d'un chevron SVG (flèche « up » ou « down » des champs numériques) de couleur `color`. Une feuille de
    style Qt ne sait pas colorer une image : un petit fichier par couleur (_temp_svg)."""
    points = "1,6 5,2 9,6" if direction == "up" else "1,2 5,6 9,2"
    return _temp_svg(f"chevron-{direction}-{color.lstrip('#')}",
                     f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="8" viewBox="0 0 10 8">'
                     f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.6" '
                     f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _build_stylesheet(c: dict) -> str:
    """Feuille de style commune paramétrée par les couleurs du thème."""
    return f"""
    * {{
        color: {c["text"]};
    }}
    QMainWindow, QDialog, QWidget {{
        background-color: {c["window"]};
        color: {c["text"]};
    }}
    QMenuBar {{
        background-color: {c["toolbar_bg"]};
        color: {c["text"]};
        border-bottom: 1px solid {c["border"]};
        spacing: 2px;
    }}
    QMenuBar::item {{
        background: transparent;
        color: {c["text"]};
        padding: 4px 10px;
    }}
    QMenuBar::item:selected, QMenuBar::item:pressed {{
        background-color: {c["menu_sel"]};
        color: {c["text"]};
    }}
    QMenu {{
        background-color: {c["menu_bg"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        padding: 4px;
    }}
    QMenu::item {{
        color: {c["text"]};
        padding: 6px 28px 6px 12px;
        background-color: transparent;
    }}
    QMenu::item:selected {{
        background-color: {c["menu_sel"]};
        color: {c["text"]};
    }}
    QMenu::separator {{
        height: 1px;
        background: {c["border"]};
        margin: 4px 8px;
    }}
    QToolBar {{
        background-color: {c["toolbar_bg"]};
        color: {c["text"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        spacing: 4px;
        padding: 2px;
    }}
    QToolBar QToolButton {{
        background-color: transparent;
        color: {c["text"]};
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px;
    }}
    QToolBar QToolButton:hover {{
        background-color: {c["button_hover"]};
        border: 1px solid {c["border"]};
    }}
    QToolBar QToolButton:pressed, QToolBar QToolButton:checked {{
        background-color: {c["accent"]};
        border: 1px solid {c["accent_hover"]};
        color: {c["on_accent"]};
    }}
    QStatusBar {{
        background-color: {c["window"]};
        color: {c["text"]};
        border-top: 1px solid {c["border"]};
    }}
    QTabWidget::pane {{
        background-color: {c["base"]};
        border: 1px solid {c["border"]};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {c["tab_bg"]};
        color: {c["text"]};
        padding: 7px 16px;
        border: 1px solid {c["border"]};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {c["tab_selected"]};
        color: {c["text"]};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {c["button_hover"]};
    }}
    QGroupBox {{
        background-color: {c["group_bg"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 14px;
        font-weight: 600;
        color: {c["text"]};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
        color: {c["text"]};
        background-color: {c["group_bg"]};
    }}
    QLabel {{
        background-color: transparent;
        color: {c["text"]};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QListView, QTreeView, QTableView, QAbstractItemView {{
        background-color: {c["input_bg"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 3px;
        padding: 3px 6px;
        selection-background-color: {c["accent"]};
        selection-color: {c["on_accent"]};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {c["accent"]};
    }}
    QComboBox QAbstractItemView {{
        background-color: {c["menu_bg"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        selection-background-color: {c["menu_sel"]};
        selection-color: {c["text"]};
    }}
    QTableView, QTreeView {{
        /* Pas de marge intérieure : elle décalerait les cellules par rapport
           à la ligne d'en-tête. */
        padding: 0px;
    }}
    QHeaderView {{
        /* L'en-tête est aussi un QAbstractItemView : sans ceci, il reçoit la
           marge et la bordure des champs de saisie et se décale par rapport
           aux colonnes. */
        padding: 0px;
        border: none;
    }}
    QHeaderView::section {{
        background-color: {c["alt"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        padding: 4px 8px;
    }}
    QPushButton {{
        background-color: {c["button"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 4px 8px;
        min-width: 1.2em;
    }}
    QPushButton:hover {{
        background-color: {c["button_hover"]};
        border: 1px solid {c["accent"]};
        color: {c["text"]};
    }}
    QPushButton:pressed {{
        background-color: {c["accent"]};
        color: {c["on_accent"]};
    }}
    QPushButton:disabled {{
        background-color: {c["alt"]};
        color: {c["disabled"]};
        border: 1px solid {c["border"]};
    }}
    QPushButton:checked {{
        background-color: {c["accent"]};
        border: 1px solid {c["accent_hover"]};
        color: {c["on_accent"]};
    }}
    QPushButton[role="primary"] {{
        background-color: {c.get("primary", c["accent"])};
        border: 1px solid {c.get("primary", c["accent"])};
        color: #ffffff;
        font-weight: bold;
    }}
    QPushButton[role="primary"]:hover {{
        background-color: {c.get("primary_hover", c["accent_hover"])};
    }}
    QCheckBox, QRadioButton {{
        color: {c["text"]};
        background-color: transparent;
        spacing: 6px;
    }}
    /* Cases à cocher toujours visibles (sinon invisibles sur fond sombre : Ponts, Kerf, Actif…) :
       cadre contrasté ; cochée = remplie de la couleur d'accent. */
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {c["muted"]};
        border-radius: 3px;
        background-color: {c["input_bg"]};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {c["accent_hover"]};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c["accent_hover"]};
        border: 1px solid {c["accent_hover"]};
    }}
    QCheckBox::indicator:disabled {{
        border: 1px solid {c["border"]};
        background-color: {c["alt"]};
    }}
    QCheckBox::indicator:checked:disabled {{
        background-color: {c["disabled"]};
        border: 1px solid {c["disabled"]};
    }}
    QAbstractSpinBox {{
        background-color: {c["input_bg"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 3px;
        padding: 2px 18px 2px 4px;
        min-height: 18px;
    }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
        background-color: {c["button"]};
        border-left: 1px solid {c["border"]};
        width: 16px;
        subcontrol-origin: border;
    }}
    QAbstractSpinBox::up-button {{
        subcontrol-position: top right;
        border-top-right-radius: 2px;
    }}
    QAbstractSpinBox::down-button {{
        subcontrol-position: bottom right;
        border-bottom-right-radius: 2px;
    }}
    QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
        background-color: {c["button_hover"]};
    }}
    QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed {{
        background-color: {c["accent"]};
    }}
    /* Flèches : chevrons dessinés (les triangles en bordures s'affichaient en carrés blancs) */
    QAbstractSpinBox::up-arrow {{
        image: url({_chevron("up", c["text"])});
        width: 10px;
        height: 8px;
    }}
    QAbstractSpinBox::down-arrow {{
        image: url({_chevron("down", c["text"])});
        width: 10px;
        height: 8px;
    }}
    QAbstractSpinBox::up-arrow:disabled {{
        image: url({_chevron("up", c["disabled"])});
    }}
    QAbstractSpinBox::down-arrow:disabled {{
        image: url({_chevron("down", c["disabled"])});
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c["border"]};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c["accent"]};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QProgressBar {{
        background-color: {c["alt"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        border-radius: 3px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {c["accent"]};
        border-radius: 2px;
    }}
    QScrollBar:vertical {{
        background: {c["window"]};
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c["scroll"]};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c["border"]};
    }}
    QScrollBar:horizontal {{
        background: {c["window"]};
        height: 12px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c["scroll"]};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
    }}
    QSplitter::handle {{
        background-color: {c["border"]};
    }}
    QToolTip {{
        background-color: {c["tooltip_bg"]};
        color: {c["tooltip_fg"]};
        border: 1px solid {c["border"]};
        padding: 4px;
    }}
    QDockWidget {{
        color: {c["text"]};
    }}
    QDockWidget::title {{
        background-color: {c["alt"]};
        color: {c["text"]};
        padding: 4px;
    }}
"""


def _modern_stylesheet(c: dict) -> str:
    """Complément des thèmes « modern » (New Dusk), appliqué après la feuille commune : à plat (peu de
    bordures, séparations par les fonds), coins arrondis, onglets soulignés de l'accent comme dans VS Code,
    champs et boutons plus aérés, barres de défilement fines, menus et bulles arrondis."""
    return f"""
    QMenuBar {{
        border-bottom: none;
        padding: 2px 4px;
    }}
    QMenuBar::item {{
        padding: 5px 10px;
        border-radius: 5px;
    }}
    QMenu {{
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 28px 6px 12px;
        border-radius: 5px;
    }}
    QToolBar {{
        border-bottom: none;
        padding: 4px;
        spacing: 6px;
    }}
    QToolBar QToolButton {{
        border: none;
        border-radius: 6px;
        padding: 5px;
    }}
    QToolBar QToolButton:hover {{
        border: none;
    }}
    QStatusBar {{
        background-color: {c["toolbar_bg"]};
        border-top: none;
        color: {c["muted"]};
    }}
    /* Onglets à la manière de VS Code : bande d'onglets, séparateurs fins, onglet actif de la couleur de la
       zone de travail, coins du haut arrondis ; pas de flèches de défilement (molette pour défiler). */
    QTabWidget::pane {{
        border: none;
        background-color: {c["tab_selected"]};
    }}
    QTabWidget::tab-bar {{
        left: 0px;
    }}
    QTabBar {{
        background-color: {c["tab_bg"]};
        qproperty-drawBase: 0;
        qproperty-usesScrollButtons: 0;
    }}
    QTabBar::tab {{
        background-color: {c["tab_bg"]};
        color: {c["muted"]};
        padding: 8px 12px;
        border: none;
        border-right: 1px solid {c.get("tab_separator", c["border"])};
        border-radius: 0px;
        margin: 0px;
    }}
    QTabBar::tab:selected {{
        background-color: {c["tab_selected"]};
        color: {c["text"]};
        border-right: 1px solid transparent;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:hover:!selected {{
        color: {c["text"]};
    }}
    QTabBar:focus {{
        outline: none;
    }}
    QTabBar::scroller {{
        width: 0px;
    }}
    QTabBar::close-button {{
        image: url({_cross(c["muted"])});
        subcontrol-position: right;
        margin-left: 2px;
        margin-right: 6px;
        border-radius: 4px;
    }}
    QTabBar::close-button:hover {{
        image: url({_cross(c["text"])});
        background-color: {c["button_hover"]};
    }}
    /* Panneaux latéraux (propriétés, listes de catégories) : plus sombres que la zone de travail, à plat. */
    QWidget[role="sidebar"] {{
        background-color: {c.get("sidebar", c["base"])};
    }}
    /* Panneau du bas (graveur) : cadres à plat et serrés, comme le terminal de VS Code. */
    QWidget[role="bottom_panel"] QGroupBox {{
        border: none;
        border-right: 1px solid {c.get("panel_border", c["border"])};
        border-radius: 0px;
        margin-top: 10px;
        padding: 12px 6px 4px 6px;
    }}
    QWidget[role="bottom_panel"] QGroupBox::title {{
        left: 6px;
    }}
    QListWidget[role="sidebar"] {{
        border: none;
        border-right: 1px solid {c.get("panel_border", c["border"])};
        border-radius: 0px;
    }}
    QGroupBox {{
        border: 1px solid {c["border"]};
        border-radius: 8px;
        margin-top: 14px;
        padding: 16px 8px 8px 8px;
    }}
    QGroupBox::title {{
        left: 10px;
        padding: 0 6px;
        color: {c["muted"]};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox {{
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 20px;
    }}
    QAbstractSpinBox {{
        padding-right: 20px;
    }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
        background-color: transparent;
        border: none;
        width: 18px;
    }}
    QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
        background-color: {c["button_hover"]};
    }}
    QAbstractSpinBox::up-button {{
        border-top-right-radius: 5px;
    }}
    QAbstractSpinBox::down-button {{
        border-bottom-right-radius: 5px;
    }}
    QLineEdit:hover, QComboBox:hover, QAbstractSpinBox:hover {{
        border: 1px solid {c["scroll"]};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {{
        border: 1px solid {c["accent_hover"]};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        border-radius: 6px;
        padding: 4px;
    }}
    QListView, QTreeView, QTableView {{
        border: 1px solid {c["border"]};
        border-radius: 6px;
        background-color: {c["base"]};
        alternate-background-color: {c["group_bg"]};
    }}
    QAbstractItemView::item:hover {{
        background-color: {c["alt"]};
    }}
    QAbstractItemView::item:selected {{
        background-color: {c["menu_sel"]};
        color: {c["text"]};
    }}
    QHeaderView::section {{
        background-color: {c["base"]};
        color: {c["muted"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        padding: 6px 8px;
        font-weight: 600;
    }}
    QPushButton {{
        background-color: {c["button"]};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background-color: {c["button_hover"]};
        border: 1px solid transparent;
    }}
    QPushButton:default, QPushButton[role="primary"] {{
        background-color: {c["primary"]};
        color: #ffffff;
    }}
    QPushButton:default:hover, QPushButton[role="primary"]:hover {{
        background-color: {c["primary_hover"]};
    }}
    QPushButton:pressed, QPushButton:checked {{
        background-color: {c["accent"]};
        border: 1px solid transparent;
        color: {c["on_accent"]};
    }}
    QPushButton:focus {{
        border: 1px solid {c["accent_hover"]};
    }}
    QPushButton:disabled {{
        background-color: {c["alt"]};
        border: 1px solid transparent;
    }}
    /* Cases à cocher en interrupteurs (marche / arrêt), dessinés en SVG : voir _switch */
    QCheckBox::indicator {{
        width: 30px;
        height: 16px;
        border: none;
        background: transparent;
        image: url({_switch(False, c["scroll"], c["text"])});
    }}
    QCheckBox::indicator:hover {{
        border: none;
        image: url({_switch(False, c["muted"], c["text"])});
    }}
    QCheckBox::indicator:checked {{
        border: none;
        background: transparent;
        image: url({_switch(True, c["accent"], "#ffffff")});
    }}
    QCheckBox::indicator:checked:hover {{
        image: url({_switch(True, c["accent_hover"], "#ffffff")});
    }}
    QCheckBox::indicator:disabled {{
        border: none;
        background: transparent;
        image: url({_switch(False, c["alt"], c["disabled"])});
    }}
    QCheckBox::indicator:checked:disabled {{
        border: none;
        background: transparent;
        image: url({_switch(True, c["disabled"], c["alt"])});
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {c["muted"]};
        border-radius: 8px;
        background-color: {c["input_bg"]};
    }}
    QRadioButton::indicator:checked {{
        border: 4px solid {c["accent_hover"]};
        background-color: {c["text"]};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {c["alt"]};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {c["accent"]};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c["text"]};
        border: 3px solid {c["accent_hover"]};
        width: 10px;
        height: 10px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    /* Barre d'avancement : fine, mais assez haute pour son texte (« Gravure : 42 % »). */
    QProgressBar {{
        border: none;
        border-radius: 6px;
        background-color: {c["alt"]};
        color: {c["text"]};
        min-height: 18px;
        max-height: 20px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        border-radius: 6px;
        background-color: {c["accent"]};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {c["scroll"]};
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background: {c["muted"]};
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}
    QSplitter::handle {{
        background-color: {c["base"]};
    }}
    QSplitter::handle:hover {{
        background-color: {c["accent"]};
    }}
    QToolTip {{
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 8px;
    }}
"""


def normalize_theme_name(theme_name) -> str:
    """Normalise la valeur lue dans QSettings / le menu vers un code THEMES.

    Sous Windows, QSettings peut renvoyer des types ou libellés inattendus ;
    on accepte aussi les alias FR/EN.
    """
    if theme_name is None:
        return "dark"
    name = str(theme_name).strip().lower()
    aliases = {
        "sombre": "dark",
        "dark": "dark",
        "clair": "light",
        "light": "light",
        "dusk": "dusk",
        "new_dusk": "new_dusk",
        "new-dusk": "new_dusk",
        "new dusk": "new_dusk",
        "new_dawn": "new_dawn",
        "new-dawn": "new_dawn",
        "new dawn": "new_dawn",
        "warm": "warm",
        "warm dim": "warm",
        "warm_dim": "warm",
        "neon": "neon",
        "laser": "neon",
        "retro80": "retro80",
        "retro": "retro80",
        "synthwave": "retro80",
        "80s": "retro80",
        "jarvis": "jarvis",
        "hud": "jarvis",
        "ironman": "jarvis",
    }
    name = aliases.get(name, name)
    if name not in THEMES:
        return "dark"
    return name


# Police des thèmes modernes : la première installée (Inter est sous Linux le plus souvent, Segoe UI sous Windows).
MODERN_FONTS = ("Inter", "Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Cantarell", "Noto Sans")
_system_font = None


def _apply_font(app, modern):
    """Police des thèmes modernes, ou celle du système (retrouvée en revenant à un autre thème)."""
    global _system_font
    if _system_font is None:
        _system_font = QFont(app.font())
    font = QFont(_system_font)
    if modern:
        installed = set(QFontDatabase.families())
        family = next((name for name in MODERN_FONTS if name in installed), None)
        if family:
            font.setFamily(family)
    app.setFont(font)


def apply_app_theme(app: QApplication, theme_name: str):
    """Applique un thème nommé à toute l'application."""
    app.setStyle("Fusion")
    name = normalize_theme_name(theme_name)
    colors = THEMES[name]
    # Réinitialise d'abord pour éviter qu'un ancien stylesheet « clair »
    # reste partiellement actif après redémarrage.
    app.setStyleSheet("")
    app.setPalette(_build_palette(colors))
    style = _build_stylesheet(colors)
    if colors.get("modern"):
        style += _modern_stylesheet(colors)
    app.setStyleSheet(style)
    _apply_font(app, colors.get("modern"))
    # Icônes : pack Jarvis (cyan) uniquement pour ce thème ; sinon Breeze.
    apply_icon_theme_for_ui(name)
    return name


def available_themes():
    """Liste ordonnée (code, clé i18n) des thèmes proposés dans le menu."""
    order = ("dark", "light", "dusk", "new_dusk", "new_dawn", "warm", "neon", "retro80", "jarvis")
    return [(code, THEMES[code]["label_key"]) for code in order]


def current_theme_name():
    """Code du thème choisi (réglage app_theme), normalisé."""
    return normalize_theme_name(ui_preferences().get("app_theme", "dark"))


def apply_saved_theme(app: QApplication):
    """Applique le thème enregistré dans les préférences (« dark » par défaut).

    La valeur est normalisée puis réécrite proprement, pour remplacer les
    anciens libellés ou les types inattendus renvoyés sous Windows.
    """
    name = current_theme_name()
    ui_preferences().set("app_theme", name)
    return apply_app_theme(app, name)


def _ensure_icon_search_path():
    """Ajoute resources/icons aux chemins de thèmes d'icônes Qt (une seule fois)."""
    for base in map(Path, resource_candidates("icons")):
        if (base / "breeze" / "index.theme").is_file() or (base / "jarvis" / "index.theme").is_file():
            paths = [str(base)] + [p for p in QIcon.themeSearchPaths() if p != str(base)]
            QIcon.setThemeSearchPaths(paths)
            return True
    return False


def apply_icon_theme_for_ui(theme_name: str) -> bool:
    """Choisit le pack d'icônes selon le thème UI.

    - jarvis → pack « jarvis » (icônes cyan HUD), s'il est présent ;
    - sinon → « breeze » (pack par défaut).

    Ne force rien si un vrai thème desktop (hors hicolor/breeze/jarvis) est
    déjà actif : on laisse le choix de l'utilisateur Linux.
    """
    name = normalize_theme_name(theme_name)
    if THEMES[name].get("mono_icons"):
        # Choisi exprès pour ses icônes d'une seule couleur : remplace aussi un thème d'icônes du bureau.
        mono = _mono_icon_theme(THEMES[name]["text"])
        if mono:
            root, mono_name = mono
            QIcon.setThemeSearchPaths([root] + [p for p in QIcon.themeSearchPaths() if p != root])
            QIcon.setThemeName(mono_name)
            return True
    wanted = "jarvis" if name == "jarvis" else "breeze"
    current = QIcon.themeName() or ""
    # Thème système utilisateur : ne pas l'écraser, sauf pour basculer
    # entre nos packs embarqués breeze ↔ jarvis.
    if current and current not in ("", "hicolor", "breeze", "jarvis") and not current.startswith("mono-"):
        return False
    if not _ensure_icon_search_path():
        return False
    for base in map(Path, resource_candidates("icons")):
        if (base / wanted / "index.theme").is_file():
            QIcon.setThemeName(wanted)
            return True
    # Repli : Breeze si jarvis absent
    if wanted == "jarvis":
        for base in map(Path, resource_candidates("icons")):
            if (base / "breeze" / "index.theme").is_file():
                QIcon.setThemeName("breeze")
                return True
    return False


def install_breeze_icon_theme():
    """Active le thème d'icônes embarqué au démarrage (Breeze, ou Jarvis si
    le thème UI enregistré est jarvis).

    Sous Linux, si un thème système est déjà configuré, on ne l'écrase pas.
    Le pack vit dans resources/icons/<breeze|jarvis>/, cherché comme les
    images de l'application (voir core.paths.resource_candidates).
    """
    return apply_icon_theme_for_ui(current_theme_name())
