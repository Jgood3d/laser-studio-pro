"""Placement automatique (imbrication, « nesting ») de pièces vectorielles sur une feuille — sans Qt.

Chaque pièce est un groupe de contours (polygones en mm, repère Y vers le haut). Les pièces sont
placées l'une après l'autre, les plus grandes d'abord, à la position la plus basse et la plus à gauche
où elles ne gênent aucune pièce déjà placée, en essayant plusieurs rotations. La collision se calcule
sur une grille (cellules de `cell` mm) : forme réelle des pièces (pas seulement leur rectangle), ce qui
permet d'emboîter une petite pièce dans le creux d'une grande.

Garantie : les pièces ne se chevauchent pas et restent à au moins `spacing` mm les unes des autres, et à
`margin` mm du bord de la feuille. La grille est volontairement prudente (jamais trop près) : l'écart
réel peut dépasser légèrement celui demandé, d'environ 2 cellules.
"""
import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw

import vector_order as vo

ANGLE_SETS = {
    "none": (0.0,),
    "flip": (0.0, 90.0),
    "quarters": (0.0, 90.0, 180.0, 270.0),
    "eighths": (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0),
}


@dataclass
class Placement:
    index: int                    # position de la pièce dans la liste d'entrée
    angle: float                  # rotation (degrés, sens trigonométrique) autour du centre de la pièce
    pivot: tuple                  # centre du rectangle englobant d'origine (x, y)
    tx: float                     # translation appliquée APRÈS la rotation
    ty: float

    def apply(self, point):
        """Nouvelle position d'un point (x, y) de la pièce."""
        return rotate_point(point, self.angle, self.pivot[0], self.pivot[1], self.tx, self.ty)


@dataclass
class NestResult:
    placements: list = field(default_factory=list)
    unplaced: list = field(default_factory=list)       # indices des pièces qui n'ont pas trouvé de place
    sheet: tuple = (0.0, 0.0, 0.0, 0.0)                # x0, y0, largeur, hauteur de la feuille
    extent: tuple = (0.0, 0.0)                         # largeur / hauteur occupées (depuis le coin de la feuille)
    piece_area: float = 0.0                            # aire totale des pièces placées (mm²)

    @property
    def utilization(self):
        """Part de la zone occupée (rectangle englobant des pièces placées) réellement couverte par les pièces."""
        area = self.extent[0] * self.extent[1]
        return self.piece_area / area if area > 0 else 0.0


def rotate_point(p, angle_deg, cx, cy, tx=0.0, ty=0.0):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    dx, dy = p[0] - cx, p[1] - cy
    return (cx + dx * c - dy * s + tx, cy + dx * s + dy * c + ty)


