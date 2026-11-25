"""Réglages de la fenêtre Qt, construits d'après la liste de la page web (spec.py) : un cadre par groupe, une
ligne par réglage, le widget selon son type (range / number : champ numérique, select : liste, check : case,
text : champ, color : bouton couleur). Les libellés et les bulles d'aide passent par le catalogue de la page.

    form = SettingsForm(spec.load(), tr)
    form.changed.connect(lambda key, value: ...)
    form.show_mode("halftone", state)   # groupes et lignes de ce mode, réglages grisés / masqués selon `state`
    form.set_value("rot", 15)           # sans émettre changed
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                             QLineEdit, QPushButton, QVBoxLayout, QWidget)

# Réglages de la page absents de la fenêtre Qt : « output » est remplacé par les boutons des modes.
# shortcut: largeur de l'image sur la plaque (img_mm), pinceau des repères (brush) et aperçu avant export
# (exp_preview) pas encore repris ; à ajouter avec la peinture des repères et la fenêtre d'aperçu d'export.
SKIPPED = {"output", "img_mm", "brush", "exp_preview"}


class SettingsForm(QWidget):
    """`spec` : spec.Spec ; `tr(texte)` : traduction du catalogue de la page. Émet changed(clé, valeur)."""

    changed = pyqtSignal(str, object)

    def __init__(self, spec, tr, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.tr = tr
        self.widgets = {}
        self.boxes = {}
        self._rows = {}                   # clé -> (formulaire, widget) : pour masquer une ligne
        layout = QVBoxLayout(self)
        for group in spec.groups:
            box = QGroupBox(tr(group["g"]))
            form = QFormLayout(box)
            for item in group["items"]:
                if item["k"] in SKIPPED:
                    continue
                widget = self._widget(item)
                tip = spec.tips.get(item["k"])
                if tip:
                    widget.setToolTip(tr(tip))
                form.addRow(tr(item.get("label", item["k"])), widget)
                self.widgets[item["k"]] = widget
                self._rows[item["k"]] = (form, widget)
            if form.rowCount():               # groupe dont aucun réglage n'est repris : pas de cadre vide
                self.boxes[group["g"]] = box
                layout.addWidget(box)
        layout.addStretch()

    # -- valeurs

    def value(self, key):
        widget, item = self.widgets[key], self.spec.item(key)
        kind = item["t"]
        if kind in ("range", "number"):
            return widget.value()
        if kind == "select":
            return widget.currentData()
        if kind == "check":
            return widget.isChecked()
        if kind == "color":
            return widget.property("color")
        return widget.text()

    def values(self):
        return {key: self.value(key) for key in self.widgets}

    def set_value(self, key, value):
        """Valeur affichée du réglage `key`, sans émettre changed (style appliqué, cadre recalé…)."""
        widget = self.widgets.get(key)
        if widget is None:
            return
        kind = self.spec.item(key)["t"]
        blocked = widget.blockSignals(True)
        if kind in ("range", "number"):
            widget.setValue(float(value or 0))
        elif kind == "select":
            widget.setCurrentIndex(max(0, widget.findData(value)))
        elif kind == "check":
            widget.setChecked(bool(value))
        elif kind == "color":
            self._set_color(widget, value)
        else:
            widget.setText(str(value or ""))
        widget.blockSignals(blocked)

    def show_mode(self, mode, state):
        """Groupes et lignes du mode `mode` (groupOK, MODE_ROWS), réglages grisés ou masqués selon les autres
        réglages (refreshDisabled), styles du mode dans « Partir d'un style », comme la page."""
        shown = {g["g"] for g in self.spec.groups_for(mode)}
        for name, box in self.boxes.items():
            box.setVisible(name in shown)
        disabled, hidden = self.spec.row_states(state)
        for key, (form, widget) in self._rows.items():
            form.setRowVisible(widget, self.spec.row_shown(key, mode) and key not in hidden)
            widget.setEnabled(key not in disabled)
            label = form.labelForField(widget)
            if label is not None:
                label.setEnabled(key not in disabled)
        if "zoom" in self.widgets:                       # au-delà de 1 : seulement en placement libre ou tourné
            free = bool(state.get("free")) or float(state.get("rot") or 0) != 0
            self.widgets["zoom"].setMaximum(10.0 if free else 1.0)
        self._fill_presets(mode)

    def _fill_presets(self, mode):
        combo = self.widgets.get("preset")
        if combo is None:
            return
        labels = dict(self.spec.item("preset")["opts"])
        blocked = combo.blockSignals(True)
        combo.clear()
        combo.addItem(self.tr(labels[""]), "")
        for name in self.spec.presets_for(mode):
            combo.addItem(self.tr(labels[name]), name)
        combo.blockSignals(blocked)

    # -- construction

    def _widget(self, item):
        kind, key = item["t"], item["k"]
        if kind in ("range", "number"):
            widget = QDoubleSpinBox()
            step = float(item.get("step", 1) or 1)
            decimals = 0 if step == int(step) else len(str(step).split(".")[1])
            widget.setDecimals(decimals)
            widget.setRange(float(item.get("min", -1e9)), float(item.get("max", 1e9)))
            widget.setSingleStep(step)
            widget.setValue(float(item.get("def") or 0))
            if item.get("fmt") == "mm":
                widget.setSuffix(" mm")
            widget.valueChanged.connect(lambda v, k=key: self.changed.emit(k, v))
        elif kind == "select":
            widget = QComboBox()
            for value, label in item.get("opts", []):
                widget.addItem(self.tr(label), value)
            widget.setCurrentIndex(max(0, widget.findData(item.get("def"))))
            widget.currentIndexChanged.connect(lambda _i, k=key, w=widget: self.changed.emit(k, w.currentData()))
        elif kind == "check":
            widget = QCheckBox()
            widget.setChecked(bool(item.get("def")))
            widget.toggled.connect(lambda v, k=key: self.changed.emit(k, v))
        elif kind == "color":
            widget = QPushButton()
            self._set_color(widget, item.get("def") or "#000000")
            widget.clicked.connect(lambda _c=False, k=key, w=widget: self._pick_color(k, w))
        else:
            widget = QLineEdit(str(item.get("def") or ""))
            if item.get("maxlen"):
                widget.setMaxLength(int(item["maxlen"]))
            widget.editingFinished.connect(lambda k=key, w=widget: self.changed.emit(k, w.text()))
        return widget

    @staticmethod
    def _set_color(button, color):
        button.setProperty("color", color)
        button.setText(color)
        button.setStyleSheet(f"background-color: {color};")

    def _pick_color(self, key, button):
        color = QColorDialog.getColor(QColor(button.property("color")), self)
        if color.isValid():
            self._set_color(button, color.name())
            self.changed.emit(key, color.name())
