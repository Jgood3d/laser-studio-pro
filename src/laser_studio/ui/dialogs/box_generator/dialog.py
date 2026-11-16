"""Fenêtre du générateur de boîte à encoches : dimensions X/Y/Z, matériau, calques,
couvercle, cloisons, et décor (texte ou SVG) à graver sur les faces, avec un aperçu qui suit les
réglages. Les calculs sont dans vector/box_generator.py, la création des objets dans vector/importers.py."""
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QSlider, QSpinBox, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)

from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL
from laser_studio.vector import box_generator as bg
from laser_studio.vector.box_generator import BoxDecor
from laser_studio.i18n import tr
from laser_studio.vector import box_3d
from laser_studio.vector import box_presets
from laser_studio.ui.dialogs.box_generator.preview import FACE_LABEL_KEYS, BoxPreview
from laser_studio.ui.dialogs.box_generator.preview_3d import Box3DView

LID_LABEL_KEYS = {
    "none": "box.lid_none", "finger": "box.lid_finger", "lip": "box.lid_lip", "sliding": "box.lid_sliding",
    "hinged": "box.lid_hinged", "pinned": "box.lid_pinned",
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


def _ratio_text(ratios):
    return ":".join(f"{r:g}" for r in ratios)


def _parse_ratios(text):
    """'1:2:1' -> (1.0, 2.0, 1.0) ; vide -> () ; illisible -> (0.0,), refusé ensuite par la validation."""
    parts = [x for x in re.split(r"[\s:;,/]+", text.strip()) if x]
    try:
        return tuple(float(x.replace(",", ".")) for x in parts)
    except ValueError:
        return (0.0,)


def _count_spin(value, maximum=bg.MAX_DIVIDERS, minimum=0):
    s = QSpinBox()
    s.setRange(minimum, maximum)
    s.setValue(int(value))
    return s


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
        self.setWindowState(Qt.WindowState.WindowMaximized)          # s'ouvre en grand ; la taille ci-dessus sert à la restauration
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
        body = QHBoxLayout()
        body.addWidget(self.scroll, 1)
        box_preview = QGroupBox(tr("box.group_preview"))
        preview_layout = QVBoxLayout(box_preview)
        self.preview = BoxPreview()
        self.view3d = Box3DView()
        self.view3d.setToolTip(tr("box.view3d_hint"))
        self.slider_open = QSlider(Qt.Orientation.Horizontal)
        self.slider_open.setRange(0, int(box_3d.MAX_OPEN_DEG))
        self.slider_open.valueChanged.connect(self.view3d.set_open_angle)
        self.lbl_open = QLabel(tr("box.open_angle"))
        page_3d = QWidget()
        lay_3d = QVBoxLayout(page_3d)
        lay_3d.addWidget(self.view3d, 1)
        row_open = QHBoxLayout()
        row_open.addWidget(self.lbl_open)
        row_open.addWidget(self.slider_open, 1)
        lay_3d.addLayout(row_open)
        self.slider_explode = QSlider(Qt.Orientation.Horizontal)
        self.slider_explode.setRange(0, 100)
        self.slider_explode.valueChanged.connect(self.view3d.set_explode)
        self.slider_explode.setToolTip(tr("box.explode_tip"))
        self.combo_material = QComboBox()
        for key in box_3d.MATERIALS:
            self.combo_material.addItem(tr(f"box.material_{key}"), key)
        self.combo_material.setCurrentIndex(max(0, self.combo_material.findData(init.get("material", box_3d.DEFAULT_MATERIAL))))
        self.view3d.set_material(self.combo_material.currentData())
        self.combo_material.currentIndexChanged.connect(
            lambda *_: self.view3d.set_material(self.combo_material.currentData()))
        self.btn_export_png = QPushButton(tr("box.export_png"))
        self.btn_export_png.clicked.connect(self._export_png)
        row_view = QHBoxLayout()
        row_view.addWidget(QLabel(tr("box.explode")))
        row_view.addWidget(self.slider_explode, 1)
        row_view.addWidget(QLabel(tr("box.material")))
        row_view.addWidget(self.combo_material)
        row_view.addWidget(self.btn_export_png)
        lay_3d.addLayout(row_view)
        lay_3d.addWidget(QLabel(tr("box.view3d_hint")))
        self.tabs_preview = QTabWidget()
        self.tabs_preview.addTab(self.preview, tr("box.tab_plan"))
        self.tabs_preview.addTab(page_3d, tr("box.tab_3d"))
        preview_layout.addWidget(self.tabs_preview, 1)
        body.addWidget(box_preview, 1)
        outer.addLayout(body, 1)

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
        self.combo_lid = QComboBox()
        for kind in ("finger", "lip", "sliding", "hinged", "pinned", "none"):
            self.combo_lid.addItem(tr(LID_LABEL_KEYS[kind]), kind)
        # Les anciens réglages mémorisés n'ont qu'un booléen « lid » (sans dessus = boîte ouverte).
        wanted_lid = init.get("lid_type", "finger") if init.get("lid", True) else "none"
        self.combo_lid.setCurrentIndex(max(0, self.combo_lid.findData(wanted_lid)))
        self.combo_lid.setToolTip(tr("box.lid_tip"))
        self.spin_hinge = _spin(5.0, bg.MAX_HINGE, init.get("hinge_length", 20.0))
        self.spin_hinge.setToolTip(tr("box.hinge_length_tip"))
        # Charnière à axe : plaques percées empilées autour d'une tige (réglages actifs pour ce type seulement).
        self.spin_hinge_count = _count_spin(init.get("hinge_count", 2), bg.MAX_HINGES, 1)
        self.spin_hinge_plates = _count_spin(init.get("hinge_plates", 3), 9, 3)
        self.spin_hinge_plates.setSingleStep(2)                       # toujours impair : 3, 5, 7, 9
        self.spin_hinge_plates.setToolTip(tr("box.hinge_plates_tip"))
        self.spin_pin = _spin(0.5, 12.0, init.get("pin_diameter", 3.0), decimals=1, step=0.5)
        self.spin_pin.setToolTip(tr("box.pin_diameter_tip"))
        self.combo_style = QComboBox()
        for style, key in (("round", "box.hinge_style_round"), ("butterfly", "box.hinge_style_butterfly")):
            self.combo_style.addItem(tr(key), style)
        self.combo_style.setCurrentIndex(max(0, self.combo_style.findData(init.get("hinge_style", "round"))))
        self.combo_style.setToolTip(tr("box.hinge_style_tip"))
        self.spin_plate_radius = _spin(0.0, 25.0, init.get("plate_radius", 0.0), decimals=1, step=0.5)
        self.spin_plate_radius.setSpecialValueText(tr("box.plate_auto"))
        self.spin_plate_radius.setToolTip(tr("box.plate_radius_tip"))
        self.chk_through = QCheckBox(tr("box.pin_through"))
        self.chk_through.setChecked(bool(init.get("pin_through", True)))
        self.chk_through.setToolTip(tr("box.pin_through_tip"))
        self.spin_fit = _spin(0.0, 2.0, init.get("pin_fit", 0.1), decimals=2, step=0.05)
        self.spin_fit.setToolTip(tr("box.pin_fit_tip"))
        self.chk_handle = QCheckBox(tr("box.handle"))
        self.chk_handle.setChecked(bool(init.get("handle", False)))
        self.chk_handle.setToolTip(tr("box.handle_tip"))
        self.spin_handle = _spin(1.0, 100.0, init.get("handle_radius", 10.0), decimals=1, step=0.5)
        self.chk_motif = QCheckBox(tr("box.motif"))
        self.chk_motif.setChecked(bool(init.get("engrave_motif", False)))
        self.chk_motif.setToolTip(tr("box.motif_tip"))
        self.spin_motif = _spin(8.0, 300.0, init.get("motif_size", 30.0), decimals=1, step=1.0)
        self.combo_motif = QComboBox()
        for shape in bg.MOTIF_SHAPES:
            self.combo_motif.addItem(tr(f"box.motif_{shape}"), shape)
        self.combo_motif.setCurrentIndex(max(0, self.combo_motif.findData(init.get("motif_shape", "butterfly"))))
        self.chk_index = QCheckBox(tr("box.index"))
        self.chk_index.setChecked(bool(init.get("engrave_index", False)))
        self.chk_index.setToolTip(tr("box.index_tip"))
        self.spin_index = _spin(2.0, 15.0, init.get("index_size", 4.0), decimals=1, step=0.5)
        self.chk_magnets = QCheckBox(tr("box.magnets"))
        self.chk_magnets.setChecked(bool(init.get("magnets", False)))
        self.chk_magnets.setToolTip(tr("box.magnets_tip"))
        self.spin_magnet_d = _spin(3.0, 20.0, init.get("magnet_diameter", 6.0), decimals=1, step=0.5)
        self.spin_magnet_n = _count_spin(init.get("magnet_count", 2), bg.MAX_MAGNETS, 1)
        self.spin_clearance = _spin(0.0, 2.0, init.get("clearance", 0.1), decimals=2, step=0.05)
        self.spin_clearance.setToolTip(tr("box.clearance_tip"))
        self.spin_gap = _spin(0.5, 50, init.get("gap", 3.0))
        form.addRow(tr("box.dimensions_are"), self.combo_mode)
        form.addRow(tr("box.width_x"), self.spin_x)
        form.addRow(tr("box.depth_y"), self.spin_y)
        form.addRow(tr("box.height_z"), self.spin_z)
        form.addRow(tr("box.thickness"), self.spin_thickness)
        form.addRow(tr("box.kerf"), self.spin_kerf)
        form.addRow(tr("box.finger"), self.spin_finger)
        form.addRow(tr("box.clearance"), self.spin_clearance)
        form.addRow(tr("box.gap"), self.spin_gap)
        box_presets_ui = QGroupBox(tr("box.group_presets"))
        play = QHBoxLayout(box_presets_ui)
        self.combo_preset = QComboBox()
        self.edit_preset_name = QLineEdit()
        self.edit_preset_name.setPlaceholderText(tr("box.preset_name_placeholder"))
        self.btn_preset_load = QPushButton(tr("box.preset_load"))
        self.btn_preset_save = QPushButton(tr("box.preset_save"))
        self.btn_preset_delete = QPushButton(tr("box.preset_delete"))
        self.btn_preset_load.clicked.connect(self._load_preset)
        self.btn_preset_save.clicked.connect(self._save_preset)
        self.btn_preset_delete.clicked.connect(self._delete_preset)
        for w in (self.combo_preset, self.btn_preset_load, self.edit_preset_name, self.btn_preset_save,
                  self.btn_preset_delete):
            play.addWidget(w, 1 if w is self.combo_preset else 0)
        self._preset_file = None                       # None : fichier par défaut du dossier utilisateur
        self._fill_presets()
        main.addWidget(box_presets_ui)
        main.addWidget(box_dims)

        # ---- Couvercle : type, charnière, fermeture ----
        box_lid = QGroupBox(tr("box.group_lid"))
        lidform = QFormLayout(box_lid)
        lidform.addRow(tr("box.lid_type"), self.combo_lid)
        lidform.addRow(tr("box.hinge_length"), self.spin_hinge)
        lidform.addRow(tr("box.hinge_count"), self.spin_hinge_count)
        lidform.addRow(tr("box.hinge_plates"), self.spin_hinge_plates)
        lidform.addRow(tr("box.pin_diameter"), self.spin_pin)
        lidform.addRow(tr("box.hinge_style"), self.combo_style)
        lidform.addRow(tr("box.plate_radius"), self.spin_plate_radius)
        lidform.addRow(self.chk_through)
        lidform.addRow(tr("box.pin_fit"), self.spin_fit)
        lidform.addRow(self.chk_handle)
        lidform.addRow(tr("box.handle_radius"), self.spin_handle)
        lidform.addRow(self.chk_magnets)
        lidform.addRow(tr("box.magnet_diameter"), self.spin_magnet_d)
        lidform.addRow(tr("box.magnet_count"), self.spin_magnet_n)
        self.lbl_lid_hint = QLabel()                                   # pourquoi une option est grisée
        self.lbl_lid_hint.setWordWrap(True)
        lidform.addRow(self.lbl_lid_hint)
        main.addWidget(box_lid)

        # ---- Gravure automatique ----
        box_engrave = QGroupBox(tr("box.group_engrave"))
        engform = QFormLayout(box_engrave)
        engform.addRow(self.chk_motif)
        engform.addRow(tr("box.motif_shape"), self.combo_motif)
        engform.addRow(tr("box.motif_size"), self.spin_motif)
        engform.addRow(self.chk_index)
        engform.addRow(tr("box.index_size"), self.spin_index)
        main.addWidget(box_engrave)

        # ---- Cloisons ----
        box_dividers = QGroupBox(tr("box.group_dividers"))
        box_dividers.setToolTip(tr("box.dividers_tip"))
        dform_div = QFormLayout(box_dividers)
        self.spin_div_x = _count_spin(init.get("dividers_x", 0))
        self.spin_div_y = _count_spin(init.get("dividers_y", 0))
        dform_div.addRow(tr("box.dividers_x"), self.spin_div_x)
        dform_div.addRow(tr("box.dividers_y"), self.spin_div_y)
        self.edit_ratio_x = QLineEdit(_ratio_text(init.get("ratios_x", ())))
        self.edit_ratio_y = QLineEdit(_ratio_text(init.get("ratios_y", ())))
        for edit in (self.edit_ratio_x, self.edit_ratio_y):
            edit.setPlaceholderText(tr("box.ratios_placeholder"))
            edit.setToolTip(tr("box.ratios_tip"))
            edit.textChanged.connect(self._refresh_summary)
        dform_div.addRow(tr("box.ratios_x"), self.edit_ratio_x)
        dform_div.addRow(tr("box.ratios_y"), self.edit_ratio_y)
        main.addWidget(box_dividers)
        box_feet = QGroupBox(tr("box.group_feet"))
        fform = QFormLayout(box_feet)
        self.chk_feet = QCheckBox(tr("box.feet"))
        self.chk_feet.setChecked(bool(init.get("feet", False)))
        self.chk_feet.setToolTip(tr("box.feet_tip"))
        self.spin_foot_size = _spin(8.0, 100.0, init.get("foot_size", 15.0), decimals=1, step=1.0)
        self.spin_foot_layers = _count_spin(init.get("foot_layers", 2), 4, 1)
        fform.addRow(self.chk_feet)
        fform.addRow(tr("box.foot_size"), self.spin_foot_size)
        fform.addRow(tr("box.foot_layers"), self.spin_foot_layers)
        main.addWidget(box_feet)

        # ---- Calques ----
        box_layers = QGroupBox(tr("box.group_layers"))
        lform = QFormLayout(box_layers)
        self.combo_cut_layer = QComboBox()
        self.combo_engrave_layer = QComboBox()
        for layer in self._layers:
            self.combo_cut_layer.addItem(layer.name, layer.id)
            self.combo_engrave_layer.addItem(layer.name, layer.id)
        self.combo_cut_layer.setCurrentIndex(self._default_layer_index(init.get("cut_layer"), (MODE_CUT,)))
        self.combo_engrave_layer.setCurrentIndex(self._default_layer_index(init.get("engrave_layer"), (MODE_FILL,)))
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
                     self.spin_finger, self.spin_gap, self.spin_clearance, self.spin_div_x, self.spin_div_y,
                     self.spin_hinge, self.spin_hinge_count, self.spin_hinge_plates, self.spin_pin,
                     self.spin_plate_radius, self.spin_fit, self.spin_handle, self.spin_motif, self.spin_index,
                     self.spin_magnet_d, self.spin_magnet_n, self.spin_foot_size, self.spin_foot_layers):
            spin.valueChanged.connect(self._refresh_summary)
        for box in (self.chk_feet, self.chk_through, self.chk_handle, self.chk_motif, self.chk_index, self.chk_magnets):
            box.toggled.connect(self._refresh_summary)
        self.combo_style.currentIndexChanged.connect(self._refresh_summary)
        self.combo_motif.currentIndexChanged.connect(self._refresh_summary)
        self.combo_mode.currentIndexChanged.connect(self._refresh_summary)
        self.combo_lid.currentIndexChanged.connect(self._refresh_summary)
        self._refresh_summary()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Préréglages et export
    # ------------------------------------------------------------------
    def _fill_presets(self, select=None):
        self.combo_preset.clear()
        for key in box_presets.BUILTIN:
            self.combo_preset.addItem(tr(f"box.preset_{key}"), ("builtin", key))
        for name in box_presets.load_user(self._preset_file):
            self.combo_preset.addItem(name, ("user", name))
        if select is not None:
            self.combo_preset.setCurrentIndex(max(0, self.combo_preset.findData(select)))

    def _load_preset(self):
        data = self.combo_preset.currentData()
        if not data:
            return
        kind, key = data
        values = box_presets.BUILTIN.get(key) if kind == "builtin" else box_presets.load_user(self._preset_file).get(key)
        if values:
            self.apply_settings(values)

    def _save_preset(self):
        name = self.edit_preset_name.text().strip()
        if name and box_presets.save_user(name, self.settings(), self._preset_file):
            self._fill_presets(select=("user", name))

    def _delete_preset(self):
        data = self.combo_preset.currentData()
        if data and data[0] == "user" and box_presets.delete_user(data[1], self._preset_file):
            self._fill_presets()

    def apply_settings(self, s):
        """Applique des réglages (préréglage) aux champs ; les clés absentes gardent leur valeur actuelle."""
        spins = {"width": self.spin_x, "depth": self.spin_y, "height": self.spin_z, "thickness": self.spin_thickness,
                 "kerf": self.spin_kerf, "finger_width": self.spin_finger, "clearance": self.spin_clearance,
                 "dividers_x": self.spin_div_x, "dividers_y": self.spin_div_y, "hinge_length": self.spin_hinge,
                 "hinge_count": self.spin_hinge_count, "hinge_plates": self.spin_hinge_plates,
                 "pin_diameter": self.spin_pin, "plate_radius": self.spin_plate_radius, "pin_fit": self.spin_fit,
                 "handle_radius": self.spin_handle, "motif_size": self.spin_motif, "index_size": self.spin_index,
                 "foot_size": self.spin_foot_size, "foot_layers": self.spin_foot_layers,
                 "magnet_diameter": self.spin_magnet_d, "magnet_count": self.spin_magnet_n, "gap": self.spin_gap}
        checks = {"pin_through": self.chk_through, "handle": self.chk_handle, "engrave_motif": self.chk_motif,
                  "engrave_index": self.chk_index, "magnets": self.chk_magnets, "feet": self.chk_feet}
        combos = {"dimensions": self.combo_mode, "lid_type": self.combo_lid, "hinge_style": self.combo_style,
                  "motif_shape": self.combo_motif, "material": self.combo_material}
        for key, widget in spins.items():
            if key in s:
                widget.setValue(s[key])
        for key, widget in checks.items():
            if key in s:
                widget.setChecked(bool(s[key]))
        for key, edit in (("ratios_x", self.edit_ratio_x), ("ratios_y", self.edit_ratio_y)):
            if key in s:
                edit.setText(_ratio_text(s[key]))
        for key, widget in combos.items():
            if key in s and widget.findData(s[key]) >= 0:
                widget.setCurrentIndex(widget.findData(s[key]))
        self._refresh_summary()

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("box.export_png"), "boite.png", tr("box.png_filter"))
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.view3d.save_png(path)

    def _fit_to_screen(self):
        """Taille initiale : au plus 85 % de la hauteur disponible de l'écran."""
        try:
            height = int(self.screen().availableGeometry().height() * 0.85)
        except (AttributeError, TypeError):
            height = 700
        try:
            width = int(self.screen().availableGeometry().width() * 0.85)
        except (AttributeError, TypeError):
            width = 1000
        self.resize(min(max(width, 700), 1100), min(max(height, 420), 900))

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
            lid=self.combo_lid.currentData() != "none", lid_type=self._lid_type(), gap=self.spin_gap.value(),
            max_width=max(self._bed_w - 20.0, 0.0), clearance=self.spin_clearance.value(),
            dividers_x=self.spin_div_x.value(), dividers_y=self.spin_div_y.value(),
            feet=self.chk_feet.isChecked(), foot_size=self.spin_foot_size.value(),
            foot_layers=self.spin_foot_layers.value(),
            ratios_x=_parse_ratios(self.edit_ratio_x.text()), ratios_y=_parse_ratios(self.edit_ratio_y.text()),
            hinge_length=self.spin_hinge.value(), hinge_count=self.spin_hinge_count.value(),
            hinge_plates=self.spin_hinge_plates.value(), pin_diameter=self.spin_pin.value(),
            hinge_style=self.combo_style.currentData(), plate_radius=self.spin_plate_radius.value(),
            pin_through=self.chk_through.isChecked(), pin_fit=self.spin_fit.value(),
            handle=self.chk_handle.isChecked() and self._lid_type() in bg.HANDLE_LIDS and self.combo_lid.currentData() != "none",
            handle_radius=self.spin_handle.value(),
            engrave_motif=self.chk_motif.isChecked() and self.combo_lid.currentData() != "none",
            motif_size=self.spin_motif.value(), motif_shape=self.combo_motif.currentData(), engrave_index=self.chk_index.isChecked(),
            index_size=self.spin_index.value(),
            magnets=self.chk_magnets.isChecked() and self.combo_lid.currentData() in bg.MAGNET_LIDS,
            magnet_diameter=self.spin_magnet_d.value(), magnet_count=self.spin_magnet_n.value(),
        )

    def _lid_type(self):
        """Type de couvercle choisi ; « finger » (valeur neutre) quand la boîte est ouverte."""
        kind = self.combo_lid.currentData()
        return "finger" if kind == "none" else kind

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
                "lid": p.lid, "lid_type": self.combo_lid.currentData(), "clearance": p.clearance,
                "dividers_x": p.dividers_x, "dividers_y": p.dividers_y,
                "feet": p.feet, "foot_size": p.foot_size, "foot_layers": p.foot_layers,
                "ratios_x": list(p.ratios_x), "ratios_y": list(p.ratios_y), "hinge_length": p.hinge_length,
                "hinge_count": p.hinge_count, "hinge_plates": p.hinge_plates, "pin_diameter": p.pin_diameter,
                "hinge_style": p.hinge_style, "plate_radius": p.plate_radius, "pin_through": p.pin_through,
                "pin_fit": p.pin_fit, "handle": self.chk_handle.isChecked(), "handle_radius": p.handle_radius,
                "engrave_motif": self.chk_motif.isChecked(), "motif_size": p.motif_size,
                "motif_shape": p.motif_shape, "material": self.combo_material.currentData(),
                "engrave_index": p.engrave_index, "index_size": p.index_size,
                "magnets": self.chk_magnets.isChecked(), "magnet_diameter": p.magnet_diameter,
                "magnet_count": p.magnet_count,
                "gap": p.gap,
                "cut_layer": self.cut_layer_id(),
                "engrave_layer": self.engrave_layer_id(), "decors": self.decors()}

    # ------------------------------------------------------------------
    def _refresh_summary(self, *_args):
        kind = self.combo_lid.currentData()
        self.spin_hinge.setEnabled(kind == "hinged")                  # réglages propres à chaque charnière
        for widget in (self.spin_hinge_count, self.spin_hinge_plates, self.spin_pin, self.combo_style,
                       self.spin_plate_radius, self.chk_through, self.spin_fit):
            widget.setEnabled(kind == "pinned")
        openable = kind in box_3d.OPENABLE_LIDS                       # le couvercle s'ouvre dans l'aperçu 3D
        self.slider_open.setEnabled(openable)
        self.lbl_open.setEnabled(openable)
        has_lid = kind != "none"
        self.chk_motif.setEnabled(has_lid)
        self.spin_motif.setEnabled(has_lid and self.chk_motif.isChecked())
        self.combo_motif.setEnabled(has_lid and self.chk_motif.isChecked())
        self.spin_index.setEnabled(self.chk_index.isChecked())
        can_magnet = kind in bg.MAGNET_LIDS                           # couvercles plats posés sur la façade
        self.chk_magnets.setEnabled(can_magnet)
        for widget in (self.spin_magnet_d, self.spin_magnet_n):
            widget.setEnabled(can_magnet and self.chk_magnets.isChecked())
        can_handle = kind in bg.HANDLE_LIDS                           # pas avec le couvercle à doigts ni sans couvercle
        self.chk_handle.setEnabled(can_handle)
        self.spin_handle.setEnabled(can_handle and self.chk_handle.isChecked())
        hints = []
        if not can_magnet:
            hints.append(tr("box.magnets_hint"))
        if not can_handle:
            hints.append(tr("box.handle_hint"))
        self.lbl_lid_hint.setText("<i>" + " ".join(hints) + "</i>" if hints else "")
        try:
            result = bg.build_box(self.params())
        except bg.BoxError as exc:
            message = error_message(exc)
            self.lbl_summary.setText(f"<span style='color:#d9534f'>{message}</span>")
            self.preview.set_error(message)
            self.view3d.set_error(message)
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            return
        W, D, H = result.outer
        counts = result.finger_counts
        text = tr("box.summary").format(
            w=W, d=D, h=H, n=len(result.panels), fx=counts["W"], fy=counts["D"], fz=counts["H"],
            fw=result.width, fh=result.height)
        if sum(result.dividers):
            nx, ny = result.dividers
            t = result.thickness
            text += " " + tr("box.summary_dividers").format(
                count=(nx + 1) * (ny + 1), cw=((W - 2 * t) - nx * t) / (nx + 1), cd=((D - 2 * t) - ny * t) / (ny + 1))
        if result.pin:
            count, diameter, length = result.pin
            text += " " + tr("box.summary_pin_through" if count == 1 and self.chk_through.isChecked()
                             else "box.summary_pin").format(n=count, d=diameter, l=length)
        if result.magnets:
            text += " " + tr("box.summary_magnets").format(n=result.magnets[0], d=result.magnets[1])
        too_big = result.width > self._bed_w - 20.0 + 1e-6 or result.height > self._bed_h - 20.0 + 1e-6
        self.preview.set_result(result, self.decors(), too_big)
        self.view3d.set_box(self.params(), result)
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
            self._refresh_summary()

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
            self._refresh_summary()
