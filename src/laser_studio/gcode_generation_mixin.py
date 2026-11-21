"""Affichage du G-Code généré : console, statistiques, barre d'état et aperçu 2D
(tracé, matière, suivi de la gravure en direct). La préparation et la
génération du job sont dans controllers/job.py (JobController)."""
import re
from PyQt6.QtWidgets import QGraphicsPathItem, QMessageBox
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainterPath, QPolygonF
import pyqtgraph as pg
import numpy as np
from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL, MODE_MARK, normalize_mode
from laser_studio.gcode import MATRIX_ENGRAVE
from laser_studio.i18n import tr

BURN_COLOR = "#ff1a1a"     # traits déjà gravés pendant un job (aperçu 2D)

# Presets d'aperçu 2D : fond matière + couleur de la zone gravée.
# lightens=False : plus de puissance = plus sombre (bois, papier).
# lightens=True  : plus de puissance = plus clair (ardoise, acrylique noir).
PREVIEW_MATERIALS = {
    "light": {
        "material_rgb": (225, 225, 225),
        "burn_rgb": (25, 25, 25),
        "lightens": False,
    },
    "wood": {
        "material_rgb": (194, 155, 105),
        "burn_rgb": (55, 35, 20),
        "lightens": False,
    },
    "bamboo": {
        "material_rgb": (210, 180, 130),
        "burn_rgb": (70, 45, 25),
        "lightens": False,
    },
    "slate": {
        "material_rgb": (40, 40, 45),
        "burn_rgb": (230, 220, 200),
        "lightens": True,
    },
    "acrylic_black": {
        "material_rgb": (25, 25, 28),
        "burn_rgb": (245, 245, 245),
        "lightens": True,
    },
}
# Rétrocompat : fond clair par défaut (comme avant).
PREVIEW_MATERIAL_RGB = PREVIEW_MATERIALS["light"]["material_rgb"]
PREVIEW_MATERIAL_ORDER = ("light", "wood", "bamboo", "slate", "acrylic_black")


