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
        if isinstance(page, QScrollArea):
            self.scroll = page                      # déjà défilante : pas de double ascenseur
        else:
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
        needed = self._content_width()
        if needed:
            width = max(width, needed)
        self.resize(width, min(max(height, 420), 900))
        saved = self._settings().value(f"settings_window/{self._key}/geometry")
        if saved:
            self.restoreGeometry(saved)
            # Taille mémorisée plus étroite que la page (ancienne largeur fixe
            # de 560 px, police plus grande) : élargie, sinon la page est coupée.
            if needed and self.width() < needed:
                self.resize(needed, self.height())

    def _content_width(self):
        """Largeur qui affiche toute la page sans ascenseur horizontal : sa
        largeur idéale, plus l'ascenseur vertical, le cadre et les marges. Au plus
        90 % de l'écran. None si elle ne peut pas être calculée."""
        try:
            content = self.scroll.widget()
            content.ensurePolished()
            frame = 2 * self.scroll.frameWidth()
            scrollbar = self.scroll.verticalScrollBar().sizeHint().width()
            margins = self.layout().contentsMargins()
            width = (content.sizeHint().width() + frame + scrollbar
                     + margins.left() + margins.right())
            screen_width = self.screen().availableGeometry().width()
        except (AttributeError, TypeError):
            return None
        return min(width, int(screen_width * 0.9))

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
