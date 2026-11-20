"""Dialogue « Boule de Noël » : prénom, police, accroche, motifs, aperçu en direct des contours à découper."""
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.models.layers import ENGRAVE_MODE, layer_label
from laser_studio.vector import ornament_generator as og
from laser_studio.vector import ornament_presets
from laser_studio.vector.ornament_region import build_ornament_parts

# Couleurs de l'aperçu : la découpe en rouge (comme le laser la suit), la gravure en bleu.
CUT_COLOR = QColor("#ff4b4b")
ENGRAVE_COLOR = QColor("#5aa9ff")


def _contours_path(contours, ox, oy, s):
    path = QPainterPath()
    for contour in contours:
        path.moveTo(ox + contour[0][0] * s, oy - contour[0][1] * s)
        for x, y in contour[1:]:
            path.lineTo(ox + x * s, oy - y * s)
        path.closeSubpath()
    path.setFillRule(Qt.FillRule.OddEvenFill)
    return path


def paint_parts(p, rect, cut, name=(), frame=(), pad=14, line=1.6):
    """Dessine la découpe (rouge) et la gravure (bleu) centrées dans `rect`, Y vers le haut. Sert à l'aperçu comme
    aux vignettes de la galerie."""
    allc = list(cut)
    if not allc:
        return
    xs = [pt[0] for c in allc for pt in c]
    ys = [pt[1] for c in allc for pt in c]
    w, h = max(max(xs), 1e-6), max(max(ys), 1e-6)
    s = min((rect.width() - 2 * pad) / w, (rect.height() - 2 * pad) / h)
    ox = rect.left() + (rect.width() - w * s) / 2
    oy = rect.top() + (rect.height() - h * s) / 2 + h * s  # Y vers le haut : on retourne
    p.setBrush(QColor(201, 164, 107, 70))
    p.setPen(QPen(CUT_COLOR, line))
    p.drawPath(_contours_path(allc, ox, oy, s))
    if name:
        p.setBrush(ENGRAVE_COLOR)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(_contours_path(name, ox, oy, s))
    if frame:
        p.setBrush(ENGRAVE_COLOR)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(_contours_path(frame, ox, oy, s))


