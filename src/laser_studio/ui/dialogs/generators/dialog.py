"""Les générateurs dans une seule fenêtre : leur liste à gauche ; à droite, la fenêtre du générateur choisi,
avec ses réglages puis son aperçu. Chaque générateur garde sa propre fenêtre (BoxGeneratorDialog…), posée ici
comme un simple widget ; ses boutons OK / Annuler sont masqués au profit des boutons communs « Importer » et
« Annuler » de cette fenêtre. « Importer » appuie sur le OK du générateur affiché : ses vérifications restent les
siennes, et il est grisé quand ce OK l'est."""
from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QStackedWidget, QVBoxLayout)

from laser_studio.i18n import tr

LIST_WIDTH = 210


class GeneratorsDialog(QDialog):
    """`pages` : (clé, titre, icône, make(parent) -> fenêtre du générateur) ; chaque fenêtre n'est construite
    qu'à son premier affichage (la boîte et son aperçu 3D, les polices du porte-clés). Validée : `chosen` est
    la clé du générateur validé, `page(clé)` sa fenêtre, à lire comme avant."""

    def __init__(self, parent, pages, start):
        super().__init__(parent)
        self.setWindowTitle(tr("ui.vector_generators"))
        self.chosen = None
        self._keys = [key for key, *_ in pages]
        self._makers = {key: make for key, _title, _icon, make in pages}
        self._pages = {}
        self.list = QListWidget()
        self.list.setFixedWidth(LIST_WIDTH)
        self.list.setIconSize(QSize(22, 22))
        self.list.setStyleSheet("QListWidget::item { padding: 8px 10px; }")
        self.list.setProperty("role", "sidebar")          # liste des générateurs : panneau latéral
        self.stack = QStackedWidget()
        for _key, title, icon, _make in pages:
            QListWidgetItem(icon, title, self.list)
            self.stack.addWidget(QLabel())             # remplacée par la fenêtre au premier affichage
        self._ok_buttons = {}                          # bouton OK (masqué) de chaque générateur
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.import_button = self.buttons.addButton(tr("library.import"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.import_button.setProperty("role", "primary")
        self.import_button.setDefault(True)
        self.buttons.accepted.connect(self._import)
        self.buttons.rejected.connect(self.reject)
        right = QVBoxLayout()
        right.addWidget(self.stack, 1)
        right.addWidget(self.buttons)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.list)
        layout.addLayout(right, 1)
        self.list.currentRowChanged.connect(self._show_row)
        self.list.setCurrentRow(self._keys.index(start) if start in self._keys else 0)
        self._fit_to_screen()

    def page(self, key):
        """Fenêtre du générateur `key` (construite au besoin)."""
        if key not in self._pages:
            dialog = self._makers[key](self)
            dialog.setWindowFlags(Qt.WindowType.Widget)      # posée dans la fenêtre, plus une fenêtre à part
            dialog.accepted.connect(lambda k=key: self._accept(k))
            dialog.rejected.connect(self.reject)
            for box in dialog.findChildren(QDialogButtonBox):
                # Valider / Annuler de la page : remplacés par les boutons communs ; les autres (« Détails »
                # de la bibliothèque) restent.
                for button in box.buttons():
                    role = box.buttonRole(button)
                    if role == QDialogButtonBox.ButtonRole.AcceptRole:
                        self._ok_buttons[key] = button
                        button.installEventFilter(self)   # grisé / actif : suivi par « Importer »
                        button.hide()
                    elif role == QDialogButtonBox.ButtonRole.RejectRole:
                        button.hide()
                if not any(not b.isHidden() for b in box.buttons()):
                    box.hide()
            index = self._keys.index(key)
            placeholder = self.stack.widget(index)
            self.stack.insertWidget(index, dialog)
            self.stack.removeWidget(placeholder)
            placeholder.deleteLater()
            self._pages[key] = dialog
        return self._pages[key]

    def _show_row(self, row):
        if row >= 0:
            self.page(self._keys[row])
            self.stack.setCurrentIndex(row)
            self._follow_ok()

    def current_key(self):
        return self._keys[self.list.currentRow()]

    def _import(self):
        """« Importer » : le OK du générateur affiché (qui vérifie ses réglages, puis valide)."""
        ok = self._ok_buttons.get(self.current_key())
        if ok is not None:
            ok.click()
        else:
            self.page(self.current_key()).accept()

    def _follow_ok(self):
        ok = self._ok_buttons.get(self.current_key())
        self.import_button.setEnabled(ok is None or ok.isEnabled())

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.EnabledChange:
            self._follow_ok()
        return super().eventFilter(watched, event)

    def _accept(self, key):
        self.chosen = key
        self.accept()

    def _fit_to_screen(self):
        try:
            area = self.screen().availableGeometry()
            self.resize(int(area.width() * 0.9), int(area.height() * 0.85))
        except AttributeError:          # sans écran (tests)
            self.resize(1300, 800)
