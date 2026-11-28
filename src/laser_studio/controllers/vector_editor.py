"""Éditeur vectoriel, côté logique : insérer et modifier des objets, placer un dessin importé, transformer la
sélection (pivoter, aligner, répartir, déplacer, redimensionner, calque), dupliquer, copier, coller, supprimer.

Il compose des actions spécialisées, qui le reçoivent comme contexte (document, canevas, calques, boîtes de
dialogue, signaux) :
- importer (vector_import.py) : SVG, DXF, export de Stencil Studio ;
- grouping (grouping_actions.py) : grouper, combiner, dégrouper, éclater ;
- text_follow (text_follow_actions.py) : texte sur contour, texte de médaille ;
- object_list (object_list_actions.py) : liste des objets (ordre, nom, œil, ignorer, supprimer dans un groupe).
Les générateurs sont dans controllers/generators.py, l'imbrication et la série dans controllers/layout.py.

Il modifie le document (VectorDocument) et s'appuie sur le canevas pour la sélection et le cadrage. Il ne
construit aucune fenêtre : les boîtes de saisie passent par EditorForms (ui/vector_editor/forms.py), les
questions par UserDialogs ; il prévient la fenêtre par signaux.

    editor = VectorEditorController(document, canvas, layers, machine, UserDialogs(window), EditorForms(window))
    editor.show_editor.connect(lambda: tabs.setCurrentWidget(vector_tab))
    with editor.changing(objects):          # une étape d'annulation, vues et panneau prévenus
        ...
"""
import time
from contextlib import contextmanager

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger
from laser_studio.i18n import tr
from laser_studio.controllers.grouping_actions import GroupingActions
from laser_studio.controllers.object_list_actions import ObjectListActions
from laser_studio.controllers.text_follow_actions import TextFollowActions
from laser_studio.controllers.vector_import import VectorImporter
from laser_studio.models.vector_objects import IGNORED_LAYER_ID, GroupObject, ShapeObject, SvgPathObject, TextObject
from laser_studio.vector import arrange, group_transform, placement
from laser_studio.vector.nudge import NUDGE_UNDO_WINDOW_S, nudge_step
from laser_studio.vector.serial_apply import object_bounds
from laser_studio.vector.serial_duplicate import union_bounds

log = get_logger()