class GcodeGenerationMixin:
    def _preview_material_preset(self):
        """Preset matière de l'aperçu 2D (fond + couleur de brûlure).

        Lu depuis le combo de l'onglet Visualisation 2D ; repli sur « light »
        si absent ou clé inconnue.
        """
        key = "light"
        combo = getattr(self, "combo_preview_material", None)
        if combo is not None:
            data = combo.currentData()
            if data:
                key = data
        return PREVIEW_MATERIALS.get(key) or PREVIEW_MATERIALS["light"]

    # Marge du fond de matière autour du job, en mm.
    MATERIAL_BACKGROUND_MARGIN_MM = 3.0

    @staticmethod
    def _cut_contours(segment_lists):
        """Contours fermés des découpes, à partir de leurs segments G1
        (listes x / y, un NaN entre deux segments) : les segments qui se
        suivent sont chaînés bout à bout. Un contour répété (découpe en
        plusieurs passes) n'est gardé qu'une fois."""
        contours, seen = [], set()
        for xs, ys in segment_lists:
            chain = []
            for i in range(0, len(xs) - 1, 3):          # (départ, arrivée, NaN)
                start, end = (xs[i], ys[i]), (xs[i + 1], ys[i + 1])
                if chain and abs(chain[-1][0] - start[0]) < 1e-3 and abs(chain[-1][1] - start[1]) < 1e-3:
                    chain.append(end)
                else:
                    if len(chain) > 2:
                        contours.append(chain)
                    chain = [start, end]
            if len(chain) > 2:
                contours.append(chain)
        result = []
        for chain in contours:
            closed = abs(chain[0][0] - chain[-1][0]) < 0.05 and abs(chain[0][1] - chain[-1][1]) < 0.05
            key = (round(min(x for x, _ in chain), 2), round(min(y for _, y in chain), 2),
                   round(max(x for x, _ in chain), 2), round(max(y for _, y in chain), 2))
            if closed and key not in seen:
                seen.add(key)
                result.append(chain)
        return result

    def _plot_material_inside_cut(self, cut_segments):
        """Matière à l'intérieur des découpes seulement (les trous restent
        vides), comme la pièce qui sortira de la machine. Renvoie False s'il
        n'y a aucun contour de découpe fermé."""
        contours = self._cut_contours(cut_segments)
        if not contours:
            return False
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)       # contour plein, trous vides
        for chain in contours:
            path.addPolygon(QPolygonF([QPointF(x, y) for x, y in chain]))
            path.closeSubpath()
        item = QGraphicsPathItem(path)
        item.setBrush(QColor(*self._preview_material_preset()["material_rgb"]))
        item.setPen(pg.mkPen(None))
        item.setZValue(-60)                             # sous la gravure (-50)
        self.plot_widget.addItem(item)
        return True

    def _plot_material_background(self, raster_groups, vector_segments):
        """Fond de la couleur de la matière sous la gravure, couvrant tout le
        job (segments gravés et tracés vectoriels, découpe comprise) plus une
        marge. En négatif, la couleur des zones non gravées (celle de la
        brûlure). Utilisé sans découpe (voir _plot_material_inside_cut)."""
        xs, ys = [], []
        for strokes in raster_groups:
            for x1, y1, x2, y2, _s in strokes:
                xs += (x1, x2)
                ys += (y1, y2)
        for seg_xs, seg_ys in vector_segments:
            xs += [v for v in seg_xs if v == v]          # NaN : séparateur de tracés
            ys += [v for v in seg_ys if v == v]
        if not xs or not ys:
            return
        margin = self.MATERIAL_BACKGROUND_MARGIN_MM
        left, bottom = min(xs) - margin, min(ys) - margin
        width, height = max(xs) - min(xs) + 2 * margin, max(ys) - min(ys) + 2 * margin
        preset = self._preview_material_preset()
        negative = bool(getattr(self, "chk_negative_raster_preview", None)
                        and self.chk_negative_raster_preview.isChecked())
        rgb = preset["burn_rgb"] if negative else preset["material_rgb"]
        pixel = np.array([[rgb]], dtype=np.uint8)
        background = pg.ImageItem(pixel)
        background.setLevels([0, 255])
        background.setRect(QRectF(left, bottom, width, height))
        background.setZValue(-60)                       # sous la gravure (-50)
        self.plot_widget.addItem(background)

    def _plot_raster_reconstruction(self, raster_strokes, tint_color=None, gamma=1.0,
                                    transparent_unburned=False):
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

        `gamma` < 1 relève les faibles puissances (aperçu seulement, l'ordre des
        niveaux est conservé) : utile pour une matrice de test, où les cases peu
        puissantes seraient sinon presque invisibles.

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

            if gamma != 1.0:
                power_arr = np.power(power_arr, gamma, dtype=np.float32)

            # Preset matière (clair / bois / ardoise…) : le couple
            # fond + couleur de brûlure fixe le sens (assombrit ou éclaircit).
            # La case « négatif » inverse encore les zones gravées / non gravées.
            preset = self._preview_material_preset()
            negative_preview = bool(getattr(self, "chk_negative_raster_preview", None)
                                     and self.chk_negative_raster_preview.isChecked())
            if negative_preview:
                power_arr = 1.0 - power_arr

            material = np.array(preset["material_rgb"], dtype=np.float32)
            if tint_color:
                burn = np.array(pg.mkColor(tint_color).getRgb()[:3], dtype=np.float32)
            else:
                burn = np.array(preset["burn_rgb"], dtype=np.float32)
            blend = power_arr[..., None]
            if transparent_unburned and not negative_preview:
                # La matière est dessinée dessous (à l'intérieur des découpes) : seule la
                # brûlure est peinte, son opacité suivant la puissance.
                rgba = np.empty(power_arr.shape + (4,), dtype=np.float32)
                rgba[..., :3] = burn
                rgba[..., 3] = power_arr * 255.0
                arr = np.clip(rgba, 0, 255).astype(np.uint8)
            else:
                rgb = material + blend * (burn - material)
                arr = np.clip(rgb, 0, 255).astype(np.uint8)
            pg_array = arr.transpose(1, 0, 2)
            if getattr(self, "chk_flip_raster_preview", None) and self.chk_flip_raster_preview.isChecked():
                pg_array = pg_array[:, ::-1]

            image_item = pg.ImageItem(pg_array)

            # Tous les rendus sont maintenant opaques et déjà à l'échelle
            # 0-255 : on fige les niveaux pour éviter tout étirement de
            # contraste automatique de pyqtgraph.
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
            self.log_message(f"; Aperçu image raster indisponible : {e}")

    def on_gcode_generation_started(self):
        """Génération lancée : barre de progression, et l'aperçu 2D est montré
        aussitôt (il se remplit à la fin, voir on_gcode_generated)."""
        self.statusBar().show_progress(0, tr("gen.in_progress"))
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)

    def show_imported_gcode(self, gcode_text, path):
        """Affiche un fichier G-Code importé (JobController.import_gcode) dans
        la console et l'aperçu 2D."""
        self.txt_console.setPlainText(gcode_text)
        num_lines = len([l for l in gcode_text.split('\n') if l.strip()])
        self.tab_vector_2d.job_stats_panel.set_stats(tr("gen.stat_lines").format(n=num_lines),
                                                     tr("gen.stat_power_imported"),
                                                     tr("gen.stat_time_imported"))
        self.plot_gcode_preview(gcode_text)
        # « Fichier > Enregistrer le G-Code » : le G-Code importé peut être réenregistré.
        self.app_actions.set_gcode_export_enabled(True)
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)
        self.log_message(tr("gcode.imported_from").format(path=path))

    def on_gcode_generation_error(self, error_text):
        self.statusBar().hide_progress()
        self.log_message(f"\n; ERREUR DE GÉNÉRATION :\n; {error_text}")
        QMessageBox.critical(self, tr("gen.failed_title"), tr("gen.failed_body").format(error=error_text))

    def on_gcode_generation_progress(self, pct):
        self.statusBar().show_progress(pct, tr("gen.in_progress_pct").format(pct=pct))

    def on_gcode_generated(self, gcode_str, num_lines, avg_power, time_str):
        self.statusBar().show_progress(100, tr("gen.done"))
        self.statusBar().hide_progress(delay_ms=1500)
        self.txt_console.setPlainText(gcode_str)
        self.tab_vector_2d.job_stats_panel.set_stats(tr("gen.stat_lines").format(n=num_lines),
                                                     tr("gen.stat_power").format(value=f"{avg_power:.1f}"),
                                                     tr("gen.stat_time").format(value=time_str))
        # « Fichier > Enregistrer le G-Code » : actif une fois le G-Code généré.
        self.app_actions.set_gcode_export_enabled(True)
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

    # ------------------------------------------------------------------
    # Gravure en temps réel sur l'aperçu 2D : les traits gravés passent en rouge
    # ------------------------------------------------------------------
    BURN_WINDOW = 200          # traits examinés au plus autour de la position de la tête
    BURN_ON_PATH_MM = 0.5      # distance tête / trait en dessous de laquelle la tête est « sur » le trait
    BURN_PLANNER_LEAD = 15     # mouvements que GRBL peut avoir acceptés (« ok ») sans les avoir faits

    def _setup_burn_overlay(self, burn_line_idx, burn_segments):
        """Prépare le calque rouge « déjà gravé » pour le G-Code qui vient d'être dessiné."""
        self._burn_line_idx = np.asarray(burn_line_idx, dtype=np.int64)
        self._burn_segs = np.asarray(burn_segments, dtype=float).reshape(-1, 4)
        n = len(self._burn_segs)
        # Données prêtes à tracer : x1, x2, NaN pour chaque trait (même format que l'aperçu).
        self._burn_xs = np.column_stack([self._burn_segs[:, 0], self._burn_segs[:, 2], np.full(n, np.nan)]).ravel()
        self._burn_ys = np.column_stack([self._burn_segs[:, 1], self._burn_segs[:, 3], np.full(n, np.nan)]).ravel()
        self._burn_done = 0
        self._stream_acked = 0
        self.burn_overlay = pg.PlotDataItem(pen=pg.mkPen(color=BURN_COLOR, width=2.2), connect="finite")
        self.burn_overlay.setZValue(900)               # au-dessus des tracés, sous le point rouge
        self.plot_widget.addItem(self.burn_overlay, ignoreBounds=True)

    def reset_burn_overlay(self):
        """Nouveau job sur le même G-Code : plus rien n'est gravé."""
        if getattr(self, "burn_overlay", None) is None:
            return
        self._burn_done = 0
        self._stream_acked = 0
        self.burn_overlay.setData([], [])

    def on_lines_acked(self, acked):
        """Reçu de GCodeStreamerThread.lines_acked : lignes acceptées par GRBL jusqu'ici."""
        self._stream_acked = acked

    def update_burn_overlay(self, x, y):
        """Avance le calque rouge d'après la position de la tête (rapport d'état GRBL).

        Les « ok » disent jusqu'à quelle ligne GRBL a pu aller : la tête est sur un des traits
        acceptés et pas encore marqués gravés. On prend le plus proche d'elle (le premier en cas
        d'égalité, pour les passes superposées) : les traits précédents sont gravés, et celui-ci
        l'est jusqu'à la tête. Si la tête n'est sur aucun trait (déplacement à vide, surbalayage,
        position décalée par G92), on avance au moins jusqu'aux traits que GRBL a forcément
        terminés (les « ok » moins les mouvements qu'il peut garder en mémoire)."""
        overlay = getattr(self, "burn_overlay", None)
        segs = getattr(self, "_burn_segs", None)
        if overlay is None or segs is None or not len(segs):
            return
        done = self._burn_done
        accepted = int(np.searchsorted(self._burn_line_idx, self._stream_acked))  # traits acceptés par GRBL
        partial = None
        done = max(done, accepted - self.BURN_PLANNER_LEAD)
        hi = min(accepted, done + self.BURN_WINDOW)
        if hi > done:
            window = segs[done:hi]
            ax, ay, bx, by = window[:, 0], window[:, 1], window[:, 2], window[:, 3]
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            t = np.where(length2 > 0, ((x - ax) * dx + (y - ay) * dy) / np.where(length2 > 0, length2, 1), 0.0)
            t = np.clip(t, 0.0, 1.0)
            px, py = ax + t * dx, ay + t * dy
            dist = np.hypot(x - px, y - py)
            best = float(dist.min())
            if best <= self.BURN_ON_PATH_MM:
                k = int(np.flatnonzero(dist <= best + 0.05)[0])
                done += k
                partial = (ax[k], ay[k], px[k], py[k])
        self._burn_done = done
        self._draw_burn_overlay(partial)

    def finish_burn_overlay(self, clean_finish):
        """Fin du job : tout est gravé si le job s'est terminé normalement, sinon le calque rouge
        reste tel quel (il montre jusqu'où la gravure est allée)."""
        if clean_finish and getattr(self, "_burn_segs", None) is not None:
            self._burn_done = len(self._burn_segs)
            self._draw_burn_overlay(None)

    def _draw_burn_overlay(self, partial):
        n = 3 * self._burn_done
        xs, ys = self._burn_xs[:n], self._burn_ys[:n]
        if partial is not None:
            ax, ay, px, py = partial
            xs = np.concatenate([xs, [ax, px, np.nan]])
            ys = np.concatenate([ys, [ay, py, np.nan]])
        self.burn_overlay.setData(xs, ys, connect="finite")

    def plot_gcode_preview(self, gcode_text):
        self._last_gcode_text = gcode_text
        try:
            self._plot_gcode_preview_impl(gcode_text)
        except Exception as e:
            # Ne jamais laisser l'aperçu 2D silencieusement vide : si le G-Code
            # (notamment un fichier importé d'un autre outil) contient une
            # ligne inattendue qui fait planter l'analyse, on le signale
            # clairement dans la console plutôt que d'afficher un graphique vide.
            self.log_message(f"\n; ERREUR aperçu 2D : {e}")
            QMessageBox.warning(self, tr("gen.preview_error_title"),
                                 tr("gen.preview_error_body").format(error=e))

    def _plot_gcode_preview_impl(self, gcode_text):
        self.plot_widget.clear()

        # Chaque phase (image / découpe SVG) et chaque calque vectoriel est
        # tracé avec sa propre couleur, repérable via les marqueurs de
        # commentaires déjà présents dans le G-Code généré.
        DEFAULT_SVG_COLOR = "#ff00ff"
        DEFAULT_LAYER_COLOR = "#00ff88"
        RASTER_LABEL = tr("gen.legend_raster")
        MATRIX_LABEL = tr("gen.legend_test_matrix")
        UNKNOWN_LABEL = tr("gen.legend_unknown")

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

        # Suivi de la gravure en temps réel : chaque trait gravé est relié au numéro de sa ligne
        # dans l'envoi, numérotée comme GCodeStreamerThread (lignes non vides, hors commentaires).
        burn_line_idx = []
        burn_segments = []
        stream_count = 0

        for line in gcode_text.split('\n'):
            raw_line = line.strip()
            if not raw_line:
                continue
            line_idx = None
            if not line.startswith(';'):
                line_idx = stream_count
                stream_count += 1

            try:
                if raw_line.startswith(';'):
                    if 'PHASE 1' in raw_line and 'GRAVURE IMAGE' in raw_line:
                        current_label, current_color = RASTER_LABEL, "#ffaa00"
                        current_layer_mode = MODE_FILL
                        current_is_test_matrix = False
                    elif 'PHASE 2' in raw_line and 'DÉCOUPE VECTORIELLE SVG' in raw_line:
                        current_label, current_color = tr("gen.legend_svg_cut"), DEFAULT_SVG_COLOR
                        current_layer_mode = MODE_CUT
                        current_is_test_matrix = False
                    elif raw_line.startswith('; --- MATRICE DE TEST LASER'):
                        current_label = tr("gen.legend_test_matrix")
                        current_color = "#00ff88"
                        current_layer_mode = "matrix"
                        current_is_test_matrix = True
                    elif raw_line.startswith('; --- CALQUE'):
                        m = re.match(r"; --- CALQUE '(.+)' \[(.+)\] ---", raw_line)
                        if m:
                            layer_name = m.group(1)
                            # Code du mode ; ancien libellé français dans un G-Code d'avant 2.6.
                            layer_mode = normalize_mode(m.group(2))
                            layer = next((l for l in self.layer_manager.layers if l.name == layer_name), None)
                            current_label = tr("gen.legend_layer").format(name=layer_name)
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
                        if line_idx is not None:
                            burn_line_idx.append(line_idx)
                            burn_segments.append((cx, cy, nx, ny))
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
        # - Calque en gravure remplie   -> raster
        # - G-Code importé non identifié -> heuristique raster
        # - SVG en découpe              -> vectoriel
        # - Matrice de test (Gravure)   -> raster, comme la gravure image
        # - Matrice de test (Découpe)   -> vectoriel
        # - Découpe / Marquage contour  -> vectoriel
        raster_groups = {}
        raster_keys_rendered_as_image = set()

        for key, strokes in raster_strokes_by_key.items():
            label, _color = key
            layer_mode = layer_mode_by_key.get(key)

            if label == RASTER_LABEL:
                # Image générée par l'application.
                is_raster = True

            elif label == MATRIX_LABEL:
                # Matrice de test en mode Gravure : rendu tramé en niveaux de gris, comme
                # une gravure image (chaque case, y compris celles avec une partie d'image,
                # reste lisible). En mode Découpe (ou matrice d'origine inconnue, ex. G-Code
                # rechargé), on garde l'affichage vectoriel.
                matrix_params = self.job.last_test_matrix_params or {}
                is_raster = matrix_params.get("mode") == MATRIX_ENGRAVE

            elif label == tr("gen.legend_svg_cut"):
                # Un SVG de découpe doit rester affiché comme des contours.
                is_raster = False

            elif layer_mode == MODE_CUT:
                # Contour vectoriel : jamais de reconstruction raster.
                is_raster = False

            elif layer_mode == MODE_MARK:
                # Contour vectoriel : jamais de reconstruction raster.
                is_raster = False

            elif layer_mode == MODE_FILL:
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
            f'<div><span style="color:#888888">■</span> {tr("gen.legend_g0").format(n=len(g0_x)//3)}</div>'
            f'<div><span style="color:#ff3355">■</span> {tr("gen.legend_overscan").format(n=len(ov_x)//3)}</div>'
            f'<div><span style="color:{BURN_COLOR}">■</span> {tr("gen.legend_burned")}</div>'
        )
        if g1_travel_x:
            legend_rows += f'<div><span style="color:#888888">■</span> {tr("gen.legend_g1_travel").format(n=len(g1_travel_x)//3)}</div>'
        # Pastille de légende = couleurs du preset matière (fond + brûlure).
        preset = self._preview_material_preset()
        mat_hex = "#%02x%02x%02x" % tuple(preset["material_rgb"])
        burn_hex = "#%02x%02x%02x" % tuple(preset["burn_rgb"])
        raster_swatch = f'<span style="color:{burn_hex}; background-color:{mat_hex}">■</span>'

        for label, color in seen_order:
            xs, ys = g1_segments[(label, color)]
            n_segs = len(xs) // 3
            if (label, color) in raster_keys_rendered_as_image:
                swatch = raster_swatch if label in (RASTER_LABEL, MATRIX_LABEL) else f'<span style="color:{color}">■</span>'
                legend_rows += f'<div>{swatch} {tr("gen.legend_layer_raster_note").format(label=label, n=n_segs)}</div>'
            else:
                legend_rows += f'<div><span style="color:{color}">■</span> {tr("gen.legend_layer_segments").format(label=label, n=n_segs)}</div>'

        self.info_text_item = pg.TextItem(
            html=f'<div style="color: #ffffff; background-color: rgba(0,0,0,170); padding: 4px;">{legend_rows}</div>',
            anchor=(0, 0)
        )
        self.plot_widget.addItem(self.info_text_item)
        # Le clear() ci-dessus a aussi retiré le point rouge de position de la tête (DRO) : on le
        # remet, sans qu'il compte dans le cadrage automatique de la vue (ignoreBounds).
        if hasattr(self, "gcode_position_marker"):
            self.plot_widget.addItem(self.gcode_position_marker, ignoreBounds=True)
        self._setup_burn_overlay(burn_line_idx, burn_segments)

        # Fond de matière : à l'intérieur des découpes (la pièce telle qu'elle sortira), les
        # zones non gravées de la gravure restant alors transparentes ; sans découpe, sous tout
        # le job. En négatif, toujours sous tout le job (vue inversée, opaque).
        negative_preview = bool(getattr(self, "chk_negative_raster_preview", None)
                                and self.chk_negative_raster_preview.isChecked())
        material_inside_cut = False
        if raster_groups:
            cut_segments = [segments for key, segments in g1_segments.items()
                            if layer_mode_by_key.get(key) == MODE_CUT or key[0] == tr("gen.legend_svg_cut")]
            if not negative_preview:
                material_inside_cut = self._plot_material_inside_cut(cut_segments)
            if not material_inside_cut:
                self._plot_material_background(raster_groups.values(), g1_segments.values())

        # Reconstruction raster par calque seulement si cela correspond à une vraie image.
        for key, strokes in raster_groups.items():
            label, color = key
            # Image et matrice de test : jamais teintées (gris sur matériau clair, ou négatif).
            tint = None if label in (RASTER_LABEL, MATRIX_LABEL) else color
            # Matrice de test : les niveaux de puissance sont relevés (gamma 0,5) pour que
            # l'image de chaque case reste visible, y compris celles à faible puissance.
            gamma = 0.5 if label == MATRIX_LABEL else 1.0
            self._plot_raster_reconstruction(strokes, tint_color=tint, gamma=gamma,
                                             transparent_unburned=material_inside_cut)

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
            # Sur une matrice de test tramée, des centaines de lignes de surbalayage se
            # superposent en barres rouges pleines qui cachent les bords des cases :
            # on les affiche plus fines et translucides pour garder l'image lisible.
            matrix_as_image = any(k[0] == MATRIX_LABEL for k in raster_keys_rendered_as_image)
            ov_pen = (
                pg.mkPen(color=(255, 51, 85, 80), width=1, style=Qt.PenStyle.DashLine)
                if matrix_as_image
                else pg.mkPen(color="#ff3355", width=2, style=Qt.PenStyle.DashLine)
            )
            self.plot_widget.plot(
                ov_x,
                ov_y,
                pen=ov_pen,
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
