"""Passerelle entre les modules de calcul (dxf_import, box_generator) et les objets
de l'éditeur vectoriel : crée des SvgPathObject (tracés fixes, comme un SVG importé)
et place texte / SVG de décor sur les faces d'une boîte.

Repère des objets : origine en bas à gauche de la zone de travail, Y vers le haut
(le tracé local, lui, est en Y vers le bas, ancré en bas à gauche de l'objet — voir
extract_svg_objects)."""
from PyQt6.QtGui import QPainterPath

from box_generator import BoxDecor  # noqa: F401  (réexporté : vector_import.BoxDecor)
from vector_layers import SvgPathObject, TextObject, extract_svg_objects


def _path_object(points, closed, tag, layer_id, shift_x, shift_y):
    """Un tracé (points en mm, Y vers le haut) -> SvgPathObject ancré en bas à gauche, ou None si dégénéré."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, min_y = min(xs), min(ys)
    if max(xs) - min_x <= 0 and max(ys) - min_y <= 0:
        return None
    path = QPainterPath()
    path.moveTo(points[0][0] - min_x, -(points[0][1] - min_y))
    for x, y in points[1:]:
        path.lineTo(x - min_x, -(y - min_y))
    if closed:
        path.closeSubpath()
    return SvgPathObject(local_path_data=path, source_tag=tag, layer_id=layer_id,
                         x_mm=min_x + shift_x, y_mm=min_y + shift_y)


def dxf_to_objects(drawing, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Objets indépendants (un par tracé du DXF). Le coin inférieur gauche de l'ensemble du dessin est
    ancré à (offset_x_mm, offset_y_mm), positions relatives conservées, comme pour un import SVG."""
    bounds = drawing.bounds()
    if bounds is None:
        return []
    shift_x, shift_y = offset_x_mm - bounds[0], offset_y_mm - bounds[1]
    objects = []
    for path in drawing.paths:
        obj = _path_object(path.points, path.closed, f"dxf:{path.layer}", layer_id, shift_x, shift_y)
        if obj is not None:
            objects.append(obj)
    return objects


def box_to_objects(result, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """[(panneau, objet)] : un contour de découpe fermé par panneau, posé selon la disposition calculée."""
    out = []
    for panel in result.panels:
        obj = _path_object(panel.placed(), True, f"box:{panel.name}", layer_id, offset_x_mm, offset_y_mm)
        if obj is not None:
            out.append((panel, obj))
    return out


def _group_bounds(objects):
    rects = [o.world_path().boundingRect() for o in objects]
    left = min(r.left() for r in rects)
    right = max(r.right() for r in rects)
    low = min(min(r.top(), r.bottom()) for r in rects)
    high = max(max(r.top(), r.bottom()) for r in rects)
    return left, low, right, high


def center_group(objects, cx, cy, width_mm=0.0):
    """Met éventuellement le groupe à la largeur `width_mm` (proportions conservées), puis centre son
    rectangle englobant sur (cx, cy). Le groupe est modifié sur place."""
    if not objects:
        return objects
    left, low, right, high = _group_bounds(objects)
    if width_mm and width_mm > 0 and right - left > 0:
        s = width_mm / (right - left)
        for o in objects:
            o.x_mm = left + (o.x_mm - left) * s
            o.y_mm = low + (o.y_mm - low) * s
            o.scale_x = getattr(o, "scale_x", 1.0) * s
            o.scale_y = getattr(o, "scale_y", 1.0) * s
        left, low, right, high = _group_bounds(objects)
    dx = cx - (left + right) / 2.0
    dy = cy - (low + high) / 2.0
    for o in objects:
        o.x_mm += dx
        o.y_mm += dy
    return objects


def decor_to_objects(decor, panel, layer_id, bed_h_mm, offset_x_mm=10.0, offset_y_mm=10.0):
    """Objets de décor (texte ou SVG dégroupé) centrés sur la face `panel` de la boîte."""
    fx, fy = panel.face_center()
    cx, cy = fx + offset_x_mm + decor.dx, fy + offset_y_mm + decor.dy
    if decor.kind == "svg":
        objects = extract_svg_objects(decor.svg_path, layer_id, bed_h_mm)
        return center_group(objects, cx, cy, decor.width_mm)
    if not decor.text.strip():
        return []
    obj = TextObject(text=decor.text, font_family=decor.font_family, size_mm=decor.size_mm,
                     bold=decor.bold, italic=decor.italic, layer_id=layer_id, x_mm=0.0, y_mm=0.0)
    return center_group([obj], cx, cy)
