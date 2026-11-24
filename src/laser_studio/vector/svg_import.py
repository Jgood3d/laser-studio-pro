"""Import SVG des modèles de la bibliothèque, selon leur convention (calques Cut / Engrave / Mark).
Le bouton « Importer » de l'éditeur utilise vector/svg_tree_import.py.

Convention (voir resources/library/README.md) :
- calque (ou groupe) « Cut » : découpe, dessinée en rouge ;
- calque (ou groupe) « Engrave » : gravure remplie ; le noir est gravé, le
  blanc (ou une couleur très claire) est creusé dans ce qui est gravé en
  dessous (gravure = union des formes foncées, moins les formes claires,
  dans l'ordre du dessin) ; un texte clair devient donc un tracé. Les
  traits (stroke) sont gravés avec leur épaisseur, comme Inkscape les
  dessine (pictogrammes dessinés au trait) ;
- calque (ou groupe) « Mark », facultatif : marquage (contour gravé), en bleu ;
- tout le reste (élément hors de ces calques, calque caché) est ignoré ;
- options : un groupe dont les sous-calques sont tous cachés sauf un (celui
  par défaut) ; le nom du groupe est le libellé du choix, le nom de chaque
  sous-calque celui d'une option. Des groupes du même nom forment un seul
  choix (un groupe « Forme » dans Cut et un autre dans Engrave). Une option
  peut aussi contenir ses propres calques Cut / Engrave / Mark.

Pris en compte aussi : les unités du document (width / height / viewBox),
les transformations cumulées, les textes (<text>, <tspan>, lignes Inkscape),
dont le contenu peut être remplacé à l'import (paramètre `texts`, voir
find_texts) et qui deviennent des objets texte modifiables de l'éditeur.

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

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QFont, QPainterPath, QPainterPathStroker, QPolygonF, QTransform

from laser_studio.models.vector_objects import SvgPathObject, TextObject
from laser_studio.vector.svg_extract import _merge_path_objects, _svg_path_element_to_single
from laser_studio.vector.svg_style import parse_color

ROLE_CUT = "cut"
ROLE_ENGRAVE = "engrave"
ROLE_MARK = "mark"

# Nom du calque ou du groupe (sans tenir compte des majuscules) -> rôle.
ROLE_NAMES = {"cut": ROLE_CUT, "engrave": ROLE_ENGRAVE, "mark": ROLE_MARK}

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
class TextField:
    """Texte du modèle modifiable à l'import : `key` (passée dans `texts`),
    `label` (nom affiché), et ce que contient le fichier : `text`, `family`
    (police), `size_mm` (taille de la police, en mm), `bold`."""
    key: str
    label: str
    text: str
    family: str = "Sans"
    size_mm: float = 5.0
    bold: bool = False


@dataclass
class TextChange:
    """Modification d'un texte à l'import (valeur de `texts`) ; None : garder
    ce que dit le fichier."""
    text: str = None
    family: str = None
    size_mm: float = None


def _text_change(value):
    """Valeur de `texts` : TextChange, ou simple chaîne (nouveau contenu)."""
    if value is None or isinstance(value, TextChange):
        return value
    if isinstance(value, dict):
        return TextChange(**value)
    return TextChange(text=str(value))


def _vertical_scale(transform):
    """Échelle verticale d'une transformation (taille d'une unité en hauteur)."""
    return math.hypot(transform.m21(), transform.m22()) or 1.0


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
    for name in ("display", "visibility", "fill", "stroke", "stroke-width", "stroke-linecap",
                 "stroke-linejoin", "font-family", "font-size", "font-weight", "font-style",
                 "text-anchor", "opacity"):
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
    """Rôle d'un calque ou d'un groupe d'après son nom exact (« Cut »,
    « Engrave », « Mark », majuscules indifférentes), ou None."""
    return ROLE_NAMES.get((label or "").strip().lower())


def _length_mm(value, default_unit="", px_mm=None):
    """Longueur SVG (« 30mm », « 12.5 », « 1in ») en mm, ou None. `px_mm` : taille d'un px (ou d'une
    longueur sans unité) en mm, 25,4 / 96 par défaut (CSS)."""
    if value is None:
        return None
    match = re.fullmatch(r"\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)\s*([a-z%]*)\s*", value)
    if not match or match.group(2) == "%":
        return None
    unit = match.group(2) or default_unit
    if unit in ("", "px"):
        return float(match.group(1)) * (px_mm or UNIT_MM["px"])
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


def viewbox_transform(viewbox, width, height, aspect="xMidYMid meet"):
    """Transformation du viewBox (x, y, largeur, hauteur) vers une zone `width` × `height`, selon
    preserveAspectRatio (SVG 1.1 § 7.8) : « none » étire, sinon échelle uniforme (« meet » : tout tient,
    « slice » : la zone est remplie) et alignement xMin / xMid / xMax, yMin / yMid / yMax."""
    vx, vy, vw, vh = viewbox
    sx, sy = width / vw, height / vh
    parts = (aspect or "xMidYMid meet").replace("defer", "").split()
    align = parts[0] if parts else "xMidYMid"
    t = QTransform()
    if align == "none":
        t.scale(sx, sy)
        t.translate(-vx, -vy)
        return t
    scale = max(sx, sy) if len(parts) > 1 and parts[1] == "slice" else min(sx, sy)
    dx = {"xMin": 0.0, "xMid": 0.5, "xMax": 1.0}.get(align[:4], 0.5) * (width - vw * scale)
    dy = {"YMin": 0.0, "YMid": 0.5, "YMax": 1.0}.get(align[4:], 0.5) * (height - vh * scale)
    t.translate(dx, dy)
    t.scale(scale, scale)
    t.translate(-vx, -vy)
    return t


def _document_transform(root, px_mm=None):
    """Unités du document -> mm (viewBox, width, height, preserveAspectRatio). `px_mm` : taille d'un px (ou
    d'une longueur sans unité) en mm, 25,4 / 96 par défaut (CSS)."""
    px_mm = px_mm or UNIT_MM["px"]
    vb = _numbers(root.attrib.get("viewBox"))
    width = _length_mm(root.attrib.get("width"), px_mm=px_mm)
    height = _length_mm(root.attrib.get("height"), px_mm=px_mm)
    if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
        # Sans width / height : 1 unité du viewBox = 1 px (taille intrinsèque) ; un seul des deux : l'autre
        # suit les proportions du viewBox.
        if not width and not height:
            width, height = vb[2] * px_mm, vb[3] * px_mm
        elif not width:
            width = height * vb[2] / vb[3]
        elif not height:
            height = width * vb[3] / vb[2]
        return viewbox_transform(vb, width, height, root.attrib.get("preserveAspectRatio"))
    t = QTransform()
    t.scale(px_mm, px_mm)
    return t


