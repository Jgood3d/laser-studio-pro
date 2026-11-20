"""Remplissages à motif et bois de renne des boules de Noël, géométrie pure (sans Qt).

Repère : X vers la droite, Y vers le haut, en mm, centre de la boule en (0, 0).

Un remplissage est un réseau de BARRES (tiges de largeur constante) qui traversent toute une zone, d'un bord à
l'autre : la `ornament_region` les rogne à la zone voulue (au-dessus ou au-dessous de la bande du prénom) puis au
disque, si bien que chaque barre se retrouve soudée à l'anneau et à la bande. Rien ne peut donc tomber à la découpe.
Les barres se recoupent librement : les polygones sont soudés par union, jamais découpés deux fois.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple

Point = Tuple[float, float]
Polygon = List[Point]

FILL_KINDS = ("Rayures", "Treillis", "Tricot", "Vagues", "Feuilles")
# Plus petit pas accepté : en dessous, deux barres voisines laisseraient un vide plus fin que ce que le laser tient.
MIN_PITCH_MM = 4.5
MIN_BAR_MM = 1.2


def bar_width(pitch: float) -> float:
    """Largeur d'une barre pour un pas donné : toujours cuttable, et jamais plus de 35 % du pas."""
    return max(MIN_BAR_MM, min(0.20 * pitch, pitch - 1.6))


def _stem(x0, y0, x1, y1, w) -> Polygon:
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n * w / 2.0, dx / n * w / 2.0
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def _dot(cx, cy, r, n=10) -> Polygon:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _ribbon(points: Sequence[Point], w: float) -> Polygon:
    """Ruban de largeur `w` le long d'une courbe lisse (décalage de chaque côté, perpendiculairement)."""
    left: List[Point] = []
    right: List[Point] = []
    n = len(points)
    for i, (x, y) in enumerate(points):
        xa, ya = points[max(i - 1, 0)]
        xb, yb = points[min(i + 1, n - 1)]
        dx, dy = xb - xa, yb - ya
        norm = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / norm * w / 2.0, dx / norm * w / 2.0
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    return left + list(reversed(right))


def _lens(x0, y0, x1, y1, width, n=14) -> Polygon:
    """Feuille en forme de lentille entre deux points (pointue aux deux bouts), `width` en son milieu."""
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    top, bottom = [], []
    for i in range(n + 1):
        t = i / n
        half = width / 2.0 * math.sin(math.pi * t) ** 0.8
        px, py = x0 + dx * t, y0 + dy * t
        top.append((px + nx * half, py + ny * half))
        bottom.append((px - nx * half, py - ny * half))
    return top + list(reversed(bottom[1:-1]))


def fill_shapes(kind: str, pitch: float, box: Tuple[float, float, float, float]) -> List[Polygon]:
    """Barres d'un remplissage qui couvrent largement `box` = (x0, y0, x1, y1). L'appelant rogne à la zone."""
    pitch = max(float(pitch), MIN_PITCH_MM)
    x0, y0, x1, y1 = box
    w = bar_width(pitch)
    width, height = x1 - x0, y1 - y0
    out: List[Polygon] = []
    if width <= 0 or height <= 0:
        return out

    if kind in ("Rayures", "Treillis"):
        step = pitch * math.sqrt(2.0)          # pas mesuré perpendiculairement aux barres = `pitch`
        span = width + height
        k = -int(math.ceil(height / step))
        while x0 + k * step < x1 + height:
            xs = x0 + k * step
            out.append(_stem(xs, y0, xs + height, y1, w))                      # diagonale montante
            if kind == "Treillis":
                out.append(_stem(xs + height, y0, xs, y1, w))                  # diagonale descendante
            k += 1
        _ = span
    elif kind == "Tricot":
        amp = 0.22 * pitch
        row = 0.95 * pitch
        x = x0 - pitch / 2.0
        while x < x1 + pitch:
            pts: List[Point] = []
            y = y0 - row
            flip = 1
            while y <= y1 + row:
                pts.append((x + flip * amp, y))
                y += row / 2.0
                flip = -flip
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                out.append(_stem(xa, ya, xb, yb, w))
            for px, py in pts:
                out.append(_dot(px, py, w / 2.0))
            x += pitch
    elif kind == "Vagues":
        amp = 0.30 * pitch
        period = 2.6 * pitch
        y = y0 - amp
        row = 0
        while y < y1 + pitch:
            pts = []
            x = x0 - 1.0
            while x <= x1 + 1.0 + 1e-9:
                pts.append((x, y + amp * math.sin(2 * math.pi * x / period + (math.pi if row % 2 else 0.0))))
                x += 1.5
            out.append(_ribbon(pts, w))
            y += pitch
            row += 1
    elif kind == "Feuilles":
        spacing = 2.7 * pitch
        leaf = 0.95 * pitch
        step = 0.95 * pitch
        x = x0 - spacing / 2.0
        while x < x1 + spacing:
            out.append(_stem(x, y0 - pitch, x, y1 + pitch, w))
            y = y0 - pitch / 2.0
            side = 1
            while y < y1 + pitch:
                tip = (x + side * leaf * math.cos(math.radians(50)), y + leaf * math.sin(math.radians(50)))
                out.append(_lens(x, y, tip[0], tip[1], 0.55 * leaf))
                side = -side
                y += step / 2.0 * 1.0 + step / 2.0
            x += spacing
    return out


def _smooth(points: Sequence[Point], iterations: int = 2) -> List[Point]:
    pts = list(points)
    for _ in range(iterations):
        nxt = [pts[0]]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            nxt += [(0.75 * xa + 0.25 * xb, 0.75 * ya + 0.25 * yb), (0.25 * xa + 0.75 * xb, 0.25 * ya + 0.75 * yb)]
        nxt.append(pts[-1])
        pts = nxt
    return pts


def antler_shapes(radius: float, width: float) -> List[Polygon]:
    """Les deux bois d'un renne, posés sur le haut de la boule de rayon `radius`. Chacun part de l'anneau (le pied
    s'y enfonce) et se ramifie ; `width` : largeur des branches. Polygones à unir au corps de la boule."""
    r = radius
    # Perche principale puis andouillers, en fraction du rayon (côté droit ; le gauche est son miroir).
    beam = [(0.56, 0.80), (0.72, 1.02), (0.70, 1.26), (0.84, 1.50)]
    tines = [
        [(0.72, 1.02), (0.98, 1.08), (1.14, 1.26)],
        [(0.70, 1.26), (0.52, 1.36), (0.50, 1.56)],
        [(0.78, 1.38), (0.98, 1.46), (1.04, 1.64)],
    ]
    out: List[Polygon] = []
    for sign in (1.0, -1.0):
        for line in [beam] + tines:
            pts = _smooth([(sign * px * r, py * r) for px, py in line], 2)
            out.append(_ribbon(pts, width))
            out.append(_dot(*pts[0], width / 2.0, 14))
            out.append(_dot(*pts[-1], width / 2.0, 14))
    return out
