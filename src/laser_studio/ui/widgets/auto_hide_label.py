"""Libellé qui se masque quand son texte est vide."""
from PyQt6.QtWidgets import QLabel


class AutoHideLabel(QLabel):
    """QLabel qui se masque tout seul quand son texte est vide et
    réapparaît dès qu'il contient quelque chose. Évite de garder un trou
    vide dans la mise en page pour les libellés d'état temporaires
    (ex. « Génération en cours… ») qui sont vides la plupart du temps."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        # Ne masque que si vide : appeler setVisible(True) sur un label sans
        # parent l'afficherait comme une fenêtre isolée avant son layout.
        if not text:
            self.hide()

    def setText(self, text):
        super().setText(text)
        self.setVisible(bool(text))
