"""Générateur de puzzle Jigsaw — tenon type champignon (col + tête ronde).

Repère LSP : X droite, Y haut. Arêtes internes partagées (emboîtement exact).
"""
from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple

Point = Tuple[float, float]


class PuzzlePiece:
    def __init__(self, col: int, row: int, points: List[Point]):
        self.id = (col, row)
        self.cut = points
        self.x = 0.0
        self.y = 0.0

    def placed(self):
        return self.cut


class PuzzleResult:
    def __init__(self, pieces, width, height, x_offset, y_offset):
        self.pieces = pieces
        self.width = width
        self.height = height
        self.x_offset = x_offset
        self.y_offset = y_offset


class PuzzleParams:
    def __init__(
        self,
        width=119.21,
        height=65.02,
        nx=5,
        ny=4,
        x=0.0,
        y=0.0,
        kerf=0.1,
        style="Classique",
        cut_layer_id=None,
        seed=None,
        tab_depth=0.22,      # profondeur / longueur côté
        tab_span=0.34,       # largeur zone / longueur côté
        neck_width=0.45,     # largeur col / largeur tête  (0.35–0.55)
        pos_random=0.60,
        jitter=0.10,
        **_extra,
    ):
        self.width = float(width)
        self.height = float(height)
        self.nx = int(nx)
        self.ny = int(ny)
        self.x = float(x)
        self.y = float(y)
        self.kerf = float(kerf)
        self.style = style
        self.cut_layer_id = cut_layer_id
        self.seed = seed
        self.tab_depth = float(tab_depth)
        self.tab_span = float(tab_span)
        self.neck_width = float(neck_width)
        self.pos_random = float(pos_random)
        self.jitter = float(jitter)
        # alias rétrocompat
        self.tab_size = self.tab_depth
        self.tab_width = self.tab_span
        self.head_bulge = 1.0 / max(0.3, self.neck_width)


def build_puzzle(params: PuzzleParams) -> PuzzleResult:
    style = getattr(params, "style", "Classique") or "Classique"
    seed = getattr(params, "seed", None)
    base = dict(
        width_mm=params.width, height_mm=params.height,
        cols=params.nx, rows=params.ny,
        x_offset=params.x, y_offset=params.y, seed=seed,
    )
    if style == "Organique":
        return generate_wavy_grid_puzzle(**base)
    return generate_classic_jigsaw_puzzle(
        **base,
        tab_depth=params.tab_depth,
        tab_span=params.tab_span,
        neck_width=getattr(params, "neck_width", 0.45),
        pos_random=getattr(params, "pos_random", 0.60),
        jitter_amt=getattr(params, "jitter", 0.10),
    )


def _lerp(a, b, t):
    return a + (b - a) * t


def _reverse(pts: Sequence[Point]) -> List[Point]:
    return list(reversed(pts))


def _straight(p0: Point, p1: Point, n: int = 4) -> List[Point]:
    return [(_lerp(p0[0], p1[0], i / n), _lerp(p0[1], p1[1], i / n)) for i in range(n + 1)]


