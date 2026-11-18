"""Import SVG complet, pour les modèles de la bibliothèque (et, une fois
validé, pour remplacer extract_svg_objects de vector_layers.py).

Par rapport à l'import SVG classique, il prend en compte :
- les unités du document (width / height / viewBox) : 1 unité ≠ 1 mm ;
- les transformations (transform="translate(...) matrix(...)..."), cumulées ;
- les éléments et calques cachés (display:none, visibility:hidden) : ignorés ;
- les calques Inkscape « Découpe », « Gravure », « Marquage » : chaque tracé
  va sur le calque de même rôle de l'éditeur (voir role_of_label) ;
- les textes (<text>, <tspan>) : objets texte modifiables de l'éditeur ;
- les variantes : un groupe dont les sous-éléments nommés sont tous cachés
  sauf un (ex. « Niveau 1 », « Niveau 2 », « Bronze »...) ; l'élément choisi
  (paramètre `variants`) est importé, les autres non.

    artwork = import_svg("totem.svg", variants={"Niveau du brevet": "Bronze"})
    for role, obj in artwork.items:      # role : "cut", "engrave", "mark"
        obj.layer_id = layer_for(role)

Repère : SVG en Y vers le bas ; éditeur en Y vers le haut (origine en bas à
gauche), le dessin ancré par son coin inférieur gauche à (offset_x, offset_y).
"""
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QFont, QPainterPath, QPolygonF, QTransform

from laser_studio.vector_layers import (
    SvgPathObject, TextObject, _merge_path_objects, _svg_path_element_to_single,
)

ROLE_CUT = "cut"
ROLE_ENGRAVE = "engrave"
ROLE_MARK = "mark"

# Mots-clés des noms de calques ou de groupes -> rôle (comparés sans accents,
# en minuscules).
ROLE_KEYWORDS = (
    (ROLE_CUT, ("decoup", "coupe", "cut")),
    (ROLE_ENGRAVE, ("grav", "engrav", "remplissage", "fill")),
    (ROLE_MARK, ("marqu", "mark", "contour", "trait")),
)

# Éléments dont le contenu ne se dessine pas.
NON_RENDERED = {"defs", "metadata", "title", "desc", "namedview", "clipPath", "mask",
                "symbol", "marker", "pattern", "linearGradient", "radialGradient", "style",
                "script", "filter"}

# Taille d'une unité, en mm.
UNIT_MM = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72, "pc": 25.4 / 6, "px": 25.4 / 96,
           "": 25.4 / 96}

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"


class SvgImportError(Exception):
    """Fichier SVG illisible."""


@dataclass
class VariantGroup:
    """Groupe de variantes : `key` (identifiant du groupe, passé dans
    `variants`), `label` (nom affiché), `options` [(clé, nom)] et l'option
    visible dans le fichier (`default`)."""
    key: str
    label: str
    options: list
    default: str


@dataclass
class ImportedArtwork:
    """Résultat de import_svg : [(rôle, objet de l'éditeur)], et la taille du
    dessin en mm."""
    items: list = field(default_factory=list)
    width_mm: float = 0.0
    height_mm: float = 0.0

    @property
    def objects(self):
        return [obj for _role, obj in self.items]


# -- lecture des attributs

def _local(tag):
    return tag.split("}")[-1] if isinstance(tag, str) else ""


def _attr(elem, name):
    """Attribut `name`, avec ou sans espace de noms (inkscape:label...)."""
    if name in elem.attrib:
        return elem.attrib[name]
    for key, value in elem.attrib.items():
        if key.split("}")[-1] == name:
            return value
    return None


def _style(elem):
    """Propriétés de style de l'élément : attribut style="a:b;c:d" et
    attributs de présentation (fill="...", display="...")."""
    props = {}
    for name in ("display", "visibility", "fill", "stroke", "font-family", "font-size",
                 "font-weight", "font-style", "text-anchor", "opacity"):
        value = elem.attrib.get(name)
        if value is not None:
            props[name] = value.strip()
    for part in (elem.attrib.get("style") or "").split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            props[key.strip()] = value.strip()
    return props


