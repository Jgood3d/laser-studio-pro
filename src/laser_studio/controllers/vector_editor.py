"""Éditeur vectoriel, côté logique : insérer et modifier des objets, importer
un SVG ou un DXF (et placer tout dessin importé), aligner, répartir, pivoter,
déplacer et redimensionner la sélection, tout supprimer. Les générateurs sont
dans controllers/generators.py, l'imbrication et la série dans
controllers/layout.py.

Il modifie le document (VectorDocument) et s'appuie sur le canevas pour la
sélection, le cadrage et les opérations propres à la vue (texte sur un
contour, médaille). Il ne construit aucune fenêtre : les boîtes de saisie
passent par EditorForms (ui/vector_editor/forms.py), les questions par
UserDialogs ; il prévient la fenêtre par signaux.

    editor = VectorEditorController(document, canvas, layers, machine, UserDialogs(window), EditorForms(window))
    editor.show_editor.connect(lambda: tabs.setCurrentWidget(vector_tab))
"""
import time

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger
from laser_studio.i18n import tr
from laser_studio.controllers.stencil_import import (
    import_summary, remove_temporary_export, route_objects, route_tree,
)
from laser_studio.models.vector_objects import IGNORED_LAYER_ID, GroupObject, ShapeObject, SvgPathObject, TextObject
from laser_studio.vector import arrange, boolean_ops, group_transform, path_ops, placement, text_follow
from laser_studio.vector.nudge import NUDGE_UNDO_WINDOW_S, nudge_step
from laser_studio.vector import dxf as dxf_import
from laser_studio.vector.importers import dxf_to_objects
from laser_studio.vector.serial_apply import object_bounds
from laser_studio.vector.serial_duplicate import union_bounds
from laser_studio.vector.svg_tree_import import import_svg_tree, svg_tree_counts

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

    # -- outils

    def commands(self):
        """Action des commandes de l'onglet (VectorEditorTab.command) propres à l'éditeur ; les générateurs,
        la mise en page et la bibliothèque ont les leurs."""
        canvas = self.canvas
        commands = {
            "import": self.import_dialog, "edit": self.edit_selected, "rotate": self.rotate_selected,
            "duplicate": self.duplicate_selected, "delete": self.delete_selected, "delete_all": self.delete_all,
            "explode": self.explode_selected, "nodes": canvas.enter_node_edit,
            "copy": self.copy_selected, "paste": self.paste_clipboard, "group": self.group_selection,
            "ungroup": self.ungroup_selection, "resize": self.resize_group,
            "text_follow": self.make_text_follow_selection, "medal": self.open_medal_text,
            "undo": canvas.undo, "redo": canvas.redo, "zoom_in": canvas.zoom_in, "zoom_out": canvas.zoom_out,
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
        self.canvas.request_recenter(items)
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
            self.canvas.exit_node_edit()
            self.canvas.load_objects([])
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
        item, obj = self.canvas.selected_object()
        if obj is None:
            self.dialogs.info(tr("vector.selection_title"), tr("vector.no_selection"))
            return
        self.edit_dialog(item, obj)

    def edit_object(self, obj):
        """Double-clic sur un objet du canevas."""
        item, current_obj = self.canvas.selected_object()
        if current_obj is not obj:
            # Sécurité : retrouve l'item correspondant si la sélection n'est pas
            # encore synchronisée au moment du double-clic.
            for it in self.canvas.scene_obj.items():
                if getattr(it, "obj", None) is obj:
                    item = it
                    break
        self.edit_dialog(item, obj)

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

    def make_text_follow_selection(self):
        """Fait suivre à un texte le contour d'un autre objet : sélectionner le texte ET l'objet (Maj + clic)."""
        pair = text_follow.text_follow_pair(self.selected_objects())
        resync = bool(pair and getattr(pair[0], "follow_points", None))
        text = self.make_text_follow()
        if text is None:
            self.dialogs.info(tr("vector.text_follow_title"), tr("vector.text_follow_need_two"))
            return
        self.properties_changed.emit(text)
        if resync:
            self.status.emit(tr("vector.text_resynced"))
        else:
            # Ouvre tout de suite les réglages du texte (position, côté, distance...).
            self.edit_dialog(self.canvas.item_for(text), text)

    def make_text_follow(self):
        """Fait suivre au texte sélectionné le contour de l'autre objet sélectionné. Le contour est COPIÉ dans
        le texte : l'objet guide n'est pas modifié (on peut le garder pour la découpe ou le supprimer). Si le
        texte suivait déjà un contour, ses réglages (position, côté, distance) sont conservés : c'est une
        resynchronisation. Renvoie le texte, ou None si la sélection ne convient pas."""
        pair = text_follow.text_follow_pair(self.selected_objects())
        if pair is None:
            return None
        text, guide = pair
        pts = text_follow.follow_path(guide)
        if pts is None:
            return None
        self.canvas.push_undo_snapshot()
        text_follow.apply_follow(text, guide, pts, keep_settings=text_follow.follows_a_path(text))
        self.document.notify_changed([text])
        self.canvas.select_objects([text])
        return text

    def resync_text_guide(self, text, push_undo=True):
        """Recopie le contour de l'objet guide dans le texte (le guide a bougé ou changé de taille), en
        gardant la position, le côté et la distance. Renvoie False si le guide n'existe plus."""
        guide = text_follow.linked_guide(text, self.document.objects)
        pts = text_follow.follow_path(guide) if guide is not None else None
        if pts is None:
            return False
        if push_undo:
            self.canvas.push_undo_snapshot()
        text_follow.apply_follow(text, guide, pts, keep_settings=True)
        self.document.notify_changed([text])
        return True

    def resync_linked_texts(self, guides):
        """Resynchronise (sans nouvelle étape d'annulation) les textes liés aux objets `guides` : appelé quand
        on vient de les déplacer ou de les modifier à la souris. Renvoie le nombre de textes recalés."""
        ids = {o.id for o in guides if not isinstance(o, TextObject)}
        texts = [o for o in self.document.objects
                 if isinstance(o, TextObject) and getattr(o, "follow_guide_id", None) in ids]
        return sum(1 for text in texts if self.resync_text_guide(text, push_undo=False))

    def open_medal_text(self):
        """Texte de médaille : un texte en haut et un en bas, à l'intérieur du contour fermé sélectionné."""
        guide = text_follow.medal_guide(self.selected_objects())
        if guide is None:
            self.dialogs.info(tr("vector.medal_title"), tr("vector.medal_need_guide"))
            return
        values = self.forms.medal(self.layers)
        if values is None:
            return
        pts = text_follow.closed_follow_path(guide)
        self.canvas.push_undo_snapshot()
        created = text_follow.medal_texts(guide, pts, **values)
        for obj in created:
            self.document.add(obj)
        if created:
            self.canvas.select_objects(created)

    # -- liste des objets (ObjectsPanel)

    def move_objects(self, entries, step):
        """Monte (`step` > 0) ou descend des objets : [(groupe ou None, objet)]. Un objet du dessus de la
        pile change de place dans le document ; un objet d'un groupe, dans son groupe (l'ordre compte pour
        une différence). Annulable."""
        top = [obj for parent, obj in entries if parent is None]
        inside = [(parent, obj) for parent, obj in entries if parent is not None]
        self.canvas.push_undo_snapshot()
        changed = self.document.move(top, step) if top else False
        tops = []
        # Du plus haut au plus bas en montant (et l'inverse), pour qu'un objet ne bloque pas son voisin.
        for parent, obj in sorted(inside, key=lambda e: e[0].children.index(e[1]), reverse=step > 0):
            if parent.move_child(obj, step):
                changed = True
                top = self._refresh_ancestors(obj)
                if top not in tops:
                    tops.append(top)
        if tops:
            self.document.notify_changed(tops)
            self.properties_changed.emit(tops[0])
        if not changed:
            self.document.drop_last_snapshot()
        return changed

    def group_selection(self, operation=boolean_ops.GROUP):
        """Groupe la sélection (simple groupe) ou la combine (union, différence…) ; un groupe seul change
        d'opération. Renvoie le groupe, ou None."""
        objects = self.selected_objects()
        if len(objects) == 1 and isinstance(objects[0], GroupObject):
            group = objects[0]
            self.set_group_operation(group, operation)
        else:
            group = self._group(objects, operation)
        if group is not None:
            self.properties_changed.emit(group)
        return group

    def _group(self, objects, operation):
        """Groupe `objects` (au moins 2) en un GroupObject : chaque objet reste entier (un texte redevient un
        texte modifiable au dégroupage) et le groupe se manipule d'un bloc. Avec une opération booléenne
        (union, différence…), les objets ne forment plus qu'un tracé, rempli sur le calque de celui du
        dessous. Le groupe prend la place du plus haut des objets dans l'empilement. Annulable."""
        if len(objects) < 2:
            return None
        order = {id(o): i for i, o in enumerate(self.document.objects)}
        objects = sorted(objects, key=lambda o: order.get(id(o), 0))
        group = GroupObject(objects, operation=operation)
        top = max(order[id(o)] for o in objects)
        self.canvas.push_undo_snapshot()
        self.document.replace(objects, [group])
        # À la place du plus haut des objets groupés, pas tout en haut de la pile.
        above = sum(1 for o in self.document.objects[:-1] if order.get(id(o), -1) > top)
        for _ in range(above):
            self.document.move([group], -1)
        self.canvas.select_objects([group])
        return group

    def set_group_operation(self, group, operation):
        """Change l'opération d'un groupe (simple groupe, union, différence…). Annulable. True si changée."""
        if not isinstance(group, GroupObject) or group.operation == operation:
            return False
        self.canvas.push_undo_snapshot()
        group.set_operation(operation)
        self.document.notify_changed([group])
        return True

    def ungroup_selection(self):
        """Dégroupe la sélection : un groupe rend ses objets, à leur place (un texte redevient un texte) ;
        un tracé importé est séparé en sous-tracés indépendants. Annulable. Renvoie les nouveaux objets."""
        targets = [o for o in self.selected_objects() if isinstance(o, GroupObject) or path_ops.can_ungroup(o)]
        if not targets:
            return []
        self.canvas.push_undo_snapshot()
        released = []
        for obj in targets:
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
                    continue                      # rien d'utile à séparer : l'objet reste tel quel
                self.document.replace([obj], children)
            released += children
        self.canvas.select_objects(released)
        self.properties_changed.emit(released[0] if released else None)
        return released

    def explode_selected(self):
        """Découpe chaque objet sélectionné en segments indépendants (une ligne = un objet) : supprimer une
        seule encoche ou un seul trait, puis le redessiner. Annulable. Renvoie les segments."""
        self.canvas.exit_node_edit()
        targets = [o for o in self.selected_objects() if path_ops.can_explode(o)]
        if not targets:
            return []
        self.canvas.push_undo_snapshot()
        segments = []
        for obj in targets:
            parts = path_ops.explode_object(obj)
            if parts:
                self.document.replace([obj], parts)
                segments += parts
        self.canvas.select_objects(segments)
        return segments

    def rename_object(self, obj, name):
        """Nom donné dans la liste des objets (vide : nom par défaut). Annulable."""
        name = name.strip()
        if name == (getattr(obj, "name", "") or ""):
            return
        self.canvas.push_undo_snapshot()
        obj.name = name
        self.document.notify_changed([obj])

    # -- sélection

    def rotate_selected(self):
        """Pivote chaque objet sélectionné de 90° sur lui-même (bouton, clic droit). Annulable."""
        objects = self.selected_objects()
        if not objects:
            self.dialogs.info(tr("vector.selection_title"), tr("vector.no_selection"))
            return
        self.canvas.push_undo_snapshot()
        group_transform.rotate_quarter(objects)
        self.document.notify_changed(objects)
        self.properties_changed.emit(objects[0])

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
        self.canvas.exit_node_edit()
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
        self.canvas.push_undo_snapshot()
        group_transform.assign_layer(objects, layer_id)
        self.document.notify_changed(objects)
        self.properties_changed.emit(objects[0])

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
        self.canvas.push_undo_snapshot()
        group_transform.resize_group(objects, *size)
        self.document.notify_changed(objects)
        self.properties_changed.emit(objects[0])

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
        canvas.exit_node_edit()
        canvas.push_undo_snapshot()
        canvas.load_objects([])
        self.properties_changed.emit(None)

    def set_selected_layer(self, layer_id):
        """Calque choisi dans le panneau des propriétés, pour l'objet sélectionné."""
        item, obj = self.canvas.selected_object()
        if obj is None:
            return
        if not layer_id or layer_id == obj.layer_id:
            return
        self.canvas.push_undo_snapshot()
        if layer_id == IGNORED_LAYER_ID:
            obj.set_ignored(True)
        else:
            # Un groupe passe tous ses objets sur ce calque.
            obj.set_layer(layer_id)
        self.document.notify_changed([obj])

    def set_object_visible(self, obj, visible):
        """Œil de la liste des objets : masque l'objet à l'affichage (il reste gravé), qu'il soit en haut de
        la pile ou dans un groupe (le groupe est redessiné sans lui). Annulable."""
        if obj.is_hidden() == (not visible):
            return
        self.canvas.push_undo_snapshot()
        obj.hidden = not visible
        self.document.notify_changed([self._refresh_ancestors(obj)])

    def toggle_ignored(self, obj):
        """Bouton « X » de la liste des objets : met l'objet sur le calque « Ignoré » (ni affiché, ni gravé,
        ni découpé) en retenant son calque, ou le lui rend. Un groupe ignore ou rend tous ses objets, chacun
        retrouvant son propre calque ; les groupes qui contiennent l'objet sont recalculés. Annulable."""
        self.canvas.push_undo_snapshot()
        fallback = self.layers.layers[0].id if self.layers.layers else None
        obj.set_ignored(not obj.is_ignored(), fallback)
        self.document.notify_changed([self._refresh_ancestors(obj)])

    def delete_object(self, group, obj):
        """Poubelle de la liste des objets : supprime `obj` du dessin, ou le retire de son groupe `group`
        (un groupe vidé disparaît à son tour). Annulable."""
        self.canvas.exit_node_edit()
        self.canvas.push_undo_snapshot()
        if group is None:
            self.document.remove(obj)
            self.properties_changed.emit(None)
            return
        chain = self._ancestors(obj)
        # Du groupe de l'objet vers le haut : chaque groupe vidé est retiré de son propre parent.
        target = obj
        for level in range(len(chain) - 1, -1, -1):
            parent = chain[level]
            parent.children = [child for child in parent.children if child is not target]
            parent.child_ignored_changed()
            if parent.children:
                for upper in reversed(chain[:level]):
                    upper.child_ignored_changed()
                self.document.notify_changed([chain[0]])
                self.properties_changed.emit(chain[0])
                return
            target = parent
        self.document.remove(target)                   # tout le groupe du dessus s'est vidé
        self.properties_changed.emit(None)

    def _ancestors(self, target):
        """Groupes qui contiennent `target`, du dessus de la pile jusqu'à son groupe ([] en haut)."""
        def search(objects, chain):
            for obj in objects:
                if obj is target:
                    return chain
                if isinstance(obj, GroupObject):
                    found = search(obj.children, chain + [obj])
                    if found is not None:
                        return found
            return None
        return search(self.document.objects, []) or []

    def _refresh_ancestors(self, obj):
        """Recalcule les groupes qui contiennent `obj` (calque, tracé), du plus proche au plus haut ;
        renvoie l'objet du document qui le contient (lui-même s'il est en haut de la pile)."""
        chain = self._ancestors(obj)
        for group in reversed(chain):
            group.child_ignored_changed()
        return chain[0] if chain else obj

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
        self.canvas.push_undo_snapshot()
        for obj in objects:
            obj.x_mm += delta_x
            obj.y_mm += delta_y
        if len(objects) == 1:
            objects[0].rotation_deg = rotation_deg
        self.document.notify_changed(objects)

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
        self.canvas.push_undo_snapshot()
        arrange.resize_shape(obj, width_mm, height_mm, anchor_id)
        self.document.notify_changed([obj])
        return obj

    def align(self, mode):
        """Aligne les objets sélectionnés les uns sur les autres (au moins 2)."""
        objects = self.selected_objects()
        if len(objects) < 2:
            return
        offsets = arrange.align_offsets(objects, mode)
        self.canvas.push_undo_snapshot()
        for obj, (dx, dy) in zip(objects, offsets):
            obj.x_mm += dx
            obj.y_mm += dy
        self.document.notify_changed(objects)
        self.properties_changed.emit(objects[0])

    def distribute(self, axis):
        """Répartit les objets sélectionnés à espacement égal (au moins 3)."""
        objects = self.selected_objects()
        if len(objects) < 3:
            return
        moves = arrange.distribute_offsets(objects, axis)
        self.canvas.push_undo_snapshot()
        for obj, delta in moves:
            if axis == "h":
                obj.x_mm += delta
            else:
                obj.y_mm += delta
        self.document.notify_changed(objects)
        self.properties_changed.emit(objects[0])

    # -- import SVG / DXF

    def import_dialog(self):
        """Importe un SVG ou un DXF choisi par l'utilisateur. Par défaut le dessin
        arrive **groupé** (un objet, ou un par calque DXF) : on le manipule
        d'un bloc ; clic droit → Dégrouper pour séparer les tracés."""
        if not self.require_layers():
            return
        path = self.dialogs.open_file(tr("vector.import_title"), tr("vector.import_filter"))
        if path:
            self.import_file(path)

    def import_file(self, path):
        """Importe le fichier SVG ou DXF `path` (aussi appelé par le glisser-déposer)."""
        if not self.require_layers():
            return
        default_layer = self.layers.default_svg_layer()
        if path.lower().endswith(".dxf"):
            self._import_dxf(path, default_layer)
            return
        try:
            # Calques et groupes du fichier gardés ; calque de chaque objet d'après sa couleur ; ce qui est
            # masqué dans le fichier arrive sur le calque « Ignoré » (vector/svg_tree_import.py).
            objects = import_svg_tree(path, lambda role: self.layers.layer_for_role(role).id if role
                                      else default_layer.id, self.machine.bed_h)
        except Exception as e:
            self.dialogs.error(tr("vector.svg_error_title"), tr("vector.svg_error").format(error=e))
            return
        if not objects or all(obj.is_ignored() for obj in objects):
            self.dialogs.info(tr("vector.svg_empty_title"), tr("vector.svg_empty"))
            return
        if not self.import_objects(objects):
            return
        self.dialogs.info(tr("vector.svg_success_title"),
                          tr("vector.svg_tree_success").format(**svg_tree_counts(objects, self.layers)))

    def import_stencil_export(self, path):
        """Fichier SVG ou DXF exporté par Stencil Studio : objets rangés dans les calques de LSP d'après
        leur calque d'origine (controllers/stencil_import.py), en une étape d'annulation. En cas
        d'échec, import standard (import_file), qui explique le problème. Le fichier temporaire est
        ensuite supprimé."""
        try:
            stats = None
            lower = path.lower()
            if lower.endswith((".dxf", ".svg")) and self.layers.layers:
                default_layer = self.layers.default_svg_layer()
                if lower.endswith(".dxf"):
                    objects = dxf_to_objects(dxf_import.read_dxf(path), default_layer.id)
                    route = route_objects
                else:
                    # Même lecture que « Importer » ; les groupes de l'export (CUT, ENGRAVE…) sont gardés.
                    objects = import_svg_tree(path, lambda _role: default_layer.id, self.machine.bed_h)
                    route = route_tree
                if not objects:
                    raise ValueError(tr("vector.svg_empty"))
                stats = route(objects, self.layers, default_layer.id, focal=self.machine.focal)
                if not self.import_objects(objects):
                    return
            else:
                self.import_file(path)
            self.status.emit(import_summary(path, stats))
        except Exception as e:  # fichier illisible ou vide : l'import standard affiche l'erreur
            self.status.emit(tr("stencil.import_fallback").format(error=e))
            self.import_file(path)
        finally:
            remove_temporary_export(path)

    def _import_dxf(self, path, default_layer):
        """Import d'un DXF (texte ASCII) : tracés regroupés par calque DXF, calque LSP par défaut."""
        try:
            drawing = dxf_import.read_dxf(path)
        except dxf_import.DxfError as e:
            key = f"vector.dxf_err.{e.code}"
            text = tr(key)
            if text == key:
                text = tr("vector.dxf_error").format(error=e)
            else:
                text = text.format(**e.info) if e.info else text
            self.dialogs.error(tr("vector.dxf_title"), text)
            return
        except Exception as e:
            self.dialogs.error(tr("vector.dxf_title"), tr("vector.dxf_error").format(error=e))
            return
        skipped = ", ".join(f"{kind} x{count}" for kind, count in sorted(drawing.skipped.items()))
        objects = dxf_to_objects(drawing, default_layer.id)
        if not objects:
            message = tr("vector.dxf_empty")
            if skipped:
                message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
            self.dialogs.info(tr("vector.dxf_title"), message)
            return
        if not self.import_objects(objects):
            return
        message = tr("vector.dxf_success").format(
            count=len(objects), layer=default_layer.name, unit=dxf_import.units_label(drawing))
        if skipped:
            message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
        self.dialogs.info(tr("vector.dxf_title"), message)
