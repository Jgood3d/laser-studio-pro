"""Éditeur des macros : liste à gauche (ajouter, dupliquer, supprimer, monter, descendre), détail à droite
(nom, infobulle, confirmation, profils machine, G-Code), import / export d'un fichier YAML.

C'est une vue : elle ne lit ni n'écrit macros.yaml. `read_file(chemin)` et `write_file(chemin, macros)`
viennent du contrôleur (controllers/macros.py) ; run() renvoie la liste validée, ou None si annulé.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from laser_studio.grbl.macros import Macro, MacroError, fires_laser, macro_from_dict, macro_to_dict
from laser_studio.i18n import tr
from laser_studio.i18n.errors import generator_error_text

# Modèle proposé pour une nouvelle macro : un décalage relatif, laser éteint.
NEW_MACRO_GCODE = "G91\nG0 X20 Y10\nG90\n"


class MacroEditorDialog(QDialog):
    def __init__(self, macros, profiles, read_file, write_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("macros.title"))
        self.resize(820, 520)
        self._read_file = read_file
        self._write_file = write_file
        self._profiles = list(profiles)
        self._entries = [macro_to_dict(m) for m in macros]
        self._current = -1
        self._loading = False

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._list_side())
        splitter.addWidget(self._detail_side())
        splitter.setStretchFactor(1, 1)

        files = QHBoxLayout()
        for key, slot in (("macros.import", self._import), ("macros.export", self._export)):
            button = QPushButton(tr(key))
            button.clicked.connect(slot)
            files.addWidget(button)
        files.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        files.addWidget(buttons)

        layout = QVBoxLayout(self)
        intro = QLabel(tr("macros.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(splitter, 1)
        layout.addLayout(files)
        self._refresh_list(0)

    # -- construction

    def _list_side(self):
        side = QWidget()
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._select)
        layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.list_buttons = {}
        for name, key, slot in (("add", "macros.add", self._add), ("duplicate", "macros.duplicate", self._duplicate),
                                ("delete", "macros.delete", self._delete), ("up", "macros.up", lambda: self._move(-1)),
                                ("down", "macros.down", lambda: self._move(1))):
            button = QPushButton(tr(key))
            button.clicked.connect(slot)
            row.addWidget(button)
            self.list_buttons[name] = button
        layout.addLayout(row)
        return side

    def _detail_side(self):
        self.detail = QWidget()
        form = QFormLayout(self.detail)
        self.name = QLineEdit()
        self.tooltip = QLineEdit()
        self.confirm = QCheckBox(tr("macros.confirm_check"))
        self.machines = QListWidget()
        self.machines.setMaximumHeight(90)
        for profile in self._profiles:
            item = QListWidgetItem(profile)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.machines.addItem(item)
        self.gcode = QPlainTextEdit()
        self.gcode.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.laser_warning = QLabel(tr("macros.laser_warning"))
        self.laser_warning.setWordWrap(True)
        self.laser_warning.setStyleSheet("color: #c0392b;")
        form.addRow(tr("macros.name"), self.name)
        form.addRow(tr("macros.tooltip"), self.tooltip)
        form.addRow("", self.confirm)
        machines_hint = QLabel(tr("macros.machines_hint"))
        machines_hint.setWordWrap(True)
        form.addRow(tr("macros.machines"), self.machines)
        form.addRow("", machines_hint)
        form.addRow(tr("macros.gcode"), self.gcode)
        form.addRow("", self.laser_warning)
        self.name.textChanged.connect(self._store)
        self.tooltip.textChanged.connect(self._store)
        self.confirm.toggled.connect(self._store)
        self.machines.itemChanged.connect(self._store)
        self.gcode.textChanged.connect(self._store)
        return self.detail

    # -- liste

    def _refresh_list(self, select):
        self._loading = True
        self.list.clear()
        for entry in self._entries:
            self.list.addItem(entry.get("name") or tr("macros.unnamed"))
        self._loading = False
        has = bool(self._entries)
        self.detail.setEnabled(has)
        for name in ("duplicate", "delete", "up", "down"):
            self.list_buttons[name].setEnabled(has)
        self._current = -1
        if has:
            self.list.setCurrentRow(max(0, min(select, len(self._entries) - 1)))
        else:
            self._show({})

    def _select(self, row):
        if self._loading:
            return
        self._current = row
        self._show(self._entries[row] if 0 <= row < len(self._entries) else {})

    def _show(self, entry):
        self._loading = True
        self.name.setText(entry.get("name", ""))
        self.tooltip.setText(entry.get("tooltip", ""))
        self.confirm.setChecked(bool(entry.get("confirm")))
        chosen = set(entry.get("machines", ()))
        for i in range(self.machines.count()):
            item = self.machines.item(i)
            item.setCheckState(Qt.CheckState.Checked if item.text() in chosen else Qt.CheckState.Unchecked)
        self.gcode.setPlainText(entry.get("gcode", ""))
        self._loading = False
        self._update_warning()

    def _store(self, *_args):
        """Le détail affiché est recopié dans l'entrée sélectionnée, à chaque modification."""
        if self._loading or not 0 <= self._current < len(self._entries):
            return
        machines = [self.machines.item(i).text() for i in range(self.machines.count())
                    if self.machines.item(i).checkState() == Qt.CheckState.Checked]
        # Profils inconnus ici (macro importée d'un autre poste) : gardés tels quels.
        kept = [m for m in self._entries[self._current].get("machines", ()) if m not in self._profiles]
        entry = {"name": self.name.text(), "tooltip": self.tooltip.text(), "confirm": self.confirm.isChecked(),
                 "machines": kept + machines, "gcode": self.gcode.toPlainText()}
        self._entries[self._current] = entry
        item = self.list.item(self._current)
        if item is not None:
            item.setText(entry["name"] or tr("macros.unnamed"))
        self._update_warning()

    def _update_warning(self):
        self.laser_warning.setVisible(fires_laser(self.gcode.toPlainText().splitlines()))

    def _add(self):
        self._entries.append({"name": tr("macros.new_name"), "gcode": NEW_MACRO_GCODE})
        self._refresh_list(len(self._entries) - 1)
        self.name.selectAll()
        self.name.setFocus()

    def _duplicate(self):
        if 0 <= self._current < len(self._entries):
            copy = dict(self._entries[self._current])
            copy["name"] = tr("macros.copy_name").format(name=copy.get("name", ""))
            self._entries.insert(self._current + 1, copy)
            self._refresh_list(self._current + 1)

    def _delete(self):
        if 0 <= self._current < len(self._entries):
            del self._entries[self._current]
            self._refresh_list(self._current)

    def _move(self, step):
        i, j = self._current, self._current + step
        if 0 <= i < len(self._entries) and 0 <= j < len(self._entries):
            self._entries[i], self._entries[j] = self._entries[j], self._entries[i]
            self._refresh_list(j)

    # -- fichiers

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("macros.import"), "", tr("macros.file_filter"))
        if not path:
            return
        try:
            imported = self._read_file(path)
        except MacroError as error:
            QMessageBox.warning(self, tr("macros.title"), generator_error_text("macros", error))
            return
        except OSError as error:
            QMessageBox.warning(self, tr("macros.title"), str(error))
            return
        self._entries += [macro_to_dict(m) for m in imported]
        self._refresh_list(len(self._entries) - 1)

    def _export(self):
        macros = self._validated()
        if macros is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("macros.export"), "macros.yaml", tr("macros.file_filter"))
        if not path:
            return
        try:
            self._write_file(path, macros)
        except OSError as error:
            QMessageBox.warning(self, tr("macros.title"), str(error))

    # -- validation

    def _validated(self):
        """Les macros de la liste, ou None (message, et la macro fautive sélectionnée) si l'une est invalide."""
        macros = []
        for index, entry in enumerate(self._entries):
            try:
                macros.append(macro_from_dict(entry, index + 1))
            except MacroError as error:
                self.list.setCurrentRow(index)
                QMessageBox.warning(self, tr("macros.title"), generator_error_text("macros", error))
                return None
        return macros

    def _accept(self):
        macros = self._validated()
        if macros is not None:
            self.result_macros = macros
            self.accept()

    def run(self):
        """Ouvre la fenêtre ; renvoie la liste de Macro validée, ou None si annulé."""
        self.result_macros = None
        return self.result_macros if self.exec() == QDialog.DialogCode.Accepted else None


__all__ = ["MacroEditorDialog", "Macro"]
