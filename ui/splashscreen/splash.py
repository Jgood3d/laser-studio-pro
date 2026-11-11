"""Écran de démarrage de Laser Studio Pro."""

import time

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen, QWidget

from core.constants import (
    BANNER_FILENAME,
    SPLASH_SCREEN_SLEEP_INTERVAL,
    SPLASH_SCREEN_WIDTH,
)
from core.paths import find_resource
from i18n import tr
from ui.utils import scaled_to_width_hidpi


class StartupSplash(QSplashScreen):
    """Écran de démarrage : bannière et message d'avancement.

    Par défaut, il affiche la bannière de l'application et le message
    « Initialisation de Laser Studio Pro... ». La durée d'affichage est
    gérée par main.py. Utilisation :

        splash = StartupSplash()
        splash.show_and_wait()
        splash.show_progress("Prêt !")      # facultatif
        splash.finish(window)               # fermé à l'ouverture de window
    """

    def __init__(self, pixmap=None):
        if pixmap is None:
            pixmap = self.banner()
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.show_progress(tr("splash.initializing"))

    @staticmethod
    def banner():
        """Bannière de l'application, large de SPLASH_SCREEN_WIDTH pixels.

        Elle reste nette sur un écran haute résolution : l'échelle retenue
        est la plus forte des écrans, le splash pouvant s'ouvrir sur l'un ou
        l'autre. Sans bannière lisible, un rectangle gris la remplace.
        """
        path = find_resource(BANNER_FILENAME)
        pixmap = QPixmap(path) if path else QPixmap()
        if pixmap.isNull():
            pixmap = QPixmap(500, 250)
            pixmap.fill(Qt.GlobalColor.darkGray)
            return pixmap
        ratio = max(
            screen.devicePixelRatio() for screen in QApplication.screens()
        )
        return scaled_to_width_hidpi(pixmap, SPLASH_SCREEN_WIDTH, ratio)

    def event(self, event):
        # Quand il est affiché, QSplashScreen attend jusqu'à 1 s qu'il soit
        # à l'écran. Sous Wayland, cette attente échoue toujours et bloque
        # pour rien : on la saute, show_and_wait() fait la sienne.
        if event.type() == QEvent.Type.Show:
            return QWidget.event(self, event)
        return super().event(event)

    def show_and_wait(self, timeout_s=1.0):
        """Affiche le splash et attend qu'il soit vraiment à l'écran.

        Sous Wayland, la fenêtre n'apparaît qu'après quelques échanges avec
        le compositeur. Sans cette attente, le chargement de la fenêtre
        principale bloquerait l'application avant que le splash soit vu.
        L'attente dure `timeout_s` secondes au plus.
        """
        self.show()
        start = time.monotonic()
        while (
            not self.windowHandle().isExposed()
            and time.monotonic() - start < timeout_s
        ):
            QApplication.processEvents()
            time.sleep(SPLASH_SCREEN_SLEEP_INTERVAL)
        QApplication.processEvents()

    def show_progress(self, message):
        """Affiche un message d'avancement en bas du splash."""
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        QApplication.processEvents()