def _parse(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise SvgImportError(str(e)) from e


# -- variantes

def _variant_options(group):
    """[(clé, nom, visible)] si `group` est un groupe d'options : au moins
    deux sous-calques (ou groupes) nommés, un seul visible ; sinon None."""
    children = [c for c in group if _local(c.tag) == "g" and _label(c)]
    if len(children) < 2 or len(children) != len([c for c in group if _local(c.tag) not in NON_RENDERED]):
        return None
    visible = [c for c in children if not _is_hidden(c)]
    if len(visible) != 1:
        return None
    return [(_label(c), _label(c), not _is_hidden(c)) for c in children]


def _chosen_option(group, options, variants):
    """Option retenue d'un groupe de variantes : celle de `variants`, sinon
    l'option visible dans le fichier."""
    chosen = (variants or {}).get(_label(group))
    if chosen in [key for key, _n, _v in options]:
        return chosen
    return next((key for key, _n, visible in options if visible), None)


def _visible_elements(root, variants):
    """Éléments dessinés (ni cachés ni écartés par une option), dans l'ordre
    du document : [(élément, profondeur, rôle, ctm)] ; rôle : celui du calque
    Cut / Engrave / Mark qui le contient, ou None ; ctm : transformation du
    repère de son parent vers les mm du document. Les enfants d'un <text> ne
    sont pas parcourus."""
    result = []

    def walk(elem, depth, role, ctm, forced=False):
        tag = _local(elem.tag)
        if tag in NON_RENDERED or (depth > 0 and _is_hidden(elem) and not forced):
            return
        if tag == "g":
            role = role_of_label(_label(elem)) or role
        result.append((elem, depth, role, ctm))
        if tag == "text":
            return
        own = parse_transform(elem.attrib.get("transform")) * ctm
        options = _variant_options(elem) if depth > 0 and tag == "g" else None
        if options:
            chosen = _chosen_option(elem, options, variants)
            for child in elem:
                if _label(child) == chosen:
                    walk(child, depth + 1, role, own, forced=True)
            return
        for child in elem:
            walk(child, depth + 1, role, own)

    walk(root, 0, None, _document_transform(root))
    return result


def find_variant_groups(path):
    """Groupes de variantes du fichier (voir VariantGroup), dans l'ordre du
    document. Le calque racine des calques n'en est jamais un (un calque de
    construction caché n'est pas une variante).

    Plusieurs groupes du même nom forment un seul choix (options réunies,
    option par défaut du premier) : un groupe « Forme » dans Cut et un autre
    dans Engrave changent ensemble la découpe et la gravure."""
    root = _parse(path)
    groups = []
    by_key = {}

    def walk(elem, depth):
        if _local(elem.tag) in NON_RENDERED or (depth > 0 and _is_hidden(elem)):
            return
        if depth > 0 and _local(elem.tag) == "g":
            options = _variant_options(elem)
            if options:
                default = next((key for key, _n, visible in options if visible), options[0][0])
                found = by_key.get(_label(elem))
                if found is None:
                    found = VariantGroup(_label(elem), _label(elem), [], default)
                    by_key[found.key] = found
                    groups.append(found)
                for key, name, _v in options:
                    if key not in [k for k, _n in found.options]:
                        found.options.append((key, name))
                return
        for child in elem:
            walk(child, depth + 1)

    walk(root, 0)
    return groups


def find_texts(path, variants=None):
    """Textes importés (visibles, dans un calque Cut / Engrave / Mark, avec
    les options choisies), à proposer pour modification (contenu, police,
    taille) : [TextField]. Un texte de plusieurs lignes donne un champ par
    ligne (clé « nom#1 », « nom#2 »...)."""
    root = _parse(path)
    fields = []
    for elem, _depth, role, ctm in _visible_elements(root, variants):
        if _local(elem.tag) != "text" or role is None:
            continue
        runs = _text_runs(elem, {})
        name = _label(elem)
        if not name:
            continue                 # sans nom ni id : pas de clé pour le remplacer
        scale = _vertical_scale(parse_transform(elem.attrib.get("transform")) * ctm)
        for index, (content, _x, _y, run_style) in enumerate(runs):
            key = name if len(runs) == 1 else f"{name}#{index + 1}"
            label = name if len(runs) == 1 else f"{name} ({index + 1})"
            fields.append(TextField(key, label, content, _font_family(run_style),
                                    round(_font_size(run_style) * scale, 2), _is_bold(run_style)))
    return fields


# -- couleurs

# Au-dessus de cette luminance (0 à 1), une couleur est « claire » : non gravée.
LIGHT_LUMINANCE = 0.8


def _rgb(color):
    """(r, g, b) d'une couleur CSS / SVG (voir svg_style.parse_color), ou None (« none », transparent…)."""
    parsed = parse_color(color)
    if parsed is None or parsed[3] <= 0:
        return None
    return parsed[:3]


def is_light(color):
    """Vrai pour le blanc et les couleurs très claires (non gravées)."""
    rgb = _rgb(color)
    if rgb is None:
        return False
    r, g, b = (v / 255 for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b >= LIGHT_LUMINANCE


# -- import

# Les opérations sur les tracés (union, différence) sont faites à cette échelle :
# Qt aplatit les courbes avec une tolérance d'environ 1 unité, trop grossière en mm.
BOOLEAN_SCALE = 100.0


class _EngraveRegion:
    """Zone gravée : union des formes foncées moins les formes claires, dans
    l'ordre du dessin (tracés en mm × BOOLEAN_SCALE)."""

    def __init__(self):
        self.path = None
        self._up = QTransform.fromScale(BOOLEAN_SCALE, BOOLEAN_SCALE)

    def add(self, path, light):
        scaled = self._up.map(path)
        scaled.setFillRule(path.fillRule())
        if self.path is None:
            if not light:
                self.path = scaled
            return
        self.path = self.path.subtracted(scaled) if light else self.path.united(scaled)

    def result(self):
        if self.path is None or self.path.isEmpty():
            return None
        down = QTransform.fromScale(1 / BOOLEAN_SCALE, 1 / BOOLEAN_SCALE)
        return down.map(self.path.simplified())


def import_svg(path, variants=None, offset_x_mm=10.0, offset_y_mm=10.0, bed_h_mm=0.0,
               texts=None):
    """Lit le SVG `path` et renvoie un ImportedArtwork : les tracés de chaque
    rôle groupés en un objet, chaque texte foncé en objet texte. `variants` :
    {clé du groupe: clé de l'option} (voir find_variant_groups ; option
    visible dans le fichier si absente). `texts` : {clé du texte: TextChange
    (contenu, police, taille en mm) ou nouveau contenu} (voir find_texts). Seul le contenu des calques Cut, Engrave et
    Mark est importé."""
    root = _parse(path)
    variants = variants or {}
    texts = texts or {}
    outlines = {}               # rôle (découpe, marquage) -> [QPainterPath en mm, Y vers le bas]
    engrave = _EngraveRegion()  # gravure remplie : formes foncées moins formes claires
    text_items = []             # (rôle, TextObject, boîte cible en mm Y vers le bas)

    def add_shape(path_mm, role, style, stroke_mm=None):
        """Forme en mm. Sur la gravure : son remplissage, puis son trait
        (`stroke_mm` : le trait déjà épaissi, voir _stroke_outline), chacun
        gravé (foncé) ou creusé (clair) selon sa couleur."""
        if role == ROLE_ENGRAVE:
            fill = style.get("fill", "black")
            if fill not in ("none", "transparent"):
                engrave.add(path_mm, is_light(fill))
            if stroke_mm is not None:
                engrave.add(stroke_mm, is_light(style.get("stroke")))
            elif fill in ("none", "transparent"):
                outlines.setdefault(role, []).append(path_mm)    # contour seul, sans trait ni remplissage
        else:
            outlines.setdefault(role, []).append(path_mm)

    def walk(elem, ctm, role, style, depth, forced=False):
        tag = _local(elem.tag)
        if tag in NON_RENDERED:
            return
        if depth > 0 and _is_hidden(elem) and not forced:
            return
        if tag == "text":
            # Le texte applique lui-même sa transformation et son style.
            text_style = {**style, **_inherited(_style(elem))}
            if role is None:
                return                    # hors des calques Cut / Engrave / Mark : ignoré
            text_role = role
            light = is_light(text_style.get("fill", "black"))
            for run in _text_glyphs(elem, ctm, style, texts):
                if text_role == ROLE_ENGRAVE and not light:
                    text_items.append((text_role, _text_object(run), run.box))
                else:
                    add_shape(run.path, text_role, text_style)    # texte clair : creusé
            return
        style = {**style, **_inherited(_style(elem))}
        ctm = parse_transform(elem.attrib.get("transform")) * ctm
        if tag in ("g", "svg", "a", "switch"):
            role = role_of_label(_label(elem)) or role
            options = _variant_options(elem) if depth > 0 and tag == "g" else None
            if options:
                chosen = _chosen_option(elem, options, variants)
                for child in elem:
                    if _label(child) == chosen:
                        walk(child, ctm, role, style, depth + 1, forced=True)
                return
            for child in elem:
                walk(child, ctm, role, style, depth + 1)
            return
        if role is None:
            return                        # hors des calques Cut / Engrave / Mark : ignoré
        geometry = _shape_path(elem, tag)
        if geometry is not None and not geometry.isEmpty():
            mapped = ctm.map(geometry)
            mapped.setFillRule(geometry.fillRule())
            stroke = _stroke_outline(geometry, style) if role == ROLE_ENGRAVE else None
            add_shape(mapped, role, style, ctm.map(stroke) if stroke is not None else None)

    walk(root, _document_transform(root), None, {}, 0)
    region = engrave.result()
    if region is not None:
        outlines.setdefault(ROLE_ENGRAVE, []).insert(0, region)
    return _to_artwork(outlines, text_items, offset_x_mm, offset_y_mm, bed_h_mm)


def _stroke_outline(geometry, style, width=None, dashes=None):
    """Trait d'une forme épaissi en surface (repère de la forme), comme le
    dessine un afficheur SVG : épaisseur `stroke-width` (ou `width`, déjà en
    unités utilisateur), bouts et angles selon `stroke-linecap` /
    `stroke-linejoin`, tirets `dashes` ((longueurs, décalage) en unités
    utilisateur, voir svg_tree_import). None sans trait visible."""
    stroke = (style.get("stroke") or "none").strip().lower()
    if width is None:
        width = (_numbers(style.get("stroke-width")) or [1.0])[0]
    if stroke in ("none", "transparent") or width <= 0:
        return None
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    stroker.setCapStyle({"round": Qt.PenCapStyle.RoundCap, "square": Qt.PenCapStyle.SquareCap}.get(
        (style.get("stroke-linecap") or "butt").strip(), Qt.PenCapStyle.FlatCap))
    stroker.setJoinStyle({"round": Qt.PenJoinStyle.RoundJoin, "bevel": Qt.PenJoinStyle.BevelJoin}.get(
        (style.get("stroke-linejoin") or "miter").strip(), Qt.PenJoinStyle.MiterJoin))
    miter = _numbers(style.get("stroke-miterlimit"))
    if miter:
        stroker.setMiterLimit(max(1.0, miter[0]))
    if dashes:
        # Qt compte les tirets en épaisseurs de trait.
        stroker.setDashPattern([max(v / width, 1e-6) for v in dashes[0]])
        stroker.setDashOffset(dashes[1] / width)
    # simplified() : surface sans recouvrements (le trait se recoupe aux angles), lisible en
    # pair-impair comme le reste de la gravure.
    outline = stroker.createStroke(geometry).simplified()
    outline.setFillRule(Qt.FillRule.OddEvenFill)
    return outline


def _inherited(style):
    """Propriétés transmises aux enfants (pas l'affichage ni l'opacité)."""
    return {k: v for k, v in style.items() if k not in ("display", "visibility", "opacity")}


def _shape_path(elem, tag, length=None):
    """Géométrie d'une forme SVG dans son propre repère, ou None. `length(nom, défaut)` : valeur d'un
    attribut de longueur en unités utilisateur (unités, pourcentages : voir svg_tree_import) ; par défaut,
    le premier nombre de l'attribut."""
    a = elem.attrib
    f = length or (lambda name, default=0.0: (_numbers(a.get(name)) or [default])[0])
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


def _font_size(style):
    return (_numbers(style.get("font-size")) or [16.0])[0]


def _line_height(style):
    """Hauteur de ligne en unités du document (Inkscape : « 1.25 », « 125% »
    ou « 12.8px »)."""
    size = _font_size(style)
    value = (style.get("line-height") or "").strip()
    number = (_numbers(value) or [None])[0]
    if number is None:
        return 1.25 * size
    if value.endswith("%"):
        return number / 100 * size
    if re.search(r"[a-z]", value):
        return number
    return number * size


def _text_runs(text_elem, style):
    """[[texte, x, y, style]] : une ligne par <tspan> positionné, sinon tout
    le texte en une ligne. Comme Inkscape, une ligne sodipodi:role="line" est
    placée sous la précédente (x et y du texte, plus une hauteur de ligne par
    ligne), quelles que soient ses propres coordonnées."""
    style = {**style, **_inherited(_style(text_elem))}
    x0 = (_numbers(text_elem.attrib.get("x")) or [0.0])[0]
    y0 = (_numbers(text_elem.attrib.get("y")) or [0.0])[0]
    runs = []
    if text_elem.text and text_elem.text.strip():
        runs.append([text_elem.text.strip(), x0, y0, style])
    line = 0
    for tspan in text_elem:
        if _local(tspan.tag) != "tspan" or _is_hidden(tspan):
            continue
        span_style = {**style, **_inherited(_style(tspan))}
        content = "".join(tspan.itertext()).strip()
        if _attr(tspan, "role") == "line":
            if content:
                runs.append([content, x0, y0 + line * _line_height(span_style), span_style])
            line += 1
            continue
        if not content:
            continue
        xs, ys = _numbers(tspan.attrib.get("x")), _numbers(tspan.attrib.get("y"))
        if (xs or ys) or not runs:
            runs.append([content, xs[0] if xs else x0, ys[0] if ys else y0, span_style])
        else:
            runs[-1][0] += content
    return runs


@dataclass
class _GlyphRun:
    """Une ligne de texte telle que le SVG la dessine : contenu, police, et
    son tracé (`path`) et sa boîte (`box`) en mm, Y vers le bas."""
    text: str
    family: str
    bold: bool
    italic: bool
    path: QPainterPath
    box: object


def _text_glyphs(text_elem, ctm, style, changes=None):
    """Lignes d'un <text> (voir _GlyphRun), modifiées par `changes`
    ({clé: TextChange ou nouveau contenu}, voir find_texts)."""
    changes = changes or {}
    ctm = parse_transform(text_elem.attrib.get("transform")) * ctm
    runs = _text_runs(text_elem, style)
    name = _label(text_elem)
    result = []
    for index, (content, x, y, run_style) in enumerate(runs):
        key = name if len(runs) == 1 else f"{name}#{index + 1}"
        change = _text_change(changes.get(key)) or TextChange()
        if change.text is not None:
            content = change.text
        size = _font_size(run_style)
        if change.size_mm:
            size = change.size_mm / _vertical_scale(ctm)      # mm -> unités du texte
        if size <= 0 or not content.strip():
            continue
        family = change.family or _font_family(run_style)
        bold = _is_bold(run_style)
        italic = (run_style.get("font-style") or "").lower() in ("italic", "oblique")
        font = QFont(family)
        font.setPixelSize(max(1, round(size * 100)))     # précision : dessiné en grand, puis réduit
        font.setBold(bold)
        font.setItalic(italic)
        glyphs = QPainterPath()
        glyphs.addText(0, 0, font, content)
        advance = glyphs.boundingRect().right()
        anchor = (run_style.get("text-anchor") or "start").lower()
        shift = {"middle": -advance / 2, "end": -advance}.get(anchor, 0.0)
        local = QTransform()
        local.translate(x, y)
        local.scale(0.01, 0.01)
        local.translate(shift, 0)
        mapped = (local * ctm).map(glyphs)
        box = mapped.boundingRect()
        if not box.isEmpty():
            result.append(_GlyphRun(content, family, bold, italic, mapped, box))
    return result


def _text_object(run):
    """Objet texte modifiable de l'éditeur (placé ensuite par _fit_text)."""
    return TextObject(text=run.text, font_family=run.family, size_mm=1.0, bold=run.bold, italic=run.italic)


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


def _set_style(elem, props):
    """Remplace des propriétés de l'attribut style de `elem`."""
    if not props:
        return
    kept = [p for p in (elem.attrib.get("style") or "").split(";")
            if p.strip() and p.split(":", 1)[0].strip() not in props]
    elem.attrib["style"] = ";".join(kept + [f"{k}:{v}" for k, v in props.items()])
    for name in props:
        elem.attrib.pop(name, None)


def _set_visible(elem, visible):
    style = [p for p in (elem.attrib.get("style") or "").split(";")
             if p.strip() and not p.strip().startswith("display")]
    style.append("display:inline" if visible else "display:none")
    elem.attrib["style"] = ";".join(style)
    elem.attrib.pop("display", None)


def svg_preview(path, variants=None, texts=None):
    """Contenu SVG (octets) tel qu'il sera importé, pour l'aperçu de la
    fiche : seule l'option choisie de chaque groupe de variantes est visible,
    les textes sont remplacés (`texts`), et les lignes de texte Inkscape
    (sodipodi:role="line") reçoivent leur position réelle (un afficheur SVG
    qui ne connaît pas Inkscape les placerait en 0, 0). `texts` : comme pour
    import_svg (contenu, police, taille)."""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("inkscape", INKSCAPE_NS)
    ET.register_namespace("sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as e:
        raise SvgImportError(str(e)) from e
    root = tree.getroot()
    texts = texts or {}

    for elem, depth, _role, ctm in _visible_elements(root, variants):
        tag = _local(elem.tag)
        if depth > 0 and tag == "g":
            options = _variant_options(elem)
            if options:
                chosen = _chosen_option(elem, options, variants)
                for child in elem:
                    if _label(child):
                        _set_visible(child, _label(child) == chosen)
        if tag != "text":
            continue
        x0 = elem.attrib.get("x", "0")
        y0 = (_numbers(elem.attrib.get("y")) or [0.0])[0]
        style = {**_inherited(_style(elem))}
        spans = [t for t in elem if _local(t.tag) == "tspan" and not _is_hidden(t)]
        line = 0
        for tspan in spans:
            if _attr(tspan, "role") == "line":
                span_style = {**style, **_inherited(_style(tspan))}
                tspan.attrib["x"] = x0
                tspan.attrib["y"] = f"{y0 + line * _line_height(span_style):.4f}"
                line += 1
        name = _label(elem)
        lines = [t for t in spans if "".join(t.itertext()).strip()] or ([elem] if (elem.text or "").strip() else [])
        scale = _vertical_scale(parse_transform(elem.attrib.get("transform")) * ctm)
        for index, target in enumerate(lines):
            key = name if len(lines) == 1 else f"{name}#{index + 1}"
            change = _text_change(texts.get(key))
            if change is None:
                continue
            if change.text is not None:
                for child in list(target):
                    target.remove(child)
                target.text = change.text
            props = {}
            if change.family:
                props["font-family"] = f"'{change.family}'"
                props["-inkscape-font-specification"] = f"'{change.family}'"
            if change.size_mm:
                props["font-size"] = f"{change.size_mm / scale:.4f}px"
            for node in {target, elem}:
                _set_style(node, props)
    return ET.tostring(root, encoding="utf-8")
