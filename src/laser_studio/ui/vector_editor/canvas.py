"""Canevas de l'éditeur vectoriel (VectorCanvasView) : la vue du VectorDocument. Il assemble ses parties et
aiguille les événements de la souris et du clavier vers elles :

- work_area (vector/work_area.py) : plateau, échelle et repère mm <-> scène, sans Qt ;
- grid, camera (scene_layers.py) : le plateau gradué et l'image de la caméra, sous les objets ;
- items (document_items.py) : un élément graphique par objet du document, et la sélection ;
- navigation (navigation.py) : zoom et cadrage ;
- les outils de la souris (tools/) : dessin, mesure, nœuds, déplacement, accroche, poignée des textes ;
- les raccourcis clavier (shortcuts.py), traduits en demandes.

C'est une vue : les opérations sur les objets (grouper, dupliquer, supprimer, copier, coller, déplacer au
clavier, calque, taille, texte sur contour…) sont faites par VectorEditorController. Le clavier et le clic
droit les demandent par signaux (command_requested, nudge_requested, layer_requested…), que
ui/vector_editor/builder.py branche sur le contrôleur.

Repère « machine » : origine en bas à gauche, Y vers le haut. Le passage au repère Qt (Y vers le bas) est
calculé pour la grille et pour chaque objet (VectorGraphicsItem.refresh), jamais par un retournement de la
vue : fitInView() peut annuler silencieusement un retournement posé sur une QGraphicsView."""
import time

from PyQt6.QtCore import QEvent, QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

from laser_studio.models.layers import LayersModel
from laser_studio.models.vector_document import VectorDocument
from laser_studio.models.vector_objects import VectorObject
from laser_studio.ui.app.theme import theme_color
from laser_studio.ui.vector_editor import shortcuts
from laser_studio.ui.vector_editor.context_menu import build_context_menu
from laser_studio.ui.vector_editor.document_items import DocumentItems
from laser_studio.ui.vector_editor.item import VectorGraphicsItem
from laser_studio.ui.vector_editor.navigation import ViewNavigator
from laser_studio.ui.vector_editor.scene_layers import CameraLayer, WorkAreaLayer
from laser_studio.ui.vector_editor.tools.drawing import SHAPE_TOOLS, DrawingTool
from laser_studio.ui.vector_editor.tools.follow_handle import FollowHandle
from laser_studio.ui.vector_editor.tools.measure import MeasureTool
from laser_studio.ui.vector_editor.tools.moving import MoveTool
from laser_studio.ui.vector_editor.tools.node_edit import NodeEditor
from laser_studio.ui.vector_editor.tools.snapping import EndpointSnap
from laser_studio.vector.work_area import WorkArea

# Après un clic droit qui annule un outil de dessin, le menu contextuel qui suit est ignoré (s).
CONTEXT_MENU_BLOCK_S = 0.6


