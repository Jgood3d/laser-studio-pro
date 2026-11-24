"""Import SVG qui garde la structure du fichier (bouton « Importer » de l'éditeur vectoriel), d'après la
spécification SVG du W3C (SVG 1.1, et SVG 2 quand il précise) : chaque groupe (<g>, <a>, <svg> imbriqué,
contenu d'un <use>) devient un groupe de l'éditeur (GroupObject), chaque forme ou texte un objet.

Rendu (ce que l'afficheur dessinerait) :
- display:none retire l'élément et tout son contenu ; visibility (hidden, collapse) s'hérite, mais un
  enfant peut repasser en visible ; une opacité nulle (cumulée le long des groupes) cache aussi ;
- styles en cascade et héritage (vector/svg_style.py) : attributs de présentation, feuille <style>,
  attribut style ; fill (noir par défaut), stroke (aucun par défaut), fill-opacity, stroke-opacity ;
- fill-rule : la règle « nonzero » (par défaut) est convertie en un contour lisible en pair-impair, la
  règle de remplissage de l'éditeur ;
- <use> (href ou xlink:href, x, y, contenu d'un <symbol>), <switch> (premier enfant dessinable), <svg>
  imbriqué (x, y, width, height, viewBox, preserveAspectRatio) ; <defs>, <symbol>, <clipPath>… ne se
  dessinent pas par eux-mêmes.

Ce que devient chaque élément dans l'éditeur :
- son calque vient de sa couleur (remplissage, sinon trait), avec une tolérance sur la teinte : noir ou
  gris foncé -> gravure, rouge -> découpe, vert -> marquage ; une autre couleur va sur le calque SVG par
  défaut ;
- le blanc (et les couleurs très claires) n'est pas une couleur de laser : l'objet arrive sur le calque
  « Ignoré » (ni gravé ni découpé). Pour évider une forme, on fait une Différence entre les objets ;
- un texte devient un texte modifiable ;
- ce que l'afficheur ne dessinerait pas (caché) est importé sur le calque « Ignoré » : ni affiché ni
  gravé, avec son calque retenu ; la tête laser de la liste des objets le fait réapparaître ;
- son nom : inkscape:label (le nom donné dans Inkscape), sinon le premier <title> de l'élément.

    objects = import_svg_tree("dessin.svg", lambda role: layers.layer_for_role(role).id, bed_h_mm=300)

Repère : SVG en Y vers le bas ; éditeur en Y vers le haut (origine en bas à gauche). L'appelant place
ensuite le dessin (VectorEditorController.import_objects).
"""
import colorsys
import re
import xml.etree.ElementTree as ET

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainterPath, QTransform

from laser_studio.models.vector_objects import GroupObject, SvgPathObject, TextObject
from laser_studio.vector.boolean_ops import paint_region
from laser_studio.vector.svg_import import (
    NON_RENDERED, ROLE_CUT, ROLE_ENGRAVE, ROLE_MARK, _attr, _document_transform, _fit_text, _length_mm, _local,
    _numbers, _parse, _shape_path, _stroke_outline, _text_glyphs, _text_object, parse_transform,
    viewbox_transform,
)
from laser_studio.vector.svg_geometry import (
    clip_area, clip_lines, css_transform, dash_pattern, dashed, outside_area, transform_origin, user_length,
)
from laser_studio.vector.svg_style import StyleSheet, computed_style, paint_alpha, parse_color

# Couleur claire (blanc) : pas une couleur de laser, objet importé sur le calque « Ignoré ».
LIGHT = "light"
# Teintes de référence (degrés) -> rôle, et écart toléré autour de chacune.
HUE_ROLES = ((0.0, ROLE_CUT), (120.0, ROLE_MARK))
HUE_TOLERANCE = 30.0
# En dessous de cette saturation ou de cette luminosité, la couleur compte comme du noir (ou du gris).
DARK_SATURATION = 0.35
DARK_VALUE = 0.25
# Au-dessus de cette luminance (0 à 1), la couleur est claire (blanc).
LIGHT_LUMINANCE = 0.8
# Échelle des conversions de règle de remplissage (Qt aplatit les courbes à environ une unité près).
FILL_RULE_SCALE = 100.0
# Éléments de forme (SVG 1.1 § 9).
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
# Éléments qui regroupent leur contenu.
CONTAINERS = {"g", "a", "svg"}


