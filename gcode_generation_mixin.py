"""Génération, aperçu, estimation et export du G-Code."""
import re
from PyQt6.QtWidgets import (QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QThread, QTimer, QRectF
import pyqtgraph as pg
import numpy as np
from PIL import Image
from svg.path import parse_path
from vector_layers import (
    extract_vector_layer_data
)
from workers import AdvancedGCodeWorker, TestMatrixWorker
from i18n import tr


class GcodeGenerationMixin:
    def export_gcode_with_ext(self, extension):
        gcode_text = self.txt_console.toPlainText()

        if not gcode_text.strip():
            QMessageBox.warning(
                self,
                tr("gcode.empty_title"),
                tr("gcode.empty_export")
            )
            return

        file_filter = tr("gcode.file_filter").format(
            extension=extension
        )
        default_filename = f"job_laser{extension}"

        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("gcode.export_title").format(
                extension=extension
            ),
            default_filename,
            file_filter
        )

        if path:
            if not path.lower().endswith(extension):
                path += extension

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(gcode_text)

                QMessageBox.information(
                    self,
                    tr("gcode.export_success_title"),
                    tr("gcode.export_success").format(path=path)
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    tr("gcode.export_error_title"),
                    tr("gcode.export_error").format(error=e)
                )

    def _plot_raster_reconstruction(self, raster_strokes, tint_color=None):
        """Reconstruit une vraie image en niveaux de gris (ou teintée avec la
        couleur du calque, si fournie) à partir des segments de gravure
        raster (position + puissance S), façon LaserGRBL, affichée sous les
        tracés vectoriels (découpe/calques).

        IMPORTANT : cette fonction ne doit être appelée qu'avec les segments
        d'UN SEUL calque à la fois (voir l'appelant) — mélanger plusieurs
        calques dans un même appel produirait une image bâtarde sans
        rapport avec ce qui est réellement gravé (chaque calque a sa propre
        étendue, sa propre densité de balayage, et parfois même une position
        totalement différente sur la pièce).

        Chaque ligne de balayage est placée à sa position Y RÉELLE et
        proportionnelle dans l'image (pas juste à un indice séquentiel) :
        sinon, un contenu avec de grands espaces vides entre motifs (ex: les
        carrés d'une matrice de test) voit ces espaces comprimés au même
        titre que les lignes de balayage très serrées à l'intérieur d'un
        motif, ce qui écrase et fait se chevaucher visuellement des zones
        qui sont en réalité bien séparées sur la pièce.

        Note honnête : je n'ai pas pu exécuter PyQt6 dans cet environnement
        pour vérifier visuellement l'orientation (haut/bas) du résultat une
        fois affiché par pyqtgraph. Si l'image apparaît retournée, coche la
        case 'Inverser aperçu image' à côté du bouton Générer.
        """
        try:
            rows = {}
            for (x1, y1, x2, y2, s_val) in raster_strokes:
                y_key = round((y1 + y2) / 2.0, 4)
                rows.setdefault(y_key, []).append((min(x1, x2), max(x1, x2), s_val))

            row_ys = sorted(rows.keys())
            if len(row_ys) < 2:
                return

            all_x = [seg[0] for segs in rows.values() for seg in segs] + \
                    [seg[1] for segs in rows.values() for seg in segs]
            min_x, max_x = min(all_x), max(all_x)
            bbox_w = max(max_x - min_x, 0.01)

            min_y_data, max_y_data = row_ys[0], row_ys[-1]
            bbox_h = max(max_y_data - min_y_data, 0.01)

            target_cols = 1200
            px_per_mm_x = target_cols / bbox_w
            img_w = max(1, int(round(bbox_w * px_per_mm_x)))

            # La densité verticale doit être calée sur l'écart RÉEL entre
            # deux lignes de balayage consécutives (pas sur une densité
            # dérivée de la largeur totale) : sinon, dès que le contenu a
            # plusieurs motifs séparés en largeur (ex: les colonnes d'une
            # matrice de test), la densité verticale déduite de la largeur
            # totale est bien plus grossière que le pas de balayage réel —
            # certaines lignes de sortie ne reçoivent alors aucune ligne
            # source (restent blanches) pendant que d'autres en reçoivent
            # plusieurs, créant un effet de bandes/hachures horizontales.
            row_gaps = [b - a for a, b in zip(row_ys[:-1], row_ys[1:]) if b - a > 0.001]
            min_row_spacing = min(row_gaps) if row_gaps else bbox_h
            px_per_mm_y_needed = 1.0 / min_row_spacing
            img_h = max(1, min(6000, int(round(bbox_h * px_per_mm_y_needed))))
            px_per_mm_y = img_h / bbox_h

            s_all = [seg[2] for segs in rows.values() for seg in segs if seg[2]]
            max_s = max(s_all) if s_all else 1.0
            if max_s <= 0:
                max_s = 1.0

            # power[ligne, colonne] : puissance normalisée (0-1). ligne 0 =
            # Y le plus petit (bas de la gravure). On combine les
            # chevauchements avec un maximum (la puissance la plus forte
            # gagne visuellement), pas une moyenne.
            power_arr = np.zeros((img_h, img_w), dtype=np.float32)
            for y_key in row_ys:
                row_idx = int(round((y_key - min_y_data) * px_per_mm_y))
                row_idx = max(0, min(img_h - 1, row_idx))
                for (xa, xb, s_val) in rows[y_key]:
                    if not s_val or s_val <= 0:
                        continue
                    power = min(max(s_val / max_s, 0.0), 1.0)
                    col_a = max(0, min(img_w - 1, int(round((xa - min_x) * px_per_mm_x))))
                    col_b = max(col_a + 1, min(img_w, int(round((xb - min_x) * px_per_mm_x)) + 1))
                    np.maximum(power_arr[row_idx, col_a:col_b], power, out=power_arr[row_idx, col_a:col_b])

            negative_preview = bool(getattr(self, "chk_negative_raster_preview", None)
                                     and self.chk_negative_raster_preview.isChecked())
            if negative_preview:
                power_arr = 1.0 - power_arr  # négatif : plus de puissance = plus clair

            # Les zones sans puissance doivent rester transparentes.
            # Sinon l'ImageItem crée un grand rectangle blanc autour de la
            # gravure importée, ce qui masque le fond et les autres tracés.
            #
            # La puissance sert à la fois :
            # - à déterminer l'intensité de la couleur ;
            # - à déterminer l'opacité du pixel.
            #
            # Ainsi, seuls les déplacements réellement gravés sont visibles.

            if negative_preview:
                # En mode négatif, on conserve volontairement un rendu
                # opaque pour que l'inversion reste lisible.
                if tint_color:
                    tint_rgb = pg.mkColor(tint_color).getRgb()[:3]
                    white = np.array([255, 255, 255], dtype=np.float32)
                    tint = np.array(tint_rgb, dtype=np.float32)
                    blend = power_arr[..., None]
                    rgb = white + blend * (tint - white)
                    arr = np.clip(rgb, 0, 255).astype(np.uint8)
                else:
                    gray = 255 * (1.0 - power_arr)
                    arr = np.clip(gray, 0, 255).astype(np.uint8)

                pg_array = (
                    arr.transpose(1, 0, 2)
                    if tint_color
                    else arr.T
                )

            else:
                # Rendu transparent :
                # - fond sans gravure : alpha 0 ;
                # - puissance maximale : alpha 255 ;
                # - gravure noire ou teintée au-dessus du fond du graphique.
                if tint_color:
                    tint_rgb = np.array(
                        pg.mkColor(tint_color).getRgb()[:3],
                        dtype=np.uint8
                    )
                    rgb = np.zeros(
                        (*power_arr.shape, 3),
                        dtype=np.uint8
                    )
                    rgb[:, :, :] = tint_rgb
                else:
                    rgb = np.zeros(
                        (*power_arr.shape, 3),
                        dtype=np.uint8
                    )

                alpha = np.clip(
                    power_arr * 255.0,
                    0,
                    255
                ).astype(np.uint8)

                rgba = np.dstack((rgb, alpha))
                pg_array = rgba.transpose(1, 0, 2)
            if getattr(self, "chk_flip_raster_preview", None) and self.chk_flip_raster_preview.isChecked():
                pg_array = pg_array[:, ::-1] if not tint_color else pg_array[:, ::-1, :]

            image_item = pg.ImageItem(pg_array)

            # Le tableau est déjà en RGBA lorsque le rendu transparent est
            # utilisé. Il ne faut pas appliquer de niveaux de gris dans ce
            # cas, sinon l'alpha peut être ignoré ou mal interprété.
            if not tint_color and negative_preview:
                image_item.setLevels([0, 255])
            image_item.setRect(QRectF(min_x, min_y_data, bbox_w, bbox_h))
            image_item.setZValue(-50)
            # Sans ça, pyqtgraph affiche l'image dézoomée en échantillonnant
            # un pixel source sur N au hasard (plus-proche-voisin) plutôt
            # qu'en moyennant : sur du tramage fin noir/blanc, ça donne un
            # bruit gris illisible tant qu'on n'a pas zoomé fort. Avec le
            # downsampling automatique, pyqtgraph fait une vraie moyenne des
            # pixels à l'affichage, donnant un aperçu correct dès la vue
            # d'ensemble (comme LaserGRBL), sans perdre le détail au zoom.
            image_item.setAutoDownsample(True)
            self.plot_widget.addItem(image_item)
        except Exception as e:
            self.txt_console.append(f"; Aperçu image raster indisponible : {e}")

    def _format_duration(self, seconds):
        seconds = max(0, int(seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m:02d}min"
        return f"{m}min {s:02d}s"

    def estimate_job_time(self):
        """Estimation RAPIDE du temps de gravure/découpe, sans générer le
        G-Code complet : utile pour ajuster vitesse/résolution avant de
        lancer un calcul complet (qui peut prendre du temps sur une grande
        image). Approximatif par nature (ignore accélérations/G0)."""
        total_seconds = 0.0
        details = []

        if self.processed_array is not None:
            h_mm = self.spin_h.value()
            w_mm = self.spin_w.value()
            lmm = self.spin_lmm.value()
            speed = self.spin_speed_engrave.value()
            overscan_dist = getattr(self, "spin_overscan", None)
            overscan = overscan_dist.value() if overscan_dist else 0.0
            rows = max(1, int(h_mm * lmm))
            distance = rows * (w_mm + 2 * overscan)
            t = (distance / max(speed, 1)) * 60.0
            total_seconds += t
            details.append(tr("gcode.image_details").format(
                duration=self._format_duration(t)
            ))

        if self.loaded_svg_path:
            try:
                from svg.path import parse_path
                import xml.etree.ElementTree as ET
                tree = ET.parse(self.loaded_svg_path)
                total_len_svg = 0.0
                for elem in tree.iter():
                    d = elem.attrib.get('d')
                    if d:
                        try:
                            total_len_svg += parse_path(d).length(error=1e-3)
                        except Exception:
                            pass
                speed_cut = self.spin_speed_cut.value()
                passes_cut = self.spin_passes_cut.value()
                t = (total_len_svg / max(speed_cut, 1)) * 60.0 * passes_cut
                total_seconds += t
                details.append(tr("gcode.svg_details").format(
                    duration=self._format_duration(t)
                ))
            except Exception:
                pass

        if hasattr(self, 'vector_canvas'):
            for layer in self.layer_manager.layers:
                if not layer.enabled:
                    continue
                objs = [o for o in self.vector_canvas.objects if o.layer_id == layer.id]
                if not objs:
                    continue
                if layer.mode == "Gravure Remplie":
                    total_area = sum(o.world_path().boundingRect().width() *
                                      o.world_path().boundingRect().height() for o in objs)
                    length_est = total_area / max(layer.line_interval, 0.02)
                    t = (length_est / max(layer.speed, 1)) * 60.0
                else:
                    total_len = sum(o.world_path().length() for o in objs)
                    t = (total_len / max(layer.speed, 1)) * 60.0 * max(layer.passes, 1)
                total_seconds += t
                details.append(tr("gcode.layer_details").format(
                    name=layer.name,
                    duration=self._format_duration(t)
                ))

        if total_seconds == 0.0:
            QMessageBox.information(
                self,
                tr("gcode.estimate_title"),
                tr("gcode.nothing_to_estimate")
            )
            return

        msg = tr("gcode.estimate_details").format(
            details="\n".join(details),
            total=self._format_duration(total_seconds)
        )

        QMessageBox.information(
            self,
            tr("gcode.estimate_title_full"),
            msg
        )

    def import_gcode_file(self):
        """Importe un fichier G-Code existant (généré par un autre outil : LaserGRBL,
        le multi-générateur kpc29laser/MGL, un export G-Code de LightBurn, etc.) pour
        l'afficher dans la console et le visualiser dans l'aperçu 2D, sans passer par
        le pipeline de génération interne (image/vecteurs) de l'application."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("gcode.import_title"),
            "",
            tr("gcode.import_filter")
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                gcode_text = f.read()
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("gcode.export_error_title"),
                tr("gcode.import_error").format(error=e)
            )
            return

        self.txt_console.setPlainText(gcode_text)
        num_lines = len([l for l in gcode_text.split('\n') if l.strip()])
        self.lbl_stat_lines.setText(f"Lignes: {num_lines}")
        self.lbl_stat_power.setText("Puissance Moyenne: — (fichier importé)")
        self.lbl_stat_time.setText("Temps Estimé: — (fichier importé)")
        self.plot_gcode_preview(gcode_text)
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)
        self.txt_console.append(
    tr("gcode.imported_from").format(path=path)
)

    def generate_job(self):
        try:
            self._generate_job_impl()
        except Exception as e:
            import traceback
            error_text = f"{e}\n\n{traceback.format_exc()}"
            self.gen_progress_bar.setVisible(False)
            self.gen_progress_bar_vector.setVisible(False)
            self.gen_progress_bar_main.setVisible(False)
            self.txt_console.append(f"\n; ERREUR AVANT GÉNÉRATION :\n; {error_text}")
            QMessageBox.critical(self, "Erreur", f"Impossible de démarrer la génération :\n\n{error_text}")

    def _generate_job_impl(self):
        job_w = self.spin_w.value()
        job_h = self.spin_h.value()
        bed_w = self.spin_machine_w.value()
        bed_h = self.spin_machine_h.value()
        if job_w > bed_w or job_h > bed_h:
            QMessageBox.warning(
                self, "Dimensions trop grandes",
                f"La zone de gravure configurée ({job_w:.1f} x {job_h:.1f} mm) dépasse la "
                f"surface de travail de la machine ({bed_w:.1f} x {bed_h:.1f} mm, définie dans "
                f"l'onglet 'Paramètres Machine').\n\n"
                "Ce n'est pas possible avec ces réglages : réduis les dimensions du job "
                "(onglet 'Dimensions & Origine') ou agrandis la zone machine avant de continuer."
            )
            return

        max_speed_limit = self.spin_machine_max_speed.value()
        speeds_to_check = [("Vitesse Gravure", self.spin_speed_engrave.value())]
        if self.chk_enable_cut.isChecked():
            speeds_to_check.append(("Vitesse Découpe (ancien mode)", self.spin_speed_cut.value()))
        for layer in self.layer_manager.layers:
            if layer.enabled:
                speeds_to_check.append((f"Calque « {layer.name} »", layer.speed))
        over_limit = [(name, spd) for name, spd in speeds_to_check if spd > max_speed_limit]
        if over_limit:
            details = "\n".join(f"  • {name} : {spd:.0f} mm/min" for name, spd in over_limit)
            reply = QMessageBox.warning(
                self, "Vitesse au-delà des limites machine",
                f"La machine active a une vitesse max de {max_speed_limit:.0f} mm/min "
                f"(onglet 'Paramètres Machine'), mais ces réglages la dépassent :\n\n{details}\n\n"
                "Continuer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        has_image = self.processed_array is not None
        has_vector_objects = hasattr(self, "vector_canvas") and len(self.vector_canvas.objects) > 0
        if has_image and has_vector_objects:
            layer_names = sorted(set(
                self.layer_manager.get(o.layer_id).name
                for o in self.vector_canvas.objects
                if self.layer_manager.get(o.layer_id)
            ))
            summary = (
                f"• Gravure de l'image chargée\n"
                f"• {len(self.vector_canvas.objects)} objet(s) vectoriel(s) sur "
                f"{len(layer_names)} calque(s) : {', '.join(layer_names) if layer_names else '—'}"
            )
            reply = QMessageBox.question(
                self, "Confirmer la génération",
                f"Ce job va combiner :\n\n{summary}\n\n"
                "Confirmer et générer le G-Code, ou annuler pour modifier d'abord ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        params = {
            'width_mm': self.spin_w.value(),
            'height_mm': self.spin_h.value(),
            'origin_pos': self.combo_origin.currentText(),
            'offset_x': self.spin_off_x.value(),
            'offset_y': self.spin_off_y.value(),
            'speed_engrave': self.spin_speed_engrave.value(),
            'power_engrave': self.spin_power_engrave.value(),
            'enable_cut': self.chk_enable_cut.isChecked(),
            'speed_cut': self.spin_speed_cut.value(),
            'power_cut': self.spin_power_cut.value(),
            'passes_cut': self.spin_passes_cut.value(),
            'laser_cmd': self.combo_laser_cmd.currentText().split()[0],
            'algo': self.combo_algo.currentText(),
            's_max': self.spin_smax.value(),
            'homing': self.chk_homing.isChecked(),
            'enable_overscan': self.chk_overscan.isChecked(),
            'overscan_mode': self.combo_overscan_mode.currentText(),
            'overscan_dist': self.spin_overscan_dist.value(),
            'overscan_pct': self.spin_overscan_pct.value(),
            'start_gcode': self.txt_start_gcode.toPlainText(),
            'end_gcode': self.txt_end_gcode.toPlainText()
        }

        if params['enable_overscan'] and self.processed_array is not None:
            if params['overscan_mode'] == "Pourcentage (%)":
                overscan_check = params['width_mm'] * (params['overscan_pct'] / 100.0)
            else:
                overscan_check = params['overscan_dist']

            if params['origin_pos'] == "Centre":
                base_x_check = params['offset_x'] - (params['width_mm'] / 2.0)
            else:
                base_x_check = params['offset_x']

            if base_x_check - overscan_check < 0:
                QMessageBox.critical(
                    self, "Position invalide (Surbalayage)",
                    f"Avec le surbalayage actuel ({overscan_check:.2f} mm) et le décalage X "
                    f"configuré ({params['offset_x']:.2f} mm), le point de départ calculé serait "
                    f"à X={base_x_check - overscan_check:.2f} mm — une position NÉGATIVE, "
                    "impossible pour la machine.\n\n"
                    "Augmente le décalage X (onglet 'Dimensions & Origine') ou réduis la distance "
                    "de surbalayage (onglet 'Configuration GRBL') avant de générer."
                )
                return

        # Extraction géométrique des calques vectoriels (texte/formes) : se fait
        # ici dans le thread principal (Qt requis), le résultat est du texte/nombres
        # purs, sans risque pour le QThread qui va s'en servir.
        vector_layers_data = extract_vector_layer_data(
            self.vector_canvas.objects, self.layer_manager
        ) if hasattr(self, "vector_canvas") else {}

        if params['enable_overscan'] and hasattr(self, "vector_canvas"):
            if params['overscan_mode'] == "Pourcentage (%)":
                vec_overscan_check = params['width_mm'] * (params['overscan_pct'] / 100.0)
            else:
                vec_overscan_check = params['overscan_dist']

            for layer_id, data in vector_layers_data.items():
                layer = data["layer"]
                if layer["mode"] != "Gravure Remplie" or not data["polygons"]:
                    continue
                min_x = min(p[0] for poly in data["polygons"] for p in poly)
                base_x = params['offset_x'] - (params['width_mm'] / 2.0) if params['origin_pos'] == "Centre" else params['offset_x']
                if base_x + min_x - vec_overscan_check < 0:
                    QMessageBox.critical(
                        self, "Position invalide (Surbalayage — calque vectoriel)",
                        f"Le calque « {layer['name']} » (Gravure Remplie) commence trop près du "
                        f"bord gauche pour le surbalayage configuré ({vec_overscan_check:.2f} mm) : "
                        f"le point de départ serait à X={base_x + min_x - vec_overscan_check:.2f} mm — "
                        "une position NÉGATIVE, impossible pour la machine.\n\n"
                        "Déplace cet objet vers la droite dans l'éditeur vectoriel, ou réduis la "
                        "distance de surbalayage (onglet 'Configuration GRBL') avant de générer."
                    )
                    return

        self.worker = AdvancedGCodeWorker(self.processed_array, self.loaded_svg_path, params, vector_layers_data)
        self.worker.finished.connect(self.on_gcode_generated)
        self.worker.progress.connect(self.on_gcode_generation_progress)
        self.worker.error.connect(self.on_gcode_generation_error)
        self.gen_progress_bar.setValue(0)
        self.gen_progress_bar.setVisible(True)
        self.lbl_gen_progress.setText("Génération en cours…")
        self.gen_progress_bar_vector.setValue(0)
        self.gen_progress_bar_vector.setVisible(True)
        self.lbl_gen_progress_vector.setText("Génération en cours…")
        self.gen_progress_bar_main.setValue(0)
        self.gen_progress_bar_main.setVisible(True)
        self.lbl_gen_progress_main.setText("Génération en cours…")
        self.worker.start()

    def on_gcode_generation_error(self, error_text):
        self.gen_progress_bar.setVisible(False)
        self.lbl_gen_progress.setText("")
        self.gen_progress_bar_vector.setVisible(False)
        self.lbl_gen_progress_vector.setText("")
        self.gen_progress_bar_main.setVisible(False)
        self.lbl_gen_progress_main.setText("")
        self.txt_console.append(f"\n; ERREUR DE GÉNÉRATION :\n; {error_text}")
        QMessageBox.critical(self, "Erreur de génération", f"La génération du G-Code a échoué :\n\n{error_text}")

    def on_gcode_generation_progress(self, pct):
        self.gen_progress_bar.setValue(pct)
        self.lbl_gen_progress.setText(f"Génération en cours… {pct}%")
        self.gen_progress_bar_vector.setValue(pct)
        self.lbl_gen_progress_vector.setText(f"Génération en cours… {pct}%")
        self.gen_progress_bar_main.setValue(pct)
        self.lbl_gen_progress_main.setText(f"Génération en cours… {pct}%")

    def generate_test_matrix(self):
        params = {
            'min_power': self.spin_mat_min_p.value(),
            'max_power': self.spin_mat_max_p.value(),
            'steps_power': self.spin_mat_steps_p.value(),
            'single_power': self.spin_mat_min_p.value(),
            'min_passes': self.spin_mat_min_passes.value(),
            'max_passes': self.spin_mat_max_passes.value(),
            'steps_passes': self.spin_mat_steps_passes.value(),
            'min_speed': self.spin_mat_min_s.value(),
            'max_speed': self.spin_mat_max_s.value(),
            'steps_speed': self.spin_mat_steps_s.value(),
            'size_square': self.spin_mat_size.value(),
            'gap': self.spin_mat_gap.value(),
            'mode': self.combo_mat_mode.currentText(),
            'lines_mm': self.spin_mat_lmm.value(),
            'matrix_offset_x': self.spin_mat_off_x.value(),
            'matrix_offset_y': self.spin_mat_off_y.value(),
            's_max': self.spin_smax.value(),
            'laser_cmd': self.combo_mat_laser_cmd.currentText().split()[0],
            'homing': self.chk_mat_homing.isChecked(),
            'enable_overscan': self.chk_overscan.isChecked(),
            'overscan_mode': self.combo_overscan_mode.currentText(),
            'overscan_dist': self.spin_overscan_dist.value(),
            'overscan_pct': self.spin_overscan_pct.value(),
        }
        # Mémorisé pour permettre le clic sur une case de l'aperçu 2D
        # (voir _on_plot_clicked) afin d'appliquer directement sa
        # puissance/vitesse aux réglages de gravure/découpe courants.
        self.last_test_matrix_params = dict(params)

        self.matrix_worker = TestMatrixWorker(params)
        self.matrix_worker.finished.connect(self.on_gcode_generated)
        self.matrix_worker.start()

    def _on_plot_clicked(self, event):
        """Clic sur l'aperçu 2D : si le G-Code affiché est bien la dernière
        matrice de test générée, retrouve la case cliquée et applique sa
        puissance/vitesse (ou nombre de passes) aux réglages de gravure ou
        de découpe courants — évite de retaper les valeurs à la main une
        fois la case idéale repérée visuellement."""
        params = getattr(self, "last_test_matrix_params", None)
        if not params:
            return
        try:
            view_box = self.plot_widget.getPlotItem().vb
            pos = view_box.mapSceneToView(event.scenePos())
            x_mm, y_mm = pos.x(), pos.y()

            offset_labels_x, offset_labels_y = 22.0, 14.0
            mat_off_x = params.get('matrix_offset_x', 0.0)
            mat_off_y = params.get('matrix_offset_y', 0.0)
            start_x = mat_off_x + offset_labels_x
            start_y = mat_off_y + offset_labels_y
            sq_size = params['size_square']
            gap = params['gap']

            min_s, max_s, steps_s = params['min_speed'], params['max_speed'], int(params['steps_speed'])
            speeds = np.linspace(min_s, max_s, steps_s)

            mode = params.get('mode', 'Gravure')
            if mode == "Gravure":
                min_p, max_p, steps_p = params['min_power'], params['max_power'], int(params['steps_power'])
                col_values = np.linspace(min_p, max_p, steps_p)
            else:
                min_pa, max_pa, steps_pa = params['min_passes'], params['max_passes'], int(params['steps_passes'])
                col_values = np.unique(np.round(np.linspace(min_pa, max_pa, steps_pa))).astype(int)

            col = int((x_mm - start_x) // (sq_size + gap))
            row = int((y_mm - start_y) // (sq_size + gap))
            if not (0 <= col < len(col_values) and 0 <= row < len(speeds)):
                return
            cell_x0 = start_x + col * (sq_size + gap)
            cell_y0 = start_y + row * (sq_size + gap)
            if not (cell_x0 <= x_mm <= cell_x0 + sq_size and cell_y0 <= y_mm <= cell_y0 + sq_size):
                return  # clic dans l'espace entre les cases, pas dans une case

            speed_val = round(float(speeds[row]))
            if mode == "Gravure":
                power_val = round(float(col_values[col]))
                self.spin_speed_engrave.setValue(speed_val)
                self.spin_power_engrave.setValue(power_val)
                self.txt_console.append(f">>> Case matrice appliquée : {speed_val} mm/min, {power_val}% (gravure)")
            else:
                passes_val = int(col_values[col])
                self.spin_speed_cut.setValue(speed_val)
                self.spin_passes_cut.setValue(passes_val)
                self.spin_power_cut.setValue(round(params.get('single_power', self.spin_power_cut.value())))
                self.txt_console.append(f">>> Case matrice appliquée : {speed_val} mm/min, {passes_val} passe(s) (découpe)")
        except Exception:
            pass  # un clic hors matrice ou une erreur de calcul ne doit jamais planter l'appli

    def on_gcode_generated(self, gcode_str, num_lines, avg_power, time_str):
        self.gen_progress_bar.setValue(100)
        self.lbl_gen_progress.setText("Terminé ✓")
        QTimer.singleShot(1500, lambda: (self.gen_progress_bar.setVisible(False), self.lbl_gen_progress.setText("")))
        self.gen_progress_bar_vector.setValue(100)
        self.lbl_gen_progress_vector.setText("Terminé ✓")
        QTimer.singleShot(1500, lambda: (self.gen_progress_bar_vector.setVisible(False), self.lbl_gen_progress_vector.setText("")))
        self.gen_progress_bar_main.setValue(100)
        self.lbl_gen_progress_main.setText("Terminé ✓")
        QTimer.singleShot(1500, lambda: (self.gen_progress_bar_main.setVisible(False), self.lbl_gen_progress_main.setText("")))
        self.txt_console.setPlainText(gcode_str)
        self.lbl_stat_lines.setText(f"Lignes: {num_lines}")
        self.lbl_stat_power.setText(f"Puissance Moyenne: {avg_power:.1f} %")
        self.lbl_stat_time.setText(f"Temps Estimé: {time_str}")
        self.plot_gcode_preview(gcode_str)
        
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)

    def update_gcode_position_marker(self, x, y):
        """Met à jour le marqueur de position temps réel (DRO) affiché sur
        l'aperçu 2D G-Code, à partir de la position machine renvoyée par
        GRBL (MPos ou WPos selon le réglage $10 du firmware). Remarque :
        aucune compensation d'un éventuel décalage G92/G54 n'est appliquée
        ici — ce marqueur est un repère visuel approximatif de suivi de
        job, pas une mesure de précision.
        """
        if not hasattr(self, "gcode_position_marker"):
            return
        self.gcode_position_marker.setData([x], [y])

    def plot_gcode_preview(self, gcode_text):
        self._last_gcode_text = gcode_text
        try:
            self._plot_gcode_preview_impl(gcode_text)
        except Exception as e:
            # Ne jamais laisser l'aperçu 2D silencieusement vide : si le G-Code
            # (notamment un fichier importé d'un autre outil) contient une
            # ligne inattendue qui fait planter l'analyse, on le signale
            # clairement dans la console plutôt que d'afficher un graphique vide.
            self.txt_console.append(f"\n; ERREUR aperçu 2D : {e}")
            QMessageBox.warning(self, "Aperçu 2D",
                                 f"L'aperçu 2D n'a pas pu être généré pour ce G-Code :\n{e}")

    def _plot_gcode_preview_impl(self, gcode_text):
        self.plot_widget.clear()

        # Chaque phase (image / découpe SVG) et chaque calque vectoriel est
        # tracé avec sa propre couleur, repérable via les marqueurs de
        # commentaires déjà présents dans le G-Code généré.
        DEFAULT_SVG_COLOR = "#ff00ff"
        DEFAULT_LAYER_COLOR = "#00ff88"
        RASTER_LABEL = "Gravure Image (Raster)"
        UNKNOWN_LABEL = "G-Code (import ou sans calque identifié)"

        current_label = UNKNOWN_LABEL
        current_color = "#00ff88"
        current_layer_mode = None
        current_is_test_matrix = False

        g0_x, g0_y = [], []
        ov_x, ov_y = [], []
        g1_travel_x, g1_travel_y = [], []  # G1 à puissance nulle (déplacement, pas de gravure)
        g1_segments = {}  # (label, color) -> ([xs], [ys]) avec NaN en séparateur
        seen_order = []   # ordre d'apparition, pour une légende stable
        raster_strokes_by_key = {}  # (label,color) -> [(x1,y1,x2,y2,S), ...]
        layer_mode_by_key = {}  # (label,color) -> mode de calque / matrice / image
        cx, cy = 0.0, 0.0
        last_modal_g = None
        last_modal_s = None

        token_re = re.compile(r'([A-Za-z])\s*(-?\d*\.?\d+)')

        for line in gcode_text.split('\n'):
            raw_line = line.strip()
            if not raw_line:
                continue

            try:
                if raw_line.startswith(';'):
                    if 'PHASE 1' in raw_line and 'GRAVURE IMAGE' in raw_line:
                        current_label, current_color = RASTER_LABEL, "#ffaa00"
                        current_layer_mode = "Gravure Remplie"
                        current_is_test_matrix = False
                    elif 'PHASE 2' in raw_line and 'DÉCOUPE VECTORIELLE SVG' in raw_line:
                        current_label, current_color = "Découpe SVG (import)", DEFAULT_SVG_COLOR
                        current_layer_mode = "Découpe"
                        current_is_test_matrix = False
                    elif raw_line.startswith('; --- MATRICE DE TEST LASER'):
                        current_label = "Matrice de test"
                        current_color = "#00ff88"
                        current_layer_mode = "Matrice"
                        current_is_test_matrix = True
                    elif raw_line.startswith('; --- CALQUE'):
                        m = re.match(r"; --- CALQUE '(.+)' \[(.+)\] ---", raw_line)
                        if m:
                            layer_name = m.group(1)
                            layer_mode = m.group(2)
                            layer = next((l for l in self.layer_manager.layers if l.name == layer_name), None)
                            current_label = f"Calque « {layer_name} »"
                            current_color = layer.color if layer else DEFAULT_LAYER_COLOR
                            current_layer_mode = layer_mode
                            current_is_test_matrix = False
                    continue

                is_overscan = 'OVERSCAN_' in raw_line.upper()
                code_part = raw_line.split(';')[0].strip()
                if not code_part:
                    continue

                tokens = token_re.findall(code_part)
                if not tokens:
                    continue

                nx, ny, g_word, s_word, m_word = cx, cy, None, None, None
                for letter, value in tokens:
                    L = letter.upper()
                    try:
                        if L == 'G':
                            g_word = int(float(value))
                        elif L == 'M':
                            m_word = int(float(value))
                        elif L == 'X':
                            nx = float(value)
                        elif L == 'Y':
                            ny = float(value)
                        elif L == 'S':
                            s_word = float(value)
                    except ValueError:
                        pass

                if g_word is not None:
                    last_modal_g = g_word
                cmd_g = g_word if g_word is not None else last_modal_g

                if s_word is not None:
                    last_modal_s = s_word
                elif m_word == 5:
                    last_modal_s = 0.0

                if is_overscan:
                    ov_x.extend([cx, nx, float('nan')])
                    ov_y.extend([cy, ny, float('nan')])
                elif cmd_g == 0:
                    g0_x.extend([cx, nx, float('nan')])
                    g0_y.extend([cy, ny, float('nan')])
                elif cmd_g == 1:
                    key = (current_label, current_color)
                    has_power = last_modal_s is not None and last_modal_s > 0

                    if has_power:
                        # Gravure réelle : comptée pour la légende et
                        # affichée dans la couleur du calque/label.
                        if key not in g1_segments:
                            g1_segments[key] = ([], [])
                            seen_order.append(key)
                            layer_mode_by_key[key] = current_layer_mode
                        xs, ys = g1_segments[key]
                        xs.extend([cx, nx, float('nan')])
                        ys.extend([cy, ny, float('nan')])
                        raster_strokes_by_key.setdefault(key, []).append((cx, cy, nx, ny, last_modal_s))
                    else:
                        # G1 à puissance nulle (laser éteint / M5) : un vrai
                        # déplacement, jamais de la gravure. Affiché comme un
                        # G0 (gris pointillé), pour ne jamais se confondre
                        # avec un tracé réellement gravé de la même couleur —
                        # sinon, entre deux motifs séparés par un déplacement
                        # G1 à vide (ex: les carrés d'une matrice de test),
                        # l'écart entre les motifs apparaît à tort dans la
                        # couleur de la gravure, rendant impossible de
                        # distinguer visuellement gravure et non-gravure.
                        g1_travel_x.extend([cx, nx, float('nan')])
                        g1_travel_y.extend([cy, ny, float('nan')])

                cx, cy = nx, ny
            except Exception:
                # Une ligne isolée mal formée ne doit jamais faire échouer tout
                # l'aperçu : on l'ignore et on continue avec les suivantes.
                continue

        # Décision du mode d'affichage.
        #
        # - Gravure Image interne       -> toujours raster
        # - Calque "Gravure Remplie"    -> raster
        # - G-Code importé non identifié -> heuristique raster
        # - SVG en découpe              -> vectoriel
        # - Matrice de test             -> vectoriel
        # - Découpe / Marquage contour  -> vectoriel
        raster_groups = {}
        raster_keys_rendered_as_image = set()

        for key, strokes in raster_strokes_by_key.items():
            label, _color = key
            layer_mode = layer_mode_by_key.get(key)

            if label == RASTER_LABEL:
                # Image générée par l'application.
                is_raster = True

            elif label == "Matrice de test":
                # Une matrice de test doit rester affichée en vectoriel.
                is_raster = False

            elif label == "Découpe SVG (import)":
                # Un SVG de découpe doit rester affiché comme des contours.
                is_raster = False

            elif layer_mode == "Découpe":
                # Contour vectoriel : jamais de reconstruction raster.
                is_raster = False

            elif layer_mode == "Marquage (Contour)":
                # Contour vectoriel : jamais de reconstruction raster.
                is_raster = False

            elif layer_mode == "Gravure Remplie":
                # Remplissage vectoriel par balayage.
                is_raster = True

            elif label == UNKNOWN_LABEL:
                # G-Code importé depuis LaserGRBL ou un autre logiciel.
                # Il n'a généralement aucun marqueur de phase : on utilise
                # l'ancienne heuristique uniquement dans ce cas.
                row_keys = {
                    round((y1 + y2) / 4.0, 4)
                    for (_, y1, _, y2, _) in strokes
                }
                n_rows = len(row_keys)
                avg_segs_per_row = (
                    len(strokes) / n_rows
                    if n_rows
                    else 0
                )

                is_raster = (
                    n_rows >= 2
                    and len(strokes) >= 40
                    and avg_segs_per_row >= 4.0
                )

            else:
                # Par sécurité, tout groupe identifié mais non reconnu
                # reste vectoriel afin d'éviter une fausse image.
                is_raster = False

            if is_raster:
                raster_groups[key] = strokes
                raster_keys_rendered_as_image.add(key)

        legend_rows = (
            f'<div><span style="color:#888888">■</span> G0 Rapide ({len(g0_x)//3} segments)</div>'
            f'<div><span style="color:#ff3355">■</span> Overscan ({len(ov_x)//3} segments)</div>'
        )
        if g1_travel_x:
            legend_rows += f'<div><span style="color:#888888">■</span> Déplacement G1 sans gravure ({len(g1_travel_x)//3} segments)</div>'
        for label, color in seen_order:
            xs, ys = g1_segments[(label, color)]
            n_segs = len(xs) // 3
            if (label, color) in raster_keys_rendered_as_image:
                legend_rows += f'<div><span style="color:{color}">■</span> {label} ({n_segs} segments — rendu en image ci-dessous)</div>'
            else:
                legend_rows += f'<div><span style="color:{color}">■</span> {label} ({n_segs} segments)</div>'

        self.info_text_item = pg.TextItem(
            html=f'<div style="color: #ffffff; background-color: rgba(0,0,0,170); padding: 4px;">{legend_rows}</div>',
            anchor=(0, 0)
        )
        self.plot_widget.addItem(self.info_text_item)

        # Reconstruction raster par calque seulement si cela correspond à une vraie image.
        for key, strokes in raster_groups.items():
            label, color = key
            tint = None if label == RASTER_LABEL else color
            self._plot_raster_reconstruction(strokes, tint_color=tint)

        hide_rapid_moves = getattr(self, "chk_hide_rapid_moves", None)
        hide_rapid = bool(
            hide_rapid_moves and hide_rapid_moves.isChecked()
        )

        if g0_x and not hide_rapid:
            self.plot_widget.plot(
                g0_x,
                g0_y,
                pen=pg.mkPen(
                    color="#555555",
                    width=1,
                    style=Qt.PenStyle.DotLine
                ),
                connect="finite"
            )

        if g1_travel_x and not hide_rapid:
            # G1 à puissance nulle : un déplacement, pas de la gravure — même
            # style que le G0 rapide pour qu'il soit clair qu'il ne s'agit
            # pas d'un tracé gravé, malgré le G1 (voir le commentaire à
            # l'enregistrement, plus haut dans cette fonction).
            self.plot_widget.plot(
                g1_travel_x,
                g1_travel_y,
                pen=pg.mkPen(
                    color="#555555",
                    width=1,
                    style=Qt.PenStyle.DotLine
                ),
                connect="finite"
            )

        if ov_x:
            self.plot_widget.plot(
                ov_x,
                ov_y,
                pen=pg.mkPen(
                    color="#ff3355",
                    width=2,
                    style=Qt.PenStyle.DashLine
                ),
                connect="finite"
            )

        for (label, color), (xs, ys) in g1_segments.items():
            if (label, color) in raster_keys_rendered_as_image:
                continue
            self.plot_widget.plot(
                xs,
                ys,
                pen=pg.mkPen(color=color, width=1.8),
                connect="finite"
            )

        self.plot_widget.enableAutoRange()
        self.plot_widget.autoRange()