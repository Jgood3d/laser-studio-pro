"""Onglet « Visualisation 2D G-Code » : dessin de l'aperçu du G-Code (modèle :
gcode/preview.py), position de la tête et traits déjà gravés pendant un job."""

import pyqtgraph as pg
from PyQt6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QPainterPath, QPolygonF
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGraphicsPathItem, QGroupBox, QHBoxLayout, QLabel, QSplitter, QToolBar,
    QVBoxLayout, QWidget,
)
import numpy as np

from laser_studio.gcode.preview import (
    DEFAULT_PREVIEW_MATERIAL, KIND_LAYER, KIND_MATRIX, KIND_RASTER, KIND_SVG_CUT, KIND_UNKNOWN, PREVIEW_MATERIALS,
    PREVIEW_MATERIAL_ORDER, BurnTracker, cut_contours, is_cut_group, is_raster_group,
    material_background_rect, parse_preview_cached, raster_image,
)
from laser_studio.i18n import tr
from laser_studio.ui.app.theme import theme_color
from laser_studio.ui.tabs.preview_2d.job_stats_panel import JobStatsPanel
from laser_studio.ui.utils import palette_icon, zoom_shortcuts
from laser_studio.core.preferences import app_preferences

# Écart entre la poignée du séparateur et les cadres de la colonne de droite.
SIDE_PANEL_LEFT_MARGIN = 6
BURN_COLOR = "#ff1a1a"     # traits déjà gravés pendant un job
# Simulation (bouton « Simuler ») : le parcours rejoué en SIMULATION_SECONDS, une image toutes les
# SIMULATION_TICK_MS, quelle que soit la taille du job.
SIMULATION_SECONDS = 15
SIMULATION_TICK_MS = 30
RAPID_PEN_COLOR = "#555555"


