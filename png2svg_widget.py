"""
png2svg_widget.py
------------------
Widget de conversion PNG -> SVG intégré à Laser Studio Pro, sous forme
d'onglet dans main_tabs_view (voir png2svg_mixin.py).

Adapté de l'outil autonome PNG -> SVG : la traduction et la persistance
des réglages UI utilisent maintenant les mêmes mécanismes que le reste
de Laser Studio Pro (i18n.py commun, QSettings "LaserStudioPro"), et il
n'y a plus de sélecteur de langue propre au widget — la langue est
globale à l'application (menu Langue, redémarrage requis).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QByteArray, QSettings, QRectF
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QSlider,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QFileDialog, QMessageBox, QSplitter,
    QScrollArea, QGraphicsView, QGraphicsScene,
)

try:
    from PyQt6.QtSvgWidgets import QGraphicsSvgItem
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG_WIDGET = True
except ImportError:
    _HAS_SVG_WIDGET = False

from converter import ConversionSettings, convert_image_to_svg, save_svg
from i18n import tr


class ZoomableSvgView(QGraphicsView):
    """Aperçu SVG avec zoom (molette ou boutons) et déplacement (glisser)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._svg_item = QGraphicsSvgItem()
        self._renderer: QSvgRenderer | None = None
        self._scene.addItem(self._svg_item)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(Qt.GlobalColor.white)
        self._has_content = False

    def load_svg_bytes(self, svg_bytes: bytes):
        self._renderer = QSvgRenderer(QByteArray(svg_bytes))
        self._svg_item.setSharedRenderer(self._renderer)
        rect = self._svg_item.boundingRect()
        if rect.isEmpty():
            rect = QRectF(0, 0, 1, 1)
        self._scene.setSceneRect(rect)
        was_empty = not self._has_content
        self._has_content = True
        if was_empty:
            self.zoom_fit()

    def zoom_fit(self):
        if self._scene.sceneRect().isEmpty():
            return
        self.resetTransform()
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self.scale(0.8, 0.8)

    def wheelEvent(self, event):
        if not self._has_content:
            return
        factor = 1.15 if event.angleDelta().y() > 0 else (1 / 1.15)
        self.scale(factor, factor)


