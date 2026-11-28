"""Générateurs de l'éditeur vectoriel : boîte à encoches, puzzle, boules de Noël, porte-clés prénom et gabarit
de placement. Les quatre premiers partagent une fenêtre (EditorForms.generators), le gabarit a la sienne.
Le contrôleur calcule les pièces (vector/) et les ajoute à l'éditeur par VectorEditorController.import_objects
(placement : marge de surbalayage, ou à côté des objets présents).
Garde les derniers réglages de chaque fenêtre.

    generators = GeneratorsController(editor, layout, forms, image_frame=..., busy=busy_cursor)
    actions.generator_requested.connect(generators.open_generators)        # « box », « puzzle »…
"""
from contextlib import nullcontext

from laser_studio.core.debug_log import get_logger
from laser_studio.i18n import tr
from laser_studio.i18n.errors import generator_error_text
from laser_studio.vector import box_generator, puzzle_generator
from laser_studio.vector import jig as jig_geometry
from laser_studio.vector import serial_duplicate as serial_dup
from laser_studio.vector.importers import (
    box_to_objects, decor_to_objects, index_to_objects, jig_to_objects, keychain_to_objects, motif_to_objects,
    ornament_to_objects, puzzle_to_objects,
)
from laser_studio.vector.serial_apply import object_bounds

log = get_logger()

# Les générateurs fabriquent leurs pièces à l'origine ; import_objects les place ensuite (marge de
# surbalayage, ou à côté des objets présents).
GENERATOR_OFFSET_MM = 0.0


