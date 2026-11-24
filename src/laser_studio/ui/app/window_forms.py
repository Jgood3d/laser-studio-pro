"""Fenêtres ouvertes par le contrôleur de la fenêtre (controllers/window.py) : à propos, support, café,
aide, historique des gravures, caméra, fenêtres de réglages, comparaison des tramages ; et ce qui touche
Qt directement (thème de l'application, curseur d'attente). Le contrôleur décide quoi ouvrir, cet objet
construit les fenêtres.

    forms = WindowForms(window)
    forms.help("index.md")
    forms.job_history(history, on_export=..., on_clear=...)
"""
from PyQt6.QtWidgets import QApplication

from laser_studio.ui.about import AboutDialog
from laser_studio.ui.app.theme import apply_app_theme
from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeDialog
from laser_studio.ui.help import HelpDialog
from laser_studio.ui.settings.window import SettingsWindow
from laser_studio.ui.support import SupportDialog
from laser_studio.ui.utils import busy_cursor


class WindowForms:
    """Fenêtres de la fenêtre principale `parent`. Aide, historique et réglages ne s'ouvrent qu'une fois :
    une nouvelle demande ramène la fenêtre au premier plan."""

    def __init__(self, parent):
        self.parent = parent
        self._help_dialog = None
        self._history_dialog = None
        self._settings_windows = {}

    # -- fenêtres d'information

    def about(self):
        AboutDialog(self.parent).exec()

    def support(self):
        SupportDialog(self.parent).exec()

    def coffee(self):
        BuyMeACoffeeDialog(self.parent).exec()

    def help(self, page="index.md"):
        """Documentation (une seule fenêtre, réutilisée), ouverte sur `page`."""
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(self.parent)
        self._help_dialog.show_page(page)

    # -- outils

    def job_history(self, history, on_export, on_clear):
        """Historique des gravures (non modale, une seule à la fois) ; ses boutons appellent `on_export()`
        et `on_clear()`."""
        from laser_studio.ui.dialogs.job_history import JobHistoryDialog   # chargée à la première ouverture

        dialog = self._history_dialog
        try:
            if dialog is not None and dialog.isVisible():
                dialog.raise_()
                dialog.activateWindow()
                return
        except RuntimeError:          # fenêtre déjà détruite (fermée)
            pass
        self._history_dialog = JobHistoryDialog(history, self.parent)
        self._history_dialog.export_requested.connect(on_export)
        self._history_dialog.clear_requested.connect(on_clear)
        self._history_dialog.show()

    def camera(self, controller):
        """Caméra (choix de l'appareil, état, actions), sur le contrôleur `controller`."""
        from laser_studio.ui.dialogs.camera import CameraDialog          # OpenCV : chargé à la demande

        CameraDialog(controller, self.parent).exec()

    def dither_comparison(self, thumbnails, on_choose):
        """Vignettes des algorithmes de tramage ; un clic appelle `on_choose(algorithme)`."""
        from laser_studio.ui.dialogs.dither_comparison import DitherComparisonDialog

        dialog = DitherComparisonDialog(self.parent, thumbnails)
        dialog.algorithm_chosen.connect(on_choose)
        dialog.exec()

    def settings_window(self, kind, title, page):
        """Fenêtre de réglages `kind` (créée à la première demande avec `title` et `page`, puis
        réutilisée), ramenée au premier plan."""
        if kind not in self._settings_windows:
            self._settings_windows[kind] = SettingsWindow(self.parent, title, page, kind)
        self._settings_windows[kind].bring_to_front()

    # -- Qt

    @staticmethod
    def apply_theme(theme_name):
        """Applique le thème `theme_name` à toute l'application."""
        apply_app_theme(QApplication.instance(), theme_name)

    @staticmethod
    def busy():
        """Curseur d'attente le temps d'un bloc `with`."""
        return busy_cursor()
