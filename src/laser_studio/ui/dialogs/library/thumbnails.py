"""Images des modèles de la bibliothèque.

- render_artwork : aperçu de la pièce telle qu'elle sortira de la machine,
  dessiné à partir de ce qui sera importé (vector.svg_tree_import) : la matière
  (bois clair) à l'intérieur des découpes, les trous transparents, la
  gravure en brun foncé (brûlure), les textes dans leur police ;
- render_svg : le fichier SVG lui-même (onglet « Dessin à graver »).
"""
from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QTransform
from PyQt6.QtSvg import QSvgRenderer

from laser_studio.vector.svg_import import ROLE_CUT, ROLE_ENGRAVE, ROLE_MARK, SvgImportError
from laser_studio.vector.svg_tree_import import import_library_svg

# Taille maxi (px) des vignettes calculées : au-delà, inutile pour la grille.
THUMBNAIL_MAX = 480

# Couleurs de l'aperçu : contreplaqué clair, gravure brûlée, chant de la découpe.
MATERIAL_COLOR = QColor("#dcb88a")
BURN_COLOR = QColor("#4a2c18")
EDGE_COLOR = QColor("#8a5a32")
# Marquage (contour gravé) : largeur du trait, en mm.
MARK_WIDTH_MM = 0.3


def render_svg(svg_data, max_px):
    """Image du SVG (chemin ou octets), dans un carré de `max_px` pixels au
    plus, proportions gardées, sur fond blanc. Image nulle si illisible."""
    renderer = QSvgRenderer(QByteArray(svg_data)) if isinstance(svg_data, (bytes, bytearray)) \
        else QSvgRenderer(svg_data)
    if not renderer.isValid():
        return QImage()
    size = renderer.defaultSize()
    w, h = max(size.width(), 1), max(size.height(), 1)
    scale = max_px / max(w, h)
    image = QImage(max(1, round(w * scale)), max(1, round(h * scale)), QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, image.width(), image.height()))
    painter.end()
    return image


def _leaves(objects):
    for obj in objects:
        children = getattr(obj, "children", None)
        if children:
            yield from _leaves(children)
        else:
            yield obj


def render_artwork(objects, max_px, margin_px=4):
    """Aperçu de la pièce sur fond transparent, dans un carré de `max_px` pixels au plus. `objects` : import
    de import_library_svg dont le calque de chaque objet est son rôle (le reste n'est pas dessiné). Sans
    découpe, la matière est le rectangle qui englobe le dessin. Image nulle si le dessin est vide."""
    paths = {ROLE_CUT: [], ROLE_ENGRAVE: [], ROLE_MARK: []}
    bounds = None
    for obj in _leaves(objects):
        if obj.layer_id not in paths:
            continue
        path = obj.world_path()
        paths[obj.layer_id].append(path)
        rect = path.boundingRect()
        bounds = rect if bounds is None else bounds.united(rect)
    if bounds is None or bounds.width() <= 0 or bounds.height() <= 0:
        return QImage()
    scale = (max_px - 2 * margin_px) / max(bounds.width(), bounds.height())
    width = round(bounds.width() * scale) + 2 * margin_px
    height = round(bounds.height() * scale) + 2 * margin_px
    # Repère éditeur (mm, Y vers le haut) -> pixels (Y vers le bas).
    view = QTransform(scale, 0, 0, -scale, margin_px - bounds.left() * scale,
                      margin_px + bounds.bottom() * scale)
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    material = QPainterPath()
    material.setFillRule(Qt.FillRule.OddEvenFill)       # contour plein, trous transparents
    for path in paths[ROLE_CUT]:
        material.addPath(path)
    if material.isEmpty():
        material.addRect(bounds)
    painter.setPen(QPen(EDGE_COLOR, 1.0))
    painter.setBrush(MATERIAL_COLOR)
    painter.drawPath(view.map(material))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(BURN_COLOR)
    for path in paths[ROLE_ENGRAVE]:
        mapped = view.map(path)
        mapped.setFillRule(Qt.FillRule.OddEvenFill)
        painter.drawPath(mapped)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(BURN_COLOR, max(1.0, MARK_WIDTH_MM * scale)))
    for path in paths[ROLE_MARK]:
        painter.drawPath(view.map(path))
    painter.end()
    return image


def item_image(item, max_px=THUMBNAIL_MAX, variants=None, texts=None):
    """Aperçu d'un modèle (LibraryItem), avec ses options et textes (ceux du
    fichier par défaut). Le SVG dessiné tel quel si l'import échoue."""
    try:
        image = render_artwork(import_library_svg(item.svg_path, lambda role: role, 0.0, variants, texts), max_px)
    except SvgImportError:
        image = QImage()
    return image if not image.isNull() else render_svg(item.svg_path, max_px)


def photo_image(item, max_px=2000):
    """Photo fournie avec le modèle (voir LibraryItem.preview_path), ou image nulle."""
    if not item.preview_path:
        return QImage()
    image = QImage(item.preview_path)
    if not image.isNull() and max(image.width(), image.height()) > max_px:
        image = image.scaled(max_px, max_px, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return image
