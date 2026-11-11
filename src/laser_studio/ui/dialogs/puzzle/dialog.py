"""Dialogue puzzle : valeurs toujours visibles (QLabel + boutons − / +), aperçu live."""
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDoubleSpinBox,
    QSpinBox, QComboBox, QDialogButtonBox, QLabel, QWidget, QGroupBox,
    QToolButton,
)
from laser_studio.vector.puzzle_generator import PuzzleParams, build_puzzle, generate_jigsaw_edge
from laser_studio.i18n import tr


class TabShapePreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 220)
        self.params = dict(tab_depth=0.22, tab_span=0.34, neck_width=0.45, style="Classique")
        self._seed = 11

    def set_params(self, **kw):
        self.params.update(kw)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1a1d24"))
        style = self.params.get("style", "Classique")
        w, h = self.width(), self.height()
        if style == "Organique":
            self._paint_grid(p, organic=True)
        else:
            self._paint_edge(p, QRectF(8, 8, w * 0.44, h - 16))
            self._paint_grid(p, organic=False, rect=QRectF(w * 0.48, 8, w * 0.50, h - 16))
        p.end()

    def _paint_edge(self, p, rect):
        p.save()
        p.setPen(QPen(QColor("#3a4050"), 1))
        p.drawRoundedRect(rect, 6, 6)
        edge = generate_jigsaw_edge(
            (0, 0), (40.0, 0), +1,
            tab_depth=self.params["tab_depth"],
            tab_span=self.params["tab_span"],
            neck_width=self.params["neck_width"],
            t_mid=0.50, jitter=0.0,
        )
        xs = [pt[0] for pt in edge]
        ys = [pt[1] for pt in edge]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        pad = 12
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        s = min((rect.width() - 2 * pad) / span_x, (rect.height() - 2 * pad) / span_y)
        cx, cy = rect.center().x(), rect.center().y()
        mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        path = QPainterPath()
        for i, (x, y) in enumerate(edge):
            px = cx + (x - mid_x) * s
            py = cy - (y - mid_y) * s
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        p.setPen(QPen(QColor("#4a5160"), 1, Qt.PenStyle.DashLine))
        y0 = cy - (0 - mid_y) * s
        p.drawLine(QPointF(rect.left() + pad, y0), QPointF(rect.right() - pad, y0))
        p.setPen(QPen(QColor("#ff4b4b"), 2.4))
        p.drawPath(path)
        p.setPen(QColor("#8b93a7"))
        p.drawText(rect.adjusted(8, 4, -8, -4),
                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, "Forme du tenon")
        p.restore()

    def _paint_grid(self, p, organic=False, rect=None):
        if rect is None:
            rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        p.save()
        p.setPen(QPen(QColor("#3a4050"), 1))
        p.drawRoundedRect(rect, 6, 6)
        params = PuzzleParams(
            width=40, height=40, nx=2, ny=2,
            style="Organique" if organic else "Classique",
            seed=self._seed,
            tab_depth=self.params["tab_depth"],
            tab_span=self.params["tab_span"],
            neck_width=self.params["neck_width"],
            pos_random=0.5, jitter=0.08,
        )
        result = build_puzzle(params)
        all_x = [pt[0] for piece in result.pieces for pt in piece.cut]
        all_y = [pt[1] for piece in result.pieces for pt in piece.cut]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        pad = 12
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        s = min((rect.width() - 2 * pad) / span_x, (rect.height() - 2 * pad) / span_y)
        cx, cy = rect.center().x(), rect.center().y()
        mid_x, mid_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        p.setPen(QPen(QColor("#ff4b4b"), 1.4))
        for piece in result.pieces:
            path = QPainterPath()
            for i, (x, y) in enumerate(piece.cut):
                px = cx + (x - mid_x) * s
                py = cy - (y - mid_y) * s
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            path.closeSubpath()
            p.drawPath(path)
        p.setPen(QColor("#8b93a7"))
        p.drawText(rect.adjusted(8, 4, -8, -4),
                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                   "Aperçu 2×2 (ondulé)" if organic else "Aperçu 2×2")
        p.restore()


