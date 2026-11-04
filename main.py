"""Point d'entrée de Laser Studio Pro."""
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

from app_utils import find_resource
from debug_log import setup_debug_logging
from qt_messages import install_qt_message_filters
from splash_screen import StartupSplash
from widgets_extra import scaled_to_width_hidpi

# Durée minimale d'affichage de l'écran de démarrage, en secondes.
SPLASH_MIN_DURATION_S = 2.0

if __name__ == "__main__":
    install_qt_message_filters()
    setup_debug_logging()
    app = QApplication(sys.argv)

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
    icon_path = (
        find_resource("laser_studio_pro.ico")
        or find_resource("laser_studio_pro_256.png")
        or find_resource("laser_studio_pro_512.png")
    )
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    # Importé ici et non en tête de fichier : ce module charge la
    # quasi-totalité de l'application (pyqtgraph, numba, scipy, OpenCV…).
    # C'est l'étape la plus longue du démarrage, pendant laquelle le splash
    # est ainsi déjà affiché.
    from main_window import FullLaserStudio

    # 3. Charger la fenêtre principale avec gestion des erreurs
    try:
        window = FullLaserStudio()
        if icon_path:
            window.setWindowIcon(QIcon(icon_path))

        splash.set_status("Prêt !")

        # Afficher la fenêtre maximisée et fermer le splash screen
        # proprement, une fois l'écran de démarrage resté
        # SPLASH_MIN_DURATION_S à l'écran.
        splash.finish_with(window)

    except Exception as e:
        splash.finish(None)
        print(f"Erreur critique au lancement : {e}")
        sys.exit(1)

    sys.exit(app.exec())