def render_thumbnail(parts, size):
    """Vignette `size`×`size` d'un modèle (`OrnamentParts`)."""
    pix = QPixmap(size, size)
    pix.fill(QColor("#1a1d24"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint_parts(p, pix.rect(), parts.cut, parts.name, parts.frame, pad=8, line=1.2)
    p.end()
    return pix


class OrnamentPreview(QWidget):
    """Contours exactement tels que le laser les suivra (après soudure), Y vers le haut : la découpe en rouge, le
    prénom gravé et le filet en bleu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 360)
        self.contours = []
        self.name = []
        self.frame = []
        self.message = ""

    def set_contours(self, contours, message="", name=(), frame=()):
        self.contours = contours
        self.name = list(name)
        self.frame = list(frame)
        self.message = message
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1a1d24"))
        paint_parts(p, self.rect(), self.contours, self.name, self.frame)
        if self.message:
            p.setPen(QColor("#ffb86b"))
            p.drawText(self.rect().adjusted(10, 8, -10, -8), Qt.AlignmentFlag.AlignTop.value | Qt.TextFlag.TextWordWrap.value,
                       self.message)
        p.end()


class OrnamentGalleryDialog(QDialog):
    """Galerie des modèles : une vignette par modèle, dessinée avec le prénom, la police et les dimensions du
    moment. Un double-clic (ou OK) choisit le modèle ; `selected_key()` le donne."""

    THUMB = 128

    def __init__(self, parent=None, name="", family="Sans Serif", bold=True, italic=False, diameter=80.0,
                 ring_width=4.0):
        super().__init__(parent)
        self.setWindowTitle(tr("ornament.gallery.title"))
        self.resize(780, 560)
        layout = QVBoxLayout(self)
        hint = QLabel(tr("ornament.gallery.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b93a7; font-size: 12px;")
        layout.addWidget(hint)
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setWordWrap(True)
        self.list.setIconSize(QSize(self.THUMB, self.THUMB))
        self.list.setGridSize(QSize(self.THUMB + 24, self.THUMB + 44))
        self.list.setSpacing(6)
        layout.addWidget(self.list, 1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        self.list.itemSelectionChanged.connect(
            lambda: self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(self.list.selectedItems())))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._fill(name or "Emma", family, bold, italic, diameter, ring_width)

    def _fill(self, name, family, bold, italic, diameter, ring_width):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for preset in ornament_presets.PRESETS:
                settings = dict(preset.settings)
                settings.update(diameter=diameter, ring_width=ring_width, name=name)
                try:
                    parts = build_ornament_parts(og.OrnamentParams(**settings), family, bold, italic)
                except og.OrnamentError:
                    continue
                item = QListWidgetItem(QIcon(render_thumbnail(parts, self.THUMB)), tr(f"ornament.preset.{preset.key}"))
                item.setData(Qt.ItemDataRole.UserRole, preset.key)
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                self.list.addItem(item)
        finally:
            QApplication.restoreOverrideCursor()

    def selected_key(self):
        items = self.list.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None


class OrnamentGeneratorDialog(QDialog):
    def __init__(self, parent=None, layers=None, saved_settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr("ornament.title"))
        self.resize(1100, 760)
        # Plein écran par défaut : le formulaire est long et l'aperçu gagne à être grand. Les boutons OK / Annuler
        # restent hors de la zone défilante, donc toujours visibles, quelle que soit la taille de l'écran.
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self.layers = layers or []
        saved = saved_settings or {}

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        self.btn_gallery = QPushButton(tr("ornament.gallery.button"))
        self.btn_gallery.setToolTip(tr("ornament.gallery.tip"))
        self.btn_gallery.clicked.connect(self._open_gallery)
        left.addWidget(self.btn_gallery)
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

        self.combo_name_mode = QComboBox()
        for key in og.NAME_MODES:
            self.combo_name_mode.addItem(tr(f"ornament.name_mode.{key}"), key)
        self._select(self.combo_name_mode, saved.get("name_mode", "Découpé"))
        self.combo_name_mode.setToolTip(tr("ornament.name_mode_tip"))
        form.addRow(tr("ornament.name_mode"), self.combo_name_mode)

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
        self.combo_crown = QComboBox()
        for key in og.CROWNS:
            self.combo_crown.addItem(tr(f"ornament.crown.{key}"), key)
        self._select(self.combo_crown, saved.get("crown", "Aucune"))
        form.addRow(tr("ornament.crown"), self.combo_crown)

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
        self.spin_drop = self._spin(-10, 60, saved.get("motif_drop", 0.0), " mm")
        self.spin_drop.setToolTip(tr("ornament.drop_tip"))
        form.addRow(tr("ornament.drop"), self.spin_drop)

        self.combo_fill = QComboBox()
        for key in og.FILLS:
            self.combo_fill.addItem(tr(f"ornament.fill.{key}"), key)
        self._select(self.combo_fill, saved.get("fill", "Aucun"))
        form.addRow(tr("ornament.fill"), self.combo_fill)
        self.combo_fill_zone = QComboBox()
        for key in og.FILL_ZONES:
            self.combo_fill_zone.addItem(tr(f"ornament.fill_zone.{key}"), key)
        self._select(self.combo_fill_zone, saved.get("fill_zone", "Haut et bas"))
        form.addRow(tr("ornament.fill_zone"), self.combo_fill_zone)
        self.spin_fill_pitch = self._spin(4.5, 120, saved.get("fill_pitch", 6.0), " mm")
        form.addRow(tr("ornament.fill_pitch"), self.spin_fill_pitch)

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
        self.spin_band = self._spin(0, 240, saved.get("band_height", 0.0), " mm")
        self.spin_band.setSpecialValueText(tr("ornament.auto"))   # 0 = automatique
        form.addRow(tr("ornament.band_height"), self.spin_band)
        self.chk_frame = QCheckBox(tr("ornament.band_frame"))
        self.chk_frame.setChecked(saved.get("band_frame", False))
        form.addRow("", self.chk_frame)

        self.combo_layer = QComboBox()
        default_index = 0
        for idx, layer in enumerate(self.layers):
            self.combo_layer.addItem(layer_label(layer), layer.id)
            if "découpe" in layer.mode.lower() or "cut" in layer.mode.lower():
                default_index = idx
        if self.combo_layer.count() > 0:
            self.combo_layer.setCurrentIndex(default_index)
        form.addRow(tr("ornament.layer"), self.combo_layer)
        self.combo_engrave_layer = QComboBox()
        engrave_index = 0
        for idx, layer in enumerate(self.layers):
            self.combo_engrave_layer.addItem(layer_label(layer), layer.id)
            if layer.mode == ENGRAVE_MODE:
                engrave_index = idx
        if self.combo_engrave_layer.count() > 0:
            self.combo_engrave_layer.setCurrentIndex(engrave_index)
        form.addRow(tr("ornament.engrave_layer"), self.combo_engrave_layer)
        left.addLayout(form)

        self.lbl_warning = QLabel()
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setStyleSheet("color: #ffb86b;")
        left.addWidget(self.lbl_warning)
        left.addStretch(1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        # Le formulaire défile ; les boutons restent fixes en bas de la colonne.
        left_host = QWidget()
        left_host.setLayout(left)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(left_host)
        left_column = QVBoxLayout()
        left_column.addWidget(scroll, 1)
        left_column.addWidget(self.buttons)

        right = QVBoxLayout()
        right.addWidget(QLabel(tr("ornament.preview")))
        self.preview = OrnamentPreview()
        right.addWidget(self.preview, 1)
        hint = QLabel(tr("ornament.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b93a7; font-size: 12px;")
        right.addWidget(hint)
        root.addLayout(left_column, 4)
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
            (self.spin_count, "valueChanged"), (self.spin_flake, "valueChanged"), (self.spin_drop, "valueChanged"),
            (self.chk_auto_offset, "toggled"), (self.spin_offset, "valueChanged"),
            (self.chk_auto_size, "toggled"), (self.spin_size, "valueChanged"),
            (self.combo_support, "currentIndexChanged"), (self.combo_name_mode, "currentIndexChanged"),
            (self.spin_band, "valueChanged"), (self.chk_frame, "toggled"), (self.combo_crown, "currentIndexChanged"),
            (self.combo_fill, "currentIndexChanged"), (self.combo_fill_zone, "currentIndexChanged"),
            (self.spin_fill_pitch, "valueChanged"),
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
        self.spin_drop.setValue(0.0)   # le bon décalage dépend du motif : on repart de zéro

    def _schedule(self, *_args):
        self._timer.start()

    def _open_gallery(self):
        family, bold, italic = self.font_options()
        gallery = OrnamentGalleryDialog(self, self.edit_name.text().strip(), family, bold, italic,
                                        self.spin_d.value(), self.spin_ring.value())
        if gallery.exec() == QDialog.DialogCode.Accepted and gallery.selected_key():
            self.apply_preset(gallery.selected_key())

    def apply_preset(self, key):
        """Recopie les réglages d'un modèle dans le formulaire (prénom, police, dimensions et calques restent)."""
        preset = ornament_presets.BY_KEY.get(key)
        if preset is None:
            return
        s = preset.settings
        # Le motif d'abord : en changer remet la taille et le décalage par défaut, qu'on écrase ensuite.
        self._select(self.combo_motif, s["motif"])
        self._fill_styles(s.get("flake_style"))
        self._select(self.combo_layout, s["flake_layout"])
        self.spin_count.setValue(s["flake_count"])
        self.spin_flake.setValue(s["flake_size"])
        self.spin_drop.setValue(s["motif_drop"])
        self._select(self.combo_name_mode, s["name_mode"])
        self._select(self.combo_support, s["support"])
        self.spin_band.setValue(s["band_height"])
        self.chk_frame.setChecked(bool(s["band_frame"]))
        self._select(self.combo_crown, s["crown"])
        self._select(self.combo_fill, s["fill"])
        self._select(self.combo_fill_zone, s["fill_zone"])
        self.spin_fill_pitch.setValue(s["fill_pitch"])
        self._select(self.combo_hanger, s["hanger"])
        self.chk_auto_offset.setChecked(s["name_offset"] is None)
        if s["name_offset"] is not None:
            self.spin_offset.setValue(s["name_offset"])
        self.chk_auto_size.setChecked(not s["name_size"])
        if s["name_size"]:
            self.spin_size.setValue(s["name_size"])
        self._update_preview()

    # -- état ----------------------------------------------------------------------------------------------
    def cut_layer_id(self):
        return self.combo_layer.currentData()

    def engrave_layer_id(self):
        return self.combo_engrave_layer.currentData()

    def is_engraved(self):
        return self.combo_name_mode.currentData() == "Gravé"

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
            motif_drop=self.spin_drop.value(), name_mode=self.combo_name_mode.currentData(),
            band_height=self.spin_band.value(), band_frame=self.chk_frame.isChecked(),
            crown=self.combo_crown.currentData(), fill=self.combo_fill.currentData(),
            fill_zone=self.combo_fill_zone.currentData(), fill_pitch=self.spin_fill_pitch.value(),
        )

    def settings(self):
        p = self.params()
        family, bold, italic = self.font_options()
        return {
            "name": p.name, "font": family, "bold": bold, "italic": italic, "diameter": p.diameter,
            "ring_width": p.ring_width, "hanger": p.hanger, "hole_diameter": p.hole_diameter,
            "motif": p.motif, "flake_layout": p.flake_layout, "flake_style": p.flake_style,
            "flake_count": p.flake_count, "flake_size": p.flake_size, "name_offset": p.name_offset,
            "name_size": p.name_size, "support": p.support, "motif_drop": p.motif_drop,
            "name_mode": p.name_mode, "band_height": p.band_height, "band_frame": p.band_frame,
            "crown": p.crown, "fill": p.fill, "fill_zone": p.fill_zone, "fill_pitch": p.fill_pitch,
        }

    def _update_preview(self):
        self.spin_offset.setEnabled(not self.chk_auto_offset.isChecked())
        self.spin_size.setEnabled(not self.chk_auto_size.isChecked())
        flakes = self.combo_motif.currentData() != "Aucun"
        for widget in (self.combo_layout, self.combo_style, self.spin_count, self.spin_flake):
            widget.setEnabled(flakes)
        # La guirlande va toujours en haut, d'un côté à l'autre : la disposition ne s'applique pas.
        self.combo_layout.setEnabled(flakes and self.combo_motif.currentData() != "Guirlande")
        self.spin_drop.setEnabled(flakes and self.combo_motif.currentData() != "Guirlande")
        self.spin_hole.setEnabled(self.combo_hanger.currentData() != "Aucun")
        engraved = self.is_engraved()
        # Prénom gravé : la bande remplace les barres ; le calque de gravure et le filet n'ont de sens que là.
        self.combo_support.setEnabled(not engraved)
        self.spin_band.setEnabled(engraved)
        self.chk_frame.setEnabled(engraved)
        self.combo_engrave_layer.setEnabled(engraved)
        filled = self.combo_fill.currentData() != "Aucun"
        self.combo_fill_zone.setEnabled(filled)
        self.spin_fill_pitch.setEnabled(filled)
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        try:
            family, bold, italic = self.font_options()
            parts = build_ornament_parts(self.params(), family, bold, italic)
            geometry, contours = parts.geometry, parts.cut
        except og.OrnamentError as e:
            self.preview.set_contours([], error_text(e))
            self.lbl_warning.clear()
            ok.setEnabled(False)
            return
        self.preview.set_contours(contours, name=parts.name, frame=parts.frame)
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
