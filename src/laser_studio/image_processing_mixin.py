"""Chargement, transformations et traitement (tramage) de l'image source."""
import os
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QImage
import numpy as np
from PIL import Image, ImageEnhance
from laser_studio.workers import ImageProcessingWorker
from laser_studio.image.filters import sharpen_image
from laser_studio.image.resolution import (
    WARN_BELOW_RATIO, clamp, dpi_to_lmm, focal_to_lmm, lmm_to_dpi, resolution_quality,
)
from laser_studio.image.size import natural_size_mm, read_dpi
from laser_studio.ui.binding import bind
from laser_studio.i18n import tr
from laser_studio.ui.dialogs.dither_comparison import DitherComparisonDialog

# Clé de UIConfig : dernier algorithme de tramage choisi par l'utilisateur.
ALGORITHM_SETTING = "image_algorithm"


class ImageProcessingMixin:
    def _bind_image_settings(self):
        """Lie les champs du tramage (curseurs, négatif, matière, algorithme,
        miroirs) au modèle self.image_settings : chaque changement, d'où
        qu'il vienne (saisie, projet, annulation, Séparation), relance le
        traitement de l'image."""
        settings = self.image_settings
        for widget, field in (
            (self.slider_bright, "brightness"),
            (self.slider_contrast, "contrast"),
            (self.slider_gamma, "gamma"),
            (self.slider_sharp, "sharpness"),
            (self.chk_invert, "invert"),
            (self.app_actions.mirror_h, "mirror_h"),
            (self.app_actions.mirror_v, "mirror_v"),
        ):
            bind(widget, settings, field)
        combo = self.combo_material_bg
        bind(combo, settings, "material_bg",
             to_widget=lambda key: combo.findData(key),
             from_widget=lambda index: combo.itemData(index) or "light")
        algo = self.combo_algo
        bind(algo, settings, "algorithm",
             to_widget=lambda name: algo.findText(name),
             from_widget=lambda index: algo.itemText(index))
        settings.changed.connect(self.update_image_processing)

    def remember_algorithm(self, algorithm):
        """Mémorise l'algorithme de tramage choisi par l'utilisateur (liste « Algorithme » ou
        comparaison des algorithmes) : il est resélectionné au prochain démarrage, donc pour
        les images chargées ensuite. Les changements faits par programme (ouverture d'un projet,
        séparation couleur) ne passent pas par ici."""
        if not algorithm:
            return
        settings = QSettings("LaserStudioPro", "UIConfig")
        settings.setValue(ALGORITHM_SETTING, algorithm)
        settings.sync()  # écriture immédiate sous Windows

    def restore_remembered_algorithm(self):
        """Resélectionne le dernier algorithme choisi, s'il existe encore dans la liste."""
        algorithm = QSettings("LaserStudioPro", "UIConfig").value(ALGORITHM_SETTING, "")
        if algorithm and self.combo_algo.findText(algorithm) >= 0:
            self.image_settings.update(algorithm=algorithm)

    def reset_image_settings(self):
        # Réinitialisation explicite : plus rien à restaurer depuis Séparation.
        self.separation.forget_glass_settings()
        self.image_settings.reset()

    def get_material_bg(self):
        """Matière choisie : "dark" (fond noir) ou "light" (fond clair)."""
        return self.image_settings.material_bg

    def set_material_bg(self, key):
        """Choisit la matière SANS toucher au négatif (projet, Séparation) ;
        une valeur inconnue revient au fond clair."""
        self.image_settings.update(material_bg=key if key in ("dark", "light") else "light")

    def material_summary_text(self):
        """Ex. « Matière : fond noir (négatif activé) » — reflète l'état
        RÉEL du négatif, donc signale une incohérence s'il a été modifié à
        la main."""
        settings = self.image_settings
        bg_key = "gen.material_dark" if settings.material_bg == "dark" else "gen.material_light"
        neg_key = "gen.negative_on" if settings.invert else "gen.negative_off"
        return tr("gen.material_summary").format(bg=tr(bg_key), negative=tr(neg_key))

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
        """DPI saisis : lignes/mm correspondants (voir image.resolution)."""
        lmm = clamp(dpi_to_lmm(dpi), self.spin_lmm.minimum(), self.spin_lmm.maximum())
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
            self.spin_dpi.setValue(lmm_to_dpi(lmm))
            self.spin_dpi.blockSignals(False)
        self._update_resolution_quality()

    def _apply_focal_to_lmm(self):
        """Calque l'intervalle de lignes sur la taille du spot laser
        configurée dans l'onglet Paramètres Machine (lignes/mm = 1/focale),
        et met aussi à jour le DPI équivalent en conséquence."""
        focal = self.machine.focal if hasattr(self, "machine") else 0.1
        if focal <= 0:
            focal = 0.1
        lmm = clamp(focal_to_lmm(focal), self.spin_lmm.minimum(), self.spin_lmm.maximum())
        self.spin_lmm.blockSignals(True)
        self.spin_lmm.setValue(lmm)
        self.spin_lmm.blockSignals(False)
        self._sync_dpi_and_quality_from_lmm(lmm)
        dpi = lmm_to_dpi(lmm)
        self.lbl_focal_info.setText(
    tr("image.focal_info").format(
        focal=focal,
        lmm=lmm,
        dpi=dpi
    )
)
        self.update_image_processing()

    def _on_machine_focal_changed(self, _value):
        """La focale est une caractéristique physique du laser : toute
        modification dans les Paramètres Machine met systématiquement à
        jour Lignes/mm, DPI et la pastille de qualité dans Image & Filtres —
        quel que soit le mode de saisie actuellement sélectionné là-bas
        (en mode 'Lignes/mm' ou 'DPI', un changement de focale ne mettait
        avant à jour que la pastille de qualité, laissant Lignes/mm et DPI
        obsolètes par rapport à la nouvelle focale)."""
        self._apply_focal_to_lmm()
        # Même lien côté onglet Calques : les pastilles de qualité du "Pas
        # remplissage (mm)" de chaque calque dépendent aussi de la focale.
        if hasattr(self, "layers_tab"):
            self.layers_tab.refresh_focal_quality()

    def _sync_matrix_lmm_from_image(self):
        """Reporte automatiquement le lignes/mm de l'onglet Image / Filtre
        (self.spin_lmm) dans la Matrice de Test gravure,
        pour que le test soit fait avec exactement la même densité de lignes
        que la gravure réelle."""
        if hasattr(self, "tab_matrix") and hasattr(self, "spin_lmm"):
            self.tab_matrix.set_lines_mm(self.spin_lmm.value())

    def _sync_separation_with_resolution(self):
        """L'onglet Séparation Couleur / Verre affiche et utilise la résolution
        réglée ici (spin_lmm). Or spin_lmm est modifié avec les signaux bloqués
        dès qu'on saisit des DPI ou qu'on suit la focale : aucun signal
        « valeur changée » n'arrivait donc jusqu'à lui, et son libellé
        « Résolution de gravure : … DPI » restait figé sur la valeur par
        défaut (254 DPI), en désaccord avec le champ DPI d'ici.
        Appelée depuis _update_resolution_quality, point central de tous les
        changements de résolution."""
        separation = getattr(self, "separation", None)
        if separation is None:
            return
        # Libellé de l'onglet mis à jour ; une image est chargée côté Séparation :
        # sa tonalité, cadrée à une densité de pixels qui dépend de la résolution
        # de gravure, est renvoyée.
        separation.resolution_changed()

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
        # Appelée après chaque changement de lignes/mm (saisie, DPI, focale,
        # restauration au démarrage) : point central pour garder la matrice
        # de test synchronisée.
        self._sync_matrix_lmm_from_image()
        self._sync_separation_with_resolution()
        if not hasattr(self, "lbl_resolution_quality") or not hasattr(self, "spin_machine_focal"):
            return
        quality = resolution_quality(self.machine.focal, self.spin_lmm.value())
        # Écart correct ou recommandé : rien à signaler, la ligne ne sert qu'à
        # prévenir d'un réglage trop fin (risque de surgravure / brûlure).
        if quality is None or quality[1] >= WARN_BELOW_RATIO:
            self.lbl_resolution_quality.setText("")
            return
        spacing, ratio, key, color = quality
        self.lbl_resolution_quality.setText(
            tr("image.quality_result").format(spacing=spacing, ratio=ratio, quality=tr(key)))
        self.lbl_resolution_quality.setStyleSheet(f"color: {color};")

    def goto_laser_focal_settings(self):
        """Bascule vers l'onglet Paramètres Machine et met le focus sur le
        champ de focale, pour un accès rapide depuis Image & Filtres."""
        if hasattr(self, "show_settings_window") and hasattr(self, "tab_machine_params"):
            self.show_settings_window("machine_params")
        if hasattr(self, "spin_machine_focal"):
            self.spin_machine_focal.setFocus()

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
        self.update_image_actions_state()
        self.show_status_message(tr("image.deleted"))

    def on_separation_tone(self, tone, w_mm, h_mm):
        """Tonalité de l'onglet Séparation (SeparationController.tone_ready) :
        devient l'image à graver, à la taille de la plaque."""
        self.raw_image = tone
        self.block_aspect_signal = True
        self.spin_w.setValue(w_mm)
        self.spin_h.setValue(h_mm)
        self.block_aspect_signal = False
        self.display_source_image()
        self.update_image_processing()

    def load_image_from_path(self, path):
        # Image classique (Images Tramage) : on rend les réglages miroir /
        # négatif / matière modifiés par un import de l'onglet Séparation.
        separation = getattr(self, "separation", None)
        if separation is not None:
            separation.release_glass_settings()
        try:
            img = Image.open(path)
            file_dpi = read_dpi(img.info)          # lu avant les conversions, qui perdent les métadonnées
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
            # Taille d'origine de l'image (d'après sa résolution enregistrée, 96 DPI à défaut), réduite
            # si besoin pour tenir dans la zone de travail de la machine — et non plus 100 mm d'office.
            bed_w = self.machine.bed_w if hasattr(self, "machine") else None
            bed_h = self.machine.bed_h if hasattr(self, "spin_machine_h") else None
            w_mm, h_mm, used_dpi, shrunk = natural_size_mm(w, h, file_dpi, bed_w, bed_h)
            self.block_aspect_signal = True
            self.spin_w.setValue(w_mm)
            self.spin_h.setValue(h_mm)
            self.block_aspect_signal = False
            self.display_source_image()
            self.update_image_processing()
            if shrunk:
                full_w, full_h, _, _ = natural_size_mm(w, h, file_dpi)
                size_msg = tr("image.natural_size_fit").format(
                    w=w_mm, h=h_mm, ow=full_w, oh=full_h, dpi=used_dpi)
            else:
                size_msg = tr("image.natural_size").format(w=w_mm, h=h_mm, dpi=used_dpi)
            # Barre d'état : nom du fichier seul ; chemin complet dans l'infobulle.
            self.show_status_message(
                f"{tr('image.loaded').format(path=os.path.basename(path))} — {size_msg}",
                f"{tr('image.loaded').format(path=path)}\n{size_msg}")
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
        # Chargement par fichier, projet ou onglet Séparation : tous passent par ici.
        self.update_image_actions_state()

    def undo_image_settings(self):
        """Ctrl+Z dans l'onglet : réglages de tramage d'avant le dernier changement."""
        self.image_history.undo()

    def redo_image_settings(self):
        self.image_history.redo()

    def update_image_processing(self, *args):
        """Retraite l'image peu après le dernier changement (plusieurs
        changements rapprochés : un seul traitement)."""
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
            **self.image_settings.processing_params(),
        }

        self.img_worker = ImageProcessingWorker(self.raw_image, params)
        self.img_worker.finished.connect(self.on_image_processed)
        self.img_worker.start()

    def on_image_processed(self, out_arr, dither_img):
        self.processed_array = out_arr
        qimg = QImage(dither_img.tobytes(), dither_img.width, dither_img.height, dither_img.width, QImage.Format.Format_Grayscale8)
        self.view_preview_dither.set_image(qimg)
        separation = getattr(self, "separation", None)
        if separation is not None:
            separation.engraved_changed()

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

        settings = self.image_settings
        bright = settings.brightness
        contrast = settings.contrast
        gamma = settings.gamma / 100.0
        invert = settings.invert

        if bright != 0:
            img = ImageEnhance.Brightness(img).enhance(1.0 + bright / 100.0)
        if contrast != 0:
            img = ImageEnhance.Contrast(img).enhance(1.0 + contrast / 100.0)

        arr = np.array(img, dtype=np.float32)
        if gamma != 1.0:
            arr = 255.0 * ((arr / 255.0) ** (1.0 / gamma))
            arr = np.clip(arr, 0, 255)
        if settings.sharpness > 0:
            arr = np.array(sharpen_image(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)),
                                         settings.sharpness), dtype=np.float32)
        if invert:
            arr = 255.0 - arr

        algos = ["Floyd-Steinberg", "Jarvis, Judice & Ninke", "Stucki", "Atkinson",
                 "Sierra", "Sierra Lite (rapide)", "Burkes",
                 "Bayer 2x2 (ordonné)", "Bayer 4x4 (ordonné)", "Bayer 8x8 (ordonné)"]

        dummy_worker = ImageProcessingWorker(None, {})
        thumbnails = []
        for algo in algos:
            try:
                thumbnails.append((algo, dummy_worker.apply_error_diffusion(arr.copy(), algo)))
            except Exception:
                continue

        dialog = DitherComparisonDialog(self, thumbnails)
        dialog.algorithm_chosen.connect(lambda name: self.image_settings.update(algorithm=name))
        dialog.algorithm_chosen.connect(self.remember_algorithm)
        dialog.exec()

    def _on_preview_options_changed(self, *_args):
        if self._last_gcode_text:
            self.plot_gcode_preview(self._last_gcode_text)