def generate_jigsaw_edge(
    p_start: Point,
    p_end: Point,
    tab_sign: int,
    *,
    tab_depth: float = 0.22,
    tab_span: float = 0.34,
    neck_width: float = 0.45,
    t_mid: float = 0.50,
    jitter: float = 0.0,
) -> List[Point]:
    """Tenon classique : plat → col lisse → tête circulaire → col → plat.

    Construction géométrique (pas un simple sinus) pour coller aux puzzles grand public.
    """
    x1, y1 = p_start
    x2, y2 = p_end
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return [p_start]
    if tab_sign == 0:
        return _straight(p_start, p_end, 6)

    ux, uy = dx / length, dy / length
    nx, ny = -uy * tab_sign, ux * tab_sign

    span = max(0.22, min(0.46, tab_span * (1 + 0.06 * jitter)))
    depth = length * max(0.14, min(0.34, tab_depth * (1 + 0.08 * jitter)))
    t_mid = max(span / 2 + 0.03, min(1.0 - span / 2 - 0.03, t_mid))
    t0 = t_mid - span / 2
    t1 = t_mid + span / 2

    # Tête = cercle. Le col est plus étroit que le diamètre de la tête.
    head_r = depth * 0.48
    neck_ratio = max(0.32, min(0.60, neck_width * (1 + 0.05 * jitter)))
    neck_half = head_r * neck_ratio          # demi-largeur du col (mm le long de l'arête)
    head_half = head_r * 0.92                # demi-largeur max de la tête le long de l'arête

    # Centre du cercle de tête, poussé le long de la normale
    # Sommet du cercle ≈ depth
    center_n = depth - head_r

    def base(t):
        return (_lerp(x1, x2, t), _lerp(y1, y2, t))

    def loc(s, n):
        """s = décalage le long de l'arête (mm) depuis le centre du tenon, n = normale."""
        cx = _lerp(x1, x2, t_mid)
        cy = _lerp(y1, y2, t_mid)
        return (cx + ux * s + nx * n, cy + uy * s + ny * n)

    half_zone = length * span / 2

    # --- points de construction ---
    # A  : début zone (sur la ligne)
    # B  : entrée col (légère courbe)
    # C  : base de la tête (jonction cercle)
    # puis arc
    A_s = -half_zone
    C_s = -neck_half
    # Point sur le cercle à l'angle où on joint le col
    # Angle depuis la normale : asin(neck_half/head_r) limité
    join_ang = math.asin(max(-0.95, min(0.95, neck_half / head_r)))

    pts: List[Point] = []
    pts.extend(_straight(p_start, base(t0), 5)[:-1])

    # A sur la ligne
    A = loc(A_s, 0.0)
    pts.append(A)

    # Courbe de Bézier quadratique A → C (entrée col douce)
    # Point de contrôle : un peu vers l'extérieur pour un arrondi naturel
    C = loc(C_s, center_n)
    # Contrôle placé à mi-chemin en s, légèrement sorti
    ctrl1 = loc((A_s + C_s) / 2, center_n * 0.18)
    for i in range(1, 10):
        t = i / 10
        u = 1 - t
        px = u * u * A[0] + 2 * u * t * ctrl1[0] + t * t * C[0]
        py = u * u * A[1] + 2 * u * t * ctrl1[1] + t * t * C[1]
        pts.append((px, py))

    # Arc de tête : du joint gauche au joint droit
    # Angles : normale = 0 en polar local
    base_ang = math.atan2(ny, nx)
    # join gauche = base_ang + (pi/2 + join? ) 
    # Le point C est à gauche : angle = base_ang + pi/2 approximativement,
    # plus précisément angle = base_ang + atan2(direction)
    # Point sur cercle relatif : offset from center = C - center
    ccx = _lerp(x1, x2, t_mid) + nx * center_n
    ccy = _lerp(y1, y2, t_mid) + ny * center_n

    # Angle du point C par rapport au centre
    def ang_of(pt):
        return math.atan2(pt[1] - ccy, pt[0] - ccx)

    # Point droit miroir
    C2 = loc(neck_half, center_n)
    a_left = ang_of(C)
    a_right = ang_of(C2)

    # On veut parcourir le côté EXTERIEUR (sommet du tenon), pas le petit arc intérieur.
    # Delta dans le sens qui passe par le sommet (direction nx, ny)
    summit = (ccx + nx * head_r, ccy + ny * head_r)
    a_sum = ang_of(summit)

    def lerp_angle_via(a0, a1, via, n):
        """Interpole a0 → a1 en passant près de `via`."""
        # Normaliser
        def norm(a):
            while a < -math.pi:
                a += 2 * math.pi
            while a > math.pi:
                a -= 2 * math.pi
            return a
        a0, a1, via = norm(a0), norm(a1), norm(via)
        # Deux chemins possibles
        d_ccw = (a1 - a0) % (2 * math.pi)
        d_cw = (a0 - a1) % (2 * math.pi)
        # Lequel passe près de via
        def dist_via(d, direction):
            # sample mid
            mid = a0 + direction * d / 2
            return abs(norm(mid - via))
        if dist_via(d_ccw, +1) <= dist_via(d_cw, -1):
            delta, direction = d_ccw, +1
        else:
            delta, direction = d_cw, -1
        return [a0 + direction * delta * i / n for i in range(n + 1)]

    angles = lerp_angle_via(a_left, a_right, a_sum, 20)
    for a in angles:
        pts.append((ccx + math.cos(a) * head_r, ccy + math.sin(a) * head_r))

    # Sortie C2 → A2
    A2 = loc(half_zone, 0.0)
    ctrl2 = loc((half_zone + neck_half) / 2, center_n * 0.18)
    for i in range(1, 10):
        t = i / 10
        u = 1 - t
        px = u * u * C2[0] + 2 * u * t * ctrl2[0] + t * t * A2[0]
        py = u * u * C2[1] + 2 * u * t * ctrl2[1] + t * t * A2[1]
        pts.append((px, py))
    pts.append(A2)

    pts.append(base(t1))
    pts.extend(_straight(base(t1), p_end, 5)[1:])
    return pts


