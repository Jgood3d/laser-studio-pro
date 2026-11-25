"""Stencil Studio en widgets Qt (expérimental), sur le même calcul (controllers/service.py) et les mêmes réglages
(spec.py, lus dans la page web) que la version web :

- ouvrir une image (ou la déposer) ; le QR code part d'une page blanche ;
- choisir le mode, un style prédéfini, les réglages (grisés ou masqués selon les autres, comme dans la page) ;
- placer le cadre sur la photo : glisser pour le déplacer, molette pour sa taille, Alt + molette pour le tourner ;
- voir l'aperçu dans la vue choisie (résultat, matière, original, superposition, rendu, caisson, assemblé) ;
- exporter : SVG et DXF vers l'éditeur vectoriel de Laser Studio (export_ready, comme la version web), les
  autres fichiers (gravure PNG, SVG avec image, caisson, diffuseur, test de flexibilité) enregistrés sur le disque.

    dialog = QStencilDialog(parent, language="fr")
    dialog.export_ready.connect(import_in_lsp)
    dialog.show()

Les calculs tournent dans un fil à part : la fenêtre ne se fige pas. Un aperçu dépassé par un réglage plus
récent est abandonné (numéro de demande « seq », comme la page).
"""
import io
import json
import math
import os
import tempfile
import threading

import numpy as np
from PIL import Image
from PyQt6.QtCore import QByteArray, QObject, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QKeySequence, QPainter, QPalette, QPixmap, QShortcut
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSizePolicy, QSplitter, QToolButton,
                             QVBoxLayout, QWidget)

from ... import spec as spec_module
from ...controllers.service import StudioService
from ...i18n import load_catalog
from ...models import frame as frame_model
from ...models.history import History, snapshot
from ...models.session import StudioSession
from .controls import SettingsForm
from .source_view import SourceView

PREVIEW_DELAY_MS = 140          # réglages regroupés avant de relancer l'aperçu, comme la page (schedule)
HISTORY_DELAY_MS = 450          # changements regroupés en une étape d'annulation, comme la page (histNote)
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
# Vues de l'aperçu, comme les boutons de la page : (vue, libellé).
VIEWS = (("result", "Result"), ("material", "Material"), ("original", "Original"), ("overlay", "Overlay"),
         ("render", "Render"), ("box", "Box"), ("assembled", "Assembled"))
# Exports, comme les boutons de la page : (format, libellé, demande « what », clé du fichier, suffixe du nom,
# filtre ; vers Laser Studio ou enregistré). « svg » et « dxf » vont dans l'éditeur vectoriel, comme dans la page.
EXPORTS = (
    ("svg", "Export SVG", None, "svg", "_cut.svg", "SVG (*.svg)"),
    ("dxf", "Export DXF", None, "dxf", "_cut.dxf", "DXF (*.dxf)"),
    ("png", "Export engraving (PNG)", None, "png", "_engrave.png", "PNG (*.png)"),
    ("svgimg", "Export SVG with image", None, "svg_image", "_engrave_cut.svg", "SVG (*.svg)"),
    ("boxsvg", "Export box (SVG)", "box", "box_svg", "_box.svg", "SVG (*.svg)"),
    ("boxdxf", "Export box (DXF)", "box", "box_dxf", "_box.dxf", "DXF (*.dxf)"),
    ("boxpdf", "Diffuser (PDF, actual size)", "box", "diffuser_pdf", "_diffuser.pdf", "PDF (*.pdf)"),
    ("flexsvg", "Flexibility test (SVG)", "flextest", "flex_svg", "_flex_test.svg", "SVG (*.svg)"),
    ("flexdxf", "Flexibility test (DXF)", "flextest", "flex_dxf", "_flex_test.dxf", "DXF (*.dxf)"),
)
TO_LASER_STUDIO = ("svg", "dxf")
# Aperçu avant export d'un fichier qui ne se dessine pas lui-même : son SVG (comme la page).
PREVIEW_KEY = {"dxf": "svg", "boxdxf": "box_svg", "flexdxf": "flex_svg", "boxpdf": "diffuser_svg"}
ENGRAVE_ONLY = ("png", "svgimg")
# Outils de la photo, comme les boutons de la page : (outil, libellé, visible seulement avec « isoler le sujet »).
TOOLS = (("move", "Move frame", False), ("box", "Subject box", False), ("fg", "Subject (green)", True),
         ("bg", "Background (red)", True), ("erase", "Eraser", True))
