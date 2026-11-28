"""Assemblage d'une boule de Noël avec les opérations booléennes de Qt.

`ornament_generator` décrit les formes ; ici on les soude pour obtenir les contours que le laser suit, chacun
UNE seule fois :

    matière = (disque ∪ accroche) − disque intérieur          l'anneau
    matière = matière ∪ ((prénom ∪ flocons ∪ suspentes ∪ barre) ∩ disque)
    matière = matière − trou de la ficelle

Les lettres qui se chevauchent (écriture cursive) sont d'abord fusionnées ; les contreformes (le trou d'un a,
d'un e, d'un o) restent des contours à part. Repère : Y vers le haut, en mm, coin bas-gauche de la boule à (0, 0).
"""
from collections import namedtuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainterPath, QTransform

# Taille de référence du texte (pixels) : grande, pour que les courbes des lettres soient précises.
TEXT_REF_PX = 200
# Les courbes sont aplaties à 0,25 unité près ; on travaille en 1/FLATTEN_SCALE mm pour descendre sous 0,02 mm.
FLATTEN_SCALE = 20.0


def polygon_path(points):
    """Chemin fermé du polygone, toujours dans le sens trigonométrique : avec le remplissage « winding », deux
    formes qui se chevauchent dans des sens opposés s'annuleraient au lieu de fusionner."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, list(points[1:]) + [points[0]]))
    if area < 0:
        points = list(reversed(points))
    path = QPainterPath()
    path.moveTo(*points[0])
    for x, y in points[1:]:
        path.lineTo(x, y)
    path.closeSubpath()
    path.setFillRule(Qt.FillRule.WindingFill)
    return path


def union_path(polygons):
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for points in polygons:
        path.addPath(polygon_path(points))
    return path.simplified()


def text_path(text, family, bold=False, italic=False):
    """Contour du prénom, Y vers le haut, ligne de base à y = 0, lettres fusionnées. Chemin vide si pas de texte."""
    path = QPainterPath()
    if not text.strip():
        return path
    font = QFont(family)
    font.setPixelSize(TEXT_REF_PX)
    font.setBold(bold)
    font.setItalic(italic)
    path.addText(0.0, 0.0, font, text)
    path.setFillRule(Qt.FillRule.WindingFill)
    return QTransform(1, 0, 0, -1, 0, 0).map(path.simplified())


def text_bounds(path):
    """(x0, y0, x1, y1) du contour du prénom, ou None s'il est vide."""
    if path.isEmpty():
        return None
    r = path.boundingRect()
    return (r.left(), r.top(), r.right(), r.bottom())


def _contours(region, dx, dy):
    """Contours fermés de `region`, en mm, décalés de (dx, dy). Les points en double sont retirés."""
    out = []
    for poly in region.toSubpathPolygons(QTransform.fromScale(FLATTEN_SCALE, FLATTEN_SCALE)):
        pts = []
        for p in poly:
            q = (p.x() / FLATTEN_SCALE + dx, p.y() / FLATTEN_SCALE + dy)
            if not pts or q != pts[-1]:
                pts.append(q)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        if len(pts) >= 3:
            out.append(pts)
    return out


def assemble(geometry, text=None):
    """Contours de découpe de la boule : liste de polygones fermés (en mm, coin bas-gauche à (0, 0)).

    `text` : le chemin renvoyé par `text_path` (ou None). Le premier polygone de la liste est le contour
    extérieur, les suivants sont les contours intérieurs (trous, contreformes, flocons détachés)."""
    disc = union_path(geometry.outer[:1])
    body = union_path(geometry.outer)
    inner = union_path(geometry.voids)

    solids = union_path(geometry.solids) if geometry.solids else QPainterPath()
    if geometry.cuts and not solids.isEmpty():
        solids = solids.subtracted(union_path(geometry.cuts))
    if geometry.late:
        solids = solids.united(union_path(geometry.late))
    # Remplissages à motif : les barres sont rognées à leur zone (au-dessus ou au-dessous du prénom), puis soudées.
    for bars, clip in geometry.fills:
        piece = union_path(bars).intersected(union_path([clip]))
        if not piece.isEmpty():
            solids = solids.united(piece)
    # Prénom découpé : les lettres sont soudées à l'anneau. Prénom gravé : elles restent hors de la découpe.
    if text is not None and not text.isEmpty() and geometry.text is not None and not geometry.engrave_text:
        t = geometry.text
        placed = QTransform(t.scale, 0, 0, t.scale, t.tx, t.ty).map(text)
        placed.setFillRule(Qt.FillRule.WindingFill)
        solids = solids.united(placed)
    solids = solids.intersected(disc) if not solids.isEmpty() else solids

    region = body.subtracted(inner)
    if not solids.isEmpty():
        region = region.united(solids)
    if geometry.holes:
        region = region.subtracted(union_path(geometry.holes))
    region = region.simplified()

    min_x, min_y, _max_x, _max_y = geometry.bounds
    contours = _contours(region, -min_x, -min_y)
    # Le plus grand contour (par aire de sa boîte) est l'extérieur : on le met en tête.
    contours.sort(key=lambda c: -((max(p[0] for p in c) - min(p[0] for p in c))
                                  * (max(p[1] for p in c) - min(p[1] for p in c))))
    return contours


def assemble_engraving(geometry, text=None):
    """Contours GRAVÉS (prénom gravé sur la bande et filet) : (contours du prénom, contours du filet), dans le même
    repère que `assemble`. Le prénom garde ses contreformes (le trou d'un a, d'un e, d'un o) comme contours à part.
    Deux listes vides si le prénom est découpé."""
    if not geometry.engrave_text:
        return [], []
    min_x, min_y, _max_x, _max_y = geometry.bounds
    name = []
    if text is not None and not text.isEmpty() and geometry.text is not None:
        t = geometry.text
        placed = QTransform(t.scale, 0, 0, t.scale, t.tx, t.ty).map(text)
        placed.setFillRule(Qt.FillRule.WindingFill)
        name = _contours(placed.simplified(), -min_x, -min_y)
    frame = [[(x - min_x, y - min_y) for x, y in poly] for poly in geometry.frame]
    return name, frame


OrnamentParts = namedtuple("OrnamentParts", "geometry cut name frame")


def build_ornament_parts(params, family="Sans Serif", bold=False, italic=False):
    """Comme `build_ornament_contours`, avec en plus le prénom gravé et le filet : `OrnamentParts`
    (géométrie, contours de découpe, contours du prénom gravé, contours du filet gravé)."""
    from laser_studio.vector.ornament_generator import build_ornament

    text = text_path(params.name, family, bold, italic)
    geometry = build_ornament(params, text_bounds(text))
    name, frame = assemble_engraving(geometry, text)
    return OrnamentParts(geometry, assemble(geometry, text), name, frame)


def build_ornament_contours(params, family="Sans Serif", bold=False, italic=False):
    """Du paramétrage aux contours : (géométrie, contours). C'est le seul point d'entrée dont l'interface a besoin."""
    from laser_studio.vector.ornament_generator import build_ornament

    text = text_path(params.name, family, bold, italic)
    geometry = build_ornament(params, text_bounds(text))
    return geometry, assemble(geometry, text)
