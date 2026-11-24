"""Canevas de l'éditeur vectoriel (VectorCanvasView) : zone de travail en mm, grille, zoom, objets
(vue du VectorDocument), sélection, menus, texte sur contour, annulation. Les outils de la souris
(dessin, mesure, nœuds, déplacement, accroche) sont dans tools/ ; le canevas leur passe ses événements."""
import time
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QTransform, QPainter, QKeySequence
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QMessageBox
from laser_studio.i18n import tr
from laser_studio.vector import group_transform, text_follow
from laser_studio.vector.nudge import NUDGE_UNDO_WINDOW_S, nudge_step
from laser_studio.models.layers import LayersModel
from laser_studio.models.vector_document import VectorDocument
from laser_studio.models.vector_objects import GroupObject, ShapeObject, SvgPathObject, TextObject, VectorObject
from laser_studio.vector import boolean_ops
from laser_studio.vector import path_ops
from laser_studio.ui.vector_editor.context_menu import build_context_menu
from laser_studio.ui.vector_editor.item import VectorGraphicsItem
from laser_studio.ui.vector_editor.resize_dialog import GroupResizeDialog
from laser_studio.ui.vector_editor.tools.follow_handle import FollowHandle
from laser_studio.ui.vector_editor.tools.drawing import SHAPE_TOOLS, DrawingTool
from laser_studio.ui.vector_editor.tools.measure import MeasureTool
from laser_studio.ui.vector_editor.tools.moving import MoveTool
from laser_studio.ui.vector_editor.tools.node_edit import NodeEditor
from laser_studio.ui.vector_editor.tools.snapping import EndpointSnap

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
        # Accroche à la grille pendant un déplacement à la souris (voir tools/moving.py) : désactivée par
        # défaut, réglable depuis la barre d'outils de l'Éditeur Vectoriel (case + pas en mm).
        self.snap_enabled = False
        self.snap_step_mm = 5.0
        # Outil de la souris : None = sélection, sinon "line" / "rect" / "circle" / "ellipse" / "measure".
        self._draw_tool = None
        # Outils de la souris (tools/) : chacun garde son état et traite les événements de son mode.
        self.snap = EndpointSnap(self)
        self.drawing = DrawingTool(self, self.snap)
        self.measure = MeasureTool(self, self.snap, self.drawing.preview_pen)
        self.nodes = NodeEditor(self)
        self.moving = MoveTool(self)
        self.follow_handle = FollowHandle(self)
        # Fin du blocage du menu contextuel après un clic droit qui a annulé un outil de dessin.
        self._ctx_menu_block_until = 0.0
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
        self.document.order_changed.connect(self._apply_order)

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
        self.drawing.cancel_preview()
        self.measure.clear_temp()
        if tool in (None, "", "select"):
            self._draw_tool = None
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self._draw_tool = tool
            self.drawing.layer_id = layer_id
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.scene_obj.clearSelection()
            self.setFocus(Qt.FocusReason.OtherFocusReason)

    @property
    def draw_tool(self):
        """Outil de la souris actif : None (sélection), 'line', 'rect', 'circle', 'ellipse', 'measure'."""
        return self._draw_tool

    @property
    def node_mode(self):
        """Vrai pendant l'édition des nœuds d'un tracé."""
        return self.nodes.active


    def clear_measure_labels(self):
        self.measure.clear_labels()


    # -- Accroche aux extrémités (dessin) ------------------------------------


    def mousePressEvent(self, event):
        # Chaque mode traite ses clics, dans cet ordre de priorité (voir tools/).
        left = event.button() == Qt.MouseButton.LeftButton
        if self.moving.press_pan(event):
            return
        # Clic droit en mode dessin : annule l'outil et revient à la sélection.
        if event.button() == Qt.MouseButton.RightButton and self._draw_tool:
            self._ctx_menu_block_until = time.monotonic() + 0.6
            self.set_draw_tool(None)
            event.accept()
            return
        if left and self.nodes.active:
            self.nodes.press(event)
            return
        if left and not self._draw_tool and self.follow_handle.press(event):
            return
        if left and self._draw_tool == "measure":
            self.measure.press(event)
            return
        if left and self._draw_tool in SHAPE_TOOLS:
            self.drawing.press(event)
            return
        if left and self.moving.press_select(event):
            return
        # Permet de conserver la sélection rectangulaire par cliquer-glisser
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self.moving.move_pan(event):
            return
        # Glisser la poignée d'un texte le long de son contour
        if self.follow_handle.move(event):
            return
        if self.nodes.move(event) or self.drawing.move(event) or self.measure.move(event):
            return
        # Survol outil dessin/mesure : prévisualise l'accroche
        if self._draw_tool and not (event.buttons() & Qt.MouseButton.LeftButton):
            self.snap.follow(self.mapToScene(event.position().toPoint()))
        if self.moving.move_drag(event):
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
        self._apply_order()
        return item

    def _apply_order(self):
        """Empilement des éléments dans l'ordre du document : le dernier objet est au-dessus."""
        for index, obj in enumerate(self.document.objects):
            item = self._items.get(id(obj))
            if item is not None:
                item.setZValue(index)

    def select_objects(self, objects):
        """Sélectionne exactement `objects` (choisis dans la liste des objets)."""
        wanted = {id(o) for o in objects}
        self.scene_obj.blockSignals(True)
        try:
            for item in self.selected_items_vector():
                item.setSelected(False)
            for obj in objects:
                item = self._items.get(id(obj))
                if item is not None:
                    item.setSelected(True)
        finally:
            self.scene_obj.blockSignals(False)
        self._on_selection_changed()
        return [o for o in self.document.objects if id(o) in wanted]

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

    def group_selected(self, operation=boolean_ops.GROUP):
        """Groupe les objets sélectionnés (au moins 2) en un GroupObject : chaque objet reste entier (un texte
        redevient un texte modifiable au dégroupage) et le groupe se manipule d'un bloc. Avec une opération
        booléenne (union, différence…), les objets ne forment plus qu'un tracé, rempli sur le calque de
        celui du dessous. Le groupe prend la place du plus haut des objets dans l'empilement. Annulable.
        Renvoie l'élément du groupe, ou None."""
        items = self.selected_items_vector()
        if len(items) < 2:
            return None
        order = {id(o): i for i, o in enumerate(self.objects)}
        items.sort(key=lambda it: order.get(id(it.obj), 0))
        objects = [it.obj for it in items]
        group = GroupObject(objects, operation=operation)
        top = max(order[id(o)] for o in objects)
        self.push_undo_snapshot()
        self.document.replace(objects, [group])
        # À la place du plus haut des objets groupés, pas tout en haut de la pile.
        remaining_above = sum(1 for o in self.document.objects[:-1] if order.get(id(o), -1) > top)
        for _ in range(remaining_above):
            self.document.move([group], -1)
        self.select_objects([group])
        return self._items[id(group)]

    def set_group_operation(self, group, operation):
        """Change l'opération d'un groupe (simple groupe, union, différence…). Annulable."""
        if not isinstance(group, GroupObject) or group.operation == operation:
            return False
        self.push_undo_snapshot()
        group.set_operation(operation)
        self.document.notify_changed([group])
        self.selection_changed.emit(group)
        return True

    def combine_selected(self, operation):
        """Opération `operation` sur la sélection : un groupe seul change d'opération, plusieurs objets sont
        groupés avec elle. Renvoie l'objet du groupe, ou None."""
        objects = [it.obj for it in self.selected_items_vector()]
        if len(objects) == 1 and isinstance(objects[0], GroupObject):
            self.set_group_operation(objects[0], operation)
            return objects[0]
        item = self.group_selected(operation)
        return item.obj if item is not None else None

    def can_ungroup_item(self, item):
        """True pour un groupe, ou un tracé (SvgPathObject) d'au moins 2 sous-tracés."""
        obj = getattr(item, "obj", None)
        return isinstance(obj, GroupObject) or path_ops.can_ungroup(obj)

    def ungroup_selected(self):
        """Dégroupe la sélection : un groupe rend ses objets, à leur place (un texte redevient un texte) ;
        un tracé importé est séparé en sous-tracés indépendants. Annulable (Ctrl+Z). Renvoie les nouveaux
        éléments."""
        items = self.selected_items_vector()
        expandable = [it for it in items if self.can_ungroup_item(it)]
        if not expandable:
            return []

        self.push_undo_snapshot()
        new_objects = []
        for it in expandable:
            obj = it.obj
            if isinstance(obj, GroupObject):
                index = self.document.objects.index(obj)
                children = obj.released_children()
                self.document.replace([obj], children)
                # Les objets reprennent la place du groupe dans l'empilement.
                for _ in range(len(self.document.objects) - len(children) - index):
                    self.document.move(children, -1)
            else:
                children = path_ops.ungroup_object(obj)
                if not children:
                    # Rien d'utile à séparer : on laisse l'objet tel quel.
                    continue
                self.document.replace([obj], children)
            new_objects += children
        self.select_objects(new_objects)
        return [self._items[id(o)] for o in new_objects]

    # ------------------------------------------------------------------
    # Exploser en segments + édition de nœuds
    # ------------------------------------------------------------------

    # Fonctions de tracé (vector/path_ops.py), gardées sous leurs anciens noms.
    _world_path_to_svg_object = staticmethod(path_ops.world_path_to_svg_object)

    def can_explode_item(self, item):
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
        targets = [it for it in items if self.can_explode_item(it)]
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
        return self.nodes.enter(item)


    def exit_node_edit(self):
        self.nodes.exit()


    def delete_selected_node(self):
        """Supprime le nœud cliqué en mode nœuds (voir NodeEditor.delete_selected_node)."""
        return self.nodes.delete_selected_node()


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
        self.follow_handle.sync()

    def mouseReleaseEvent(self, event):
        left = event.button() == Qt.MouseButton.LeftButton
        if self.follow_handle.release(event):
            return
        if self.measure.release(event):
            return
        self._release(event)
        # Un objet qu'on vient de déplacer : les textes qui suivent son contour le suivent aussi, et la poignée
        # du texte sélectionné est replacée.
        if left:
            self.resync_linked_texts([i.obj for i in self.selected_items_vector()])
            self.follow_handle.sync()

    def _release(self, event):
        left = event.button() == Qt.MouseButton.LeftButton
        if self.moving.release_pan(event):
            return
        if left and self.nodes.active:
            self.nodes.release(event)
            return
        if self.drawing.release(event):
            return
        # Autres outils dessin/mesure : pas de finalisation sur release
        if left and self._draw_tool in SHAPE_TOOLS + ("measure",):
            event.accept()
            return
        if self.moving.release_drag(event):
            return
        super().mouseReleaseEvent(event)


    def mouseDoubleClickEvent(self, event):
        if self.nodes.double_click(event):
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
            if self.drawing.in_progress():
                self.drawing.cancel_preview()
            elif self._draw_tool == "measure" and self.measure.p1 is not None:
                self.measure.clear_temp()
            else:
                self.set_draw_tool(None)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self.nodes.active:
            self.exit_node_edit()
            event.accept()
            return
        # Saisie de dimensions après le 1er point ou profondeur après base
        if self.drawing.key(event):
            return
        if self.nodes.active and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            # Supprime le nœud le plus récemment dragué, ou celui sous le curseur
            self.nodes.delete_key()
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
        if time.monotonic() < self._ctx_menu_block_until:
            # Le clic droit vient d'annuler un outil de dessin : pas de menu.
            return

        selected = [it for it in self.scene_obj.selectedItems() if isinstance(it, VectorGraphicsItem)]
        if not selected:
            item_at = self.itemAt(event.pos())
            if isinstance(item_at, VectorGraphicsItem):
                item_at.setSelected(True)
                selected = [item_at]

        click_mm = self.scene_to_mm(self.mapToScene(event.pos()))
        build_context_menu(self, selected, click_mm).exec(event.globalPos())

    # -- Texte le long d'un objet existant (calcul : vector/text_follow.py) ---------------------------------

    def text_follow_candidates(self):
        """(élément texte, élément guide) si la sélection est exactement un texte et un autre objet, sinon None."""
        items = self.selected_items_vector()
        texts = [it for it in items if isinstance(it.obj, TextObject)]
        guides = [it for it in items if not isinstance(it.obj, TextObject)]
        if len(items) == 2 and len(texts) == 1 and len(guides) == 1:
            return texts[0], guides[0]
        return None

    def make_text_follow_object(self):
        """Fait suivre au texte sélectionné le contour de l'autre objet sélectionné. Le contour est COPIÉ dans
        le texte : l'objet guide n'est pas modifié (on peut le garder pour la découpe ou le supprimer). Si le
        texte suivait déjà un contour, ses réglages (position, côté, distance) sont conservés : c'est une
        resynchronisation. Renvoie False si la sélection ne convient pas."""
        pair = self.text_follow_candidates()
        if pair is None:
            return False
        text_item, guide_item = pair
        pts = text_follow.follow_path(guide_item.obj)
        if pts is None:
            return False
        self.push_undo_snapshot()
        text = text_item.obj
        text_follow.apply_follow(text, guide_item.obj, pts, keep_settings=text_follow.follows_a_path(text))
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
        pts = text_follow.follow_path(guide_item.obj)
        if pts is None:
            return False
        if push_undo:
            self.push_undo_snapshot()
        text_follow.apply_follow(text_item.obj, guide_item.obj, pts, keep_settings=True)
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

    def medal_guide_item(self):
        """L'élément sélectionné s'il s'agit d'un seul objet (hors texte) à contour fermé, sinon None."""
        items = self.selected_items_vector()
        if len(items) == 1 and text_follow.closed_follow_path(items[0].obj) is not None:
            return items[0]
        return None

    def make_medal_texts(self, top_text, bottom_text, font_family, size_mm, margin_mm, layer_id,
                         bold=False, italic=False):
        """Pose `top_text` en haut et `bottom_text` en bas, à l'intérieur du contour fermé sélectionné (voir
        text_follow.medal_texts). Renvoie la liste des objets texte créés."""
        guide_item = self.medal_guide_item()
        if guide_item is None:
            return []
        pts = text_follow.closed_follow_path(guide_item.obj)
        self.push_undo_snapshot()
        created = text_follow.medal_texts(guide_item.obj, pts, top_text, bottom_text, font_family, size_mm,
                                          margin_mm, layer_id, bold=bold, italic=italic)
        for obj in created:
            self.add_object(obj)
        return created

    def discard_added_object(self, item):
        """Retire un objet qu'on vient d'ajouter pour un aperçu, et l'étape d'annulation prise juste avant :
        la boîte de dialogue a été annulée."""
        self._remove_item(item)
        self.document.drop_last_snapshot()
        self.follow_handle.sync()

    def add_basic_shape(self, kind, cx_mm, cy_mm, size_mm=20.0):
        """Ajoute une ligne / un carré / un cercle centré sur (cx_mm, cy_mm),
        sur le calque par défaut, et le sélectionne (taille modifiable ensuite
        via le panneau de position/taille ou « Redimensionner »)."""
        layer_id = self.drawing.default_layer_id()
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

    # -- Sélection traitée comme un groupe (calcul : vector/group_transform.py) ------------------------------

    def assign_layer(self, items, layer_id):
        self.push_undo_snapshot()
        group_transform.assign_layer([it.obj for it in items], layer_id)
        for it in items:
            it.refresh()

    def rotate_quarter(self, items):
        self.push_undo_snapshot()
        group_transform.rotate_quarter([it.obj for it in items])
        for it in items:
            it.refresh()

    def resize_group(self, items):
        """Redimensionne toute la sélection COMME UN GROUPE, en mm : proportions et positions relatives entre
        les objets conservées, coin bas-gauche du groupe fixe."""
        objects = [it.obj for it in items]
        _x, _y, width, height = group_transform.group_bounds(objects)
        dialog = GroupResizeDialog(max(width, 1e-6), max(height, 1e-6), self)
        if not dialog.exec():
            return
        self.push_undo_snapshot()
        group_transform.resize_group(objects, *dialog.size_mm())
        for it in items:
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