class GeneratorsController:
    """`editor` : VectorEditorController (calques, machine, messages, sélection, ajout des objets) ;
    `layout` : LayoutController (taille de feuille, imbrication proposée après les boules) ; `forms` :
    EditorForms. État de l'interface lu à chaque usage : `image_frame()` (x, y, largeur, hauteur) en mm de
    l'image à graver, pour caler le puzzle, ou None ; `busy()` : curseur d'attente pendant un calcul long."""

    def __init__(self, editor, layout, forms, image_frame=lambda: None, busy=nullcontext, library=None):
        self.editor = editor
        self.canvas = editor.canvas
        self.layers = editor.layers
        self.machine = editor.machine
        self.dialogs = editor.dialogs
        self.layout = layout
        self.forms = forms
        self._image_frame = image_frame
        self._busy = busy
        self.library = library               # LibraryController : page « Bibliothèque » (None : sans)
        # Derniers réglages de chaque fenêtre, repris à sa prochaine ouverture.
        self.box_settings = None
        self.puzzle_settings = None
        self.ornament_settings = None
        self.keychain_settings = None
        self.jig_settings = None
        self.last_generator = "box"          # la fenêtre des générateurs rouvre sur le dernier utilisé

    def commands(self):
        """Commandes de l'onglet (VectorEditorTab.command) que ce contrôleur traite."""
        return {"generators": self.open_generators, "jig": self.open_jig_generator,
                **{kind: (lambda kind=kind: self.open_generators(kind))
                   for kind in ("library", "box", "puzzle", "ornament", "keychain")}}

    def open_generators(self, kind=None):
        """Fenêtre des générateurs, ouverte sur `kind` (« library », « box », « puzzle », « ornament »,
        « keychain » ; par défaut le dernier utilisé) ; le générateur validé fabrique ses pièces (ou le modèle
        de la bibliothèque) et les ajoute à l'éditeur."""
        if not self.editor.require_layers():
            return
        try:
            target_rect = self._image_frame()
        except Exception:
            log.warning("Puzzle : cadre de l'image illisible, puzzle non calé", exc_info=True)
            target_rect = None
        layers, bed_w, bed_h = self.layers.layers, self.machine.bed_w, self.machine.bed_h
        requests = {
            "box": (layers, bed_w, bed_h, self.box_settings),
            "puzzle": (layers, bed_w, bed_h, self.puzzle_settings, target_rect),
            # Taille de la feuille de matière : à choisir dans la fenêtre (dernière saisie, sinon le plateau).
            "ornament": (layers, self.ornament_settings, self.layout.sheet_default()),
            "keychain": (layers, self.keychain_settings),
        }
        library = self.library.generator_request() if self.library is not None else None
        if library is not None:
            requests["library"] = library
        elif kind == "library":
            self.dialogs.info(tr("library.title"), tr("library.empty"))
            return
        picked = self.forms.generators(kind or self.last_generator, requests)
        if picked is None:
            return
        kind, choice = picked
        self.last_generator = kind
        if kind == "library":
            self.library.import_choice(choice)
            return
        {"box": self._make_box, "puzzle": self._make_puzzle, "ornament": self._make_ornament,
         "keychain": self._make_keychain}[kind](choice)

    def open_jig_generator(self):
        """Gabarit de placement : une plaque à découper avec une poche par objet (dimensions de la sélection, plus
        un jeu), pour poser les porte-clés, décapsuleurs, stylos... toujours au même endroit avant de les graver.
        Avec les mêmes colonnes et espacements que « Dupliquer en série », chaque exemplaire tombe dans sa poche."""
        if not self.editor.require_layers():
            return
        objects = self.editor.selected_objects()
        box = serial_dup.union_bounds([object_bounds(o) for o in objects]) if objects else None
        choice = self.forms.jig(self.layers.layers, (box[2] - box[0]) if box else 0.0,
                                (box[3] - box[1]) if box else 0.0, box is not None,
                                self.machine.bed_w, self.machine.bed_h, self.jig_settings)
        if choice is None:
            return
        self.jig_settings = choice.settings
        try:
            jig = jig_geometry.build_jig(choice.params)
        except jig_geometry.JigError as e:
            self.dialogs.warning(tr("jig.title"), generator_error_text("jig", e, generic_key=f"jig.err.{e.code}"))
            return
        mode = choice.position_mode
        if mode == "around" and box:
            origin_x, origin_y = jig_geometry.plate_origin_around(jig, box[0], box[1])
        elif mode == "beside" and box:
            origin_x, origin_y = box[2] + 10.0, box[1]
        else:
            origin_x, origin_y = choice.position_xy
        new_objects = jig_to_objects(jig, choice.cut_layer, origin_x, origin_y, choice.with_base)
        self.editor.add_objects(new_objects, show=False)
        message = tr("jig.done").format(count=jig.count, pw=f"{jig.pocket_w:.1f}", ph=f"{jig.pocket_h:.1f}",
                                        w=f"{jig.plate_w:.1f}", h=f"{jig.plate_h:.1f}")
        total_w = jig.plate_w * (2 if choice.with_base else 1) + (10.0 if choice.with_base else 0.0)
        if (origin_x < 0 or origin_y < 0 or origin_x + total_w > self.machine.bed_w
                or origin_y + jig.plate_h > self.machine.bed_h):
            message += "\n\n" + tr("jig.out_of_bed").format(bed_w=f"{self.machine.bed_w:.0f}",
                                                           bed_h=f"{self.machine.bed_h:.0f}")
        self.dialogs.info(tr("jig.title"), message)

    def _make_box(self, choice):
        """Boîte à encoches : les panneaux (calque de découpe) et le décor texte/SVG (calque de gravure)."""
        self.box_settings = choice.settings
        try:
            result = box_generator.build_box(choice.params)
        except box_generator.BoxError as e:
            self.dialogs.warning(tr("box.title"), generator_error_text("box", e, generic_key="box.err.generic"))
            return
        offset = GENERATOR_OFFSET_MM
        panels = box_to_objects(result, choice.cut_layer, offset, offset)
        by_name = result.face_panels()          # y compris le couvercle d'une charnière (porté par l'arrière)
        decor_objects = []
        bed_h = self.machine.bed_h
        for decor in choice.decors:
            panel = by_name.get(decor.face)
            if panel is None:
                continue                       # face absente (ex. dessus d'une boîte ouverte)
            try:
                decor_objects += decor_to_objects(decor, panel, choice.engrave_layer, bed_h, offset, offset)
            except Exception as e:
                self.dialogs.warning(tr("box.title"), tr("box.decor_error").format(error=e))
        decor_objects += motif_to_objects(result, choice.engrave_layer, offset, offset)
        decor_objects += index_to_objects(result, choice.engrave_layer, offset, offset)
        if not self.editor.import_objects([obj for _, obj in panels] + decor_objects):
            return
        message = tr("box.done").format(count=len(result.panels), decor=len(decor_objects),
                                        w=result.width, h=result.height)
        if result.width > self.machine.bed_w or result.height > self.machine.bed_h:
            message += "\n\n" + tr("box.too_big").format(bed_w=self.machine.bed_w, bed_h=self.machine.bed_h)
        self.dialogs.info(tr("box.title"), message)

    def _make_puzzle(self, choice):
        """Puzzle : les pièces sur le calque de découpe, calées sur l'image s'il y en a une."""
        self.puzzle_settings = choice.settings
        params = choice.params
        try:
            result = puzzle_generator.build_puzzle(params)
        except puzzle_generator.PuzzleError as e:
            self.dialogs.warning(tr("puzzle.title"), generator_error_text("puzzle", e))
            return
        except Exception as e:
            self.dialogs.warning(tr("puzzle.error"), str(e))
            return
        objects = puzzle_to_objects(result, choice.cut_layer, offset_x_mm=GENERATOR_OFFSET_MM, offset_y_mm=GENERATOR_OFFSET_MM)
        if not objects:
            self.dialogs.warning(tr("puzzle.title"), tr("puzzle.empty"))
            return
        # Position choisie dans la fenêtre du puzzle (par défaut calée sur l'image) : gardée, sauf si
        # l'utilisateur le place à côté des objets présents.
        if not self.editor.import_objects(objects, keep_position=True):
            return
        self.dialogs.notify(tr("puzzle.done").format(
            nx=params.nx, ny=params.ny, w=params.width, h=params.height, count=len(result.pieces)))

    def _make_ornament(self, choice):
        """Boules de Noël : contours soudés (découpe) et prénom gravé ; un prénom par ligne donne une boule par
        prénom, rangées en grille, avec proposition d'imbrication."""
        self.ornament_settings = choice.settings
        sheet_w, sheet_h = choice.sheet
        # L'imbrication reprendra cette taille de feuille.
        self.layout.remember_sheet(sheet_w, sheet_h)
        from laser_studio.vector import ornament_batch, ornament_generator
        from laser_studio.vector.importers import ornament_engrave_to_objects
        from laser_studio.vector.ornament_region import build_ornament_parts
        family, bold, italic = choice.font
        built, failed, single_error = [], [], None
        with self._busy():                     # une série de boules peut prendre un moment
            for name, params in choice.balls:
                try:
                    built.append((name, build_ornament_parts(params, family, bold, italic)))
                except ornament_generator.OrnamentError as e:
                    if len(choice.balls) == 1:
                        single_error = e
                        break
                    failed.append(name)
        if single_error is not None:
            self.dialogs.warning(tr("ornament.title"), generator_error_text("ornament", single_error))
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
            ball = ornament_to_objects(parts.cut, choice.cut_layer, offset_x_mm=ox, offset_y_mm=oy)
            # Prénom gravé sur la bande : le prénom et le filet vont sur le calque de gravure, au même repère.
            ball += ornament_engrave_to_objects(parts.name, parts.frame, choice.engrave_layer,
                                                offset_x_mm=ox, offset_y_mm=oy)
            if ball:
                objects += ball
                ball_count += 1
        if not objects:
            self.dialogs.warning(tr("ornament.title"), tr("ornament.empty"))
            return
        new_items = self.editor.import_objects(objects)
        if not new_items:
            return
        if ball_count == 1:
            geometry, contours = built[0][1].geometry, built[0][1].cut
            self.dialogs.notify(tr("ornament.done").format(
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
            self.layout.open_nesting()

    def _make_keychain(self, choice):
        """Porte-clés prénom : la base découpée et le texte gravé."""
        # Importé ici, comme avant : chargé à la première utilisation.
        from laser_studio.vector import keychain_generator

        self.keychain_settings = choice.settings
        try:
            family, bold, italic = choice.font
            result = keychain_generator.build_keychain(choice.params, family, bold, italic)
        except keychain_generator.KeychainError as e:
            self.dialogs.warning(tr("keychain.title"), generator_error_text("keychain", e))
            return
        objects = keychain_to_objects(
            result,
            cut_layer_id=choice.cut_layer,
            engrave_layer_id=choice.engrave_layer,
            offset_x_mm=GENERATOR_OFFSET_MM,
            offset_y_mm=GENERATOR_OFFSET_MM,
        )
        if not objects or not self.editor.import_objects(objects):
            return
        if getattr(result, "glue_letters", False):
            done_key = "keychain.done_glue"
        elif getattr(result, "two_layers", False):
            done_key = "keychain.done_two_layers"
        else:
            done_key = "keychain.done"
        self.dialogs.notify(tr(done_key).format(w=result.width, h=result.height))
