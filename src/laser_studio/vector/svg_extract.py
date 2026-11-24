"""Lecture des tracés SVG (attribut d de <path>) en QPainterPath, arcs compris, et fusion de tracés en un
objet. Utilisé par les importeurs SVG (vector/svg_tree_import.py, vector/svg_import.py) et par
path_ops (sous-tracés)."""
import math
from svg.path import parse_path, Move, Line, Close, CubicBezier, QuadraticBezier, Arc
from PyQt6.QtGui import QPainterPath, QTransform
from laser_studio.models.vector_objects import SvgPathObject


def _arc_to_cubics(path, arc):
    """Ajoute à `path` l'arc d'ellipse `arc` (svg.path.Arc : centre, rayons, rotation, angle de départ et
    balayage en degrés) en cubiques de Bézier d'au plus 90° chacune (écart inférieur à 0,03 % du rayon), sans
    dépendre de l'unité du document. Un arc dégénéré (rayon nul) est un segment, comme le veut SVG."""
    scale = getattr(arc, "radius_scale", 1.0) or 1.0
    rx, ry = abs(arc.radius.real) * scale, abs(arc.radius.imag) * scale
    if rx == 0 or ry == 0 or arc.delta == 0:
        path.lineTo(arc.end.real, arc.end.imag)
        return
    phi = math.radians(arc.rotation)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)

    def point(t):
        x, y = rx * math.cos(t), ry * math.sin(t)
        return arc.center.real + cos_phi * x - sin_phi * y, arc.center.imag + sin_phi * x + cos_phi * y

    def tangent(t):
        x, y = -rx * math.sin(t), ry * math.cos(t)
        return cos_phi * x - sin_phi * y, sin_phi * x + cos_phi * y

    pieces = max(1, math.ceil(abs(arc.delta) / 90.0 - 1e-9))
    step = math.radians(arc.delta) / pieces
    k = 4.0 / 3.0 * math.tan(step / 4.0)
    t = math.radians(arc.theta)
    for _ in range(pieces):
        (x1, y1), (dx1, dy1) = point(t), tangent(t)
        (x2, y2), (dx2, dy2) = point(t + step), tangent(t + step)
        path.cubicTo(x1 + k * dx1, y1 + k * dy1, x2 - k * dx2, y2 - k * dy2, x2, y2)
        t += step


def _svg_path_element_to_subpaths(d):
    """Convertit le 'd' d'un <path> SVG en une liste de QPainterPath
    INDÉPENDANTS, un par sous-tracé (une commande M/m démarre un nouveau
    sous-tracé). Utilisé par le dégroupage manuel (clic droit).

    Les courbes de Bézier sont converties EXACTEMENT (cubicTo/quadTo, pas
    d'échantillonnage) ; les arcs d'ellipse deviennent des cubiques (voir
    _arc_to_cubics), quelle que soit l'unité du fichier."""
    parsed = parse_path(d)
    paths = []
    current = None
    for seg in parsed:
        if isinstance(seg, Move):
            if current is not None and current.elementCount() > 0:
                paths.append(current)
            current = QPainterPath()
            current.moveTo(seg.end.real, seg.end.imag)
            continue
        if current is None:
            current = QPainterPath()
            current.moveTo(seg.start.real, seg.start.imag)
        if isinstance(seg, (Line, Close)):
            current.lineTo(seg.end.real, seg.end.imag)
        elif isinstance(seg, CubicBezier):
            current.cubicTo(seg.control1.real, seg.control1.imag,
                             seg.control2.real, seg.control2.imag,
                             seg.end.real, seg.end.imag)
        elif isinstance(seg, QuadraticBezier):
            current.quadTo(seg.control.real, seg.control.imag,
                            seg.end.real, seg.end.imag)
        elif isinstance(seg, Arc):
            _arc_to_cubics(current, seg)
    if current is not None and current.elementCount() > 0:
        paths.append(current)
    return paths


def _svg_path_element_to_single(d):
    """Comme _svg_path_element_to_subpaths, mais renvoie UN seul QPainterPath
    contenant tous les sous-tracés (import groupé par défaut)."""
    combined = QPainterPath()
    for qp in _svg_path_element_to_subpaths(d):
        combined.addPath(qp)
    return combined


def _qpainterpath_to_subpaths(path):
    """Découpe un QPainterPath en sous-tracés indépendants (un par MoveTo).
    Préserve lignes et cubiques ; les autres types sont ramenés en lineTo."""
    paths = []
    current = None
    i = 0
    n = path.elementCount()
    while i < n:
        el = path.elementAt(i)
        et = el.type
        if et == QPainterPath.ElementType.MoveToElement:
            if current is not None and current.elementCount() > 0:
                paths.append(current)
            current = QPainterPath()
            current.moveTo(el.x, el.y)
            i += 1
        elif et == QPainterPath.ElementType.LineToElement:
            if current is None:
                current = QPainterPath()
                current.moveTo(el.x, el.y)
            else:
                current.lineTo(el.x, el.y)
            i += 1
        elif et == QPainterPath.ElementType.CurveToElement:
            # CurveTo + CurveToData + CurveToData
            if current is None:
                current = QPainterPath()
                current.moveTo(el.x, el.y)
                i += 1
                continue
            c1x, c1y = el.x, el.y
            if i + 2 < n:
                c2 = path.elementAt(i + 1)
                end = path.elementAt(i + 2)
                current.cubicTo(c1x, c1y, c2.x, c2.y, end.x, end.y)
                i += 3
            else:
                current.lineTo(c1x, c1y)
                i += 1
        else:
            if current is None:
                current = QPainterPath()
                current.moveTo(el.x, el.y)
            else:
                current.lineTo(el.x, el.y)
            i += 1
    if current is not None and current.elementCount() > 0:
        paths.append(current)
    return paths


def _merge_path_objects(objects, source_tag="group"):
    """Fusionne plusieurs SvgPathObject en un seul (même logique que group_selected).
    Les objets d'entrée doivent déjà être dans le repère monde cohérent."""
    if not objects:
        return None
    if len(objects) == 1:
        return objects[0]
    combined = QPainterPath()
    for obj in objects:
        combined.addPath(obj.world_path())
    bbox = combined.boundingRect()
    if bbox.isNull() or (bbox.width() <= 0 and bbox.height() <= 0):
        return objects[0]
    x0, y0 = bbox.left(), bbox.top()
    to_local = QTransform(1, 0, 0, -1, -x0, y0)
    local = to_local.map(combined)
    return SvgPathObject(
        local_path_data=local, source_tag=source_tag,
        layer_id=objects[0].layer_id, x_mm=x0, y_mm=y0,
    )
