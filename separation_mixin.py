# -*- coding: utf-8 -*-
"""Onglet « Séparation Couleur / Verre » (PyQt6), calqué sur l'onglet PNG -> SVG.

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
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from image import separation as engine
from workers import AdvancedGCodeWorker, build_gain_test_array
from i18n import tr

class SeparationMixin:
    # Mettre à False une fois le diagnostic de lenteur terminé.
    SEP_DEBUG = True

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _init_separation_state(self):
        """État et minuteurs de l'onglet Séparation (la vue, SeparationTab,
        est construite et branchée par main_window._build_separation_tab)."""
        self.sep_src = None          # image couleur complète (RGB)
        self.sep_src_small = None    # miniature pour les aperçus
        self.sep_path = ""
        self.sep_dirty = False
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


    def _sep_original_with_crop(self):
        """Image source entière ; hors de la zone gravée, elle est assombrie et
        la zone est cernée d'un cadre rouge."""
        prev = self.sep_src_small.copy()
        prev.thumbnail((self.PREVIEW_MAX, self.PREVIEW_MAX))
        fr, z, ox, oy = self.tab_separation.frame_args()
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
        self.tab_separation.set_engrave_dpi(round(self.spin_lmm.value() * 25.4))

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
        self.tab_separation.set_image_ratio(self.sep_src.width / self.sep_src.height)
        self.tab_separation.fit_plate_to_image()
        self.separation_push_tone()
        self.update_image_actions_state()

    def separation_rotate_image(self, angle):
        """Pivote l'image source de `angle` degrés (positif = sens antihoraire, comme PIL)
        et échange la largeur et la hauteur de la plaque."""
        if self.sep_src is None:
            return
        self.sep_src = self.sep_src.rotate(angle, expand=True)
        small = self.sep_src.copy()
        small.thumbnail((2500, 2500))
        self.sep_src_small = small
        self.sep_version += 1
        self.tab_separation.set_image_ratio(self.sep_src.width / self.sep_src.height)
        self.tab_separation.swap_plate_size()
        self.separation_push_tone()

    def separation_clear_image(self):
        """Retire l'image source et vide les aperçus. L'image déjà envoyée à
        Image & Filtres y reste (elle se supprime depuis cet onglet)."""
        self.sep_push_timer.stop()
        self.sep_preview_timer.stop()
        self.sep_src = None
        self.sep_src_small = None
        self.sep_path = ""
        self.sep_version += 1
        self._sep_cache = None
        self._sep_stale = set()
        self.sep_lbl_file.setText(tr("sep.no_image_loaded"))
        for view in self.sep_views:
            view.clear_image()
        self._sep_view_sizes = {}
        self.tab_separation.set_image_ratio(None)
        self.update_image_actions_state()

    def _sep_apply_glass_settings(self):
        """Applique matière « fond noir » + négatif + miroir horizontal.
        Ces cases sont partagées avec l'onglet Images Tramage : on mémorise
        l'état d'avant (une seule fois) pour le rendre quand une image est
        chargée côté Images Tramage (voir separation_release_image_settings)."""
        if not getattr(self, "_sep_glass_settings_active", False):
            self._sep_prev_image_settings = {
                "material": self.get_material_bg() if hasattr(self, "get_material_bg") else None,
                "invert": self.chk_invert.isChecked(),
                "mirror_h": self.app_actions.mirror_h.isChecked(),
            }
            self._sep_glass_settings_active = True
        if hasattr(self, "set_material_bg"):
            self.set_material_bg("dark")  # ne touche pas à la case, réglée juste après
        self.chk_invert.setChecked(True)
        self.app_actions.mirror_h.setChecked(True)

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
        self.app_actions.mirror_h.setChecked(prev["mirror_h"])

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
                               *self.tab_separation.frame_args())
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
        key = (self.sep_version, pw, ph, self.tab_separation.frame_args(),
               self.sep_sat.value(), self.sep_cla.value())
        c = self._sep_cache
        if c is None or c["key"] != key:
            img = engine.cadrer(self.sep_src_small, pw, ph, *self.tab_separation.frame_args())
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
            if self.app_actions.mirror_h.isChecked():
                lum = lum[:, ::-1]
            if self.app_actions.mirror_v.isChecked():
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
    # --- Assistant de calibrage du gain de point ---
    def separation_gain_test(self):
        """Génère la grille de test du gain de point : une ligne par valeur du
        curseur « Gain de point » (0 à 20), une colonne par ton (0 à 100 %), avec
        la résolution, la vitesse, la puissance et la machine actuelles. Une fois
        gravée, on repère la ligne dont les cases passent régulièrement du noir
        au clair, et on règle le curseur sur la valeur écrite à gauche."""
        mirror = self.app_actions.mirror_h.isChecked()
        arr, w_mm, h_mm = build_gain_test_array(self.spin_lmm.value(), mirror=mirror)
        bed_w, bed_h = self.spin_machine_w.value(), self.spin_machine_h.value()
        if w_mm > bed_w or h_mm > bed_h:
            QMessageBox.warning(
                self, tr("sep.gain_test_title"),
                tr("sep.gain_test_too_big").format(w=w_mm, h=h_mm, bed_w=bed_w, bed_h=bed_h),
            )
            return
        params = self._build_gcode_params()
        params.update(width_mm=w_mm, height_mm=h_mm, algo="Floyd-Steinberg", enable_cut=False)
        self._gain_test_worker = AdvancedGCodeWorker(arr, None, params, None)
        self._gain_test_worker.finished.connect(self._on_gain_test_ready)
        self._gain_test_worker.error.connect(self.on_gcode_generation_error)
        self._gain_test_worker.start()

    def _on_gain_test_ready(self, gcode, n_lines, avg_power, time_str):
        header = (
            "; --- TEST DU GAIN DE POINT ---\n"
            "; Lignes de haut en bas : gain 0, 5, 10, 15, 20. Colonnes : 0 % (peinture intacte) a 100 % (verre degage).\n"
            "; Repere la ligne dont les cases passent regulierement du noir au clair,\n"
            "; puis regle le curseur Gain de point sur la valeur ecrite a gauche de cette ligne.\n"
        )
        self.on_gcode_generated(header + gcode, n_lines + header.count("\n"), avg_power, time_str)
        QMessageBox.information(self, tr("sep.gain_test_title"), tr("sep.gain_test_done"))

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
                                  *self.tab_separation.frame_args())
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
