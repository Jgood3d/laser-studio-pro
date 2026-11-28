"""Gabarit de placement (logique pure, sans Qt) : une plaque à découper avec une poche par objet, aux dimensions
de l'objet (plus un jeu). On y pose les porte-clés, décapsuleurs, stylos... pour les graver toujours au même endroit.

Repère : mm, Y vers le haut, origine de la plaque en bas à gauche. Les poches sont rangées comme les exemplaires de
« Dupliquer en série » : avec les mêmes colonnes, les mêmes espacements et le même sens des rangées, chaque exemplaire
tombe pile sur sa poche (espacement = distance entre deux objets, bord à bord).
"""
import math
from dataclasses import dataclass

MAX_POCKETS = 400
MIN_WALL_MM = 2.0          # en dessous, la paroi entre deux poches est fragile (avertissement)
_EPS = 1e-9


class JigError(Exception):
    """Réglage impossible. `code` : size | count | overlap ; `info` : valeurs pour le message."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


@dataclass
class JigParams:
    obj_w: float                      # dimensions de l'objet à loger
    obj_h: float
    cols: int = 1
    rows: int = 1
    clearance: float = 0.3            # jeu de chaque côté de l'objet
    gap_x: float = 6.0                # distance entre deux objets voisins (comme « Dupliquer en série »)
    gap_y: float = 6.0
    margin: float = 8.0               # bordure entre une poche et le bord de la plaque
    pocket_shape: str = "rect"        # "rect" | "ellipse"
    pocket_radius: float = 0.0        # coins arrondis des poches (rect)
    plate_radius: float = 0.0         # coins arrondis de la plaque
    upward: bool = True               # première poche en bas à gauche (rangées vers le haut) ou en haut à gauche


@dataclass
class Jig:
    params: JigParams
    pocket_w: float
    pocket_h: float
    pitch_x: float
    pitch_y: float
    plate_w: float
    plate_h: float
    wall_x: float                     # épaisseur de matière entre deux poches voisines
    wall_y: float
    plate: list                       # contour de la plaque (polygone fermé)
    pockets: list                     # un polygone fermé par poche, dans l'ordre des exemplaires (ligne par ligne)
    object_origins: list              # coin bas-gauche de l'objet dans chaque poche (même ordre)

    @property
    def count(self):
        return len(self.pockets)

    def thin_wall(self):
        """Vrai si une paroi entre deux poches est inférieure à MIN_WALL_MM."""
        p = self.params
        return (p.cols > 1 and self.wall_x < MIN_WALL_MM) or (p.rows > 1 and self.wall_y < MIN_WALL_MM)


def rounded_rect(x, y, w, h, radius=0.0, segments=8):
    """Rectangle (coin bas-gauche x, y) aux coins arrondis, polygone fermé dans le sens trigonométrique."""
    r = max(0.0, min(float(radius), w / 2.0, h / 2.0))
    if r <= _EPS:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    pts = []
    corners = ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180))
    for cx, cy, start in corners:
        for i in range(segments + 1):
            a = math.radians(start + 90.0 * i / segments)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(pts[0])
    return pts


def ellipse(x, y, w, h, segments=72):
    """Ellipse inscrite dans le rectangle (x, y, w, h), polygone fermé."""
    cx, cy, rx, ry = x + w / 2.0, y + h / 2.0, w / 2.0, h / 2.0
    pts = [(cx + rx * math.cos(2 * math.pi * i / segments), cy + ry * math.sin(2 * math.pi * i / segments))
           for i in range(segments)]
    pts.append(pts[0])
    return pts


def build_jig(p):
    """Géométrie du gabarit pour `p` (JigParams). Lève JigError si les réglages sont impossibles."""
    if p.obj_w <= 0 or p.obj_h <= 0:
        raise JigError("size")
    cols, rows = max(1, int(p.cols)), max(1, int(p.rows))
    if cols * rows > MAX_POCKETS:
        raise JigError("count", max=MAX_POCKETS)
    c = max(0.0, float(p.clearance))
    pocket_w, pocket_h = p.obj_w + 2 * c, p.obj_h + 2 * c
    pitch_x, pitch_y = p.obj_w + p.gap_x, p.obj_h + p.gap_y
    wall_x, wall_y = pitch_x - pocket_w, pitch_y - pocket_h
    if (cols > 1 and wall_x <= _EPS) or (rows > 1 and wall_y <= _EPS):
        raise JigError("overlap", min=f"{2 * c:g}")
    margin = max(0.0, float(p.margin))
    plate_w = 2 * margin + (cols - 1) * pitch_x + pocket_w
    plate_h = 2 * margin + (rows - 1) * pitch_y + pocket_h
    pockets, origins = [], []
    for k in range(cols * rows):
        row, col = divmod(k, cols)
        px = margin + col * pitch_x
        py = margin + (row if p.upward else rows - 1 - row) * pitch_y
        if p.pocket_shape == "ellipse":
            pockets.append(ellipse(px, py, pocket_w, pocket_h))
        else:
            pockets.append(rounded_rect(px, py, pocket_w, pocket_h, p.pocket_radius))
        origins.append((px + c, py + c))
    return Jig(params=p, pocket_w=pocket_w, pocket_h=pocket_h, pitch_x=pitch_x, pitch_y=pitch_y,
               plate_w=plate_w, plate_h=plate_h, wall_x=wall_x, wall_y=wall_y,
               plate=rounded_rect(0.0, 0.0, plate_w, plate_h, p.plate_radius), pockets=pockets,
               object_origins=origins)


def plate_origin_around(jig, obj_min_x, obj_min_y):
    """Coin bas-gauche de la plaque pour que la première poche entoure l'objet dont le coin bas-gauche est
    (obj_min_x, obj_min_y) : les exemplaires de « Dupliquer en série » (mêmes colonnes et espacements) tombent
    alors chacun dans sa poche."""
    ox, oy = jig.object_origins[0]
    return obj_min_x - ox, obj_min_y - oy
