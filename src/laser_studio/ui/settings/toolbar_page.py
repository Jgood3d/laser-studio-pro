"""Page « Barre d'outils » de la fenêtre Paramètres (issue #190).

À gauche : toutes les commandes disponibles, groupées par menu, avec
recherche. À droite : les boutons de la barre, dans l'ordre. Boutons
Ajouter / Retirer / Monter / Descendre / Séparateur / Rétablir par défaut.
Glisser-déposer et clavier (accessibilité).
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.app.menu.toolbar_config import (
    CATALOG,
    DEFAULT_ACTIONS,
    SEPARATOR,
    action_for_id,
    catalog_label,
    load_toolbar_actions,
    reset_toolbar_actions,
    save_toolbar_actions,
)


ROLE_ID = Qt.ItemDataRole.UserRole
ROLE_GROUP = Qt.ItemDataRole.UserRole + 1


class ToolbarPage(QWidget):
    """`actions` : AppActions ; `on_apply` : callable(list[str]) appelé après
    chaque modification pour reconstruire la barre immédiatement."""

    changed = pyqtSignal(list)  # nouvelle liste d'identifiants

    def __init__(self, actions, on_apply=None, parent=None):
        super().__init__(parent)
        self._actions = actions
        self._on_apply = on_apply

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("toolbar.search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_available)

        left_label = QLabel(tr("toolbar.available"))
        self.available = QListWidget()
        self.available.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.available.setDragEnabled(True)
        self.available.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.available.itemDoubleClicked.connect(lambda _item: self._add())

        self.btn_add = QPushButton(tr("toolbar.add"))
        self.btn_remove = QPushButton(tr("toolbar.remove"))
        self.btn_up = QPushButton(tr("toolbar.move_up"))
        self.btn_down = QPushButton(tr("toolbar.move_down"))
        self.btn_sep = QPushButton(tr("toolbar.add_separator"))
        self.btn_reset = QPushButton(tr("toolbar.reset"))
        for btn, slot in (
            (self.btn_add, self._add),
            (self.btn_remove, self._remove),
            (self.btn_up, lambda: self._move(-1)),
            (self.btn_down, lambda: self._move(1)),
            (self.btn_sep, self._add_separator),
            (self.btn_reset, self._reset),
        ):
            btn.clicked.connect(slot)

        mid = QVBoxLayout()
        mid.addStretch()
        for btn in (self.btn_add, self.btn_remove, self.btn_up, self.btn_down,
                    self.btn_sep, self.btn_reset):
            mid.addWidget(btn)
        mid.addStretch()

        right_label = QLabel(tr("toolbar.current"))
        self.current = QListWidget()
        self.current.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.current.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.current.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.current.model().rowsMoved.connect(lambda *_: self._commit())
        self.current.itemDoubleClicked.connect(lambda _item: self._remove())

        left_col = QVBoxLayout()
        left_col.addWidget(left_label)
        left_col.addWidget(self.search)
        left_col.addWidget(self.available, 1)

        right_col = QVBoxLayout()
        right_col.addWidget(right_label)
        right_col.addWidget(self.current, 1)

        row = QHBoxLayout()
        row.addLayout(left_col, 1)
        row.addLayout(mid)
        row.addLayout(right_col, 1)

        hint = QLabel(tr("toolbar.hint"))
        hint.setWordWrap(True)
        hint.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addLayout(row, 1)
        layout.addWidget(hint)

        self._populate_available()
        self._populate_current(load_toolbar_actions())

        self.available.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.current.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _populate_available(self):
        self.available.clear()
        for group_id, title_key, entries in CATALOG:
            header = QListWidgetItem(tr(title_key))
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setData(ROLE_GROUP, group_id)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            self.available.addItem(header)
            for action_id, _label_key in entries:
                self._add_available_item(action_id)

    def _add_available_item(self, action_id):
        action = action_for_id(self._actions, action_id)
        label = catalog_label(action_id) or action_id
        item = QListWidgetItem(label)
        if action is not None and not action.icon().isNull():
            item.setIcon(action.icon())
        else:
            item.setIcon(QIcon())
        item.setData(ROLE_ID, action_id)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        self.available.addItem(item)

    def _populate_current(self, action_ids):
        self.current.clear()
        for action_id in action_ids:
            self.current.addItem(self._make_current_item(action_id))

    def _make_current_item(self, action_id):
        if action_id == SEPARATOR:
            item = QListWidgetItem("——— " + tr("toolbar.separator") + " ———")
            item.setData(ROLE_ID, SEPARATOR)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            return item
        action = action_for_id(self._actions, action_id)
        label = catalog_label(action_id) or action_id
        item = QListWidgetItem(label)
        if action is not None and not action.icon().isNull():
            item.setIcon(action.icon())
        item.setData(ROLE_ID, action_id)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        return item

    def _filter_available(self, text):
        text = (text or "").strip().casefold()
        for i in range(self.available.count()):
            item = self.available.item(i)
            if item.data(ROLE_GROUP) is not None:
                item.setHidden(False)
                continue
            if not text:
                item.setHidden(False)
                continue
            label = item.text().casefold()
            item.setHidden(text not in label)

    def _current_ids(self):
        ids = []
        for i in range(self.current.count()):
            aid = self.current.item(i).data(ROLE_ID)
            if aid:
                ids.append(aid)
        return ids

    def _commit(self):
        ids = self._current_ids()
        save_toolbar_actions(ids)
        self.changed.emit(ids)
        if self._on_apply is not None:
            self._on_apply(ids)

    def _selected_available_ids(self):
        ids = []
        for item in self.available.selectedItems():
            aid = item.data(ROLE_ID)
            if aid:
                ids.append(aid)
        return ids

    def _add(self):
        ids = self._selected_available_ids()
        if not ids:
            return
        for aid in ids:
            self.current.addItem(self._make_current_item(aid))
        self._commit()

    def _remove(self):
        rows = sorted(
            (self.current.row(item) for item in self.current.selectedItems()),
            reverse=True,
        )
        if not rows:
            return
        for row in rows:
            self.current.takeItem(row)
        if not any(i != SEPARATOR for i in self._current_ids()):
            self._populate_current(DEFAULT_ACTIONS)
        self._commit()

    def _move(self, delta):
        rows = sorted(self.current.row(item) for item in self.current.selectedItems())
        if not rows:
            return
        if delta < 0 and rows[0] == 0:
            return
        if delta > 0 and rows[-1] == self.current.count() - 1:
            return
        if delta < 0:
            for row in rows:
                item = self.current.takeItem(row)
                self.current.insertItem(row + delta, item)
                item.setSelected(True)
        else:
            for row in reversed(rows):
                item = self.current.takeItem(row)
                self.current.insertItem(row + delta, item)
                item.setSelected(True)
        self._commit()

    def _add_separator(self):
        row = self.current.currentRow()
        item = self._make_current_item(SEPARATOR)
        if row < 0:
            self.current.addItem(item)
        else:
            self.current.insertItem(row + 1, item)
        self._commit()

    def _reset(self):
        ids = reset_toolbar_actions()
        self._populate_current(ids)
        self.changed.emit(ids)
        if self._on_apply is not None:
            self._on_apply(ids)

    def reload(self):
        """Recharge la liste depuis les préférences (après ouverture de la page)."""
        self._populate_current(load_toolbar_actions())
