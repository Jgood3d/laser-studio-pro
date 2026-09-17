"""Petits widgets réutilisables qui ne rentrent pas ailleurs."""
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt


class HistoryLineEdit(QLineEdit):
    """QLineEdit avec historique des commandes rappelable via les flèches
    Haut/Bas, comme un terminal classique. Utilisé pour le champ de
    commande manuelle GRBL."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []
        self._history_index = -1

    def add_to_history(self, text):
        text = text.strip()
        if not text:
            return
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._history_index = len(self._history)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            if self._history and self._history_index > 0:
                self._history_index -= 1
                self.setText(self._history[self._history_index])
            event.accept()
            return
        if event.key() == Qt.Key.Key_Down:
            if self._history:
                if self._history_index < len(self._history) - 1:
                    self._history_index += 1
                    self.setText(self._history[self._history_index])
                else:
                    self._history_index = len(self._history)
                    self.clear()
            event.accept()
            return
        super().keyPressEvent(event)