def color_role(color, current_color=None):
    """Rôle d'une couleur SVG : ROLE_ENGRAVE (noir, gris foncé), ROLE_CUT (rouge), ROLE_MARK (vert), LIGHT
    (blanc, très clair), ou None (pas de couleur, transparente, dégradé, autre teinte)."""
    parsed = parse_color(color, current_color)
    if parsed is None or parsed[3] <= 0:
        return None
    r, g, b = (v / 255 for v in parsed[:3])
    if 0.2126 * r + 0.7152 * g + 0.0722 * b >= LIGHT_LUMINANCE:
        return LIGHT
    hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)
    if saturation < DARK_SATURATION or value < DARK_VALUE:
        return ROLE_ENGRAVE
    hue *= 360.0
    for reference, role in HUE_ROLES:
        distance = min(abs(hue - reference), 360.0 - abs(hue - reference))
        if distance <= HUE_TOLERANCE:
            return role
    return None


def element_name(elem):
    """Nom lisible : inkscape:label, sinon le texte du premier <title> enfant ; « » sinon (les id
    générés, path42, n'apprennent rien)."""
    label = (_attr(elem, "label") or "").strip()
    if label:
        return label
    for child in elem:
        if _local(child.tag) == "title" and child.text and child.text.strip():
            return child.text.strip()
    return ""


def even_odd_equivalent(path, fill_rule):
    """Tracé à remplir en pair-impair qui couvre la même surface que `path` rempli avec `fill_rule`
    (« nonzero » ou « evenodd »)."""
    if (fill_rule or "nonzero").strip().lower() == "evenodd":
        result = type(path)(path)
        result.setFillRule(Qt.FillRule.OddEvenFill)
        return result
    up = QTransform.fromScale(FILL_RULE_SCALE, FILL_RULE_SCALE)
    scaled = up.map(path)
    scaled.setFillRule(Qt.FillRule.WindingFill)
    result = QTransform.fromScale(1 / FILL_RULE_SCALE, 1 / FILL_RULE_SCALE).map(scaled.simplified())
    result.setFillRule(Qt.FillRule.OddEvenFill)
    return result


