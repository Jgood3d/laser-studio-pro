"""Fenêtre du gabarit de placement : dimensions de l'objet, jeu, nombre de poches, espacements, position de la
plaque et calque de découpe. Les calculs sont dans vector/jig.py, la création des objets dans vector/importers.py."""
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.models.layer_modes import MODE_CUT
from laser_studio.vector import jig as jg


def error_message(error):
    """Texte (traduit) d'une JigError."""
    text = tr(f"jig.err.{error.code}")
    try:
        return text.format(**error.info)
    except (KeyError, IndexError, ValueError):
        return text


def _spin(minimum, maximum, value, decimals=1, step=1.0):
    s = QDoubleSpinBox()
    s.setRange(minimum, maximum)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setSuffix(" mm")
    return s


def _count(minimum, maximum, value):
    s = QSpinBox()
    s.setRange(minimum, maximum)
    s.setValue(int(value))
    return s


class JigDialog(QDialog):
    """Lit : `jig_params()`, `position_mode()`, `position_xy()`, `with_base()`, `cut_layer_id()`, `settings()`."""

    def __init__(self, parent, layers, obj_w, obj_h, has_selection, bed_w_mm, bed_h_mm, initial=None):
        """obj_w / obj_h : dimensions de la sélection (mm), utilisées si has_selection ; sinon valeurs mémorisées."""
        super().__init__(parent)
        init = initial or {}
        self._layers = list(layers)
        self._has_selection = bool(has_selection)
        self.setWindowTitle(tr("jig.title"))
        self.setMinimumWidth(460)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        if self._has_selection:
            info = QLabel(tr("jig.selection_info").format(w=f"{obj_w:.1f}", h=f"{obj_h:.1f}"))
        else:
            info = QLabel(tr("jig.no_selection_info"))
            obj_w, obj_h = init.get("obj_w", 50.0), init.get("obj_h", 25.0)
        info.setWordWrap(True)
        form.addRow(info)

        self.spin_obj_w = _spin(0.1, 2000, obj_w)
        self.spin_obj_h = _spin(0.1, 2000, obj_h)
        self.spin_clearance = _spin(0, 10, init.get("clearance", 0.3), decimals=2, step=0.05)
        self.spin_clearance.setToolTip(tr("jig.clearance_tip"))
        form.addRow(tr("jig.obj_w"), self.spin_obj_w)
        form.addRow(tr("jig.obj_h"), self.spin_obj_h)
        form.addRow(tr("jig.clearance"), self.spin_clearance)

        self.combo_shape = QComboBox()
        self.combo_shape.addItem(tr("jig.shape_rect"), "rect")
        self.combo_shape.addItem(tr("jig.shape_ellipse"), "ellipse")
        self.combo_shape.setCurrentIndex(max(0, self.combo_shape.findData(init.get("shape", "rect"))))
        self.spin_pocket_radius = _spin(0, 200, init.get("pocket_radius", 0.0))
        form.addRow(tr("jig.shape"), self.combo_shape)
        form.addRow(tr("jig.pocket_radius"), self.spin_pocket_radius)

        self.spin_cols = _count(1, 50, init.get("cols", 3))
        self.spin_rows = _count(1, 50, init.get("rows", 2))
        self.spin_gap_x = _spin(0, 200, init.get("gap_x", 6.0), step=0.5)
        self.spin_gap_y = _spin(0, 200, init.get("gap_y", 6.0), step=0.5)
        tip = tr("jig.gap_tip")
        self.spin_gap_x.setToolTip(tip)
        self.spin_gap_y.setToolTip(tip)
        self.combo_dir = QComboBox()
        self.combo_dir.addItem(tr("serial.dir_up"), True)
        self.combo_dir.addItem(tr("serial.dir_down"), False)
        self.combo_dir.setCurrentIndex(max(0, self.combo_dir.findData(init.get("upward", True))))
        form.addRow(tr("jig.cols"), self.spin_cols)
        form.addRow(tr("jig.rows"), self.spin_rows)
        form.addRow(tr("jig.gap_x"), self.spin_gap_x)
        form.addRow(tr("jig.gap_y"), self.spin_gap_y)
        form.addRow(tr("serial.direction"), self.combo_dir)
        sync = QLabel(tr("jig.sync_hint"))
        sync.setWordWrap(True)
        form.addRow(sync)

        self.spin_margin = _spin(0, 200, init.get("margin", 8.0), step=0.5)
        self.spin_plate_radius = _spin(0, 200, init.get("plate_radius", 3.0))
        self.check_base = QCheckBox(tr("jig.base"))
        self.check_base.setChecked(bool(init.get("base", False)))
        form.addRow(tr("jig.margin"), self.spin_margin)
        form.addRow(tr("jig.plate_radius"), self.spin_plate_radius)
        form.addRow(self.check_base)

        self.combo_position = QComboBox()
        if self._has_selection:
            self.combo_position.addItem(tr("jig.pos_beside"), "beside")
            self.combo_position.addItem(tr("jig.pos_around"), "around")
        self.combo_position.addItem(tr("jig.pos_manual"), "manual")
        # Libellés longs : la liste ne doit pas imposer sa largeur à la fenêtre (voir tests/test_widget_widths.py).
        self.combo_position.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_position.setMinimumContentsLength(16)
        self.combo_position.setCurrentIndex(max(0, self.combo_position.findData(init.get("position", "beside"))))
        self.spin_x = _spin(-5000, 5000, init.get("x", 10.0))
        self.spin_y = _spin(-5000, 5000, init.get("y", 10.0))
        form.addRow(tr("jig.position"), self.combo_position)
        form.addRow(tr("jig.x"), self.spin_x)
        form.addRow(tr("jig.y"), self.spin_y)

        self.combo_layer = QComboBox()
        for layer in self._layers:
            self.combo_layer.addItem(layer.name, layer.id)
        self.combo_layer.setCurrentIndex(self._default_layer_index(init.get("layer"), (MODE_CUT,)))
        form.addRow(tr("jig.cut_layer"), self.combo_layer)

        self._bed_w, self._bed_h = float(bed_w_mm), float(bed_h_mm)
        self.label_info = QLabel()
        self.label_info.setWordWrap(True)
        form.addRow(self.label_info)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

        for w in (self.spin_obj_w, self.spin_obj_h, self.spin_clearance, self.spin_pocket_radius, self.spin_gap_x,
                  self.spin_gap_y, self.spin_margin, self.spin_plate_radius):
            w.valueChanged.connect(self._refresh)
        for w in (self.spin_cols, self.spin_rows):
            w.valueChanged.connect(self._refresh)
        for w in (self.combo_shape, self.combo_dir, self.combo_position):
            w.currentIndexChanged.connect(self._refresh)
        self.check_base.toggled.connect(self._refresh)
        self._refresh()

    def _default_layer_index(self, wanted_id, mode_names):
        for i, layer in enumerate(self._layers):
            if wanted_id and layer.id == wanted_id:
                return i
        for i, layer in enumerate(self._layers):
            if getattr(layer, "mode", "") in mode_names:
                return i
        return 0

    def _refresh(self, *_):
        manual = self.combo_position.currentData() == "manual"
        self.spin_x.setEnabled(manual)
        self.spin_y.setEnabled(manual)
        self.spin_pocket_radius.setEnabled(self.combo_shape.currentData() == "rect")
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        try:
            jig = jg.build_jig(self.jig_params())
        except jg.JigError as e:
            self.label_info.setText(error_message(e))
            self.label_info.setStyleSheet("color: #c0392b;")
            ok.setEnabled(False)
            return
        ok.setEnabled(True)
        text = tr("jig.info").format(pw=f"{jig.pocket_w:.1f}", ph=f"{jig.pocket_h:.1f}", w=f"{jig.plate_w:.1f}",
                                     h=f"{jig.plate_h:.1f}", px=f"{jig.pitch_x:.1f}", py=f"{jig.pitch_y:.1f}")
        walls = [w for w, n in ((jig.wall_x, jig.params.cols), (jig.wall_y, jig.params.rows)) if n > 1]
        warn = jig.thin_wall()
        if walls:
            text += "\n" + tr("jig.wall").format(wall=f"{min(walls):.1f}")
        if warn:
            text += "\n" + tr("jig.wall_thin").format(min=f"{jg.MIN_WALL_MM:g}")
        total_w = jig.plate_w * (2 if self.check_base.isChecked() else 1) + (10 if self.check_base.isChecked() else 0)
        too_big = total_w > self._bed_w + 1e-6 or jig.plate_h > self._bed_h + 1e-6
        if too_big:
            text += "\n" + tr("jig.too_big").format(bed_w=f"{self._bed_w:.0f}", bed_h=f"{self._bed_h:.0f}")
        self.label_info.setText(text)
        self.label_info.setStyleSheet("color: #c0392b;" if (warn or too_big) else "")

    # -- résultats ----------------------------------------------------------------------------------------------
    def jig_params(self):
        return jg.JigParams(
            obj_w=self.spin_obj_w.value(), obj_h=self.spin_obj_h.value(), cols=self.spin_cols.value(),
            rows=self.spin_rows.value(), clearance=self.spin_clearance.value(), gap_x=self.spin_gap_x.value(),
            gap_y=self.spin_gap_y.value(), margin=self.spin_margin.value(),
            pocket_shape=self.combo_shape.currentData(), pocket_radius=self.spin_pocket_radius.value(),
            plate_radius=self.spin_plate_radius.value(), upward=bool(self.combo_dir.currentData()))

    def position_mode(self):
        """"beside" | "around" | "manual" (les deux premiers seulement s'il y a une sélection)."""
        return self.combo_position.currentData()

    def position_xy(self):
        return self.spin_x.value(), self.spin_y.value()

    def with_base(self):
        return self.check_base.isChecked()

    def cut_layer_id(self):
        return self.combo_layer.currentData()

    def settings(self):
        """Réglages à mémoriser pour la prochaine ouverture."""
        s = {
            "clearance": self.spin_clearance.value(), "shape": self.combo_shape.currentData(),
            "pocket_radius": self.spin_pocket_radius.value(), "cols": self.spin_cols.value(),
            "rows": self.spin_rows.value(), "gap_x": self.spin_gap_x.value(), "gap_y": self.spin_gap_y.value(),
            "upward": bool(self.combo_dir.currentData()), "margin": self.spin_margin.value(),
            "plate_radius": self.spin_plate_radius.value(), "base": self.check_base.isChecked(),
            "position": self.combo_position.currentData(), "x": self.spin_x.value(), "y": self.spin_y.value(),
            "layer": self.combo_layer.currentData(),
        }
        if not self._has_selection:                      # sans sélection, les dimensions saisies sont mémorisées
            s["obj_w"], s["obj_h"] = self.spin_obj_w.value(), self.spin_obj_h.value()
        return s
