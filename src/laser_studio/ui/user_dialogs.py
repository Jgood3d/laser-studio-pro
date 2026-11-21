"""Boîtes de dialogue posées à l'utilisateur par les contrôleurs : messages,
confirmations, choix de fichier.

Les contrôleurs ne créent pas de QMessageBox / QFileDialog eux-mêmes : ils
reçoivent un UserDialogs. Dans les tests, on leur passe un objet qui a les
mêmes méthodes et qui répond à la place de l'utilisateur.

    dialogs = UserDialogs(window)
    if dialogs.confirm(tr("gen.confirm_title"), texte):
        ...
"""
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No
_CANCEL = QMessageBox.StandardButton.Cancel


class UserDialogs:
    """Boîtes de dialogue modales, centrées sur `parent`."""

    def __init__(self, parent=None):
        self.parent = parent

    def info(self, title, text):
        QMessageBox.information(self.parent, title, text)

    def warning(self, title, text):
        QMessageBox.warning(self.parent, title, text)

    def error(self, title, text):
        QMessageBox.critical(self.parent, title, text)

    def confirm(self, title, text):
        """Question Oui / Annuler, Oui par défaut. True si Oui."""
        return QMessageBox.question(self.parent, title, text, _YES | _CANCEL, _YES) == _YES

    def confirm_default_no(self, title, text):
        """Question Oui / Non, Non par défaut (action à risque : lancer un job,
        écrire la configuration du graveur). True si Oui."""
        return QMessageBox.question(self.parent, title, text, _YES | _NO, _NO) == _YES

    def confirm_yes_no(self, title, text):
        """Question Oui / Non, bouton par défaut choisi par Qt (suppression
        d'un élément). True si Oui."""
        return QMessageBox.question(self.parent, title, text, _YES | _NO) == _YES

    def ask_yes_no(self, title, text):
        """Avertissement Oui / Non, sans bouton par défaut. True si Oui."""
        return QMessageBox.warning(self.parent, title, text, _YES | _NO) == _YES

    def save_file(self, title, default_name, file_filter):
        """Chemin choisi pour enregistrer, ou "" si annulé."""
        path, _ = QFileDialog.getSaveFileName(self.parent, title, default_name, file_filter)
        return path

    def open_file(self, title, file_filter):
        """Fichier choisi à ouvrir, ou "" si annulé."""
        path, _ = QFileDialog.getOpenFileName(self.parent, title, "", file_filter)
        return path

    def ask_text(self, title, label):
        """Texte saisi (non nettoyé), ou None si annulé."""
        text, ok = QInputDialog.getText(self.parent, title, label)
        return text if ok else None
