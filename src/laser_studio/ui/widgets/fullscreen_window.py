"""Fenêtre « Plein écran » qui accueille le contenu d'un onglet."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout


class FullscreenWindow(QDialog):
    """Fenêtre à part, maximisée, qui accueille le contenu d'un onglet.

    Un bouton rouge en haut la ferme, comme la croix ou Échap. À la
    fermeture, elle rend le contenu (sans parent) et émet
    `content_released` : c'est à la fenêtre principale de le remettre
    dans ses onglets.

        window = FullscreenWindow(self, tab, title, close_text)
        window.content_released.connect(put_tab_back)
        window.show_maximized()
    """

    # Le contenu est sorti de la fenêtre, prêt à retourner dans les onglets.
    content_released = pyqtSignal()

    def __init__(self, parent, content, title, close_text):
        super().__init__(parent)
        # Fenêtre indépendante à part entière (pas une simple boîte de
        # dialogue) : boutons minimiser / agrandir / fermer du système et
        # vrai comportement plein écran.
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(title)
        self._content = content
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.addWidget(self._close_button(close_text))
        self._layout.addWidget(content)
        content.setVisible(True)
        self.finished.connect(self._release_content)

    def _close_button(self, text):
        button = QPushButton(text)
        button.setStyleSheet(
            "background-color: #8f2b2b; color: white; padding: 6px; "
            "font-weight: bold;"
        )
        button.clicked.connect(self.close)
        return button

    def show_maximized(self):
        self.show()
        self.setWindowState(Qt.WindowState.WindowMaximized)

    def _release_content(self, _result=None):
        self._layout.removeWidget(self._content)
        self._content.setParent(None)
        self.content_released.emit()
