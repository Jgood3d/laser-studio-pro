"""Boîtes de dialogue posées à l'utilisateur par les contrôleurs : messages,
confirmations, choix de fichier.

Les contrôleurs ne créent pas de QMessageBox / QFileDialog eux-mêmes : ils
reçoivent un UserDialogs. Dans les tests, on leur passe un objet qui a les
mêmes méthodes et qui répond à la place de l'utilisateur.

    dialogs = UserDialogs(window)
    if dialogs.confirm(tr("gen.confirm_title"), texte):
        ...
    dialogs.notify(tr("project.save_success"))     # réussite : barre d'état, sans fenêtre à fermer
"""
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QInputDialog, QLabel, QMessageBox,
                             QPushButton, QVBoxLayout)

from laser_studio.i18n import tr

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No
_CANCEL = QMessageBox.StandardButton.Cancel


class UserDialogs:
    """Boîtes de dialogue modales, centrées sur `parent`."""

    def __init__(self, parent=None):
        self.parent = parent

    def info(self, title, text):
        QMessageBox.information(self.parent, title, text)

    def notify(self, text):
        """Une réussite (projet enregistré, import, export…) : message dans la barre d'état de la fenêtre, le
        texte complet en infobulle, sans fenêtre à fermer. Sans barre d'état (fenêtre à part), une boîte."""
        window = self.parent.window() if self.parent is not None else None
        status_bar = getattr(window, "statusBar", None)
        bar = status_bar() if callable(status_bar) else None
        if bar is not None and hasattr(bar, "show_log"):
            bar.show_log(text)
        else:
            QMessageBox.information(self.parent, "", text)

    def countdown(self, seconds):
        """Compte à rebours avant la gravure (ui/dialogs/countdown) : True à la fin, False si annulé. Rien à
        attendre si `seconds` vaut 0."""
        if seconds <= 0:
            return True
        from laser_studio.ui.dialogs.countdown import CountdownDialog   # chargé au premier compte à rebours
        return CountdownDialog(seconds, self.parent).exec() == QDialog.DialogCode.Accepted

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

    def open_folder(self, title):
        """Dossier choisi, ou "" si annulé."""
        return QFileDialog.getExistingDirectory(self.parent, title)

    def ask_text(self, title, label, text=""):
        """Texte saisi (non nettoyé), ou None si annulé ; `text` : texte proposé au départ."""
        args = (self.parent, title, label)
        answer, ok = QInputDialog.getText(*args, text=text) if text else QInputDialog.getText(*args)
        return answer if ok else None

    def ask_number(self, title, label, value, minimum, maximum, decimals=1):
        """Nombre saisi (entre `minimum` et `maximum`), ou None si annulé."""
        number, ok = QInputDialog.getDouble(self.parent, title, label, value, minimum, maximum, decimals)
        return number if ok else None

    def choose(self, title, text, choices):
        """Choix entre plusieurs réponses, plus Annuler. `choices` : liste de (clé, libellé), le premier
        étant le bouton par défaut. Renvoie la clé choisie, ou None si annulé (bouton ou Échap)."""
        return ChoiceDialog(title, text, choices, self.parent).choose()


class ChoiceDialog(QDialog):
    """Question et une réponse par bouton, empilés sur toute la largeur dans l'ordre donné (les libellés
    restent lisibles en entier, quel que soit le style du bureau), puis Annuler."""

    def __init__(self, title, text, choices, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.key = None
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.buttons = {}
        for index, (key, choice) in enumerate(choices):
            button = QPushButton(choice)
            button.setAutoDefault(index == 0)
            button.setDefault(index == 0)
            button.clicked.connect(lambda _checked=False, k=key: self._pick(k))
            layout.addWidget(button)
            self.buttons[key] = button
        cancel = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        cancel.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        cancel.rejected.connect(self.reject)
        layout.addWidget(cancel)
        self.setMinimumWidth(380)

    def _pick(self, key):
        self.key = key
        self.accept()

    def choose(self):
        return self.key if self.exec() == QDialog.DialogCode.Accepted else None
