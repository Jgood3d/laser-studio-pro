"""Point d'entrée de Laser Studio Pro."""
import sys

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt6.QtCore import Qt, QSettings, QLoggingCategory, qInstallMessageHandler

from app_utils import find_resource
from debug_log import setup_debug_logging
from main_window import FullLaserStudio

# Avertissements de Qt sans conséquence, écartés de la console (voir qt_message_handler).
IGNORED_QT_MESSAGES = (
    # Sous Wayland, seule une fenêtre popup (menu, liste déroulante) peut capturer la souris. Quand un
    # widget de Qt le demande pour une fenêtre normale, Qt ignore la demande et écrit ce message.
    "This plugin supports grabbing the mouse only for popup windows",
)


def qt_message_handler(mode, context, message):
    """Affiche les messages de Qt comme d'habitude, sauf ceux de IGNORED_QT_MESSAGES."""
    if any(ignored in message for ignored in IGNORED_QT_MESSAGES):
        return
    category = context.category
    prefix = f"{category}: " if category and category != "default" else ""
    sys.stderr.write(f"{prefix}{message}\n")


def apply_app_theme(app: QApplication, theme_name: str):
    """Applique le thème sombre ou clair à l'application."""
    app.setStyle("Fusion")
    if theme_name == "dark":
        app.setStyleSheet("")  # Réinitialise les styles globaux pour le mode sombre
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(18, 18, 18))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(90, 169, 255))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(43, 92, 143))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(dark_palette)
    else:
        # Feuille de style globale renforcée pour forcer le fond blanc/clair sur la fenêtre et les widgets sous Windows
        app.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f2f2f2;
                color: #1a1a1a;
            }
            QMenuBar, QMenu, QToolBar {
                background-color: #e6e6e6;
                color: #1a1a1a;
                border: none;
            }
            QMenuBar::item:selected, QMenu::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                color: #1a1a1a;
                padding: 6px 14px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #1a1a1a;
                font-weight: bold;
            }
            QGroupBox {
                background-color: #f9f9f9;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #333333;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QListView {
                background-color: #ffffff;
                color: #1a1a1a;
                border: 1px solid #adadad;
                border-radius: 2px;
                padding: 2px;
            }
            QPushButton {
                background-color: #e1e1e1;
                color: #1a1a1a;
                border: 1px solid #adadad;
                border-radius: 3px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #e5f1fb;
                border: 1px solid #0078d7;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
            }
        """)
        light_palette = QPalette()
        light_palette.setColor(QPalette.ColorRole.Window, QColor(242, 242, 242))
        light_palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(235, 235, 235))
        light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.Button, QColor(225, 225, 225))
        light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 26))
        light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
        light_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(light_palette)


if __name__ == "__main__":
    qInstallMessageHandler(qt_message_handler)
    QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput=false")
    setup_debug_logging()
    app = QApplication(sys.argv)

    # Charger le thème mémorisé (par défaut "dark")
    settings = QSettings("LaserStudioPro", "UIConfig")
    current_theme = settings.value("app_theme", "dark")
    apply_app_theme(app, current_theme)

    icon_path = (
        find_resource("laser_studio_pro.ico")
        or find_resource("laser_studio_pro_256.png")
        or find_resource("laser_studio_pro_512.png")
    )
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    # 1. Charger et redimensionner l'image pour éviter qu'elle ne prenne tout l'écran
    banner_path = find_resource("laser_studio_pro_banner.png")
    if banner_path:
        pixmap = QPixmap(banner_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation)
    else:
        pixmap = QPixmap(500, 250)
        pixmap.fill(Qt.GlobalColor.darkGray)

    # 2. Afficher l'écran de démarrage
    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    def update_splash_status(message):
        splash.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white
        )
        app.processEvents()

    update_splash_status("Initialisation de Laser Studio Pro...")

    # 3. Charger la fenêtre principale avec gestion des erreurs
    try:
        window = FullLaserStudio()
        if icon_path:
            window.setWindowIcon(QIcon(icon_path))

        update_splash_status("Prêt !")
        
        window.showMaximized()
        splash.finish(window)
        
    except Exception as e:
        splash.finish(None)
        print(f"Erreur critique au lancement : {e}")
        sys.exit(1)

    sys.exit(app.exec())