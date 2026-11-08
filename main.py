"""Point d'entrée de Laser Studio Pro."""
import sys
import sys
if "--stencil-studio" in sys.argv:
    from stencil_studio.studio_window import main as _stencil_main
    sys.exit(_stencil_main())

<<<<<<< HEAD
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt6.QtCore import Qt, QSettings
from PyQt6 import QtWebEngineWidgets

from app_utils import find_resource
from debug_log import setup_debug_logging
from qt_messages import install_qt_message_filters
from ui_splash_screen import StartupSplash
from widgets_extra import scaled_to_width_hidpi

# Durée minimale d'affichage de l'écran de démarrage, en secondes.
SPLASH_MIN_DURATION_S = 2.0


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


def install_breeze_icon_theme():
    """Active le thème d'icônes Breeze embarqué (surtout utile sous Windows/macOS).

    Sous Linux, si un thème système est déjà configuré, on ne l'écrase pas.
    Le pack minimal vit dans icons/breeze/ à côté de main.py (ou dans le bundle
    PyInstaller via --add-data \"icons;icons\").
    """
    from pathlib import Path
    from PyQt6.QtGui import QIcon

    # Ne pas écraser un vrai thème desktop déjà choisi par l'utilisateur.
    current = QIcon.themeName()
    if current and current not in ("", "hicolor"):
        return False

    candidates = []
    here = Path(__file__).resolve().parent
    candidates.append(here / "icons")
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "icons")
        candidates.append(Path(sys.executable).resolve().parent / "icons")

    for base in candidates:
        index = base / "breeze" / "index.theme"
        if index.is_file():
            paths = [str(base)] + [p for p in QIcon.themeSearchPaths() if p != str(base)]
            QIcon.setThemeSearchPaths(paths)
            QIcon.setThemeName("breeze")
            return True
    return False
=======
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt6.QtCore import Qt, QSettings, QLoggingCategory, qInstallMessageHandler

from app_utils import find_resource
from debug_log import setup_debug_logging
from main_window import FullLaserStudio
>>>>>>> aed42af (feat: description de vos modifications)

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
<<<<<<< HEAD
    install_qt_message_filters()
=======
    qInstallMessageHandler(qt_message_handler)
    QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput=false")
>>>>>>> aed42af (feat: description de vos modifications)
    setup_debug_logging()
    app = QApplication(sys.argv)
    install_breeze_icon_theme()

    # Charger le thème mémorisé (par défaut "dark")
    settings = QSettings("LaserStudioPro", "UIConfig")
    current_theme = settings.value("app_theme", "dark")
    apply_app_theme(app, current_theme)

<<<<<<< HEAD
    # 1. Charger et redimensionner l'image pour éviter qu'elle ne prenne
    # tout l'écran
    banner_path = find_resource("laser_studio_pro_banner.png")
    if banner_path:
        pixmap = QPixmap(banner_path)
        if not pixmap.isNull():
            # Redimensionne à 600px de large en conservant les proportions,
            # net sur un écran haute résolution (échelle la plus forte des
            # écrans, le splash pouvant s'ouvrir sur l'un ou l'autre)
            ratio = max(screen.devicePixelRatio() for screen in app.screens())
            pixmap = scaled_to_width_hidpi(pixmap, 600, ratio)
    else:
        pixmap = QPixmap(500, 250)
        pixmap.fill(Qt.GlobalColor.darkGray)

    # 2. Afficher l'écran de démarrage
    splash = StartupSplash(pixmap, SPLASH_MIN_DURATION_S)
    splash.show_now()
    splash.set_status("Initialisation de Laser Studio Pro...")

    # Après l'affichage du splash, pour qu'il apparaisse le plus tôt possible.
=======
>>>>>>> aed42af (feat: description de vos modifications)
    icon_path = (
        find_resource("laser_studio_pro.ico")
        or find_resource("laser_studio_pro_256.png")
        or find_resource("laser_studio_pro_512.png")
    )
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

<<<<<<< HEAD
    # Importé ici et non en tête de fichier : ce module charge la
    # quasi-totalité de l'application (pyqtgraph, numba, scipy, OpenCV…).
    # C'est l'étape la plus longue du démarrage, pendant laquelle le splash
    # est ainsi déjà affiché.
    from main_window import FullLaserStudio
=======
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
>>>>>>> aed42af (feat: description de vos modifications)

    # 3. Charger la fenêtre principale avec gestion des erreurs
    try:
        window = FullLaserStudio()
        if icon_path:
            window.setWindowIcon(QIcon(icon_path))

<<<<<<< HEAD
        splash.set_status("Prêt !")

        # Afficher la fenêtre maximisée et fermer le splash screen
        # proprement, une fois l'écran de démarrage resté
        # SPLASH_MIN_DURATION_S à l'écran.
        splash.finish_with(window)

=======
        update_splash_status("Prêt !")
        
        window.showMaximized()
        splash.finish(window)
        
>>>>>>> aed42af (feat: description de vos modifications)
    except Exception as e:
        splash.finish(None)
        print(f"Erreur critique au lancement : {e}")
        sys.exit(1)

    sys.exit(app.exec())