class _TreeImport:
    """Parcours du document : `layer_for(rôle)` donne l'identifiant du calque d'un rôle (None : calque SVG par
    défaut)."""

    MAX_USE_DEPTH = 16          # <use> imbriqués : au-delà, référence circulaire

    def __init__(self, root, layer_for, bed_h_mm):
        self.layer_for = layer_for
        self.bed_h_mm = bed_h_mm
        self.sheet = StyleSheet.from_root(root)
        self.ids = {elem.attrib["id"]: elem for elem in root.iter() if "id" in elem.attrib}
        # mm du document (Y vers le bas) -> repère de l'éditeur (Y vers le haut).
        self.flip = QTransform(1, 0, 0, -1, 0, bed_h_mm)
        self._use_depth = 0
        self.viewport = (100.0, 100.0)      # taille de la zone d'affichage, en unités utilisateur
        # Tracés qui sont des contours (pas des surfaces), par id() ; l'objet est gardé pour que Python ne
        # redonne pas son id() à un autre objet si celui-ci est jeté (détourage).
        self._outlines = {}

    # -- objets

    def _place(self, obj, role, hidden, name):
        """Calque d'après le rôle ; caché ou blanc : calque « Ignoré » (le blanc retient le calque SVG par
        défaut)."""
        obj.layer_id = self.layer_for(None if role == LIGHT else role)
        if name:
            obj.name = name
        if hidden or role == LIGHT:
            obj.set_ignored(True)
        return obj

    @staticmethod
    def _make_path(world):
        """Tracé de l'éditeur (SvgPathObject) d'un tracé monde (repère éditeur), ou None s'il est vide."""
        box = world.boundingRect()
        if world.isEmpty() or (box.width() <= 0 and box.height() <= 0):
            return None
        local = QTransform(1, 0, 0, -1, -box.left(), box.top()).map(world)
        return SvgPathObject(local_path_data=local, source_tag="svg", x_mm=box.left(), y_mm=box.top())

    def _path_object(self, path_mm, role, hidden, name, area=True):
        """Objet d'un tracé en mm du document ; `area` : surface remplie (sinon contour)."""
        obj = self._make_path(self.flip.map(path_mm))
        if obj is None:
            return None
        if not area:
            self._outlines[id(obj)] = obj
        return self._place(obj, role, hidden, name)

    def _group(self, children, name):
        group = GroupObject(children, name=name)
        group.child_ignored_changed()       # calque du premier objet visible (« Ignoré » s'il n'y en a aucun)
        return group

    # -- rendu

    @staticmethod
    def _invisible(style, opacity):
        return style.get("visibility", "visible").strip().lower() in ("hidden", "collapse") or opacity <= 0

    # -- longueurs, zone d'affichage

    def _font_size(self, style):
        return user_length(style.get("font-size"), "diag", self.viewport, 16.0, default=16.0)

    def _length_getter(self, elem, style):
        """`length(nom, défaut)` pour _shape_path : attribut de longueur en unités utilisateur."""
        font = self._font_size(style)

        def length(name, default=0.0):
            axis = "x" if name in ("x", "width", "rx", "cx", "x1", "x2") else \
                "y" if name in ("y", "height", "ry", "cy", "y1", "y2") else "diag"
            return user_length(elem.attrib.get(name), axis, self.viewport, font, default)
        return length

    def _normalized(self, style, parent_style):
        """Style dont font-size est en unités utilisateur (em et % : de la police du parent)."""
        size = style.get("font-size")
        if size is None:
            return style
        parent_size = user_length(parent_style.get("font-size"), "diag", self.viewport, 16.0, default=16.0)
        text = str(size).strip()
        if text.endswith("%"):
            value = parent_size * float(text[:-1] or 0) / 100.0
        else:
            value = user_length(text, "diag", self.viewport, parent_size, default=parent_size)
        return {**style, "font-size": f"{value:g}"}

    def _own_transform(self, elem, style):
        """Transformation propre de l'élément : propriété CSS transform (SVG 2, prioritaire), sinon
        l'attribut transform ; transform-origin pris en compte pour la propriété CSS."""
        css = style.get("transform")
        if css and css.strip().lower() != "none":
            origin = transform_origin(style.get("transform-origin") or elem.attrib.get("transform-origin"),
                                      self.viewport, self._font_size(style))
            return css_transform(css, self.viewport, self._font_size(style), origin)
        return parse_transform(elem.attrib.get("transform"))

    # -- formes et textes

    def _shape(self, elem, tag, ctm, style, hidden, name):
        """Objets d'une forme : son remplissage, puis son trait s'il est visible (contour de découpe ou de
        marquage tel quel, en tirets si stroke-dasharray ; trait foncé ou blanc épaissi comme à l'écran, sur
        la gravure)."""
        geometry = _shape_path(elem, tag, self._length_getter(elem, style))
        if geometry is None or geometry.isEmpty():
            return []
        current = style.get("color")
        font = self._font_size(style)
        objects = []
        if paint_alpha(style, "fill") > 0 and tag not in ("line",):
            role = color_role(style.get("fill", "black"), current)
            path = ctm.map(geometry)
            if role in (ROLE_ENGRAVE, LIGHT):
                # Surface remplie : convertie en règle pair-impair, celle du remplissage de l'éditeur.
                path = even_odd_equivalent(path, style.get("fill-rule"))
            objects.append(self._path_object(path, role, hidden, name, area=role in (ROLE_ENGRAVE, LIGHT)))
        width = user_length(style.get("stroke-width"), "diag", self.viewport, font, default=1.0)
        if paint_alpha(style, "stroke") > 0 and width > 0:
            role = color_role(style.get("stroke"), current)
            dashes = dash_pattern(style, self.viewport, font)
            if role in (ROLE_ENGRAVE, LIGHT):
                outline = _stroke_outline(geometry, style, width=width, dashes=dashes)
                path = ctm.map(outline) if outline is not None else None
                area = True
            else:
                path = ctm.map(dashed(geometry, *dashes) if dashes else geometry)
                area = False
            if path is not None and not path.isEmpty():
                objects.append(self._path_object(path, role, hidden, name, area=area))
        return [obj for obj in objects if obj is not None]

    def _text(self, elem, ctm, style, hidden, name):
        """Un texte modifiable par ligne (groupés s'il y en a plusieurs). Sa couleur : celle du remplissage,
        ou du trait pour un texte en contour seul (lettres à découper) ; caché si aucun des deux ne se voit."""
        paint = "fill" if paint_alpha(style, "fill") > 0 else "stroke" if paint_alpha(style, "stroke") > 0 else None
        if paint is None:
            hidden = True
        role = color_role(style.get(paint or "fill", "black"), style.get("color"))
        if style.get("transform") and style["transform"].strip().lower() != "none":
            # Propriété CSS transform : remplace l'attribut, que _text_glyphs appliquerait.
            ctm = self._own_transform(elem, style) * ctm
            elem = _without_transform(elem)
        objects = []
        for run in _text_glyphs(elem, ctm, style):
            obj = _text_object(run)
            _fit_text(obj, run.box, self.bed_h_mm)
            objects.append(self._place(obj, role, hidden, name))
        if len(objects) > 1:
            return [self._group(objects, name)]
        return objects

    def _children(self, elem, ctm, style, depth, hidden, opacity):
        return [obj for child in elem for obj in self.walk(child, ctm, style, depth + 1, hidden, opacity)]

    def _number(self, elem, name, axis="diag"):
        return user_length(elem.attrib.get(name), axis, self.viewport)

    def _viewport_of(self, elem, width, height):
        vb = _numbers(elem.attrib.get("viewBox"))
        return (vb[2], vb[3]) if len(vb) == 4 and vb[2] > 0 and vb[3] > 0 else (width or self.viewport[0],
                                                                                  height or self.viewport[1])

    def _nested_svg(self, elem, ctm):
        """Repère du contenu d'un <svg> imbriqué : décalé de x, y (unités du parent), puis viewBox dans
        width × height selon preserveAspectRatio. Renvoie (repère, zone d'affichage du contenu)."""
        t = QTransform()
        t.translate(self._number(elem, "x", "x"), self._number(elem, "y", "y"))
        vb = _numbers(elem.attrib.get("viewBox"))
        width = user_length(elem.attrib.get("width", "100%"), "x", self.viewport)
        height = user_length(elem.attrib.get("height", "100%"), "y", self.viewport)
        if len(vb) == 4 and vb[2] > 0 and vb[3] > 0 and width > 0 and height > 0:
            t = viewbox_transform(vb, width, height, elem.attrib.get("preserveAspectRatio")) * t
        return t * ctm, self._viewport_of(elem, width, height)

    def _use(self, elem, ctm, style, depth, hidden, opacity, name):
        """Contenu d'un <use> : l'élément référencé, placé en x, y, héritant du style du <use>."""
        href = (_attr(elem, "href") or "").strip()
        target = self.ids.get(href[1:]) if href.startswith("#") else None
        if target is None or self._use_depth >= self.MAX_USE_DEPTH:
            return []
        shift = QTransform()
        shift.translate(self._number(elem, "x", "x"), self._number(elem, "y", "y"))
        ctm = shift * ctm
        self._use_depth += 1
        saved_viewport = self.viewport
        try:
            if _local(target.tag) == "symbol":
                symbol_style = self._normalized(computed_style(target, style, self.sheet), style)
                vb = _numbers(target.attrib.get("viewBox"))
                width = user_length(elem.attrib.get("width", "100%"), "x", self.viewport)
                height = user_length(elem.attrib.get("height", "100%"), "y", self.viewport)
                if len(vb) == 4 and vb[2] > 0 and vb[3] > 0 and width > 0 and height > 0:
                    ctm = viewbox_transform(vb, width, height, target.attrib.get("preserveAspectRatio")) * ctm
                self.viewport = self._viewport_of(target, width, height)
                children = self._children(target, ctm, symbol_style, depth, hidden, opacity)
            else:
                children = self.walk(target, ctm, style, depth + 1, hidden, opacity)
        finally:
            self._use_depth -= 1
            self.viewport = saved_viewport
        if not children:
            return []
        return [self._group(children, name or element_name(target))]

    # -- clipPath, mask

    def _reference(self, value, tag):
        """Élément <tag> désigné par « url(#id) », ou None."""
        match = re.fullmatch(r"\s*url\(\s*['\"]?#([^'\")]+)['\"]?\s*\)\s*", value or "")
        target = self.ids.get(match.group(1)) if match else None
        return target if target is not None and _local(target.tag) == tag else None

    def _zone_shapes(self, container, ctm, parent_style, mask=False):
        """[(tracé en mm du document, clair)] des formes et textes d'un <clipPath> ou d'un <mask>, en
        respectant display, visibility, transform, clip-rule (clipPath) et fill-rule (mask)."""
        result = []
        for child in container:
            tag = _local(child.tag)
            style = self._normalized(computed_style(child, parent_style, self.sheet), parent_style)
            if style.get("display", "inline").strip().lower() == "none" or self._invisible(style, 1.0):
                continue
            own = self._own_transform(child, style) * ctm
            if tag == "use":
                href = (_attr(child, "href") or "").strip()
                target = self.ids.get(href[1:]) if href.startswith("#") else None
                if target is not None:
                    shift = QTransform()
                    shift.translate(self._number(child, "x", "x"), self._number(child, "y", "y"))
                    wrapper = [target]
                    result += self._zone_shapes(wrapper, shift * own, style, mask)
                continue
            if tag == "g" and mask:
                result += self._zone_shapes(child, own, style, mask)
                continue
            if tag == "text":
                path = QPainterPath()
                for run in _text_glyphs(child, ctm, style):
                    path.addPath(run.path)
            elif tag in SHAPES:
                geometry = _shape_path(child, tag, self._length_getter(child, style))
                if geometry is None:
                    continue
                path = own.map(geometry)
            else:
                continue
            rule = style.get("fill-rule" if mask else "clip-rule")
            light = True
            if mask:
                color = parse_color(style.get("fill", "black"), style.get("color"))
                if color is None or paint_alpha(style, "fill") <= 0:
                    continue
                r, g, b = (v / 255 for v in color[:3])
                light = (0.2126 * r + 0.7152 * g + 0.0722 * b) * paint_alpha(style, "fill") >= 0.5
            result.append((even_odd_equivalent(path, rule), light))
        return result

    def _zone(self, style, own, objects):
        """Zone visible (mm du document, Y vers le bas) d'après clip-path et mask, ou None sans eux. Unités
        objectBoundingBox : rapportées à l'encombrement des objets produits par l'élément."""
        zone = None
        for prop, tag in (("clip-path", "clipPath"), ("mask", "mask")):
            target = self._reference(style.get(prop), tag)
            if target is None:
                continue
            units_attr = "clipPathUnits" if tag == "clipPath" else "maskContentUnits"
            default_units = "userSpaceOnUse"
            base = own
            if (target.attrib.get(units_attr) or default_units) == "objectBoundingBox":
                box = self._objects_box_user(objects, own)
                if box is None:
                    return QPainterPath()
                base = QTransform(box.width(), 0, 0, box.height(), box.left(), box.top()) * own
            if tag == "clipPath":
                base = parse_transform(target.attrib.get("transform")) * base
            container_style = computed_style(target, {}, self.sheet)
            shapes = self._zone_shapes(target, base, container_style, mask=tag == "mask")
            if tag == "clipPath":
                region = QPainterPath()
                region.setFillRule(Qt.FillRule.WindingFill)
                for path, _light in shapes:
                    region.addPath(even_odd_equivalent(path, "evenodd"))
                region = even_odd_equivalent(region, "nonzero")
            else:
                # Masque : visible là où son contenu est clair (luminance), dans l'ordre du dessin.
                region = paint_region([(path, not light) for path, light in shapes])
            zone = region if zone is None else clip_area(zone, region)
        return zone

    def _objects_box_user(self, objects, own):
        """Encombrement des objets (repère éditeur) ramené dans le repère utilisateur de l'élément."""
        box = None
        for obj in objects:
            rect = full_world_path(obj).boundingRect()
            if rect.isNull():
                continue
            box = rect if box is None else box.united(rect)
        if box is None:
            return None
        inverse, ok = own.inverted()
        if not ok:
            return None
        return inverse.map(self.flip.map(QPainterPath(_rect_path(box)))).boundingRect()

    def _clip(self, obj, zone):
        """L'objet restreint à la zone (repère éditeur), ou None s'il n'en reste rien. Une surface est
        découpée ; un contour (découpe, marquage) garde ses parties dans la zone ; un texte reste modifiable
        s'il est entièrement dans la zone, sinon il devient un tracé."""
        if isinstance(obj, GroupObject):
            children = [c for c in (self._clip(child, zone) for child in obj.children) if c is not None]
            if not children:
                return None
            obj.children = children
            obj.child_ignored_changed()
            return obj
        world = obj.world_path()
        if isinstance(obj, TextObject):
            if outside_area(world, zone).isEmpty():
                return obj
            world = clip_area(world, zone)
            if world.isEmpty():
                return None
            replacement = self._make_path(world)
            for attr in ("layer_id", "saved_layer_id", "name", "hidden"):
                if hasattr(obj, attr):
                    setattr(replacement, attr, getattr(obj, attr))
            return replacement
        clipped = clip_lines(world, zone) if id(obj) in self._outlines else clip_area(world, zone)
        if clipped.isEmpty():
            return None
        fresh = self._make_path(clipped)
        obj._local_path_data, obj.x_mm, obj.y_mm = fresh._local_path_data, fresh.x_mm, fresh.y_mm
        return obj

    # -- parcours

    def walk(self, elem, ctm, parent_style, depth, hidden, opacity):
        """Objets de `elem` et de son contenu, dans l'ordre du dessin (du dessous vers le dessus).
        `hidden` : un ancêtre ne se dessine pas (display:none) ; `opacity` : opacité cumulée des ancêtres."""
        tag = _local(elem.tag)
        if tag in NON_RENDERED or tag in ("image", "foreignObject"):
            return []
        style = self._normalized(computed_style(elem, parent_style, self.sheet), parent_style)
        if style.get("display", "inline").strip().lower() == "none":
            hidden = True
        try:
            opacity *= max(0.0, min(1.0, float(style.get("opacity", "1"))))
        except ValueError:
            pass
        name = element_name(elem)
        own = self._own_transform(elem, style) * ctm
        saved_viewport = self.viewport
        try:
            objects = self._render(elem, tag, ctm, own, style, depth, hidden, opacity, name)
        finally:
            self.viewport = saved_viewport
        if objects and (style.get("clip-path") or style.get("mask")):
            zone = self._zone(style, own, objects)
            if zone is not None:
                zone_editor = self.flip.map(zone)
                objects = [o for o in (self._clip(obj, zone_editor) for obj in objects) if o is not None]
        return objects

    def _render(self, elem, tag, ctm, own, style, depth, hidden, opacity, name):
        if tag == "text":
            return self._text(elem, ctm, style, hidden or self._invisible(style, opacity), name)
        if tag == "use":
            return self._use(elem, own, style, depth, hidden, opacity, name)
        if tag == "switch":
            for child in elem:
                if _local(child.tag) not in NON_RENDERED:
                    return self.walk(child, own, style, depth + 1, hidden, opacity)
            return []
        if tag in CONTAINERS:
            if tag == "svg" and depth > 0:
                own, self.viewport = self._nested_svg(elem, own)
            children = self._children(elem, own, style, depth, hidden, opacity)
            if depth == 0 or not children:
                return children
            return [self._group(children, name)]
        if tag in SHAPES:
            return self._shape(elem, tag, own, style, hidden or self._invisible(style, opacity), name)
        return []


