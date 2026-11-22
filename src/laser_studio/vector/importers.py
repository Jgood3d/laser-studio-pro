"""Passerelle entre les modules de calcul (vector.dxf, vector.box_generator) et les objets
de l'éditeur vectoriel : crée des SvgPathObject (tracés fixes, comme un SVG importé)
et place texte / SVG de décor sur les faces d'une boîte.

Repère des objets : origine en bas à gauche de la zone de travail, Y vers le haut
(le tracé local, lui, est en Y vers le bas, ancré en bas à gauche de l'objet — voir
extract_svg_objects)."""
from PyQt6.QtGui import QPainterPath

from laser_studio.vector.box_generator import BoxDecor  # noqa: F401  (réexporté : vector.importers.BoxDecor)
from laser_studio.models.vector_objects import SvgPathObject, TextObject
from laser_studio.vector.svg_extract import extract_svg_objects


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


def _compound_path_object(polys, tag, layer_id, shift_x, shift_y):
    """Plusieurs contours fermés (points en mm, Y vers le haut) -> un seul SvgPathObject ancré en bas à gauche."""
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    if not xs:
        return None
    min_x, min_y = min(xs), min(ys)
    path = QPainterPath()
    for poly in polys:
        path.moveTo(poly[0][0] - min_x, -(poly[0][1] - min_y))
        for x, y in poly[1:]:
            path.lineTo(x - min_x, -(y - min_y))
        path.closeSubpath()
    return SvgPathObject(local_path_data=path, source_tag=tag, layer_id=layer_id,
                         x_mm=min_x + shift_x, y_mm=min_y + shift_y)


def jig_to_objects(jig, layer_id, origin_x_mm, origin_y_mm, with_base=False, base_gap_mm=10.0):
    """Gabarit de placement : les poches (un seul objet, découpées en premier) puis le contour de la plaque, et
    éventuellement une plaque de fond pleine posée à droite. (origin_x_mm, origin_y_mm) = coin bas-gauche de la plaque."""
    objects = [_compound_path_object(jig.pockets, "jig:pockets", layer_id, origin_x_mm, origin_y_mm),
               _path_object(jig.plate, True, "jig:plate", layer_id, origin_x_mm, origin_y_mm)]
    if with_base:
        objects.append(_path_object(jig.plate, True, "jig:base", layer_id,
                                    origin_x_mm + jig.plate_w + base_gap_mm, origin_y_mm))
    return [o for o in objects if o is not None]


def dxf_to_objects(drawing, layer_id, offset_x_mm=10.0, offset_y_mm=10.0, ungroup=False):
    """Convertit un DXF en objets vectoriels.

    Par défaut (`ungroup=False`), les tracés sont regroupés **par calque DXF**
    (un SvgPathObject par couche) : l'ensemble d'une couche se manipule d'un
    bloc, et le routage Stencil Studio (CUT / FRAME / ENGRAVE) reste possible.
    Avec `ungroup=True`, un objet par tracé (ancien comportement).

    Le coin inférieur gauche de l'ensemble du dessin est ancré à
    (offset_x_mm, offset_y_mm), positions relatives conservées.
    """
    from laser_studio.vector.svg_extract import _merge_path_objects

    bounds = drawing.bounds()
    if bounds is None:
        return []
    shift_x, shift_y = offset_x_mm - bounds[0], offset_y_mm - bounds[1]
    objects = []
    for path in drawing.paths:
        obj = _path_object(path.points, path.closed, f"dxf:{path.layer}", layer_id, shift_x, shift_y)
        if obj is not None:
            objects.append(obj)

    if ungroup or len(objects) <= 1:
        return objects

    # Regroupe par calque DXF (source_tag = "dxf:<nom>").
    by_layer = {}
    for obj in objects:
        by_layer.setdefault(obj.source_tag, []).append(obj)
    grouped = []
    for tag, objs in by_layer.items():
        if len(objs) == 1:
            grouped.append(objs[0])
        else:
            merged = _merge_path_objects(objs, source_tag=tag)
            grouped.append(merged if merged is not None else objs[0])
    return grouped


