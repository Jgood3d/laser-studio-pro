"""Éditeur vectoriel, côté logique : insérer et modifier des objets, importer
un SVG ou un DXF, lancer les générateurs (boîte, puzzle, boule de Noël,
porte-clés), imbrication, duplication en série, gabarit, aligner, répartir,
pivoter, déplacer et redimensionner la sélection, tout supprimer.

Il modifie le document (VectorDocument) et s'appuie sur le canevas pour la
sélection, le cadrage et les opérations propres à la vue (texte sur un
contour, médaille). Il ouvre les fenêtres des générateurs et les boîtes de
saisie (comme LibraryController ouvre la bibliothèque), pose ses questions
par UserDialogs et prévient la fenêtre par signaux.

    editor = VectorEditorController(document, canvas, layers, machine, UserDialogs(window), window)
    editor.show_editor.connect(lambda: tabs.setCurrentWidget(vector_tab))
    actions.box_generator_requested.connect(editor.open_box_generator)
"""
from contextlib import nullcontext

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QDialog

from laser_studio.i18n import tr
from laser_studio.controllers.stencil_import import import_summary, remove_temporary_export, route_objects
from laser_studio.models.vector_objects import SvgPathObject, TextObject
from laser_studio.ui.dialogs.box_generator import BoxGeneratorDialog, error_message
from laser_studio.ui.dialogs.jig import JigDialog, error_message as jig_error_message
from laser_studio.ui.dialogs.nesting import NestingDialog
from laser_studio.ui.dialogs.ornament import OrnamentGeneratorDialog
from laser_studio.ui.dialogs.ornament.dialog import error_text as ornament_error_text
from laser_studio.ui.dialogs.puzzle import PuzzleGeneratorDialog
from laser_studio.ui.dialogs.serial_duplicate import SerialDuplicateDialog
from laser_studio.ui.vector_editor.assign_layer_dialog import AssignLayerDialog
from laser_studio.ui.vector_editor.medal_dialog import MedalTextDialog
from laser_studio.ui.vector_editor.shape_dialog import ShapeInsertDialog
from laser_studio.ui.vector_editor.text_dialog import TextInsertDialog
from laser_studio.vector import arrange, box_generator, nesting, puzzle_generator
from laser_studio.vector import dxf as dxf_import
from laser_studio.vector import jig as jig_geometry
from laser_studio.vector import serial_duplicate as serial_dup
from laser_studio.vector.importers import (
    box_to_objects, decor_to_objects, dxf_to_objects, index_to_objects, jig_to_objects, keychain_to_objects,
    motif_to_objects, ornament_to_objects, puzzle_to_objects,
)
from laser_studio.vector.nesting_apply import apply_result, build_pieces
from laser_studio.vector.serial_apply import object_bounds, run_serial_duplicate
from laser_studio.vector.svg_extract import extract_svg_objects
from laser_studio.core.debug_log import get_logger

log = get_logger()

# Marge (mm) entre le bord du plateau et les pièces d'un générateur.
GENERATOR_OFFSET_MM = 10.0


