"""Passerelle entre l'éditeur vectoriel et l'algorithme d'imbrication (nesting.py) : extrait les
contours des objets, regroupe ceux qui vont ensemble (un trou ou un détail gravé suit sa pièce), puis
applique les positions et rotations calculées en gardant chaque groupe rigide."""
from PyQt6.QtGui import QTransform

import nesting as ng


def object_polygons(obj):
    """Contours de l'objet en mm, repère monde (origine en bas à gauche, Y vers le haut)."""
    return [[(pt.x(), pt.y()) for pt in poly] for poly in obj.world_path().toSubpathPolygons(QTransform())]


def build_pieces(objects):
    """(pièces, membres) : `pièces[i]` = tous les contours du groupe i, `membres[i]` = ses objets."""
    shapes = [object_polygons(o) for o in objects]
    groups = ng.group_by_containment(shapes)
    pieces = [[poly for idx in group for poly in shapes[idx]] for group in groups]
    members = [[objects[idx] for idx in group] for group in groups]
    return pieces, members


def apply_result(canvas, members, result):
    """Déplace et tourne chaque groupe placé, d'un seul bloc.

    La transformation d'un objet est : translation (x, y), puis rotation, puis échelle. Tourner un groupe de
    `angle` autour de son pivot revient donc à tourner la position de chaque objet autour du pivot, et à
    ajouter `angle` à sa propre rotation. Renvoie la liste des objets déplacés."""
    moved = []
    for placement in result.placements:
        for obj in members[placement.index]:
            x, y = placement.apply((obj.x_mm, obj.y_mm))
            canvas.set_object_position(obj, x, y, (obj.rotation_deg + placement.angle) % 360.0)
            moved.append(obj)
    return moved
