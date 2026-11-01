"""Point d'entrée de Laser Studio Pro."""
import sys

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

from app_utils import find_resource
from main_window import FullLaserStudio


if __name__ == "__main__":
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