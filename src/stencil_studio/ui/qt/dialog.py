"""Stencil Studio en widgets Qt (expérimental) : le parcours principal de la page web, image -> réglages ->
aperçu -> export vers Laser Studio, sur le même calcul (controllers/service.py) et les mêmes réglages
(spec.py, lus dans la page).

    dialog = QStencilDialog(parent, language="fr")
    dialog.export_ready.connect(import_in_lsp)          # chemin d'un SVG, comme la version web
    dialog.show()

Les calculs tournent dans un fil à part : la fenêtre ne se fige pas. Un aperçu dépassé par un réglage plus
récent est abandonné (comme dans la page : numéro de demande « seq »).
"""
import io
import os
import tempfile
import threading

import numpy as np
from PIL import Image
from PyQt6.QtCore import QByteArray, QObject, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QSizePolicy, QSplitter, QToolButton, QVBoxLayout, QWidget)

from ... import spec as spec_module
from ...controllers.service import StudioService
from ...i18n import load_catalog
from ...models.frame import centered_frame
from ...models.session import StudioSession
from .controls import SettingsForm

PREVIEW_DELAY_MS = 140          # réglages regroupés avant de relancer l'aperçu, comme la page (schedule)
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"


def to_qimage(rgb):
    """Tableau RGB (h, w, 3) -> QImage (copie : indépendante du tableau)."""
    rgb = np.ascontiguousarray(rgb[..., :3])
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


def mode_icon(path, color):
    """Icône d'un mode de la page (tracé SVG 24 px), dessinée dans la couleur du texte."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{path}</svg>')
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pixmap)


class ImageView(QLabel):
    """Image (photo ou aperçu) toujours ajustée à la place disponible, proportions gardées."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(200, 200)
        self.setWordWrap(True)

    def set_image(self, qimage):
        self._pixmap = QPixmap.fromImage(qimage)
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        if self._pixmap is not None:
            self.setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))


class _Results(QObject):
    """Résultats des calculs, du fil de calcul vers la fenêtre."""
    preview = pyqtSignal(dict)
    export = pyqtSignal(dict)
    failed = pyqtSignal(str)


