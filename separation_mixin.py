# -*- coding: utf-8 -*-
"""Onglet « Séparation Couleur / Verre » (PyQt6), calqué sur png2svg_mixin.py.

Principe : l'image couleur est chargée ici ; sa tonalité (canal V) est envoyée à
l'onglet « Image & Filtres » (raw_image), qui applique luminosité / contraste /
gamma / tramage / résolution (spot laser) et produit self.processed_array =
calque noir (0 = gravé). Le calque couleur est calculé ici à la MÊME taille
physique. Le DPI de gravure est celui d'Image & Filtres (spin_lmm * 25.4).
"""
import os
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

import separation_engine as engine
from graphics_view import ZoomableGraphicsView
from i18n import tr

_IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")


class _SeparationRoot(QWidget):
    """Conteneur de l'onglet, qui accepte le glisser-déposer d'une image."""

    def __init__(self, on_drop):
        super().__init__()
        self._on_drop = on_drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(_IMG_EXT):
                e.acceptProposedAction()
                self._on_drop(p)
                return


class SeparationMixin:
    # Mettre à False une fois le diagnostic de lenteur terminé.
    SEP_DEBUG = True

    # (saturation %, clarté %, diffusion en 1/100 mm) - à calibrer à l'œil
    SEP_SUPPORTS = {0: (140, 100, 15), 1: (170, 90, 60)}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _init_separation_tab(self):
        self.sep_src = None          # image couleur complète (RGB)
        self.sep_src_small = None    # miniature pour les aperçus
        self.sep_path = ""
        self.sep_dirty = False
        self._sep_block = False      # évite les boucles entre largeur et hauteur
        self.sep_version = 0         # incrémenté à chaque nouvelle image (invalide le cache)
        self._sep_cache = None       # calque couleur mis en cache (voir _sep_color_data)
        self._sep_stale = set()      # aperçus à recalculer (seul l'onglet affiché l'est vraiment)
        self._sep_view_sizes = {}
        self._sep_t0 = None          # diagnostic : instant du dernier changement de tramage
        self._sep_timing = {}
        self.combo_algo.currentIndexChanged.connect(self._sep_mark_t0)

        self.sep_push_timer = QTimer()
        self.sep_push_timer.setSingleShot(True)
        self.sep_push_timer.setInterval(300)
        self.sep_push_timer.timeout.connect(self.separation_push_tone)

        self.sep_preview_timer = QTimer()
        self.sep_preview_timer.setSingleShot(True)
        self.sep_preview_timer.setInterval(250)
        self.sep_preview_timer.timeout.connect(self.separation_refresh_preview)

        root = _SeparationRoot(self.separation_load_path)
        self.tab_separation = root
        outer = QVBoxLayout(root)
        outer.setContentsMargins(4, 4, 4, 4)

        bar = QHBoxLayout()
        bar.addStretch()
        btn_fs = QPushButton(tr("ui.vector_fullscreen"))
        btn_fs.clicked.connect(lambda: self._toggle_fullscreen_tab("tab_separation", "sep.tab_title"))
        bar.addWidget(btn_fs)
        outer.addLayout(bar)

        body = QHBoxLayout()
        outer.addLayout(body, 1)

        panel = QWidget()
        pl = QVBoxLayout(panel)

        btn_load = QPushButton(tr("sep.load_image_btn"))
        btn_load.clicked.connect(self.separation_load_image)
        pl.addWidget(btn_load)
        hint = QLabel(tr("sep.drag_drop_hint"))
        hint.setStyleSheet("color: #888888;")
        pl.addWidget(hint)
        self.sep_lbl_file = QLabel(tr("sep.no_image_loaded"))
        self.sep_lbl_file.setWordWrap(True)
        pl.addWidget(self.sep_lbl_file)

        # --- Plaque de verre ---
        gb = QGroupBox(tr("sep.plate_title"))
        f = QFormLayout(gb)
        self.sep_w = QDoubleSpinBox(); self.sep_w.setRange(5, 2000); self.sep_w.setValue(150)
        self.sep_h = QDoubleSpinBox(); self.sep_h.setRange(5, 2000); self.sep_h.setValue(100)
        self.sep_dp = QSpinBox(); self.sep_dp.setRange(72, 1200); self.sep_dp.setValue(300)
        self.sep_framing = QComboBox()
        self.sep_framing.addItems([tr("sep.crop_fit"), tr("sep.stretch")])
        self.sep_keep_ratio = QCheckBox(tr("sep.keep_ratio"))
        self.sep_keep_ratio.setChecked(True)
        self.sep_w.valueChanged.connect(lambda _v: self._sep_on_plate_changed("w"))
        self.sep_h.valueChanged.connect(lambda _v: self._sep_on_plate_changed("h"))
        self.sep_keep_ratio.toggled.connect(self._sep_on_keep_ratio)
        self.sep_framing.currentIndexChanged.connect(self._sep_on_framing_changed)
        f.addRow(self.sep_keep_ratio)
        f.addRow(tr("sep.width"), self.sep_w)
        f.addRow(tr("sep.height"), self.sep_h)
        f.addRow(tr("sep.print_dpi"), self.sep_dp)
        f.addRow(tr("sep.framing"), self.sep_framing)
        self.sep_lbl_dpi = QLabel()
        self.sep_lbl_dpi.setWordWrap(True)
        f.addRow(self.sep_lbl_dpi)
        note = QLabel(tr("sep.sync_note"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #888888;")
        f.addRow(note)
        pl.addWidget(gb)

        # --- Recadrage (plaque aux proportions libres) ---
        gb = QGroupBox(tr("sep.crop_title"))
        self.sep_crop_box = gb
        f = QFormLayout(gb)
        crop_hint = QLabel(tr("sep.crop_hint"))
        crop_hint.setWordWrap(True)
        crop_hint.setStyleSheet("color: #888888;")
        f.addRow(crop_hint)
        self.sep_crop_zoom = self._sep_slider(f, "sep.crop_zoom", 100, 400, 100,
                                              lambda v: f"{v} %", self._sep_on_crop_changed)
        self.sep_crop_x = self._sep_slider(f, "sep.crop_x", 0, 100, 50,
                                           lambda v: f"{v} %", self._sep_on_crop_changed)
        self.sep_crop_y = self._sep_slider(f, "sep.crop_y", 0, 100, 50,
                                           lambda v: f"{v} %", self._sep_on_crop_changed)
        btn_reset = QPushButton(tr("sep.crop_reset"))
        btn_reset.clicked.connect(self._sep_reset_crop)
        f.addRow(btn_reset)
        pl.addWidget(gb)
        self._sep_update_crop_enabled()

        # --- Calque noir ---
        gb = QGroupBox(tr("sep.black_layer_title"))
        f = QFormLayout(gb)
        info = QLabel(tr("sep.black_info"))
        info.setWordWrap(True)
        info.setStyleSheet("color: #888888;")
        f.addRow(info)
        self.sep_gain = self._sep_slider(f, "sep.gain", 0, 20, 0, lambda v: f"{v}",
                                         self._sep_schedule_push, "sep.gain_tip")
        pl.addWidget(gb)

        # --- Calque couleur ---
        gb = QGroupBox(tr("sep.color_layer_title"))
        f = QFormLayout(gb)
        self.sep_support = QComboBox()
        self.sep_support.addItems([tr("sep.transparent_film"), tr("sep.tracing_paper"), tr("sep.custom")])
        self.sep_support.activated.connect(self._sep_apply_support)
        f.addRow(tr("sep.support_medium"), self.sep_support)
        self.sep_sat = self._sep_slider(f, "sep.saturation", 50, 300, 140,
                                        lambda v: f"{v / 100:.2f}", self._sep_schedule_preview)
        self.sep_cla = self._sep_slider(f, "sep.lightness", 40, 100, 100,
                                        lambda v: f"{v / 100:.2f}", self._sep_schedule_preview)
        self.sep_mir_print = QCheckBox(tr("sep.mirror_print"))
        self.sep_mir_print.setToolTip(tr("sep.mirror_print_tip"))
        self.sep_mir_print.toggled.connect(self._sep_schedule_preview)
        f.addRow(self.sep_mir_print)
        pl.addWidget(gb)

        # --- Simulation ---
        gb = QGroupBox(tr("sep.backlight_title"))
        f = QFormLayout(gb)
        self.sep_dif = self._sep_slider(f, "sep.light_diffusion", 0, 100, 15,
                                        lambda v: f"{v / 100:.2f}", self._sep_schedule_preview)
        self.sep_int = self._sep_slider(f, "sep.backlight_intensity", 50, 300, 100,
                                        lambda v: f"{v / 100:.2f}", self._sep_schedule_preview)
        pl.addWidget(gb)

        btn_export = QPushButton(tr("sep.export_btn"))
        btn_export.clicked.connect(self.separation_export)
        pl.addWidget(btn_export)
        tip = QLabel(tr("sep.tip"))
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #888888;")
        pl.addWidget(tip)
        pl.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(360)
        body.addWidget(scroll)

        # --- Aperçus ---
        self.sep_tabs = QTabWidget()
        self.sep_views = []
        for key in ("sep.tab_original", "sep.tab_engraving", "sep.tab_print", "sep.tab_simulation"):
            v = ZoomableGraphicsView()
            self.sep_views.append(v)
            self.sep_tabs.addTab(v, tr(key))
        self.sep_tabs.setCurrentIndex(3)
        self.sep_tabs.currentChanged.connect(lambda _i: self._sep_render_current())
        body.addWidget(self.sep_tabs, 1)

        self._sep_update_dpi_label()
        return root

    def _sep_slider(self, form, label_key, lo, hi, val, fmt, on_change, tip_key=None):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        lab = QLabel(fmt(val))
        lab.setMinimumWidth(42)
        s.valueChanged.connect(lambda v: (lab.setText(fmt(v)), on_change()))
        row = QHBoxLayout()
        row.addWidget(s, 1)
        row.addWidget(lab)
        form.addRow(tr(label_key), row)
        if tip_key:
            s.setToolTip(tr(tip_key))
        return s

    def _sep_apply_support(self, i):
        if i in self.SEP_SUPPORTS:
            sat, cla, dif = self.SEP_SUPPORTS[i]
            self.sep_sat.setValue(sat)
            self.sep_cla.setValue(cla)
            self.sep_dif.setValue(dif)

    # --- Proportions et recadrage ---
    def _sep_frame_args(self):
        """(cadrage, zoom, ox, oy) réellement appliqués. Avec les proportions de
        l'image conservées, ou en mode « étirer », zoom et décalage sont ignorés."""
        fr = self.sep_framing.currentIndex()
        if self.sep_keep_ratio.isChecked() or fr != 0:
            return (fr if not self.sep_keep_ratio.isChecked() else 0, 1.0, 0.5, 0.5)
        return (0, self.sep_crop_zoom.value() / 100.0,
                self.sep_crop_x.value() / 100.0, self.sep_crop_y.value() / 100.0)

    def _sep_apply_ratio(self, driver="w"):
        """Recalcule la hauteur (driver='w') ou la largeur (driver='h') pour
        respecter les proportions de l'image chargée."""
        if self.sep_src is None:
            return
        ratio = self.sep_src.width / self.sep_src.height
        self._sep_block = True
        try:
            if driver == "w":
                self.sep_h.setValue(self.sep_w.value() / ratio)
            else:
                self.sep_w.setValue(self.sep_h.value() * ratio)
        finally:
            self._sep_block = False

    def _sep_on_plate_changed(self, which):
        if self._sep_block:
            return
        if self.sep_keep_ratio.isChecked():
            self._sep_apply_ratio(which)
        self._sep_schedule_push()
        self._sep_schedule_preview()

    def _sep_on_keep_ratio(self, checked):
        if checked:
            self._sep_apply_ratio("w")
        self._sep_update_crop_enabled()
        self._sep_schedule_push()
        self._sep_schedule_preview()

    def _sep_on_framing_changed(self, *_a):
        self._sep_update_crop_enabled()
        self._sep_schedule_push()
        self._sep_schedule_preview()

    def _sep_update_crop_enabled(self):
        libre = not self.sep_keep_ratio.isChecked()
        self.sep_framing.setEnabled(libre)
        self.sep_crop_box.setEnabled(libre and self.sep_framing.currentIndex() == 0)

    def _sep_on_crop_changed(self):
        self._sep_schedule_push()
        self._sep_schedule_preview()

    def _sep_reset_crop(self):
        for sl, v in ((self.sep_crop_zoom, 100), (self.sep_crop_x, 50), (self.sep_crop_y, 50)):
            sl.setValue(v)

    def _sep_original_with_crop(self):
        """Image source entière ; hors de la zone gravée, elle est assombrie et
        la zone est cernée d'un cadre rouge."""
        prev = self.sep_src_small.copy()
        prev.thumbnail((self.PREVIEW_MAX, self.PREVIEW_MAX))
        fr, z, ox, oy = self._sep_frame_args()
        if fr != 0:
            return prev
        box = engine.boite_recadrage(prev.width, prev.height,
                                     self.sep_w.value() / self.sep_h.value(), z, ox, oy)
        b = tuple(int(round(v)) for v in box)
        if b[2] - b[0] >= prev.width - 1 and b[3] - b[1] >= prev.height - 1:
            return prev  # toute l'image est utilisée
        sombre = Image.blend(prev, Image.new("RGB", prev.size, (0, 0, 0)), 0.6)
        sombre.paste(prev.crop(b), b[:2])
        ImageDraw.Draw(sombre).rectangle([b[0], b[1], b[2] - 1, b[3] - 1], outline=(255, 60, 60), width=2)
        return sombre

    def _sep_schedule_push(self, *_a):
        self.sep_push_timer.start()

    def _sep_schedule_preview(self, *_a):
        self.sep_preview_timer.start()

    def _sep_update_dpi_label(self):
        dpi = round(self.spin_lmm.value() * 25.4)
        self.sep_lbl_dpi.setText(tr("sep.engrave_dpi").format(dpi=dpi))

    # ------------------------------------------------------------------
    # Chargement de l'image et envoi de la tonalité à Image & Filtres
    # ------------------------------------------------------------------
    def separation_load_image(self):
        path, _f = QFileDialog.getOpenFileName(self, tr("image.open_title"), "", tr("image.file_filter"))
        if path:
            self.separation_load_path(path)

    def separation_load_path(self, path):
        try:
            im = ImageOps.exif_transpose(Image.open(path))
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                im = im.convert("RGBA")
                fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
                im = Image.alpha_composite(fond, im)
            self.sep_src = im.convert("RGB")
        except Exception as e:
            QMessageBox.critical(self, tr("image.error_title"), tr("image.load_error").format(error=e))
            return
        small = self.sep_src.copy()
        small.thumbnail((2500, 2500))
        self.sep_src_small = small
        self.sep_path = path
        self.sep_version += 1
        self.sep_lbl_file.setText(os.path.basename(path))
        # Réglage habituel pour le verre peint (gravure côté peinture, vue à
        # travers le verre) : on retire la peinture sur les zones claires
        # (matière « fond noir » => négatif) et on grave en miroir. Modifiable
        # ensuite dans Image & Filtres.
        self._sep_apply_glass_settings()
        if self.sep_keep_ratio.isChecked():
            self._sep_apply_ratio("w")
        self.separation_push_tone()

    def _sep_apply_glass_settings(self):
        """Applique matière « fond noir » + négatif + miroir horizontal.
        Ces cases sont partagées avec l'onglet Images Tramage : on mémorise
        l'état d'avant (une seule fois) pour le rendre quand une image est
        chargée côté Images Tramage (voir separation_release_image_settings)."""
        if not getattr(self, "_sep_glass_settings_active", False):
            self._sep_prev_image_settings = {
                "material": self.get_material_bg() if hasattr(self, "get_material_bg") else None,
                "invert": self.chk_invert.isChecked(),
                "mirror_h": self.chk_mirror_h.isChecked(),
            }
            self._sep_glass_settings_active = True
        if hasattr(self, "set_material_bg"):
            self.set_material_bg("dark")  # ne touche pas à la case, réglée juste après
        self.chk_invert.setChecked(True)
        self.chk_mirror_h.setChecked(True)

    def separation_release_image_settings(self):
        """Appelé quand une image est chargée côté Images Tramage : rend les
        réglages (matière, négatif, miroir) tels qu'ils étaient avant le
        passage par l'onglet Séparation, pour ne pas les y laisser coincés."""
        if not getattr(self, "_sep_glass_settings_active", False):
            return
        self._sep_glass_settings_active = False
        prev = getattr(self, "_sep_prev_image_settings", None)
        if not prev:
            return
        if prev.get("material") and hasattr(self, "set_material_bg"):
            self.set_material_bg(prev["material"])
        self.chk_invert.setChecked(prev["invert"])
        self.chk_mirror_h.setChecked(prev["mirror_h"])

    def separation_push_tone(self):
        """Envoie la tonalité (canal V, cadrée sur la plaque) à Image & Filtres
        et reporte les dimensions de la plaque dans l'onglet Dimensions."""
        if self.sep_src is None:
            return
        w_mm, h_mm = self.sep_w.value(), self.sep_h.value()
        longest = max(w_mm, h_mm)
        # px/mm : au moins la résolution de gravure, ~2000 px minimum, 6000 px maximum
        scale = min(max(self.spin_lmm.value(), 2000.0 / longest), 6000.0 / longest)
        framed = engine.cadrer(self.sep_src, round(w_mm * scale), round(h_mm * scale),
                               *self._sep_frame_args())
        tone = engine.tonalite_v(np.asarray(framed))
        tone = engine.compenser_gain_point(tone, self.sep_gain.value() / 100.0)
        self.raw_image = Image.fromarray((tone * 255 + 0.5).astype(np.uint8))
        self.block_aspect_signal = True
        self.spin_w.setValue(w_mm)
        self.spin_h.setValue(h_mm)
        self.block_aspect_signal = False
        self.display_source_image()
        self.update_image_processing()
        self._sep_update_dpi_label()

    def _sep_mark_t0(self, *_a):
        self._sep_t0 = time.perf_counter()

    def separation_on_processed(self):
        """Appelé par on_image_processed : le calque noir vient d'être recalculé."""
        t_hook = time.perf_counter()
        self._sep_update_dpi_label()
        self._sep_timing = {}
        if self.sep_src is not None:
            self.separation_refresh_preview()
        if self.SEP_DEBUG and self.sep_src is not None and self.processed_array is not None:
            t_end = time.perf_counter()
            H, W = self.processed_array.shape
            tm = self._sep_timing
            avant = f"{(t_hook - self._sep_t0) * 1000:.0f} ms" if self._sep_t0 else "?"
            try:
                from workers import _HAS_NUMBA
            except Exception:
                _HAS_NUMBA = "?"
            msg = (f"[Séparation] {self.combo_algo.currentText()} | numba actif : {_HAS_NUMBA} | "
                   f"tableau {W}x{H} px ({W * H / 1e6:.1f} Mpx) | "
                   f"attente+traitement Image&Filtres : {avant} | "
                   f"aperçu : {(t_end - t_hook) * 1000:.0f} ms "
                   f"(couleur {tm.get('couleur', 0):.0f}, simulation {tm.get('simulation', 0):.0f}, "
                   f"affichage {tm.get('affichage', 0):.0f})")
            print(msg)
            if hasattr(self, "txt_console"):
                self.txt_console.append(msg)
            self._sep_t0 = None

    def separation_refresh_if_dirty(self):
        if self.sep_dirty:
            self._sep_render_current()

    PREVIEW_MAX = 1200  # taille maxi (px) des aperçus : au-delà, inutile et lent

    def separation_refresh_preview(self):
        """Invalide les aperçus ; seul l'onglet d'aperçu affiché est recalculé
        tout de suite, les autres le seront quand on les ouvrira."""
        if self.sep_src_small is None or self.processed_array is None:
            return
        self._sep_stale = {0, 1, 2, 3}
        self._sep_render_current()

    def _sep_color_data(self, pw, ph):
        """Calque couleur de l'aperçu, mis en cache : il ne dépend ni du tramage
        ni des réglages d'Image & Filtres, seulement de l'image, du cadrage, de
        la saturation et de la clarté."""
        key = (self.sep_version, pw, ph, self._sep_frame_args(),
               self.sep_sat.value(), self.sep_cla.value())
        c = self._sep_cache
        if c is None or c["key"] != key:
            img = engine.cadrer(self.sep_src_small, pw, ph, *self._sep_frame_args())
            couleur = engine.calculer_calque_couleur(
                np.asarray(img), self.sep_sat.value() / 100.0, self.sep_cla.value() / 100.0)
            c = {"key": key, "img": img, "couleur": couleur,
                 "lin": engine.vers_lineaire(couleur)}
            self._sep_cache = c
        return c

    def _sep_render_current(self):
        arr = self.processed_array
        if self.sep_src_small is None or arr is None:
            return
        if not self.tab_separation.isVisible():
            self.sep_dirty = True
            return
        self.sep_dirty = False
        idx = self.sep_tabs.currentIndex()
        if idx not in self._sep_stale:
            return
        self._sep_stale.discard(idx)

        H, W = arr.shape
        f = min(1.0, self.PREVIEW_MAX / max(W, H))
        pw, ph = max(1, round(W * f)), max(1, round(H * f))

        if idx == 1:  # fichier gravure : tel que reçu par le laser (0 = gravé)
            grav = Image.fromarray(arr)
            self._sep_show(1, grav if f == 1.0 else grav.resize((pw, ph), Image.NEAREST))
            return

        if idx == 0:
            self._sep_show(0, self._sep_original_with_crop())
            return

        t_a = time.perf_counter()
        cd = self._sep_color_data(pw, ph)
        self._sep_timing["couleur"] = (time.perf_counter() - t_a) * 1000
        if idx == 2:
            im = engine.array_vers_image(cd["couleur"])
            if self.sep_mir_print.isChecked():
                im = ImageOps.mirror(im)
            self._sep_show(2, im)
        else:
            # Fraction de verre dégagé (0 = gravé = la lumière passe), orientation de lecture
            t_b = time.perf_counter()
            grav = Image.fromarray(arr).resize((pw, ph), Image.BOX)
            lum = (255.0 - np.asarray(grav, dtype=np.float32)) / 255.0
            if self.chk_mirror_h.isChecked():
                lum = lum[:, ::-1]
            if self.chk_mirror_v.isChecked():
                lum = lum[::-1, :]
            lum = np.ascontiguousarray(lum)
            dpi_prev = pw / (self.sep_w.value() / 25.4)
            rayon = self.sep_dif.value() / 100.0 / 25.4 * dpi_prev
            if rayon > 0.3:
                m = Image.fromarray((lum * 255 + 0.5).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rayon))
                lum = np.asarray(m, dtype=np.float32) / 255.0
            sim = engine.simuler_vers_image(lum[..., None], cd["lin"], self.sep_int.value() / 100.0)
            self._sep_timing["simulation"] = (time.perf_counter() - t_b) * 1000
            self._sep_show(3, sim)

    def _sep_show(self, idx, im):
        t_c = time.perf_counter()
        self._sep_show_impl(idx, im)
        self._sep_timing["affichage"] = (time.perf_counter() - t_c) * 1000

    def _sep_show_impl(self, idx, im):
        view = self.sep_views[idx]
        if self._sep_view_sizes.get(idx) != im.size:
            view.clear_image()
            self._sep_view_sizes[idx] = im.size
        w, h = im.size
        if im.mode == "L":
            data = im.tobytes()
            qimg = QImage(data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            data = im.convert("RGB").tobytes()
            qimg = QImage(data, w, h, 3 * w, QImage.Format.Format_RGB888)
        view.set_image(qimg.copy())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def separation_export(self):
        if self.sep_src is None or self.processed_array is None:
            QMessageBox.information(self, tr("sep.tab_title"), tr("sep.no_image_loaded"))
            return
        if self.process_timer.isActive() or (self.img_worker and self.img_worker.isRunning()):
            QMessageBox.information(self, tr("sep.tab_title"), tr("sep.not_ready"))
            return
        dossier = QFileDialog.getExistingDirectory(self, tr("sep.export_folder"))
        if not dossier:
            return
        base = os.path.join(dossier, os.path.splitext(os.path.basename(self.sep_path))[0])
        w_mm, h_mm = self.sep_w.value(), self.sep_h.value()
        dpi_g = round(self.spin_lmm.value() * 25.4)
        dpi_p = self.sep_dp.value()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # Calque noir : exactement ce que reçoit le laser (miroir/négatif d'Image & Filtres inclus)
            f_grav = f"{base}_gravure.png"
            grav = Image.fromarray(self.processed_array)
            if self.combo_algo.currentText() != "Niveaux de Gris":
                grav = grav.point(lambda x: 255 if x > 127 else 0, mode="1")
            grav.save(f_grav, dpi=(dpi_g, dpi_g))

            # Calque couleur : même taille physique, à la résolution d'impression
            img_p = engine.cadrer(self.sep_src, round(w_mm / 25.4 * dpi_p), round(h_mm / 25.4 * dpi_p),
                                  *self._sep_frame_args())
            couleur = engine.array_vers_image(engine.calculer_calque_couleur(
                np.asarray(img_p), self.sep_sat.value() / 100.0, self.sep_cla.value() / 100.0))
            if self.sep_mir_print.isChecked():
                couleur = ImageOps.mirror(couleur)
            f_coul = f"{base}_couleur.png"
            couleur.save(f_coul, dpi=(dpi_p, dpi_p))
            f_pdf = f"{base}_couleur.pdf"
            pdf_ok = engine.generer_pdf_impression(couleur, dpi_p, f_pdf, w_mm, h_mm)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("laser.error"), str(e))
            return
        QApplication.restoreOverrideCursor()

        fichiers = [f_grav, f_coul] + ([f_pdf] if pdf_ok else [])
        msg = tr("sep.files_created") + "\n" + "\n".join(os.path.basename(p) for p in fichiers)
        if not pdf_ok:
            msg += "\n\n" + tr("sep.pdf_too_large")
        QMessageBox.information(self, tr("sep.export_complete"), msg)
