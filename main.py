"""Point d'entrée de Laser Studio Pro."""
import sys
import sys
if "--stencil-studio" in sys.argv:
    from stencil_studio.studio_window import main as _stencil_main
    sys.exit(_stencil_main())

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


from app_theme import apply_app_theme


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


if __name__ == "__main__":
    install_qt_message_filters()
    setup_debug_logging()
    app = QApplication(sys.argv)
    install_breeze_icon_theme()

    # Charger le thème mémorisé (par défaut "dark") et l'appliquer tout de suite
    from app_theme import normalize_theme_name
    settings = QSettings("LaserStudioPro", "UIConfig")
    current_theme = normalize_theme_name(settings.value("app_theme", "dark"))
    # Réécrit une valeur propre (évite les anciens libellés / types Windows)
    settings.setValue("app_theme", current_theme)
    apply_app_theme(app, current_theme)

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

        # Réapplique le thème après construction de l'UI : certains widgets
        # (surtout sous Windows) naissent avec la palette système claire et
        # ignoraient le stylesheet posé trop tôt.
        saved = normalize_theme_name(
            QSettings("LaserStudioPro", "UIConfig").value("app_theme", "dark")
        )
        apply_app_theme(app, saved)

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
