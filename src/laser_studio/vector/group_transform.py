"""Transformations d'un ensemble d'objets traité comme un groupe (menu contextuel de l'éditeur vectoriel) :
encombrement, mise à l'échelle qui garde les positions relatives, rotation d'un quart de tour, calque.
Agit sur les objets du document ; le canevas rafraîchit ensuite leurs éléments."""
from laser_studio.models.vector_objects import GroupObject, ShapeObject, SvgPathObject, TextObject
from laser_studio.vector.text_on_path import scaled_points


def group_bounds(objects):
    """(x_min, y_min, largeur, hauteur) en mm de l'encombrement commun des objets (repère monde)."""
    boxes = [obj.world_path().boundingRect() for obj in objects]
    x_min = min(b.left() for b in boxes)
    y_min = min(b.top() for b in boxes)
    width = max(b.right() for b in boxes) - x_min
    height = max(b.bottom() for b in boxes) - y_min
    return x_min, y_min, width, height


def scale_group(objects, factor_x, factor_y, origin):
    """Met les objets à l'échelle comme un seul groupe, autour de `origin` (x, y) mm : positions relatives
    et proportions conservées. Chaque type garde ses propres réglages (taille de police, échelle du tracé)."""
    x0, y0 = origin
    for obj in objects:
        obj.x_mm = x0 + (obj.x_mm - x0) * factor_x
        obj.y_mm = y0 + (obj.y_mm - y0) * factor_y
        if isinstance(obj, ShapeObject):
            obj.width_mm *= factor_x
            obj.height_mm *= factor_y
        elif isinstance(obj, TextObject):
            obj.size_mm *= factor_y
            obj.letter_spacing_mm *= factor_x
            obj.arc_radius_mm = getattr(obj, "arc_radius_mm", 0.0) * factor_y
            if getattr(obj, "follow_points", None):
                obj.follow_points = scaled_points(obj.follow_points, factor_x, factor_y)
                obj.follow_gap_mm = getattr(obj, "follow_gap_mm", 0.0) * factor_y
        elif isinstance(obj, SvgPathObject):
            obj.scale_x = getattr(obj, "scale_x", 1.0) * factor_x
            obj.scale_y = getattr(obj, "scale_y", 1.0) * factor_y
        elif isinstance(obj, GroupObject):
            # Les objets du groupe, à leur place au groupement, mis à l'échelle autour de son origine.
            scale_group(obj.children, factor_x, factor_y, obj.origin)
            obj.invalidate()


def resize_group(objects, width_mm, height_mm):
    """Donne au groupe la taille `width_mm` × `height_mm`, coin bas-gauche fixe."""
    x_min, y_min, width, height = group_bounds(objects)
    scale_group(objects, width_mm / max(width, 1e-6), height_mm / max(height, 1e-6), (x_min, y_min))


def rotate_quarter(objects):
    """Tourne chaque objet de 90° sur lui-même."""
    for obj in objects:
        obj.rotation_deg = (obj.rotation_deg + 90.0) % 360.0


def assign_layer(objects, layer_id):
    for obj in objects:
        obj.set_layer(layer_id)
