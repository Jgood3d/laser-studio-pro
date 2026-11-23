"""Dialogue « Porte-clés prénom » (façon NameKey) : aperçu en direct découpe + gravure."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
    QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.i18n.errors import generator_error_text
from laser_studio.models.layer_modes import MODE_CUT
from laser_studio.models.layers import ENGRAVE_MODE, layer_label
from laser_studio.vector import keychain_generator as kg


class KeychainPreview(QWidget):
    """Aperçu en direct : base découpée (rouge) et texte gravé (bleu/cyan), Y vers le haut."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 280)
        self.result: kg.KeychainResult | None = None
        self.message = ""

    def set_result(self, result: kg.KeychainResult | None, message: str = ""):
        self.result = result
        self.message = message
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1a1d24"))

        if self.result and self.result.base_contours:
            w = max(self.result.width, 1e-6)
            h = max(self.result.height, 1e-6)
            pad = 24
            s = min((self.width() - 2 * pad) / w, (self.height() - 2 * pad) / h)
            ox = (self.width() - w * s) / 2.0
            oy = (self.height() - h * s) / 2.0 + h * s

            def to_qpath(contours):
                qp = QPainterPath()
                qp.setFillRule(Qt.FillRule.OddEvenFill)
                for c in contours:
                    qp.moveTo(ox + c[0][0] * s, oy - c[0][1] * s)
                    for x, y in c[1:]:
                        qp.lineTo(ox + x * s, oy - y * s)
                    qp.closeSubpath()
                return qp

            two = getattr(self.result, "two_layers", False)

            # --- Pièce GAUCHE (fond) ---
            if self.result.base_contours:
                base_qp = to_qpath(self.result.base_contours)
                p.setBrush(QColor(201, 164, 107, 75))
                p.setPen(QPen(QColor("#ff4b4b"), 1.6))
                p.drawPath(base_qp)

            if two:
                # Contour fin du prénom (guide de collage)
                if getattr(self.result, "outline_contours", None):
                    out_qp = to_qpath(self.result.outline_contours)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(QColor("#4da6ff"), 1.4))
                    p.drawPath(out_qp)

                # --- Pièce DROITE (dessus) ---
                top_base = getattr(self.result, "top_base_contours", None) or []
                if top_base:
                    top_qp = to_qpath(top_base)
                    p.setBrush(QColor(201, 164, 107, 55))
                    p.setPen(QPen(QColor("#ff4b4b"), 1.6))
                    p.drawPath(top_qp)

                top_text = getattr(self.result, "top_text_contours", None) or []
                if top_text:
                    letters_qp = to_qpath(top_text)
                    p.setBrush(QColor(120, 220, 140, 180))
                    p.setPen(QPen(QColor("#3dba5c"), 1.0))
                    p.drawPath(letters_qp)
            else:
                # Mode classique : texte gravé
                if self.result.text_contours:
                    text_qp = to_qpath(self.result.text_contours)
                    p.setBrush(QColor(77, 166, 255, 160))
                    p.setPen(QPen(QColor("#4da6ff"), 1.0))
                    p.drawPath(text_qp)

            # Dimensions totales affichées en bas
            p.setPen(QColor("#a0a8b8"))
            p.drawText(
                self.rect().adjusted(10, 6, -10, -6),
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                f"{self.result.width:.1f} × {self.result.height:.1f} mm",
            )

        if self.message:
            p.setPen(QColor("#ffb86b"))
            p.drawText(
                self.rect().adjusted(10, 8, -10, -8),
                Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                self.message,
            )
        p.end()


