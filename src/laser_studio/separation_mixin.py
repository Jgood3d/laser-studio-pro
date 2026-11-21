# -*- coding: utf-8 -*-
"""Onglet « Séparation Couleur / Verre », côté interface : boîtes de
dialogue, aperçus, liens avec « Graver une image ». L'état et la logique
(image source, tonalité, aperçus, export, réglages du verre) sont dans
controllers.separation.SeparationController (self.separation), les réglages
de l'onglet dans models.separation.SeparationSettings."""
import os
import time

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from laser_studio.controllers.separation import SeparationController
from laser_studio.i18n import tr
from laser_studio.models.separation import SeparationSettings
from laser_studio.ui.binding import bind
from laser_studio.workers import AdvancedGCodeWorker, build_gain_test_array


class SeparationMixin:
    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _init_separation(self, tab):
        """Réglages et contrôleur de la Séparation, liés à l'onglet `tab`
        (SeparationTab), et abonnement à leurs signaux."""
        self.separation_settings = SeparationSettings(self)
        for widget, field in (
            (tab.plate_width_spin, "plate_w"),
            (tab.plate_height_spin, "plate_h"),
            (tab.print_dpi_spin, "print_dpi"),
            (tab.gain_slider, "gain"),
            (tab.saturation_slider, "saturation"),
            (tab.lightness_slider, "lightness"),
            (tab.mirror_print_check, "mirror_print"),
            (tab.diffusion_slider, "diffusion"),
            (tab.intensity_slider, "intensity"),
        ):
            bind(widget, self.separation_settings, field)
        self.separation = SeparationController(
            self.separation_settings, self.image_settings,
            frame_args=tab.frame_args, engrave_lmm=lambda: self.spin_lmm.value(), parent=self)
        self.separation.tone_ready.connect(self._on_separation_tone)
        self.separation.source_changed.connect(self._on_separation_source_changed)
        self.separation.previews_invalidated.connect(self.separation_refresh_preview)
        self._sep_dirty = False          # aperçu à recalculer quand l'onglet sera affiché
        self._sep_view_sizes = {}

    def _sep_update_dpi_label(self):
        self.tab_separation.set_engrave_dpi(self.separation.engrave_dpi())

    # ------------------------------------------------------------------
    # Image source et tonalité envoyée à « Graver une image »
    # ------------------------------------------------------------------
    def separation_load_image(self):
        path, _f = QFileDialog.getOpenFileName(self, tr("image.open_title"), "", tr("image.file_filter"))
        if path:
            self.separation_load_path(path)

    def separation_load_path(self, path):
        try:
            self.separation.load(path)
        except Exception as e:
            QMessageBox.critical(self, tr("image.error_title"), tr("image.load_error").format(error=e))
            return
        self.tab_separation.fit_plate_to_image()
        self.separation.push_tone()

    def separation_rotate_image(self, angle):
        """Pivote l'image source de `angle` degrés (positif = sens antihoraire, comme PIL)
        et échange la largeur et la hauteur de la plaque."""
        if self.separation.rotate(angle):
            self.tab_separation.swap_plate_size()
            self.separation.push_tone()

    def separation_clear_image(self):
        """Retire l'image source et vide les aperçus. L'image déjà envoyée à
        Image & Filtres y reste (elle se supprime depuis cet onglet)."""
        self.separation.clear()
        for view in self.sep_views:
            view.clear_image()
        self._sep_view_sizes = {}

    def _on_separation_source_changed(self, ratio, file_name):
        """Image chargée, pivotée ou retirée."""
        self.tab_separation.set_image_ratio(ratio)
        if ratio is None:
            self.sep_lbl_file.setText(tr("sep.no_image_loaded"))
        elif file_name:
            self.sep_lbl_file.setText(file_name)
        self.update_image_actions_state()

    def separation_release_image_settings(self):
        """Une image est chargée dans « Graver une image » : réglages
        (matière, négatif, miroir) d'avant la Séparation rendus."""
        self.separation.release_glass_settings()

    def _on_separation_tone(self, tone, w_mm, h_mm):
        """Tonalité de la Séparation : devient l'image de « Graver une
        image », à la taille de la plaque."""
        self.raw_image = tone
        self.block_aspect_signal = True
        self.spin_w.setValue(w_mm)
        self.spin_h.setValue(h_mm)
        self.block_aspect_signal = False
        self.display_source_image()
        self.update_image_processing()
        self._sep_update_dpi_label()

    # ------------------------------------------------------------------
    # Aperçus
    # ------------------------------------------------------------------
    def separation_on_processed(self):
        """Appelé par on_image_processed : le calque noir vient d'être recalculé."""
        t_hook = time.perf_counter()
        self._sep_update_dpi_label()
        self.separation.timing = {}
        if self.separation.has_image():
            self.separation_refresh_preview()
        report = self.separation.timing_report(self.processed_array, t_hook, time.perf_counter())
        if report:
            print(report)

    def separation_refresh_if_dirty(self):
        if self._sep_dirty:
            self._sep_render_current()

    def separation_refresh_preview(self):
        """Invalide les aperçus ; seul l'onglet d'aperçu affiché est recalculé
        tout de suite, les autres le seront quand on les ouvrira."""
        if self.separation.source_small is None or self.processed_array is None:
            return
        self.separation.invalidate_previews()
        self._sep_render_current()

    def _sep_render_current(self):
        if self.separation.source_small is None or self.processed_array is None:
            return
        if not self.tab_separation.isVisible():
            self._sep_dirty = True
            return
        self._sep_dirty = False
        index = self.sep_tabs.currentIndex()
        if not self.separation.needs_render(index):
            return
        image = self.separation.render_preview(index, self.processed_array)
        if image is not None:
            t_c = time.perf_counter()
            self._sep_show(index, image)
            self.separation.timing["affichage"] = (time.perf_counter() - t_c) * 1000

    def _sep_show(self, index, im):
        view = self.sep_views[index]
        if self._sep_view_sizes.get(index) != im.size:
            view.clear_image()
            self._sep_view_sizes[index] = im.size
        w, h = im.size
        if im.mode == "L":
            data = im.tobytes()
            qimg = QImage(data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            data = im.convert("RGB").tobytes()
            qimg = QImage(data, w, h, 3 * w, QImage.Format.Format_RGB888)
        view.set_image(qimg.copy())

    # ------------------------------------------------------------------
    # Assistant de calibrage du gain de point
    # ------------------------------------------------------------------
    def separation_gain_test(self):
        """Génère la grille de test du gain de point : une ligne par valeur du
        curseur « Gain de point » (0 à 20), une colonne par ton (0 à 100 %), avec
        la résolution, la vitesse, la puissance et la machine actuelles. Une fois
        gravée, on repère la ligne dont les cases passent régulièrement du noir
        au clair, et on règle le curseur sur la valeur écrite à gauche."""
        mirror = self.image_settings.mirror_h
        arr, w_mm, h_mm = build_gain_test_array(self.spin_lmm.value(), mirror=mirror)
        bed_w, bed_h = self.machine.bed_w, self.machine.bed_h
        if w_mm > bed_w or h_mm > bed_h:
            QMessageBox.warning(
                self, tr("sep.gain_test_title"),
                tr("sep.gain_test_too_big").format(w=w_mm, h=h_mm, bed_w=bed_w, bed_h=bed_h),
            )
            return
        params = self.job.build_params()
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

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def separation_export(self):
        if not self.separation.has_image() or self.processed_array is None:
            QMessageBox.information(self, tr("sep.tab_title"), tr("sep.no_image_loaded"))
            return
        if self.process_timer.isActive() or (self.img_worker and self.img_worker.isRunning()):
            QMessageBox.information(self, tr("sep.tab_title"), tr("sep.not_ready"))
            return
        folder = QFileDialog.getExistingDirectory(self, tr("sep.export_folder"))
        if not folder:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            files, pdf_ok = self.separation.export(folder, self.processed_array)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("laser.error"), str(e))
            return
        QApplication.restoreOverrideCursor()
        msg = tr("sep.files_created") + "\n" + "\n".join(os.path.basename(p) for p in files)
        if not pdf_ok:
            msg += "\n\n" + tr("sep.pdf_too_large")
        QMessageBox.information(self, tr("sep.export_complete"), msg)