class PlusMinusRow(QWidget):
    """label | − | valeur (QLabel) | +   — toujours lisible, sans spinbox."""
    changed = pyqtSignal()

    def __init__(self, label, lo, hi, value, step=0.01, decimals=2, suffix="", parent=None):
        super().__init__(parent)
        self.lo = float(lo)
        self.hi = float(hi)
        self.step = float(step)
        self.decimals = int(decimals)
        self.suffix = suffix
        self._value = float(value)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel(label)
        lbl.setMinimumWidth(140)
        lay.addWidget(lbl)

        btn_m = QToolButton()
        btn_m.setText("−")
        btn_m.setFixedSize(30, 28)
        btn_m.clicked.connect(lambda: self._nudge(-1))
        lay.addWidget(btn_m)

        self.val_lbl = QLabel()
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_lbl.setFixedWidth(80)
        self.val_lbl.setStyleSheet(
            "QLabel { background: #2a2f3a; color: #e8eaed; border: 1px solid #4a5160;"
            " border-radius: 4px; padding: 4px 6px; font-weight: 600; }"
        )
        lay.addWidget(self.val_lbl)

        btn_p = QToolButton()
        btn_p.setText("+")
        btn_p.setFixedSize(30, 28)
        btn_p.clicked.connect(lambda: self._nudge(+1))
        lay.addWidget(btn_p)
        lay.addStretch(1)
        self._refresh()

    def _nudge(self, direction):
        self.setValue(self._value + direction * self.step)

    def setValue(self, v):
        self._value = max(self.lo, min(self.hi, float(v)))
        self._refresh()
        self.changed.emit()

    def value(self):
        return self._value

    def _refresh(self):
        txt = f"{self._value:.{self.decimals}f}"
        if self.suffix:
            txt += self.suffix
        self.val_lbl.setText(txt)


