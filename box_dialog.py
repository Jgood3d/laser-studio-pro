"""Fenêtre du générateur de boîte à encoches : dimensions X/Y/Z, matériau, calques,
et décor (texte ou SVG) à graver sur les faces. Les calculs sont dans box_generator.py,
la création des objets dans vector_import.py."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

import box_generator as bg
from box_generator import BoxDecor
from i18n import tr

FACE_LABEL_KEYS = {
    "front": "box.face_front", "back": "box.face_back", "left": "box.face_left",
    "right": "box.face_right", "top": "box.face_top", "bottom": "box.face_bottom",
}
_ROLE = Qt.ItemDataRole.UserRole


def error_message(error):
    """Texte (traduit) d'une BoxError."""
    key = f"box.err.{error.code}"
    text = tr(key)
    if text == key:                      # code inconnu : message générique
        text = tr("box.err.generic")
    try:
        return text.format(**error.info)
    except (KeyError, IndexError, ValueError):
        return text


def _spin(minimum, maximum, value, decimals=1, step=1.0, suffix=" mm"):
    s = QDoubleSpinBox()
    s.setRange(minimum, maximum)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    if suffix:
        s.setSuffix(suffix)
    return s


class BoxGeneratorDialog(QDialog):
    """Saisie des paramètres de la boîte ; `params()`, `decors()` et les calques choisis sont lus après acceptation."""

    def __init__(self, parent, layers, bed_w_mm, bed_h_mm, initial=None):
        super().__init__(parent)
        self.setWindowTitle(tr("box.title"))
        self.setMinimumWidth(520)
        self._fit_to_screen()
        self._layers = list(layers)
        self._bed_w = float(bed_w_mm)
        self._bed_h = float(bed_h_mm)
        init = initial or {}

        # Le contenu défile : sur un écran peu haut, la fenêtre entière dépassait de l'écran et les
        # boutons Valider / Annuler devenaient inaccessibles. Résumé et boutons restent donc HORS de
        # la zone qui défile, toujours visibles en bas de la fenêtre.
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        main = QVBoxLayout(content)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)

        # ---- Dimensions et matériau ----
        box_dims = QGroupBox(tr("box.group_dimensions"))
        form = QFormLayout(box_dims)
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(tr("box.mode_outer"), "outer")
        self.combo_mode.addItem(tr("box.mode_inner"), "inner")
        self.combo_mode.setCurrentIndex(max(0, self.combo_mode.findData(init.get("dimensions", "outer"))))
        self.spin_x = _spin(10, 2000, init.get("width", 100.0))
        self.spin_y = _spin(10, 2000, init.get("depth", 70.0))
        self.spin_z = _spin(10, 2000, init.get("height", 50.0))
        self.spin_thickness = _spin(0.5, 25, init.get("thickness", 3.0), decimals=2, step=0.1)
        self.spin_kerf = _spin(0.0, 2.0, init.get("kerf", 0.1), decimals=2, step=0.01)
        self.spin_kerf.setToolTip(tr("box.kerf_tip"))
        self.spin_finger = _spin(0.0, 200, init.get("finger_width", 0.0))
        self.spin_finger.setSpecialValueText(tr("box.finger_auto"))
        self.spin_finger.setToolTip(tr("box.finger_tip"))
        self.chk_lid = QCheckBox(tr("box.lid"))
        self.chk_lid.setChecked(init.get("lid", True))
        self.spin_gap = _spin(0.5, 50, init.get("gap", 3.0))
        form.addRow(tr("box.dimensions_are"), self.combo_mode)
        form.addRow(tr("box.width_x"), self.spin_x)
        form.addRow(tr("box.depth_y"), self.spin_y)
        form.addRow(tr("box.height_z"), self.spin_z)
        form.addRow(tr("box.thickness"), self.spin_thickness)
        form.addRow(tr("box.kerf"), self.spin_kerf)
        form.addRow(tr("box.finger"), self.spin_finger)
        form.addRow("", self.chk_lid)
        form.addRow(tr("box.gap"), self.spin_gap)
        main.addWidget(box_dims)

        # ---- Calques ----
        box_layers = QGroupBox(tr("box.group_layers"))
        lform = QFormLayout(box_layers)
        self.combo_cut_layer = QComboBox()
        self.combo_engrave_layer = QComboBox()
        for layer in self._layers:
            self.combo_cut_layer.addItem(layer.name, layer.id)
            self.combo_engrave_layer.addItem(layer.name, layer.id)
        self.combo_cut_layer.setCurrentIndex(self._default_layer_index(init.get("cut_layer"), ("Découpe", "Cut")))
        self.combo_engrave_layer.setCurrentIndex(self._default_layer_index(init.get("engrave_layer"), ("Gravure Remplie", "Fill")))
        lform.addRow(tr("box.cut_layer"), self.combo_cut_layer)
        lform.addRow(tr("box.engrave_layer"), self.combo_engrave_layer)
        main.addWidget(box_layers)

        # ---- Décor ----
        box_decor = QGroupBox(tr("box.group_decor"))
        dlay = QVBoxLayout(box_decor)
        dform = QFormLayout()
        self.combo_face = QComboBox()
        for face in bg.FACE_NAMES:
            self.combo_face.addItem(tr(FACE_LABEL_KEYS[face]), face)
        self.combo_face.setCurrentIndex(max(0, self.combo_face.findData("front")))
        self.combo_decor_kind = QComboBox()
        self.combo_decor_kind.addItem(tr("box.decor_text"), "text")
        self.combo_decor_kind.addItem(tr("box.decor_svg"), "svg")
        dform.addRow(tr("box.decor_face"), self.combo_face)
        dform.addRow(tr("box.decor_kind"), self.combo_decor_kind)
        dlay.addLayout(dform)

        self.stack_decor = QStackedWidget()
        page_text = QWidget()
        tform = QFormLayout(page_text)
        self.edit_decor_text = QLineEdit()
        self.edit_decor_text.setPlaceholderText(tr("box.decor_text_placeholder"))
        self.combo_decor_font = QFontComboBox()
        self.spin_decor_size = _spin(2, 300, 10.0)
        self.chk_decor_bold = QCheckBox(tr("vector.dlg.bold"))
        self.chk_decor_italic = QCheckBox(tr("vector.dlg.italic"))
        style_row = QHBoxLayout()
        style_row.addWidget(self.chk_decor_bold)
        style_row.addWidget(self.chk_decor_italic)
        tform.addRow(tr("vector.dlg.text_label"), self.edit_decor_text)
        tform.addRow(tr("vector.dlg.font"), self.combo_decor_font)
        tform.addRow(tr("vector.dlg.size_height"), self.spin_decor_size)
        tform.addRow(tr("vector.dlg.style"), style_row)
        self.stack_decor.addWidget(page_text)

        page_svg = QWidget()
        sform = QFormLayout(page_svg)
        self.edit_decor_svg = QLineEdit()
        self.edit_decor_svg.setReadOnly(True)
        btn_browse = QPushButton(tr("box.decor_browse"))
        btn_browse.clicked.connect(self._browse_svg)
        svg_row = QHBoxLayout()
        svg_row.addWidget(self.edit_decor_svg, 1)
        svg_row.addWidget(btn_browse)
        self.spin_decor_width = _spin(0.0, 1000, 0.0)
        self.spin_decor_width.setSpecialValueText(tr("box.decor_width_original"))
        sform.addRow(tr("box.decor_svg_file"), svg_row)
        sform.addRow(tr("box.decor_width"), self.spin_decor_width)
        self.stack_decor.addWidget(page_svg)
        dlay.addWidget(self.stack_decor)
        self.combo_decor_kind.currentIndexChanged.connect(self.stack_decor.setCurrentIndex)

        pos_row = QHBoxLayout()
        self.spin_decor_dx = _spin(-500, 500, 0.0)
        self.spin_decor_dy = _spin(-500, 500, 0.0)
        pos_row.addWidget(QLabel(tr("box.decor_dx")))
        pos_row.addWidget(self.spin_decor_dx)
        pos_row.addWidget(QLabel(tr("box.decor_dy")))
        pos_row.addWidget(self.spin_decor_dy)
        dlay.addLayout(pos_row)

        btn_row = QHBoxLayout()
        btn_add = QPushButton(tr("box.decor_add"))
        btn_add.clicked.connect(self._add_decor)
        btn_remove = QPushButton(tr("box.decor_remove"))
        btn_remove.clicked.connect(self._remove_decor)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        dlay.addLayout(btn_row)
        self.list_decor = QListWidget()
        self.list_decor.setMaximumHeight(90)
        dlay.addWidget(self.list_decor)
        main.addWidget(box_decor)
        for decor in init.get("decors", []):
            self._append_decor_item(decor)

        # ---- Résumé et validation ----
        self.lbl_summary = QLabel()
        self.lbl_summary.setWordWrap(True)
        outer.addWidget(self.lbl_summary)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

        for spin in (self.spin_x, self.spin_y, self.spin_z, self.spin_thickness, self.spin_kerf,
                     self.spin_finger, self.spin_gap):
            spin.valueChanged.connect(self._refresh_summary)
        self.combo_mode.currentIndexChanged.connect(self._refresh_summary)
        self.chk_lid.toggled.connect(self._refresh_summary)
        self._refresh_summary()

    # ------------------------------------------------------------------
    def _fit_to_screen(self):
        """Taille initiale : au plus 85 % de la hauteur disponible de l'écran."""
        try:
            height = int(self.screen().availableGeometry().height() * 0.85)
        except (AttributeError, TypeError):
            height = 700
        self.resize(560, min(max(height, 420), 900))

    def _default_layer_index(self, wanted_id, mode_names):
        for i, layer in enumerate(self._layers):
            if wanted_id and layer.id == wanted_id:
                return i
        for i, layer in enumerate(self._layers):
            if getattr(layer, "mode", "") in mode_names:
                return i
        return 0

    def params(self):
        return bg.BoxParams(
            width=self.spin_x.value(), depth=self.spin_y.value(), height=self.spin_z.value(),
            thickness=self.spin_thickness.value(), kerf=self.spin_kerf.value(),
            finger_width=self.spin_finger.value(), dimensions=self.combo_mode.currentData(),
            lid=self.chk_lid.isChecked(), gap=self.spin_gap.value(),
            max_width=max(self._bed_w - 20.0, 0.0),
        )

    def cut_layer_id(self):
        return self.combo_cut_layer.currentData()

    def engrave_layer_id(self):
        return self.combo_engrave_layer.currentData()

    def decors(self):
        return [self.list_decor.item(i).data(_ROLE) for i in range(self.list_decor.count())]

    def settings(self):
        """Valeurs à réafficher à la prochaine ouverture."""
        p = self.params()
        return {"width": p.width, "depth": p.depth, "height": p.height, "thickness": p.thickness,
                "kerf": p.kerf, "finger_width": p.finger_width, "dimensions": p.dimensions,
                "lid": p.lid, "gap": p.gap, "cut_layer": self.cut_layer_id(),
                "engrave_layer": self.engrave_layer_id(), "decors": self.decors()}

    # ------------------------------------------------------------------
    def _refresh_summary(self, *_args):
        try:
            result = bg.build_box(self.params())
        except bg.BoxError as exc:
            self.lbl_summary.setText(f"<span style='color:#d9534f'>{error_message(exc)}</span>")
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        W, D, H = result.outer
        counts = result.finger_counts
        text = tr("box.summary").format(
            w=W, d=D, h=H, n=len(result.panels), fx=counts["W"], fy=counts["D"], fz=counts["H"],
            fw=result.width, fh=result.height)
        too_big = result.width > self._bed_w - 20.0 + 1e-6 or result.height > self._bed_h - 20.0 + 1e-6
        if too_big:
            text += "<br><span style='color:#f0ad4e'>" + tr("box.too_big").format(bed_w=self._bed_w, bed_h=self._bed_h) + "</span>"
        self.lbl_summary.setText(text)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _browse_svg(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("box.decor_svg_file"), "", tr("box.svg_filter"))
        if path:
            self.edit_decor_svg.setText(path)

    def _current_decor(self):
        face = self.combo_face.currentData()
        dx, dy = self.spin_decor_dx.value(), self.spin_decor_dy.value()
        if self.combo_decor_kind.currentData() == "svg":
            path = self.edit_decor_svg.text().strip()
            if not path:
                return None
            return BoxDecor(face=face, kind="svg", svg_path=path, width_mm=self.spin_decor_width.value(), dx=dx, dy=dy)
        text = self.edit_decor_text.text()
        if not text.strip():
            return None
        return BoxDecor(face=face, kind="text", text=text, font_family=self.combo_decor_font.currentFont().family(),
                        size_mm=self.spin_decor_size.value(), bold=self.chk_decor_bold.isChecked(),
                        italic=self.chk_decor_italic.isChecked(), dx=dx, dy=dy)

    def _add_decor(self):
        decor = self._current_decor()
        if decor is not None:
            self._append_decor_item(decor)

    def _append_decor_item(self, decor):
        face = tr(FACE_LABEL_KEYS[decor.face])
        what = decor.text if decor.kind == "text" else decor.svg_path.replace("\\", "/").split("/")[-1]
        item = QListWidgetItem(f"{face} — {what}")
        item.setData(_ROLE, decor)
        self.list_decor.addItem(item)

    def _remove_decor(self):
        row = self.list_decor.currentRow()
        if row >= 0:
            self.list_decor.takeItem(row)
