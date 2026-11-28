"""Objets de l'éditeur vectoriel <-> logique de duplication en série (vector/serial_duplicate.py) : clonage
des objets, rectangles englobants et placement des exemplaires (grille ou imbrication). Sans canevas : le
contrôleur (controllers/layout.py) ajoute ensuite les exemplaires, en une seule action annulable (Ctrl+Z)."""
import copy
import uuid
from dataclasses import dataclass, field

from laser_studio.vector import nesting as ng
from laser_studio.vector import serial_duplicate as sd
from laser_studio.vector.nesting_apply import apply_result, object_polygons
from laser_studio.models.vector_objects import VectorObject


def object_bounds(obj):
    """Rectangle englobant monde (xmin, ymin, xmax, ymax), Y vers le haut ; None si l'objet n'a aucun tracé
    ou s'il est sur le calque « Ignoré » (ni affiché ni gravé)."""
    if getattr(obj, "is_ignored", lambda: False)():
        return None
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
    copies: list = field(default_factory=list)          # exemplaires gardés ; copies[0] = les objets d'origine
    extent: tuple = (0.0, 0.0)                          # emprise (largeur, hauteur) en mm
    unplaced: int = 0                                   # exemplaires abandonnés faute de place (mode imbrication)
    overflow: list = field(default_factory=list)        # indices des exemplaires dont le texte dépasse du motif

    @property
    def n_copies(self):
        return len(self.copies)


def plan_serial_duplicate(objects, params, obstacles=None):
    """Exemplaires de `objects` selon `params` (voir SerialDuplicateDialog.params()), placés : l'original est
    l'exemplaire 1 (modifié en place : texte, position). `obstacles` : contours à éviter en imbrication."""
    names = params.get("names") or []
    text_index = params.get("text_index")
    copies = sd.build_copies(objects, params["count"], clone=clone_object, bounds=object_bounds,
                             text_index=text_index, names=names, keep_center=params.get("keep_center", True))
    result = SerialResult()
    if text_index is not None and names:
        result.overflow = sd.overflowing(copies, text_index, object_bounds)
    dropped = set()
    if params["layout"] == "nest":
        opts = params["nest"]
        pieces = [[poly for obj in c for poly in object_polygons(obj)] for c in copies]
        nest_result = ng.nest(pieces, opts["sheet_w"], opts["sheet_h"], spacing=opts["spacing"],
                              margin=opts["margin"], angles=opts["angles"], cell=opts["cell"],
                              origin=opts["origin"], obstacles=obstacles)
        apply_result(copies, nest_result)
        dropped = {i for i in nest_result.unplaced if i > 0}            # l'original reste où il est
        result.extent = nest_result.extent
    else:
        result.extent = sd.layout_grid(copies, object_bounds, params["cols"], params["gap_x"],
                                       params["gap_y"], upward=params.get("upward", True))
    result.copies = [c for i, c in enumerate(copies) if i not in dropped]
    result.unplaced = len(dropped)
    return result