class QStencilDialog(QDialog):
    """`language` : langue des textes (catalogue de la page). Émet export_ready(chemin du SVG)."""

    export_ready = pyqtSignal(str)

    def __init__(self, parent=None, language="en", service=None):
        super().__init__(parent)
        self.setWindowTitle("Stencil Studio (Qt)")
        self.resize(1300, 820)
        catalog = load_catalog(language)
        self.tr_ = lambda text, **kw: (catalog.get(text, text).format(**kw) if kw else catalog.get(text, text))
        self.language = language
        self.spec = spec_module.load()
        self.state = self.spec.defaults()
        self.service = service or StudioService(StudioSession())
        self._seq = 0
        self._results = _Results(self)
        self._results.preview.connect(self._show_preview)
        self._results.export.connect(self._deliver_export)
        self._results.failed.connect(lambda msg: self.status.setText(self.tr_("Error: {msg}", msg=msg)))
        self._timer = QTimer(self, singleShot=True, interval=PREVIEW_DELAY_MS)
        self._timer.timeout.connect(self._send_preview)

        self.form = SettingsForm(self.spec, self.tr_)
        self.form.changed.connect(self._changed)
        settings = QScrollArea()
        settings.setWidgetResizable(True)
        settings.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        settings.setWidget(self.form)
        settings.setMinimumWidth(380)
        self.source_view = ImageView(self.tr_("Open an image to start (or drop it on this window)."))
        self.result_view = ImageView()
        views = QSplitter(Qt.Orientation.Horizontal)
        views.addWidget(self._titled(self.tr_("Original"), self.source_view))
        views.addWidget(self._titled(self.tr_("Result"), self.result_view))
        self.status = QLabel()
        self.status.setWordWrap(True)
        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(settings)
        body.addWidget(views)
        body.setStretchFactor(1, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(self._top_row())
        layout.addWidget(body, 1)
        layout.addWidget(self.status)
        self.setAcceptDrops(True)
        self._set_mode(self.state.get("output") or "stencil")

    # -- construction

    def _top_row(self):
        """Ouvrir une image, les modes de la page (boutons à icône), puis l'export."""
        row = QHBoxLayout()
        open_button = QPushButton(self.tr_("Open image..."))
        open_button.clicked.connect(self.open_dialog)
        row.addWidget(open_button)
        self.mode_buttons = QButtonGroup(self)
        self.mode_buttons.setExclusive(True)
        color = QApplication.palette().color(QPalette.ColorRole.WindowText).name()
        for mode in self.spec.modes:
            button = QToolButton()
            button.setText(self.tr_(mode["label"]))
            button.setToolTip(self.tr_(mode["tip"]))
            button.setIcon(mode_icon(mode["ic"], color))
            button.setIconSize(QSize(22, 22))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setCheckable(True)
            button.setProperty("mode", mode["id"])
            self.mode_buttons.addButton(button)
            row.addWidget(button)
        self.mode_buttons.buttonClicked.connect(lambda b: self._changed("output", b.property("mode")))
        row.addStretch()
        self.export_button = QPushButton(self.tr_("Export SVG"))
        self.export_button.setProperty("role", "primary")
        self.export_button.clicked.connect(self.export_svg)
        row.addWidget(self.export_button)
        return row

    @staticmethod
    def _titled(title, widget):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"<b>{title}</b>"))
        layout.addWidget(widget, 1)
        return box

    # -- image

    def open_dialog(self):
        path, _filter = QFileDialog.getOpenFileName(self, self.tr_("Open image..."), "", IMAGE_FILTER)
        if path:
            self.open_path(path)

    def open_path(self, path):
        with open(path, "rb") as f:
            self.load_image(f.read(), os.path.basename(path))

    def load_image(self, data, name):
        """Image de la session (octets d'un fichier image) ; la photo s'affiche et l'aperçu se calcule."""
        try:
            self.service.load_image(data, name)
        except Exception as error:          # fichier illisible : message, la fenêtre reste utilisable
            self.status.setText(self.tr_("Error: {msg}", msg=str(error)))
            return
        self.source_view.set_image(to_qimage(self.service.session.disp_rgb))
        self.schedule()

    def _blank_image(self):
        """Le QR code n'a pas besoin de photo : une page blanche, comme la page web (makeBlankImage)."""
        buf = io.BytesIO()
        Image.new("RGB", (1000, 1000), "white").save(buf, "PNG")
        self.load_image(buf.getvalue(), "qr.png")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile():
                self.open_path(url.toLocalFile())
                break

    # -- réglages

    def _set_mode(self, mode):
        for button in self.mode_buttons.buttons():
            button.setChecked(button.property("mode") == mode)
        self.form.show_mode(mode)

    def _changed(self, key, value):
        self.state[key] = value
        if key == "output":
            self._set_mode(value)
            if value == "qr" and not self.service.session.has_image():
                self._blank_image()
                return
        self.schedule()

    def request(self, work, view="result"):
        """Demande au calcul, comme la page (payload) : réglages, cadre, sujet, vue, résolution."""
        s = self.state
        iw, ih = self.service.session.img.size
        self._seq += 1
        return {"seq": self._seq, "params": self.spec.request_params(s), "frame": centered_frame(s, iw, ih),
                "isolate": bool(s.get("isolate")), "margin": s.get("margin"), "mbr": [], "lpg": {"pts": [], "edges": []},
                "view": view, "work": work, "moving": False, "box": None,
                "style": {"material": s.get("material"), "backlight": bool(s.get("backlight")),
                          "light": s.get("lightcolor"), "lang": self.language}}

    # -- aperçu et export (fil de calcul)

    def schedule(self):
        self._timer.start()

    def _send_preview(self):
        if not self.service.session.has_image():
            return
        req = self.request(int(self.state.get("previewRes") or 1200))
        self.status.setText(self.tr_("Computing..."))
        self._run(lambda: self.service.preview_result(req), self._results.preview)

    def _run(self, job, signal):
        def target():
            try:
                signal.emit(job())
            except Exception as error:      # calcul en échec : message dans la fenêtre, pas de plantage
                self._results.failed.emit(str(error))
        threading.Thread(target=target, name="qstencil-calcul", daemon=True).start()

    def _show_preview(self, out):
        if out.get("stale") or out.get("seq") != self._seq:
            return                          # un réglage plus récent a relancé l'aperçu
        self.result_view.set_image(to_qimage(out["image"]))
        self.status.setText(self.stats_text(out.get("stats") or {}))

    def stats_text(self, stats):
        parts = []
        if stats.get("w_mm"):
            parts.append(f"{stats['w_mm']:.1f} x {stats['h_mm']:.1f} mm")
        if stats.get("contours") is not None:
            parts.append(self.tr_("{n} contours", n=stats["contours"]))
        if stats.get("length_mm"):
            parts.append(self.tr_("Cut length: {mm} mm", mm=round(stats["length_mm"])))
        return " · ".join(parts)

    def export_svg(self):
        """Export SVG vers Laser Studio, comme « Exporter en SVG » de la page dans Laser Studio."""
        if not self.service.session.has_image():
            self.status.setText(self.tr_("Open an image first."))
            return
        req = self.request(int(self.state.get("exportRes") or 1200))
        self.status.setText(self.tr_("Exporting..."))
        self._run(lambda: self.service.export_result(req), self._results.export)

    def _deliver_export(self, out):
        name = (out.get("name") or "stencil") + "_cut.svg"
        path = os.path.join(tempfile.mkdtemp(prefix="qstencil-"), name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(out["svg"])
        self.status.setText(self.stats_text(out.get("stats") or {}) + " · " + self.tr_("Saved: {name}", name=name))
        self.export_ready.emit(path)
