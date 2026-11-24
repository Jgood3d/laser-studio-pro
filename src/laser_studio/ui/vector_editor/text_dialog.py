"""Boîte d'insertion et de modification d'un texte (TextInsertDialog)."""
import math
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QFormLayout, QPushButton, QLabel, QComboBox, QDoubleSpinBox, QCheckBox, QDialog,
    QDialogButtonBox, QLineEdit, QFontComboBox, QRadioButton, QButtonGroup, QInputDialog,
)
from laser_studio.i18n import tr
from laser_studio.vector.text_on_arc import default_center_deg
from laser_studio.vector.text_on_path import (
    default_center_fraction, is_closed, path_length, place_for_fraction, side_center_fraction,
    spacing_to_span, ANCHORS,
)
from laser_studio.vector import text_presets
from laser_studio.models.layers import LayersModel, layer_label
from laser_studio.models.vector_objects import TextObject

# Ancien nom du modèle des calques (models/layers.py).


class TextInsertDialog(QDialog):
    """Boîte de dialogue façon LightBurn pour insérer/éditer un objet texte."""

    # Position d'un texte sur un cercle selon le côté choisi (degrés, 90 = haut, 270 = bas).
    _ARC_SIDE_DEG = {"top": 90.0, "bottom": 270.0, "left": 180.0, "right": 0.0}

    def __init__(self, layer_manager: LayersModel, text_obj: TextObject = None, parent=None, on_preview=None,
                 is_new=False):
        """`on_preview` : appelé après chaque réglage d'un texte déjà posé, pour redessiner l'objet pendant
        que la boîte est ouverte (aperçu en direct). L'objet est remis dans son état d'origine à la
        fermeture : l'appelant applique ensuite `get_object()` si la boîte est acceptée.
        `is_new` : le texte vient d'être posé sur le canevas pour l'aperçu (il n'existait pas avant la boîte)."""
        super().__init__(parent)
        self.setWindowTitle(tr("vector.dlg.text_title_new") if (text_obj is None or is_new)
                            else tr("vector.dlg.text_title_edit"))
        self.layer_manager = layer_manager
        self.editing = text_obj
        self._on_preview = on_preview if text_obj is not None else None
        self._original_state = dict(text_obj.__dict__) if text_obj is not None else None
        self._follow_points = list(getattr(text_obj, "follow_points", None) or [])
        self._follow_guide_id = getattr(text_obj, "follow_guide_id", None)
        self._place_touched = False      # l'utilisateur a choisi lui-même la position
        self._syncing = False            # réglage modifié par le code, pas par l'utilisateur

        layout = QFormLayout(self)

        # Préréglages : police, taille, disposition... enregistrés sous un nom.
        self.combo_preset = QComboBox()
        self.btn_preset_save = QPushButton(tr("vector.dlg.preset_save"))
        self.btn_preset_delete = QPushButton(tr("vector.dlg.preset_delete"))
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.combo_preset, 1)
        preset_row.addWidget(self.btn_preset_save)
        preset_row.addWidget(self.btn_preset_delete)
        layout.addRow(tr("vector.dlg.preset"), preset_row)
        self._reload_presets()
        self.combo_preset.activated.connect(self._on_preset_chosen)
        self.btn_preset_save.clicked.connect(self._save_preset)
        self.btn_preset_delete.clicked.connect(self._delete_preset)

        self.edit_text = QLineEdit(text_obj.text if (text_obj and not is_new) else tr("vector.dlg.text_default"))
        if is_new:
            self.edit_text.selectAll()      # on tape directement le texte voulu
        layout.addRow(tr("vector.dlg.text_label"), self.edit_text)

        self.combo_font = QFontComboBox()
        if text_obj:
            self.combo_font.setCurrentFont(QFont(text_obj.font_family))
        layout.addRow(tr("vector.dlg.font"), self.combo_font)

        style_row = QHBoxLayout()
        self.chk_bold = QCheckBox(tr("vector.dlg.bold")); self.chk_bold.setChecked(bool(text_obj and text_obj.bold))
        self.chk_italic = QCheckBox(tr("vector.dlg.italic")); self.chk_italic.setChecked(bool(text_obj and text_obj.italic))
        style_row.addWidget(self.chk_bold); style_row.addWidget(self.chk_italic)
        layout.addRow(tr("vector.dlg.style"), style_row)

        self.spin_size = QDoubleSpinBox(); self.spin_size.setRange(1.0, 500.0)
        self.spin_size.setValue(text_obj.size_mm if text_obj else 10.0)
        self.spin_size.setSuffix(" mm")
        layout.addRow(tr("vector.dlg.size_height"), self.spin_size)

        self.spin_spacing = QDoubleSpinBox(); self.spin_spacing.setRange(-5.0, 500.0)
        self.spin_spacing.setValue(text_obj.letter_spacing_mm if text_obj else 0.0)
        self.spin_spacing.setSuffix(" mm")
        layout.addRow(tr("vector.dlg.letter_spacing"), self.spin_spacing)

        arc_inside = bool(getattr(text_obj, "arc_inside", False))
        self.spin_arc_radius = QDoubleSpinBox(); self.spin_arc_radius.setRange(0.0, 1000.0)
        self.spin_arc_radius.setDecimals(1); self.spin_arc_radius.setSuffix(" mm")
        self.spin_arc_radius.setSpecialValueText(tr("vector.dlg.arc_off"))
        self.spin_arc_radius.setValue(getattr(text_obj, "arc_radius_mm", 0.0))
        self.combo_arc_side = QComboBox()
        self.combo_arc_side.addItem(tr("vector.dlg.arc_outside"), False)
        self.combo_arc_side.addItem(tr("vector.dlg.arc_inside"), True)
        self.combo_arc_side.setCurrentIndex(1 if arc_inside else 0)
        center = getattr(text_obj, "arc_center_deg", None)
        self.spin_arc_center = QDoubleSpinBox(); self.spin_arc_center.setRange(0.0, 360.0)
        self.spin_arc_center.setDecimals(1); self.spin_arc_center.setSuffix(" °")
        self.spin_arc_center.setValue(default_center_deg(arc_inside) if center is None else center)
        self.combo_arc_side.currentIndexChanged.connect(self._on_arc_side_changed)
        self.spin_arc_radius.valueChanged.connect(self._update_arc_enabled)
        self._update_arc_enabled()

        # Texte le long d'un autre objet (voir VectorCanvasView.make_text_follow_object) : position sur le
        # tracé, sens, décalage. Affiché seulement pour un texte déjà posé sur un tracé.
        self._has_follow = bool(text_obj and getattr(text_obj, "follow_points", None))
        if not self._has_follow:
            # Texte sur un cercle (rayon, côté, angle). Pour un texte posé sur un tracé, ces réglages ne
            # servent à rien : la position, le côté et la distance se règlent ci-dessous, donc on ne
            # les affiche pas (des champs grisés laissaient croire à une panne).
            layout.addRow(tr("vector.dlg.arc_radius"), self.spin_arc_radius)
            layout.addRow(tr("vector.dlg.arc_side"), self.combo_arc_side)
            layout.addRow(tr("vector.dlg.arc_angle"), self.spin_arc_center)
            self.combo_place = self._make_place_combo()
            layout.addRow(tr("vector.dlg.follow_place"), self.combo_place)
            self._update_arc_enabled()
        if self._has_follow:
            self.spin_follow_pos = QDoubleSpinBox(); self.spin_follow_pos.setRange(0.0, 100.0)
            self.spin_follow_pos.setDecimals(1); self.spin_follow_pos.setSuffix(" %")
            self.spin_follow_pos.setValue(100.0 * float(getattr(text_obj, "follow_center", 0.5)))
            self.combo_place = self._make_place_combo()
            layout.addRow(tr("vector.dlg.follow_place"), self.combo_place)
            layout.addRow(tr("vector.dlg.follow_pos"), self.spin_follow_pos)
            self.chk_follow_reverse = QCheckBox(tr("vector.dlg.follow_reverse"))
            self.chk_follow_reverse.setChecked(bool(getattr(text_obj, "follow_reverse", False)))
            self.chk_follow_reverse.toggled.connect(self._on_follow_reverse_toggled)
            layout.addRow(self.chk_follow_reverse)
            self.spin_follow_gap = QDoubleSpinBox(); self.spin_follow_gap.setRange(-100.0, 100.0)
            self.spin_follow_gap.setDecimals(1); self.spin_follow_gap.setSuffix(" mm")
            self.spin_follow_gap.setValue(float(getattr(text_obj, "follow_gap_mm", 0.0)))
            layout.addRow(tr("vector.dlg.follow_gap"), self.spin_follow_gap)
            self.chk_follow_detach = QCheckBox(tr("vector.dlg.follow_detach"))
            layout.addRow(self.chk_follow_detach)

        # Position des lettres par rapport au trait (cercle ou contour).
        self.combo_anchor = QComboBox()
        for anchor in ANCHORS:
            self.combo_anchor.addItem(tr("vector.dlg.anchor_" + anchor), anchor)
        current_anchor = getattr(text_obj, "text_anchor", "above")
        self.combo_anchor.setCurrentIndex(max(0, self.combo_anchor.findData(current_anchor)))
        layout.addRow(tr("vector.dlg.anchor"), self.combo_anchor)

        # Étaler : règle l'espacement pour que le texte couvre une part du cercle ou du contour.
        spread_row = QHBoxLayout()
        self.spin_span = QDoubleSpinBox(); self.spin_span.setRange(1.0, 100.0)
        self.spin_span.setDecimals(0); self.spin_span.setSuffix(" %"); self.spin_span.setValue(100.0)
        self.btn_spread = QPushButton(tr("vector.dlg.spread_btn"))
        self.btn_spread.setToolTip(tr("vector.dlg.spread_tip"))
        self.btn_spread.clicked.connect(self._spread_text)
        spread_row.addWidget(self.spin_span); spread_row.addWidget(self.btn_spread)
        layout.addRow(tr("vector.dlg.spread"), spread_row)
        self._update_arc_enabled()

        orient_row = QHBoxLayout()
        self.rb_horizontal = QRadioButton(tr("vector.dlg.horizontal"))
        self.rb_vertical = QRadioButton(tr("vector.dlg.vertical"))
        (self.rb_vertical if (text_obj and text_obj.vertical) else self.rb_horizontal).setChecked(True)
        grp = QButtonGroup(self); grp.addButton(self.rb_horizontal); grp.addButton(self.rb_vertical)
        orient_row.addWidget(self.rb_horizontal); orient_row.addWidget(self.rb_vertical)
        layout.addRow(tr("vector.dlg.orientation"), orient_row)

        mirror_row = QHBoxLayout()
        self.chk_mirror_h = QCheckBox(tr("img.mirror_h"))
        self.chk_mirror_h.setChecked(bool(text_obj and text_obj.mirror_h))
        self.chk_mirror_v = QCheckBox(tr("img.mirror_v"))
        self.chk_mirror_v.setChecked(bool(text_obj and text_obj.mirror_v))
        mirror_row.addWidget(self.chk_mirror_h); mirror_row.addWidget(self.chk_mirror_v)
        layout.addRow(tr("vector.dlg.mirror"), mirror_row)

        self.combo_layer = QComboBox()
        for l in self.layer_manager.layers:
            self.combo_layer.addItem(layer_label(l), l.id)
        if text_obj and text_obj.layer_id:
            idx = self.combo_layer.findData(text_obj.layer_id)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        elif text_obj is None:
            # Nouveau texte : calque de gravure par défaut (le premier calque sinon).
            engrave = self.layer_manager.engrave_layer()
            idx = self.combo_layer.findData(engrave.id) if engrave is not None else -1
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        layout.addRow(tr("ui.vector_layer"), self.combo_layer)

        pos_row = QHBoxLayout()
        self.spin_x = QDoubleSpinBox(); self.spin_x.setRange(-1000.0, 1000.0)
        self.spin_x.setDecimals(2); self.spin_x.setSuffix(" mm")
        self.spin_x.setValue(text_obj.x_mm if text_obj else 10.0)
        self.spin_y = QDoubleSpinBox(); self.spin_y.setRange(-1000.0, 1000.0)
        self.spin_y.setDecimals(2); self.spin_y.setSuffix(" mm")
        self.spin_y.setValue(text_obj.y_mm if text_obj else 10.0)
        pos_row.addWidget(QLabel("X :")); pos_row.addWidget(self.spin_x)
        pos_row.addWidget(QLabel("Y :")); pos_row.addWidget(self.spin_y)
        layout.addRow(tr("vector.dlg.corner_pos"), pos_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._sync_place_combo()
        self._wire_live_preview()

    # -- Position : haut / bas / gauche / droite ---------------------------------------------------------

    def _make_place_combo(self):
        combo = QComboBox()
        combo.addItem(tr("vector.dlg.follow_place_custom"), None)
        for side in ("top", "bottom", "left", "right"):
            combo.addItem(tr("vector.dlg.follow_place_" + side), side)
        combo.activated.connect(self._on_place_chosen)
        return combo

    def _position_spin(self):
        return self.spin_follow_pos if self._has_follow else self.spin_arc_center

    def _on_place_chosen(self, _index):
        side = self.combo_place.currentData()
        if side is None:
            return
        self._place_touched = True
        self._set_position(side)

    def _set_position(self, side):
        """Place le texte du côté voulu : sur le tracé (fraction de sa longueur) ou sur le cercle (angle)."""
        self._syncing = True
        try:
            if self._has_follow:
                self.spin_follow_pos.setValue(100.0 * side_center_fraction(self._follow_points, side))
            else:
                self.spin_arc_center.setValue(self._ARC_SIDE_DEG[side])
        finally:
            self._syncing = False
        self._sync_place_combo()

    def _sync_place_combo(self):
        """Le choix de la liste suit la position : « position libre » si elle ne correspond à aucun côté."""
        if self._has_follow:
            side = place_for_fraction(self._follow_points, self.spin_follow_pos.value() / 100.0)
        else:
            angle = self.spin_arc_center.value() % 360.0
            side = next((k for k, v in self._ARC_SIDE_DEG.items() if abs(v - angle) < 0.05), None)
        for i in range(self.combo_place.count()):
            if self.combo_place.itemData(i) == side:
                self.combo_place.setCurrentIndex(i)
                return

    def _on_position_edited(self, _value=None):
        if not self._syncing:
            self._place_touched = True
        self._sync_place_combo()

    # -- Aperçu en direct --------------------------------------------------------------------------------

    def _wire_live_preview(self):
        """Chaque réglage redessine le texte sur le canevas, sans attendre « OK »."""
        self._position_spin().valueChanged.connect(self._on_position_edited)
        if self._on_preview is None:
            return
        signals = [self.edit_text.textChanged, self.combo_font.currentFontChanged,
                   self.chk_bold.toggled, self.chk_italic.toggled, self.spin_size.valueChanged,
                   self.spin_spacing.valueChanged, self.spin_arc_radius.valueChanged,
                   self.combo_arc_side.currentIndexChanged, self.spin_arc_center.valueChanged,
                   self.rb_vertical.toggled, self.chk_mirror_h.toggled, self.chk_mirror_v.toggled,
                   self.combo_layer.currentIndexChanged, self.spin_x.valueChanged, self.spin_y.valueChanged,
                   self.combo_anchor.currentIndexChanged]
        if self._has_follow:
            signals += [self.spin_follow_pos.valueChanged, self.chk_follow_reverse.toggled,
                        self.spin_follow_gap.valueChanged, self.chk_follow_detach.toggled]
        for signal in signals:
            signal.connect(self._preview)

    def _preview(self, *_args):
        try:
            self.get_object()
            self._on_preview()
        except Exception:       # un réglage en cours de saisie ne doit jamais fermer la boîte
            pass

    # -- Étaler le texte ---------------------------------------------------------------------------------

    def _spread_text(self):
        """Règle l'espacement des lettres pour que le texte couvre la part du cercle ou du contour demandée."""
        if self.editing is None:
            return
        obj = self.get_object()
        fraction = self.spin_span.value() / 100.0
        wrap = fraction >= 0.999
        if self._has_follow and not self.chk_follow_detach.isChecked():
            span = fraction * path_length(self._follow_points)
            wrap = wrap and is_closed(self._follow_points)
        elif obj.arc_radius_mm > 0:
            span = fraction * 2.0 * math.pi * obj.arc_baseline_radius_mm()
        else:
            return
        spacing = spacing_to_span(obj.text_advances_mm(), span, wrap)
        self.spin_spacing.setValue(min(self.spin_spacing.maximum(), max(self.spin_spacing.minimum(), spacing)))

    # -- Préréglages -------------------------------------------------------------------------------------

    def _reload_presets(self, select=None):
        self.combo_preset.clear()
        self.combo_preset.addItem(tr("vector.dlg.preset_none"), None)
        for name in sorted(text_presets.load_user(), key=str.lower):
            self.combo_preset.addItem(name, name)
        idx = self.combo_preset.findData(select) if select else 0
        self.combo_preset.setCurrentIndex(max(0, idx))
        self.btn_preset_delete.setEnabled(self.combo_preset.currentData() is not None)

    def _preset_values(self):
        values = {
            "font_family": self.combo_font.currentFont().family(),
            "bold": self.chk_bold.isChecked(), "italic": self.chk_italic.isChecked(),
            "size_mm": self.spin_size.value(), "letter_spacing_mm": self.spin_spacing.value(),
            "text_anchor": self.combo_anchor.currentData(),
        }
        if self._has_follow:
            values["follow_reverse"] = self.chk_follow_reverse.isChecked()
            values["follow_gap_mm"] = self.spin_follow_gap.value()
        else:
            values["arc_radius_mm"] = self.spin_arc_radius.value()
            values["arc_inside"] = bool(self.combo_arc_side.currentData())
        return values

    def _apply_preset(self, v):
        if "font_family" in v:
            self.combo_font.setCurrentFont(QFont(v["font_family"]))
        if "bold" in v:
            self.chk_bold.setChecked(v["bold"])
        if "italic" in v:
            self.chk_italic.setChecked(v["italic"])
        if "size_mm" in v:
            self.spin_size.setValue(v["size_mm"])
        if "letter_spacing_mm" in v:
            self.spin_spacing.setValue(v["letter_spacing_mm"])
        if "text_anchor" in v:
            self.combo_anchor.setCurrentIndex(max(0, self.combo_anchor.findData(v["text_anchor"])))
        if self._has_follow:
            if "follow_reverse" in v:
                self.chk_follow_reverse.setChecked(v["follow_reverse"])
            if "follow_gap_mm" in v:
                self.spin_follow_gap.setValue(v["follow_gap_mm"])
        else:
            if "arc_radius_mm" in v:
                self.spin_arc_radius.setValue(v["arc_radius_mm"])
            if "arc_inside" in v:
                self.combo_arc_side.setCurrentIndex(1 if v["arc_inside"] else 0)

    def _on_preset_chosen(self, _index):
        name = self.combo_preset.currentData()
        self.btn_preset_delete.setEnabled(name is not None)
        if name is not None:
            self._apply_preset(text_presets.load_user().get(name, {}))

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, tr("vector.dlg.preset_name_title"), tr("vector.dlg.preset_name_label"),
                                        text=self.combo_preset.currentData() or "")
        if ok and name.strip():
            if text_presets.save_user(name, self._preset_values()):
                self._reload_presets(select=name.strip())

    def _delete_preset(self):
        name = self.combo_preset.currentData()
        if name is not None and text_presets.delete_user(name):
            self._reload_presets()

    def showEvent(self, event):
        """Aperçu en direct : la boîte se range sur le côté droit de la fenêtre pour laisser voir le texte."""
        super().showEvent(event)
        parent = self.parentWidget()
        if self._on_preview is None or parent is None or getattr(self, "_placed", False):
            return
        self._placed = True
        try:
            frame = parent.window().frameGeometry()
            screen = self.screen().availableGeometry()
            x = min(frame.right() - self.width() - 20, screen.right() - self.width())
            y = min(max(frame.top() + 80, screen.top()), screen.bottom() - self.height())
            self.move(max(x, screen.left()), y)
        except Exception:   # pas d'écran connu (hors écran, fenêtre fermée) : position par défaut de Qt
            pass

    def done(self, result):
        """À la fermeture, remet le texte dans son état d'origine : le texte a été modifié pour l'aperçu, et
        l'appelant enregistre l'annulation (Ctrl+Z) puis applique `get_object()` seulement si on accepte."""
        if self._original_state is not None:
            self.editing.__dict__.clear()
            self.editing.__dict__.update(self._original_state)
            if self._on_preview is not None:
                self._on_preview()
        super().done(result)

    def _on_arc_side_changed(self):
        """Passer d'extérieur à intérieur déplace le texte du haut vers le bas du cercle, tant que
        l'angle est encore celui par défaut de l'autre côté."""
        inside = bool(self.combo_arc_side.currentData())
        if not self._place_touched and abs(self.spin_arc_center.value() - default_center_deg(not inside)) < 1e-6:
            self._syncing = True
            self.spin_arc_center.setValue(default_center_deg(inside))
            self._syncing = False

    def _on_follow_reverse_toggled(self, inside):
        """Mettre le texte de l'autre côté du trait le fait lire à l'envers à l'endroit où il était (le haut
        des lettres vise le centre) : tant que la position est encore celle par défaut de l'autre côté, on
        l'amène au bas du contour (ou au haut en décochant), où il se lit à l'endroit."""
        points = self._follow_points
        if not points or self._place_touched:
            return
        old = 100.0 * default_center_fraction(points, not inside)
        if abs(self.spin_follow_pos.value() - old) < 0.1:
            self._syncing = True
            self.spin_follow_pos.setValue(100.0 * default_center_fraction(points, inside))
            self._syncing = False

    def _update_arc_enabled(self):
        on = self.spin_arc_radius.value() > 0
        self.combo_arc_side.setEnabled(on)
        self.spin_arc_center.setEnabled(on)
        curved = on or getattr(self, "_has_follow", False)
        if hasattr(self, "combo_anchor"):
            self.combo_anchor.setEnabled(curved)
            self.spin_span.setEnabled(curved)
            self.btn_spread.setEnabled(curved)
        if hasattr(self, "combo_place"):
            self.combo_place.setEnabled(on)

    def get_object(self) -> TextObject:
        layer_id = self.combo_layer.currentData()
        if self.editing:
            obj = self.editing
        else:
            obj = TextObject(layer_id=layer_id, x_mm=10.0, y_mm=10.0)
        obj.text = self.edit_text.text() or "TEXTE"
        obj.font_family = self.combo_font.currentFont().family()
        obj.bold = self.chk_bold.isChecked()
        obj.italic = self.chk_italic.isChecked()
        obj.size_mm = self.spin_size.value()
        obj.letter_spacing_mm = self.spin_spacing.value()
        obj.arc_radius_mm = self.spin_arc_radius.value()
        obj.arc_inside = bool(self.combo_arc_side.currentData())
        obj.arc_center_deg = self.spin_arc_center.value()
        obj.text_anchor = self.combo_anchor.currentData() or "above"
        if self._has_follow:
            if self.chk_follow_detach.isChecked():
                obj.follow_points = None        # redevient un texte droit
                obj.follow_guide_id = None
            else:
                obj.follow_points = list(self._follow_points)    # (l'aperçu a pu détacher le texte)
                obj.follow_guide_id = self._follow_guide_id
                obj.follow_center = self.spin_follow_pos.value() / 100.0
                obj.follow_reverse = self.chk_follow_reverse.isChecked()
                obj.follow_gap_mm = self.spin_follow_gap.value()
        obj.vertical = self.rb_vertical.isChecked()
        obj.mirror_h = self.chk_mirror_h.isChecked()
        obj.mirror_v = self.chk_mirror_v.isChecked()
        obj.layer_id = layer_id
        obj.x_mm = self.spin_x.value()
        obj.y_mm = self.spin_y.value()
        return obj
