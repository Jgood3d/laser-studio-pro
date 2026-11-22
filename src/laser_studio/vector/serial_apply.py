"""Passerelle entre l'éditeur vectoriel (Qt) et la logique de duplication en série (vector/serial_duplicate.py) :
clonage des objets, rectangles englobants, placement (grille ou imbrication) et ajout au canevas, en une seule
action annulable (Ctrl+Z)."""
import copy
import uuid
from dataclasses import dataclass, field

from laser_studio.vector import nesting as ng
from laser_studio.vector import serial_duplicate as sd
from laser_studio.vector.nesting_apply import apply_result, object_polygons
from laser_studio.models.vector_objects import VectorObject


def object_bounds(obj):
    """Rectangle englobant monde (xmin, ymin, xmax, ymax), Y vers le haut ; None si l'objet n'a aucun tracé."""
    path = obj.world_path()
    if path.isEmpty():
        return None
    r = path.boundingRect()
    return (r.left(), r.top(), r.right(), r.bottom())


def clone_object(obj):
    clone = VectorObject.from_dict(copy.deepcopy(obj.to_dict()))
    clone.id = uuid.uuid4().hex[:8]
    return clone


@dataclass
class SerialResult:
    n_copies: int = 0                                   # exemplaires présents sur le canevas (original compris)
    extent: tuple = (0.0, 0.0)                          # emprise (largeur, hauteur) en mm
    unplaced: int = 0                                   # exemplaires abandonnés faute de place (mode imbrication)
    overflow: list = field(default_factory=list)        # indices des exemplaires dont le texte dépasse du motif
    items: list = field(default_factory=list)           # éléments graphiques ajoutés


def _existing_polygons(canvas, template):
    """Contours des objets déjà sur le canevas (calques actifs) qui ne font pas partie du motif dupliqué :
    ce sont des obstacles pour l'imbrication (par exemple un lot dupliqué juste avant)."""
    enabled = {layer.id for layer in canvas.layer_manager.layers if layer.enabled}
    skip = {id(o) for o in template}
    return [poly for obj in canvas.objects if id(obj) not in skip and obj.layer_id in enabled
            for poly in object_polygons(obj)]


def run_serial_duplicate(canvas, objects, params):
    """Crée les exemplaires de `objects` selon `params` (voir SerialDuplicateDialog.params()) ; l'original est
    l'exemplaire 1. Annule tout et relance l'exception en cas d'erreur."""
    names = params.get("names") or []
    text_index = params.get("text_index")
    canvas.push_undo_snapshot()
    try:
        copies = sd.build_copies(objects, params["count"], clone=clone_object, bounds=object_bounds,
                                 text_index=text_index, names=names, keep_center=params.get("keep_center", True))
        result = SerialResult()
        if text_index is not None and names:
            result.overflow = sd.overflowing(copies, text_index, object_bounds)
        dropped = set()
        if params["layout"] == "nest":
            opts = params["nest"]
            pieces = [[poly for obj in c for poly in object_polygons(obj)] for c in copies]
            obstacles = _existing_polygons(canvas, copies[0]) if params.get("avoid_existing", True) else None
            nest_result = ng.nest(pieces, opts["sheet_w"], opts["sheet_h"], spacing=opts["spacing"],
                                  margin=opts["margin"], angles=opts["angles"], cell=opts["cell"],
                                  origin=opts["origin"], obstacles=obstacles)
            apply_result(canvas, copies, nest_result)
            dropped = {i for i in nest_result.unplaced if i > 0}        # l'original reste où il est
            result.extent = nest_result.extent
        else:
            result.extent = sd.layout_grid(copies, object_bounds, params["cols"], params["gap_x"],
                                           params["gap_y"], upward=params.get("upward", True))
        kept = [c for i, c in enumerate(copies) if i not in dropped]
        for c in kept[1:]:
            result.items += [canvas.add_object(obj) for obj in c]
        for obj in copies[0]:                                            # texte et position modifiés en place
            canvas.set_object_position(obj, obj.x_mm, obj.y_mm)
        result.n_copies = len(kept)
        result.unplaced = len(dropped)
    except Exception:
        canvas.undo()
        raise
    ids = {id(obj) for c in kept for obj in c}
    canvas.scene_obj.clearSelection()
    selected = [it for it in canvas.scene_obj.items() if hasattr(it, "obj") and id(it.obj) in ids]
    for it in selected:
        it.setSelected(True)
    canvas.request_recenter(selected)
    return result