def generate_classic_jigsaw_puzzle(
    width_mm, height_mm, cols=5, rows=4,
    x_offset=0.0, y_offset=0.0, seed=None,
    tab_depth=0.22, tab_span=0.34, neck_width=0.45,
    pos_random=0.60, jitter_amt=0.10,
) -> PuzzleResult:
    rng = random.Random(seed)
    dx = width_mm / cols
    dy = height_mm / rows

    h_tabs = [[rng.choice((-1, 1)) for _ in range(max(0, cols - 1))] for _ in range(rows)]
    v_tabs = [[rng.choice((-1, 1)) for _ in range(cols)] for _ in range(max(0, rows - 1))]
    h_jit = [[rng.uniform(-1, 1) * jitter_amt for _ in range(max(0, cols - 1))] for _ in range(rows)]
    v_jit = [[rng.uniform(-1, 1) * jitter_amt for _ in range(cols)] for _ in range(max(0, rows - 1))]

    def rand_mid():
        spread = 0.28 * max(0.0, min(1.0, pos_random))
        return 0.5 + rng.uniform(-spread, spread)

    h_mid = [[rand_mid() for _ in range(max(0, cols - 1))] for _ in range(rows)]
    v_mid = [[rand_mid() for _ in range(cols)] for _ in range(max(0, rows - 1))]
    kw = dict(tab_depth=tab_depth, tab_span=tab_span, neck_width=neck_width)

    H_edges = []
    for r in range(rows):
        row = []
        for c in range(cols - 1):
            x = x_offset + (c + 1) * dx
            y0, y1 = y_offset + r * dy, y_offset + (r + 1) * dy
            row.append(generate_jigsaw_edge(
                (x, y0), (x, y1), tab_sign=-h_tabs[r][c],
                t_mid=h_mid[r][c], jitter=h_jit[r][c], **kw,
            ))
        H_edges.append(row)

    V_edges = []
    for r in range(rows - 1):
        row = []
        for c in range(cols):
            y = y_offset + (r + 1) * dy
            x0, x1 = x_offset + c * dx, x_offset + (c + 1) * dx
            row.append(generate_jigsaw_edge(
                (x0, y), (x1, y), tab_sign=v_tabs[r][c],
                t_mid=v_mid[r][c], jitter=v_jit[r][c], **kw,
            ))
        V_edges.append(row)

    pieces = []
    for r in range(rows):
        for c in range(cols):
            x0 = x_offset + c * dx
            x1 = x0 + dx
            y0 = y_offset + r * dy
            y1 = y0 + dy
            bottom = _straight((x0, y0), (x1, y0), 6) if r == 0 else list(V_edges[r - 1][c])
            right = _straight((x1, y0), (x1, y1), 6) if c == cols - 1 else list(H_edges[r][c])
            top = _straight((x1, y1), (x0, y1), 6) if r == rows - 1 else _reverse(V_edges[r][c])
            left = _straight((x0, y1), (x0, y0), 6) if c == 0 else _reverse(H_edges[r][c - 1])
            contour: List[Point] = []
            for edge in (bottom, right, top, left):
                start = 0 if not contour else 1
                contour.extend(edge[start:])
            pieces.append(PuzzlePiece(c, r, contour))
    return PuzzleResult(pieces, width_mm, height_mm, x_offset, y_offset)


def _wave_edge(p0, p1, amplitude, sign, steps=24):
    x1, y1 = p0
    x2, y2 = p1
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-9 or sign == 0 or abs(amplitude) < 1e-9:
        return _straight(p0, p1, 6)
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    pts = []
    for i in range(steps + 1):
        t = i / steps
        window = math.sin(math.pi * t) ** 1.15
        bump = amplitude * sign * math.sin(math.pi * t) * window
        pts.append((x1 + t * dx + nx * bump, y1 + t * dy + ny * bump))
    return pts


def generate_wavy_grid_puzzle(
    width_mm, height_mm, cols=5, rows=4,
    x_offset=0.0, y_offset=0.0, seed=None,
) -> PuzzleResult:
    rng = random.Random(seed)
    dx = width_mm / cols
    dy = height_mm / rows
    amp_x, amp_y = dx * 0.11, dy * 0.11
    h_sign = [[rng.choice((-1, 1)) for _ in range(max(0, cols - 1))] for _ in range(rows)]
    v_sign = [[rng.choice((-1, 1)) for _ in range(cols)] for _ in range(max(0, rows - 1))]
    H_edges = []
    for r in range(rows):
        row = []
        for c in range(cols - 1):
            x = x_offset + (c + 1) * dx
            y0, y1 = y_offset + r * dy, y_offset + (r + 1) * dy
            row.append(_wave_edge((x, y0), (x, y1), amp_x, -h_sign[r][c]))
        H_edges.append(row)
    V_edges = []
    for r in range(rows - 1):
        row = []
        for c in range(cols):
            y = y_offset + (r + 1) * dy
            x0, x1 = x_offset + c * dx, x_offset + (c + 1) * dx
            row.append(_wave_edge((x0, y), (x1, y), amp_y, v_sign[r][c]))
        V_edges.append(row)
    pieces = []
    for r in range(rows):
        for c in range(cols):
            x0 = x_offset + c * dx
            x1 = x0 + dx
            y0 = y_offset + r * dy
            y1 = y0 + dy
            bottom = _straight((x0, y0), (x1, y0), 6) if r == 0 else list(V_edges[r - 1][c])
            right = _straight((x1, y0), (x1, y1), 6) if c == cols - 1 else list(H_edges[r][c])
            top = _straight((x1, y1), (x0, y1), 6) if r == rows - 1 else _reverse(V_edges[r][c])
            left = _straight((x0, y1), (x0, y0), 6) if c == 0 else _reverse(H_edges[r][c - 1])
            contour: List[Point] = []
            for edge in (bottom, right, top, left):
                start = 0 if not contour else 1
                contour.extend(edge[start:])
            pieces.append(PuzzlePiece(c, r, contour))
    return PuzzleResult(pieces, width_mm, height_mm, x_offset, y_offset)
