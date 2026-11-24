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
from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger
from laser_studio.i18n import tr
from laser_studio.controllers.stencil_import import import_summary, remove_temporary_export, route_objects
from laser_studio.models.vector_objects import GroupObject, SvgPathObject, TextObject
from laser_studio.vector import arrange, placement
from laser_studio.vector import dxf as dxf_import
from laser_studio.vector.importers import dxf_to_objects
from laser_studio.vector.serial_apply import object_bounds
from laser_studio.vector.serial_duplicate import union_bounds
from laser_studio.vector.svg_extract import extract_svg_objects

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

    # -- outils

    def commands(self):
        """Action des commandes de l'onglet (VectorEditorTab.command) propres à l'éditeur ; les générateurs,
        la mise en page et la bibliothèque ont les leurs."""
        canvas = self.canvas
        commands = {
            "import": self.import_dialog, "edit": self.edit_selected, "rotate": self.rotate_selected,
            "duplicate": self.duplicate_selected, "delete": self.delete_selected, "delete_all": self.delete_all,
            "explode": canvas.explode_selected, "nodes": canvas.enter_node_edit,
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
            canvas.scene_obj.clearSelection()
            item.setSelected(True)
        else:
            canvas.discard_added_object(item)

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
        pair = self.canvas.text_follow_candidates()
        resync = bool(pair and getattr(pair[0].obj, "follow_points", None))
        if not self.canvas.make_text_follow_object():
            self.dialogs.info(tr("vector.text_follow_title"), tr("vector.text_follow_need_two"))
            return
        item, obj = self.canvas.selected_object()
        if obj is not None:
            self.properties_changed.emit(obj)
            if resync:
                self.status.emit(tr("vector.text_resynced"))
            else:
                # Ouvre tout de suite les réglages du texte (position, côté, distance...).
                self.edit_dialog(item, obj)

    def open_medal_text(self):
        """Texte de médaille : un texte en haut et un en bas, à l'intérieur du contour fermé sélectionné."""
        if self.canvas.medal_guide_item() is None:
            self.dialogs.info(tr("vector.medal_title"), tr("vector.medal_need_guide"))
            return
        values = self.forms.medal(self.layers)
        if values is not None:
            created = self.canvas.make_medal_texts(**values)
            if created:
                self.canvas.scene_obj.clearSelection()
                for item in self.canvas.scene_obj.items():
                    if getattr(item, "obj", None) in created:
                        item.setSelected(True)

    # -- liste des objets (ObjectsPanel)

    def move_objects(self, entries, step):
        """Monte (`step` > 0) ou descend des objets : [(groupe ou None, objet)]. Un objet du dessus de la
        pile change de place dans le document ; un objet d'un groupe, dans son groupe (l'ordre compte pour
        une différence). Annulable."""
        top = [obj for parent, obj in entries if parent is None]
        inside = [(parent, obj) for parent, obj in entries if parent is not None]
        self.canvas.push_undo_snapshot()
        changed = self.document.move(top, step) if top else False
        groups = []
        # Du plus haut au plus bas en montant (et l'inverse), pour qu'un objet ne bloque pas son voisin.
        for parent, obj in sorted(inside, key=lambda e: e[0].children.index(e[1]), reverse=step > 0):
            if parent.move_child(obj, step):
                changed = True
                if parent not in groups:
                    groups.append(parent)
        if groups:
            self.document.notify_changed(groups)
            self.properties_changed.emit(groups[0])
        if not changed:
            self.document.drop_last_snapshot()
        return changed

    def group_selection(self, operation):
        """Groupe la sélection (simple groupe) ou la combine (union, différence…) ; un groupe seul change
        d'opération. Renvoie le groupe, ou None."""
        group = self.canvas.combine_selected(operation)
        if group is not None:
            self.properties_changed.emit(group)
        return group

    def ungroup_selection(self):
        released = self.canvas.ungroup_selected()
        self.properties_changed.emit(released[0].obj if released else None)
        return released

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
        """Pivote l'objet sélectionné de 90°."""
        item, obj = self.canvas.selected_object()
        if obj is None:
            self.dialogs.info(tr("vector.selection_title"), tr("vector.no_selection"))
            return
        self.canvas.push_undo_snapshot()
        obj.rotation_deg = (obj.rotation_deg + 90.0) % 360.0
        self.document.notify_changed([obj])
        self.properties_changed.emit(obj)

    def duplicate_selected(self):
        self.canvas.duplicate_selected()

    def delete_selected(self):
        self.canvas.remove_selected()

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
        if layer_id and layer_id != obj.layer_id:
            self.canvas.push_undo_snapshot()
            obj.layer_id = layer_id
            self.document.notify_changed([obj])

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
            objects = extract_svg_objects(path, default_layer.id, self.machine.bed_h)
        except Exception as e:
            self.dialogs.error(tr("vector.svg_error_title"), tr("vector.svg_error").format(error=e))
            return
        if not objects:
            self.dialogs.info(tr("vector.svg_empty_title"), tr("vector.svg_empty"))
            return
        if not self.import_objects(objects):
            return
        self.dialogs.info(tr("vector.svg_success_title"),
                          tr("vector.svg_success").format(count=len(objects), layer=default_layer.name))

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
                else:
                    objects = extract_svg_objects(path, default_layer.id, self.machine.bed_h, ungroup=True)
                if not objects:
                    raise ValueError(tr("vector.svg_empty"))
                stats = route_objects(objects, self.layers, default_layer.id, focal=self.machine.focal)
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