class Preview2DTab(QWidget):
    """Aperçu 2D du G-Code, avec ses options dans une barre flottante en
    haut du graphique (options_toolbar). À sa
    droite, de l'autre côté d'un séparateur réglable, une colonne étroite :
    la position du job sur le plateau, puis les statistiques du job
    (job_stats_panel).

    show_gcode() dessine le G-Code (lu par gcode.preview.parse_preview) ;
    set_head_position() place la tête du laser ; pendant un job, les traits
    déjà gravés passent en rouge (set_lines_acked, update_burn, finish_burn).
    Les options et les clics émettent des signaux :

        tab = Preview2DTab(job_position_box)
        tab.show_gcode(gcode, layer_colors={"Découpe": "#ff3b30"})
        tab.display_options_changed.connect(self.redraw_preview)
        tab.plot_clicked.connect(job.apply_matrix_cell)

    Les cases restent lisibles directement (flip_check, negative_check,
    hide_rapid_check, optimize_path_check). « Optimiser le chemin », dans
    son propre cadre « Génération », est lié au modèle JobPlacement par la
    fenêtre et s'applique à la prochaine génération, pas à l'aperçu affiché.

    `job_position_box` : cadre « Position du job sur le plateau »
    (JobPositionBox), construit avec l'onglet image, placé en haut de la
    colonne de droite.
    """

    # Une option d'affichage a changé (inverser, négatif, déplacements
    # rapides) : l'aperçu est à redessiner.
    display_options_changed = pyqtSignal()
    # Clic sur l'aperçu, en mm dans le repère du lit.
    plot_clicked = pyqtSignal(float, float)
    # Message pour la console (partie de l'aperçu impossible à dessiner).
    log = pyqtSignal(str)

    def __init__(self, job_position_box, parent=None):
        super().__init__(parent)
        self.job_position_box = job_position_box
        # Suivi de la gravure du G-Code affiché, et son tracé rouge.
        self.burn = BurnTracker()
        self.burn_overlay = None
        # Plateau de la machine (largeur, profondeur en mm), dessiné sous le job (set_bed) ; la vue est cadrée
        # dessus tant qu'aucun G-Code n'est affiché.
        self._bed = None
        self._bed_item = None
        self._showing_gcode = False
        self.job_stats_panel = JobStatsPanel()
        self._create_options()
        self.side_panel = self._side_panel()
        # Comme « Graver une image » et l'éditeur vectoriel : le graphique, une barre verticale (loupes) contre
        # la colonne de droite (options d'affichage, position du job, statistiques).
        self.zoom_in_action = self._zoom_action("zoom-in", "ui.zoom_in_tip", self.zoom_in)
        self.zoom_out_action = self._zoom_action("zoom-out", "ui.zoom_out_tip", self.zoom_out)
        zoom_shortcuts(self, self.zoom_in, self.zoom_out)
        self.options_toolbar = QToolBar()
        self.options_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.options_toolbar.setIconSize(QSize(20, 20))
        self.options_toolbar.addAction(self.zoom_in_action)
        self.options_toolbar.addAction(self.zoom_out_action)
        # Simulation : rejoue le parcours du laser (traits gravés dans l'ordre du G-Code) avant de lancer.
        play_icon = palette_icon("media-playback-start", self.palette())
        self.simulate_action = QAction(play_icon, tr("preview.simulate_tip"), self)
        self.simulate_action.setCheckable(True)
        self.simulate_action.toggled.connect(self._simulate)
        self.options_toolbar.addSeparator()
        self.options_toolbar.addAction(self.simulate_action)
        self._simulation_step = 1
        self._simulation_timer = QTimer(self)
        self._simulation_timer.setInterval(SIMULATION_TICK_MS)
        self._simulation_timer.timeout.connect(self._simulation_tick)
        plot_area = QWidget()
        row = QHBoxLayout(plot_area)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._plot(), 1)
        row.addWidget(self.options_toolbar)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(plot_area)
        self.splitter.addWidget(self.side_panel)
        # Colonne de droite aussi étroite que possible : Qt la ramène à sa
        # largeur minimale. Elle garde sa largeur quand la fenêtre change de
        # taille ; le séparateur reste réglable.
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([100000, 1])
        layout = QVBoxLayout(self)
        layout.addWidget(self.splitter)

    # -- zoom

    # Facteur d'un clic sur les loupes (ou Ctrl++ / Ctrl+-), comme dans les autres vues.
    BUTTON_ZOOM_STEP = 1.25

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:      # thème changé à la volée
            self.plot_widget.setBackground(theme_color("canvas", "#111111"))
            self._label_axes()
        super().changeEvent(event)

    def _label_axes(self):
        """Titres des axes, dans la couleur des graduations du thème (blancs sur les thèmes sans réglage)."""
        color = theme_color("canvas_label", "#ffffff").name()
        self.plot_widget.setLabel("bottom", tr("ui.plot_x"), color=color)
        self.plot_widget.setLabel("left", tr("ui.plot_y"), color=color)

    def zoom_in(self):
        self._zoom(1.0 / self.BUTTON_ZOOM_STEP)

    def zoom_out(self):
        self._zoom(self.BUTTON_ZOOM_STEP)

    def _zoom(self, scale):
        """Zoom autour du milieu du graphique (`scale` < 1 : plus près)."""
        self.plot_widget.getViewBox().scaleBy((scale, scale))

    def _zoom_action(self, icon, tip_key, slot):
        action = QAction(palette_icon(icon, self.palette()), tr(tip_key), self)
        action.setToolTip(tr(tip_key))
        action.triggered.connect(slot)
        return action

    # -- construction

    def _side_panel(self):
        """Options d'affichage, position du job sur le plateau, génération, puis statistiques du job."""
        panel = QWidget()
        panel.setProperty("role", "sidebar")              # panneau latéral (thèmes modernes)
        display = QGroupBox(tr("preview.display_box"))
        form = QFormLayout(display)
        form.addRow(self.material_label, self.material_combo)
        for check in (self.flip_check, self.negative_check, self.hide_rapid_check):
            form.addRow(check)
        # « Optimiser le chemin » change le G-Code généré, pas l'affichage : cadre à part.
        generation = QGroupBox(tr("preview.generation_box"))
        QFormLayout(generation).addRow(self.optimize_path_check)
        layout = QVBoxLayout(panel)
        # Marge à gauche : les cadres ne touchent pas la poignée du séparateur.
        layout.setContentsMargins(SIDE_PANEL_LEFT_MARGIN, 0, 0, 0)
        layout.addWidget(display)
        layout.addWidget(self.job_position_box)
        layout.addWidget(generation)
        layout.addWidget(self.job_stats_panel)
        layout.addStretch()
        return panel

    def _create_options(self):
        """Options de l'aperçu, affichées dans le cadre « Affichage » de la colonne de droite."""
        self.material_label = QLabel(tr("preview.material_label"))
        self.material_combo = QComboBox()
        self.material_combo.setToolTip(tr("preview.material_tip"))
        for key in PREVIEW_MATERIAL_ORDER:
            self.material_combo.addItem(tr(f"preview.material.{key}"), key)
        # Dernier choix mémorisé (sinon fond clair, comme avant).
        saved = app_preferences().get("preview_material", DEFAULT_PREVIEW_MATERIAL)
        idx = self.material_combo.findData(saved)
        self.material_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.material_combo.currentIndexChanged.connect(self._on_material_changed)

        self.flip_check = self._option(
            "preview.flip", "preview.flip_tip", checked=False
        )
        # Décochée : aperçu réaliste (brûlure de la matière choisie sur les zones gravées).
        # Cochée, elle inverse zones gravées et non gravées : une gravure de texte en réserve
        # semblait alors inversée.
        self.negative_check = self._option(
            "preview.negative", "preview.negative_tip", checked=False
        )
        self.hide_rapid_check = self._option(
            "preview.hide_rapid", "preview.hide_rapid_tip"
        )
        for check in (
            self.flip_check,
            self.negative_check,
            self.hide_rapid_check,
        ):
            check.stateChanged.connect(self.display_options_changed)
        self.optimize_path_check = self._option(
            "ui.optimize_path", "ui.optimize_path_tip"
        )

    def _on_material_changed(self, *_args):
        """Mémorise le preset et redessine l'aperçu."""
        key = self.material_combo.currentData() or DEFAULT_PREVIEW_MATERIAL
        app_preferences().set("preview_material", key)
        self.display_options_changed.emit()

    @staticmethod
    def _option(key, tip_key, checked=True):
        check = QCheckBox(tr(key))
        check.setToolTip(tr(tip_key))
        check.setChecked(checked)
        return check

    def _plot(self):
        """Zone de dessin, avec le point rouge de la tête et le texte
        affiché tant qu'aucun G-Code n'est généré."""
        self.plot_widget = pg.PlotWidget(title=tr("ui.plot_title"))
        self.plot_widget.setBackground(theme_color("canvas", "#111111"))
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._label_axes()
        self.plot_widget.scene().sigMouseClicked.connect(self._on_clicked)

        self.position_marker = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#ff2d55"),
            symbol="o",
        )
        self.position_marker.setZValue(1000)
        self.plot_widget.addItem(self.position_marker)

        # Remplacé par la légende au premier aperçu dessiné.
        self.info_text_item = pg.TextItem(
            html=(
                '<div style="color: #cccccc;">'
                f'{tr("ui.plot_empty_state")}</div>'
            ),
            anchor=(0, 0),
        )
        self.plot_widget.addItem(self.info_text_item)
        return self.plot_widget

    def set_bed(self, width, height):
        """Plateau de la machine (mm) : contour en pointillés, et vue cadrée dessus tant qu'aucun G-Code n'est
        affiché (sinon des axes de -1 à 1 sans repère)."""
        self._bed = (width, height)
        self._draw_bed()
        if not self._showing_gcode:
            self.plot_widget.setRange(QRectF(0.0, 0.0, width, height), padding=0.05)

    def _draw_bed(self):
        """(Re)dessine le contour du plateau, sans qu'il compte dans le cadrage automatique sur le job."""
        if self._bed_item is not None:
            self.plot_widget.removeItem(self._bed_item)
            self._bed_item = None
        if self._bed is None:
            return
        width, height = self._bed
        pen = pg.mkPen(color=theme_color("canvas_edge", "#555555"), width=1, style=Qt.PenStyle.DashLine)
        self._bed_item = pg.PlotDataItem([0, width, width, 0, 0], [0, 0, height, height, 0], pen=pen)
        self._bed_item.setZValue(-10)
        self.plot_widget.addItem(self._bed_item, ignoreBounds=True)

    # -- événements

    def _on_clicked(self, event):
        """Convertit la position du clic en mm, dans le repère du lit."""
        view_box = self.plot_widget.getPlotItem().vb
        pos = view_box.mapSceneToView(event.scenePos())
        self.plot_clicked.emit(pos.x(), pos.y())

    # -- options d'affichage

    def material_preset(self):
        """Preset matière choisi (fond + couleur de brûlure), « light » si
        inconnu."""
        key = self.material_combo.currentData() or DEFAULT_PREVIEW_MATERIAL
        return PREVIEW_MATERIALS.get(key) or PREVIEW_MATERIALS[DEFAULT_PREVIEW_MATERIAL]

    def _negative(self):
        return self.negative_check.isChecked()

    # -- position de la tête

    def set_head_position(self, x, y):
        """Place le point rouge de la tête (position renvoyée par GRBL, MPos
        ou WPos selon $10, sans compensation d'un décalage G92/G54 : repère
        visuel de suivi, pas une mesure de précision). Ignorée pendant une simulation, qui déplace le point."""
        if self._simulation_timer.isActive():
            return
        self.position_marker.setData([x], [y])

    def clear_head_position(self):
        """Plus de position connue (graveur déconnecté) : le point disparaît."""
        self.position_marker.setData([], [])

    # -- suivi de la gravure en direct

    def _simulate(self, running):
        """Bouton « Simuler » : rejoue les traits gravés dans l'ordre du G-Code, en SIMULATION_SECONDS, sur
        le tracé rouge du suivi de gravure, la tête suivant le trait en cours. Décoché : arrêt."""
        if not running:
            self._simulation_timer.stop()
            return
        count = len(self.burn.segments)
        if self.burn_overlay is None or not count:
            self.simulate_action.setChecked(False)
            return
        self.burn.reset()
        self._simulation_step = max(1, count * SIMULATION_TICK_MS // (SIMULATION_SECONDS * 1000))
        self._simulation_timer.start()

    def _simulation_tick(self):
        burn = self.burn
        burn.done = min(len(burn.segments), burn.done + self._simulation_step)
        x, y = burn.segments[burn.done - 1, 2:4]
        self.position_marker.setData([x], [y])
        self._draw_burn()
        if burn.done >= len(burn.segments):
            self.simulate_action.setChecked(False)

    def stop_simulation(self):
        """Arrête la simulation (nouveau G-Code, gravure réelle qui commence)."""
        self.simulate_action.setChecked(False)

    def reset_burn(self):
        """Nouveau job sur le G-Code affiché : plus rien n'est gravé."""
        self.stop_simulation()
        if self.burn_overlay is None:
            return
        self.burn.reset()
        self.burn_overlay.setData([], [])

    def set_lines_acked(self, acked):
        """Lignes acceptées par GRBL jusqu'ici (GCodeStreamerThread.lines_acked)."""
        self.burn.lines_acked = acked

    def update_burn(self, x, y):
        """Avance le tracé rouge d'après la position de la tête."""
        if self.burn_overlay is not None and self.burn.update(x, y):
            self._draw_burn()

    def finish_burn(self, clean_finish):
        """Fin du job : tout est rouge s'il s'est terminé normalement, sinon le
        tracé montre jusqu'où la gravure est allée."""
        if self.burn_overlay is not None and self.burn.finish(clean_finish):
            self._draw_burn()

    def _draw_burn(self):
        xs, ys = self.burn.points()
        self.burn_overlay.setData(xs, ys, connect="finite")

    # -- dessin de l'aperçu

    def show_gcode(self, gcode_text, layer_colors=None, matrix_engrave=False):
        """Dessine le G-Code. `layer_colors` : couleur de chaque calque, par
        nom ; `matrix_engrave` : une matrice de test est en mode gravure
        (affichée en image, sinon en traits)."""
        self.stop_simulation()
        plot = self.plot_widget
        plot.clear()
        self._bed_item = None                          # retiré par clear() : redessiné ci-dessous
        self._showing_gcode = True
        self._draw_bed()
        preview = parse_preview_cached(gcode_text, layer_colors)
        raster_keys = {g.key for g in preview.groups if is_raster_group(g, matrix_engrave)}
        raster_groups = [g for g in preview.groups if g.key in raster_keys]

        self.info_text_item = pg.TextItem(
            html='<div style="color: #ffffff; background-color: rgba(0,0,0,170); padding: 4px;">'
                 f'{self._legend(preview, raster_keys)}</div>',
            anchor=(0, 0),
        )
        plot.addItem(self.info_text_item)
        # plot.clear() a aussi retiré le point de la tête : on le remet, sans
        # qu'il compte dans le cadrage automatique de la vue.
        plot.addItem(self.position_marker, ignoreBounds=True)
        self.burn = BurnTracker(preview.burn_line_idx, preview.burn_segments)
        self.burn_overlay = pg.PlotDataItem(pen=pg.mkPen(color=BURN_COLOR, width=2.2), connect="finite")
        self.burn_overlay.setZValue(900)                # au-dessus des tracés, sous le point de la tête
        plot.addItem(self.burn_overlay, ignoreBounds=True)

        # Fond de matière : à l'intérieur des découpes (la pièce telle qu'elle sortira), les
        # zones non gravées de la gravure restant alors transparentes ; sans découpe, sous tout
        # le job. En négatif, toujours sous tout le job (vue inversée, opaque).
        material_inside_cut = False
        if raster_groups:
            if not self._negative():
                cut_segments = [(g.xs, g.ys) for g in preview.groups if is_cut_group(g)]
                material_inside_cut = self._draw_material_inside_cut(cut_segments)
            if not material_inside_cut:
                self._draw_material_background(raster_groups, preview.groups)

        for group in raster_groups:
            self._draw_raster(group, material_inside_cut)

        hide_rapid = self.hide_rapid_check.isChecked()
        rapid_pen = pg.mkPen(color=RAPID_PEN_COLOR, width=1, style=Qt.PenStyle.DotLine)
        if preview.rapid[0] and not hide_rapid:
            plot.plot(*preview.rapid, pen=rapid_pen, connect="finite")
        if preview.travel[0] and not hide_rapid:
            # G1 à puissance nulle : un déplacement, pas de la gravure — même style que le G0.
            plot.plot(*preview.travel, pen=rapid_pen, connect="finite")
        if preview.overscan[0]:
            # Sur une matrice de test tramée, des centaines de lignes de surbalayage se
            # superposent en barres rouges pleines qui cachent les bords des cases :
            # on les affiche plus fines et translucides pour garder l'image lisible.
            matrix_as_image = any(g.kind == KIND_MATRIX for g in raster_groups)
            ov_pen = (pg.mkPen(color=(255, 51, 85, 80), width=1, style=Qt.PenStyle.DashLine)
                      if matrix_as_image
                      else pg.mkPen(color="#ff3355", width=2, style=Qt.PenStyle.DashLine))
            plot.plot(*preview.overscan, pen=ov_pen, connect="finite")
        for group in preview.groups:
            if group.key not in raster_keys:
                plot.plot(group.xs, group.ys, pen=pg.mkPen(color=group.color, width=1.8), connect="finite")

        plot.enableAutoRange()
        plot.autoRange()

    @staticmethod
    def _group_label(group):
        if group.kind == KIND_RASTER:
            return tr("gen.legend_raster")
        if group.kind == KIND_MATRIX:
            return tr("gen.legend_test_matrix")
        if group.kind == KIND_SVG_CUT:
            return tr("gen.legend_svg_cut")
        if group.kind == KIND_LAYER:
            return tr("gen.legend_layer").format(name=group.name)
        return tr("gen.legend_unknown")

    def _legend(self, preview, raster_keys):
        """Légende : déplacements, surbalayage, traits gravés, puis chaque groupe."""
        rows = (
            f'<div><span style="color:#888888">■</span> {tr("gen.legend_g0").format(n=len(preview.rapid[0]) // 3)}</div>'
            f'<div><span style="color:#ff3355">■</span> {tr("gen.legend_overscan").format(n=len(preview.overscan[0]) // 3)}</div>'
            f'<div><span style="color:{BURN_COLOR}">■</span> {tr("gen.legend_burned")}</div>'
        )
        if preview.travel[0]:
            rows += (f'<div><span style="color:#888888">■</span> '
                     f'{tr("gen.legend_g1_travel").format(n=len(preview.travel[0]) // 3)}</div>')
        # Pastille des images = couleurs du preset matière (fond + brûlure).
        preset = self.material_preset()
        mat_hex = "#%02x%02x%02x" % tuple(preset["material_rgb"])
        burn_hex = "#%02x%02x%02x" % tuple(preset["burn_rgb"])
        raster_swatch = f'<span style="color:{burn_hex}; background-color:{mat_hex}">■</span>'
        for group in preview.groups:
            label = self._group_label(group)
            n_segs = len(group.xs) // 3
            if group.key in raster_keys:
                swatch = (raster_swatch if group.kind in (KIND_RASTER, KIND_MATRIX, KIND_UNKNOWN)
                          else f'<span style="color:{group.color}">■</span>')
                rows += f'<div>{swatch} {tr("gen.legend_layer_raster_note").format(label=label, n=n_segs)}</div>'
            else:
                rows += (f'<div><span style="color:{group.color}">■</span> '
                         f'{tr("gen.legend_layer_segments").format(label=label, n=n_segs)}</div>')
        return rows

    def _draw_material_inside_cut(self, cut_segments):
        """Matière à l'intérieur des découpes seulement (les trous restent
        vides), comme la pièce qui sortira de la machine. False s'il n'y a
        aucun contour de découpe fermé."""
        contours = cut_contours(cut_segments)
        if not contours:
            return False
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)       # contour plein, trous vides
        for chain in contours:
            path.addPolygon(QPolygonF([QPointF(x, y) for x, y in chain]))
            path.closeSubpath()
        item = QGraphicsPathItem(path)
        item.setBrush(QColor(*self.material_preset()["material_rgb"]))
        item.setPen(pg.mkPen(None))
        item.setZValue(-60)                             # sous la gravure (-50)
        self.plot_widget.addItem(item)
        return True

    def _draw_material_background(self, raster_groups, groups):
        """Fond de la couleur de la matière sous tout le job, plus une marge.
        En négatif, la couleur des zones non gravées (celle de la brûlure)."""
        rect = material_background_rect([g.strokes for g in raster_groups], [(g.xs, g.ys) for g in groups])
        if rect is None:
            return
        preset = self.material_preset()
        rgb = preset["burn_rgb"] if self._negative() else preset["material_rgb"]
        background = pg.ImageItem(np.array([[rgb]], dtype=np.uint8))
        background.setLevels([0, 255])
        background.setRect(QRectF(*rect))
        background.setZValue(-60)                       # sous la gravure (-50)
        self.plot_widget.addItem(background)

    def _draw_raster(self, group, transparent_unburned):
        """Image reconstituée de la gravure d'un groupe, sous les tracés."""
        try:
            preset = self.material_preset()
            # Image, matrice de test et G-Code importé sans repère : couleur de brûlure de la
            # matière ; un calque : teinté de sa couleur.
            if group.kind in (KIND_RASTER, KIND_MATRIX, KIND_UNKNOWN):
                burn_rgb = preset["burn_rgb"]
            else:
                burn_rgb = pg.mkColor(group.color).getRgb()[:3]
            # Matrice de test : faibles puissances relevées pour que chaque case reste visible.
            gamma = 0.5 if group.kind == KIND_MATRIX else 1.0
            result = raster_image(group.strokes, preset["material_rgb"], burn_rgb, gamma=gamma,
                                  negative=self._negative(), transparent_unburned=transparent_unburned,
                                  flip=self.flip_check.isChecked())
            if result is None:
                return
            pixels, rect = result
            image_item = pg.ImageItem(pixels)
            # Rendus déjà à l'échelle 0-255 : pas d'étirement automatique du contraste.
            image_item.setLevels([0, 255])
            image_item.setRect(QRectF(*rect))
            image_item.setZValue(-50)
            # Vue d'ensemble : pyqtgraph moyenne les pixels au lieu d'en prendre un sur N
            # (sinon un tramage fin devient un bruit gris illisible tant qu'on n'a pas zoomé).
            image_item.setAutoDownsample(True)
            self.plot_widget.addItem(image_item)
        except Exception as e:
            self.log.emit(f"; Aperçu image raster indisponible : {e}")