def _rect_path(rect):
    path = QPainterPath()
    path.addRect(rect)
    return path


def full_world_path(obj):
    """Tracé monde de l'objet, objets ignorés d'un groupe compris (encombrement pour objectBoundingBox)."""
    if isinstance(obj, GroupObject):
        return obj.world_transform().map(obj.full_local_path())
    return obj.world_path()


def _without_transform(elem):
    """Copie de l'élément sans son attribut transform (remplacé par la propriété CSS transform)."""
    copy = ET.Element(elem.tag, {k: v for k, v in elem.attrib.items() if k != "transform"})
    copy.text, copy.tail = elem.text, elem.tail
    copy.extend(list(elem))
    return copy


# Logiciels dont le « px » n'est pas celui de CSS (96 par pouce) : (repère dans le fichier, px par pouce).
LEGACY_PX = 90.0          # Inkscape avant 0.92
ILLUSTRATOR_PX = 72.0     # Adobe Illustrator


def document_px_mm(path, root):
    """Taille d'un px du document en mm : 25,4 / 96 (CSS, la règle), sauf pour les fichiers d'Inkscape
    antérieurs à 0.92 (90 px par pouce) et d'Adobe Illustrator (72 px par pouce), qui ne la suivaient pas.
    Ne compte que pour un document dont la taille est en px ou sans unité."""
    inkscape = next((v for k, v in root.attrib.items() if k.endswith("}version") and "inkscape" in k), "")
    match = re.match(r"\s*(\d+)\.(\d+)", inkscape or "")
    if match and (int(match.group(1)), int(match.group(2))) < (0, 92):
        return 25.4 / LEGACY_PX
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(2048)
    except OSError:
        head = ""
    if "Adobe Illustrator" in head:
        return 25.4 / ILLUSTRATOR_PX
    return 25.4 / 96.0


