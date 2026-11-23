"""Canevas de l'éditeur vectoriel (VectorCanvasView) : zone de travail en mm,
objets déplaçables, outils de dessin, mesure, édition des nœuds, annulation."""
import math
import time
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainterPath, QPen, QBrush, QTransform, QPainter, QKeySequence
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsEllipseItem, QFormLayout,
    QLabel, QDoubleSpinBox, QCheckBox, QDialog, QDialogButtonBox, QMessageBox, QMenu,
)
from laser_studio.i18n import tr
from laser_studio.vector.nudge import NUDGE_UNDO_WINDOW_S, nudge_step
from laser_studio.vector.text_on_path import (
    default_center_fraction, is_closed, orient_path, path_length, relative_points, scaled_points,
    side_center_fraction, point_at_fraction, project_fraction,
)
from laser_studio.models.layers import LayersModel, layer_label
from laser_studio.models.vector_document import VectorDocument
from laser_studio.models.vector_objects import ShapeObject, SvgPathObject, TextObject, VectorObject
from laser_studio.vector import path_ops
from laser_studio.ui.vector_editor.item import VectorGraphicsItem

# Ancien nom du modèle des calques (models/layers.py).

# Facteur de zoom d'un cran de molette, et d'un clic sur les loupes (ou Ctrl++ / Ctrl+-).
WHEEL_ZOOM_STEP = 1.15
BUTTON_ZOOM_STEP = 1.25