def box_to_objects(result, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """[(panneau, objet)] : les fentes de charnière (traits ouverts), les trous (fentes de cloison) puis le
    contour de découpe de chaque panneau, posés selon la disposition calculée. Un panneau peut donc
    apparaître plusieurs fois."""
    out = []
    for panel in result.panels:
        for slit in panel.placed_slits():
            obj = _path_object(slit, False, f"box:{panel.name}:hinge", layer_id, offset_x_mm, offset_y_mm)
            if obj is not None:
                out.append((panel, obj))
        for hole in panel.placed_holes():
            obj = _path_object(hole, True, f"box:{panel.name}:hole", layer_id, offset_x_mm, offset_y_mm)
            if obj is not None:
                out.append((panel, obj))
        obj = _path_object(panel.placed(), True, f"box:{panel.name}", layer_id, offset_x_mm, offset_y_mm)
        if obj is not None:
            out.append((panel, obj))
    return out


def motif_to_objects(result, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Contours gravés du papillon (un objet fermé par contour)."""
    out = []
    for loop in result.motif:
        obj = _path_object(loop, True, "box:motif", layer_id, offset_x_mm, offset_y_mm)
        if obj is not None:
            out.append(obj)
    return out


def index_to_objects(result, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Numéros de pièce gravés : un texte centré sur chaque emplacement trouvé par le générateur."""
    out = []
    for text, x, y, size in result.index:
        obj = TextObject(text=text, font_family="Arial", size_mm=size, bold=False, italic=False,
                         layer_id=layer_id, x_mm=0.0, y_mm=0.0)
        out += center_group([obj], x + offset_x_mm, y + offset_y_mm)
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
    """Objets de décor (texte ou SVG, groupé par défaut) centrés sur la face `panel` de la boîte."""
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


def puzzle_to_objects(result, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Puzzle -> objets de découpe : le contour extérieur (fermé) et UN objet qui regroupe toutes les arêtes
    internes (tracés ouverts, chacune une seule fois).

    On ne crée surtout pas un contour fermé par pièce : deux pièces voisines partagent leur frontière, le
    laser la découperait deux fois."""
    from laser_studio.vector.svg_extract import _merge_path_objects

    objects = []
    outline = _path_object(result.outline, True, "puzzle:outline", layer_id, offset_x_mm, offset_y_mm) \
        if result.outline else None
    if outline is not None:
        objects.append(outline)
    edges = [e for e in (_path_object(points, False, "puzzle:edge", layer_id, offset_x_mm, offset_y_mm)
                         for points in result.edges) if e is not None]
    if edges:
        merged = _merge_path_objects(edges, source_tag="puzzle:edges")
        objects.append(merged if merged is not None else edges[0])
    return objects


def apriltags_to_objects(targets, layer_id):
    """AprilTags d'alignement caméra -> un objet de gravure (remplissage) par tag, aux positions exactes du
    plateau (mm machine : les coordonnées des cibles sont absolues, donc aucun décalage)."""
    from laser_studio.camera.workspace_alignment import apriltag_engrave_polygons

    objects = []
    for target in targets:
        obj = _compound_path_object(apriltag_engrave_polygons(target), f"apriltag:{target.tag_id}",
                                    layer_id, 0.0, 0.0)
        if obj is not None:
            objects.append(obj)
    return objects


def apriltag_template_to_objects(targets, layer_id, bed_w_mm=None, label_mm=4.0):
    """Gabarit de pose des AprilTags imprimés : pour chaque tag, un cadre carré (le côté du tag, aux positions
    exactes du plateau : coordonnées machine absolues) et son numéro, posé à côté du cadre. Le laser les marque sur
    le plateau ; il n'y a plus qu'à coller chaque tag imprimé dans son cadre, sous le bon numéro.

    Le numéro est à droite du cadre, ou à gauche pour les tags de la moitié droite du plateau (`bed_w_mm`)."""
    objects = []
    for target in targets:
        half = target.size_mm / 2.0
        x0, x1 = target.cx_mm - half, target.cx_mm + half
        y0, y1 = target.cy_mm - half, target.cy_mm + half
        frame = _path_object([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True,
                             f"apriltag_frame:{target.tag_id}", layer_id, 0.0, 0.0)
        if frame is not None:
            objects.append(frame)
        text = str(target.tag_id)
        text_w = label_mm * 0.7 * len(text)            # largeur approchée du numéro
        on_left = bed_w_mm is not None and target.cx_mm > bed_w_mm / 2.0
        label_x = x0 - 1.5 - text_w if on_left else x1 + 1.5
        objects.append(TextObject(text=text, font_family="Arial", size_mm=label_mm, layer_id=layer_id,
                                  x_mm=label_x, y_mm=target.cy_mm - label_mm / 2.0))
    return objects


def ornament_to_objects(contours, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Boule de Noël -> objets de découpe : le contour extérieur, et UN objet qui regroupe tous les contours
    intérieurs (trou de la ficelle, contreformes des lettres, vides entre les flocons).

    `contours` vient de `ornament_region.assemble` : le premier est l'extérieur. Chaque contour y est déjà
    unique (la matière est soudée), donc rien n'est découpé deux fois."""
    from laser_studio.vector.svg_extract import _merge_path_objects

    if not contours:
        return []
    objects = []
    outline = _path_object(contours[0], True, "ornament:outline", layer_id, offset_x_mm, offset_y_mm)
    if outline is not None:
        objects.append(outline)
    inner = [o for o in (_path_object(c, True, "ornament:inner", layer_id, offset_x_mm, offset_y_mm)
                         for c in contours[1:]) if o is not None]
    if inner:
        merged = _merge_path_objects(inner, source_tag="ornament:inner")
        objects.append(merged if merged is not None else inner[0])
    return objects

def ornament_engrave_to_objects(name_contours, frame_contours, layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Boule de Noël, prénom gravé -> objets de gravure : UN objet pour le prénom (ses contreformes y restent des
    trous) et UN pour le filet de la bande. Les contours viennent de `ornament_region.assemble_engraving`, dans le
    même repère que ceux de la découpe : la gravure tombe donc exactement sur la bande."""
    objects = []
    for contours, tag in ((name_contours, "ornament:name"), (frame_contours, "ornament:frame")):
        if contours:
            obj = _compound_path_object(contours, tag, layer_id, offset_x_mm, offset_y_mm)
            if obj is not None:
                objects.append(obj)
    return objects


def keychain_to_objects(result, cut_layer_id, engrave_layer_id, offset_x_mm=10.0, offset_y_mm=10.0):
    """Porte-clés -> objets vectoriels.

    Mode classique :
      - trou + contour extérieur de la base sur `cut_layer_id`
      - texte (remplissage) sur `engrave_layer_id`

    Mode 2 couches (deux porte-clés côte à côte par prénom) :
      - GAUCHE (fond) : base découpe + contour prénom en gravure (guide)
      - DROITE (dessus) : base découpe + lettres solides en découpe

    En mode lot (plusieurs prénoms), chaque prénom est traité comme une pièce
    indépendante pour que l'imbrication automatique les regroupe correctement.
    """
    from laser_studio.vector.svg_extract import _merge_path_objects

    objects = []

    def _add_merged(contours, closed, tag, layer_id, ox, oy):
        if not contours:
            return
        objs = [
            o for o in (_path_object(c, closed, tag, layer_id, ox, oy)
                        for c in contours)
            if o is not None
        ]
        if not objs:
            return
        merged = _merge_path_objects(objs, source_tag=tag)
        objects.append(merged if merged is not None else objs[0])

    def _add_base(base_contours, tag_prefix, ox, oy):
        """Contour extérieur + trou(s) dans UN seul objet (imbrication les garde ensemble)."""
        if not base_contours:
            return
        # Un seul SvgPathObject compound : la plaque et son anneau restent liés
        obj = _compound_path_object(
            base_contours, f"{tag_prefix}:plate", cut_layer_id, ox, oy
        )
        if obj is not None:
            objects.append(obj)

    def _emit_one(res, ox, oy):
        """Émet les objets d'un seul porte-clés (éventuellement 2 couches)."""
        two = getattr(res, "two_layers", False)
        if two:
            _add_base(res.base_contours, "keychain:bottom", ox, oy)
            _add_merged(
                getattr(res, "outline_contours", None) or [],
                True, "keychain:glue_guide", engrave_layer_id, ox, oy
            )
            _add_base(getattr(res, "top_base_contours", None) or [], "keychain:top", ox, oy)
            _add_merged(
                getattr(res, "top_text_contours", None) or [],
                True, "keychain:letters", cut_layer_id, ox, oy
            )
        else:
            if res.text_contours:
                _add_merged(res.text_contours, True, "keychain:text", engrave_layer_id, ox, oy)
            _add_base(res.base_contours, "keychain", ox, oy)

    pieces = getattr(result, "pieces", None) or []
    if pieces:
        # Lot : chaque prénom a déjà ses coordonnées locales ; on applique seulement le décalage global
        for res in pieces:
            _emit_one(res, offset_x_mm, offset_y_mm)
    else:
        # Un seul prénom
        _emit_one(result, offset_x_mm, offset_y_mm)

    return objects
