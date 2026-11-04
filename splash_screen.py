"""Écran de démarrage de Laser Studio Pro."""
import time

from PyQt6.QtWidgets import QApplication, QSplashScreen, QWidget
from PyQt6.QtCore import Qt, QEvent, QTimer


class StartupSplash(QSplashScreen):
    """Écran de démarrage : réellement affiché avant de poursuivre le
    chargement (Wayland), messages d'avancement, et fenêtre principale
    montrée après une durée minimale."""

    def __init__(self, pixmap, min_duration_s=0.0):
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.min_duration_s = min_duration_s
        self._shown_at = None

    def event(self, event):
        # À l'événement Show, QSplashScreen attend que la fenêtre soit
        # exposée (1 s au plus), mais avant que show() l'ait remise au
        # compositeur : sous Wayland, l'attente échoue donc toujours et
        # show() bloque 1 s pour rien. Elle est remplacée par celle de
        # show_now().
        if event.type() == QEvent.Type.Show:
            return QWidget.event(self, event)
        return super().event(event)

    def show_now(self, timeout_s=1.0):
        """Affiche le splash et attend qu'il soit réellement à l'écran
        (timeout_s au plus).

        Sous Wayland, la fenêtre n'apparaît qu'après quelques échanges avec
        le compositeur : un seul processEvents() ne suffit pas, et la
        construction de la fenêtre principale bloque ensuite la boucle
        d'événements jusqu'à la fermeture du splash, qui ne serait jamais
        vu."""
        self.show()
        self._shown_at = time.monotonic()
        deadline = self._shown_at + timeout_s
        while (not self.windowHandle().isExposed()
               and time.monotonic() < deadline):
            QApplication.processEvents()
            time.sleep(0.005)
        QApplication.processEvents()

    def set_status(self, message):
        """Message d'avancement en bas du splash."""
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white
        )
        QApplication.processEvents()

    def remaining_s(self):
        """Temps restant avant la fin de la durée minimale d'affichage
        (0 si elle est écoulée)."""
        if self._shown_at is None:
            return 0.0
        elapsed_s = time.monotonic() - self._shown_at
        return max(0.0, self.min_duration_s - elapsed_s)

    def finish_with(self, window):
        """Montre `window` maximisée et ferme le splash, une fois la durée
        minimale écoulée.

        Le délai passe par un QTimer et non une pause : la boucle
        d'événements continue de tourner et le splash d'être redessiné."""
        def show_window():
            window.showMaximized()
            self.finish(window)

        QTimer.singleShot(int(self.remaining_s() * 1000), show_window)
