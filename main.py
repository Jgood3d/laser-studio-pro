"""Point d'entrée de Laser Studio Pro."""
import sys

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QLoggingCategory, qInstallMessageHandler

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


if __name__ == "__main__":
    qInstallMessageHandler(qt_message_handler)
    # Sous Wayland, Qt affiche « qt.qpa.wayland.textinput: … Trying to disable … but 0x0 is focused »
    # quand le focus clavier change à la fermeture d'une fenêtre : avertissement interne à Qt, sans
    # conséquence. On masque cette seule catégorie (QT_LOGGING_RULES permet de la réactiver).
    QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput=false")
    setup_debug_logging()
    app = QApplication(sys.argv)

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
            # Redimensionne à 600px de large en conservant les proportions
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
        
        # Afficher la fenêtre maximisée et fermer le splash screen proprement
        window.showMaximized()
        splash.finish(window)
        
    except Exception as e:
        splash.finish(None)
        print(f"Erreur critique au lancement : {e}")
        sys.exit(1)

    sys.exit(app.exec())