class VectorCanvasView(QGraphicsView):
    """Vue d'édition : zone de travail en mm, objets déplaçables à la souris,
    coloration selon le calque. Indépendante des vues image (aucun impact
    sur les performances du tramage)."""

    selection_changed = pyqtSignal(object)  # VectorObject ou None
    object_moved = pyqtSignal(object)       # VectorObject déplacé à la souris
    edit_requested = pyqtSignal(object)     # double-clic sur un objet
    insert_text_requested = pyqtSignal(float, float)  # clic droit > Texte (x_mm, y_mm)
    serial_duplicate_requested = pyqtSignal()        # clic droit > Dupliquer en série...
    jig_requested = pyqtSignal()                     # clic droit > Gabarit de placement...
    medal_text_requested = pyqtSignal()              # clic droit > Texte de médaille...

    def __init__(self, layer_manager: LayersModel, parent=None, document=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        # Document (objets, annuler / refaire, presse-papiers) : le canevas en est la vue. Il crée ou retire
        # ses éléments graphiques quand le document le signale (voir _on_object_added…).
        self.document = document if document is not None else VectorDocument(self)
        self._items = {}  # id(objet) -> VectorGraphicsItem
        self.document.object_added.connect(self._on_object_added)
        self.document.object_removed.connect(self._on_object_removed)
        self.document.objects_changed.connect(self._on_objects_changed)
        self.document.objects_reset.connect(self._on_objects_reset)
        self.px_per_mm = 4.0
        self.grid_items = []
        self._camera_item = None        # image de la caméra posée sous la grille (voir set_camera_background)
        self._camera_opacity = 0.7

        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setBackgroundBrush(QColor("#1c1c1c"))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Repère "machine" : origine en bas-gauche, Y croissant vers le haut.
        # (Le flip est calculé objet par objet et pour la grille — voir
        # VectorGraphicsItem.refresh et _draw_grid — plutôt qu'au niveau de la
        # vue : un flip posé sur la QGraphicsView pouvait être silencieusement
        # annulé par fitInView(), ce qui cassait tout l'alignement.)
        self._pan_last_pos = None
        self._group_drag_items = []
        self._group_drag_last_scene_pos = None
        self._group_drag_anchor_item = None
        # Accroche à la grille pendant un déplacement à la souris (voir
        # mouseMoveEvent) : désactivée par défaut, réglable depuis la barre
        # d'outils de l'Éditeur Vectoriel (case + pas en mm).
        self.snap_enabled = False
        self.snap_step_mm = 5.0
        # Outil de dessin à la souris : None = sélection, sinon "line" / "rect" / "ellipse".
        self._draw_tool = None
        self._draw_start_scene = None
        self._draw_preview_item = None
        self._draw_layer_id = None
        # Accroche aux extrémités des tracés existants pendant le dessin
        self.endpoint_snap_enabled = True
        self.endpoint_snap_px = 12.0  # rayon d'accroche en pixels écran
        self._snap_indicator = None  # marqueur visuel du point d'accroche
        # Saisie de dimensions au clavier après le 1er point (ex: "25" ou "30x20")
        self._draw_dim_buffer = ""
        self._draw_last_cursor_scene = None
        # Phases : None → "p1" (2e clic) → "p2" (prêt à tirer) → "depth" (en train de tirer)
        self._draw_phase = None
        self._draw_base_p1 = None
        self._draw_base_p2 = None
        self._draw_awaiting_second = False
        self._draw_awaiting_depth = False
        self._draw_depth_dragging = False
        # Cercle / ellipse d'un seul geste : bouton enfoncé depuis le 1er point (clic-glisser), position du
        # clic à l'écran pour distinguer un simple clic (2 clics) d'un glissé.
        self._draw_pressed = False
        self._draw_press_screen = None
        # Outil mesure : deux clics → distance affichée
        self._measure_p1 = None
        self._measure_preview = None
        self._measure_labels = []  # annotations persistantes jusqu'à nouvel outil
        self._measure_text = None       # texte qui suit le trait pendant qu'on le tire
        self._measure_press_px = None   # position écran du premier appui (pour reconnaître un glissé)
        # Mode édition de nœuds (sommets d'un SvgPathObject)
        self._node_mode = False
        self._node_target_item = None
        self._node_handles = []
        # Poignée qui fait glisser un texte le long du contour qu'il suit (voir _sync_follow_handle).
        self._follow_handle = None
        self._follow_handle_item = None
        self._follow_dragging = False
        self._follow_drag_pushed = False
        self._node_polylines = []  # list[list[QPointF]] en coordonnées locales objet
        self._node_drag_index = None  # (poly_idx, pt_idx) pendant un drag
        self._node_drag_pushed_undo = False
        # Recentrage différé de la vue (voir request_recenter) : attend la
        # fin des redimensionnements (plein écran, changement d'onglet)
        # avant de centrer, sinon la taille du viewport est encore fausse.
        self._recenter_items = None
        self._recenter_pending = False
        self._recenter_timer = QTimer(self)
        self._recenter_timer.setSingleShot(True)
        self._recenter_timer.timeout.connect(self._do_recenter)

        self.work_rect_item = None
        self.set_work_area(100.0, 100.0)

        self.scene_obj.selectionChanged.connect(self._on_selection_changed)

    # -- zone de travail ----------------------------------------------------
    def request_recenter(self, items=None):
        """Demande de centrer la vue sur `items` (liste de VectorGraphicsItem),
        ou à défaut sur la sélection, ou à défaut sur tous les objets. Le
        recentrage est différé et re-planifié à chaque redimensionnement
        (voir resizeEvent) : il s'exécute une fois la fenêtre / l'onglet
        réellement affiché à sa taille définitive."""
        self._recenter_items = list(items) if items else None
        self._recenter_pending = True
        self._recenter_timer.start(120)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._recenter_pending:
            self._recenter_timer.start(120)

    def _do_recenter(self):
        self._recenter_pending = False
        items = self._recenter_items
        self._recenter_items = None
        self.center_on_items(items)

    def center_on_items(self, items=None, margin_px=40, max_scale=10.0):
        """Cadre la vue sur la boîte englobante de `items` (sinon la
        sélection, sinon tous les objets, sinon la zone de travail) : zoom
        ajusté pour que l'ensemble remplisse la fenêtre (avec une marge), et
        centré au milieu. Le zoom est plafonné (`max_scale`) pour qu'un tout
        petit objet ne soit pas agrandi démesurément."""
        rect = QRectF()
        candidates = items if items else (self.selected_items_vector() or [
            i for i in self.scene_obj.items() if isinstance(i, VectorGraphicsItem)
        ])
        for it in candidates:
            try:
                if it.scene() is self.scene_obj:
                    rect = rect.united(it.sceneBoundingRect())
            except RuntimeError:
                pass  # objet supprimé entre-temps
        if rect.isNull() and self.work_rect_item:
            rect = self.work_rect_item.sceneBoundingRect()
        if rect.isNull():
            return

        vp = self.viewport().size()
        if vp.width() <= 2 * margin_px or vp.height() <= 2 * margin_px:
            return  # vue pas encore affichée à sa taille définitive

        # Zoom qui fait tenir l'ensemble dans la fenêtre, marge comprise.
        target = min(
            (vp.width() - 2 * margin_px) / max(rect.width(), 1e-6),
            (vp.height() - 2 * margin_px) / max(rect.height(), 1e-6),
            max_scale,
        )

        # Zone de la scène assez grande pour que la cible puisse être
        # réellement centrée (un QGraphicsView ne défile pas au-delà de sa
        # sceneRect : sans ça, un objet près de l'origine resterait
        # décentré). Recalculée à chaque fois depuis la zone de travail,
        # pour ne pas grossir indéfiniment.
        half_w = vp.width() / 2.0 / target
        half_h = vp.height() / 2.0 / target
        center = rect.center()
        needed = QRectF(center.x() - half_w, center.y() - half_h, 2 * half_w, 2 * half_h)
        base = QRectF()
        if self.work_rect_item:
            base = self.work_rect_item.sceneBoundingRect().adjusted(-50, -50, 50, 50)
        self.scene_obj.setSceneRect(base.united(rect.adjusted(-50, -50, 50, 50)).united(needed))

        self.resetTransform()
        self.scale(target, target)
        self.centerOn(center)

    def set_snap_enabled(self, enabled):
        """Grille magnétique (case de la barre de l'éditeur) : déplacements calés sur la grille."""
        self.snap_enabled = bool(enabled)

    def set_snap_step(self, step_mm):
        """Pas de la grille magnétique, en mm."""
        self.snap_step_mm = float(step_mm)

    def set_work_area(self, w_mm, h_mm):
        self.work_w_mm, self.work_h_mm = w_mm, h_mm
        if self.work_rect_item:
            self.scene_obj.removeItem(self.work_rect_item)
        for item in self.grid_items:
            self.scene_obj.removeItem(item)
        self.grid_items = []

        s = self.px_per_mm
        rect = QRectF(0, 0, w_mm * s, h_mm * s)
        self.work_rect_item = QGraphicsRectItem(rect)
        pen = QPen(QColor("#666666"), 1)
        pen.setCosmetic(True)
        self.work_rect_item.setPen(pen)
        self.work_rect_item.setZValue(-100)
        self.scene_obj.addItem(self.work_rect_item)

        self._draw_grid(w_mm, h_mm)

        self.scene_obj.setSceneRect(rect.adjusted(-50, -50, 50, 50))
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_grid(self, w_mm, h_mm):
        """Grille en mm avec repères chiffrés le long des bords bas et gauche,
        pour se repérer facilement (origine = coin bas-gauche = 0,0). Les
        coordonnées écran sont calculées directement en Y inversé (bas-gauche
        -> Y-descendant Qt) : aucun flip de vue n'est utilisé (voir __init__),
        donc pas besoin de contre-flip sur les étiquettes non plus.
        """
        s = self.px_per_mm
        work_h_px = h_mm * s
        span = max(w_mm, h_mm)
        # Paliers plus fins qu'avant (l'ancien "50mm partout au-delà de 200mm"
        # était trop grossier pour se repérer précisément sur une zone de
        # travail courante de 200-400mm).
        if span <= 50:
            step = 5
        elif span <= 150:
            step = 10
        elif span <= 400:
            step = 20
        elif span <= 1000:
            step = 50
        else:
            step = 100
        minor_step = step / 4.0

        minor_pen = QPen(QColor("#262626"), 0)
        minor_pen.setCosmetic(True)

        grid_pen = QPen(QColor("#333333"), 0)
        grid_pen.setCosmetic(True)

        # Lignes mineures (sans étiquette) pour un repérage plus précis entre
        # deux graduations principales.
        xm = minor_step
        while xm < w_mm - 1e-6:
            line = self.scene_obj.addLine(xm * s, 0, xm * s, work_h_px, minor_pen)
            line.setZValue(-95)
            self.grid_items.append(line)
            xm += minor_step
        ym = minor_step
        while ym < h_mm - 1e-6:
            screen_y = work_h_px - ym * s
            line = self.scene_obj.addLine(0, screen_y, w_mm * s, screen_y, minor_pen)
            line.setZValue(-95)
            self.grid_items.append(line)
            ym += minor_step

        x = 0.0
        while x <= w_mm + 1e-6:
            line = self.scene_obj.addLine(x * s, 0, x * s, work_h_px, grid_pen)
            line.setZValue(-90)
            self.grid_items.append(line)
            label = self.scene_obj.addSimpleText(f"{x:g}")
            label.setBrush(QColor("#999999"))
            label.setPos(x * s + 2, work_h_px - 16)
            label.setZValue(-80)
            self.grid_items.append(label)
            x += step

        y = 0.0
        while y <= h_mm + 1e-6:
            screen_y = work_h_px - y * s
            line = self.scene_obj.addLine(0, screen_y, w_mm * s, screen_y, grid_pen)
            line.setZValue(-90)
            self.grid_items.append(line)
            label = self.scene_obj.addSimpleText(f"{y:g}")
            label.setBrush(QColor("#999999"))
            label.setPos(2, screen_y - 16)
            label.setZValue(-80)
            self.grid_items.append(label)
            y += step

        origin_label = self.scene_obj.addSimpleText("0,0 (origine)")
        origin_label.setBrush(QColor("#ff8844"))
        origin_label.setPos(2, work_h_px - 32)
        origin_label.setZValue(-80)
        self.grid_items.append(origin_label)

    def wheelEvent(self, event):
        factor = WHEEL_ZOOM_STEP if event.angleDelta().y() > 0 else 1 / WHEEL_ZOOM_STEP
        self.scale(factor, factor)

    def zoom_in(self):
        """Zoom avant (bouton loupe +, Ctrl++), centré sur le milieu de la vue."""
        self._zoom_centered(BUTTON_ZOOM_STEP)

    def zoom_out(self):
        """Zoom arrière (bouton loupe -, Ctrl+-), centré sur le milieu de la vue."""
        self._zoom_centered(1 / BUTTON_ZOOM_STEP)

    def _zoom_centered(self, factor):
        center = self.mapToScene(self.viewport().rect().center())
        anchor = self.transformationAnchor()
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.scale(factor, factor)
        self.centerOn(center)
        self.setTransformationAnchor(anchor)

    def scene_to_mm(self, scene_pos):
        """Point scène Qt (Y bas) -> millimètres machine (origine bas-gauche, Y haut)."""
        s = self.px_per_mm
        work_h_px = self.work_h_mm * s
        return scene_pos.x() / s, (work_h_px - scene_pos.y()) / s

    def mm_to_scene(self, x_mm, y_mm):
        """Millimètres machine (Y haut) -> point scène Qt (Y bas)."""
        s = self.px_per_mm
        work_h_px = self.work_h_mm * s
        return QPointF(x_mm * s, work_h_px - y_mm * s)

    # -- image de la caméra en fond du plateau ------------------------------------------------------------
    def set_camera_background(self, image_bgr, bed_w_mm, bed_h_mm):
        """Pose l'image de la caméra (déjà redressée sur le plateau : haut de l'image = Y max) sous la grille et
        sous les objets, à l'échelle du plateau, pour placer ce qu'on grave sur la vraie matière."""
        import cv2
        import numpy as np
        from PyQt6.QtGui import QImage, QPixmap
        from PyQt6.QtWidgets import QGraphicsPixmapItem

        self.clear_camera_background()
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return
        code = cv2.COLOR_GRAY2RGB if image_bgr.ndim == 2 else cv2.COLOR_BGR2RGB
        rgb = np.ascontiguousarray(cv2.cvtColor(image_bgr, code))
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        item = QGraphicsPixmapItem(QPixmap.fromImage(qimg))
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        s = self.px_per_mm
        item.setTransform(QTransform.fromScale(bed_w_mm * s / w, bed_h_mm * s / h))
        item.setPos(self.mm_to_scene(0.0, bed_h_mm))        # coin haut-gauche du plateau
        item.setZValue(-97)                                  # au-dessus du fond (-100), sous la grille (-95)
        item.setOpacity(self._camera_opacity)
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)  # ne gêne ni la sélection ni les outils
        self.scene_obj.addItem(item)
        self._camera_item = item

    def clear_camera_background(self):
        item = self._camera_item
        self._camera_item = None
        if item is not None:
            try:
                self.scene_obj.removeItem(item)
            except RuntimeError:
                pass

    def set_camera_background_opacity(self, value):
        """Opacité de l'image de la caméra, de 0,05 à 1."""
        self._camera_opacity = max(0.05, min(1.0, float(value)))
        if self._camera_item is not None:
            try:
                self._camera_item.setOpacity(self._camera_opacity)
            except RuntimeError:
                self._camera_item = None

    def set_draw_tool(self, tool, layer_id=None):
        """Active un outil : None/'select', 'line', 'rect', 'circle', 'ellipse', 'measure'.

        rect : 3 points (base en 2 clics, puis profondeur) ; circle : du centre vers le rayon ; ellipse :
        d'un coin du cadre à l'autre. Cercle et ellipse se tracent d'un seul geste (clic-glisser) ou en
        2 clics."""
        self._cancel_draw_preview()
        self._clear_measure_temp()
        if tool in (None, "", "select"):
            self._draw_tool = None
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self._draw_tool = tool
            self._draw_layer_id = layer_id
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.scene_obj.clearSelection()
            self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _cancel_draw_preview(self):
        if self._draw_preview_item is not None:
            try:
                self.scene_obj.removeItem(self._draw_preview_item)
            except RuntimeError:
                pass
            self._draw_preview_item = None
        self._hide_snap_indicator()
        self._draw_start_scene = None
        self._draw_dim_buffer = ""
        self._draw_last_cursor_scene = None
        self._draw_base_p1 = None
        self._draw_base_p2 = None
        self._draw_phase = None
        self._draw_awaiting_second = False
        self._draw_awaiting_depth = False
        self._draw_depth_dragging = False
        self._draw_pressed = False
        self._draw_press_screen = None

    def _clear_measure_temp(self):
        self._measure_p1 = None
        self._measure_press_px = None
        for attr in ("_measure_preview", "_measure_text"):
            item = getattr(self, attr)
            if item is not None:
                try:
                    self.scene_obj.removeItem(item)
                except RuntimeError:
                    pass
                setattr(self, attr, None)

    def clear_measure_labels(self):
        for it in self._measure_labels:
            try:
                self.scene_obj.removeItem(it)
            except RuntimeError:
                pass
        self._measure_labels = []

    def _default_draw_layer_id(self):
        if self._draw_layer_id:
            return self._draw_layer_id
        layer = self.layer_manager.default_svg_layer()
        return layer.id if layer else (self.layer_manager.layers[0].id if self.layer_manager.layers else None)

    def _preview_pen(self):
        layer = self.layer_manager.get(self._default_draw_layer_id())
        color = QColor(layer.color) if layer else QColor("#00aaff")
        pen = QPen(color, 1.5, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        return pen

    # -- Accroche aux extrémités (dessin) ------------------------------------

    def _collect_endpoint_scene_points(self):
        """Extrémités (et coins) de tous les objets vectoriels, en coords scène."""
        pts = []
        for item in self.scene_obj.items():
            if not isinstance(item, VectorGraphicsItem):
                continue
            # Pendant le dessin, l'aperçu n'est pas un VectorGraphicsItem
            try:
                world = item.obj.world_path()
            except Exception:
                continue
            for poly in world.toSubpathPolygons(QTransform()):
                if poly.count() < 1:
                    continue
                # Extrémités de polyligne
                for idx in (0, poly.count() - 1):
                    p = poly.at(idx)
                    x_mm, y_mm = p.x(), p.y()
                    # world_path est déjà en mm monde Y-haut
                    pts.append(self.mm_to_scene(x_mm, y_mm))
                # Tous les sommets (utile pour repartir d'un coin d'encoche)
                for i in range(poly.count()):
                    p = poly.at(i)
                    pts.append(self.mm_to_scene(p.x(), p.y()))
        return pts

    def _snap_scene_pos(self, scene_pos):
        """Accroche scene_pos à l'extrémité / sommet le plus proche si dans le rayon."""
        if not self.endpoint_snap_enabled:
            return scene_pos, False
        view_scale = max(abs(self.transform().m11()), 0.01)
        max_d = self.endpoint_snap_px / view_scale
        max_d2 = max_d * max_d
        best = None
        best_d2 = max_d2
        for p in self._collect_endpoint_scene_points():
            dx = p.x() - scene_pos.x()
            dy = p.y() - scene_pos.y()
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best = p
        if best is not None:
            return QPointF(best), True
        return scene_pos, False

    def _show_snap_indicator(self, scene_pos):
        view_scale = max(abs(self.transform().m11()), 0.01)
        r = 6.0 / view_scale
        if self._snap_indicator is None:
            self._snap_indicator = QGraphicsEllipseItem()
            self._snap_indicator.setBrush(QBrush(QColor(255, 200, 0, 180)))
            self._snap_indicator.setPen(QPen(QColor("#222222"), 0))
            self._snap_indicator.setZValue(3000)
            self.scene_obj.addItem(self._snap_indicator)
        self._snap_indicator.setRect(scene_pos.x() - r, scene_pos.y() - r, 2 * r, 2 * r)
        self._snap_indicator.setVisible(True)

    def _hide_snap_indicator(self):
        if self._snap_indicator is not None:
            self._snap_indicator.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # Clic droit en mode dessin : annule l'outil et revient à la sélection.
        if event.button() == Qt.MouseButton.RightButton and self._draw_tool:
            self._ctx_menu_block_until = time.monotonic() + 0.6
            self.set_draw_tool(None)
            event.accept()
            return

        # Mode nœuds : clic gauche = sélection / début de drag d'un sommet
        if event.button() == Qt.MouseButton.LeftButton and self._node_mode:
            scene_pos = self.mapToScene(event.position().toPoint())
            hit = self._hit_node_handle(scene_pos)
            if hit is not None:
                self._node_drag_index = hit
                self._node_drag_pushed_undo = False
                event.accept()
                return
            # Double-clic géré séparément ; simple clic sur segment = rien
            event.accept()
            return

        if (event.button() == Qt.MouseButton.LeftButton and not self._draw_tool
                and self._hit_follow_handle(event.position().toPoint())):
            self._follow_dragging = True
            self._follow_drag_pushed = False
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._draw_tool == "measure":
            raw = self.mapToScene(event.position().toPoint())
            pt, snapped = self._snap_scene_pos(raw)
            if snapped:
                self._show_snap_indicator(pt)
            if self._measure_p1 is None:
                self._measure_p1 = pt
                self._measure_press_px = event.position().toPoint()
                if self._measure_preview is None:
                    self._measure_preview = self.scene_obj.addPath(QPainterPath(), self._preview_pen())
                    self._measure_preview.setZValue(1000)
            else:
                self._end_measure(pt)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._draw_tool in ("line", "rect", "circle", "ellipse"):
            if not self.layer_manager.layers:
                event.accept()
                return
            raw = self.mapToScene(event.position().toPoint())
            pt, snapped = self._snap_scene_pos(raw)
            if snapped:
                self._show_snap_indicator(pt)

            phase = self._draw_phase

            # --- Phase profondeur : début du TIRÉ (après les 2 clics nœuds) ---
            if (
                phase in ("p2", "depth")
                and self._draw_tool == "rect"
                and self._draw_base_p1 is not None
                and self._draw_base_p2 is not None
            ):
                self._draw_phase = "depth"
                self._draw_depth_dragging = True
                self._draw_awaiting_depth = True
                self._draw_last_cursor_scene = pt
                event.accept()
                return

            # --- Phase p1 : 2e CLIC (pas de tiré) → place le 2e nœud ---
            if phase == "p1" and self._draw_start_scene is not None:
                if self._draw_tool in ("line", "circle", "ellipse"):
                    start = self._draw_start_scene
                    self._cancel_draw_preview()
                    obj = self._create_drawn_object(start, pt)
                    if obj is not None:
                        self.push_undo_snapshot()
                        item = self.add_object(obj)
                        self.scene_obj.clearSelection()
                        item.setSelected(True)
                    event.accept()
                    return
                # Rectangle : largeur figée, on n'autorise le tiré QU'après ce clic
                self._draw_base_p1 = QPointF(self._draw_start_scene)
                self._draw_base_p2 = QPointF(pt)
                self._draw_phase = "p2"
                self._draw_awaiting_second = False
                self._draw_awaiting_depth = True
                self._draw_depth_dragging = False
                self._draw_dim_buffer = ""
                self._draw_last_cursor_scene = pt
                if self._draw_preview_item is None:
                    self._draw_preview_item = self.scene_obj.addPath(
                        QPainterPath(), self._preview_pen()
                    )
                    self._draw_preview_item.setZValue(1000)
                # Aperçu = segment de base uniquement (pas encore de profondeur)
                path = QPainterPath()
                path.moveTo(self._draw_base_p1)
                path.lineTo(self._draw_base_p2)
                self._draw_preview_item.setPath(path)
                self._draw_preview_item.setPen(self._preview_pen())
                event.accept()
                return

            # --- Phase None : 1er CLIC ---
            if phase is None:
                self._draw_start_scene = pt
                self._draw_phase = "p1"
                self._draw_pressed = self._draw_tool in ("circle", "ellipse")
                self._draw_press_screen = event.position().toPoint()
                self._draw_awaiting_second = True
                self._draw_awaiting_depth = False
                self._draw_depth_dragging = False
                self._draw_base_p1 = None
                self._draw_base_p2 = None
                self._draw_dim_buffer = ""
                self._draw_last_cursor_scene = pt
                if self._draw_preview_item is None:
                    self._draw_preview_item = self.scene_obj.addPath(
                        QPainterPath(), self._preview_pen()
                    )
                    self._draw_preview_item.setZValue(1000)
                event.accept()
                return

            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            item_at = self.itemAt(event.position().toPoint())

            if isinstance(item_at, VectorGraphicsItem):
                modifiers = event.modifiers()

                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    # Ctrl + clic : ajoute l'objet à la sélection (ou le
                    # retire s'il en faisait déjà partie), sans toucher au
                    # reste de la sélection.
                    new_state = not item_at.isSelected()
                    item_at.setSelected(new_state)
                    if not new_state:
                        # Objet désélectionné : simple bascule, pas de
                        # déplacement groupé à démarrer.
                        event.accept()
                        return
                elif not item_at.isSelected():
                    # Sans Ctrl : si l'objet cliqué ne fait pas déjà partie
                    # de la sélection, il devient l'unique objet sélectionné.
                    self.scene_obj.clearSelection()
                    item_at.setSelected(True)

                selected = self.selected_items_vector()

                if selected:
                    self.push_undo_snapshot()
                    self._group_drag_items = selected
                    self._group_drag_anchor_item = item_at
                    self._group_drag_last_scene_pos = self.mapToScene(
                        event.position().toPoint()
                    )
                    event.accept()
                    return

        # Permet de conserver la sélection rectangulaire par cliquer-glisser
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_last_pos is not None and (
            event.buttons() & Qt.MouseButton.MiddleButton
        ):
            new_pos = event.position().toPoint()
            delta = new_pos - self._pan_last_pos
            self._pan_last_pos = new_pos

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return

        # Glisser la poignée d'un texte le long de son contour
        if self._follow_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self._drag_follow_handle(event.position().toPoint())
            event.accept()
            return

        # Drag d'un nœud
        if (
            self._node_mode
            and self._node_drag_index is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            if not self._node_drag_pushed_undo:
                self.push_undo_snapshot()
                self._node_drag_pushed_undo = True
            scene_pos = self.mapToScene(event.position().toPoint())
            local = self._scene_to_local(scene_pos)
            pi, vi = self._node_drag_index
            if pi < len(self._node_polylines) and vi < len(self._node_polylines[pi]):
                self._node_polylines[pi][vi] = local
                # Mise à jour légère : rebuild path + handles
                item = self._node_target_item
                if item is not None and isinstance(item.obj, SvgPathObject):
                    path = self._polylines_to_path(self._node_polylines)
                    sx = getattr(item.obj, "scale_x", 1.0) or 1.0
                    sy = getattr(item.obj, "scale_y", 1.0) or 1.0
                    if abs(sx - 1.0) > 1e-9 or abs(sy - 1.0) > 1e-9:
                        t = QTransform()
                        t.scale(1.0 / sx, 1.0 / sy)
                        path = t.map(path)
                    item.obj._local_path_data = path
                    item.refresh()
                    # Déplace juste le handle concerné
                    for h in self._node_handles:
                        data = h.data(0)
                        if data and data[0] == "node" and data[1] == pi and data[2] == vi:
                            view_scale = max(self.transform().m11(), 0.01)
                            r = 5.0 / view_scale
                            sp = self._local_to_scene(local)
                            h.setRect(sp.x() - r, sp.y() - r, 2 * r, 2 * r)
                            break
            event.accept()
            return

        # Aperçu profondeur : UNIQUEMENT pendant le tiré (bouton enfoncé)
        if (
            self._draw_tool == "rect"
            and self._draw_depth_dragging
            and self._draw_base_p1 is not None
            and self._draw_base_p2 is not None
            and self._draw_preview_item is not None
        ):
            raw = self.mapToScene(event.position().toPoint())
            end, snapped = self._snap_scene_pos(raw)
            self._draw_last_cursor_scene = end
            if snapped:
                self._show_snap_indicator(end)
            else:
                self._hide_snap_indicator()
            depth = self._depth_from_cursor(self._draw_base_p1, self._draw_base_p2, end)
            path = self._preview_path_base_depth(
                self._draw_base_p1, self._draw_base_p2, depth,
                ellipse=(self._draw_tool == "ellipse"),
            )
            self._draw_preview_item.setPath(path)
            self._draw_preview_item.setPen(self._preview_pen())
            event.accept()
            return

        # Phase p2 (base fixée, pas encore de tiré) : segment fixe + accroche
        if (
            self._draw_tool == "rect"
            and self._draw_phase == "p2"
            and self._draw_base_p1 is not None
            and self._draw_base_p2 is not None
            and self._draw_preview_item is not None
        ):
            raw = self.mapToScene(event.position().toPoint())
            end, snapped = self._snap_scene_pos(raw)
            self._draw_last_cursor_scene = end
            if snapped:
                self._show_snap_indicator(end)
            else:
                self._hide_snap_indicator()
            path = QPainterPath()
            path.moveTo(self._draw_base_p1)
            path.lineTo(self._draw_base_p2)
            self._draw_preview_item.setPath(path)
            self._draw_preview_item.setPen(self._preview_pen())
            event.accept()
            return

        # Phase p1 : ligne du 1er point vers le curseur (sans tenir le bouton)
        if (
            self._draw_tool in ("line", "rect", "circle", "ellipse")
            and self._draw_phase == "p1"
            and self._draw_start_scene is not None
            and self._draw_preview_item is not None
        ):
            raw_end = self.mapToScene(event.position().toPoint())
            end, snapped = self._snap_scene_pos(raw_end)
            self._draw_last_cursor_scene = end
            if snapped:
                self._show_snap_indicator(end)
            else:
                self._hide_snap_indicator()
            if self._draw_tool in ("circle", "ellipse"):
                path = self._shape_preview_path(self._draw_tool, self._draw_start_scene, end)
            else:
                path = QPainterPath()
                path.moveTo(self._draw_start_scene)
                path.lineTo(end)
            self._draw_preview_item.setPath(path)
            self._draw_preview_item.setPen(self._preview_pen())
            event.accept()
            return

        # Aperçu mesure
        if self._draw_tool == "measure" and self._measure_p1 is not None:
            raw = self.mapToScene(event.position().toPoint())
            end, snapped = self._snap_scene_pos(raw)
            if snapped:
                self._show_snap_indicator(end)
            else:
                self._hide_snap_indicator()
            if self._measure_preview is not None:
                path = QPainterPath()
                path.moveTo(self._measure_p1)
                path.lineTo(end)
                self._measure_preview.setPath(path)
            # La mesure s'affiche pendant qu'on tire le trait, à côté de lui.
            self._update_measure_text(self._measure_p1, end)
            event.accept()
            return

        # Survol outil dessin/mesure : prévisualise l'accroche
        if self._draw_tool and not (event.buttons() & Qt.MouseButton.LeftButton):
            raw = self.mapToScene(event.position().toPoint())
            snapped_pos, snapped = self._snap_scene_pos(raw)
            if snapped:
                self._show_snap_indicator(snapped_pos)
            else:
                self._hide_snap_indicator()

        # Déplacement groupé des objets sélectionnés
        if (
            self._group_drag_items
            and event.buttons() & Qt.MouseButton.LeftButton
            and self._group_drag_last_scene_pos is not None
        ):
            current_scene_pos = self.mapToScene(event.position().toPoint())
            delta = current_scene_pos - self._group_drag_last_scene_pos

            if delta.x() or delta.y():
                delta_x_mm = delta.x() / self.px_per_mm
                delta_y_mm = -delta.y() / self.px_per_mm

                for item in self._group_drag_items:
                    item.obj.x_mm += delta_x_mm
                    item.obj.y_mm += delta_y_mm

                # Accroche à la grille : on ne recale QUE l'objet réellement
                # cliqué (l'ancre) sur le pas de grille, puis on répercute le
                # même petit correctif sur le reste de la sélection — plutôt
                # que d'accrocher chaque objet indépendamment, ce qui
                # déformerait l'agencement relatif d'une sélection multiple.
                if (
                    self.snap_enabled
                    and self.snap_step_mm > 0
                    and self._group_drag_anchor_item is not None
                ):
                    anchor = self._group_drag_anchor_item
                    snapped_x = round(anchor.obj.x_mm / self.snap_step_mm) * self.snap_step_mm
                    snapped_y = round(anchor.obj.y_mm / self.snap_step_mm) * self.snap_step_mm
                    corr_x = snapped_x - anchor.obj.x_mm
                    corr_y = snapped_y - anchor.obj.y_mm
                    if corr_x or corr_y:
                        for item in self._group_drag_items:
                            item.obj.x_mm += corr_x
                            item.obj.y_mm += corr_y

                for item in self._group_drag_items:
                    item.refresh()

                self._group_drag_last_scene_pos = current_scene_pos

            event.accept()
            return

        super().mouseMoveEvent(event)

    # -- gestion des objets ---------------------------------------------------
    @property
    def objects(self):
        """Objets du document (lecture ; pour modifier, passer par self.document)."""
        return self.document.objects

    def add_object(self, obj: VectorObject):
        """Ajoute `obj` au document ; renvoie son élément graphique."""
        self.document.add(obj)
        return self._items[id(obj)]

    def item_for(self, obj):
        """Élément graphique de `obj`, ou None."""
        return self._items.get(id(obj))

    def _create_item(self, obj):
        item = VectorGraphicsItem(obj, self.layer_manager, self)
        item.double_click_callback = lambda o=obj: self.edit_requested.emit(o)
        self.scene_obj.addItem(item)
        self._items[id(obj)] = item
        return item

    def _on_object_added(self, obj):
        self._create_item(obj)

    def _on_object_removed(self, obj):
        item = self._items.pop(id(obj), None)
        if item is not None:
            try:
                self.scene_obj.removeItem(item)
            except RuntimeError:
                pass

    def _on_objects_changed(self, objects):
        for obj in objects:
            item = self._items.get(id(obj))
            if item is not None:
                item.refresh()

    def _on_objects_reset(self):
        """Tout le document a changé (annuler, refaire, charger) : nouveaux éléments."""
        for item in list(self.scene_obj.items()):
            if isinstance(item, VectorGraphicsItem):
                self.scene_obj.removeItem(item)
        self._items = {}
        for obj in self.document.objects:
            self._create_item(obj)

    def _remove_item(self, item):
        """Retire l'objet de `item` du document, et l'élément de la scène même si
        son objet n'y était plus."""
        if not self.document.remove(item.obj):
            try:
                self.scene_obj.removeItem(item)
            except RuntimeError:
                pass

    def remove_selected(self):
        self.exit_node_edit()
        self.push_undo_snapshot()
        for item in list(self.scene_obj.selectedItems()):
            if isinstance(item, VectorGraphicsItem):
                self._remove_item(item)

    def duplicate_selected(self):
        self.push_undo_snapshot()
        objects = [item.obj for item in list(self.scene_obj.selectedItems()) if isinstance(item, VectorGraphicsItem)]
        return [self._items[id(clone)] for clone in self.document.duplicate(objects)]

    def group_selected(self):
        """Regroupe les objets sélectionnés (Ctrl+clic, rectangle ou Ctrl+A)
        en UN SEUL objet tracé (SvgPathObject) : la géométrie de chaque
        partie est reprise telle qu'elle est actuellement positionnée sur
        le canevas (position, rotation, miroir, taille), puis fusionnée.
        Le nouvel objet se déplace / se redimensionne / change de calque
        comme un tout. Le calque retenu est celui de l'objet le plus ancien
        de la sélection. Annulable avec Ctrl+Z. Renvoie le nouvel item, ou
        None si moins de 2 objets sont sélectionnés."""
        items = self.selected_items_vector()
        if len(items) < 2:
            return None
        order = {id(o): i for i, o in enumerate(self.objects)}
        items.sort(key=lambda it: order.get(id(it.obj), 0))
        group_obj = path_ops.group_objects([it.obj for it in items])
        if group_obj is None:
            return None
        self.push_undo_snapshot()
        self.document.replace([it.obj for it in items], [group_obj])
        new_item = self._items[id(group_obj)]
        new_item.setSelected(True)
        return new_item

    def _can_ungroup_item(self, item):
        """True si l'item est un SvgPathObject avec au moins 2 sous-tracés."""
        return path_ops.can_ungroup(getattr(item, "obj", None))

    def ungroup_selected(self):
        """Dégroupe les SvgPathObject sélectionnés : chaque sous-tracé devient
        un objet indépendant (sélectionnable, assignable à un autre calque).
        Inverse de group_selected / de l'import groupé. Annulable (Ctrl+Z).
        Renvoie la liste des nouveaux items créés."""
        items = self.selected_items_vector()
        expandable = [it for it in items if self._can_ungroup_item(it)]
        if not expandable:
            return []

        self.push_undo_snapshot()
        new_items = []
        for it in expandable:
            children = path_ops.ungroup_object(it.obj)
            if not children:
                # Rien d'utile à séparer : on laisse l'objet tel quel.
                continue
            self.document.replace([it.obj], children)
            new_items += [self._items[id(child)] for child in children]

        for it in new_items:
            it.setSelected(True)
        return new_items

    # ------------------------------------------------------------------
    # Exploser en segments + édition de nœuds
    # ------------------------------------------------------------------

    # Fonctions de tracé (vector/path_ops.py), gardées sous leurs anciens noms.
    _path_to_polylines = staticmethod(path_ops.path_to_polylines)
    _polylines_to_path = staticmethod(path_ops.polylines_to_path)
    _world_path_to_svg_object = staticmethod(path_ops.world_path_to_svg_object)

    def _can_explode_item(self, item):
        # Tout objet avec une géométrie de chemin (forme, svg, texte) peut être explosé
        # en segments s'il a au moins une arête.
        obj = getattr(item, "obj", None)
        return obj is not None and path_ops.can_explode(obj)

    def explode_selected(self):
        """Découpe chaque objet sélectionné en **segments indépendants**
        (une ligne = un objet). Permet de supprimer une seule encoche ou un
        seul trait puis de le redessiner. Annulable (Ctrl+Z)."""
        self.exit_node_edit()
        items = self.selected_items_vector()
        targets = [it for it in items if self._can_explode_item(it)]
        if not targets:
            return []

        self.push_undo_snapshot()
        new_items = []
        for it in targets:
            segments = path_ops.explode_object(it.obj)
            if not segments:
                continue
            self.document.replace([it.obj], segments)
            new_items += [self._items[id(child)] for child in segments]

        for it in new_items:
            it.setSelected(True)
        return new_items

    def _ensure_svg_path_object(self, item):
        """Convertit ShapeObject/TextObject en SvgPathObject pour l'édition de nœuds."""
        obj = item.obj
        if isinstance(obj, SvgPathObject):
            return item
        # Bake world path into a new SvgPathObject at same position
        baked = path_ops.bake_object(obj)
        if baked is None:
            return None
        self.document.replace([obj], [baked])
        return self._items[id(baked)]

    def enter_node_edit(self, item=None):
        """Active le mode nœuds sur l'item donné (ou la sélection unique)."""
        self.set_draw_tool(None)
        if item is None:
            selected = self.selected_items_vector()
            if len(selected) != 1:
                return False
            item = selected[0]
        item = self._ensure_svg_path_object(item)
        if item is None or not isinstance(item.obj, SvgPathObject):
            return False

        self.exit_node_edit()
        self._node_mode = True
        self._node_target_item = item
        self.scene_obj.clearSelection()
        item.setSelected(True)
        # Désactive le déplacement de l'objet pendant l'édition de nœuds
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self._rebuild_node_handles()
        self.setCursor(Qt.CursorShape.CrossCursor)
        return True

    def exit_node_edit(self):
        if self._node_target_item is not None:
            try:
                self._node_target_item.setFlag(
                    QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True
                )
            except RuntimeError:
                pass
        self._clear_node_handles()
        self._node_mode = False
        self._node_target_item = None
        self._node_polylines = []
        self._node_drag_index = None
        self._node_drag_pushed_undo = False
        if not self._draw_tool:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _clear_node_handles(self):
        for h in self._node_handles:
            try:
                self.scene_obj.removeItem(h)
            except RuntimeError:
                pass
        self._node_handles = []

    def _local_to_scene(self, local_pt: QPointF):
        """Point local objet (Y Qt descendant dans local_path) -> scène."""
        item = self._node_target_item
        if item is None:
            return local_pt
        s = self.px_per_mm
        # Même pipeline que VectorGraphicsItem.refresh : scale mm->px puis transform item
        p_px = QPointF(local_pt.x() * s, local_pt.y() * s)
        return item.mapToScene(p_px)

    def _scene_to_local(self, scene_pt: QPointF):
        item = self._node_target_item
        if item is None:
            return scene_pt
        s = self.px_per_mm
        p_item = item.mapFromScene(scene_pt)
        return QPointF(p_item.x() / s, p_item.y() / s)

    def _rebuild_node_handles(self):
        self._clear_node_handles()
        item = self._node_target_item
        if item is None or not isinstance(item.obj, SvgPathObject):
            return
        # Polylignes en coords locales (avec scale_x/y déjà appliqué via local_path)
        self._node_polylines = self._path_to_polylines(item.obj.local_path())
        s = self.px_per_mm
        handle_r = 4.0  # px écran approx — on utilise cosmetic via setScale inverse
        for pi, pts in enumerate(self._node_polylines):
            for vi, pt in enumerate(pts):
                scene_pt = self._local_to_scene(pt)
                # Taille constante à l'écran : rayon en coords scène selon zoom
                view_scale = max(self.transform().m11(), 0.01)
                r = 5.0 / view_scale
                handle = QGraphicsEllipseItem(scene_pt.x() - r, scene_pt.y() - r, 2 * r, 2 * r)
                handle.setBrush(QBrush(QColor("#ffcc00")))
                handle.setPen(QPen(QColor("#222222"), 0))
                handle.setZValue(2000)
                handle.setData(0, ("node", pi, vi))
                handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                self.scene_obj.addItem(handle)
                self._node_handles.append(handle)

    def _apply_node_polylines_to_object(self):
        item = self._node_target_item
        if item is None or not isinstance(item.obj, SvgPathObject):
            return
        path = self._polylines_to_path(self._node_polylines)
        # Si scale_x/y != 1, local_path applique le scale : on stocke le path « non scalé »
        sx = getattr(item.obj, "scale_x", 1.0) or 1.0
        sy = getattr(item.obj, "scale_y", 1.0) or 1.0
        if abs(sx - 1.0) > 1e-9 or abs(sy - 1.0) > 1e-9:
            t = QTransform()
            t.scale(1.0 / sx, 1.0 / sy)
            path = t.map(path)
        item.obj._local_path_data = path
        item.refresh()
        self._rebuild_node_handles()

    def _hit_node_handle(self, scene_pos):
        view_scale = max(self.transform().m11(), 0.01)
        hit_r = 8.0 / view_scale
        best = None
        best_d = hit_r * hit_r
        for h in self._node_handles:
            data = h.data(0)
            if not data or data[0] != "node":
                continue
            c = h.rect().center()
            # rect is in item coords = scene for these items
            d = (c.x() - scene_pos.x()) ** 2 + (c.y() - scene_pos.y()) ** 2
            if d <= best_d:
                best_d = d
                best = (data[1], data[2])
        return best

    def _hit_segment(self, scene_pos):
        """Renvoie (poly_idx, insert_after_idx, local_point) si proche d'un segment."""
        if not self._node_polylines:
            return None
        view_scale = max(self.transform().m11(), 0.01)
        max_dist_scene = 8.0 / view_scale
        local_pos = self._scene_to_local(scene_pos)
        best = None
        best_d = max_dist_scene / max(self.px_per_mm, 1e-6)
        best_d = best_d * best_d
        for pi, pts in enumerate(self._node_polylines):
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                # Projection du point sur le segment
                abx, aby = b.x() - a.x(), b.y() - a.y()
                len2 = abx * abx + aby * aby
                if len2 < 1e-12:
                    continue
                t = ((local_pos.x() - a.x()) * abx + (local_pos.y() - a.y()) * aby) / len2
                t = max(0.0, min(1.0, t))
                proj = QPointF(a.x() + t * abx, a.y() + t * aby)
                dx, dy = local_pos.x() - proj.x(), local_pos.y() - proj.y()
                d = dx * dx + dy * dy
                if d < best_d:
                    best_d = d
                    best = (pi, i, proj)
        return best

    def delete_selected_node(self):
        """Supprime le nœud sous le curseur n'est pas disponible ici ; utilisé
        via sélection interne _node_drag_index ou dernier nœud cliqué."""
        if not self._node_mode or self._node_drag_index is None:
            return False
        pi, vi = self._node_drag_index
        if pi >= len(self._node_polylines):
            return False
        pts = self._node_polylines[pi]
        if len(pts) <= 2:
            # Trop peu de points : supprimer toute la polyligne
            self.push_undo_snapshot()
            self._node_polylines.pop(pi)
            if not self._node_polylines:
                # Plus rien : supprimer l'objet
                item = self._node_target_item
                self.exit_node_edit()
                if item is not None:
                    self.document.remove(item.obj)
                return True
            self._apply_node_polylines_to_object()
            return True
        self.push_undo_snapshot()
        pts.pop(vi)
        self._node_drag_index = None
        self._apply_node_polylines_to_object()
        return True

    def refresh_all(self):
        for item in self.scene_obj.items():
            if isinstance(item, VectorGraphicsItem):
                item.refresh()

    def selected_object(self):
        for item in self.scene_obj.selectedItems():
            if isinstance(item, VectorGraphicsItem):
                return item, item.obj
        return None, None
    def selected_items_vector(self):
        """Renvoie tous les éléments vectoriels actuellement sélectionnés."""
        return [
            item
            for item in self.scene_obj.selectedItems()
            if isinstance(item, VectorGraphicsItem)
    ]

    def _on_selection_changed(self):
        _, obj = self.selected_object()
        self.selection_changed.emit(obj)
        self._sync_follow_handle()

    def mouseReleaseEvent(self, event):
        if self._follow_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._follow_dragging = False
            self._follow_drag_pushed = False
            event.accept()
            return
        # Outil mesure : un trait tiré (appui, glissé, relâché) se termine au relâchement. Un simple clic ne
        # termine rien : le second clic donne l'autre extrémité.
        if (event.button() == Qt.MouseButton.LeftButton and self._draw_tool == "measure"
                and self._measure_p1 is not None and self._measure_press_px is not None):
            released = event.position().toPoint()
            if (released - self._measure_press_px).manhattanLength() >= 8:
                pt, _snapped = self._snap_scene_pos(self.mapToScene(released))
                self._end_measure(pt)
                event.accept()
                return
        self._mouse_release_core(event)
        # Un objet qu'on vient de déplacer : les textes qui suivent son contour le suivent aussi, et la poignée
        # du texte sélectionné est replacée.
        if event.button() == Qt.MouseButton.LeftButton:
            self.resync_linked_texts([i.obj for i in self.selected_items_vector()])
            self._sync_follow_handle()

    def _mouse_release_core(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = None
            self.setCursor(
                Qt.CursorShape.CrossCursor if self._draw_tool else Qt.CursorShape.ArrowCursor
            )
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._node_mode:
            if self._node_drag_index is not None:
                self._rebuild_node_handles()
                self._node_drag_index = None
                self._node_drag_pushed_undo = False
            event.accept()
            return

        # Cercle / ellipse : relâchement après un clic-glisser = forme terminée, d'un seul geste. Un simple
        # clic sans glisser laisse l'outil en attente du 2e clic.
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._draw_tool in ("circle", "ellipse")
            and self._draw_phase == "p1"
            and self._draw_pressed
        ):
            self._draw_pressed = False
            moved = 0
            if self._draw_press_screen is not None:
                moved = (event.position().toPoint() - self._draw_press_screen).manhattanLength()
            if moved >= 4 and self._draw_start_scene is not None:
                raw = self.mapToScene(event.position().toPoint())
                pt, _ = self._snap_scene_pos(raw)
                start = self._draw_start_scene
                self._cancel_draw_preview()
                obj = self._create_drawn_object(start, pt)
                if obj is not None:
                    self.push_undo_snapshot()
                    item = self.add_object(obj)
                    self.scene_obj.clearSelection()
                    item.setSelected(True)
            event.accept()
            return

        # Rectangle : fin du TIRÉ de profondeur (relâchement)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._draw_tool == "rect"
            and self._draw_depth_dragging
            and self._draw_base_p1 is not None
            and self._draw_base_p2 is not None
        ):
            raw = self.mapToScene(event.position().toPoint())
            pt, _ = self._snap_scene_pos(raw)
            depth = self._depth_from_cursor(self._draw_base_p1, self._draw_base_p2, pt)
            obj = self._create_rect_from_base(
                self._draw_base_p1, self._draw_base_p2, depth,
                ellipse=(self._draw_tool == "ellipse"),
            )
            self._draw_depth_dragging = False
            self._cancel_draw_preview()
            if obj is not None:
                self.push_undo_snapshot()
                item = self.add_object(obj)
                self.scene_obj.clearSelection()
                item.setSelected(True)
            event.accept()
            return

        # Autres outils dessin/mesure : pas de finalisation sur release
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._draw_tool in ("line", "rect", "circle", "ellipse", "measure")
        ):
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._group_drag_items:
            moved_items = list(self._group_drag_items)

            self._group_drag_items = []
            self._group_drag_last_scene_pos = None
            self._group_drag_anchor_item = None

            for item in moved_items:
                self.object_moved.emit(item.obj)

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _create_drawn_object(self, start_scene, end_scene):
        """Crée un ShapeObject (ligne / rect / ellipse) à partir de deux points scène."""
        x1, y1 = self.scene_to_mm(start_scene)
        x2, y2 = self.scene_to_mm(end_scene)
        layer_id = self._default_draw_layer_id()
        if not layer_id:
            return None

        if self._draw_tool == "line":
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 0.05:
                return None
            angle = math.degrees(math.atan2(dy, dx))
            return ShapeObject(
                shape_type="Ligne",
                width_mm=length,
                height_mm=0.1,
                layer_id=layer_id,
                x_mm=x1,
                y_mm=y1,
                rotation_deg=angle,
            )

        if self._draw_tool == "circle":
            # Cercle : 1er point = centre, 2e point = un point du cercle.
            radius = math.hypot(x2 - x1, y2 - y1)
            if radius < 0.05:
                return None
            return ShapeObject(
                shape_type="Ellipse",
                width_mm=2 * radius,
                height_mm=2 * radius,
                layer_id=layer_id,
                x_mm=x1 - radius,
                y_mm=y1 - radius,
            )

        # Rectangle / ellipse : coin bas-gauche + largeur / hauteur positives
        left, right = (x1, x2) if x1 <= x2 else (x2, x1)
        bottom, top = (y1, y2) if y1 <= y2 else (y2, y1)
        w, h = right - left, top - bottom
        if w < 0.05 and h < 0.05:
            return None
        w = max(w, 0.05)
        h = max(h, 0.05)
        shape_type = "Ellipse" if self._draw_tool == "ellipse" else "Rectangle"
        return ShapeObject(
            shape_type=shape_type,
            width_mm=w,
            height_mm=h,
            layer_id=layer_id,
            x_mm=left,
            y_mm=bottom,
        )

    def _create_drawn_object_from_dims(self, start_scene, dims, direction_scene=None):
        """Crée une forme à partir du 1er point + dimensions clavier.

        Ligne : dims = (length_mm,) — direction = curseur ou horizontale.
        Rect/ellipse : dims = (width_mm, height_mm) — signe selon quadrant curseur.
        Cercle : dims = (rayon_mm,) — le 1er point est le centre.
        """
        x1, y1 = self.scene_to_mm(start_scene)
        layer_id = self._default_draw_layer_id()
        if not layer_id:
            return None

        if self._draw_tool == "line":
            length = float(dims[0])
            if length < 0.05:
                return None
            # Direction : vers le curseur si dispo, sinon +X
            if direction_scene is not None:
                x2, y2 = self.scene_to_mm(direction_scene)
                dx, dy = x2 - x1, y2 - y1
                norm = math.hypot(dx, dy)
                if norm < 1e-9:
                    dx, dy = 1.0, 0.0
                else:
                    dx, dy = dx / norm, dy / norm
            else:
                dx, dy = 1.0, 0.0
            angle = math.degrees(math.atan2(dy, dx))
            return ShapeObject(
                shape_type="Ligne",
                width_mm=length,
                height_mm=0.1,
                layer_id=layer_id,
                x_mm=x1,
                y_mm=y1,
                rotation_deg=angle,
            )

        if self._draw_tool == "circle":
            # Cercle : la valeur saisie est le rayon, le 1er point est le centre.
            radius = abs(float(dims[0]))
            if radius < 0.05:
                return None
            return ShapeObject(
                shape_type="Ellipse",
                width_mm=2 * radius,
                height_mm=2 * radius,
                layer_id=layer_id,
                x_mm=x1 - radius,
                y_mm=y1 - radius,
            )

        if len(dims) < 2:
            return None
        w, h = abs(float(dims[0])), abs(float(dims[1]))
        if w < 0.05 and h < 0.05:
            return None
        w, h = max(w, 0.05), max(h, 0.05)
        # Quadrant selon le curseur par rapport au 1er point
        sx = sy = 1.0
        if direction_scene is not None:
            x2, y2 = self.scene_to_mm(direction_scene)
            if x2 < x1:
                sx = -1.0
            if y2 < y1:
                sy = -1.0
        left = x1 if sx >= 0 else x1 - w
        bottom = y1 if sy >= 0 else y1 - h
        shape_type = "Ellipse" if self._draw_tool == "ellipse" else "Rectangle"
        return ShapeObject(
            shape_type=shape_type,
            width_mm=w,
            height_mm=h,
            layer_id=layer_id,
            x_mm=left,
            y_mm=bottom,
        )

    def _parse_draw_dimensions(self, text):
        """Parse '25', '25mm', '30x20', '30 x 20', '30,20' → tuple de floats (mm)."""
        t = (text or "").strip().lower().replace(",", "x").replace(" ", "")
        t = t.replace("mm", "")
        if not t:
            return None
        if "x" in t:
            parts = [p for p in t.split("x") if p]
            try:
                vals = tuple(float(p) for p in parts[:2])
            except ValueError:
                return None
            return vals if vals else None
        try:
            return (float(t),)
        except ValueError:
            return None

    def _commit_draw_dimensions(self):
        """Valide le buffer de dimensions et crée l'objet."""
        dims = self._parse_draw_dimensions(self._draw_dim_buffer)
        if not dims:
            return False

        # Profondeur seule après base 2 nœuds (rect / ellipse)
        if (
            self._draw_awaiting_depth
            and self._draw_base_p1 is not None
            and self._draw_base_p2 is not None
            and self._draw_tool == "rect"
        ):
            depth = float(dims[0])
            # Signe : côté du curseur par rapport à la base
            if self._draw_last_cursor_scene is not None:
                auto = self._depth_from_cursor(
                    self._draw_base_p1, self._draw_base_p2, self._draw_last_cursor_scene
                )
                if auto < 0:
                    depth = -abs(depth)
                else:
                    depth = abs(depth)
            obj = self._create_rect_from_base(
                self._draw_base_p1, self._draw_base_p2, depth,
                ellipse=(self._draw_tool == "ellipse"),
            )
            self._cancel_draw_preview()
            if obj is None:
                return False
            self.push_undo_snapshot()
            item = self.add_object(obj)
            self.scene_obj.clearSelection()
            item.setSelected(True)
            return True

        if not self._draw_awaiting_second or self._draw_start_scene is None:
            return False
        if self._draw_tool == "line" and len(dims) >= 1:
            pass
        elif self._draw_tool == "circle" and len(dims) >= 1:
            pass
        elif self._draw_tool in ("rect", "ellipse") and len(dims) >= 2:
            pass
        elif self._draw_tool in ("rect", "ellipse") and len(dims) == 1:
            dims = (dims[0], dims[0])  # carré / cercle
        else:
            return False
        obj = self._create_drawn_object_from_dims(
            self._draw_start_scene, dims, self._draw_last_cursor_scene
        )
        self._cancel_draw_preview()
        if obj is None:
            return False
        self.push_undo_snapshot()
        item = self.add_object(obj)
        self.scene_obj.clearSelection()
        item.setSelected(True)
        return True

    def _shape_preview_path(self, tool, start_scene, end_scene):
        """Aperçu scène d'un cercle (centre = 1er point, passe par le curseur) ou d'une ellipse (cadre
        d'un coin à l'autre)."""
        path = QPainterPath()
        if tool == "circle":
            radius = math.hypot(end_scene.x() - start_scene.x(), end_scene.y() - start_scene.y())
            path.addEllipse(start_scene, radius, radius)
        else:
            path.addEllipse(QRectF(start_scene, end_scene).normalized())
        return path

    def _depth_from_cursor(self, p1_scene, p2_scene, cursor_scene):
        """Distance signée du curseur à la droite p1→p2, en mm (Y machine)."""
        x1, y1 = self.scene_to_mm(p1_scene)
        x2, y2 = self.scene_to_mm(p2_scene)
        cx, cy = self.scene_to_mm(cursor_scene)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return 0.0
        # Normale unitaire à gauche de p1→p2 : (-dy, dx) / length
        nx, ny = -dy / length, dx / length
        # Projection du vecteur p1→cursor sur la normale
        return (cx - x1) * nx + (cy - y1) * ny

    def _preview_path_base_depth(self, p1_scene, p2_scene, depth_mm, ellipse=False):
        """Aperçu scène d'un rectangle (ou ellipse) défini par base + profondeur."""
        x1, y1 = self.scene_to_mm(p1_scene)
        x2, y2 = self.scene_to_mm(p2_scene)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return QPainterPath()
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux  # normale
        # 4 coins en mm monde
        c0 = (x1, y1)
        c1 = (x2, y2)
        c2 = (x2 + nx * depth_mm, y2 + ny * depth_mm)
        c3 = (x1 + nx * depth_mm, y1 + ny * depth_mm)
        s0 = self.mm_to_scene(*c0)
        s1 = self.mm_to_scene(*c1)
        s2 = self.mm_to_scene(*c2)
        s3 = self.mm_to_scene(*c3)
        path = QPainterPath()
        if ellipse:
            # Approximation : bounding orienté via polygone
            path.moveTo(s0)
            path.lineTo(s1)
            path.lineTo(s2)
            path.lineTo(s3)
            path.closeSubpath()
        else:
            path.moveTo(s0)
            path.lineTo(s1)
            path.lineTo(s2)
            path.lineTo(s3)
            path.closeSubpath()
        return path

    def _create_rect_from_base(self, p1_scene, p2_scene, depth_mm, ellipse=False):
        """Rectangle/ellipse : largeur = |p1p2|, hauteur = |depth|, orientation = angle p1→p2."""
        x1, y1 = self.scene_to_mm(p1_scene)
        x2, y2 = self.scene_to_mm(p2_scene)
        dx, dy = x2 - x1, y2 - y1
        width = math.hypot(dx, dy)
        # Refuse les « rectangles plats » (souvent un 3e clic trop proche de la base)
        if width < 0.05 or abs(depth_mm) < 0.2:
            return None
        layer_id = self._default_draw_layer_id()
        if not layer_id:
            return None
        angle = math.degrees(math.atan2(dy, dx))
        height = abs(depth_mm)
        # Toujours ancrer l'origine (x_mm,y_mm) sur le 1er point p1.
        # Si la profondeur est de l'autre côté de la normale, on inverse le
        # sens local via mirror_v pour que le corps du rectangle suive l'aperçu
        # tout en gardant p1 comme point d'ancrage (1er point).
        mirror_v = False
        if depth_mm < 0:
            mirror_v = True
        shape_type = "Ellipse" if ellipse else "Rectangle"
        return ShapeObject(
            shape_type=shape_type,
            width_mm=width,
            height_mm=height,
            layer_id=layer_id,
            x_mm=x1,
            y_mm=y1,
            rotation_deg=angle,
            mirror_v=mirror_v,
        )

    def _measure_label_text(self, p1_scene, p2_scene):
        """Texte d'une mesure : distance, puis ΔX / ΔY."""
        x1, y1 = self.scene_to_mm(p1_scene)
        x2, y2 = self.scene_to_mm(p2_scene)
        dx, dy = x2 - x1, y2 - y1
        label = f"{math.hypot(dx, dy):.2f} mm"
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            label += f"  (ΔX {dx:+.2f}  ΔY {dy:+.2f})"
        return label

    def _place_measure_text(self, text_item, p1_scene, p2_scene):
        """Taille constante à l'écran ; centré au-dessus du milieu du trait, ou à droite s'il est presque vertical."""
        view_scale = max(abs(self.transform().m11()), 0.01)
        text_item.setScale(1.0 / view_scale)
        rect = text_item.boundingRect()
        w, h = rect.width() / view_scale, rect.height() / view_scale
        gap = 8.0 / view_scale
        mx, my = (p1_scene.x() + p2_scene.x()) / 2, (p1_scene.y() + p2_scene.y()) / 2
        if abs(p2_scene.y() - p1_scene.y()) > 2.0 * abs(p2_scene.x() - p1_scene.x()):
            text_item.setPos(mx + gap, my - h / 2)
        else:
            text_item.setPos(mx - w / 2, my - h - gap)

    def _update_measure_text(self, p1_scene, p2_scene):
        """Met à jour (en le créant au besoin) le texte de mesure qui accompagne le trait en cours."""
        from PyQt6.QtWidgets import QGraphicsSimpleTextItem

        if self._measure_text is None:
            self._measure_text = QGraphicsSimpleTextItem()
            self._measure_text.setBrush(QBrush(QColor("#ffcc66")))
            self._measure_text.setZValue(1501)
            self.scene_obj.addItem(self._measure_text)
        self._measure_text.setText(self._measure_label_text(p1_scene, p2_scene))
        self._place_measure_text(self._measure_text, p1_scene, p2_scene)

    def _end_measure(self, p2_scene):
        """Termine la mesure : l'annotation reste affichée, le trait et le texte provisoires disparaissent."""
        p1_scene = self._measure_p1
        self._clear_measure_temp()
        self._hide_snap_indicator()
        if p1_scene is not None:
            self._finalize_measure(p1_scene, p2_scene)

    def _finalize_measure(self, p1_scene, p2_scene):
        """Ajoute une annotation de mesure (distance + ΔX / ΔY) sur le canevas."""
        from PyQt6.QtWidgets import QGraphicsSimpleTextItem

        path = QPainterPath()
        path.moveTo(p1_scene)
        path.lineTo(p2_scene)
        pen = QPen(QColor("#ffaa00"), 1.2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        line_item = self.scene_obj.addPath(path, pen)
        line_item.setZValue(1500)

        text_item = QGraphicsSimpleTextItem(self._measure_label_text(p1_scene, p2_scene))
        text_item.setBrush(QBrush(QColor("#ffcc66")))
        text_item.setZValue(1501)
        self.scene_obj.addItem(text_item)
        self._place_measure_text(text_item, p1_scene, p2_scene)
        self._measure_labels.extend([line_item, text_item])

    def mouseDoubleClickEvent(self, event):
        if self._node_mode and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            # Priorité : pas sur un nœud existant
            if self._hit_node_handle(scene_pos) is None:
                hit = self._hit_segment(scene_pos)
                if hit is not None:
                    pi, after_i, proj = hit
                    self.push_undo_snapshot()
                    self._node_polylines[pi].insert(after_i + 1, proj)
                    self._apply_node_polylines_to_object()
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)

    @staticmethod
    def _is_zoom_key(event, direction):
        """Ctrl++ (direction +1) ou Ctrl+- (direction -1), sur la rangée du haut ou le pavé numérique.
        Ctrl+= compte aussi pour Ctrl++ : sur un clavier QWERTY, « + » est sur la touche « = »."""
        if direction > 0 and event.matches(QKeySequence.StandardKey.ZoomIn):
            return True
        if direction < 0 and event.matches(QKeySequence.StandardKey.ZoomOut):
            return True
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return False
        keys = (Qt.Key.Key_Plus, Qt.Key.Key_Equal) if direction > 0 else (Qt.Key.Key_Minus,)
        return event.key() in keys

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._draw_tool:
            if self._draw_phase is not None or self._draw_awaiting_depth or self._draw_awaiting_second:
                self._cancel_draw_preview()
                event.accept()
                return
            if self._draw_tool == "measure" and self._measure_p1 is not None:
                self._clear_measure_temp()
                event.accept()
                return
            self.set_draw_tool(None)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self._node_mode:
            self.exit_node_edit()
            event.accept()
            return

        # Saisie de dimensions après le 1er point ou profondeur après base
        if (
            (self._draw_awaiting_second or self._draw_awaiting_depth)
            and self._draw_tool in ("line", "rect", "circle", "ellipse")
        ):
            key = event.key()
            text = event.text() or ""
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._commit_draw_dimensions():
                    event.accept()
                    return
            if key == Qt.Key.Key_Backspace:
                self._draw_dim_buffer = self._draw_dim_buffer[:-1]
                event.accept()
                return
            if text and (text.isdigit() or text in ".,xX*-+"):
                if text in "X*":
                    text = "x"
                if text == ",":
                    text = "."
                self._draw_dim_buffer += text
                event.accept()
                return

        if self._node_mode and event.key() in (
            Qt.Key.Key_Delete, Qt.Key.Key_Backspace
        ):
            # Supprime le nœud le plus récemment dragué, ou celui sous le curseur
            if self._node_drag_index is not None:
                self.delete_selected_node()
            else:
                # Essaye le nœud sous la position courante de la souris
                from PyQt6.QtGui import QCursor
                scene_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
                hit = self._hit_node_handle(scene_pos)
                if hit is not None:
                    self._node_drag_index = hit
                    self.delete_selected_node()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            for item in self.scene_obj.items():
                if isinstance(item, VectorGraphicsItem):
                    item.setSelected(True)
            event.accept()
            return
        if self._is_zoom_key(event, +1):
            self.zoom_in()
            event.accept()
            return
        if self._is_zoom_key(event, -1):
            self.zoom_out()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Redo):
            self.redo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selected()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_clipboard()
            event.accept()
            return
        if event.key() == Qt.Key.Key_G and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.group_selected()
            event.accept()
            return
        if event.key() == Qt.Key.Key_D and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.duplicate_selected()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.remove_selected()
            event.accept()
            return
        arrows = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, 1), Qt.Key.Key_Down: (0, -1)}
        if event.key() in arrows:
            direction = arrows[event.key()]
            if self.nudge_selection(direction[0], direction[1], event.modifiers()):
                event.accept()
                return
        super().keyPressEvent(event)

    def nudge_selection(self, dir_x, dir_y, modifiers=None):
        """Flèches du clavier : déplace la sélection de 1 mm (Maj : 10 mm ; Alt : 0,1 mm). Les pressions
        rapprochées (touche maintenue) ne comptent que pour UN « Annuler ». Renvoie False si rien n'est
        sélectionné : la vue défile alors normalement."""
        items = [it for it in self.scene_obj.selectedItems() if isinstance(it, VectorGraphicsItem)]
        if not items:
            return False
        shift = bool(modifiers and (modifiers & Qt.KeyboardModifier.ShiftModifier))
        alt = bool(modifiers and (modifiers & Qt.KeyboardModifier.AltModifier))
        step = nudge_step(shift=shift, alt=alt)
        now = time.monotonic()
        if now - getattr(self, "_last_nudge_time", -1e9) > NUDGE_UNDO_WINDOW_S:
            self.push_undo_snapshot()
        self._last_nudge_time = now
        for item in items:
            item.obj.x_mm += dir_x * step
            item.obj.y_mm += dir_y * step
            item.refresh()
        return True

    def copy_selected(self):
        """Ctrl+C : copie les objets sélectionnés dans un presse-papiers
        interne (propre à l'éditeur, pas le presse-papiers système)."""
        self.document.copy([it.obj for it in self.scene_obj.selectedItems() if isinstance(it, VectorGraphicsItem)])

    def paste_clipboard(self):
        """Ctrl+V : colle les objets copiés, légèrement décalés pour rester
        visibles distinctement de l'original."""
        if not self.document.has_clipboard():
            return
        self.push_undo_snapshot()
        for item in list(self.scene_obj.selectedItems()):
            item.setSelected(False)
        for clone in self.document.paste():
            self._items[id(clone)].setSelected(True)

    def push_undo_snapshot(self):
        """À appeler AVANT toute action qui modifie les objets (ajout,
        suppression, déplacement, redimensionnement...), pour pouvoir revenir
        en arrière avec Ctrl+Z ou le bouton Annuler (VectorDocument.push_snapshot)."""
        self.document.push_snapshot()

    def undo(self):
        self.document.undo()

    def redo(self):
        """Ctrl+Y (ou Ctrl+Maj+Z selon la plateforme, via
        QKeySequence.StandardKey.Redo) : rétablit la dernière action annulée
        par undo()."""
        self.document.redo()

    def contextMenuEvent(self, event):
        """Clic droit : actions sur la sélection (calque, taille, groupe...) et,
        toujours, sous-menu « Ajouter une forme » (texte, ligne, carré, cercle)
        à l'endroit cliqué — y compris sur un canevas vide."""
        if time.monotonic() < getattr(self, "_ctx_menu_block_until", 0.0):
            # Le clic droit vient d'annuler un outil de dessin : pas de menu.
            return

        selected = [it for it in self.scene_obj.selectedItems() if isinstance(it, VectorGraphicsItem)]
        if not selected:
            item_at = self.itemAt(event.pos())
            if isinstance(item_at, VectorGraphicsItem):
                item_at.setSelected(True)
                selected = [item_at]

        menu = QMenu(self)
        if selected:
            self._populate_selection_menu(menu, selected)
            menu.addSeparator()

        click_mm = self.scene_to_mm(self.mapToScene(event.pos()))
        self._populate_insert_menu(menu, click_mm)
        menu.exec(event.globalPos())

    # -- Texte le long d'un objet existant -------------------------------------

    # Finesse de l'aplatissement des courbes du contour : 1/20 mm.
    _FOLLOW_FLATTEN = 20.0

    def text_follow_candidates(self):
        """(élément texte, élément guide) si la sélection est exactement un texte et un autre objet, sinon None."""
        items = self.selected_items_vector()
        texts = [it for it in items if isinstance(it.obj, TextObject)]
        guides = [it for it in items if not isinstance(it.obj, TextObject)]
        if len(items) == 2 and len(texts) == 1 and len(guides) == 1:
            return texts[0], guides[0]
        return None

    def _guide_polyline(self, obj):
        """Contour le plus long de `obj`, en points (x, y) mm monde (Y vers le haut), courbes aplaties.
        Refermé si l'objet est une forme fermée. None si l'objet n'a pas de contour exploitable."""
        k = self._FOLLOW_FLATTEN
        best, best_len = None, 0.0
        for poly in obj.world_path().toSubpathPolygons(QTransform.fromScale(k, k)):
            pts = [(poly.at(i).x() / k, poly.at(i).y() / k) for i in range(poly.count())]
            length = path_length(pts)
            if len(pts) >= 2 and length > best_len:
                best, best_len = pts, length
        if best is None:
            return None
        closed_shape = isinstance(obj, ShapeObject) and obj.shape_type in ("Rectangle", "Ellipse", "Polygone Régulier")
        if closed_shape and not is_closed(best):
            best.append(best[0])
        return best

    def _apply_follow(self, text, guide_obj, pts, keep_settings=False):
        """Pose `text` sur le contour `pts` (de `guide_obj`) : copie du tracé, origine, position par défaut.
        `keep_settings` : texte déjà posé sur un tracé qu'on resynchronise, la position, le côté et la
        distance choisis sont conservés."""
        origin = (min(x for x, _y in pts), min(y for _x, y in pts))
        # Le texte est calculé directement dans le repère du tracé : ni rotation ni miroir, origine = coin
        # bas-gauche du tracé.
        text.rotation_deg = 0.0
        text.mirror_h = False
        text.mirror_v = False
        text.vertical = False
        text.arc_radius_mm = 0.0
        text.x_mm, text.y_mm = origin
        text.follow_points = relative_points(pts, origin)
        text.follow_closed = is_closed(pts)
        text.follow_guide_id = guide_obj.id
        if not keep_settings:
            text.follow_center = default_center_fraction(pts)
            text.follow_reverse = False
            text.follow_gap_mm = 0.0

    def make_text_follow_object(self):
        """Fait suivre au texte sélectionné le contour de l'autre objet sélectionné. Le contour est COPIÉ dans
        le texte : l'objet guide n'est pas modifié (on peut le garder pour la découpe ou le supprimer). Si le
        texte suivait déjà un contour, ses réglages (position, côté, distance) sont conservés : c'est une
        resynchronisation. Renvoie False si la sélection ne convient pas."""
        pair = self.text_follow_candidates()
        if pair is None:
            return False
        text_item, guide_item = pair
        pts = self._guide_polyline(guide_item.obj)
        if pts is None:
            return False
        pts = orient_path(pts)
        if path_length(pts) < 1.0:
            return False
        self.push_undo_snapshot()
        text = text_item.obj
        self._apply_follow(text, guide_item.obj, pts, keep_settings=bool(getattr(text, "follow_points", None)))
        text_item.refresh()
        self.scene_obj.clearSelection()
        text_item.setSelected(True)
        return True

    def _object_by_id(self, obj_id):
        for it in self.scene_obj.items():
            if isinstance(it, VectorGraphicsItem) and it.obj.id == obj_id:
                return it
        return None

    def linked_guide_item(self, text_obj):
        """Élément de l'objet dont `text_obj` a copié le contour, s'il existe encore (sinon None)."""
        guide_id = getattr(text_obj, "follow_guide_id", None)
        if not guide_id or not getattr(text_obj, "follow_points", None):
            return None
        item = self._object_by_id(guide_id)
        return item if item is not None and not isinstance(item.obj, TextObject) else None

    def resync_text_guide(self, text_item, push_undo=True):
        """Recopie le contour de l'objet guide dans le texte (le guide a bougé ou changé de taille), en
        gardant la position, le côté et la distance. Renvoie False si le guide n'existe plus."""
        guide_item = self.linked_guide_item(text_item.obj)
        if guide_item is None:
            return False
        pts = self._guide_polyline(guide_item.obj)
        if pts is None:
            return False
        pts = orient_path(pts)
        if path_length(pts) < 1.0:
            return False
        if push_undo:
            self.push_undo_snapshot()
        self._apply_follow(text_item.obj, guide_item.obj, pts, keep_settings=True)
        text_item.refresh()
        return True

    def resync_linked_texts(self, guide_objs):
        """Resynchronise (sans nouvelle étape d'annulation) les textes liés aux objets `guide_objs` : appelé
        quand on vient de déplacer ou modifier ces objets."""
        ids = {o.id for o in guide_objs if not isinstance(o, TextObject)}
        if not ids:
            return 0
        done = 0
        for item in [i for i in self.scene_obj.items() if isinstance(i, VectorGraphicsItem)]:
            if isinstance(item.obj, TextObject) and getattr(item.obj, "follow_guide_id", None) in ids:
                if self.resync_text_guide(item, push_undo=False):
                    done += 1
        return done

    # -- Texte de médaille : un texte en haut et un en bas, à l'intérieur d'un contour fermé -----------------

    def medal_guide_item(self):
        """L'élément sélectionné s'il s'agit d'un seul objet (hors texte) à contour fermé, sinon None."""
        items = self.selected_items_vector()
        if len(items) != 1 or isinstance(items[0].obj, TextObject):
            return None
        pts = self._guide_polyline(items[0].obj)
        if pts is None or not is_closed(pts) or path_length(pts) < 1.0:
            return None
        return items[0]

    def make_medal_texts(self, top_text, bottom_text, font_family, size_mm, margin_mm, layer_id,
                         bold=False, italic=False):
        """Pose `top_text` en haut et `bottom_text` en bas, à l'intérieur du contour fermé sélectionné : les
        deux se lisent à l'endroit, la tête des lettres vers l'extérieur en haut, vers le centre en bas, à
        `margin_mm` du trait. Un texte vide est ignoré. Renvoie la liste des objets texte créés."""
        guide_item = self.medal_guide_item()
        if guide_item is None:
            return []
        pts = orient_path(self._guide_polyline(guide_item.obj))
        created = []
        self.push_undo_snapshot()
        for text, bottom in ((top_text, False), (bottom_text, True)):
            if not text.strip():
                continue
            obj = TextObject(text=text, font_family=font_family, size_mm=size_mm, bold=bold, italic=italic,
                             layer_id=layer_id)
            self._apply_follow(obj, guide_item.obj, pts)
            obj.follow_center = side_center_fraction(pts, "bottom" if bottom else "top")
            if bottom:
                # Lu de gauche à droite en bas : sens inversé, le haut des lettres vise le centre.
                obj.follow_reverse = True
                obj.text_anchor = "above"
                obj.follow_gap_mm = margin_mm
            else:
                # En haut, à l'endroit : lettres accrochées sous le trait, vers le centre.
                obj.follow_reverse = False
                obj.text_anchor = "below"
                obj.follow_gap_mm = -margin_mm
            self.add_object(obj)
            created.append(obj)
        return created

    def discard_added_object(self, item):
        """Retire un objet qu'on vient d'ajouter pour un aperçu, et l'étape d'annulation prise juste avant :
        la boîte de dialogue a été annulée."""
        self._remove_item(item)
        self.document.drop_last_snapshot()
        self._sync_follow_handle()

    # -- Poignée : faire glisser un texte le long de son contour --------------------------------------------

    def _follow_text_item(self):
        """L'élément texte sélectionné s'il suit un contour (et seul), sinon None."""
        items = self.selected_items_vector()
        if len(items) != 1:
            return None
        obj = items[0].obj
        if isinstance(obj, TextObject) and not obj.vertical and getattr(obj, "follow_points", None):
            return items[0]
        return None

    def _follow_handle_scene_pos(self, item):
        obj = item.obj
        x, y = point_at_fraction(obj.follow_points, float(getattr(obj, "follow_center", 0.5)))
        s = self.px_per_mm
        # Le chemin local du texte est en Y vers le bas : même passage mm -> px que VectorGraphicsItem.
        return item.mapToScene(QPointF(x * s, -y * s))

    def _sync_follow_handle(self):
        """Crée, déplace ou retire la poignée selon la sélection (un texte posé sur un contour)."""
        item = self._follow_text_item()
        if item is None:
            if self._follow_handle is not None:
                try:
                    self.scene_obj.removeItem(self._follow_handle)
                except RuntimeError:
                    pass
            self._follow_handle = None
            self._follow_handle_item = None
            return
        if self._follow_handle is None or self._follow_handle_item is not item:
            if self._follow_handle is not None:
                try:
                    self.scene_obj.removeItem(self._follow_handle)
                except RuntimeError:
                    pass
            handle = QGraphicsEllipseItem(-6.0, -6.0, 12.0, 12.0)
            handle.setBrush(QBrush(QColor("#00d4ff")))
            handle.setPen(QPen(QColor("#102030"), 1))
            handle.setZValue(2100)
            # Taille constante à l'écran, quel que soit le zoom.
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            handle.setToolTip(tr("vector.follow_handle_tip"))
            self.scene_obj.addItem(handle)
            self._follow_handle = handle
            self._follow_handle_item = item
        self._follow_handle.setPos(self._follow_handle_scene_pos(item))

    def _hit_follow_handle(self, view_pos):
        if self._follow_handle is None:
            return False
        center = self.mapFromScene(self._follow_handle.pos())
        return (view_pos - center).manhattanLength() <= 14

    def _drag_follow_handle(self, view_pos):
        """Le texte suit la souris le long de son contour (point le plus proche)."""
        item = self._follow_handle_item
        if item is None:
            return
        s = self.px_per_mm
        local = item.mapFromScene(self.mapToScene(view_pos))
        point = (local.x() / s, -local.y() / s)
        if not self._follow_drag_pushed:
            self.push_undo_snapshot()
            self._follow_drag_pushed = True
        item.obj.follow_center = project_fraction(item.obj.follow_points, point)
        item.refresh()
        self._follow_handle.setPos(self._follow_handle_scene_pos(item))

    def _populate_selection_menu(self, menu, selected):
        """Entrées du clic droit qui agissent sur la sélection courante."""
        n = len(selected)
        label_suffix = tr("vector.n_objects").format(n=n) if n > 1 else ""

        layer_menu = menu.addMenu(tr("vector.assign_to_layer") + label_suffix)
        for layer in self.layer_manager.layers:
            action = layer_menu.addAction(layer_label(layer))
            action.triggered.connect(lambda checked=False, lid=layer.id, items=selected: self._bulk_assign_layer(items, lid))

        resize_action = menu.addAction(tr("vector.resize_ellipsis") + label_suffix)
        resize_action.triggered.connect(lambda: self._bulk_resize(selected))

        if n >= 2:
            group_action = menu.addAction(tr("vector.group_objects").format(n=n))
            group_action.triggered.connect(self.group_selected)

        ungroupable = [it for it in selected if self._can_ungroup_item(it)]
        if ungroupable:
            ungroup_action = menu.addAction(tr("vector.ungroup_objects"))
            ungroup_action.triggered.connect(self.ungroup_selected)

        explodable = [it for it in selected if self._can_explode_item(it)]
        if explodable:
            explode_action = menu.addAction(tr("vector.explode_path"))
            explode_action.triggered.connect(self.explode_selected)

        pair = self.text_follow_candidates()
        if pair is not None:
            already = bool(getattr(pair[0].obj, "follow_points", None))
            follow_action = menu.addAction(tr("vector.text_resync" if already else "vector.text_follow"))
            follow_action.triggered.connect(self.make_text_follow_object)
        elif len(selected) == 1 and isinstance(selected[0].obj, TextObject):
            if self.linked_guide_item(selected[0].obj) is not None:
                resync_action = menu.addAction(tr("vector.text_resync"))
                resync_action.triggered.connect(lambda: self.resync_text_guide(selected[0]))
        if self.medal_guide_item() is not None:
            medal_action = menu.addAction(tr("vector.medal"))
            medal_action.triggered.connect(self.medal_text_requested.emit)

        if len(selected) == 1:
            nodes_action = menu.addAction(tr("vector.edit_nodes"))
            nodes_action.triggered.connect(lambda: self.enter_node_edit(selected[0]))

        if self._node_mode:
            menu.addSeparator()
            exit_nodes = menu.addAction(tr("vector.exit_nodes"))
            exit_nodes.triggered.connect(self.exit_node_edit)
            del_node = menu.addAction(tr("vector.delete_node"))
            del_node.triggered.connect(self.delete_selected_node)

        menu.addSeparator()
        rotate_action = menu.addAction(tr("ui.vector_rotate_90"))
        rotate_action.triggered.connect(lambda: self._bulk_rotate(selected))
        dup_action = menu.addAction(tr("ui.vector_duplicate"))
        dup_action.triggered.connect(self.duplicate_selected)
        serial_action = menu.addAction(tr("ui.vector_serial_duplicate"))
        serial_action.triggered.connect(lambda: self.serial_duplicate_requested.emit())
        jig_action = menu.addAction(tr("ui.vector_jig"))
        jig_action.triggered.connect(lambda: self.jig_requested.emit())
        del_action = menu.addAction(tr("ui.vector_delete"))
        del_action.triggered.connect(self.remove_selected)

    def _populate_insert_menu(self, menu, click_mm):
        """Sous-menu « Ajouter une forme » : texte, ligne, carré, cercle,
        centrés sur le point cliqué (coordonnées monde, mm)."""
        add_menu = menu.addMenu(tr("vector.ctx_add_shape"))
        x_mm, y_mm = click_mm
        add_menu.addAction(tr("vector.ctx_text")).triggered.connect(
            lambda checked=False: self.insert_text_requested.emit(x_mm, y_mm))
        add_menu.addAction(tr("vector.ctx_line")).triggered.connect(
            lambda checked=False: self.add_basic_shape("Ligne", x_mm, y_mm))
        add_menu.addAction(tr("vector.ctx_square")).triggered.connect(
            lambda checked=False: self.add_basic_shape("Carré", x_mm, y_mm))
        add_menu.addAction(tr("vector.ctx_circle")).triggered.connect(
            lambda checked=False: self.add_basic_shape("Cercle", x_mm, y_mm))
        add_menu.addSeparator()
        add_menu.addAction(tr("ui.vector_jig")).triggered.connect(lambda checked=False: self.jig_requested.emit())

    def add_basic_shape(self, kind, cx_mm, cy_mm, size_mm=20.0):
        """Ajoute une ligne / un carré / un cercle centré sur (cx_mm, cy_mm),
        sur le calque par défaut, et le sélectionne (taille modifiable ensuite
        via le panneau de position/taille ou « Redimensionner »)."""
        layer_id = self._default_draw_layer_id()
        if not layer_id:
            QMessageBox.warning(self, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return None
        if kind == "Ligne":
            obj = ShapeObject(shape_type="Ligne", width_mm=size_mm * 1.5, height_mm=0.1,
                              layer_id=layer_id, x_mm=cx_mm - size_mm * 0.75, y_mm=cy_mm)
        else:
            shape_type = "Ellipse" if kind == "Cercle" else "Rectangle"
            obj = ShapeObject(shape_type=shape_type, width_mm=size_mm, height_mm=size_mm,
                              layer_id=layer_id, x_mm=cx_mm - size_mm / 2.0, y_mm=cy_mm - size_mm / 2.0)
        self.push_undo_snapshot()
        item = self.add_object(obj)
        self.scene_obj.clearSelection()
        item.setSelected(True)
        self.selection_changed.emit(obj)
        return item

    def _bulk_assign_layer(self, items, layer_id):
        self.push_undo_snapshot()
        for it in items:
            it.obj.layer_id = layer_id
            it.refresh()

    def _bulk_resize(self, items):
        """Redimensionne toute la sélection COMME UN GROUPE : les proportions
        et positions relatives entre les objets sont conservées (comme un
        redimensionnement de groupe dans un éditeur vectoriel classique),
        en millimètres plutôt qu'en pourcentage abstrait."""
        boxes = [it.obj.world_path().boundingRect() for it in items]
        x_min = min(b.left() for b in boxes)
        x_max = max(b.right() for b in boxes)
        y_min = min(b.top() for b in boxes)
        y_max = max(b.bottom() for b in boxes)
        current_w = max(x_max - x_min, 1e-6)
        current_h = max(y_max - y_min, 1e-6)

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("vector.dlg.resize_title"))
        layout = QFormLayout(dialog)
        layout.addRow(QLabel(tr("vector.dlg.group_size").format(w=current_w, h=current_h)))

        chk_keep_ratio = QCheckBox(tr("vector.dlg.keep_ratio"))
        chk_keep_ratio.setChecked(True)
        layout.addRow("", chk_keep_ratio)

        spin_w = QDoubleSpinBox(); spin_w.setRange(0.1, 5000.0); spin_w.setDecimals(2)
        spin_w.setValue(current_w); spin_w.setSuffix(" mm")
        spin_h = QDoubleSpinBox(); spin_h.setRange(0.1, 5000.0); spin_h.setDecimals(2)
        spin_h.setValue(current_h); spin_h.setSuffix(" mm")
        layout.addRow(tr("vector.dlg.new_width"), spin_w)
        layout.addRow(tr("vector.dlg.new_height"), spin_h)

        ratio = current_w / current_h if current_h else 1.0
        state = {"updating": False}

        def on_w_changed(val):
            if state["updating"] or not chk_keep_ratio.isChecked():
                return
            state["updating"] = True
            spin_h.setValue(val / ratio if ratio else val)
            state["updating"] = False

        def on_h_changed(val):
            if state["updating"] or not chk_keep_ratio.isChecked():
                return
            state["updating"] = True
            spin_w.setValue(val * ratio)
            state["updating"] = False

        spin_w.valueChanged.connect(on_w_changed)
        spin_h.valueChanged.connect(on_h_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if not dialog.exec():
            return

        self.push_undo_snapshot()
        factor_x = spin_w.value() / current_w
        factor_y = spin_h.value() / current_h

        for it in items:
            obj = it.obj
            # Repositionne l'objet proportionnellement à l'intérieur du groupe
            # (mise à l'échelle autour du coin bas-gauche du groupe entier).
            obj.x_mm = x_min + (obj.x_mm - x_min) * factor_x
            obj.y_mm = y_min + (obj.y_mm - y_min) * factor_y
            if isinstance(obj, ShapeObject):
                obj.width_mm *= factor_x
                obj.height_mm *= factor_y
            elif isinstance(obj, TextObject):
                obj.size_mm *= factor_y
                obj.letter_spacing_mm *= factor_x
                obj.arc_radius_mm = getattr(obj, "arc_radius_mm", 0.0) * factor_y
                if getattr(obj, "follow_points", None):
                    obj.follow_points = scaled_points(obj.follow_points, factor_x, factor_y)
                    obj.follow_gap_mm = getattr(obj, "follow_gap_mm", 0.0) * factor_y
            elif isinstance(obj, SvgPathObject):
                obj.scale_x = getattr(obj, "scale_x", 1.0) * factor_x
                obj.scale_y = getattr(obj, "scale_y", 1.0) * factor_y
            it.refresh()

    def _bulk_rotate(self, items):
        self.push_undo_snapshot()
        for it in items:
            it.obj.rotation_deg = (it.obj.rotation_deg + 90.0) % 360.0
            it.refresh()

    def set_object_position(self, obj: VectorObject, x_mm, y_mm, rotation_deg=None):
        """Positionnement précis par saisie numérique (offset X/Y en mm depuis
        l'origine de la zone de travail), utilisé par le panneau de propriétés."""
        obj.x_mm = x_mm
        obj.y_mm = y_mm
        if rotation_deg is not None:
            obj.rotation_deg = rotation_deg
        for item in self.scene_obj.items():
            if isinstance(item, VectorGraphicsItem) and item.obj is obj:
                item.refresh()
                break

    # -- (dé)sérialisation ----------------------------------------------------
    def serialize_objects(self):
        return self.document.serialize()

    def load_objects(self, data):
        self.document.load(data)