class PngToSvgWidget(QWidget):
    """Widget de conversion PNG -> SVG, intégré comme onglet de Laser Studio Pro."""

    svgGenerated = pyqtSignal(str)       # émis à chaque régénération réussie du SVG
    sendToVectorEditor = pyqtSignal(str)  # émis quand l'utilisateur clique "Envoyer vers l'Éditeur Vectoriel"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path: str | None = None
        self.last_result = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._regenerate)
        self.settings = QSettings("LaserStudioPro", "UIConfig")

        self._build_ui()
        self._retranslate()
        self._restore_ui_state()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QHBoxLayout(self)

        # ---- Panneau de gauche : réglages ----
        left = QVBoxLayout()

        self.btn_open = QPushButton()
        self.btn_open.clicked.connect(self._on_open)
        left.addWidget(self.btn_open)

        self.group_settings = QGroupBox()
        form = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.currentIndexChanged.connect(self._queue_update)

        self.render_combo = QComboBox()
        self.render_combo.currentIndexChanged.connect(self._queue_update)

        self.centerline_chk = QCheckBox()
        self.centerline_chk.toggled.connect(self._on_centerline_toggled)

        self.stroke_width_spin = QDoubleSpinBox()
        self.stroke_width_spin.setRange(0.01, 5.0)
        self.stroke_width_spin.setSingleStep(0.05)
        self.stroke_width_spin.setValue(0.1)
        self.stroke_width_spin.setDecimals(2)
        self.stroke_width_spin.valueChanged.connect(self._queue_update)

        self.fill_threshold_spin = QSpinBox()
        self.fill_threshold_spin.setRange(2, 100)
        self.fill_threshold_spin.setValue(8)
        self.fill_threshold_spin.setEnabled(False)
        self.fill_threshold_spin.valueChanged.connect(self._queue_update)

        self.auto_threshold_chk = QCheckBox()
        self.auto_threshold_chk.setChecked(True)
        self.auto_threshold_chk.toggled.connect(self._on_auto_threshold_toggled)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.setEnabled(False)
        self.threshold_slider.valueChanged.connect(self._queue_update)

        self.invert_chk = QCheckBox()
        self.invert_chk.toggled.connect(self._queue_update)

        self.blur_spin = QSpinBox()
        self.blur_spin.setRange(0, 20)
        self.blur_spin.valueChanged.connect(self._queue_update)

        self.simplify_spin = QDoubleSpinBox()
        self.simplify_spin.setRange(0.0, 10.0)
        self.simplify_spin.setSingleStep(0.1)
        self.simplify_spin.setValue(1.0)
        self.simplify_spin.valueChanged.connect(self._queue_update)

        self.min_area_spin = QDoubleSpinBox()
        self.min_area_spin.setRange(0.0, 500.0)
        self.min_area_spin.setValue(6.0)
        self.min_area_spin.valueChanged.connect(self._queue_update)

        self.n_colors_spin = QSpinBox()
        self.n_colors_spin.setRange(2, 32)
        self.n_colors_spin.setValue(6)
        self.n_colors_spin.setEnabled(False)
        self.n_colors_spin.valueChanged.connect(self._queue_update)

        self.mode_combo.currentIndexChanged.connect(
            lambda i: self.n_colors_spin.setEnabled(i == 1)
        )
        self.mode_combo.currentIndexChanged.connect(
            lambda i: self.centerline_chk.setEnabled(i == 0)
        )

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.1, 5000.0)
        self.width_spin.setValue(50.0)
        self.width_spin.valueChanged.connect(self._on_width_changed)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.1, 5000.0)
        self.height_spin.setValue(50.0)
        self.height_spin.valueChanged.connect(self._on_height_changed)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["mm", "cm", "in"])
        self.unit_combo.currentIndexChanged.connect(self._queue_update)

        self.keep_ratio_chk = QCheckBox()
        self.keep_ratio_chk.setChecked(True)

        self.lbl_mode = QLabel()
        self.lbl_render = QLabel()
        self.lbl_stroke_width = QLabel()
        self.lbl_fill_threshold = QLabel()
        self.lbl_threshold = QLabel()
        self.lbl_invert = QLabel()
        self.lbl_blur = QLabel()
        self.lbl_simplify = QLabel()
        self.lbl_min_area = QLabel()
        self.lbl_n_colors = QLabel()
        self.lbl_width = QLabel()
        self.lbl_height = QLabel()
        self.lbl_unit = QLabel()

        form.addRow(self.lbl_mode, self.mode_combo)
        form.addRow(self.lbl_render, self.render_combo)
        form.addRow(self.centerline_chk)
        form.addRow(self.lbl_fill_threshold, self.fill_threshold_spin)
        form.addRow(self.lbl_stroke_width, self.stroke_width_spin)
        form.addRow(self.auto_threshold_chk)
        form.addRow(self.lbl_threshold, self.threshold_slider)
        form.addRow(self.lbl_invert, self.invert_chk)
        form.addRow(self.lbl_blur, self.blur_spin)
        form.addRow(self.lbl_simplify, self.simplify_spin)
        form.addRow(self.lbl_min_area, self.min_area_spin)
        form.addRow(self.lbl_n_colors, self.n_colors_spin)

        self.lbl_output_size_header = QLabel()
        self.lbl_output_size_header.setStyleSheet("font-weight: bold; margin-top: 8px;")
        form.addRow(self.lbl_output_size_header)
        form.addRow(self.lbl_width, self.width_spin)
        form.addRow(self.lbl_height, self.height_spin)
        form.addRow(self.lbl_unit, self.unit_combo)
        form.addRow(self.keep_ratio_chk)

        self.group_settings.setLayout(form)
        left.addWidget(self.group_settings)

        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export.setEnabled(False)
        left.addWidget(self.btn_export)

        self.btn_send_vector = QPushButton()
        self.btn_send_vector.setStyleSheet("background-color: #3a6b3a; color: white;")
        self.btn_send_vector.clicked.connect(self._on_send_to_vector)
        self.btn_send_vector.setEnabled(False)
        left.addWidget(self.btn_send_vector)

        self.status_label = QLabel()
        left.addWidget(self.status_label)
        left.addStretch(1)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMinimumWidth(380)

        # Défilement pour garantir que TOUS les réglages restent accessibles
        # même si la fenêtre est redimensionnée en plus petit.
        left_scroll = QScrollArea()
        left_scroll.setWidget(left_widget)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setMinimumWidth(380)
        left_scroll.setMaximumWidth(560)

        # ---- Panneau de droite : aperçu ----
        right = QVBoxLayout()
        preview_row = QHBoxLayout()

        orig_col = QVBoxLayout()
        self.lbl_original_title = QLabel()
        self.original_view = QLabel()
        self.original_view.setMinimumSize(300, 300)
        self.original_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_view.setStyleSheet("background:#dddddd;")
        orig_col.addWidget(self.lbl_original_title)
        orig_col.addWidget(self.original_view)

        svg_col = QVBoxLayout()
        svg_header = QHBoxLayout()
        self.lbl_svg_title = QLabel()
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_fit = QPushButton()
        self.btn_zoom_in = QPushButton("+")
        for b in (self.btn_zoom_out, self.btn_zoom_fit, self.btn_zoom_in):
            b.setMaximumWidth(60)
        svg_header.addWidget(self.lbl_svg_title)
        svg_header.addStretch(1)
        svg_header.addWidget(self.btn_zoom_out)
        svg_header.addWidget(self.btn_zoom_fit)
        svg_header.addWidget(self.btn_zoom_in)

        if _HAS_SVG_WIDGET:
            self.svg_view = ZoomableSvgView()
            self.btn_zoom_out.clicked.connect(self.svg_view.zoom_out)
            self.btn_zoom_in.clicked.connect(self.svg_view.zoom_in)
            self.btn_zoom_fit.clicked.connect(self.svg_view.zoom_fit)
        else:
            self.svg_view = QLabel("PyQt6.QtSvgWidgets introuvable")
            self.btn_zoom_out.setEnabled(False)
            self.btn_zoom_in.setEnabled(False)
            self.btn_zoom_fit.setEnabled(False)
        self.svg_view.setMinimumSize(300, 300)
        self.svg_view.setStyleSheet("background:#ffffff;")
        svg_col.addLayout(svg_header)
        svg_col.addWidget(self.svg_view)

        preview_row.addLayout(orig_col)
        preview_row.addLayout(svg_col)
        right.addLayout(preview_row)

        right_widget = QWidget()
        right_widget.setLayout(right)

        self.splitter = QSplitter()
        self.splitter.addWidget(left_scroll)
        self.splitter.addWidget(right_widget)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizes([420, 700])
        self.splitter.splitterMoved.connect(self._save_splitter_state)
        root.addWidget(self.splitter)

    def _retranslate(self):
        self.btn_open.setText(tr("png2svg.open_image"))
        self.btn_export.setText(tr("png2svg.export_svg"))
        self.btn_send_vector.setText(tr("png2svg.send_to_vector"))
        self.group_settings.setTitle(tr("png2svg.settings"))
        self.lbl_mode.setText(tr("png2svg.mode"))
        self.lbl_render.setText(tr("png2svg.render_mode"))
        self.centerline_chk.setText(tr("png2svg.centerline"))
        self.lbl_stroke_width.setText(tr("png2svg.stroke_width"))
        self.lbl_fill_threshold.setText(tr("png2svg.fill_threshold"))
        self.lbl_threshold.setText(tr("png2svg.threshold"))
        self.auto_threshold_chk.setText(tr("png2svg.auto_threshold"))
        self.lbl_invert.setText("")
        self.invert_chk.setText(tr("png2svg.invert"))
        self.lbl_blur.setText(tr("png2svg.smoothing"))
        self.lbl_simplify.setText(tr("png2svg.simplify"))
        self.lbl_min_area.setText(tr("png2svg.min_area"))
        self.lbl_n_colors.setText(tr("png2svg.n_colors"))
        self.lbl_output_size_header.setText(tr("png2svg.output_size"))
        self.lbl_width.setText(tr("png2svg.width"))
        self.lbl_height.setText(tr("png2svg.height"))
        self.lbl_unit.setText(tr("png2svg.unit"))
        self.keep_ratio_chk.setText(tr("png2svg.keep_aspect_ratio"))
        self.lbl_original_title.setText(tr("png2svg.original"))
        self.lbl_svg_title.setText(tr("png2svg.svg_preview"))
        self.btn_zoom_fit.setText(tr("png2svg.zoom_fit"))
        self.btn_zoom_in.setToolTip(tr("png2svg.zoom_in"))
        self.btn_zoom_out.setToolTip(tr("png2svg.zoom_out"))

        current_mode = self.mode_combo.currentIndex()
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItem(tr("png2svg.mode_bw"), "bw")
        self.mode_combo.addItem(tr("png2svg.mode_color"), "color")
        self.mode_combo.setCurrentIndex(max(current_mode, 0))
        self.mode_combo.blockSignals(False)

        current_render = self.render_combo.currentIndex()
        self.render_combo.blockSignals(True)
        self.render_combo.clear()
        self.render_combo.addItem(tr("png2svg.render_fill"), "fill")
        self.render_combo.addItem(tr("png2svg.render_outline"), "outline")
        self.render_combo.setCurrentIndex(max(current_render, 0))
        self.render_combo.blockSignals(False)

        if not self.image_path:
            self.status_label.setText(tr("png2svg.no_image"))

    # ------------------------------------------------------- Persistance UI
    def _save_splitter_state(self, *_):
        self.settings.setValue("png2svg_splitter_sizes", self.splitter.sizes())

    def _restore_ui_state(self):
        sizes = self.settings.value("png2svg_splitter_sizes")
        if sizes:
            try:
                self.splitter.setSizes([int(v) for v in sizes])
            except (TypeError, ValueError):
                pass

    # ------------------------------------------------------------- Actions
    def _on_auto_threshold_toggled(self, checked: bool):
        self.threshold_slider.setEnabled(not checked)
        self._queue_update()

    def _on_centerline_toggled(self, checked: bool):
        self.render_combo.setEnabled(not checked)
        self.fill_threshold_spin.setEnabled(checked)
        self._queue_update()

    def _on_width_changed(self, value):
        if self.keep_ratio_chk.isChecked() and self.last_result:
            ratio = self.last_result.image_height_px / self.last_result.image_width_px
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(value * ratio)
            self.height_spin.blockSignals(False)
        self._queue_update()

    def _on_height_changed(self, value):
        if self.keep_ratio_chk.isChecked() and self.last_result:
            ratio = self.last_result.image_width_px / self.last_result.image_height_px
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(value * ratio)
            self.width_spin.blockSignals(False)
        self._queue_update()

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("png2svg.open_image"), "", "PNG (*.png)"
        )
        if not path:
            return
        self.image_path = path
        self.original_view.setPixmap(
            QPixmap(path).scaled(
                self.original_view.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.btn_export.setEnabled(True)
        self._regenerate()

    def _queue_update(self, *_):
        if self.image_path:
            self._debounce.start()

    def _unit_to_mm(self, value: float) -> float:
        unit = self.unit_combo.currentText()
        return {"mm": 1.0, "cm": 10.0, "in": 25.4}[unit] * value

    def _current_settings(self) -> ConversionSettings:
        return ConversionSettings(
            mode=self.mode_combo.currentData() or "bw",
            render_mode=self.render_combo.currentData() or "fill",
            centerline=self.centerline_chk.isChecked(),
            fill_threshold_px=float(self.fill_threshold_spin.value()),
            stroke_width_mm=self.stroke_width_spin.value(),
            threshold=self.threshold_slider.value(),
            auto_threshold=self.auto_threshold_chk.isChecked(),
            invert=self.invert_chk.isChecked(),
            blur=self.blur_spin.value(),
            simplify=self.simplify_spin.value(),
            min_area=self.min_area_spin.value(),
            n_colors=self.n_colors_spin.value(),
            output_width_mm=self._unit_to_mm(self.width_spin.value()),
            output_height_mm=self._unit_to_mm(self.height_spin.value()),
            keep_aspect_ratio=self.keep_ratio_chk.isChecked(),
        )

    def _regenerate(self):
        if not self.image_path:
            return
        try:
            result = convert_image_to_svg(self.image_path, self._current_settings())
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"⚠ {exc}")
            return

        self.last_result = result
        if _HAS_SVG_WIDGET:
            self.svg_view.load_svg_bytes(result.svg_text.encode("utf-8"))
        self.status_label.setText(tr("png2svg.paths_count").format(n=result.path_count))
        self.btn_send_vector.setEnabled(True)
        self.svgGenerated.emit(result.svg_text)

    def _on_export(self):
        if not self.last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("png2svg.export_svg"), "", "SVG (*.svg)"
        )
        if not path:
            return
        if not path.lower().endswith(".svg"):
            path += ".svg"
        save_svg(self.last_result, path)
        QMessageBox.information(self, tr("png2svg.export_svg"), tr("png2svg.export_success"))

    def _on_send_to_vector(self):
        if not self.last_result:
            return
        self.sendToVectorEditor.emit(self.last_result.svg_text)

    def get_svg_text(self) -> str | None:
        """API pratique : récupère le dernier SVG généré."""
        return self.last_result.svg_text if self.last_result else None
