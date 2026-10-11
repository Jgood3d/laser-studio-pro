"""Fenêtre de réglages ouverte depuis la barre de menus (Machine & Profils, Configuration GRBL).

La fenêtre héberge une page de réglages déjà construite (ses widgets restent les mêmes objets : tout
le code qui les lit continue de fonctionner) dans une zone défilante. Non modale : on peut garder la
fenêtre ouverte et continuer à travailler. La fermer la masque seulement ; sa taille et sa position
sont mémorisées entre deux sessions."""
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog, QScrollArea, QVBoxLayout


class SettingsWindow(QDialog):
    def __init__(self, parent, title, page, key, default_width=560):
        super().__init__(parent)
        self._key = key
        self.page = page
        self.setWindowTitle(title)
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(page)
        layout.addWidget(self.scroll)
        self._apply_initial_size(default_width)

    def _settings(self):
        return QSettings("LaserStudioPro", "UIConfig")

    def _apply_initial_size(self, width):
        try:
            height = int(self.screen().availableGeometry().height() * 0.85)
        except (AttributeError, TypeError):
            height = 700
        self.resize(width, min(max(height, 420), 900))
        saved = self._settings().value(f"settings_window/{self._key}/geometry")
        if saved:
            self.restoreGeometry(saved)

    def _remember_geometry(self):
        self._settings().setValue(f"settings_window/{self._key}/geometry", self.saveGeometry())

    def closeEvent(self, event):
        self._remember_geometry()
        super().closeEvent(event)

    def done(self, result):
        self._remember_geometry()
        super().done(result)

    def bring_to_front(self):
        self.show()
        self.raise_()
        self.activateWindow()