def bounds_of(polygons):
    xs = [p[0] for poly in polygons for p in poly]
    ys = [p[1] for poly in polygons for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def group_by_containment(shapes):
    """Regroupe les formes imbriquées : un trou ou un détail gravé suit la pièce qui le contient.

    shapes : liste de formes, chacune étant une liste de polygones. Une forme B est dans une forme A si
    A est strictement plus grande, si le rectangle de A contient celui de B et si tous les points
    d'échantillon de B sont à l'intérieur de A (règle pair-impair : un point dans un TROU de A n'est pas
    dans A). Renvoie une liste de groupes d'indices ; le premier indice de chaque groupe est la forme
    extérieure, les autres sont triés."""
    n = len(shapes)
    boxes, areas, samples = [], [], []
    for polys in shapes:
        boxes.append(bounds_of(polys) if polys else (0, 0, 0, 0))
        areas.append(max((vo.polygon_area(p) for p in polys), default=0.0))
        samples.append([pt for poly in polys for pt in vo._samples(poly, 4)][:12])
    parent = [None] * n
    for j in range(n):
        if not samples[j]:
            continue
        best = None
        for i in range(n):
            if i == j or areas[i] <= areas[j] * (1 + 1e-9) + 1e-9:
                continue
            bi, bj = boxes[i], boxes[j]
            if bj[0] < bi[0] - 1e-9 or bj[1] < bi[1] - 1e-9 or bj[2] > bi[2] + 1e-9 or bj[3] > bi[3] + 1e-9:
                continue
            solids = [p for p in shapes[i] if len(p) >= 3]
            if not solids:
                continue
            if all(sum(1 for poly in solids if vo.point_in_polygon(x, y, poly)) % 2 == 1 for x, y in samples[j]):
                if best is None or areas[i] < areas[best]:
                    best = i
        parent[j] = best
    root = []
    for j in range(n):
        r = j
        while parent[r] is not None:
            r = parent[r]
        root.append(r)
    groups = {}
    for j in range(n):
        groups.setdefault(root[j], []).append(j)
    return [[r] + sorted(m for m in members if m != r) for r, members in sorted(groups.items())]


def _dilate(mask, r):
    """Dilatation carrée de r cellules (séparable)."""
    if r <= 0:
        return mask
    out = mask.copy()
    for k in range(1, r + 1):
        out[:, k:] |= mask[:, :-k]
        out[:, :-k] |= mask[:, k:]
    mid = out.copy()
    for k in range(1, r + 1):
        out[k:, :] |= mid[:-k, :]
        out[:-k, :] |= mid[k:, :]
    return out


class _Piece:
    """Pièce préparée : contours pleins (extérieurs) et traits (lignes ouvertes) servant au masque."""

    def __init__(self, index, polygons):
        self.index = index
        self.polygons = polygons
        depths = vo.nesting_depths(polygons)
        self.solids = [p for p, d in zip(polygons, depths) if d == 0 and len(p) >= 3 and vo.polygon_area(p) > 1e-9]
        self.strokes = [p for p, d in zip(polygons, depths) if d == 0 and not (len(p) >= 3 and vo.polygon_area(p) > 1e-9) and len(p) >= 2]
        self.area = sum(vo.polygon_area(p) for p in self.solids)
        x0, y0, x1, y1 = bounds_of(polygons)
        self.pivot = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        self.size = (x1 - x0, y1 - y0)

    def mask(self, angle, cell, r):
        """(masque booléen dilaté de r cellules, coin bas-gauche du corps après rotation, en mm)."""
        cx, cy = self.pivot
        solids = [[rotate_point(p, angle, cx, cy) for p in poly] for poly in self.solids]
        strokes = [[rotate_point(p, angle, cx, cy) for p in poly] for poly in self.strokes]
        x0, y0, x1, y1 = bounds_of(solids + strokes)
        w = int(math.ceil((x1 - x0) / cell)) + 1 + 2 * r
        h = int(math.ceil((y1 - y0) / cell)) + 1 + 2 * r
        img = Image.new("1", (w, h), 0)
        draw = ImageDraw.Draw(img)
        for poly in solids:
            pts = [((x - x0) / cell + r, (y - y0) / cell + r) for x, y in poly]
            draw.polygon(pts, fill=1)
            draw.line(pts + [pts[0]], fill=1, width=1)
        for poly in strokes:
            pts = [((x - x0) / cell + r, (y - y0) / cell + r) for x, y in poly]
            draw.line(pts, fill=1, width=1)
        return _dilate(np.array(img, dtype=bool), r), (x0, y0)


def nest(pieces, sheet_w, sheet_h, spacing=2.0, margin=0.0, angles=ANGLE_SETS["quarters"], cell=1.0,
         origin=(0.0, 0.0), progress=None):
    """Place `pieces` (liste de listes de polygones en mm) sur une feuille sheet_w x sheet_h dont le coin
    bas-gauche est `origin`. Renvoie un NestResult ; pour chaque Placement, p' = pivot + R(angle)(p - pivot) + (tx, ty).

    progress(done, total) est appelée après chaque pièce si fournie (renvoyer False l'interrompt)."""
    cell = float(cell)
    if cell <= 0:
        raise ValueError("cell")
    result = NestResult(sheet=(origin[0], origin[1], sheet_w, sheet_h))
    prepared = [_Piece(i, polys) for i, polys in enumerate(pieces) if polys]
    result.unplaced = [i for i, polys in enumerate(pieces) if not polys]
    usable_w, usable_h = sheet_w - 2 * margin, sheet_h - 2 * margin
    if usable_w <= 0 or usable_h <= 0:
        result.unplaced += [p.index for p in prepared]
        return result
    # Rayon de dilatation : moitié de l'écart voulu, plus 1 cellule pour couvrir les arrondis de la grille.
    r = int(math.ceil(spacing / (2.0 * cell))) + 1
    W = int(math.ceil(usable_w / cell)) + 2 * r
    H = int(math.ceil(usable_h / cell)) + 2 * r
    occ = np.zeros((H, W), dtype=bool)
    base_x, base_y = origin[0] + margin, origin[1] + margin

    order = sorted(prepared, key=lambda p: (-p.area, -(p.size[0] * p.size[1]), p.index))
    masks = {p.index: [(a,) + p.mask(a, cell, r) for a in angles] for p in order}
    hmax = max((m[1].shape[0] for ms in masks.values() for m in ms), default=1)
    wmax = max((m[1].shape[1] for ms in masks.values() for m in ms), default=1)

    def padded(n):
        return ((n + 15) // 16) * 16

    top_used = 0
    placed_boxes = []
    for done, piece in enumerate(order, 1):
        rows = min(H, top_used + hmax + 1)
        shape = (padded(rows + hmax - 1), padded(W + wmax - 1))
        fa = np.fft.rfft2(occ[:rows].astype(np.float64), s=shape)
        best = None
        for angle, mask, (bx, by) in masks[piece.index]:
            h, w = mask.shape
            if h > rows or w > W:
                continue
            fb = np.fft.rfft2(mask[::-1, ::-1].astype(np.float64), s=shape)
            corr = np.fft.irfft2(fa * fb, s=shape)[h - 1:rows, w - 1:W]
            ys, xs = np.nonzero(corr < 0.5)
            if ys.size == 0:
                continue
            score = (ys + h).astype(np.int64) * (W + 1) + xs
            k = int(np.argmin(score))
            cand = (int(score[k]), angle, int(ys[k]), int(xs[k]), mask, bx, by)
            if best is None or cand[0] < best[0]:
                best = cand
        if best is not None:
            _, angle, y, x, mask, bx, by = best
            h, w = mask.shape
            occ[y:y + h, x:x + w] |= mask
            top_used = max(top_used, y + h)
            target_x = base_x + x * cell
            target_y = base_y + y * cell
            result.placements.append(Placement(piece.index, angle, piece.pivot, target_x - bx, target_y - by))
            result.piece_area += piece.area
            placed_boxes.append((target_x, target_y, target_x + (w - 2 * r) * cell, target_y + (h - 2 * r) * cell))
        else:
            result.unplaced.append(piece.index)
        if progress is not None and progress(done, len(order)) is False:
            result.unplaced += [p.index for p in order[done:]]
            break
    result.placements.sort(key=lambda pl: pl.index)
    result.unplaced.sort()
    if placed_boxes:
        result.extent = (max(b[2] for b in placed_boxes) - base_x, max(b[3] for b in placed_boxes) - base_y)
    return result