class PuzzleGeneratorDialog(QDialog):
    def __init__(self, parent=None, layers=None, bed_w=400.0, bed_h=400.0,
                 saved_settings=None, target_image_rect=None):
        super().__init__(parent)
        self.setWindowTitle(tr("puzzle.title"))
        self.resize(740, 520)
        self.layers = layers or []
        saved = saved_settings or {}

        if target_image_rect:
            self.def_x, self.def_y, self.def_w, self.def_h = target_image_rect
        else:
            self.def_w = saved.get("w", 119.21)
            self.def_h = saved.get("h", 65.02)
            self.def_x = saved.get("x", 0.0)
            self.def_y = saved.get("y", 0.0)

        root = QHBoxLayout(self)
        left = QVBoxLayout()

        info = QLabel("Configuration du puzzle ajustée à l'image active :")
        info.setWordWrap(True)
        info.setStyleSheet("font-weight: bold; color: #27ae60;")
        left.addWidget(info)

        form = QFormLayout()
        self.combo_style = QComboBox()
        self.combo_style.addItem("Jigsaw Classique (tenons / mortaises)", "Classique")
        self.combo_style.addItem("Grille Ondulée (vagues)", "Organique")
        if "style" in saved:
            idx = self.combo_style.findData(saved["style"])
            if idx >= 0:
                self.combo_style.setCurrentIndex(idx)
        self.combo_style.currentIndexChanged.connect(self._on_style_changed)
        form.addRow("Style de découpe :", self.combo_style)

        self.combo_layer = QComboBox()
        default_index = 0
        for idx, layer in enumerate(self.layers):
            self.combo_layer.addItem(f"{layer.name} [{layer.mode}]", layer.id)
            if "découpe" in layer.mode.lower() or "cut" in layer.mode.lower():
                default_index = idx
        if self.combo_layer.count() > 0:
            self.combo_layer.setCurrentIndex(default_index)
        form.addRow("Calque de découpe :", self.combo_layer)

        # Dimensions : spinbox standards (flèches OK ici, champ principal)
        self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(1, 3000); self.spin_w.setDecimals(2)
        self.spin_w.setValue(self.def_w); self.spin_w.setSuffix(" mm")
        self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(1, 3000); self.spin_h.setDecimals(2)
        self.spin_h.setValue(self.def_h); self.spin_h.setSuffix(" mm")
        form.addRow("Largeur :", self.spin_w)
        form.addRow("Hauteur :", self.spin_h)

        self.spin_cols = QSpinBox(); self.spin_cols.setRange(2, 50); self.spin_cols.setValue(saved.get("cols", 5))
        self.spin_rows = QSpinBox(); self.spin_rows.setRange(2, 50); self.spin_rows.setValue(saved.get("rows", 4))
        form.addRow("Pièces en largeur :", self.spin_cols)
        form.addRow("Pièces en hauteur :", self.spin_rows)

        self.spin_x = QDoubleSpinBox(); self.spin_x.setRange(0, 3000); self.spin_x.setDecimals(2)
        self.spin_x.setValue(self.def_x); self.spin_x.setSuffix(" mm")
        self.spin_y = QDoubleSpinBox(); self.spin_y.setRange(0, 3000); self.spin_y.setDecimals(2)
        self.spin_y.setValue(self.def_y); self.spin_y.setSuffix(" mm")
        form.addRow("Position X :", self.spin_x)
        form.addRow("Position Y :", self.spin_y)
        left.addLayout(form)

        self.grp_shape = QGroupBox("Forme du tenon (Classique)")
        shape_lay = QVBoxLayout(self.grp_shape)

        def pm(label, lo, hi, key, default, step=0.01):
            w = PlusMinusRow(label, lo, hi, saved.get(key, default), step=step)
            w.changed.connect(self._update_preview)
            shape_lay.addWidget(w)
            return w

        self.row_depth = pm("Profondeur", 0.14, 0.34, "tab_depth", 0.22)
        self.row_span = pm("Largeur zone", 0.22, 0.46, "tab_span", 0.34)
        self.row_neck = pm("Largeur du col", 0.32, 0.60, "neck_width", 0.45)
        self.row_pos = pm("Position aléatoire", 0.00, 1.00, "pos_random", 0.60, 0.05)
        self.row_jitter = pm("Variation taille", 0.00, 0.30, "jitter", 0.10)
        left.addWidget(self.grp_shape)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        left.addWidget(buttons)

        right = QVBoxLayout()
        right.addWidget(QLabel("Aperçu :"))
        self.preview = TabShapePreview()
        right.addWidget(self.preview, 1)
        hint = QLabel(
            "Forme du tenon : réglage avec − et +.\n"
            "Col étroit + tête ronde = puzzle classique."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b93a7; font-size: 12px;")
        right.addWidget(hint)

        root.addLayout(left, 3)
        root.addLayout(right, 4)
        self.combo_style.currentIndexChanged.connect(self._update_preview)
        self._on_style_changed()
        self._update_preview()

    def _on_style_changed(self):
        self.grp_shape.setEnabled(self.combo_style.currentData() == "Classique")

    def _update_preview(self):
        self.preview.set_params(
            style=self.combo_style.currentData(),
            tab_depth=self.row_depth.value(),
            tab_span=self.row_span.value(),
            neck_width=self.row_neck.value(),
        )

    def cut_layer_id(self):
        return self.combo_layer.currentData()

    def params(self):
        return PuzzleParams(
            width=self.spin_w.value(),
            height=self.spin_h.value(),
            nx=self.spin_cols.value(),
            ny=self.spin_rows.value(),
            x=self.spin_x.value(),
            y=self.spin_y.value(),
            style=self.combo_style.currentData(),
            cut_layer_id=self.cut_layer_id(),
            tab_depth=self.row_depth.value(),
            tab_span=self.row_span.value(),
            neck_width=self.row_neck.value(),
            pos_random=self.row_pos.value(),
            jitter=self.row_jitter.value(),
        )

    def settings(self):
        return {
            "style": self.combo_style.currentData(),
            "w": self.spin_w.value(),
            "h": self.spin_h.value(),
            "cols": self.spin_cols.value(),
            "rows": self.spin_rows.value(),
            "x": self.spin_x.value(),
            "y": self.spin_y.value(),
            "tab_depth": self.row_depth.value(),
            "tab_span": self.row_span.value(),
            "neck_width": self.row_neck.value(),
            "pos_random": self.row_pos.value(),
            "jitter": self.row_jitter.value(),
        }
