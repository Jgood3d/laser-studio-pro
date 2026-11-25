"""Réglages de la fenêtre Qt, construits d'après la liste de la page web (spec.py) : un groupe repliable par
groupe de la page, sur une seule colonne, le titre au-dessus du champ ; le widget selon son type (range : curseur
avec sa valeur saisissable à droite du titre, number : champ numérique, select : liste, check : case et son texte,
text : champ, color : bouton couleur). Les libellés et les bulles d'aide passent par le catalogue de la page.

    form = SettingsForm(spec.load(), tr)
    form.changed.connect(lambda key, value: ...)
    form.show_mode("halftone", state)   # groupes et lignes de ce mode, réglages grisés / masqués selon `state`
    form.set_value("rot", 15)           # sans émettre changed
    form.set_filter("pont", advanced=False)   # recherche, réglages avancés masqués (applyFilter)
"""
import unicodedata

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSizePolicy, QSlider, QToolButton, QVBoxLayout, QWidget)

# Réglage de la page absent du formulaire : « output » est remplacé par les boutons des modes.
SKIPPED = {"output"}


def _decimals(step):
    return 0 if step == int(step) else len(f"{step:.6g}".split(".")[1])


class SliderField(QWidget):
    """Réglage « range » de la page : curseur, et valeur saisissable au clavier avec son unité (`spin`, placé à
    droite du titre). Les pourcentages s'affichent × 100, comme la page ; value() rend la valeur du calcul."""

    valueChanged = pyqtSignal(float)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.step = float(item.get("step", 1) or 1)
        self.minimum, self.maximum = float(item.get("min", 0)), float(item.get("max", 1))
        self.factor = 100 if item.get("fmt") == "pct" else 1
        unit = {"mm": "mm", "pct": "%"}.get(item.get("fmt"), item.get("unit", ""))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(_decimals(self.step * self.factor))
        self.spin.setSingleStep(self.step * self.factor)
        self.spin.setSuffix(f" {unit}" if unit else "")
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin.setMinimumWidth(80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider)
        self._set_range()
        self._show(float(item.get("def") or 0))
        self.slider.valueChanged.connect(lambda i: self.setValue(self.minimum + i * self.step))
        self.spin.valueChanged.connect(lambda v: self.setValue(v / self.factor))

    def value(self):
        return self._value

    def setValue(self, value):
        """Comme un champ Qt : émet valueChanged si la valeur change (bloqué par blockSignals)."""
        before = self.value()
        self._show(value)                         # curseur et champ toujours d'accord
        if self.value() != before:
            self.valueChanged.emit(self.value())

    def _show(self, value):
        value = min(self.maximum, max(self.minimum, float(value)))
        self._value = round(value, 6)
        for widget in (self.slider, self.spin):
            widget.blockSignals(True)
        self.slider.setValue(round((value - self.minimum) / self.step))
        self.spin.setValue(value * self.factor)
        for widget in (self.slider, self.spin):
            widget.blockSignals(False)

    def setMaximum(self, maximum):
        """Borne haute changée (zoom au-delà de 1 seulement en placement libre)."""
        value = self.value()
        self.maximum = float(maximum)
        self._set_range()
        self._show(value)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self.spin.setEnabled(enabled)

    def _set_range(self):
        self.slider.setRange(0, round((self.maximum - self.minimum) / self.step))
        self.spin.setRange(self.minimum * self.factor, self.maximum * self.factor)


