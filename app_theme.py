"""Thèmes clair / sombre de Laser Studio Pro (palette + feuille de style globale)."""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor


# Feuille de style thème clair (inspiré Windows 11 / Fluent, fond vraiment clair).
_LIGHT_STYLESHEET = """
    * {
        color: #1a1a1a;
    }
    QMainWindow, QDialog, QWidget {
        background-color: #f3f3f3;
        color: #1a1a1a;
    }
    QMenuBar {
        background-color: #ffffff;
        color: #1a1a1a;
        border-bottom: 1px solid #e5e5e5;
        spacing: 2px;
    }
    QMenuBar::item {
        background: transparent;
        color: #1a1a1a;
        padding: 4px 10px;
    }
    QMenuBar::item:selected, QMenuBar::item:pressed {
        background-color: #e8e8e8;
        color: #1a1a1a;
    }
    QMenu {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        padding: 4px;
    }
    QMenu::item {
        color: #1a1a1a;
        padding: 6px 28px 6px 12px;
        background-color: transparent;
    }
    QMenu::item:selected {
        background-color: #e5f1fb;
        color: #1a1a1a;
    }
    QMenu::separator {
        height: 1px;
        background: #e5e5e5;
        margin: 4px 8px;
    }
    QToolBar {
        background-color: #f9f9f9;
        color: #1a1a1a;
        border: none;
        border-bottom: 1px solid #e5e5e5;
        spacing: 4px;
        padding: 2px;
    }
    QToolBar QToolButton {
        background-color: transparent;
        color: #1a1a1a;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px;
    }
    QToolBar QToolButton:hover {
        background-color: #e8e8e8;
        border: 1px solid #d0d0d0;
    }
    QToolBar QToolButton:pressed, QToolBar QToolButton:checked {
        background-color: #d0e8f7;
        border: 1px solid #0078d4;
    }
    QStatusBar {
        background-color: #f3f3f3;
        color: #1a1a1a;
        border-top: 1px solid #e5e5e5;
    }
    QTabWidget::pane {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        top: -1px;
    }
    QTabBar::tab {
        background-color: #ebebeb;
        color: #1a1a1a;
        padding: 7px 16px;
        border: 1px solid #d0d0d0;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #ffffff;
        color: #1a1a1a;
        font-weight: 600;
    }
    QTabBar::tab:hover:!selected {
        background-color: #f5f5f5;
    }
    QGroupBox {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 14px;
        font-weight: 600;
        color: #1a1a1a;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
        color: #333333;
        background-color: #ffffff;
    }
    QLabel {
        background-color: transparent;
        color: #1a1a1a;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QListView, QTreeView, QTableView, QAbstractItemView {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #adadad;
        border-radius: 3px;
        padding: 3px 6px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
        border: 1px solid #0078d4;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        selection-background-color: #e5f1fb;
        selection-color: #1a1a1a;
    }
    QHeaderView::section {
        background-color: #f0f0f0;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        padding: 4px 8px;
    }
    QPushButton {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #adadad;
        border-radius: 4px;
        /* Padding modéré : les boutons « − » / « + » font 30 px de large ;
           un padding horizontal de 14 px les vidait complètement. */
        padding: 4px 8px;
        min-width: 1.2em;
    }
    QPushButton:hover {
        background-color: #e5f1fb;
        border: 1px solid #0078d4;
        color: #1a1a1a;
    }
    QPushButton:pressed {
        background-color: #cce4f7;
        color: #1a1a1a;
    }
    QPushButton:disabled {
        background-color: #f0f0f0;
        color: #a0a0a0;
        border: 1px solid #d0d0d0;
    }
    /* Cases / radios : on ne redessine PAS l'indicateur (sinon la coche disparaît).
       Seules les couleurs de texte restent forcées. */
    QCheckBox, QRadioButton {
        color: #1a1a1a;
        background-color: transparent;
        spacing: 6px;
    }
    /* Flèches des spinbox (Largeur / Hauteur…) visibles sur fond clair */
    QAbstractSpinBox {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #adadad;
        border-radius: 3px;
        padding: 2px 4px;
    }
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
        background-color: #f0f0f0;
        border-left: 1px solid #d0d0d0;
        width: 16px;
    }
    QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {
        background-color: #e5f1fb;
    }
    QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
        width: 8px;
        height: 8px;
    }
    QSlider::groove:horizontal {
        height: 4px;
        background: #d0d0d0;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #0078d4;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
    QProgressBar {
        background-color: #e5e5e5;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        border-radius: 3px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #0078d4;
        border-radius: 2px;
    }
    QScrollBar:vertical {
        background: #f3f3f3;
        width: 12px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        border-radius: 4px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    QScrollBar:horizontal {
        background: #f3f3f3;
        height: 12px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        border-radius: 4px;
        min-width: 24px;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        width: 0;
        height: 0;
    }
    QSplitter::handle {
        background-color: #e5e5e5;
    }
    QToolTip {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        padding: 4px;
    }
    QDockWidget {
        color: #1a1a1a;
        titlebar-close-icon: none;
    }
    QDockWidget::title {
        background-color: #f0f0f0;
        color: #1a1a1a;
        padding: 4px;
    }
"""


