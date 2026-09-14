"""Point d'entrée de Laser Studio Pro."""
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app_utils import find_resource
from main_window import FullLaserStudio


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # .ico est un format Windows ; sous Linux, on utilise plutôt un .png (Qt
    # gère les deux nativement selon l'OS, mais autant fournir le format que
    # chaque système attend). On essaie le .ico puis le .png en repli.
    # find_resource() cherche à la fois à côté de l'exécutable et dans le
    # bundle PyInstaller (si le fichier a été embarqué via --add-data).
    icon_path = (
        find_resource("laser_studio_pro.ico")
        or find_resource("laser_studio_pro_256.png")
        or find_resource("laser_studio_pro_512.png")
    )
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    window = FullLaserStudio()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    window.showMaximized()
    sys.exit(app.exec())