# Réglages qui changent le cadre (forme, format, taille, rotation, placement libre, zoom).
FRAME_KEYS = ("shape", "aspect", "custom_w", "custom_h", "size_mm", "rot", "free", "zoom")


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
    """Image d'aperçu toujours ajustée à la place disponible, proportions gardées."""

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
    export = pyqtSignal(str, dict)          # (format, fichiers)
    failed = pyqtSignal(str)


class QStencilDialog(QDialog):
    """`language` : langue des textes (catalogue de la page). Émet export_ready(chemin d'un SVG ou d'un DXF)."""

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
        self.view = "result"
        self.service = service or StudioService(StudioSession())
        self._seq = 0
        self._moving = False
        self._results = _Results(self)
        self._results.preview.connect(self._show_preview)
        self._results.export.connect(self._deliver_export)
        self._results.failed.connect(lambda msg: self.status.setText(self.tr_("Error: {msg}", msg=msg)))
        self._timer = QTimer(self, singleShot=True, interval=PREVIEW_DELAY_MS)
        self._timer.timeout.connect(self._send_preview)
        self.history = History()
        self._history_timer = QTimer(self, singleShot=True, interval=HISTORY_DELAY_MS)
        self._history_timer.timeout.connect(self._commit_history)

        self.form = SettingsForm(self.spec, self.tr_)
        self.form.changed.connect(self._changed)
        settings = QScrollArea()
        settings.setWidgetResizable(True)
        settings.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        settings.setWidget(self.form)
        settings.setMinimumWidth(380)
        self.source_view = SourceView(self.state, self.tr_("Open an image to start (or drop it on this window)."))
        self.source_view.frame_changed.connect(self._frame_moved)
        self.source_view.rotation_changed.connect(lambda angle: self._changed("rot", angle, from_view=True))
        self.source_view.subject_box_drawn.connect(self._subject_box_drawn)
        self.source_view.hints_painted.connect(self._hints_painted)
        self.source_view.custom_size_changed.connect(self._custom_size_changed)
        self.source_view.message.connect(lambda text: self.status.setText(self.tr_(text)))
        self.result_view = ImageView()
        views = QSplitter(Qt.Orientation.Horizontal)
        views.addWidget(self._titled(self._tool_row(), self.source_view))
        views.addWidget(self._titled(self._view_combo(), self.result_view))
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
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self.redo)
        self._set_mode(self.state.get("output") or "stencil")

    # -- construction

    def _top_row(self):
        """Ouvrir une image, les modes de la page (boutons à icône), puis les exports."""
        row = QHBoxLayout()
        open_button = QPushButton(self.tr_("Open image..."))
        open_button.clicked.connect(self.open_dialog)
        row.addWidget(open_button)
        self.undo_button, self.redo_button = QToolButton(), QToolButton()
        for button, text, tip, slot in ((self.undo_button, "↶", "Undo (Ctrl+Z)", self.undo),
                                        (self.redo_button, "↷", "Redo (Ctrl+Y)", self.redo)):
            button.setText(text)
            button.setToolTip(self.tr_(tip))
            button.setEnabled(False)
            button.clicked.connect(slot)
            row.addWidget(button)
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
        more = QToolButton()
        more.setText(self.tr_("Export"))
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.export_menu = QMenu(more)
        self.export_actions = {}
        for fmt, label, *_rest in EXPORTS[1:]:
            action = self.export_menu.addAction(self.tr_(label))
            action.triggered.connect(lambda _c=False, f=fmt: self.export(f))
            self.export_actions[fmt] = action
        more.setMenu(self.export_menu)
        row.addWidget(more)
        return row

    def _tool_row(self):
        """Outils de la photo : déplacer le cadre, rectangle du sujet, repères (avec « isoler le sujet »)."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        self.tool_buttons = QButtonGroup(self)
        self.tool_buttons.setExclusive(True)
        for tool, label, _isolate_only in TOOLS:
            button = QToolButton()
            button.setText(self.tr_(label))
            button.setCheckable(True)
            button.setChecked(tool == "move")
            button.setProperty("tool", tool)
            self.tool_buttons.addButton(button)
            row.addWidget(button)
        self.tool_buttons.buttonClicked.connect(lambda b: setattr(self.source_view, "tool", b.property("tool")))
        return box

    def _view_combo(self):
        """Vues de l'aperçu, comme les boutons au-dessus du résultat dans la page."""
        self.view_combo = QComboBox()
        for view, label in VIEWS:
            self.view_combo.addItem(self.tr_(label), view)
        self.view_combo.currentIndexChanged.connect(lambda _i: self.set_view(self.view_combo.currentData()))
        return self.view_combo

    @staticmethod
    def _titled(title, widget):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)
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
        """Image de la session (octets d'un fichier image) ; la photo s'affiche avec le cadre de départ et
        l'aperçu se calcule."""
        try:
            self.service.load_image(data, name)
        except Exception as error:          # fichier illisible : message, la fenêtre reste utilisable
            self.status.setText(self.tr_("Error: {msg}", msg=str(error)))
            return
        self.source_view.set_image(to_qimage(self.service.session.disp_rgb))
        self._sync_zoom()
        self.history.reset(self._snapshot())                # nouvelle image : historique vidé (histReset)
        self._history_buttons()
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

    # -- réglages et cadre

    def _set_mode(self, mode):
        for button in self.mode_buttons.buttons():
            button.setChecked(button.property("mode") == mode)
        self._refresh_form()

    def _refresh_form(self):
        mode = self.state.get("output") or "stencil"
        self.form.show_mode(mode, self.state)
        for fmt in ENGRAVE_ONLY:                           # boutons « eg » de la page : gravure seulement
            self.export_actions[fmt].setEnabled(mode == "engrave")
        isolate = bool(self.state.get("isolate"))
        for button in self.tool_buttons.buttons():         # repères : seulement en isolant le sujet (« isoonly »)
            only = next(t[2] for t in TOOLS if t[0] == button.property("tool"))
            button.setVisible(isolate or not only)
        if not isolate and self.source_view.tool in ("fg", "bg", "erase"):
            self._choose_tool("move")

    def _changed(self, key, value, from_view=False):
        """Un réglage a changé (formulaire, boutons des modes, molette sur la photo), comme changed() de la page."""
        if key == "preset":
            self.apply_preset(value)
            return
        previous_ratio = frame_model.aspect(self.state, self.source_view.iw, self.source_view.ih)
        self.state[key] = value
        if from_view:
            self.form.set_value(key, value)
        if key == "output":
            self._set_mode(value)
            if value == "qr" and not self.service.session.has_image():
                self._blank_image()
                return
        if key == "zoom":
            self.source_view.set_frame({**self.source_view.frame(), "w": float(value)})
        elif key == "img_mm" and self.source_view.iw:
            width = frame_model.width_for_image_mm(self.state, self.source_view.iw, self.source_view.ih, value)
            if width > 1 and not self.state.get("free"):     # image plus petite que le cadre : marges vides
                self.state["free"] = True
                self.form.set_value("free", True)
            self.source_view.set_frame({**self.source_view.frame(), "w": width})
        elif key == "aspect" and value == "custom" and self.state.get("shape") != "circle":
            self._fill_custom_size(previous_ratio)          # pré-rempli avec les dimensions actuelles
        elif key in ("custom_w", "custom_h"):
            size = max(20.0, min(400.0, max(float(self.state["custom_w"]), float(self.state["custom_h"]))))
            self.state["size_mm"] = size
            self.form.set_value("size_mm", size)
        elif key == "size_mm" and self.state.get("aspect") == "custom" and self.state.get("shape") != "circle":
            self._fill_custom_size(frame_model.aspect(self.state, 1, 1))   # l'échelle change, pas le rapport
        if key in FRAME_KEYS and key != "zoom":
            self.source_view.refresh_frame()
        self._sync_zoom()
        self._refresh_form()
        self.schedule()

    def _fill_custom_size(self, ratio):
        """Largeur et hauteur personnalisées pour le rapport `ratio` et la taille actuelle (comme la page)."""
        size = float(self.state["size_mm"])
        cw, ch = (size, size / ratio) if ratio >= 1 else (size * ratio, size)
        for key, value in (("custom_w", round(cw, 1)), ("custom_h", round(ch, 1))):
            self.state[key] = value
            self.form.set_value(key, value)

    def _sync_zoom(self):
        """Réglages « zoom » (largeur du cadre) et « img_mm » (largeur de la photo sur la plaque), d'après le
        cadre, comme clampFrame / syncImgMm de la page."""
        f = self.source_view.frame()
        zoom = round(f["w"], 2)
        self.state["zoom"] = zoom
        self.form.set_value("zoom", zoom)
        if self.source_view.iw:
            mm = frame_model.image_width_mm(self.state, self.source_view.iw, self.source_view.ih, f)
            self.state["img_mm"] = mm
            self.form.set_value("img_mm", mm)

    def _custom_size_changed(self):
        """Poignées ou double-clic sur le cadre : largeur, hauteur et taille du format personnalisé."""
        for key in ("custom_w", "custom_h", "size_mm"):
            self.form.set_value(key, self.state[key])
        self._sync_zoom()

    # -- annuler / refaire

    def _snapshot(self):
        return snapshot(self.state, self.source_view.frame(), self.source_view.subject_box)

    def _commit_history(self):
        if self.service.session.has_image():
            self.history.commit(self._snapshot())
            self._history_buttons()

    def _history_buttons(self):
        self.undo_button.setEnabled(self.history.can_undo())
        self.redo_button.setEnabled(self.history.can_redo())

    def undo(self):
        self._restore(self.history.undo(self._snapshot()))

    def redo(self):
        self._restore(self.history.redo(self._snapshot()))

    def _restore(self, snap):
        """Réglages, cadre et rectangle du sujet d'un état de l'historique (histRestore)."""
        self._history_timer.stop()
        if snap is not None:
            o = json.loads(snap)
            self.state.update(o["S"])
            for key, value in self.state.items():
                self.form.set_value(key, value)
            self.source_view.subject_box = o["B"]
            self.source_view.set_frame(o["F"])
            self._set_mode(self.state.get("output") or "stencil")
            self._sync_zoom()
            self.schedule()
        self._history_buttons()

    def _choose_tool(self, tool):
        self.source_view.tool = tool
        for button in self.tool_buttons.buttons():
            button.setChecked(button.property("tool") == tool)

    def _subject_box_drawn(self, box):
        """Rectangle du sujet tracé : le sujet est isolé et le cadre se règle sur lui (comme la page)."""
        if box and not self.state.get("isolate"):
            self.state["isolate"] = True
            self.form.set_value("isolate", True)
            self._refresh_form()
        if box:
            self.fit_frame_to_box(box)
        self.schedule()

    def fit_frame_to_box(self, box):
        """Cadre réglé sur le rectangle du sujet, 8 % de marge (fitFrameToBox) ; hors cercle, au format usuel le
        plus proche des proportions du sujet."""
        iw, ih = self.source_view.iw, self.source_view.ih
        if self.state.get("shape") != "circle":
            target = (box["w"] * iw) / (box["h"] * ih)
            ratios = [o[0] for o in self.spec.item("aspect")["opts"] if o[0] not in ("full", "custom")]
            best = min(ratios, key=lambda r: abs(math.log(float(r) / target)))
            self.state["aspect"] = best
            self.form.set_value("aspect", best)
        a = frame_model.aspect(self.state, iw, ih)
        bw, bh = box["w"] * iw * 1.08, box["h"] * ih * 1.08
        width = max(bw, bh * a) / iw
        self.source_view.set_frame({"cx": box["x"] + box["w"] / 2, "cy": box["y"] + box["h"] / 2, "w": width})
        self._sync_zoom()
        self._refresh_form()

    def _hints_painted(self, png):
        """Repères peints : envoyés au calcul (dans le fil de calcul, sous son verrou, comme /api/hints)."""
        def send():
            with self.service.lock:
                self.service.set_hints(png)
            return {}
        self._run(send, lambda _out: self._results.preview.emit({"hints": True}))

    def _frame_moved(self, moving):
        self._moving = moving
        self._sync_zoom()
        self.schedule()

    def apply_preset(self, name):
        """Style prédéfini (applyPreset de la page) : ses réglages remplacent les actuels."""
        preset = self.spec.presets.get(name)
        if not preset:
            return
        for key, value in preset.items():
            self.state[key] = value
            self.form.set_value(key, value)
        self.state["preset"] = ""
        self._set_mode(self.state.get("output") or "stencil")
        self.source_view.refresh_frame()
        if self.state.get("output") == "qr" and not self.service.session.has_image():
            self._blank_image()
            return
        self.schedule()

    def set_view(self, view):
        """Vue de l'aperçu ; recalculée tout de suite, comme dans la page (setView)."""
        self.view = view
        self._timer.stop()
        self._send_preview()

    def request(self, work, view=None):
        """Demande au calcul, comme la page (payload) : réglages, cadre, sujet, vue, résolution."""
        s = self.state
        self._seq += 1
        frame = frame_model.request_frame(s, self.source_view.iw, self.source_view.ih, self.source_view.frame())
        return {"seq": self._seq, "params": self.spec.request_params(s), "frame": frame,
                "isolate": bool(s.get("isolate")), "margin": s.get("margin"), "mbr": [], "lpg": {"pts": [], "edges": []},
                "view": view or self.view, "work": work, "moving": self._moving, "box": self.source_view.subject_box,
                "style": {"material": s.get("material"), "backlight": bool(s.get("backlight")),
                          "light": s.get("lightcolor"), "lang": self.language}}

    # -- aperçu et export (fil de calcul)

    def schedule(self):
        self._timer.start()
        self._history_timer.start()           # une étape d'annulation par série de changements (histNote)

    def _send_preview(self):
        if not self.service.session.has_image():
            return
        req = self.request(int(self.state.get("previewRes") or 1200))
        self.status.setText(self.tr_("Computing..."))
        self._run(lambda: self.service.preview_result(req), lambda out: self._results.preview.emit(out))

    def _run(self, job, done):
        def target():
            try:
                done(job())
            except Exception as error:      # calcul en échec : message dans la fenêtre, pas de plantage
                self._results.failed.emit(str(error))
        threading.Thread(target=target, name="qstencil-calcul", daemon=True).start()

    def _show_preview(self, out):
        if out.get("hints"):                # repères reçus par le calcul : aperçu relancé en isolant le sujet
            if self.state.get("isolate"):
                self.schedule()
            return
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
        self.export("svg")

    def export(self, fmt):
        """Export au format `fmt` (voir EXPORTS), calculé à la résolution d'export."""
        if not self.service.session.has_image():
            self.status.setText(self.tr_("Open an image first."))
            return
        what = next(e[2] for e in EXPORTS if e[0] == fmt)
        req = self.request(int(self.state.get("exportRes") or 1200))
        if what:
            req["what"] = what
            req["lang"] = self.language
        self.status.setText(self.tr_("Exporting..."))
        self._run(lambda: self.service.export_result(req), lambda out: self._results.export.emit(fmt, out))

    def confirm_export(self, name, picture, out):
        """Aperçu avant export (« Aperçu avant l'export », showExportPreview de la page) : `picture` est le SVG
        (texte) ou le PNG (octets) à montrer. True pour exporter."""
        dialog = QDialog(self)
        dialog.setWindowTitle(name)
        layout = QVBoxLayout(dialog)
        preview = ImageView()
        preview.setMinimumSize(520, 420)
        image = QImage()
        if isinstance(picture, bytes):
            image.loadFromData(picture)                    # gravure PNG
        elif picture:
            renderer = QSvgRenderer(QByteArray(picture.encode("utf-8")))
            size = renderer.defaultSize().scaled(1000, 1000, Qt.AspectRatioMode.KeepAspectRatio)
            image = QImage(size, QImage.Format.Format_RGB32)
            image.fill(Qt.GlobalColor.white)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
        if not image.isNull():
            preview.set_image(image)
        layout.addWidget(preview, 1)
        layout.addWidget(QLabel(self.stats_text(out.get("stats") or {})))
        buttons = QDialogButtonBox()
        buttons.addButton(self.tr_("Download"), QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self.tr_("Back to editing"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _deliver_export(self, fmt, out):
        _fmt, _label, _what, key, suffix, file_filter = next(e for e in EXPORTS if e[0] == fmt)
        content = out.get(key)
        if content is None:                 # ex. pas de diffuseur dans ce caisson
            self.status.setText(self.tr_("No diffuser in this box (enable the diffuser sheet).") if fmt == "boxpdf"
                                else self.tr_("Error: {msg}", msg=key))
            return
        name = (out.get("name") or "stencil") + suffix
        if self.state.get("exp_preview") and not self.confirm_export(name, out.get(PREVIEW_KEY.get(fmt, key)), out):
            return
        if fmt in TO_LASER_STUDIO:          # vers l'éditeur vectoriel, comme la version web dans Laser Studio
            path = os.path.join(tempfile.mkdtemp(prefix="qstencil-"), name)
        else:
            path, _f = QFileDialog.getSaveFileName(self, self.tr_(_label), name, file_filter)
            if not path:
                return
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
            f.write(content)
        self.status.setText(self.stats_text(out.get("stats") or {}) + " · "
                            + self.tr_("Saved: {name}", name=os.path.basename(path)))
        if fmt in TO_LASER_STUDIO:
            self.export_ready.emit(path)