class VectorEditorController(QObject):
    """Logique de l'éditeur vectoriel.

    `document` : VectorDocument. `canvas` : VectorCanvasView (sélection,
    cadrage, aperçu des boîtes de saisie). `layers` : LayersModel.
    `machine` : MachineConfig (taille du plateau). `dialogs` : UserDialogs.
    `parent` : fenêtre parente des boîtes de saisie et des générateurs.

    État de l'interface, lu à chaque usage :
    - image_frame() : (x, y, largeur, hauteur) en mm de l'image de « Graver
      une image », pour caler le puzzle dessus, ou None ;
    - busy() : gestionnaire de contexte pendant un calcul long (curseur
      d'attente).

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

    def __init__(self, document, canvas, layers, machine, dialogs, parent=None, *,
                 image_frame=lambda: None, busy=nullcontext):
        super().__init__(parent)
        self.document = document
        self.canvas = canvas
        self.layers = layers
        self.machine = machine
        self.dialogs = dialogs
        self._parent = parent
        self._image_frame = image_frame
        self._busy = busy
        # Derniers réglages de chaque fenêtre, repris à sa prochaine ouverture.
        self.box_settings = None
        self.puzzle_settings = None
        self.ornament_settings = None
        self.keychain_settings = None
        self.nesting_settings = None
        self.serial_settings = None
        self.jig_settings = None

    # -- outils

    def commands(self):
        """Action de chaque commande de l'onglet (VectorEditorTab.command), sauf la bibliothèque."""
        canvas = self.canvas
        commands = {
            "import": self.import_dialog, "box": self.open_box_generator, "puzzle": self.open_puzzle_generator,
            "ornament": self.open_ornament_generator, "keychain": self.open_keychain_generator,
            "nesting": self.open_nesting, "edit": self.edit_selected, "rotate": self.rotate_selected,
            "duplicate": self.duplicate_selected, "serial": self.open_serial_duplicate,
            "jig": self.open_jig_generator, "delete": self.delete_selected, "delete_all": self.delete_all,
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
        if resolved and not self._require_layers():
            resolved = None
        layer = self.layers.default_svg_layer() if self.layers.layers else None
        self.canvas.set_draw_tool(resolved, layer_id=layer.id if layer else None)
        self.draw_tool_changed.emit(resolved)

    def _require_layers(self):
        """Vrai s'il existe au moins un calque ; sinon, le dit."""
        if self.layers.layers:
            return True
        self.dialogs.warning(tr("vector.no_layer_title"), tr("vector.no_layer_body"))
        return False

    def selected_objects(self):
        return [item.obj for item in self.canvas.selected_items_vector()]

    def add_objects(self, objects, show=True):
        """Ajoute `objects` (une étape d'annulation), affiche l'éditeur si
        `show` et cadre la vue dessus. Renvoie leurs éléments graphiques."""
        self.canvas.push_undo_snapshot()
        items = [self.canvas.add_object(obj) for obj in objects]
        if show:
            self.show_editor.emit()
        self.canvas.request_recenter(items)
        return items

    # -- insérer, modifier

    def insert_text(self, x_mm=None, y_mm=None):
        """Insère un texte. Si x_mm/y_mm sont donnés (clic droit sur le canevas),
        la boîte de dialogue est pré-remplie avec cette position."""
        if not self._require_layers():
            return
        # Aperçu en direct : le texte est posé sur le canevas avant d'ouvrir la boîte, et retiré si on annule.
        engrave = self.layers.engrave_layer()
        layer = engrave if engrave is not None else self.layers.layers[0]
        obj = TextObject(text=tr("vector.dlg.text_default"), layer_id=layer.id,
                         x_mm=10.0 if x_mm is None else x_mm, y_mm=10.0 if y_mm is None else y_mm)
        canvas = self.canvas
        canvas.push_undo_snapshot()
        item = canvas.add_object(obj)
        dialog = TextInsertDialog(self.layers, text_obj=obj, parent=self._parent, is_new=True,
                                  on_preview=lambda: (item.refresh(), canvas._sync_follow_handle()))
        if dialog.exec():
            # La boîte a remis le texte dans son état d'origine : on applique les réglages choisis.
            dialog.get_object()
            item.refresh()
            canvas.scene_obj.clearSelection()
            item.setSelected(True)
        else:
            canvas.discard_added_object(item)

    def insert_shape(self):
        if not self._require_layers():
            return
        dialog = ShapeInsertDialog(self.layers, parent=self._parent)
        if dialog.exec():
            obj = dialog.get_object()
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
            dialog = TextInsertDialog(self.layers, text_obj=obj, parent=self._parent,
                                      on_preview=lambda: (item.refresh(), canvas._sync_follow_handle()))
            if dialog.exec():
                # La boîte a remis le texte dans son état d'origine : on enregistre l'annulation, puis on applique.
                canvas.push_undo_snapshot()
                dialog.get_object()
                item.refresh()
                self.properties_changed.emit(obj)
            canvas._sync_follow_handle()
        elif isinstance(obj, SvgPathObject):
            dialog = AssignLayerDialog(self.layers, svg_obj=obj, title=tr("vector.svg_properties"), parent=self._parent)
            if dialog.exec():
                canvas.push_undo_snapshot()
                dialog.apply_to(obj)
                item.refresh()
                self.properties_changed.emit(obj)
        else:
            dialog = ShapeInsertDialog(self.layers, shape_obj=obj, parent=self._parent)
            if dialog.exec():
                canvas.push_undo_snapshot()
                dialog.get_object()
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
        dialog = MedalTextDialog(self.layers, parent=self._parent)
        if dialog.exec():
            created = self.canvas.make_medal_texts(**dialog.values())
            if created:
                self.canvas.scene_obj.clearSelection()
                for item in self.canvas.scene_obj.items():
                    if getattr(item, "obj", None) in created:
                        item.setSelected(True)

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
        if not self._require_layers():
            return
        path = self.dialogs.open_file(tr("vector.import_title"), tr("vector.import_filter"))
        if path:
            self.import_file(path)

    def import_file(self, path):
        """Importe le fichier SVG ou DXF `path` (aussi appelé par le glisser-déposer)."""
        if not self._require_layers():
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
        self.add_objects(objects)
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
                self.add_objects(objects)
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
        self.add_objects(objects)
        message = tr("vector.dxf_success").format(
            count=len(objects), layer=default_layer.name, unit=dxf_import.units_label(drawing))
        if skipped:
            message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
        self.dialogs.info(tr("vector.dxf_title"), message)

    # -- imbrication, série, gabarit

    def _sheet_default(self):
        """Taille de feuille proposée : la dernière saisie (boules ou imbrication), sinon le plateau de la machine."""
        prev = self.nesting_settings or {}
        return prev.get("sheet_w", self.machine.bed_w), prev.get("sheet_h", self.machine.bed_h)

    def _remember_sheet(self, width, height):
        """Garde la taille de feuille choisie pour les prochaines fenêtres (boules de Noël, imbrication).
        Elle ne dépend pas du matériau choisi : c'est l'utilisateur qui la fixe à chaque fois."""
        self.nesting_settings = {**(self.nesting_settings or {}), "sheet_w": width, "sheet_h": height}

    def open_nesting(self):
        """Placement automatique : range les pièces sélectionnées (ou toutes) sur la feuille pour
        gaspiller le moins de matière possible. Un trou ou un détail gravé reste avec sa pièce."""
        canvas = self.canvas
        enabled_ids = {layer.id for layer in self.layers.layers if layer.enabled}
        candidates = [o for o in canvas.objects if o.layer_id in enabled_ids]
        selected = [item.obj for item in canvas.scene_obj.selectedItems() if hasattr(item, "obj") and item.obj in candidates]
        if not candidates:
            self.dialogs.info(tr("nest.title"), tr("nest.no_objects"))
            return
        sheet_w, sheet_h = self._sheet_default()
        init = {**(self.nesting_settings or {}), "sheet_w": sheet_w, "sheet_h": sheet_h}
        dialog = NestingDialog(self._parent, self.machine.bed_w, self.machine.bed_h,
                               len(selected), len(candidates), init)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.nesting_settings = dialog.settings()
        self._remember_sheet(dialog.options()["sheet_w"], dialog.options()["sheet_h"])
        objects = selected if dialog.scope() == "selection" and selected else candidates
        options = dialog.options()
        pieces, members = build_pieces(objects)
        with self._busy():
            result = nesting.nest(pieces, options["sheet_w"], options["sheet_h"], spacing=options["spacing"],
                                  margin=options["margin"], angles=options["angles"], cell=options["cell"],
                                  origin=options["origin"])
        if not result.placements:
            self.dialogs.warning(tr("nest.title"), tr("nest.nothing_placed"))
            return
        canvas.push_undo_snapshot()
        moved = apply_result(canvas, members, result)
        moved_ids = {id(o) for o in moved}
        items = [item for item in canvas.scene_obj.items() if hasattr(item, "obj") and id(item.obj) in moved_ids]
        if items:
            canvas.request_recenter(items)
        message = tr("nest.done").format(
            placed=len(result.placements), sheet_w=options["sheet_w"], sheet_h=options["sheet_h"],
            percent=result.utilization * 100.0, ext_w=result.extent[0], ext_h=result.extent[1])
        if result.unplaced:
            message += "\n\n" + tr("nest.unplaced").format(count=len(result.unplaced))
        self.dialogs.info(tr("nest.title"), message)

    def open_serial_duplicate(self):
        """Duplication en série : fabrique N exemplaires de la sélection (découpe + gravure + texte), avec un
        texte (prénom) par exemplaire si on le souhaite, rangés en grille ou par imbrication automatique."""
        canvas = self.canvas
        objects = self.selected_objects()
        if not objects:
            self.dialogs.info(tr("serial.title"), tr("serial.no_selection"))
            return
        order = {id(o): i for i, o in enumerate(canvas.objects)}
        objects.sort(key=lambda o: order.get(id(o), 0))
        texts = [(o.text, i) for i, o in enumerate(objects) if isinstance(o, TextObject)]
        box = serial_dup.union_bounds([object_bounds(o) for o in objects]) or (0.0, 0.0, 0.0, 0.0)
        dialog = SerialDuplicateDialog(self._parent, texts, len(objects), box[2] - box[0], box[3] - box[1],
                                       self.machine.bed_w, self.machine.bed_h, self.serial_settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.serial_settings = dialog.settings()
        params = dialog.params()
        try:
            with self._busy():
                result = run_serial_duplicate(canvas, objects, params)
        except Exception as e:
            self.dialogs.warning(tr("serial.title"), tr("serial.error").format(error=e))
            return
        message = tr("serial.done").format(count=result.n_copies, w=f"{result.extent[0]:.0f}",
                                           h=f"{result.extent[1]:.0f}")
        if result.unplaced:
            message += "\n\n" + tr("serial.unplaced").format(count=result.unplaced)
        if result.overflow:
            names = params["names"]
            labels = [names[i] if i < len(names) else str(i + 1) for i in result.overflow]
            shown = ", ".join(labels[:8]) + (", …" if len(labels) > 8 else "")
            message += "\n\n" + tr("serial.overflow").format(names=shown)
        self.dialogs.info(tr("serial.title"), message)

    def open_jig_generator(self):
        """Gabarit de placement : une plaque à découper avec une poche par objet (dimensions de la sélection, plus
        un jeu), pour poser les porte-clés, décapsuleurs, stylos... toujours au même endroit avant de les graver.
        Avec les mêmes colonnes et espacements que « Dupliquer en série », chaque exemplaire tombe dans sa poche."""
        if not self._require_layers():
            return
        objects = self.selected_objects()
        box = serial_dup.union_bounds([object_bounds(o) for o in objects]) if objects else None
        dialog = JigDialog(self._parent, self.layers.layers,
                           (box[2] - box[0]) if box else 0.0, (box[3] - box[1]) if box else 0.0, box is not None,
                           self.machine.bed_w, self.machine.bed_h, self.jig_settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.jig_settings = dialog.settings()
        try:
            jig = jig_geometry.build_jig(dialog.jig_params())
        except jig_geometry.JigError as e:
            self.dialogs.warning(tr("jig.title"), jig_error_message(e))
            return
        mode = dialog.position_mode()
        if mode == "around" and box:
            origin_x, origin_y = jig_geometry.plate_origin_around(jig, box[0], box[1])
        elif mode == "beside" and box:
            origin_x, origin_y = box[2] + 10.0, box[1]
        else:
            origin_x, origin_y = dialog.position_xy()
        new_objects = jig_to_objects(jig, dialog.cut_layer_id(), origin_x, origin_y, dialog.with_base())
        self.add_objects(new_objects, show=False)
        message = tr("jig.done").format(count=jig.count, pw=f"{jig.pocket_w:.1f}", ph=f"{jig.pocket_h:.1f}",
                                        w=f"{jig.plate_w:.1f}", h=f"{jig.plate_h:.1f}")
        total_w = jig.plate_w * (2 if dialog.with_base() else 1) + (10.0 if dialog.with_base() else 0.0)
        if (origin_x < 0 or origin_y < 0 or origin_x + total_w > self.machine.bed_w
                or origin_y + jig.plate_h > self.machine.bed_h):
            message += "\n\n" + tr("jig.out_of_bed").format(bed_w=f"{self.machine.bed_w:.0f}",
                                                           bed_h=f"{self.machine.bed_h:.0f}")
        self.dialogs.info(tr("jig.title"), message)

    # -- générateurs

    def open_box_generator(self):
        """Générateur de boîte à encoches : les panneaux (calque de découpe) et le
        décor texte/SVG (calque de gravure)."""
        if not self._require_layers():
            return
        dialog = BoxGeneratorDialog(self._parent, self.layers.layers, self.machine.bed_w, self.machine.bed_h,
                                    self.box_settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.box_settings = dialog.settings()
        try:
            result = box_generator.build_box(dialog.params())
        except box_generator.BoxError as e:
            self.dialogs.warning(tr("box.title"), error_message(e))
            return
        offset = GENERATOR_OFFSET_MM
        panels = box_to_objects(result, dialog.cut_layer_id(), offset, offset)
        by_name = result.face_panels()          # y compris le couvercle d'une charnière (porté par l'arrière)
        decor_objects = []
        bed_h = self.machine.bed_h
        for decor in dialog.decors():
            panel = by_name.get(decor.face)
            if panel is None:
                continue                       # face absente (ex. dessus d'une boîte ouverte)
            try:
                decor_objects += decor_to_objects(decor, panel, dialog.engrave_layer_id(), bed_h, offset, offset)
            except Exception as e:
                self.dialogs.warning(tr("box.title"), tr("box.decor_error").format(error=e))
        decor_objects += motif_to_objects(result, dialog.engrave_layer_id(), offset, offset)
        decor_objects += index_to_objects(result, dialog.engrave_layer_id(), offset, offset)
        self.add_objects([obj for _, obj in panels] + decor_objects)
        message = tr("box.done").format(count=len(result.panels), decor=len(decor_objects),
                                        w=result.width, h=result.height)
        if result.width > self.machine.bed_w - 2 * offset or result.height > self.machine.bed_h - 2 * offset:
            message += "\n\n" + tr("box.too_big").format(bed_w=self.machine.bed_w, bed_h=self.machine.bed_h)
        self.dialogs.info(tr("box.title"), message)

    def open_puzzle_generator(self):
        """Générateur de puzzle : les pièces sur le calque de découpe, calées sur l'image s'il y en a une."""
        if not self._require_layers():
            return
        try:
            target_rect = self._image_frame()
        except Exception:
            log.warning("Puzzle : cadre de l'image illisible, puzzle non calé", exc_info=True)
            target_rect = None
        dialog = PuzzleGeneratorDialog(
            parent=self._parent,
            layers=self.layers.layers,
            bed_w=self.machine.bed_w,
            bed_h=self.machine.bed_h,
            saved_settings=self.puzzle_settings,
            target_image_rect=target_rect,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if hasattr(dialog, "settings"):
            self.puzzle_settings = dialog.settings()
        try:
            params = dialog.params()
            result = puzzle_generator.build_puzzle(params)
        except puzzle_generator.PuzzleError as e:
            key = f"puzzle.err.{e.code}"
            text = tr(key)
            if text == key:
                text = tr("puzzle.error") + f" ({e.code})"
            else:
                try:
                    text = text.format(**e.info)
                except (KeyError, IndexError, ValueError):     # traduction sans les bons champs
                    pass
            self.dialogs.warning(tr("puzzle.title"), text)
            return
        except Exception as e:
            self.dialogs.warning(tr("puzzle.error"), str(e))
            return
        layer_id = dialog.cut_layer_id() if hasattr(dialog, "cut_layer_id") else params.cut_layer_id
        objects = puzzle_to_objects(result, layer_id, offset_x_mm=GENERATOR_OFFSET_MM, offset_y_mm=GENERATOR_OFFSET_MM)
        if not objects:
            self.dialogs.warning(tr("puzzle.title"), tr("puzzle.empty"))
            return
        self.add_objects(objects)
        self.dialogs.info(tr("puzzle.title"), tr("puzzle.done").format(
            nx=params.nx, ny=params.ny, w=params.width, h=params.height, count=len(result.pieces)))

    def open_ornament_generator(self):
        """Générateur de boules de Noël : contours soudés (découpe) et prénom gravé ; un prénom par ligne
        donne une boule par prénom, rangées en grille, avec proposition d'imbrication."""
        if not self._require_layers():
            return
        # Taille de la feuille de matière : à choisir dans la fenêtre (dernière saisie, sinon le plateau).
        dialog = OrnamentGeneratorDialog(parent=self._parent, layers=self.layers.layers,
                                         saved_settings=self.ornament_settings,
                                         sheet=self._sheet_default())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.ornament_settings = dialog.settings()
        sheet_w, sheet_h = dialog.sheet()
        # L'imbrication reprendra cette taille de feuille.
        self._remember_sheet(sheet_w, sheet_h)
        from laser_studio.vector import ornament_batch, ornament_generator
        from laser_studio.vector.importers import ornament_engrave_to_objects
        from laser_studio.vector.ornament_region import build_ornament_parts
        names = dialog.names() or [""]
        family, bold, italic = dialog.font_options()
        built, failed, single_error = [], [], None
        with self._busy():                     # une série de boules peut prendre un moment
            for name in names:
                try:
                    built.append((name, build_ornament_parts(dialog.params(name), family, bold, italic)))
                except ornament_generator.OrnamentError as e:
                    if len(names) == 1:
                        single_error = e
                        break
                    failed.append(name)
        if single_error is not None:
            self.dialogs.warning(tr("ornament.title"), ornament_error_text(single_error))
            return
        # Rangement en grille d'après la boîte réelle de chaque boule (découpe + gravure du prénom et du filet).
        boxes = []
        for _name, parts in built:
            box = ornament_batch.contours_bounds(list(parts.cut) + list(parts.name) + list(parts.frame))
            boxes.append(box or (0.0, 0.0, 0.0, 0.0))
        # Colonnes : autant que la largeur du matériau le permet (10 mm de marge de chaque côté).
        widest = max((b[2] - b[0] for b in boxes), default=0.0)
        cols = ornament_batch.columns_for_width(len(boxes), widest, sheet_w - 2 * ornament_batch.SHEET_MARGIN_MM)
        offsets, extent = ornament_batch.grid_offsets(boxes, max_cols=cols)
        objects, ball_count = [], 0
        for (_name, parts), (dx, dy) in zip(built, offsets):
            ox, oy = GENERATOR_OFFSET_MM + dx, GENERATOR_OFFSET_MM + dy
            ball = ornament_to_objects(parts.cut, dialog.cut_layer_id(), offset_x_mm=ox, offset_y_mm=oy)
            # Prénom gravé sur la bande : le prénom et le filet vont sur le calque de gravure, au même repère.
            ball += ornament_engrave_to_objects(parts.name, parts.frame, dialog.engrave_layer_id(),
                                                offset_x_mm=ox, offset_y_mm=oy)
            if ball:
                objects += ball
                ball_count += 1
        if not objects:
            self.dialogs.warning(tr("ornament.title"), tr("ornament.empty"))
            return
        new_items = self.add_objects(objects)
        if ball_count == 1:
            geometry, contours = built[0][1].geometry, built[0][1].cut
            self.dialogs.info(tr("ornament.title"), tr("ornament.done").format(
                w=geometry.width, h=geometry.height, count=len(contours)))
            return
        message = tr("ornament.done_batch").format(n=ball_count, w=extent[0], h=extent[1])
        if failed:
            message += "\n\n" + tr("ornament.batch_failed").format(names=", ".join(failed))
        if (extent[0] + 2 * ornament_batch.SHEET_MARGIN_MM > sheet_w
                or extent[1] + 2 * ornament_batch.SHEET_MARGIN_MM > sheet_h):
            message += "\n\n" + tr("ornament.batch_overflow").format(w=sheet_w, h=sheet_h)
        message += "\n\n" + tr("ornament.batch_nest_ask")
        if self.dialogs.confirm_yes_no(tr("ornament.title"), message):
            # Les boules créées sont sélectionnées : l'imbrication s'ouvre avec « sélection » comme périmètre.
            self.canvas.scene_obj.clearSelection()
            for item in new_items:
                item.setSelected(True)
            self.open_nesting()

    def open_keychain_generator(self):
        """Générateur de porte-clés prénom : la base découpée et le texte gravé."""
        if not self._require_layers():
            return
        from laser_studio.ui.dialogs.keychain import KeychainGeneratorDialog
        from laser_studio.ui.dialogs.keychain.dialog import error_text as keychain_error_text
        from laser_studio.vector import keychain_generator

        dialog = KeychainGeneratorDialog(parent=self._parent, layers=self.layers.layers,
                                         saved_settings=self.keychain_settings)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.keychain_settings = dialog.settings()
        try:
            family, bold, italic = dialog.font_options()
            result = keychain_generator.build_keychain(dialog.params(), family, bold, italic)
        except keychain_generator.KeychainError as e:
            self.dialogs.warning(tr("keychain.title"), keychain_error_text(e))
            return
        objects = keychain_to_objects(
            result,
            cut_layer_id=dialog.cut_layer_id(),
            engrave_layer_id=dialog.engrave_layer_id(),
            offset_x_mm=GENERATOR_OFFSET_MM,
            offset_y_mm=GENERATOR_OFFSET_MM,
        )
        if not objects:
            return
        self.add_objects(objects)
        done_key = "keychain.done_two_layers" if getattr(result, "two_layers", False) else "keychain.done"
        self.dialogs.info(tr("keychain.title"), tr(done_key).format(w=result.width, h=result.height))
