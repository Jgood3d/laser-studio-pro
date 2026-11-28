"""Disposition des objets du dessin : boîte englobante d'un groupe, alignement,
répartition, point d'ancrage d'une forme. Calculs sur les tracés (QtGui, sans
widget) ; rien n'est modifié ici sauf dans move_group_to et resize_shape.

Repère machine : X vers la droite, Y vers le haut. Sur la boîte englobante
d'un tracé monde (QRectF), box.top() est le bord BAS de l'objet en mm et
box.bottom() son bord HAUT.
"""
from PyQt6.QtCore import QPointF

ALIGN_MODES = ("left", "right", "center_h", "top", "bottom", "middle_v")


def group_bounds(objects):
    """(gauche, bas, droite, haut) en mm de l'ensemble des objets."""
    boxes = [obj.world_path().boundingRect() for obj in objects]
    return (min(b.left() for b in boxes), min(b.top() for b in boxes),
            max(b.right() for b in boxes), max(b.bottom() for b in boxes))


def align_offsets(objects, mode):
    """Déplacement (dx, dy) de chaque objet pour les aligner les uns sur les
    autres (mode : ALIGN_MODES), d'après la boîte de l'ensemble."""
    boxes = [obj.world_path().boundingRect() for obj in objects]
    group_left = min(b.left() for b in boxes)
    group_right = max(b.right() for b in boxes)
    group_bottom = min(b.top() for b in boxes)
    group_top = max(b.bottom() for b in boxes)
    offsets = []
    for b in boxes:
        dx = dy = 0.0
        if mode == "left":
            dx = group_left - b.left()
        elif mode == "right":
            dx = group_right - b.right()
        elif mode == "center_h":
            dx = (group_left + group_right) / 2.0 - (b.left() + b.right()) / 2.0
        elif mode == "bottom":
            dy = group_bottom - b.top()
        elif mode == "top":
            dy = group_top - b.bottom()
        elif mode == "middle_v":
            dy = (group_bottom + group_top) / 2.0 - (b.top() + b.bottom()) / 2.0
        offsets.append((dx, dy))
    return offsets


def distribute_offsets(objects, axis):
    """[(objet, déplacement)] pour répartir les objets à espacement égal sur
    l'axe `axis` ("h" : déplacement en X, sinon en Y), les deux objets des
    extrémités restant en place."""
    boxes = [(obj, obj.world_path().boundingRect()) for obj in objects]
    moves = []
    if axis == "h":
        boxes.sort(key=lambda pair: pair[1].left())
        span = boxes[-1][1].right() - boxes[0][1].left()
        total_size = sum(b.width() for _, b in boxes)
        gap = (span - total_size) / (len(boxes) - 1)
        cursor = boxes[0][1].left()
        for obj, b in boxes:
            moves.append((obj, cursor - b.left()))
            cursor += b.width() + gap
    else:
        boxes.sort(key=lambda pair: pair[1].top())  # bas -> haut, en mm
        span = boxes[-1][1].bottom() - boxes[0][1].top()
        total_size = sum(b.height() for _, b in boxes)
        gap = (span - total_size) / (len(boxes) - 1)
        cursor = boxes[0][1].top()
        for obj, b in boxes:
            moves.append((obj, cursor - b.top()))
            cursor += b.height() + gap
    return moves


def shape_world_corners(obj):
    """4 coins de la forme en coordonnées machine (après local_path + world_transform)."""
    br = obj.local_path().boundingRect()
    locals_pts = [
        QPointF(br.left(), br.top()),
        QPointF(br.right(), br.top()),
        QPointF(br.left(), br.bottom()),
        QPointF(br.right(), br.bottom()),
    ]
    wt = obj.world_transform()
    return [wt.map(p) for p in locals_pts]


def shape_world_anchor(obj, anchor_id):
    """Coin d'ancrage en mm machine (Y vers le haut).

    - origin : point de placement (x_mm, y_mm) = 1er point lors d'un tracé A→B
    - bl/br/tl/tr : coins du bounding box monde
    """
    if anchor_id == "origin":
        return QPointF(float(obj.x_mm), float(obj.y_mm))
    corners = shape_world_corners(obj)
    # Machine : Y haut → « bas » = plus petite ordonnée
    if anchor_id == "bl":
        return min(corners, key=lambda p: (p.y(), p.x()))
    if anchor_id == "br":
        return min(corners, key=lambda p: (p.y(), -p.x()))
    if anchor_id == "tl":
        return max(corners, key=lambda p: (p.y(), -p.x()))
    if anchor_id == "tr":
        return max(corners, key=lambda p: (p.y(), p.x()))
    return QPointF(float(obj.x_mm), float(obj.y_mm))


def resize_shape(obj, width_mm, height_mm, anchor_id=None):
    """Change la taille d'une forme ; avec `anchor_id`, ce coin (ou l'origine)
    reste fixe dans le plan machine."""
    if anchor_id is None:
        obj.width_mm = width_mm
        obj.height_mm = height_mm
        return
    before = shape_world_anchor(obj, anchor_id)
    obj.width_mm = width_mm
    obj.height_mm = height_mm
    after = shape_world_anchor(obj, anchor_id)
    obj.x_mm += before.x() - after.x()
    obj.y_mm += before.y() - after.y()
