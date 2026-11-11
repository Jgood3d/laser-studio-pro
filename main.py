"""Point d'entrée de Laser Studio Pro."""
import sys
import sys
if "--stencil-studio" in sys.argv:
    from stencil_studio.studio_window import main as _stencil_main
    sys.exit(_stencil_main())

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QElapsedTimer, QTimer
from PyQt6 import QtWebEngineWidgets

from core.constants import SPLASH_SCREEN_DURATION
from core.debug_log import setup_debug_logging
from core.paths import find_resource
from i18n import tr
from ui.app.qt_messages import install_qt_message_filters
from ui.splashscreen import StartupSplash
from ui.app.theme import apply_saved_theme, install_breeze_icon_theme


if __name__ == "__main__":
    # Chronomètre du démarrage : la fenêtre principale ne s'ouvre pas avant
    # SPLASH_SCREEN_DURATION secondes, pour laisser le splash visible.
    startup_timer = QElapsedTimer()
    startup_timer.start()

    install_qt_message_filters()
    setup_debug_logging()
    app = QApplication(sys.argv)

    # 1. Afficher l'écran de démarrage le plus tôt possible (il charge
    # lui-même la bannière)
    splash = StartupSplash()
    splash.show_and_wait()

    # Icônes et thème : après le splash, qui n'en a pas besoin, mais avant
    # la fenêtre principale, qui les utilise dès sa construction.
    install_breeze_icon_theme()
    apply_saved_theme(app)

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

    # 2. Charger la fenêtre principale avec gestion des erreurs
    try:
        window = FullLaserStudio()
        if icon_path:
            window.setWindowIcon(QIcon(icon_path))

        # Réapplique le thème après construction de l'UI : certains widgets
        # (surtout sous Windows) naissent avec la palette système claire et
        # ignoraient le stylesheet posé trop tôt.
        apply_saved_theme(app)

        splash.show_progress(tr("splash.ready"))

        # La fenêtre principale remplace le splash une fois écoulées
        # SPLASH_SCREEN_DURATION secondes depuis le début du démarrage.
        # L'attente passe par un QTimer : l'application continue de tourner
        # et le splash d'être affiché pendant ce temps.
        def show_main_window():
            window.showMaximized()
            splash.finish(window)

        remaining_ms = round(SPLASH_SCREEN_DURATION * 1000) - startup_timer.elapsed()
        QTimer.singleShot(max(0, remaining_ms), show_main_window)

    except Exception as e:
        splash.finish(None)
        print(f"Erreur critique au lancement : {e}")
        sys.exit(1)

    sys.exit(app.exec())