class KeychainGeneratorDialog(QDialog):
    def __init__(self, parent=None, layers=None, saved_settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr("keychain.title"))
        self.resize(840, 560)
        self.layers = layers or []
        saved = saved_settings or {}

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        form = QFormLayout()

        self.edit_text = QPlainTextEdit(saved.get("text", "Emma"))
        self.edit_text.setMinimumHeight(72)
        self.edit_text.setMaximumHeight(110)
        self.edit_text.setPlaceholderText(tr("keychain.text_placeholder"))
        form.addRow(tr("keychain.text"), self.edit_text)

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

        self.spin_text_h = self._spin(4.0, 150.0, saved.get("text_height_mm", 14.0), " mm")
        form.addRow(tr("keychain.text_height"), self.spin_text_h)

        self.spin_spacing = self._spin(70.0, 200.0, saved.get("letter_spacing", 100.0), " %", decimals=0)
        form.addRow(tr("keychain.letter_spacing"), self.spin_spacing)

        self.spin_margin = self._spin(1.0, 30.0, saved.get("margin_mm", 3.0), " mm")
        form.addRow(tr("keychain.margin"), self.spin_margin)

        self.chk_bridge = QCheckBox(tr("keychain.bridge_isolated"))
        self.chk_bridge.setChecked(saved.get("bridge_isolated", True))
        form.addRow("", self.chk_bridge)

        self.chk_two_layers = QCheckBox(tr("keychain.two_layers"))
        self.chk_two_layers.setChecked(saved.get("two_layers", False))
        self.chk_two_layers.setToolTip(tr("keychain.two_layers_tip"))
        form.addRow("", self.chk_two_layers)

        self.combo_ring = QComboBox()
        for key in kg.RING_POSITIONS:
            self.combo_ring.addItem(tr(f"keychain.ring.{key}"), key)
        self._select(self.combo_ring, saved.get("ring_position", "Gauche"))
        form.addRow(tr("keychain.ring_position"), self.combo_ring)

        self.spin_ring_d = self._spin(4.0, 40.0, saved.get("ring_outer_d", 9.0), " mm")
        form.addRow(tr("keychain.ring_outer"), self.spin_ring_d)

        self.spin_hole_d = self._spin(1.5, 25.0, saved.get("ring_hole_d", 4.0), " mm")
        form.addRow(tr("keychain.ring_hole"), self.spin_hole_d)

        self.spin_overlap = self._spin(0.5, 15.0, saved.get("ring_overlap_mm", 2.0), " mm")
        form.addRow(tr("keychain.ring_overlap"), self.spin_overlap)

        # Sélection des calques Découpe et Gravure
        self.combo_cut_layer = QComboBox()
        self.combo_engrave_layer = QComboBox()
        cut_idx = 0
        eng_idx = 0
        for idx, layer in enumerate(self.layers):
            lbl = layer_label(layer)
            self.combo_cut_layer.addItem(lbl, layer.id)
            self.combo_engrave_layer.addItem(lbl, layer.id)
            if layer.mode == MODE_CUT:
                cut_idx = idx
            elif layer.mode == ENGRAVE_MODE:
                eng_idx = idx
        if self.layers:
            self.combo_cut_layer.setCurrentIndex(cut_idx)
            self.combo_engrave_layer.setCurrentIndex(eng_idx)

        form.addRow(tr("keychain.cut_layer"), self.combo_cut_layer)
        form.addRow(tr("keychain.engrave_layer"), self.combo_engrave_layer)

        left.addLayout(form)
        left.addStretch(1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        left.addWidget(self.buttons)

        right = QVBoxLayout()
        right.addWidget(QLabel(tr("keychain.preview")))
        self.preview = KeychainPreview()
        right.addWidget(self.preview, 1)
        hint = QLabel(tr("keychain.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b93a7; font-size: 12px;")
        right.addWidget(hint)

        root.addLayout(left, 4)
        root.addLayout(right, 5)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._update_preview)

        for widget, signal in (
            (self.edit_text, "textChanged"),
            (self.combo_font, "currentFontChanged"),
            (self.chk_bold, "toggled"),
            (self.chk_italic, "toggled"),
            (self.spin_text_h, "valueChanged"),
            (self.spin_spacing, "valueChanged"),
            (self.spin_margin, "valueChanged"),
            (self.chk_bridge, "toggled"),
            (self.chk_two_layers, "toggled"),
            (self.combo_ring, "currentIndexChanged"),
            (self.spin_ring_d, "valueChanged"),
            (self.spin_hole_d, "valueChanged"),
            (self.spin_overlap, "valueChanged"),
        ):
            getattr(widget, signal).connect(self._schedule)

        self._update_preview()

    @staticmethod
    def _spin(lo, hi, value, suffix, decimals=1):
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    @staticmethod
    def _select(combo, data):
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _schedule(self, *_args):
        self._timer.start()

    def cut_layer_id(self):
        return self.combo_cut_layer.currentData()

    def engrave_layer_id(self):
        return self.combo_engrave_layer.currentData()

    def font_options(self):
        return (
            self.combo_font.currentFont().family(),
            self.chk_bold.isChecked(),
            self.chk_italic.isChecked(),
        )

    def params(self) -> kg.KeychainParams:
        return kg.KeychainParams(
            text=self.edit_text.toPlainText(),
            text_height_mm=self.spin_text_h.value(),
            letter_spacing=self.spin_spacing.value(),
            margin_mm=self.spin_margin.value(),
            ring_position=self.combo_ring.currentData(),
            ring_outer_d=self.spin_ring_d.value(),
            ring_hole_d=self.spin_hole_d.value(),
            ring_overlap_mm=self.spin_overlap.value(),
            bridge_isolated=self.chk_bridge.isChecked(),
            two_layers=self.chk_two_layers.isChecked(),
        )

    def settings(self) -> dict:
        p = self.params()
        family, bold, italic = self.font_options()
        return {
            "text": p.text,
            "font": family,
            "bold": bold,
            "italic": italic,
            "text_height_mm": p.text_height_mm,
            "letter_spacing": p.letter_spacing,
            "margin_mm": p.margin_mm,
            "ring_position": p.ring_position,
            "ring_outer_d": p.ring_outer_d,
            "ring_hole_d": p.ring_hole_d,
            "ring_overlap_mm": p.ring_overlap_mm,
            "bridge_isolated": p.bridge_isolated,
            "two_layers": p.two_layers,
        }

    def _update_preview(self):
        has_ring = self.combo_ring.currentData() != "Aucun"
        for w in (self.spin_ring_d, self.spin_hole_d, self.spin_overlap):
            w.setEnabled(has_ring)

        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        names = [ln.strip() for ln in self.edit_text.toPlainText().splitlines() if ln.strip()]

        # Lot (plusieurs prénoms) : pas de génération live (trop lent).
        # On affiche juste le nombre et on active OK.
        if len(names) > 1:
            msg = tr("keychain.batch_preview").format(n=len(names))
            self.preview.set_result(None, msg)
            ok.setEnabled(True)
            return

        try:
            family, bold, italic = self.font_options()
            res = kg.build_keychain(self.params(), family, bold, italic)
        except kg.KeychainError as e:
            self.preview.set_result(None, error_text(e))
            ok.setEnabled(False)
            return

        self.preview.set_result(res)
        ok.setEnabled(True)


def error_text(error: kg.KeychainError) -> str:
    return generator_error_text("keychain", error)