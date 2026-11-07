"""Thèmes clair / sombre / Dusk / Warm dim de Laser Studio Pro (palette + feuille de style)."""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor


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
}


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
        border-radius: : 3px;
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
    QCheckBox, QRadioButton {{
        color: {c["text"]};
        background-color: transparent;
        spacing: 6px;
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
    /* Flèches visibles sur tous les thèmes (Fusion/Windows les masque souvent) */
    QAbstractSpinBox::up-arrow {{
        width: 0;
        height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {c["text"]};
        background: transparent;
        margin: 1px;
    }}
    QAbstractSpinBox::down-arrow {{
        width: 0;
        height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c["text"]};
        background: transparent;
        margin: 1px;
    }}
    QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::down-arrow:disabled {{
        border-bottom-color: {c["disabled"]};
        border-top-color: {c["disabled"]};
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
        "warm": "warm",
        "warm dim": "warm",
        "warm_dim": "warm",
    }
    name = aliases.get(name, name)
    if name not in THEMES:
        return "dark"
    return name


def apply_app_theme(app: QApplication, theme_name: str):
    """Applique un thème nommé (`dark`, `light`, `dusk`, `warm`) à toute l'application."""
    app.setStyle("Fusion")
    name = normalize_theme_name(theme_name)
    colors = THEMES[name]
    # Réinitialise d'abord pour éviter qu'un ancien stylesheet « clair »
    # reste partiellement actif après redémarrage.
    app.setStyleSheet("")
    app.setPalette(_build_palette(colors))
    app.setStyleSheet(_build_stylesheet(colors))
    return name


def available_themes():
    """Liste ordonnée (code, clé i18n) des thèmes proposés dans le menu."""
    order = ("dark", "light", "dusk", "warm")
    return [(code, THEMES[code]["label_key"]) for code in order]
