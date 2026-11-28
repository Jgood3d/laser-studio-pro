"""Panneau du bas de la fenêtre, comme celui de VS Code : ses onglets (Graveur, G-code, File d'attente) sur
une barre toujours visible, sous les onglets de travail. Replié, il ne garde que cette barre ; il se déplie au
clic sur un onglet, avec Ctrl+J (menu Affichage), ou tout seul pendant une gravure et en cas d'alarme. Il
démarre replié : au lancement, le graveur n'est pas encore connecté, la place va aux onglets de travail.

    panel = BottomPanel([("machine", "Graveur", machine_scroll), ("gcode", "G-code", console)], splitter)
    panel.show_page("machine")
    panel.toggle()
"""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QScrollArea, QStackedWidget, QTabBar, QToolButton, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.utils import palette_icon

UNLIMITED_HEIGHT = 16777215              # QWIDGETSIZE_MAX


class BottomPanel(QWidget):
    """`pages` : (clé, titre, widget) ; `splitter` : le séparateur vertical onglets / panneau, dont les tailles
    (panneau déplié) sont gardées dans `expanded_sizes` pour être rendues au dépliage."""

    collapsed_changed = pyqtSignal(bool)

    def __init__(self, pages, splitter, parent=None):
        super().__init__(parent)
        self.setProperty("role", "bottom_panel")             # cadres à plat (thèmes modernes, theme.py)
        self.splitter = splitter
        # Les onglets de travail ne se replient jamais : un QSplitter garde repliée une zone mise à 0, même
        # quand la fenêtre grandit ensuite (bug : fenêtre vide au démarrage, panneau replié avant l'affichage).
        splitter.setCollapsible(0, False)
        self.keys = [key for key, _title, _widget in pages]
        self.expanded_sizes = None
        self._collapsed = None
        self.bar = QTabBar()
        self.bar.setDrawBase(False)
        self.bar.setExpanding(False)
        self.bar.setUsesScrollButtons(False)              # pas de petites flèches : tous les onglets visibles
        self.bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)     # pas de cadre de focus autour des onglets
        self.stack = QStackedWidget()
        for _key, title, widget in pages:
            self.bar.addTab(title)
            self.stack.addWidget(widget)
        self.toggle_button = QToolButton()
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.setToolTip(tr("panel.toggle_tip"))
        self.header = QWidget()
        row = QHBoxLayout(self.header)
        row.setContentsMargins(4, 0, 4, 0)
        row.addWidget(self.bar)
        row.addStretch()
        row.addWidget(self.toggle_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.stack, 1)
        self.bar.currentChanged.connect(self.stack.setCurrentIndex)
        self.bar.tabBarClicked.connect(lambda _index: self.set_collapsed(False))
        self.toggle_button.clicked.connect(self.toggle)
        self.set_collapsed(True)

    def is_collapsed(self):
        return bool(self._collapsed)

    def current_key(self):
        return self.keys[self.bar.currentIndex()]

    def show_page(self, key):
        """Déplie le panneau sur l'onglet `key`."""
        self.bar.setCurrentIndex(self.keys.index(key))
        self.set_collapsed(False)

    def toggle(self):
        self.set_collapsed(not self._collapsed)

    def _shrink(self):
        sizes = self.splitter.sizes()
        height = self.header.sizeHint().height()
        # Pas encore de taille (fenêtre pas encore affichée) : la hauteur maximale du panneau suffit, la mise en
        # page donnera le reste aux onglets.
        if len(sizes) == 2 and self._collapsed and sum(sizes) > height:
            self.splitter.setSizes([sum(sizes) - height, height])

    def _fit_to_content(self):
        sizes = self.splitter.sizes()
        if len(sizes) != 2 or sum(sizes) <= 0:
            return
        page = self.stack.widget(0)                              # le graveur, dans sa zone défilante
        content = page.widget() if isinstance(page, QScrollArea) and page.widget() else page
        wanted = min(self.header.sizeHint().height() + content.minimumSizeHint().height() + 8, sum(sizes) // 2)
        self.splitter.setSizes([sum(sizes) - wanted, wanted])

    def set_collapsed(self, collapsed):
        """Replie (seule la barre d'onglets reste) ou déplie le panneau, à la hauteur qu'il avait."""
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        if collapsed:
            sizes = self.splitter.sizes()
            if self._collapsed is False and len(sizes) == 2 and all(v > 0 for v in sizes):
                self.expanded_sizes = sizes
            self.stack.hide()
            self.setMaximumHeight(self.header.sizeHint().height())
            QTimer.singleShot(0, self._shrink)                    # la place libérée revient aux onglets
        else:
            self.stack.show()
            self.setMaximumHeight(UNLIMITED_HEIGHT)
            if self.expanded_sizes:
                QTimer.singleShot(0, lambda sizes=self.expanded_sizes: self.splitter.setSizes(sizes))
            else:
                QTimer.singleShot(0, self._fit_to_content)       # premier dépliage : la hauteur du contenu
        self._collapsed = collapsed
        self.toggle_button.setIcon(palette_icon("go-up" if collapsed else "go-down", self.palette()))
        self.collapsed_changed.emit(collapsed)