# Feuille de style thème sombre : force les boutons / groupbox (sinon Fusion
# sous Windows les laisse clairs après un passage par le thème clair).
_DARK_STYLESHEET = """
    QPushButton {
        background-color: #3a3a3a;
        color: #e0e0e0;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px 8px;
        min-width: 1.2em;
    }
    QPushButton:hover {
        background-color: #4a4a4a;
        border: 1px solid #6a9fdb;
        color: #ffffff;
    }
    QPushButton:pressed {
        background-color: #2b5c8f;
        color: #ffffff;
    }
    QPushButton:disabled {
        background-color: #2a2a2a;
        color: #777777;
        border: 1px solid #3a3a3a;
    }
    QPushButton:checked {
        background-color: #2b5c8f;
        border: 1px solid #4a8ad4;
        color: #ffffff;
    }
    QGroupBox {
        background-color: #2a2a2a;
        border: 1px solid #444444;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 14px;
        font-weight: 600;
        color: #e0e0e0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
        color: #cccccc;
        background-color: #2a2a2a;
    }
    QToolBar QToolButton {
        background-color: transparent;
        color: #e0e0e0;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px;
    }
    QToolBar QToolButton:hover {
        background-color: #3a3a3a;
        border: 1px solid #555555;
    }
    QToolBar QToolButton:pressed, QToolBar QToolButton:checked {
        background-color: #2b5c8f;
        border: 1px solid #4a8ad4;
    }
"""


def apply_app_theme(app: QApplication, theme_name: str):
    """Applique le thème sombre ou clair à toute l'application (palette + feuille de style)."""
    app.setStyle("Fusion")
    if theme_name == "dark":
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(18, 18, 18))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(90, 169, 255))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(43, 92, 143))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(140, 140, 140))
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
        app.setPalette(dark_palette)
        # Stylesheet sombre pour les boutons (alignement vectoriel, etc.) :
        # la seule palette ne suffit pas sous Windows après un thème clair.
        app.setStyleSheet(_DARK_STYLESHEET)
    else:
        # Thème clair Windows : palette complète + stylesheet pour forcer les zones
        # qui restent sombres sous Fusion (surtout barres d'outils / onglets).
        light_palette = QPalette()
        light_palette.setColor(QPalette.ColorRole.Window, QColor(243, 243, 243))
        light_palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 212))
        light_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
        light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(140, 140, 140))
        light_palette.setColor(QPalette.ColorRole.Light, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.Midlight, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ColorRole.Mid, QColor(200, 200, 200))
        light_palette.setColor(QPalette.ColorRole.Dark, QColor(160, 160, 160))
        light_palette.setColor(QPalette.ColorRole.Shadow, QColor(100, 100, 100))
        light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(160, 160, 160))
        light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(160, 160, 160))
        light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(160, 160, 160))
        light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, QColor(245, 245, 245))
        app.setPalette(light_palette)
        app.setStyleSheet(_LIGHT_STYLESHEET)