def import_svg_tree(path, layer_for, bed_h_mm):
    """Objets du SVG `path`, du dessous vers le dessus : un groupe par groupe du fichier. `layer_for(rôle)` :
    identifiant du calque d'un rôle (ROLE_ENGRAVE, ROLE_CUT, ROLE_MARK) ou, pour None, du calque SVG par
    défaut. Lève SvgImportError si le fichier est illisible."""
    root = _parse(path)
    walker = _TreeImport(root, layer_for, bed_h_mm)
    px_mm = document_px_mm(path, root)
    vb = _numbers(root.attrib.get("viewBox"))
    if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
        walker.viewport = (vb[2], vb[3])
    else:
        width = _length_mm(root.attrib.get("width"), px_mm=px_mm)
        height = _length_mm(root.attrib.get("height"), px_mm=px_mm)
        walker.viewport = ((width or 0) / px_mm or 100.0, (height or 0) / px_mm or 100.0)
    return walker.walk(root, _document_transform(root, px_mm), {}, 0, False, 1.0)


def svg_tree_counts(objects, layers):
    """{"count": objets importés, "hidden": dont cachés (calque « Ignoré »), "layers": calques utilisés}
    pour le message de fin d'import ; `layers` : LayersModel."""
    leaves = []

    def collect(obj):
        children = getattr(obj, "children", None)
        if children:
            for child in children:
                collect(child)
        else:
            leaves.append(obj)

    for obj in objects:
        collect(obj)
    names = []
    for obj in leaves:
        layer = layers.get(obj.layer_id) if not obj.is_ignored() else None
        if layer is not None and layer.name not in names:
            names.append(layer.name)
    return {"count": len(leaves), "hidden": sum(1 for o in leaves if o.is_ignored()),
            "layers": ", ".join(names) or "—"}
