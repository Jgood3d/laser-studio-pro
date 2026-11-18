"""Dialogue « Boule de Noël » : prénom, police, accroche, motifs, aperçu en direct des contours à découper."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.models.layers import layer_label
from laser_studio.vector import ornament_generator as og
from laser_studio.vector.ornament_region import build_ornament_contours


class OrnamentPreview(QWidget):
    """Contours exactement tels que le laser les suivra (après soudure), Y vers le haut."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 360)
        self.contours = []
        self.message = ""

    def set_contours(self, contours, message=""):
        self.contours = contours
        self.message = message
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1a1d24"))
        if self.contours:
            xs = [pt[0] for c in self.contours for pt in c]
            ys = [pt[1] for c in self.contours for pt in c]
            w, h = max(max(xs), 1e-6), max(max(ys), 1e-6)
            pad = 14
            s = min((self.width() - 2 * pad) / w, (self.height() - 2 * pad) / h)
            ox = (self.width() - w * s) / 2
            oy = (self.height() - h * s) / 2 + h * s  # Y vers le haut : on retourne
            path = QPainterPath()
            for contour in self.contours:
                path.moveTo(ox + contour[0][0] * s, oy - contour[0][1] * s)
                for x, y in contour[1:]:
                    path.lineTo(ox + x * s, oy - y * s)
                path.closeSubpath()
            p.setBrush(QColor(201, 164, 107, 70))
            p.setPen(QPen(QColor("#ff4b4b"), 1.6))
            path.setFillRule(Qt.FillRule.OddEvenFill)
            p.drawPath(path)
        if self.message:
            p.setPen(QColor("#ffb86b"))
            p.drawText(self.rect().adjusted(10, 8, -10, -8), Qt.AlignmentFlag.AlignTop.value | Qt.TextFlag.TextWordWrap.value,
                       self.message)
        p.end()


