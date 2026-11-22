"""Opérations de géométrie sur les objets du dessin : grouper, dégrouper,
exploser en segments, convertir en tracé. Elles fabriquent de nouveaux
objets sans toucher au document : l'appelant les remplace
(VectorDocument.replace) et prend l'étape d'annulation.

Les tracés sont des QPainterPath (QtGui, sans widget). Repère « monde » :
origine bas-gauche, Y vers le haut ; repère local d'un SvgPathObject : ancré
sur le coin bas-gauche de sa boîte englobante, Y vers le bas (comme
extract_svg_objects).
"""
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath, QTransform

from laser_studio.models.vector_objects import SvgPathObject
from laser_studio.vector.svg_extract import _qpainterpath_to_subpaths


def path_to_polylines(path):
    """Convertit un QPainterPath en polylignes (liste de listes de QPointF).

    Les courbes sont aplaties via toSubpathPolygons (précision suffisante
    pour l'édition laser : segments / encoches).
    """
    polylines = []
    for poly in path.toSubpathPolygons(QTransform()):
        pts = [QPointF(p) for p in poly]
        if len(pts) >= 2:
            polylines.append(pts)
    return polylines


def polylines_to_path(polylines):
    path = QPainterPath()
    for pts in polylines:
        if len(pts) < 2:
            continue
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
    return path


def world_path_to_svg_object(world_path, layer_id, source_tag="segment"):
    """Crée un SvgPathObject ancré sur le bbox monde d'un petit tracé."""
    bbox = world_path.boundingRect()
    if bbox.width() <= 0 and bbox.height() <= 0:
        # Segment purement horizontal/vertical : bbox peut avoir une dim nulle.
        if world_path.elementCount() == 0:
            return None
    x0, y0 = bbox.left(), bbox.top()
    # Même convention que group/ungroup : Y monde haut -> local avec flip
    to_local = QTransform(1, 0, 0, -1, -x0, y0)
    local = to_local.map(world_path)
    return SvgPathObject(
        local_path_data=local,
        source_tag=source_tag,
        layer_id=layer_id,
        x_mm=x0,
        y_mm=y0,
    )


def group_objects(objects):
    """UN SEUL objet tracé (SvgPathObject) qui réunit `objects`, déjà rangés
    dans l'ordre du document : la géométrie de chaque partie est reprise telle
    qu'elle est positionnée (position, rotation, miroir, taille), puis
    fusionnée. Le calque retenu est celui du premier objet. None si le tracé
    réuni est vide."""
    combined = QPainterPath()
    for obj in objects:
        combined.addPath(obj.world_path())
    bbox = combined.boundingRect()
    if bbox.isNull():
        return None
    x0, y0 = bbox.left(), bbox.top()
    to_local = QTransform(1, 0, 0, -1, -x0, y0)
    local = to_local.map(combined)
    return SvgPathObject(
        local_path_data=local, source_tag="group",
        layer_id=objects[0].layer_id, x_mm=x0, y_mm=y0,
    )


def can_ungroup(obj):
    """True si l'objet est un SvgPathObject avec au moins 2 sous-tracés."""
    if not isinstance(obj, SvgPathObject):
        return False
    return len(_qpainterpath_to_subpaths(obj.local_path())) >= 2


def ungroup_object(obj):
    """Un objet indépendant par sous-tracé de `obj` (même calque), ou une
    liste vide s'il n'y a rien d'utile à séparer (moins de 2 morceaux)."""
    subs = _qpainterpath_to_subpaths(obj.local_path())
    # Transforme chaque sous-tracé local en objet monde indépendant.
    # world_transform mappe le repère local de l'objet parent.
    wt = obj.world_transform()
    children = []
    for sub in subs:
        if sub.elementCount() == 0:
            continue
        world_sub = wt.map(sub)
        bbox = world_sub.boundingRect()
        if bbox.width() <= 0 and bbox.height() <= 0:
            continue
        x0, y0 = bbox.left(), bbox.top()
        to_local = QTransform(1, 0, 0, -1, -x0, y0)
        local = to_local.map(world_sub)
        children.append(SvgPathObject(
            local_path_data=local,
            source_tag=getattr(obj, "source_tag", "path") or "path",
            layer_id=obj.layer_id,
            x_mm=x0,
            y_mm=y0,
        ))
    return children if len(children) >= 2 else []


def can_explode(obj):
    """True si l'objet a au moins une arête (forme, tracé, texte)."""
    polys = path_to_polylines(obj.world_path())
    return sum(max(0, len(pts) - 1) for pts in polys) >= 1


def explode_object(obj):
    """Un objet par segment de `obj` (une ligne = un objet), même calque."""
    segments = []
    for pts in path_to_polylines(obj.world_path()):
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if (a - b).manhattanLength() < 1e-6:
                continue
            seg = QPainterPath()
            seg.moveTo(a)
            seg.lineTo(b)
            child = world_path_to_svg_object(seg, obj.layer_id, source_tag="segment")
            if child is not None:
                segments.append(child)
    return segments


def bake_object(obj):
    """L'objet converti en SvgPathObject à la même place (forme ou texte à
    éditer nœud par nœud), ou None si son tracé est vide."""
    return world_path_to_svg_object(obj.world_path(), obj.layer_id, source_tag=getattr(obj, "kind", "path"))