class Section(QWidget):
    """Groupe repliable, comme les <details> de la page : en-tête cliquable avec une flèche, réglages dessous."""

    def __init__(self, title, opened=True, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = QToolButton()
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setStyleSheet("QToolButton { border: none; font-weight: bold; text-align: left; padding: 4px; }")
        self.header.toggled.connect(self.set_open)
        self.body = QWidget()
        layout.addWidget(self.header)
        layout.addWidget(self.body)
        self.set_open(opened)

    def is_open(self):
        return self.header.isChecked()

    def set_open(self, opened):
        blocked = self.header.blockSignals(True)
        self.header.setChecked(opened)
        self.header.blockSignals(blocked)
        self.header.setArrowType(Qt.ArrowType.DownArrow if opened else Qt.ArrowType.RightArrow)
        self.body.setVisible(opened)


class SettingsForm(QWidget):
    """`spec` : spec.Spec ; `tr(texte)` : traduction du catalogue de la page. Émet changed(clé, valeur)."""

    changed = pyqtSignal(str, object)

    def __init__(self, spec, tr, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.tr = tr
        self.widgets = {}
        self.boxes = {}
        self.query = ""
        self.advanced = False
        self._mode, self._state = "stencil", {}
        self._rows = {}                   # clé -> (ligne, titre ou None) : pour masquer ou griser une ligne
        self._opened_before_search = None  # état des groupes avant une recherche, rendu quand elle est vidée
        layout = QVBoxLayout(self)
        for group in spec.groups:
            box = Section(tr(group["g"]), group["g"] in spec.default_open)
            rows = QVBoxLayout(box.body)
            rows.setContentsMargins(8, 0, 4, 8)
            for item in group["items"]:
                if item["k"] in SKIPPED:
                    continue
                widget = self._widget(item)
                row, label = self._row(item, widget)
                tip = spec.tips.get(item["k"])
                if tip:
                    row.setToolTip(tr(tip))
                rows.addWidget(row)
                self.widgets[item["k"]] = widget
                self._rows[item["k"]] = (row, label)
            if rows.count():                  # groupe dont aucun réglage n'est repris : pas de cadre vide
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
        réglages (refreshDisabled), recherche et réglages avancés (applyFilter), styles du mode dans « Partir
        d'un style », comme la page."""
        self._mode, self._state = mode, state
        shown = {g["g"] for g in self.spec.groups_for(mode)}
        disabled, hidden = self.spec.row_states(state)
        query = normalize(self.query.strip())
        visible_in = {}
        for group in self.spec.groups:
            for item in group["items"]:
                key = item["k"]
                if key not in self._rows:
                    continue
                row, label = self._rows[key]
                widget = self.widgets[key]
                advanced = (key in self.spec.advanced and not self.advanced
                            and not (key not in self.spec.no_reset and self.spec.is_modified(key, state.get(key))))
                text = normalize(" ".join((self.tr(item.get("label", key)), self.tr(self.spec.tips.get(key, "")),
                                           self.tr(group["g"]))))
                show = (self.spec.row_shown(key, mode) and key not in hidden and not (advanced and not query)
                        and (not query or query in text))
                row.setVisible(show)
                visible_in[group["g"]] = visible_in.get(group["g"], 0) + show
                widget.setEnabled(key not in disabled)
                if label is not None:
                    label.setEnabled(key not in disabled)
        if query and self._opened_before_search is None:
            self._opened_before_search = {name: box.is_open() for name, box in self.boxes.items()}
        elif not query and self._opened_before_search is not None:
            for name, opened in self._opened_before_search.items():
                self.boxes[name].set_open(opened)
            self._opened_before_search = None
        for name, box in self.boxes.items():
            box.setVisible(name in shown and visible_in.get(name, 0) > 0)
            if query and visible_in.get(name, 0):        # la recherche ouvre les groupes où elle trouve un réglage
                box.set_open(True)
        if "zoom" in self.widgets:                       # au-delà de 1 : seulement en placement libre ou tourné
            free = bool(state.get("free")) or float(state.get("rot") or 0) != 0
            self.widgets["zoom"].setMaximum(10.0 if free else 1.0)
        self._fill_presets(mode)

    def insert_after(self, key, widget):
        """Widget sur toute la largeur, juste sous le réglage `key` (panneau des couleurs sous « ml_sep »)."""
        row = self._rows[key][0]
        rows = row.parentWidget().layout()
        rows.insertWidget(rows.indexOf(row) + 1, widget)

    def set_filter(self, query=None, advanced=None):
        """Recherche dans les réglages et « afficher les réglages avancés », comme la page."""
        if query is not None:
            self.query = query
        if advanced is not None:
            self.advanced = bool(advanced)
        self.show_mode(self._mode, self._state)

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

    def _row(self, item, widget):
        """Ligne de la page : titre au-dessus du champ (valeur du curseur à droite du titre) ; une case porte son
        texte. Rend (ligne, titre ou None)."""
        text = self.tr(item.get("label", item["k"]))
        if item["t"] == "check":
            widget.setText(text)
            return widget, None
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 2)
        layout.setSpacing(2)
        label = QLabel(text)
        label.setWordWrap(True)
        top = QHBoxLayout()
        top.addWidget(label, 1)
        if isinstance(widget, SliderField):
            top.addWidget(widget.spin)
        layout.addLayout(top)
        layout.addWidget(widget)
        return row, label

    def _widget(self, item):
        kind, key = item["t"], item["k"]
        if kind == "range":
            widget = SliderField(item)
            widget.valueChanged.connect(lambda v, k=key: self.changed.emit(k, v))
        elif kind == "number":
            widget = QDoubleSpinBox()
            step = float(item.get("step", 1) or 1)
            widget.setDecimals(max(_decimals(step), 1))   # champ libre de la page : garde les dixièmes
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


def normalize(text):
    """Texte comparable pour la recherche : minuscules, sans accents (norm de la page)."""
    decomposed = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