class VectorCanvasView(QGraphicsView):
    """Vue d'édition : plateau en mm, objets déplaçables à la souris, colorés selon leur calque."""

    selection_changed = pyqtSignal(object)  # VectorObject ou None
    object_moved = pyqtSignal(object)       # VectorObject déplacé à la souris
    edit_requested = pyqtSignal(object)     # double-clic sur un objet
    insert_text_requested = pyqtSignal(float, float)  # clic droit > Texte (x_mm, y_mm)
    serial_duplicate_requested = pyqtSignal()        # clic droit > Dupliquer en série...
    jig_requested = pyqtSignal()                     # clic droit > Gabarit de placement...
    medal_text_requested = pyqtSignal()              # clic droit > Texte de médaille...
    # Commande de l'éditeur demandée au clavier ou au clic droit : "undo", "redo", "copy", "paste", "group",
    # "ungroup", "duplicate", "delete", "rotate", "resize", "explode", "text_follow" (VectorEditorController).
    command_requested = pyqtSignal(str)
    nudge_requested = pyqtSignal(int, int, bool, bool)   # flèches : direction x, y ; Maj, Alt
    layer_requested = pyqtSignal(str)                # clic droit > Assigner au calque
    combine_requested = pyqtSignal(str)              # clic droit > Combiner (opération booléenne)
    shape_requested = pyqtSignal(str, float, float)  # clic droit > Ajouter une forme (genre, x_mm, y_mm)
    text_resync_requested = pyqtSignal(object)       # clic droit > Recaler le texte sur son contour
    objects_moved = pyqtSignal(list)                 # objets déplacés à la souris (textes liés à recaler)

    def __init__(self, layer_manager: LayersModel, parent=None, document=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        # Document (objets, annuler / refaire, presse-papiers) : le canevas en est la vue.
        self.document = document if document is not None else VectorDocument(self)
        self.work_area = WorkArea()
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setBackgroundBrush(theme_color("canvas", "#1c1c1c"))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.grid = WorkAreaLayer(self.scene_obj)
        self.camera = CameraLayer(self.scene_obj)
        self.items = DocumentItems(self.document, self.scene_obj, self._make_item)
        self.navigation = ViewNavigator(self, plate=self.grid.bounds,
                                        items=lambda: self.items.selected() or self.items.all())
        # Accroche à la grille pendant un déplacement à la souris (tools/moving.py) : réglée depuis la barre
        # d'outils de l'éditeur (case et pas en mm).
        self.snap_enabled = False
        self.snap_step_mm = 5.0
        # Outil de la souris : None = sélection, sinon "line" / "rect" / "circle" / "ellipse" / "measure".
        self._draw_tool = None
        self.snap = EndpointSnap(self)
        self.drawing = DrawingTool(self, self.snap)
        self.measure = MeasureTool(self, self.snap, self.drawing.preview_pen)
        self.nodes = NodeEditor(self)
        self.moving = MoveTool(self)
        self.follow_handle = FollowHandle(self)
        self._context_menu_blocked_until = 0.0

        self.set_work_area(100.0, 100.0)
        self.scene_obj.selectionChanged.connect(self._on_selection_changed)

    # -- plateau et repère

    @property
    def px_per_mm(self):
        return self.work_area.px_per_mm

    @property
    def work_w_mm(self):
        return self.work_area.width_mm

    @property
    def work_h_mm(self):
        return self.work_area.height_mm

    def set_work_area(self, w_mm, h_mm, fit=True):
        """Plateau de `w_mm` × `h_mm` (taille de la machine) : grille redessinée, objets replacés dans le
        nouveau repère, vue cadrée sur le plateau si `fit`."""
        resized = (w_mm, h_mm) != (self.work_area.width_mm, self.work_area.height_mm)
        self.work_area = WorkArea(w_mm, h_mm, self.work_area.px_per_mm)
        self.grid.show(self.work_area)
        if resized:
            self.items.refresh()                       # leur Y d'écran dépend de la hauteur du plateau
        plate = self.grid.bounds()
        self.scene_obj.setSceneRect(plate.adjusted(-50, -50, 50, 50))
        if fit:
            self.fitInView(plate, Qt.AspectRatioMode.KeepAspectRatio)

    def scene_to_mm(self, scene_pos):
        """Point de la scène Qt (Y vers le bas) -> (x, y) en mm machine (origine bas-gauche, Y vers le haut)."""
        return self.work_area.to_mm(scene_pos.x(), scene_pos.y())

    def mm_to_scene(self, x_mm, y_mm):
        """Millimètres machine (Y vers le haut) -> point de la scène Qt (Y vers le bas)."""
        return QPointF(*self.work_area.to_scene(x_mm, y_mm))

    def set_camera_background(self, image_bgr, bed_w_mm, bed_h_mm):
        """Image de la caméra redressée sur le plateau de `bed_w_mm` × `bed_h_mm` (CameraLayer.show)."""
        self.camera.show(image_bgr, bed_w_mm, bed_h_mm, self.work_area)

    def set_snap_enabled(self, enabled):
        """Grille magnétique (case de la barre de l'éditeur) : déplacements calés sur la grille."""
        self.snap_enabled = bool(enabled)

    def set_snap_step(self, step_mm):
        """Pas de la grille magnétique, en mm."""
        self.snap_step_mm = float(step_mm)

    def changeEvent(self, event):
        # Thème changé à la volée : fond et grille reprennent ses couleurs.
        if event.type() == QEvent.Type.PaletteChange:
            self.setBackgroundBrush(theme_color("canvas", "#1c1c1c"))
            self.grid.show(self.work_area)
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.navigation.view_resized()

    def wheelEvent(self, event):
        self.navigation.wheel(event.angleDelta().y())

    # -- objets et sélection

    @property
    def objects(self):
        """Objets du document (lecture ; pour modifier, passer par self.document)."""
        return self.document.objects

    def add_object(self, obj: VectorObject):
        """Ajoute `obj` au document ; renvoie son élément graphique."""
        self.document.add(obj)
        return self.items.item_for(obj)

    def item_for(self, obj):
        """Élément graphique de `obj`, ou None."""
        return self.items.item_for(obj)

    def selected_items_vector(self):
        """Éléments graphiques sélectionnés."""
        return self.items.selected()

    def select_objects(self, objects):
        """Sélectionne exactement `objects` (choisis dans la liste des objets) ; renvoie ceux sélectionnés."""
        selected = self.items.select(objects)
        self._on_selection_changed()
        return selected

    def push_undo_snapshot(self):
        """À appeler AVANT toute action qui modifie les objets (ajout, suppression, déplacement,
        redimensionnement…), pour pouvoir revenir en arrière (VectorDocument.push_snapshot)."""
        self.document.push_snapshot()

    def _make_item(self, obj):
        return VectorGraphicsItem(obj, self.layer_manager, self, on_double_click=lambda: self.edit_requested.emit(obj))

    def _on_selection_changed(self):
        _item, obj = self.items.selected_object()
        self.selection_changed.emit(obj)
        self.follow_handle.sync()

    # -- outil de la souris

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

    # -- souris : chaque outil traite ses événements, dans cet ordre de priorité

    def mousePressEvent(self, event):
        left = event.button() == Qt.MouseButton.LeftButton
        if self.moving.press_pan(event):
            return
        if event.button() == Qt.MouseButton.RightButton and self._draw_tool:
            # Clic droit en mode dessin : annule l'outil et revient à la sélection, sans menu contextuel.
            self._context_menu_blocked_until = time.monotonic() + CONTEXT_MENU_BLOCK_S
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
        super().mousePressEvent(event)                 # sélection rectangulaire par cliquer-glisser

    def mouseMoveEvent(self, event):
        if self.moving.move_pan(event) or self.follow_handle.move(event):
            return
        if self.nodes.move(event) or self.drawing.move(event) or self.measure.move(event):
            return
        if self._draw_tool and not (event.buttons() & Qt.MouseButton.LeftButton):
            self.snap.follow(self.mapToScene(event.position().toPoint()))   # aperçu de l'accroche
        if self.moving.move_drag(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.follow_handle.release(event) or self.measure.release(event):
            return
        self._release(event)
        # Objets déplacés : les textes qui suivent leur contour suivent aussi, la poignée du texte est replacée.
        if event.button() == Qt.MouseButton.LeftButton:
            moved = [item.obj for item in self.items.selected()]
            if moved:
                self.objects_moved.emit(moved)
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
        if left and self._draw_tool in SHAPE_TOOLS + ("measure",):
            event.accept()                             # outils à clics : rien à finir au relâchement
            return
        if self.moving.release_drag(event):
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.nodes.double_click(event):
            return
        super().mouseDoubleClickEvent(event)

    # -- clavier

    def keyPressEvent(self, event):
        if self._handle_key(event):
            event.accept()
        else:
            super().keyPressEvent(event)               # sans sélection, les flèches font défiler la vue

    def _handle_key(self, event):
        """Traite la touche si elle concerne le canevas ; True si c'est le cas."""
        key = event.key()
        if key == Qt.Key.Key_Escape and self._draw_tool:
            if self.drawing.in_progress():
                self.drawing.cancel_preview()
            elif self._draw_tool == "measure" and self.measure.p1 is not None:
                self.measure.clear_temp()
            else:
                self.set_draw_tool(None)
            return True
        if key == Qt.Key.Key_Escape and self.nodes.active:
            self.nodes.exit()
            return True
        if self.drawing.key(event):                    # dimensions saisies pendant un tracé
            return True
        if self.nodes.active and key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.nodes.delete_key()
            return True
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self.items.select_all_active()
            return True
        zoom = shortcuts.zoom_direction(event)
        if zoom:
            (self.navigation.zoom_in if zoom > 0 else self.navigation.zoom_out)()
            return True
        command = shortcuts.key_command(event)
        if command is not None:
            self.command_requested.emit(command)
            return True
        nudge = shortcuts.arrow_nudge(event)
        if nudge is not None and self.items.selected():
            self.nudge_requested.emit(*nudge)
            return True
        return False

    # -- menu du clic droit

    def contextMenuEvent(self, event):
        """Clic droit : actions sur la sélection (calque, taille, groupe…) et, toujours, « Ajouter une forme »
        à l'endroit cliqué, y compris sur un canevas vide."""
        if time.monotonic() < self._context_menu_blocked_until:
            return                                     # le clic droit vient d'annuler un outil de dessin
        selected = self.items.selected()
        if not selected:
            item_at = self.itemAt(event.pos())
            if isinstance(item_at, VectorGraphicsItem):
                item_at.setSelected(True)
                selected = [item_at]
        click_mm = self.scene_to_mm(self.mapToScene(event.pos()))
        build_context_menu(self, selected, click_mm).exec(event.globalPos())
