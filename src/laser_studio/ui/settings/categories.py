"""Pages de réglages réunies dans une fenêtre, comme les paramètres de VS Code : la liste des catégories à
gauche, la page choisie à droite, chacune dans sa zone défilante.

    categories = SettingsCategories([("machine_params", "Paramètres du graveur", page), ("grbl", "GRBL", page2)])
    categories.show_page("grbl")
"""
from PyQt6.QtWidgets import QHBoxLayout, QListWidget, QScrollArea, QStackedWidget, QWidget

LIST_WIDTH = 200
# Taille minimale de la fenêtre « Paramètres » : l'éditeur des macros (liste et détail côte à côte) y tient.
MIN_WIDTH, MIN_HEIGHT = 1180, 620


class SettingsCategories(QWidget):
    """`pages` : (clé, titre, page déjà construite) ; les pages restent les mêmes objets, le code qui lit
    leurs widgets continue de fonctionner."""

    scrolls_itself = True       # SettingsWindow ne l'enveloppe pas dans une seconde zone défilante

    def __init__(self, pages, parent=None):
        super().__init__(parent)
        self.keys = [key for key, _title, _page in pages]
        self.list = QListWidget()
        self.list.setFixedWidth(LIST_WIDTH)
        self.list.setStyleSheet("QListWidget::item { padding: 6px 10px; }")
        self.list.setProperty("role", "sidebar")          # liste des catégories : panneau latéral
        self.stack = QStackedWidget()
        for _key, title, page in pages:
            self.list.addItem(title)
            if not isinstance(page, QScrollArea):
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setWidget(page)
                page = scroll
            self.stack.addWidget(page)
        self.list.currentRowChanged.connect(self.stack.setCurrentIndex)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list)
        layout.addWidget(self.stack, 1)
        self.list.setCurrentRow(0)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

    def show_page(self, key):
        """Affiche la page `key` (et la sélectionne dans la liste)."""
        self.list.setCurrentRow(self.keys.index(key))

    def current_key(self):
        return self.keys[self.list.currentRow()]
