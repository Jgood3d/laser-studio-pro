"""Mise en page dans l'éditeur vectoriel : imbrication automatique des pièces sur une feuille et duplication
en série de la sélection. Garde les derniers réglages de chaque fenêtre et la taille de feuille choisie.

    layout = LayoutController(editor, forms, busy=busy_cursor)
    canvas.serial_duplicate_requested.connect(layout.open_serial_duplicate)
"""
from contextlib import nullcontext

from laser_studio.i18n import tr
from laser_studio.models.vector_objects import TextObject
from laser_studio.vector import nesting
from laser_studio.vector import serial_duplicate as serial_dup
from laser_studio.vector.nesting_apply import apply_result, build_pieces
from laser_studio.vector.serial_apply import object_bounds, run_serial_duplicate


class LayoutController:
    """`editor` : VectorEditorController (canevas, calques, machine, messages, sélection) ; `forms` :
    EditorForms ; `busy()` : gestionnaire de contexte pendant un calcul long (curseur d'attente)."""

    def __init__(self, editor, forms, busy=nullcontext):
        self.editor = editor
        self.canvas = editor.canvas
        self.layers = editor.layers
        self.machine = editor.machine
        self.dialogs = editor.dialogs
        self.forms = forms
        self._busy = busy
        # Derniers réglages de chaque fenêtre, repris à sa prochaine ouverture.
        self.nesting_settings = None
        self.serial_settings = None

    def commands(self):
        """Commandes de l'onglet (VectorEditorTab.command) que ce contrôleur traite."""
        return {"nesting": self.open_nesting, "serial": self.open_serial_duplicate}

    # -- taille de feuille

    def sheet_default(self):
        """Taille de feuille proposée : la dernière saisie (boules ou imbrication), sinon le plateau de la machine."""
        prev = self.nesting_settings or {}
        return prev.get("sheet_w", self.machine.bed_w), prev.get("sheet_h", self.machine.bed_h)

    def remember_sheet(self, width, height):
        """Garde la taille de feuille choisie pour les prochaines fenêtres (boules de Noël, imbrication).
        Elle ne dépend pas du matériau choisi : c'est l'utilisateur qui la fixe à chaque fois."""
        self.nesting_settings = {**(self.nesting_settings or {}), "sheet_w": width, "sheet_h": height}

    # -- imbrication

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
        sheet_w, sheet_h = self.sheet_default()
        init = {**(self.nesting_settings or {}), "sheet_w": sheet_w, "sheet_h": sheet_h}
        choice = self.forms.nesting(self.machine.bed_w, self.machine.bed_h, len(selected), len(candidates), init)
        if choice is None:
            return
        self.nesting_settings = choice.settings
        options = choice.options
        self.remember_sheet(options["sheet_w"], options["sheet_h"])
        objects = selected if choice.scope == "selection" and selected else candidates
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

    # -- duplication en série

    def open_serial_duplicate(self):
        """Duplication en série : fabrique N exemplaires de la sélection (découpe + gravure + texte), avec un
        texte (prénom) par exemplaire si on le souhaite, rangés en grille ou par imbrication automatique."""
        canvas = self.canvas
        objects = self.editor.selected_objects()
        if not objects:
            self.dialogs.info(tr("serial.title"), tr("serial.no_selection"))
            return
        order = {id(o): i for i, o in enumerate(canvas.objects)}
        objects.sort(key=lambda o: order.get(id(o), 0))
        texts = [(o.text, i) for i, o in enumerate(objects) if isinstance(o, TextObject)]
        box = serial_dup.union_bounds([object_bounds(o) for o in objects]) or (0.0, 0.0, 0.0, 0.0)
        choice = self.forms.serial(texts, len(objects), box[2] - box[0], box[3] - box[1],
                                   self.machine.bed_w, self.machine.bed_h, self.serial_settings)
        if choice is None:
            return
        self.serial_settings = choice.settings
        params = choice.params
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
