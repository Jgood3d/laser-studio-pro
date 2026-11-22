"""Import SVG classique (extract_svg_objects) : tracés et textes d'un fichier
SVG en objets de l'éditeur vectoriel. Le nouvel importeur, utilisé par la
bibliothèque, est vector/svg_import.py."""
import re
from svg.path import parse_path, Move, Line, Close, CubicBezier, QuadraticBezier, Arc
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath, QTransform, QPolygonF
from laser_studio.models.vector_objects import SvgPathObject


def _svg_path_element_to_subpaths(d):
    """Convertit le 'd' d'un <path> SVG en une liste de QPainterPath
    INDÉPENDANTS, un par sous-tracé (une commande M/m démarre un nouveau
    sous-tracé). Utilisé par le dégroupage manuel (clic droit).

    Les courbes de Bézier sont converties EXACTEMENT (cubicTo/quadTo, pas
    d'échantillonnage) ; seuls les arcs (rares en pratique) sont échantillonnés
    faute d'équivalent direct dans QPainterPath."""
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
            try:
                length = seg.length()
            except Exception:
                length = 0
            n = max(4, int(length / 0.3)) if length else 8
            for i in range(1, n + 1):
                pt = seg.point(i / n)
                current.lineTo(pt.real, pt.imag)
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


def extract_svg_objects(svg_path, layer_id, bed_h_mm, offset_x_mm=10.0, offset_y_mm=10.0,
                        ungroup=False):
    """Importe un fichier SVG dans l'éditeur vectoriel.

    Par défaut (`ungroup=False`), tout le dessin est importé comme **un seul**
    objet groupé : on le déplace / redimensionne / assigne à un calque d'un bloc.
    Le dégroupage (séparation en tracés indépendants) se fait ensuite à la
    demande via le menu contextuel (clic droit → Dégrouper).

    Avec `ungroup=True`, chaque tracé/sous-tracé devient un objet indépendant
    (ancien comportement).

    Convention : 1 unité SVG = 1 mm. Les positions relatives sont conservées ;
    l'ensemble est translaté pour ancrer son coin inférieur gauche à
    (offset_x_mm, offset_y_mm). Utilisé par l'import SVG, PNG→SVG, décor de
    boîte et Stencil Studio.
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(svg_path)
    root = tree.getroot()

    def local_tag(elem):
        return elem.tag.split('}')[-1]

    # Parent map pour retrouver le <g id="CUT|FRAME|ENGRAVE|LAYER_n"> englobant
    parent_map = {c: p for p in root.iter() for c in list(p)}

    def ancestor_group_id(elem):
        cur = elem
        while cur is not None:
            if local_tag(cur) == "g":
                gid = cur.attrib.get("id") or cur.attrib.get("label")
                if not gid:
                    # inkscape:label éventuel
                    for k, v in cur.attrib.items():
                        if k.endswith("label") and v:
                            gid = v
                            break
                if gid:
                    return str(gid).strip()
            cur = parent_map.get(cur)
        return None

    def source_tag_for(elem, geom_tag):
        gid = ancestor_group_id(elem)
        if gid:
            return f"svg:{gid}"
        return geom_tag

    raw = []  # (QPainterPath en coordonnées SVG brutes Y-bas, source_tag)

    for elem in root.iter():
        tag = local_tag(elem)
        try:
            if tag == 'path':
                d = elem.attrib.get('d')
                if not d:
                    continue
                st = source_tag_for(elem, tag)
                if ungroup:
                    # Sépare chaque sous-tracé (M/m) en objet indépendant.
                    for qp in _svg_path_element_to_subpaths(d):
                        raw.append((qp, st))
                else:
                    # Garde le <path> entier (éventuellement multi-sous-tracés)
                    # comme une seule géométrie ; le fusion globale plus bas
                    # regroupera aussi les autres éléments du fichier.
                    qp = _svg_path_element_to_single(d)
                    if qp.elementCount() > 0:
                        raw.append((qp, st))
            elif tag == 'rect':
                x = float(elem.attrib.get('x', 0)); y = float(elem.attrib.get('y', 0))
                w = float(elem.attrib.get('width', 0)); h = float(elem.attrib.get('height', 0))
                if w > 0 and h > 0:
                    qp = QPainterPath()
                    qp.addRect(x, y, w, h)
                    raw.append((qp, source_tag_for(elem, tag)))
            elif tag == 'circle':
                cx = float(elem.attrib.get('cx', 0)); cy = float(elem.attrib.get('cy', 0))
                r = float(elem.attrib.get('r', 0))
                if r > 0:
                    qp = QPainterPath()
                    qp.addEllipse(cx - r, cy - r, 2 * r, 2 * r)
                    raw.append((qp, source_tag_for(elem, tag)))
            elif tag == 'ellipse':
                cx = float(elem.attrib.get('cx', 0)); cy = float(elem.attrib.get('cy', 0))
                rx = float(elem.attrib.get('rx', 0)); ry = float(elem.attrib.get('ry', 0))
                if rx > 0 and ry > 0:
                    qp = QPainterPath()
                    qp.addEllipse(cx - rx, cy - ry, 2 * rx, 2 * ry)
                    raw.append((qp, source_tag_for(elem, tag)))
            elif tag in ('polygon', 'polyline'):
                pts_str = elem.attrib.get('points', '')
                coords = [float(v) for v in re.split(r'[\s,]+', pts_str.strip()) if v]
                if len(coords) >= 4:
                    poly = QPolygonF([QPointF(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)])
                    qp = QPainterPath()
                    qp.addPolygon(poly)
                    if tag == 'polygon':
                        qp.closeSubpath()
                    raw.append((qp, source_tag_for(elem, tag)))
            elif tag == 'line':
                x1 = float(elem.attrib.get('x1', 0)); y1 = float(elem.attrib.get('y1', 0))
                x2 = float(elem.attrib.get('x2', 0)); y2 = float(elem.attrib.get('y2', 0))
                qp = QPainterPath()
                qp.moveTo(x1, y1)
                qp.lineTo(x2, y2)
                raw.append((qp, source_tag_for(elem, tag)))
        except Exception:
            continue

    objects = []
    for qp, tag in raw:
        bbox = qp.boundingRect()
        if bbox.width() <= 0 and bbox.height() <= 0:
            continue
        reanchor = QTransform()
        reanchor.translate(-bbox.left(), -bbox.bottom())
        local = reanchor.map(qp)

        world_x = bbox.left()
        world_y = bed_h_mm - bbox.bottom()

        obj = SvgPathObject(local_path_data=local, source_tag=tag,
                             layer_id=layer_id, x_mm=world_x, y_mm=world_y)
        objects.append(obj)

    if objects:
        # Translation en bloc de tout le dessin importé (positions relatives
        # entre tracés inchangées) pour ancrer son coin inférieur gauche à
        # l'offset demandé au lieu de l'ancrage brut issu du SVG.
        min_x = min(obj.x_mm for obj in objects)
        min_y = min(obj.y_mm for obj in objects)
        delta_x = offset_x_mm - min_x
        delta_y = offset_y_mm - min_y
        for obj in objects:
            obj.x_mm += delta_x
            obj.y_mm += delta_y

        # Import groupé : un seul objet pour tout le fichier.
        if not ungroup and len(objects) > 1:
            merged = _merge_path_objects(objects, source_tag="svg_group")
            if merged is not None:
                objects = [merged]

    return objects
