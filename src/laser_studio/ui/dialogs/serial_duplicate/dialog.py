"""Fenêtre de réglage de la duplication en série : nombre d'exemplaires, un texte (prénom) par exemplaire,
disposition en grille ou par imbrication automatique."""
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel,
    QPlainTextEdit, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.vector import nesting
from laser_studio.vector import serial_duplicate as sd


def _spin(minimum, maximum, value, decimals=1, step=1.0):
    s = QDoubleSpinBox()
    s.setRange(minimum, maximum)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setSuffix(" mm")
    return s


def _preview(text, limit=24):
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit - 1] + "…"


class SerialDuplicateDialog(QDialog):
    """Lit : `params()` (paramètres pour serial_apply.plan_serial_duplicate) et `settings()` (à mémoriser)."""

    def __init__(self, parent, texts, n_objects, set_w, set_h, bed_w_mm, bed_h_mm, initial=None):
        """texts : [(texte, indice de l'objet dans la sélection)] pour chaque texte de la sélection ;
        set_w / set_h : taille d'un exemplaire (mm)."""
        super().__init__(parent)
        init = initial or {}
        self._set_w, self._set_h = float(set_w), float(set_h)
        self._bed_w, self._bed_h = float(bed_w_mm), float(bed_h_mm)
        self._cols_user = bool(init.get("cols_user", False))
        self._has_text = bool(texts)
        self.setWindowTitle(tr("serial.title"))
        self.setMinimumWidth(480)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        info = QLabel(tr("serial.selection_info").format(count=n_objects))
        info.setWordWrap(True)
        form.addRow(info)

        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, sd.MAX_COPIES)
        self.spin_count.setValue(int(init.get("count", 5)))
        self.spin_count.setToolTip(tr("serial.count_tip"))
        form.addRow(tr("serial.count"), self.spin_count)

        # -- personnalisation (un texte par exemplaire) --------------------------------------------------------
        self.combo_text = QComboBox()
        self.edit_names = QPlainTextEdit()
        self.check_center = QCheckBox(tr("serial.keep_center"))
        self.check_center.setChecked(bool(init.get("keep_center", True)))
        if self._has_text:
            for text, index in texts:
                self.combo_text.addItem(_preview(text), index)
            self.edit_names.setPlaceholderText(tr("serial.names_placeholder"))
            self.edit_names.setMinimumHeight(110)
            form.addRow(tr("serial.text_target"), self.combo_text)
            form.addRow(tr("serial.names"), self.edit_names)
            form.addRow(self.check_center)
        else:
            no_text = QLabel(tr("serial.no_text"))
            no_text.setWordWrap(True)
            form.addRow(no_text)

        # -- disposition ----------------------------------------------------------------------------------------
        self.combo_layout = QComboBox()
        self.combo_layout.addItem(tr("serial.layout_grid"), "grid")
        self.combo_layout.addItem(tr("serial.layout_nest"), "nest")
        self.combo_layout.setCurrentIndex(max(0, self.combo_layout.findData(init.get("layout", "grid"))))
        form.addRow(tr("serial.layout"), self.combo_layout)

        self.grid_box = QGroupBox(tr("serial.layout_grid"))
        grid_form = QFormLayout(self.grid_box)
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(int(init["cols"]) if self._cols_user and "cols" in init
                                else sd.default_columns(self.spin_count.value()))
        self.spin_gap_x = _spin(0, 200, init.get("gap_x", 5.0), step=0.5)
        self.spin_gap_y = _spin(0, 200, init.get("gap_y", 5.0), step=0.5)
        self.combo_dir = QComboBox()
        self.combo_dir.addItem(tr("serial.dir_up"), True)
        self.combo_dir.addItem(tr("serial.dir_down"), False)
        self.combo_dir.setCurrentIndex(max(0, self.combo_dir.findData(init.get("upward", True))))
        grid_form.addRow(tr("serial.columns"), self.spin_cols)
        grid_form.addRow(tr("serial.gap_x"), self.spin_gap_x)
        grid_form.addRow(tr("serial.gap_y"), self.spin_gap_y)
        grid_form.addRow(tr("serial.direction"), self.combo_dir)
        form.addRow(self.grid_box)

        self.nest_box = QGroupBox(tr("serial.layout_nest"))
        nest_form = QFormLayout(self.nest_box)
        self.spin_sheet_w = _spin(10, 5000, init.get("sheet_w", self._bed_w))
        self.spin_sheet_h = _spin(10, 5000, init.get("sheet_h", self._bed_h))
        self.spin_origin_x = _spin(0, 5000, init.get("origin_x", 0.0))
        self.spin_origin_y = _spin(0, 5000, init.get("origin_y", 0.0))
        self.spin_spacing = _spin(0, 50, init.get("spacing", 2.0), step=0.5)
        self.spin_margin = _spin(0, 100, init.get("margin", 3.0), step=0.5)
        self.combo_rotations = QComboBox()
        for key, name in (("none", "nest.rot_none"), ("flip", "nest.rot_flip"),
                          ("quarters", "nest.rot_quarters"), ("eighths", "nest.rot_eighths")):
            self.combo_rotations.addItem(tr(name), key)
        self.combo_rotations.setCurrentIndex(max(0, self.combo_rotations.findData(init.get("rotations", "none"))))
        self.combo_precision = QComboBox()
        for value, name in ((2.0, "nest.prec_fast"), (1.0, "nest.prec_normal"), (0.5, "nest.prec_precise")):
            self.combo_precision.addItem(tr(name), value)
        self.combo_precision.setCurrentIndex(max(0, self.combo_precision.findData(init.get("cell", 1.0))))
        nest_form.addRow(tr("nest.sheet_w"), self.spin_sheet_w)
        nest_form.addRow(tr("nest.sheet_h"), self.spin_sheet_h)
        nest_form.addRow(tr("nest.origin_x"), self.spin_origin_x)
        nest_form.addRow(tr("nest.origin_y"), self.spin_origin_y)
        nest_form.addRow(tr("nest.spacing"), self.spin_spacing)
        nest_form.addRow(tr("nest.margin"), self.spin_margin)
        nest_form.addRow(tr("nest.rotations"), self.combo_rotations)
        nest_form.addRow(tr("nest.precision"), self.combo_precision)
        self.check_avoid = QCheckBox(tr("serial.avoid_existing"))
        self.check_avoid.setChecked(bool(init.get("avoid_existing", True)))
        self.check_avoid.setToolTip(tr("serial.avoid_existing_tip"))
        nest_form.addRow(self.check_avoid)
        nest_hint = QLabel(tr("serial.nest_hint"))
        nest_hint.setWordWrap(True)
        nest_form.addRow(nest_hint)
        form.addRow(self.nest_box)

        self.label_extent = QLabel()
        self.label_extent.setWordWrap(True)
        form.addRow(self.label_extent)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.buttons = buttons

        self.spin_count.valueChanged.connect(self._on_count_changed)
        self.edit_names.textChanged.connect(self._on_count_changed)
        self.spin_cols.valueChanged.connect(self._on_cols_edited)
        self.combo_layout.currentIndexChanged.connect(self._refresh)
        for w in (self.spin_gap_x, self.spin_gap_y):
            w.valueChanged.connect(self._refresh)
        self._refresh()

    # -- état ---------------------------------------------------------------------------------------------------
    def names(self):
        return sd.parse_names(self.edit_names.toPlainText()) if self._has_text else []

    def count(self):
        return sd.copy_count(self.names(), self.spin_count.value())

    def _on_count_changed(self, *_):
        if not self._cols_user:                      # tant que l'utilisateur n'a pas choisi, grille à peu près carrée
            self.spin_cols.blockSignals(True)
            self.spin_cols.setValue(sd.default_columns(self.count()))
            self.spin_cols.blockSignals(False)
        self._refresh()

    def _on_cols_edited(self, *_):
        self._cols_user = True
        self._refresh()

    def _refresh(self, *_):
        nest = self.combo_layout.currentData() == "nest"
        self.grid_box.setVisible(not nest)
        self.nest_box.setVisible(nest)
        self.spin_count.setEnabled(not self.names())
        n = self.count()
        if nest:
            self.label_extent.setText(tr("serial.count_info").format(count=n))
            self.label_extent.setStyleSheet("")
            return
        w, h = sd.grid_extent(n, self.spin_cols.value(), self._set_w, self._set_h,
                              self.spin_gap_x.value(), self.spin_gap_y.value())
        text = tr("serial.extent").format(count=n, w=f"{w:.0f}", h=f"{h:.0f}")
        too_big = w > self._bed_w + 1e-6 or h > self._bed_h + 1e-6
        if too_big:
            text += "\n" + tr("serial.extent_too_big").format(bed_w=f"{self._bed_w:.0f}", bed_h=f"{self._bed_h:.0f}")
        self.label_extent.setText(text)
        self.label_extent.setStyleSheet("color: #c0392b;" if too_big else "")

    # -- résultats ----------------------------------------------------------------------------------------------
    def params(self):
        """Paramètres pour serial_apply.plan_serial_duplicate."""
        return {
            "count": self.spin_count.value(), "names": self.names(), "text_index": self.text_index(),
            "keep_center": self.check_center.isChecked(), "layout": self.combo_layout.currentData(),
            "cols": self.spin_cols.value(), "gap_x": self.spin_gap_x.value(), "gap_y": self.spin_gap_y.value(),
            "upward": bool(self.combo_dir.currentData()), "avoid_existing": self.check_avoid.isChecked(),
            "nest": {
                "sheet_w": self.spin_sheet_w.value(), "sheet_h": self.spin_sheet_h.value(),
                "origin": (self.spin_origin_x.value(), self.spin_origin_y.value()),
                "spacing": self.spin_spacing.value(), "margin": self.spin_margin.value(),
                "angles": nesting.ANGLE_SETS[self.combo_rotations.currentData()],
                "cell": self.combo_precision.currentData(),
            },
        }

    def text_index(self):
        """Indice (dans la sélection) du texte à personnaliser, ou None s'il n'y a pas de noms."""
        if not self._has_text or not self.names():
            return None
        return self.combo_text.currentData()

    def settings(self):
        """Réglages à mémoriser pour la prochaine ouverture (les noms saisis ne sont pas conservés)."""
        return {
            "count": self.spin_count.value(), "keep_center": self.check_center.isChecked(),
            "layout": self.combo_layout.currentData(), "cols": self.spin_cols.value(), "cols_user": self._cols_user,
            "gap_x": self.spin_gap_x.value(), "gap_y": self.spin_gap_y.value(),
            "upward": bool(self.combo_dir.currentData()), "avoid_existing": self.check_avoid.isChecked(),
            "sheet_w": self.spin_sheet_w.value(), "sheet_h": self.spin_sheet_h.value(),
            "origin_x": self.spin_origin_x.value(), "origin_y": self.spin_origin_y.value(),
            "spacing": self.spin_spacing.value(), "margin": self.spin_margin.value(),
            "rotations": self.combo_rotations.currentData(), "cell": self.combo_precision.currentData(),
        }
