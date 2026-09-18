"""Chargement, transformations et traitement (tramage) de l'image source."""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QGridLayout, QDialog)
from PyQt6.QtGui import QPixmap, QImage
import numpy as np
from PIL import Image, ImageEnhance
from workers import ImageProcessingWorker
from i18n import tr


class ImageProcessingMixin:
    def reset_image_settings(self):
        self.slider_bright.setValue(0)
        self.slider_contrast.setValue(0)
        self.slider_gamma.setValue(100)
        self.chk_invert.setChecked(False)
        self.chk_mirror_h.setChecked(False)
        self.chk_mirror_v.setChecked(False)

    def on_lmm_mode_changed(self, index):
        """Change le mode de saisie de la résolution (Lignes/mm, DPI, ou
        calée sur la focale du laser). L'onglet affiché change, et la
        valeur réelle utilisée en interne (self.spin_lmm, en lignes/mm)
        est recalculée en conséquence."""
        self.stack_lmm_input.setCurrentIndex(index)
        if index == 1:
            # DPI -> lignes/mm, à partir de la valeur DPI déjà affichée.
            self.on_dpi_value_changed(self.spin_dpi.value())
        elif index == 2:
            self._apply_focal_to_lmm()
        else:
            # Mode 'Lignes/mm' : la valeur de spin_lmm fait foi telle quelle
            # (saisie directe ou restaurée au démarrage) — on synchronise
            # simplement le DPI équivalent et la pastille de qualité dessus.
            self._sync_dpi_and_quality_from_lmm(self.spin_lmm.value())

    def on_dpi_value_changed(self, dpi):
        """1 pouce = 25.4 mm : lignes/mm = DPI / 25.4."""
        lmm = dpi / 25.4
        lmm = max(self.spin_lmm.minimum(), min(self.spin_lmm.maximum(), lmm))
        self.spin_lmm.blockSignals(True)
        self.spin_lmm.setValue(lmm)
        self.spin_lmm.blockSignals(False)
        self._update_resolution_quality()
        self.update_image_processing()

    def _sync_dpi_and_quality_from_lmm(self, lmm):
        """Maintient le champ DPI et l'indicateur de qualité synchronisés à
        chaque changement de lignes/mm, quelle que soit son origine (saisie
        directe en mode 'Lignes / mm', ou calcul depuis la focale)."""
        if hasattr(self, "spin_dpi"):
            self.spin_dpi.blockSignals(True)
            self.spin_dpi.setValue(lmm * 25.4)
            self.spin_dpi.blockSignals(False)
        self._update_resolution_quality()

    def _apply_focal_to_lmm(self):
        """Calque l'intervalle de lignes sur la taille du spot laser
        configurée dans l'onglet Paramètres Machine (lignes/mm = 1/focale),
        et met aussi à jour le DPI équivalent en conséquence."""
        focal = self.spin_machine_focal.value() if hasattr(self, "spin_machine_focal") else 0.1
        if focal <= 0:
            focal = 0.1
        lmm = 1.0 / focal
        lmm = max(self.spin_lmm.minimum(), min(self.spin_lmm.maximum(), lmm))
        self.spin_lmm.blockSignals(True)
        self.spin_lmm.setValue(lmm)
        self.spin_lmm.blockSignals(False)
        self._sync_dpi_and_quality_from_lmm(lmm)
        dpi = lmm * 25.4
        self.lbl_focal_info.setText(
    tr("image.focal_info").format(
        focal=focal,
        lmm=lmm,
        dpi=dpi
    )
)
        self.update_image_processing()

    def _on_machine_focal_changed(self, _value):
        """La modification de la focale dans les Paramètres Machine met à
        jour l'intervalle de lignes en direct si le mode 'Focale laser' est
        actif, et rafraîchit sinon simplement l'indicateur de qualité (la
        focale a pu changer même si on n'est pas en mode Focale)."""
        if hasattr(self, "combo_lmm_mode") and self.combo_lmm_mode.currentIndex() == 2:
            self._apply_focal_to_lmm()
        else:
            self._update_resolution_quality()

    def _update_resolution_quality(self):
        """Pastille indiquant si l'écart de lignes actuellement réglé est
        bien adapté à la taille du spot laser configurée, quel que soit le
        mode de saisie utilisé. Le classement est exprimé en multiples de
        la focale (seuils calés sur un tableau de référence à 5 zones) :
          - < 0.6x focale   : trop fin, forte surgravure / risque de brûlure
          - 0.6x - 0.9x     : fin, surgravure probable
          - 0.9x - 1.25x    : fin mais correct
          - 1.25x - 2.25x   : zone recommandée
          - > 2.25x         : grossier mais correct
        """
        if not hasattr(self, "lbl_resolution_quality") or not hasattr(self, "spin_machine_focal"):
            return
        focal = self.spin_machine_focal.value()
        lmm = self.spin_lmm.value()
        if focal <= 0 or lmm <= 0:
            self.lbl_resolution_quality.setText("")
            return
        spacing = 1.0 / lmm
        ratio = spacing / focal
        if ratio < 0.6:
            text, color = tr("image.quality_too_fine"), "#e05656"
        elif ratio < 0.9:
            text, color = tr("image.quality_fine"), "#e0a656"
        elif ratio < 1.25:
            text, color = tr("image.quality_fine_ok"), "#999999"
        elif ratio <= 2.25:
            text, color = tr("image.quality_recommended"), "#56c271"
        else:
            text, color = tr("image.quality_coarse"), "#999999"
        self.lbl_resolution_quality.setText(
    tr("image.quality_result").format(
        spacing=spacing,
        ratio=ratio,
        quality=text
    )
)
        self.lbl_resolution_quality.setStyleSheet(f"color: {color};")

    def goto_laser_focal_settings(self):
        """Bascule vers l'onglet Paramètres Machine et met le focus sur le
        champ de focale, pour un accès rapide depuis Image & Filtres."""
        if hasattr(self, "settings_tabs") and hasattr(self, "tab_machine_params"):
            self.settings_tabs.setCurrentWidget(self.tab_machine_params)
        if hasattr(self, "spin_machine_focal"):
            self.spin_machine_focal.setFocus()

    def save_current_lmm_as_focal(self):
        """Synchronisation dans l'autre sens : enregistre l'écart de lignes
        actuellement réglé (mode Lignes/mm ou DPI) comme focale du laser
        dans les Paramètres Machine, après confirmation, puis sauvegarde ce
        réglage machine tout de suite."""
        if not hasattr(self, "spin_machine_focal"):
            return
        lmm = self.spin_lmm.value()
        if lmm <= 0:
            return
        new_focal = 1.0 / lmm
        current_focal = self.spin_machine_focal.value()
        reply = QMessageBox.question(
            self, tr("image.save_focal_title"),
            tr("image.save_focal_question").format(
                current=current_focal,
                new=new_focal
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.spin_machine_focal.setValue(new_focal)
        self.save_machine_settings()
        QMessageBox.information(
    self,
    tr("image.focal_saved_title"),
    tr("image.focal_saved").format(focal=new_focal)
)

    def rotate_image_left(self):
        if self.raw_image:
            self.raw_image = self.raw_image.rotate(90, expand=True)
            w, h = self.raw_image.size
            self.block_aspect_signal = True
            self.spin_w.setValue(100.0)
            self.spin_h.setValue(100.0 * (h / w))
            self.block_aspect_signal = False
            self.display_source_image()
            self.update_image_processing()

    def rotate_image_right(self):
        if self.raw_image:
            self.raw_image = self.raw_image.rotate(270, expand=True)
            w, h = self.raw_image.size
            self.block_aspect_signal = True
            self.spin_w.setValue(100.0)
            self.spin_h.setValue(100.0 * (h / w))
            self.block_aspect_signal = False
            self.display_source_image()
            self.update_image_processing()

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(
    self,
    tr("image.open_title"),
    "",
    tr("image.file_filter")
)
        if path:
            self.load_image_from_path(path)

    def clear_image(self):
        """Supprime l'image chargée : remet l'onglet Image & Filtres à vide,
        sans toucher aux calques/objets vectoriels ni à la découpe SVG."""
        if not self.raw_image and self.processed_array is None:
            return
        reply = QMessageBox.question(
    self,
    tr("image.delete_title"),
    tr("image.delete_question"),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.raw_image = None
        self.processed_array = None
        self.view_preview_src.clear_image()
        self.view_preview_dither.clear_image()
        self.txt_console.append(tr("image.deleted"))

    def load_image_from_path(self, path):
        try:
            img = Image.open(path)
            # Les PNG avec transparence (RGBA, LA, ou palette avec canal alpha)
            # doivent être aplatis sur un fond blanc avant la conversion en
            # niveaux de gris : sinon PIL garde les valeurs RGB brutes des
            # pixels transparents (souvent noires), qui se retrouvent gravées
            # comme si elles étaient opaques.
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img = img.convert("RGBA")
                background = Image.new("RGBA", img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(background, img)
            self.raw_image = img.convert("L")
            w, h = self.raw_image.size
            self.block_aspect_signal = True
            self.spin_w.setValue(100.0)
            self.spin_h.setValue(100.0 * (h / w))
            self.block_aspect_signal = False
            self.display_source_image()
            self.update_image_processing()
            self.txt_console.append(
    tr("image.loaded").format(path=path)
)
        except Exception as e:
            QMessageBox.critical(
    self,
    tr("image.error_title"),
    tr("image.load_error").format(error=e)
)

    def on_dimension_changed(self, changed_axis, value):
        if self.block_aspect_signal or not self.chk_keep_ratio.isChecked() or not self.raw_image:
            return
        w, h = self.raw_image.size
        aspect = h / w
        self.block_aspect_signal = True
        if changed_axis == 'w':
            self.spin_h.setValue(value * aspect)
        else:
            self.spin_w.setValue(value / aspect)
        self.block_aspect_signal = False
        self.update_image_processing()

    def display_source_image(self):
        if self.raw_image:
            img = self.raw_image.copy()
            qimg = QImage(img.tobytes(), img.width, img.height, img.width, QImage.Format.Format_Grayscale8)
            self.view_preview_src.set_image(qimg)

    def update_image_processing(self, *args):
        self.process_timer.start(150)

    def _do_update_image_processing(self):
        if not self.raw_image:
            return

        if self.img_worker and self.img_worker.isRunning():
            # Un traitement (potentiellement lent : Stucki/Jarvis) est déjà en
            # cours. Au lieu d'ignorer cette demande (ce qui perdait des
            # changements comme le négatif ou l'algorithme choisi), on la
            # mémorise pour la relancer automatiquement dès que le worker
            # actuel se termine, avec les réglages les plus récents.
            self.pending_reprocess = True
            return

        params = {
            'w_mm': self.spin_w.value(),
            'h_mm': self.spin_h.value(),
            'lmm': self.spin_lmm.value(),
            'mirror_h': self.chk_mirror_h.isChecked(),
            'mirror_v': self.chk_mirror_v.isChecked(),
            'bright': self.slider_bright.value(),
            'contrast': self.slider_contrast.value(),
            'gamma': self.slider_gamma.value(),
            'invert': self.chk_invert.isChecked(),
            'algo': self.combo_algo.currentText()
        }

        self.img_worker = ImageProcessingWorker(self.raw_image, params)
        self.img_worker.finished.connect(self.on_image_processed)
        self.img_worker.start()

    def on_image_processed(self, out_arr, dither_img):
        self.processed_array = out_arr
        qimg = QImage(dither_img.tobytes(), dither_img.width, dither_img.height, dither_img.width, QImage.Format.Format_Grayscale8)
        self.view_preview_dither.set_image(qimg)

        if self.pending_reprocess:
            # Des réglages ont changé (ex. négatif coché/décoché, algorithme
            # changé) pendant que ce traitement tournait : on relance tout de
            # suite avec l'état actuel des contrôles, sans attendre une
            # nouvelle interaction de l'utilisateur.
            self.pending_reprocess = False
            self._do_update_image_processing()

    def compare_dither_algorithms(self):
        """Affiche une grille de vignettes comparant chaque algorithme de
        tramage sur l'image chargée (avec les réglages actuels de luminosité/
        contraste/gamma/négatif), pour choisir sans faire d'allers-retours.
        Calculé sur une miniature basse résolution : quasi instantané."""
        if not self.raw_image:
            QMessageBox.information(
    self,
    tr("image.compare_title"),
    tr("image.compare_empty")
)
            return

        img = self.raw_image.copy()
        img.thumbnail((220, 220), Image.Resampling.LANCZOS)

        bright = self.slider_bright.value()
        contrast = self.slider_contrast.value()
        gamma = self.slider_gamma.value() / 100.0
        invert = self.chk_invert.isChecked()

        if bright != 0:
            img = ImageEnhance.Brightness(img).enhance(1.0 + bright / 100.0)
        if contrast != 0:
            img = ImageEnhance.Contrast(img).enhance(1.0 + contrast / 100.0)

        arr = np.array(img, dtype=np.float32)
        if gamma != 1.0:
            arr = 255.0 * ((arr / 255.0) ** (1.0 / gamma))
            arr = np.clip(arr, 0, 255)
        if invert:
            arr = 255.0 - arr

        algos = ["Floyd-Steinberg", "Jarvis, Judice & Ninke", "Stucki", "Atkinson",
                 "Sierra", "Sierra Lite (rapide)", "Burkes",
                 "Bayer 2x2 (ordonné)", "Bayer 4x4 (ordonné)", "Bayer 8x8 (ordonné)"]

        dummy_worker = ImageProcessingWorker(None, {})

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("image.compare_dialog_title"))
        grid = QGridLayout(dialog)
        cols = 5
        for i, algo in enumerate(algos):
            try:
                out_arr = dummy_worker.apply_error_diffusion(arr.copy(), algo)
            except Exception:
                continue
            h, w = out_arr.shape
            qimg = QImage(out_arr.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg)

            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            lbl_img = QLabel()
            lbl_img.setPixmap(pixmap)
            lbl_img.setStyleSheet("border: 1px solid #555;")
            btn_choose = QPushButton(algo)
            btn_choose.clicked.connect(lambda _, a=algo, d=dialog: self._choose_algo_from_comparison(a, d))
            cell_layout.addWidget(lbl_img)
            cell_layout.addWidget(btn_choose)
            grid.addWidget(cell, i // cols, i % cols)

        dialog.exec()

    def _choose_algo_from_comparison(self, algo, dialog):
        self.combo_algo.setCurrentText(algo)
        dialog.accept()

    def on_flip_raster_preview_changed(self, _state):
        if self._last_gcode_text:
            self.plot_gcode_preview(self._last_gcode_text)