class OrnamentGeneratorDialog(QDialog):
    def __init__(self, parent=None, layers=None, saved_settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ornament.title"))
        self.resize(820, 620)
        self.layers = layers or []
        saved = saved_settings or {}

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        form = QFormLayout()

        self.edit_name = QLineEdit(saved.get("name", "Emma"))
        self.edit_name.setMaxLength(40)
        form.addRow(tr("ornament.name"), self.edit_name)

        font_row = QHBoxLayout()
        self.combo_font = QFontComboBox()
        self.combo_font.setCurrentFont(QFont(saved.get("font", "Sans Serif")))
        self.chk_bold = QCheckBox(tr("ornament.bold"))
        self.chk_bold.setChecked(saved.get("bold", True))
        self.chk_italic = QCheckBox(tr("ornament.italic"))
        self.chk_italic.setChecked(saved.get("italic", False))
        font_row.addWidget(self.combo_font, 1)
        font_row.addWidget(self.chk_bold)
        font_row.addWidget(self.chk_italic)
        form.addRow(tr("ornament.font"), font_row)

        self.spin_d = self._spin(30, 400, saved.get("diameter", 80.0), " mm")
        form.addRow(tr("ornament.diameter"), self.spin_d)
        self.spin_ring = self._spin(1.5, 100, saved.get("ring_width", 4.0), " mm")
        form.addRow(tr("ornament.ring_width"), self.spin_ring)

        self.combo_hanger = QComboBox()
        for key in og.HANGERS:
            self.combo_hanger.addItem(tr(f"ornament.hanger.{key}"), key)
        self._select(self.combo_hanger, saved.get("hanger", "Anneau"))
        form.addRow(tr("ornament.hanger"), self.combo_hanger)
        self.spin_hole = self._spin(1.5, 10, saved.get("hole_diameter", 3.0), " mm")
        form.addRow(tr("ornament.hole"), self.spin_hole)

        self.combo_motif = QComboBox()
        for key in og.MOTIFS:
            self.combo_motif.addItem(tr(f"ornament.motif.{key}"), key)
        self._select(self.combo_motif, saved.get("motif", "Flocons"))
        form.addRow(tr("ornament.motif"), self.combo_motif)
        self.combo_layout = QComboBox()
        for key in og.FLAKE_LAYOUTS:
            self.combo_layout.addItem(tr(f"ornament.layout.{key}"), key)
        self._select(self.combo_layout, saved.get("flake_layout", "Suspendus"))
        form.addRow(tr("ornament.layout"), self.combo_layout)
        self.combo_style = QComboBox()
        self._fill_styles(saved.get("flake_style", "Classique"))
        form.addRow(tr("ornament.style"), self.combo_style)
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 7)
        self.spin_count.setValue(saved.get("flake_count", 3))
        form.addRow(tr("ornament.count"), self.spin_count)
        self.spin_flake = self._spin(8, 240, saved.get("flake_size", 16.0), " mm")
        form.addRow(tr("ornament.flake_size"), self.spin_flake)

        self.chk_auto_offset = QCheckBox(tr("ornament.auto"))
        self.chk_auto_offset.setChecked(saved.get("name_offset") is None)
        self.spin_offset = self._spin(-200, 200, saved.get("name_offset") or 0.0, " mm")
        offset_row = QHBoxLayout()
        offset_row.addWidget(self.chk_auto_offset)
        offset_row.addWidget(self.spin_offset, 1)
        form.addRow(tr("ornament.name_offset"), offset_row)
        self.chk_auto_size = QCheckBox(tr("ornament.auto"))
        self.chk_auto_size.setChecked(not saved.get("name_size"))
        self.spin_size = self._spin(2, 300, saved.get("name_size") or 20.0, " mm")
        size_row = QHBoxLayout()
        size_row.addWidget(self.chk_auto_size)
        size_row.addWidget(self.spin_size, 1)
        form.addRow(tr("ornament.name_size"), size_row)

        self.combo_support = QComboBox()
        for key in og.SUPPORTS:
            self.combo_support.addItem(tr(f"ornament.support.{key}"), key)
        self._select(self.combo_support, saved.get("support", "Barre"))
        self.combo_support.setToolTip(tr("ornament.support_tip"))
        form.addRow(tr("ornament.support"), self.combo_support)

        self.combo_layer = QComboBox()
        default_index = 0
        for idx, layer in enumerate(self.layers):
            self.combo_layer.addItem(layer_label(layer), layer.id)
            if "découpe" in layer.mode.lower() or "cut" in layer.mode.lower():
                default_index = idx
        if self.combo_layer.count() > 0:
            self.combo_layer.setCurrentIndex(default_index)
        form.addRow(tr("ornament.layer"), self.combo_layer)
        left.addLayout(form)

        self.lbl_warning = QLabel()
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setStyleSheet("color: #ffb86b;")
        left.addWidget(self.lbl_warning)
        left.addStretch(1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        left.addWidget(self.buttons)

        right = QVBoxLayout()
        right.addWidget(QLabel(tr("ornament.preview")))
        self.preview = OrnamentPreview()
        right.addWidget(self.preview, 1)
        hint = QLabel(tr("ornament.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b93a7; font-size: 12px;")
        right.addWidget(hint)
        root.addLayout(left, 4)
        root.addLayout(right, 5)

        # Un recalcul 150 ms après la dernière modification : la soudure des lettres n'est pas instantanée.
        self.combo_motif.currentIndexChanged.connect(self._on_motif_changed)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._update_preview)
        for widget, signal in (
            (self.edit_name, "textChanged"), (self.combo_font, "currentFontChanged"),
            (self.chk_bold, "toggled"), (self.chk_italic, "toggled"), (self.spin_d, "valueChanged"),
            (self.spin_ring, "valueChanged"), (self.combo_hanger, "currentIndexChanged"),
            (self.spin_hole, "valueChanged"), (self.combo_motif, "currentIndexChanged"),
            (self.combo_layout, "currentIndexChanged"), (self.combo_style, "currentIndexChanged"),
            (self.spin_count, "valueChanged"), (self.spin_flake, "valueChanged"),
            (self.chk_auto_offset, "toggled"), (self.spin_offset, "valueChanged"),
            (self.chk_auto_size, "toggled"), (self.spin_size, "valueChanged"),
            (self.combo_support, "currentIndexChanged"),
        ):
            getattr(widget, signal).connect(self._schedule)
        self._update_preview()

    # -- aides ---------------------------------------------------------------------------------------------
    @staticmethod
    def _spin(lo, hi, value, suffix):
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    @staticmethod
    def _select(combo, data):
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _fill_styles(self, wanted=None):
        """Liste les styles du motif choisi ; garde `wanted` s'il existe pour ce motif."""
        motif = self.combo_motif.currentData() if hasattr(self, "combo_motif") else "Flocons"
        styles = og.MOTIF_STYLES.get(motif, ("Classique",))
        blocked = self.combo_style.blockSignals(True)
        try:
            self.combo_style.clear()
            for key in styles:
                self.combo_style.addItem(tr(f"ornament.style.{key}"), key)
            index = self.combo_style.findData(wanted)
            self.combo_style.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self.combo_style.blockSignals(blocked)

    def _on_motif_changed(self, *_args):
        """Un autre motif : ses styles, et une taille qui lui convient (un Père Noël de 16 mm n'aurait pas de visage)."""
        self._fill_styles(self.combo_style.currentData())
        default = og.MOTIF_DEFAULT_SIZE.get(self.combo_motif.currentData())
        if default:
            self.spin_flake.setValue(default)

    def _schedule(self, *_args):
        self._timer.start()

    # -- état ----------------------------------------------------------------------------------------------
    def cut_layer_id(self):
        return self.combo_layer.currentData()

    def font_options(self):
        return self.combo_font.currentFont().family(), self.chk_bold.isChecked(), self.chk_italic.isChecked()

    def params(self):
        return og.OrnamentParams(
            diameter=self.spin_d.value(), ring_width=self.spin_ring.value(), hanger=self.combo_hanger.currentData(),
            hole_diameter=self.spin_hole.value(), name=self.edit_name.text().strip(),
            name_size=0.0 if self.chk_auto_size.isChecked() else self.spin_size.value(),
            name_offset=None if self.chk_auto_offset.isChecked() else self.spin_offset.value(),
            support=self.combo_support.currentData(), motif=self.combo_motif.currentData(),
            flake_layout=self.combo_layout.currentData(), flake_style=self.combo_style.currentData(),
            flake_count=self.spin_count.value(), flake_size=self.spin_flake.value(),
        )

    def settings(self):
        p = self.params()
        family, bold, italic = self.font_options()
        return {
            "name": p.name, "font": family, "bold": bold, "italic": italic, "diameter": p.diameter,
            "ring_width": p.ring_width, "hanger": p.hanger, "hole_diameter": p.hole_diameter,
            "motif": p.motif, "flake_layout": p.flake_layout, "flake_style": p.flake_style,
            "flake_count": p.flake_count, "flake_size": p.flake_size, "name_offset": p.name_offset,
            "name_size": p.name_size, "support": p.support,
        }

    def _update_preview(self):
        self.spin_offset.setEnabled(not self.chk_auto_offset.isChecked())
        self.spin_size.setEnabled(not self.chk_auto_size.isChecked())
        flakes = self.combo_motif.currentData() != "Aucun"
        for widget in (self.combo_layout, self.combo_style, self.spin_count, self.spin_flake):
            widget.setEnabled(flakes)
        # La guirlande va toujours en haut, d'un côté à l'autre : la disposition ne s'applique pas.
        self.combo_layout.setEnabled(flakes and self.combo_motif.currentData() != "Guirlande")
        self.spin_hole.setEnabled(self.combo_hanger.currentData() != "Aucun")
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        try:
            family, bold, italic = self.font_options()
            geometry, contours = build_ornament_contours(self.params(), family, bold, italic)
        except og.OrnamentError as e:
            self.preview.set_contours([], error_text(e))
            self.lbl_warning.clear()
            ok.setEnabled(False)
            return
        self.preview.set_contours(contours)
        self.lbl_warning.setText(tr("ornament.warn.floating") if geometry.floating_name else "")
        ok.setEnabled(bool(contours))


def error_text(error):
    """Message traduit d'une OrnamentError (clé `ornament.err.<code>`)."""
    key = f"ornament.err.{error.code}"
    text = tr(key)
    if text == key:
        return tr("ornament.error") + f" ({error.code})"
    try:
        return text.format(**error.info)
    except Exception:
        return text
