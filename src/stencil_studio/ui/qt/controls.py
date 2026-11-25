"""Réglages de la fenêtre Qt, construits d'après la liste de la page web (spec.py) : un cadre par groupe, une
ligne par réglage, le widget selon son type (range / number : champ numérique, select : liste, check : case,
text : champ, color : bouton couleur). Les libellés et les bulles d'aide passent par le catalogue de la page.

    form = SettingsForm(spec.load(), tr)
    form.changed.connect(lambda key, value: ...)
    form.show_mode("halftone")          # groupes et lignes de ce mode seulement
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                             QLineEdit, QPushButton, QVBoxLayout, QWidget)

# Réglages de la page que la fenêtre Qt ne propose pas encore.
# shortcut: placement libre / rotation / zoom du cadre, peinture des repères, styles prédéfinis et aperçu avant
# export ne sont pas repris dans le parcours principal ; à ajouter avec l'édition du cadre et des repères.
SKIPPED = {"output", "preset", "free", "rot", "img_mm", "zoom", "brush", "exp_preview"}


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

    def show_mode(self, mode):
        """N'affiche que les groupes et les lignes du mode `mode`, comme la page (groupOK, MODE_ROWS)."""
        shown = {g["g"] for g in self.spec.groups_for(mode)}
        for name, box in self.boxes.items():
            box.setVisible(name in shown)
        for key, (form, widget) in self._rows.items():
            form.setRowVisible(widget, self.spec.row_shown(key, mode))

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