class VectorEditorController(QObject):
    """Logique de l'éditeur vectoriel.

    `document` : VectorDocument. `canvas` : VectorCanvasView (sélection,
    cadrage, aperçu des boîtes de saisie). `layers` : LayersModel.
    `machine` : MachineConfig (taille du plateau). `dialogs` : UserDialogs.
    `forms` : EditorForms (boîtes de saisie du texte, des formes, de la
    médaille).

    État de l'interface, lu à chaque usage :
    - overscan_margin(largeur_mm) : marge à gauche (mm) laissée au
      surbalayage devant un dessin importé de cette largeur (0 s'il est
      désactivé).

    Signaux :
    - show_editor() : afficher l'onglet de l'éditeur (après un import, un
      générateur) ;
    - properties_changed(objet ou None) : la sélection a changé de forme,
      de place ou de calque (panneau des propriétés à remettre à jour) ;
    - status(texte) : message pour la barre d'état ;
    - draw_tool_changed(outil ou None) : outil de la souris actif (boutons
      de l'onglet à cocher).
    """

    show_editor = pyqtSignal()
    properties_changed = pyqtSignal(object)
    status = pyqtSignal(str)
    draw_tool_changed = pyqtSignal(object)

    def __init__(self, document, canvas, layers, machine, dialogs, parent=None, *, forms=None,
                 overscan_margin=lambda width_mm: 0.0):
        super().__init__(parent)
        self.document = document
        self.canvas = canvas
        self.layers = layers
        self.machine = machine
        self.dialogs = dialogs
        self.forms = forms
        self._overscan_margin = overscan_margin
        self._last_nudge_time = -1e9          # flèches : pressions rapprochées = une seule étape d'annulation
        self.importer = VectorImporter(self)
        self.grouping = GroupingActions(self)
        self.text_follow = TextFollowActions(self)
        self.object_list = ObjectListActions(self)

    @contextmanager
    def changing(self, objects, show=True):
        """Modification de `objects` dans le bloc : une étape d'annulation prise avant ; après, les vues sont
        prévenues (notify_changed) et, avec `show`, le panneau des propriétés montre le premier objet."""
        self.canvas.push_undo_snapshot()
        yield objects
        self.document.notify_changed(objects)
        if show and objects:
            self.properties_changed.emit(objects[0])

    # -- outils

    def commands(self):
        """Action des commandes de l'onglet (VectorEditorTab.command) propres à l'éditeur ; les générateurs,
        la mise en page et la bibliothèque ont les leurs."""
        canvas = self.canvas
        commands = {
            "import": self.importer.open_dialog, "edit": self.edit_selected, "rotate": self.rotate_selected,
            "duplicate": self.duplicate_selected, "delete": self.delete_selected, "delete_all": self.delete_all,
            "explode": self.grouping.explode_selection, "nodes": canvas.nodes.enter,
            "copy": self.copy_selected, "paste": self.paste_clipboard, "group": self.grouping.group_selection,
            "ungroup": self.grouping.ungroup_selection, "resize": self.resize_group,
            "text_follow": self.text_follow.follow_selection, "medal": self.text_follow.medal,
            "undo": canvas.document.undo, "redo": canvas.document.redo, "zoom_in": canvas.navigation.zoom_in,
            "zoom_out": canvas.navigation.zoom_out,
            "text": self.insert_text, "shape": self.insert_shape,
            "distribute_h": lambda: self.distribute("h"), "distribute_v": lambda: self.distribute("v"),
        }
        for edge in ("left", "center_h", "right", "top", "middle_v", "bottom"):
            commands[f"align_{edge}"] = lambda edge=edge: self.align(edge)
        return commands

    def choose_draw_tool(self, tool):
        """Outil de dessin à la souris sur le canevas.

        tool: None/'select', 'line', 'rect', 'circle', 'ellipse', 'measure'. Rectangle : 3 points. Cercle (du
        centre vers le rayon) et ellipse (d'un coin du cadre à l'autre) : un seul clic-glisser. Échap ou clic
        droit annule l'outil. Sans calque, l'outil n'est pas activé (message)."""
        resolved = None if tool in (None, "select") else tool
        if resolved and not self.require_layers():
            resolved = None
        layer = self.layers.default_svg_layer() if self.layers.layers else None
        self.canvas.set_draw_tool(resolved, layer_id=layer.id if layer else None)
        self.draw_tool_changed.emit(resolved)

    def require_layers(self):
        """Vrai s'il existe au moins un calque ; sinon, le dit."""
        if self.layers.layers:
            return True
        self.dialogs.warning(tr("vector.no_layer_title"), tr("vector.no_layer_body"))
        return False

    def selected_objects(self):
        return [item.obj for item in self.canvas.selected_items_vector()]

    def add_objects(self, objects, show=True, snapshot=True):
        """Ajoute `objects` (une étape d'annulation, sauf `snapshot` faux : déjà prise), affiche l'éditeur
        si `show` et cadre la vue dessus. Renvoie leurs éléments graphiques."""
        if snapshot:
            self.canvas.push_undo_snapshot()
        items = [self.canvas.add_object(obj) for obj in objects]
        if show:
            self.show_editor.emit()
        self.canvas.navigation.request_recenter(items)
        return items

    def import_objects(self, objects, show=True, keep_position=False):
        """Ajoute un dessin importé (fichier, bibliothèque, générateur, Stencil Studio, vectorisation) en le
        plaçant (vector/placement.py) : coin bas-gauche à la marge du surbalayage ; si l'éditeur contient
        déjà des objets, l'utilisateur choisit d'ajouter sans y toucher, de les remplacer, ou de placer le
        dessin à leur droite ou au-dessus. `keep_position` : le dessin a déjà sa place (puzzle calé sur
        l'image) ; « ajouter » et « remplacer » ne le déplacent pas. Une seule étape d'annulation. Renvoie
        les éléments ajoutés (liste vide si l'utilisateur annule)."""
        new_bounds = union_bounds([object_bounds(o) for o in objects])
        if new_bounds is None:
            return self.add_objects(objects, show)
        existing = self.canvas.objects
        mode = placement.ADD
        if existing:
            mode = self.dialogs.choose(tr("vector.place_title"), tr("vector.place_question").format(
                count=len(existing)), [(key, tr(f"vector.place_{key}")) for key in placement.MODES])
            if mode is None:
                return []
        existing_bounds = union_bounds([object_bounds(o) for o in existing]) if existing else None
        if keep_position and (existing_bounds is None or mode in (placement.ADD, placement.REPLACE)):
            dx = dy = 0.0
        else:
            margin_x = self._overscan_margin(new_bounds[2] - new_bounds[0])
            dx, dy = placement.placement_offset(new_bounds, existing_bounds, mode, margin_x=margin_x)
        for obj in objects:
            obj.x_mm += dx
            obj.y_mm += dy
        self.canvas.push_undo_snapshot()
        if mode == placement.REPLACE:
            self.canvas.nodes.exit()
            self.canvas.document.load([])
            self.properties_changed.emit(None)
        return self.add_objects(objects, show, snapshot=False)

    # -- insérer, modifier

    def insert_text(self, x_mm=None, y_mm=None):
        """Insère un texte. Si x_mm/y_mm sont donnés (clic droit sur le canevas),
        la boîte de dialogue est pré-remplie avec cette position."""
        if not self.require_layers():
            return
        # Aperçu en direct : le texte est posé sur le canevas avant d'ouvrir la boîte, et retiré si on annule.
        engrave = self.layers.engrave_layer()
        layer = engrave if engrave is not None else self.layers.layers[0]
        obj = TextObject(text=tr("vector.dlg.text_default"), layer_id=layer.id,
                         x_mm=10.0 if x_mm is None else x_mm, y_mm=10.0 if y_mm is None else y_mm)
        canvas = self.canvas
        canvas.push_undo_snapshot()
        item = canvas.add_object(obj)
        if self.forms.text(self.layers, obj, on_preview=lambda: (item.refresh(), canvas.follow_handle.sync()),
                           is_new=True):
            item.refresh()
            canvas.select_objects([obj])
        else:
            # Annulé : l'objet de l'aperçu et l'étape d'annulation prise juste avant disparaissent.
            self.document.remove(obj)
            self.document.drop_last_snapshot()
            canvas.follow_handle.sync()

    def insert_shape(self):
        if not self.require_layers():
            return
        obj = self.forms.shape(self.layers)
        if obj is not None:
            self.canvas.push_undo_snapshot()
            self.canvas.add_object(obj)

    def edit_selected(self):
        item, obj = self.canvas.items.selected_object()
        if obj is None:
            self.dialogs.info(tr("vector.selection_title"), tr("vector.no_selection"))
            return
        self.edit_dialog(item, obj)

    def edit_object(self, obj):
        """Double-clic sur un objet du canevas."""
        self.edit_dialog(self.canvas.item_for(obj), obj)

    def edit_dialog(self, item, obj):
        """Boîte de modification de l'objet : texte, tracé importé ou forme."""
        canvas = self.canvas
        if isinstance(obj, TextObject):
            # La boîte remet le texte dans son état d'origine avant d'appliquer : l'annulation est prise entre les deux.
            if self.forms.text(self.layers, obj, on_preview=lambda: (item.refresh(), canvas.follow_handle.sync()),
                               before_apply=canvas.push_undo_snapshot):
                item.refresh()
                self.properties_changed.emit(obj)
            canvas.follow_handle.sync()
        elif isinstance(obj, GroupObject):
            # Un groupe n'a pas de boîte : ses objets se modifient une fois dégroupés.
            self.status.emit(tr("objects.group_edit_hint"))
        elif isinstance(obj, SvgPathObject):
            if self.forms.svg_properties(self.layers, obj, tr("vector.svg_properties"),
                                         before_apply=canvas.push_undo_snapshot):
                item.refresh()
                self.properties_changed.emit(obj)
        else:
            if self.forms.shape(self.layers, obj, before_apply=canvas.push_undo_snapshot) is not None:
                item.refresh()
                self.properties_changed.emit(obj)

    # -- sélection

    def rotate_selected(self):
        """Pivote chaque objet sélectionné de 90° sur lui-même (bouton, clic droit). Annulable."""
        objects = self.selected_objects()
        if not objects:
            self.dialogs.info(tr("vector.selection_title"), tr("vector.no_selection"))
            return
        with self.changing(objects):
            group_transform.rotate_quarter(objects)

    def duplicate_selected(self):
        """Copie décalée de chaque objet sélectionné (Ctrl+D). Annulable. Renvoie les copies."""
        objects = self.selected_objects()
        if not objects:
            return []
        self.canvas.push_undo_snapshot()
        return self.document.duplicate(objects)

    def delete_selected(self):
        """Supprime les objets sélectionnés (Suppr). Annulable."""
        objects = self.selected_objects()
        self.canvas.nodes.exit()
        if not objects:
            return
        self.canvas.push_undo_snapshot()
        for obj in objects:
            self.document.remove(obj)
        self.properties_changed.emit(None)

    def copy_selected(self):
        """Ctrl+C : copie les objets sélectionnés dans le presse-papiers de l'éditeur (pas celui du système)."""
        self.document.copy(self.selected_objects())

    def paste_clipboard(self):
        """Ctrl+V : colle les objets copiés, décalés pour rester distincts de l'original, et les sélectionne."""
        if not self.document.has_clipboard():
            return []
        self.canvas.push_undo_snapshot()
        pasted = self.document.paste()
        self.canvas.select_objects(pasted)
        return pasted

    def nudge_selection(self, dir_x, dir_y, shift=False, alt=False):
        """Flèches du clavier : déplace la sélection de 1 mm (Maj : 10 mm ; Alt : 0,1 mm). Les pressions
        rapprochées (touche maintenue) ne comptent que pour UN « Annuler »."""
        objects = self.selected_objects()
        if not objects:
            return False
        step = nudge_step(shift=shift, alt=alt)
        now = time.monotonic()
        if now - self._last_nudge_time > NUDGE_UNDO_WINDOW_S:
            self.canvas.push_undo_snapshot()
        self._last_nudge_time = now
        for obj in objects:
            obj.x_mm += dir_x * step
            obj.y_mm += dir_y * step
        self.document.notify_changed(objects)
        return True

    def assign_layer(self, layer_id):
        """Clic droit › Assigner au calque : la sélection (et tous les objets de ses groupes). Annulable."""
        objects = self.selected_objects()
        if not objects:
            return
        with self.changing(objects):
            group_transform.assign_layer(objects, layer_id)

    def resize_group(self):
        """Redimensionne toute la sélection comme un groupe, en mm : proportions et positions relatives
        conservées, coin bas-gauche fixe. Taille demandée par une fenêtre (EditorForms.group_resize)."""
        objects = self.selected_objects()
        if not objects:
            return
        _x, _y, width, height = group_transform.group_bounds(objects)
        size = self.forms.group_resize(max(width, 1e-6), max(height, 1e-6))
        if size is None:
            return
        with self.changing(objects):
            group_transform.resize_group(objects, *size)

    def add_basic_shape(self, kind, cx_mm, cy_mm, size_mm=20.0):
        """Clic droit › Ajouter : une ligne, un carré ou un cercle centré sur (cx_mm, cy_mm), sur le calque
        SVG par défaut, sélectionné. Renvoie l'objet, ou None sans calque."""
        if not self.require_layers():
            return None
        layer_id = self.layers.default_svg_layer().id
        if kind == "Ligne":
            obj = ShapeObject(shape_type="Ligne", width_mm=size_mm * 1.5, height_mm=0.1,
                              layer_id=layer_id, x_mm=cx_mm - size_mm * 0.75, y_mm=cy_mm)
        else:
            shape_type = "Ellipse" if kind == "Cercle" else "Rectangle"
            obj = ShapeObject(shape_type=shape_type, width_mm=size_mm, height_mm=size_mm,
                              layer_id=layer_id, x_mm=cx_mm - size_mm / 2.0, y_mm=cy_mm - size_mm / 2.0)
        self.canvas.push_undo_snapshot()
        self.document.add(obj)
        self.canvas.select_objects([obj])
        return obj

    def delete_all(self):
        """« Tout supprimer » : vide l'éditeur, après confirmation. Annulable d'un coup."""
        canvas = self.canvas
        if not canvas.objects:
            return
        if not self.dialogs.confirm_default_no(
                tr("vector.delete_all_title"), tr("vector.delete_all_question").format(count=len(canvas.objects))):
            return
        canvas.nodes.exit()
        canvas.push_undo_snapshot()
        canvas.document.load([])
        self.properties_changed.emit(None)

    def set_selected_layer(self, layer_id):
        """Calque choisi dans le panneau des propriétés, pour l'objet sélectionné."""
        item, obj = self.canvas.items.selected_object()
        if obj is None:
            return
        if not layer_id or layer_id == obj.layer_id:
            return
        with self.changing([obj], show=False):
            if layer_id == IGNORED_LAYER_ID:
                obj.set_ignored(True)
            else:
                obj.set_layer(layer_id)        # un groupe passe tous ses objets sur ce calque

    def move_selection_to(self, left_mm, bottom_mm, rotation_deg):
        """Déplace l'objet ou le groupe sélectionné : coin bas-gauche de
        l'ensemble en (left_mm, bottom_mm) ; un objet seul prend aussi
        `rotation_deg` (la rotation d'un groupe n'est pas modifiée)."""
        objects = self.selected_objects()
        if not objects:
            return
        current_left, current_bottom, _right, _top = arrange.group_bounds(objects)
        delta_x = left_mm - current_left
        delta_y = bottom_mm - current_bottom
        with self.changing(objects, show=False):
            for obj in objects:
                obj.x_mm += delta_x
                obj.y_mm += delta_y
            if len(objects) == 1:
                objects[0].rotation_deg = rotation_deg

    def resize_selected_shape(self, width_mm, height_mm, anchor_id=None):
        """Change la taille de la forme sélectionnée (seule) ; avec `anchor_id`,
        ce coin (ou l'origine = 1er point) reste fixe. Renvoie la forme
        modifiée, ou None si rien n'a changé."""
        objects = self.selected_objects()
        if len(objects) != 1:
            return None
        obj = objects[0]
        if getattr(obj, "kind", None) != "shape":
            return None
        if not hasattr(obj, "width_mm") or not hasattr(obj, "height_mm"):
            return None
        if abs(width_mm - obj.width_mm) < 1e-9 and abs(height_mm - obj.height_mm) < 1e-9:
            return None
        with self.changing([obj], show=False):
            arrange.resize_shape(obj, width_mm, height_mm, anchor_id)
        return obj

    def align(self, mode):
        """Aligne les objets sélectionnés les uns sur les autres (au moins 2)."""
        objects = self.selected_objects()
        if len(objects) < 2:
            return
        offsets = arrange.align_offsets(objects, mode)
        with self.changing(objects):
            for obj, (dx, dy) in zip(objects, offsets):
                obj.x_mm += dx
                obj.y_mm += dy

    def distribute(self, axis):
        """Répartit les objets sélectionnés à espacement égal (au moins 3)."""
        objects = self.selected_objects()
        if len(objects) < 3:
            return
        moves = arrange.distribute_offsets(objects, axis)
        with self.changing(objects):
            for obj, delta in moves:
                if axis == "h":
                    obj.x_mm += delta
                else:
                    obj.y_mm += delta
