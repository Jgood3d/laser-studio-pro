"""Texte posé sur le contour d'un autre objet, et textes de médaille : calcul sur les objets du document,
sans scène ni widget. Le canevas (ui/vector_editor/canvas.py) retrouve les éléments à l'écran et appelle
ces fonctions.

Le contour du guide est COPIÉ dans le texte (follow_points, relatifs au coin bas-gauche du tracé) : le guide
n'est jamais modifié, et le texte garde l'identifiant du guide (follow_guide_id) pour être resynchronisé
quand le guide bouge."""
from PyQt6.QtGui import QTransform

from laser_studio.models.vector_objects import ShapeObject, TextObject
from laser_studio.vector.text_on_path import (
    default_center_fraction, is_closed, orient_path, path_length, relative_points, side_center_fraction,
)

# Finesse de l'aplatissement des courbes du contour : 1/20 mm.
FLATTEN = 20.0
# Longueur minimale d'un contour pour y poser un texte (mm).
MIN_LENGTH_MM = 1.0
CLOSED_SHAPES = ("Rectangle", "Ellipse", "Polygone Régulier")


def guide_polyline(obj):
    """Contour le plus long de `obj`, en points (x, y) mm monde (Y vers le haut), courbes aplaties.
    Refermé si l'objet est une forme fermée. None si l'objet n'a pas de contour exploitable."""
    k = FLATTEN
    best, best_len = None, 0.0
    for poly in obj.world_path().toSubpathPolygons(QTransform.fromScale(k, k)):
        pts = [(poly.at(i).x() / k, poly.at(i).y() / k) for i in range(poly.count())]
        length = path_length(pts)
        if len(pts) >= 2 and length > best_len:
            best, best_len = pts, length
    if best is None:
        return None
    if isinstance(obj, ShapeObject) and obj.shape_type in CLOSED_SHAPES and not is_closed(best):
        best.append(best[0])
    return best


def follow_path(obj):
    """Contour de `obj` orienté pour y poser un texte, ou None s'il n'y en a pas ou s'il est trop court."""
    pts = guide_polyline(obj)
    if pts is None:
        return None
    pts = orient_path(pts)
    return pts if path_length(pts) >= MIN_LENGTH_MM else None


def closed_follow_path(obj):
    """Contour fermé de `obj` (textes de médaille), ou None. Les textes ne sont pas acceptés comme guide."""
    if isinstance(obj, TextObject):
        return None
    pts = guide_polyline(obj)
    if pts is None or not is_closed(pts) or path_length(pts) < MIN_LENGTH_MM:
        return None
    return orient_path(pts)


def apply_follow(text, guide_obj, pts, keep_settings=False):
    """Pose `text` sur le contour `pts` (de `guide_obj`) : copie du tracé, origine, position par défaut.
    `keep_settings` : texte déjà posé sur un tracé qu'on resynchronise, la position, le côté et la
    distance choisis sont conservés."""
    origin = (min(x for x, _y in pts), min(y for _x, y in pts))
    # Le texte est calculé directement dans le repère du tracé : ni rotation ni miroir, origine = coin
    # bas-gauche du tracé.
    text.rotation_deg = 0.0
    text.mirror_h = False
    text.mirror_v = False
    text.vertical = False
    text.arc_radius_mm = 0.0
    text.x_mm, text.y_mm = origin
    text.follow_points = relative_points(pts, origin)
    text.follow_closed = is_closed(pts)
    text.follow_guide_id = guide_obj.id
    if not keep_settings:
        text.follow_center = default_center_fraction(pts)
        text.follow_reverse = False
        text.follow_gap_mm = 0.0


def follows_a_path(obj):
    """Vrai si `obj` est un texte posé sur un contour."""
    return isinstance(obj, TextObject) and bool(getattr(obj, "follow_points", None))


def medal_texts(guide_obj, pts, top_text, bottom_text, font_family, size_mm, margin_mm, layer_id,
                bold=False, italic=False):
    """Textes de médaille posés à l'intérieur du contour fermé `pts` de `guide_obj` : `top_text` en haut,
    `bottom_text` en bas, les deux lisibles à l'endroit, à `margin_mm` du trait. Un texte vide est ignoré.
    Renvoie les objets créés (pas encore ajoutés au document)."""
    created = []
    for text, bottom in ((top_text, False), (bottom_text, True)):
        if not text.strip():
            continue
        obj = TextObject(text=text, font_family=font_family, size_mm=size_mm, bold=bold, italic=italic,
                         layer_id=layer_id)
        apply_follow(obj, guide_obj, pts)
        obj.follow_center = side_center_fraction(pts, "bottom" if bottom else "top")
        if bottom:
            # Lu de gauche à droite en bas : sens inversé, le haut des lettres vise le centre.
            obj.follow_reverse = True
            obj.text_anchor = "above"
            obj.follow_gap_mm = margin_mm
        else:
            # En haut, à l'endroit : lettres accrochées sous le trait, vers le centre.
            obj.follow_reverse = False
            obj.text_anchor = "below"
            obj.follow_gap_mm = -margin_mm
        created.append(obj)
    return created


# -- règles de la sélection (menu du clic droit et contrôleur de l'éditeur)

def text_follow_pair(objects):
    """(texte, guide) si `objects` sont exactement un texte et un autre objet, sinon None."""
    texts = [o for o in objects if isinstance(o, TextObject)]
    guides = [o for o in objects if not isinstance(o, TextObject)]
    if len(objects) == 2 and len(texts) == 1 and len(guides) == 1:
        return texts[0], guides[0]
    return None


def linked_guide(text, objects):
    """Objet de `objects` dont le texte `text` a copié le contour, s'il existe encore (sinon None)."""
    guide_id = getattr(text, "follow_guide_id", None)
    if not guide_id or not getattr(text, "follow_points", None):
        return None
    return next((o for o in objects if o.id == guide_id and not isinstance(o, TextObject)), None)


def medal_guide(objects):
    """L'objet si `objects` est un seul objet (hors texte) à contour fermé, sinon None."""
    if len(objects) == 1 and closed_follow_path(objects[0]) is not None:
        return objects[0]
    return None