def _is_hidden(elem):
    style = _style(elem)
    return (style.get("display") == "none" or style.get("visibility") in ("hidden", "collapse")
            or style.get("opacity") in ("0", "0.0"))


def _label(elem):
    """Nom lisible : inkscape:label, sinon id."""
    return (_attr(elem, "label") or elem.attrib.get("id") or "").strip()


def _plain(text):
    """Minuscules sans accents, pour comparer des noms."""
    table = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")
    return text.lower().translate(table)


def role_of_label(label):
    """Rôle d'un calque ou d'un groupe d'après son nom (« Découpes » -> cut,
    « Gravure » -> engrave, « Marquage » -> mark), ou None."""
    plain = _plain(label or "")
    for role, keywords in ROLE_KEYWORDS:
        if any(word in plain for word in keywords):
            return role
    return None


def _length_mm(value, default_unit=""):
    """Longueur SVG (« 30mm », « 12.5 », « 1in ») en mm, ou None."""
    if value is None:
        return None
    match = re.fullmatch(r"\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)\s*([a-z%]*)\s*", value)
    if not match or match.group(2) == "%":
        return None
    unit = match.group(2) or default_unit
    return float(match.group(1)) * UNIT_MM.get(unit, UNIT_MM["px"])


def _numbers(text):
    return [float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", text or "")]


def parse_transform(text):
    """Attribut transform -> QTransform (repère de l'élément -> repère parent)."""
    result = QTransform()
    for name, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", text or ""):
        v = _numbers(args)
        t = QTransform()
        if name == "matrix" and len(v) == 6:
            t = QTransform(v[0], v[1], v[2], v[3], v[4], v[5])
        elif name == "translate" and v:
            t.translate(v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale" and v:
            t.scale(v[0], v[1] if len(v) > 1 else v[0])
        elif name == "rotate" and v:
            if len(v) >= 3:
                t.translate(v[1], v[2])
                t.rotate(v[0])
                t.translate(-v[1], -v[2])
            else:
                t.rotate(v[0])
        elif name == "skewX" and v:
            t = QTransform(1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY" and v:
            t = QTransform(1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        # Transformations listées de gauche à droite : la dernière s'applique en premier.
        result = t * result
    return result


def _document_transform(root):
    """Unités du document -> mm (viewBox, width, height)."""
    vb = _numbers(root.attrib.get("viewBox"))
    width = _length_mm(root.attrib.get("width"))
    height = _length_mm(root.attrib.get("height"))
    t = QTransform()
    if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
        sx = (width / vb[2]) if width else UNIT_MM["px"]
        sy = (height / vb[3]) if height else sx
        if not width and height:
            sx = sy
        t.scale(sx, sy)
        t.translate(-vb[0], -vb[1])
    else:
        t.scale(UNIT_MM["px"], UNIT_MM["px"])
    return t


def _parse(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise SvgImportError(str(e)) from e


# -- variantes

def _variant_options(group):
    """[(clé, nom, visible)] si `group` est un groupe de variantes (au moins
    deux sous-éléments nommés, un seul visible au plus, au moins un caché),
    sinon None."""
    children = [c for c in group if _local(c.tag) not in NON_RENDERED and _label(c)]
    if len(children) < 2:
        return None
    visible = [c for c in children if not _is_hidden(c)]
    if len(visible) > 1 or len(visible) == len(children):
        return None
    return [(_label(c), _label(c), not _is_hidden(c)) for c in children]


def find_variant_groups(path):
    """Groupes de variantes du fichier (voir VariantGroup), dans l'ordre du
    document. Le calque racine des calques n'en est jamais un (un calque de
    construction caché n'est pas une variante)."""
    root = _parse(path)
    groups = []

    def walk(elem, depth):
        if _local(elem.tag) in NON_RENDERED or (depth > 0 and _is_hidden(elem)):
            return
        if depth > 0 and _local(elem.tag) == "g":
            options = _variant_options(elem)
            if options:
                default = next((key for key, _n, visible in options if visible), options[0][0])
                groups.append(VariantGroup(_label(elem), _label(elem),
                                           [(key, name) for key, name, _v in options], default))
                return
        for child in elem:
            walk(child, depth + 1)

    walk(root, 0)
    return groups


# -- import

def import_svg(path, variants=None, offset_x_mm=10.0, offset_y_mm=10.0, bed_h_mm=0.0,
               default_role=None):
    """Lit le SVG `path` et renvoie un ImportedArtwork : les tracés de chaque
    rôle groupés en un objet, chaque texte en objet texte. `variants` :
    {clé du groupe: clé de l'option} (voir find_variant_groups ; option
    visible dans le fichier si absente). `default_role` : rôle d'un tracé hors
    calque nommé (sinon : rempli -> gravure, contour seul -> découpe)."""
    root = _parse(path)
    variants = variants or {}
    shapes = {}          # rôle -> [QPainterPath en mm, Y vers le bas]
    texts = []           # (rôle, TextObject, boîte cible en mm Y vers le bas)

    def role_for(style, inherited):
        if inherited:
            return inherited
        if default_role:
            return default_role
        fill = style.get("fill", "black")
        return ROLE_ENGRAVE if fill not in ("none", "transparent") else ROLE_CUT

    def walk(elem, ctm, role, style, depth, forced=False):
        tag = _local(elem.tag)
        if tag in NON_RENDERED:
            return
        if depth > 0 and _is_hidden(elem) and not forced:
            return
        if tag == "text":
            # Le texte applique lui-même sa transformation et son style (_text_objects).
            for obj, box in _text_objects(elem, ctm, style):
                texts.append((role_for({**style, **_style(elem)}, role), obj, box))
            return
        own = _style(elem)
        style = {**style, **{k: v for k, v in own.items() if k not in ("display", "visibility", "opacity")}}
        ctm = parse_transform(elem.attrib.get("transform")) * ctm
        if tag in ("g", "svg", "a", "switch"):
            role = role_of_label(_label(elem)) or role
            options = _variant_options(elem) if depth > 0 and tag == "g" else None
            if options:
                chosen = variants.get(_label(elem)) or next(
                    (key for key, _n, visible in options if visible), None)
                for child in elem:
                    if _label(child) == chosen:
                        walk(child, ctm, role_of_label(_label(child)) or role, style, depth + 1, forced=True)
                return
            for child in elem:
                walk(child, ctm, role, style, depth + 1)
            return
        geometry = _shape_path(elem, tag)
        if geometry is not None and not geometry.isEmpty():
            shapes.setdefault(role_for(style, role), []).append(ctm.map(geometry))

    walk(root, _document_transform(root), None, {}, 0)
    return _to_artwork(shapes, texts, offset_x_mm, offset_y_mm, bed_h_mm)


def _shape_path(elem, tag):
    """Géométrie d'une forme SVG dans son propre repère, ou None."""
    a = elem.attrib
    f = lambda name, default=0.0: (_numbers(a.get(name)) or [default])[0]  # noqa: E731
    path = QPainterPath()
    if tag == "path":
        d = a.get("d")
        return _svg_path_element_to_single(d) if d else None
    if tag == "rect":
        w, h = f("width"), f("height")
        if w <= 0 or h <= 0:
            return None
        rx, ry = a.get("rx"), a.get("ry")
        rx_v = f("rx") if rx is not None else (f("ry") if ry is not None else 0.0)
        ry_v = f("ry") if ry is not None else rx_v
        rx_v, ry_v = min(rx_v, w / 2), min(ry_v, h / 2)
        if rx_v > 0 or ry_v > 0:
            path.addRoundedRect(f("x"), f("y"), w, h, rx_v, ry_v)
        else:
            path.addRect(f("x"), f("y"), w, h)
        return path
    if tag == "circle":
        r = f("r")
        if r <= 0:
            return None
        path.addEllipse(QPointF(f("cx"), f("cy")), r, r)
        return path
    if tag == "ellipse":
        rx, ry = f("rx"), f("ry")
        if rx <= 0 or ry <= 0:
            return None
        path.addEllipse(QPointF(f("cx"), f("cy")), rx, ry)
        return path
    if tag in ("polygon", "polyline"):
        v = _numbers(a.get("points"))
        if len(v) < 4:
            return None
        path.addPolygon(QPolygonF([QPointF(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]))
        if tag == "polygon":
            path.closeSubpath()
        return path
    if tag == "line":
        path.moveTo(f("x1"), f("y1"))
        path.lineTo(f("x2"), f("y2"))
        return path
    return None


# -- textes

def _font_family(style):
    family = (style.get("font-family") or "Sans").split(",")[0].strip().strip("'\"")
    return family or "Sans"


def _is_bold(style):
    weight = (style.get("font-weight") or "normal").lower()
    return weight in ("bold", "bolder") or (weight.isdigit() and int(weight) >= 600)


def _text_runs(text_elem, style):
    """[(texte, x, y, style)] : une ligne par <tspan> positionné (x / y),
    sinon tout le texte en une ligne."""
    x0 = (_numbers(text_elem.attrib.get("x")) or [0.0])[0]
    y0 = (_numbers(text_elem.attrib.get("y")) or [0.0])[0]
    runs = []
    if text_elem.text and text_elem.text.strip():
        runs.append([text_elem.text.strip(), x0, y0, style])
    for tspan in text_elem:
        if _local(tspan.tag) != "tspan" or _is_hidden(tspan):
            continue
        content = "".join(tspan.itertext()).strip()
        if not content:
            continue
        span_style = {**style, **_style(tspan)}
        xs, ys = _numbers(tspan.attrib.get("x")), _numbers(tspan.attrib.get("y"))
        if (xs or ys) or not runs:
            runs.append([content, xs[0] if xs else x0, ys[0] if ys else y0, span_style])
        else:
            runs[-1][0] += content
    return runs


def _text_objects(text_elem, ctm, style):
    """Objets texte modifiables d'un <text> : [(TextObject, boîte cible)].

    La boîte cible est celle du texte tel que le SVG le dessine (taille,
    ancrage, transformation), en mm Y vers le bas ; l'objet texte est ensuite
    mis à la même hauteur et centré dessus (_to_artwork)."""
    style = {**style, **{k: v for k, v in _style(text_elem).items()
                         if k not in ("display", "visibility", "opacity")}}
    ctm = parse_transform(text_elem.attrib.get("transform")) * ctm
    result = []
    for content, x, y, run_style in _text_runs(text_elem, style):
        size = (_numbers(run_style.get("font-size")) or [16.0])[0]
        if size <= 0:
            continue
        family = _font_family(run_style)
        bold = _is_bold(run_style)
        italic = (run_style.get("font-style") or "").lower() in ("italic", "oblique")
        font = QFont(family)
        font.setPixelSize(max(1, round(size * 100)))     # précision : dessiné en grand, puis réduit
        font.setBold(bold)
        font.setItalic(italic)
        glyphs = QPainterPath()
        glyphs.addText(0, 0, font, content)
        bounds = glyphs.boundingRect()
        advance = bounds.right()
        anchor = (run_style.get("text-anchor") or "start").lower()
        shift = {"middle": -advance / 2, "end": -advance}.get(anchor, 0.0)
        local = QTransform()
        local.translate(x, y)
        local.scale(0.01, 0.01)
        local.translate(shift, 0)
        box = (local * ctm).map(glyphs).boundingRect()
        if box.isEmpty():
            continue
        obj = TextObject(text=content, font_family=family, size_mm=1.0, bold=bold, italic=italic)
        result.append((obj, box))
    return result


def _fit_text(obj, box, bed_h_mm):
    """Met l'objet texte à la hauteur de `box` et le centre dessus (repère
    éditeur, Y vers le haut). Un texte étiré en largeur dans le SVG
    (scale(1.04, 0.96)...) ne peut pas l'être dans l'éditeur : l'écart de
    largeur est rattrapé par l'espacement des lettres."""
    obj.x_mm = obj.y_mm = 0.0
    height = obj.world_path().boundingRect().height()
    if height > 0:
        obj.size_mm *= box.height() / height
    width = obj.world_path().boundingRect().width()
    gaps = len(obj.text) - 1
    if gaps > 0 and width > 0 and abs(box.width() - width) > 0.01 * width:
        obj.letter_spacing_mm = (box.width() - width) / gaps
    current = obj.world_path().boundingRect()
    target_cx = box.center().x()
    target_cy = bed_h_mm - box.center().y()
    obj.x_mm += target_cx - current.center().x()
    obj.y_mm += target_cy - current.center().y()


def _to_artwork(shapes, texts, offset_x_mm, offset_y_mm, bed_h_mm):
    """Objets de l'éditeur, ancrés par le coin inférieur gauche du dessin."""
    flip = QTransform(1, 0, 0, -1, 0, bed_h_mm)      # mm Y vers le bas -> repère éditeur
    items = []
    for role, paths in shapes.items():
        parts = []
        for path in paths:
            world = flip.map(path)
            bbox = world.boundingRect()
            if bbox.width() <= 0 and bbox.height() <= 0:
                continue
            to_local = QTransform(1, 0, 0, -1, -bbox.left(), bbox.top())
            parts.append(SvgPathObject(local_path_data=to_local.map(world), source_tag=f"svg:{role}",
                                       x_mm=bbox.left(), y_mm=bbox.top()))
        merged = _merge_path_objects(parts, source_tag=f"svg:{role}")
        if merged is not None:
            items.append((role, merged))
    for role, obj, box in texts:
        _fit_text(obj, box, bed_h_mm)
        items.append((role, obj))
    artwork = ImportedArtwork(items)
    if not items:
        return artwork
    bounds = None
    for _role, obj in items:
        rect = obj.world_path().boundingRect()
        bounds = rect if bounds is None else bounds.united(rect)
    dx, dy = offset_x_mm - bounds.left(), offset_y_mm - bounds.top()
    for _role, obj in items:
        obj.x_mm += dx
        obj.y_mm += dy
    artwork.width_mm, artwork.height_mm = bounds.width(), bounds.height()
    return artwork


# -- fiche détail de la bibliothèque

def document_size_mm(path):
    """(largeur, hauteur) du document en mm (attributs width / height, sinon
    viewBox en px), ou None."""
    root = _parse(path)
    width = _length_mm(root.attrib.get("width"))
    height = _length_mm(root.attrib.get("height"))
    if width and height:
        return width, height
    vb = _numbers(root.attrib.get("viewBox"))
    if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
        return vb[2] * UNIT_MM["px"], vb[3] * UNIT_MM["px"]
    return None


def svg_with_variants(path, variants):
    """Contenu SVG (octets) où seule l'option choisie de chaque groupe de
    variantes est visible : pour dessiner l'aperçu de la variante choisie."""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("inkscape", INKSCAPE_NS)
    ET.register_namespace("sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
    tree = ET.parse(path)
    root = tree.getroot()

    def set_visible(elem, visible):
        style = [p for p in (elem.attrib.get("style") or "").split(";")
                 if p.strip() and not p.strip().startswith("display")]
        style.append("display:inline" if visible else "display:none")
        elem.attrib["style"] = ";".join(style)
        elem.attrib.pop("display", None)

    def walk(elem, depth):
        if _local(elem.tag) in NON_RENDERED or (depth > 0 and _is_hidden(elem)):
            return
        if depth > 0 and _local(elem.tag) == "g":
            options = _variant_options(elem)
            if options:
                chosen = (variants or {}).get(_label(elem))
                if chosen in [key for key, _n, _v in options]:
                    for child in elem:
                        if _label(child):
                            set_visible(child, _label(child) == chosen)
                return
        for child in elem:
            walk(child, depth + 1)

    walk(root, 0)
    return ET.tostring(root, encoding="utf-8")
