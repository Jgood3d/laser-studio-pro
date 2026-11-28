"""Générateur de puzzle Jigsaw — tenon à col étroit et tête ronde qui déborde du col.

Repère LSP : X droite, Y haut. Arêtes internes partagées (emboîtement exact).

Forme de l'ergot : trois courbes de Bézier cubiques (épaule, col, tête). La taille de référence est la plus
petite dimension d'une pièce (`knob_unit`), pour que les ergots horizontaux et verticaux aient la même
taille même avec des pièces rectangulaires. Deux plafonds, mesurés sur des milliers de puzzles, évitent que
deux ergots voisins se touchent : la hauteur de la tête (MAX_TAB_DEPTH) et le décalage d'un gros ergot vers
un coin (voir `generate_classic_jigsaw_puzzle`) ; le jeu minimal entre deux traits reste >= 0,1 x la plus
petite dimension d'une pièce sur toute la plage des curseurs.
"""
from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple

Point = Tuple[float, float]


class PuzzleError(ValueError):
    """Paramètres de puzzle invalides (message prêt à afficher)."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


class PuzzlePiece:
    def __init__(self, col: int, row: int, points: List[Point]):
        self.id = (col, row)
        self.cut = points
        self.x = 0.0
        self.y = 0.0

    def placed(self):
        return self.cut


class PuzzleResult:
    """Résultat d'un puzzle.

    `pieces` : un contour fermé par pièce (nominal, sans kerf) — sert à l'aperçu. Deux pièces voisines y
    partagent leur frontière : NE PAS les envoyer telles quelles au laser, chaque arête interne serait
    découpée deux fois.
    `outline` : contour extérieur fermé du puzzle (rectangle, agrandi de kerf/2 par `apply_kerf`).
    `edges` : arêtes internes, chacune UNE seule fois, en tracés ouverts. C'est ce que le laser découpe
    (avec `outline`)."""

    def __init__(self, pieces, width, height, x_offset, y_offset, outline=None, edges=None):
        self.pieces = pieces
        self.width = width
        self.height = height
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.outline = outline if outline is not None else []
        self.edges = edges if edges is not None else []


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


def validate_params(params: PuzzleParams):
    """Vérifie les dimensions et la taille des tenons ; lève PuzzleError si invalide."""
    if params.width <= 0 or params.height <= 0:
        raise PuzzleError("size", width=params.width, height=params.height)
    if params.nx < 1 or params.ny < 1:
        raise PuzzleError("grid", nx=params.nx, ny=params.ny)
    if params.kerf < 0:
        raise PuzzleError("kerf", value=params.kerf)
    piece_w = params.width / params.nx
    piece_h = params.height / params.ny
    min_side = min(piece_w, piece_h)
    if min_side < 3.0:
        raise PuzzleError("piece_too_small", side=min_side, minimum=3.0)
    # tab_depth est déjà un ratio dans generate_jigsaw_edge (depth = length * tab_depth)
    if params.tab_depth > 0.40:
        raise PuzzleError("tab_too_deep", value=params.tab_depth, maximum=0.40)
    if params.tab_span < 0.15 or params.tab_span > 0.55:
        raise PuzzleError("tab_span", value=params.tab_span)
    if not (0.25 <= params.neck_width <= 0.70):
        raise PuzzleError("neck_width", value=params.neck_width)
    # kerf ne doit pas manger toute la pièce
    if params.kerf > 0 and params.kerf >= min_side * 0.25:
        raise PuzzleError("kerf_too_large", value=params.kerf, side=min_side)
    return piece_w, piece_h


def _close_contour(pts: List[Point]) -> List[Point]:
    """Assure un contour fermé (dernier point = premier)."""
    if len(pts) < 3:
        return pts
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    if abs(x0 - x1) > 1e-9 or abs(y0 - y1) > 1e-9:
        return list(pts) + [(x0, y0)]
    return list(pts)


def apply_kerf(result: PuzzleResult, kerf: float) -> PuzzleResult:
    """Compense la largeur du trait laser.

    Une arête interne n'est découpée qu'une fois : le trait enlève kerf/2 à chacune des deux pièces qui
    la bordent, donc aucune correction n'est à faire. Seul le contour extérieur est agrandi de kerf/2,
    pour que le puzzle fini ait les dimensions demandées. (Les arêtes internes s'arrêtent sur la
    frontière nominale : l'écart de kerf/2 est couvert par la largeur du trait.)"""
    if kerf is None or kerf <= 0:
        return result
    h = 0.5 * float(kerf)
    result.outline = _outline_rect(
        result.x_offset - h, result.y_offset - h,
        result.x_offset + result.width + h, result.y_offset + result.height + h,
    )
    return result


def _outline_rect(x0, y0, x1, y1) -> List[Point]:
    """Contour extérieur : rectangle fermé, sens anti-horaire."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _unique_edges(H_edges, V_edges) -> List[List[Point]]:
    """Arêtes internes à plat, chacune une seule fois (en tracés ouverts)."""
    return [list(e) for row in H_edges for e in row] + [list(e) for row in V_edges for e in row]


def build_puzzle(params: PuzzleParams) -> PuzzleResult:
    validate_params(params)
    style = getattr(params, "style", "Classique") or "Classique"
    seed = getattr(params, "seed", None)
    base = dict(
        width_mm=params.width, height_mm=params.height,
        cols=params.nx, rows=params.ny,
        x_offset=params.x, y_offset=params.y, seed=seed,
    )
    if style == "Organique":
        result = generate_wavy_grid_puzzle(**base)
    else:
        result = generate_classic_jigsaw_puzzle(
            **base,
            tab_depth=params.tab_depth,
            tab_span=params.tab_span,
            neck_width=getattr(params, "neck_width", 0.45),
            pos_random=getattr(params, "pos_random", 0.60),
            jitter_amt=getattr(params, "jitter", 0.10),
        )
    # Fermeture des pièces (aperçu) ; le kerf ne s'applique qu'au contour extérieur (voir apply_kerf)
    for piece in result.pieces:
        piece.cut = _close_contour(piece.cut)
    return apply_kerf(result, params.kerf)


def _lerp(a, b, t):
    return a + (b - a) * t


def _reverse(pts: Sequence[Point]) -> List[Point]:
    return list(reversed(pts))


def _straight(p0: Point, p1: Point, n: int = 4) -> List[Point]:
    return [(_lerp(p0[0], p1[0], i / n), _lerp(p0[1], p1[1], i / n)) for i in range(n + 1)]


CURVE_STEPS = 14          # points par segment de Bézier (3 segments par ergot)
MAX_TAB_DEPTH = 0.30      # hauteur maximale d'un ergot, en fraction de la plus petite dimension d'une pièce


def _bezier(p0, p1, p2, p3, steps):
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1.0 - t
        a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


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
    knob_unit: float = None,
) -> List[Point]:
    """Arête avec un ergot : plat -> épaule -> col -> tête ronde qui déborde -> col -> épaule -> plat.

    tab_depth = hauteur de la tête, tab_span = largeur de la tête, neck_width = largeur du col (relative),
    t_mid = position de l'ergot le long de l'arête (0..1), jitter = variation de taille de CET ergot
    (-0,3..+0,3). knob_unit = taille de référence (mm) des ergots ; par défaut la longueur de l'arête.
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

    s = (knob_unit if knob_unit else length) / length       # ergot dimensionné sur knob_unit
    size = max(0.75, min(1.25, 1.0 + jitter))
    # Hauteur effective de la tête (variation de taille comprise), plafonnée : au-delà, un ergot
    # horizontal et un ergot vertical voisins finissent par se toucher.
    depth = min(max(0.10, min(0.40, tab_depth)) * size, MAX_TAB_DEPTH)
    t = (depth / 2.5) * s                                    # la tête monte à 2,5 t
    b = 2.0 * t * (max(0.18, min(0.50, tab_span)) / 0.34)    # demi-largeur (contrôle) de la tête
    a = t * (max(0.30, min(0.65, neck_width)) / 0.45)        # demi-largeur du col
    a = min(a, 0.80 * b)                                     # le col reste plus étroit que la tête
    c0 = max(0.35, min(0.65, t_mid))

    p = [
        (0.0, 0.0),
        (max(c0 - 0.30, 0.02), 0.0),
        (c0, -t),
        (c0 - a, t),
        (c0 - b, 3.0 * t),
        (c0 + b, 3.0 * t),
        (c0 + a, t),
        (c0, -t),
        (min(c0 + 0.30, 0.98), 0.0),
        (1.0, 0.0),
    ]
    p = [(x1 + ux * (l * length) + nx * (w * length), y1 + uy * (l * length) + ny * (w * length))
         for l, w in p]
    pts = [p[0]]
    pts += _bezier(p[0], p[1], p[2], p[3], CURVE_STEPS)
    pts += _bezier(p[3], p[4], p[5], p[6], CURVE_STEPS)
    pts += _bezier(p[6], p[7], p[8], p[9], CURVE_STEPS)
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

    # Plus l'ergot est profond, moins on peut le décaler vers un coin : un ergot horizontal et un ergot
    # vertical voisins se feraient face dans le même coin. À profondeur maximale les ergots restent
    # centrés ; seuls leur taille et leur sens varient.
    deep = min(tab_depth * (1.0 + max(0.0, jitter_amt)), MAX_TAB_DEPTH)
    room = 1.0 - max(0.0, min(1.0, (deep - 0.18) / 0.12))

    def rand_mid():
        spread = 0.15 * max(0.0, min(1.0, pos_random)) * room
        return 0.5 + rng.uniform(-spread, spread)

    h_mid = [[rand_mid() for _ in range(max(0, cols - 1))] for _ in range(rows)]
    v_mid = [[rand_mid() for _ in range(cols)] for _ in range(max(0, rows - 1))]
    kw = dict(tab_depth=tab_depth, tab_span=tab_span, neck_width=neck_width, knob_unit=min(dx, dy))

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
    return PuzzleResult(
        pieces, width_mm, height_mm, x_offset, y_offset,
        outline=_outline_rect(x_offset, y_offset, x_offset + width_mm, y_offset + height_mm),
        edges=_unique_edges(H_edges, V_edges),
    )


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
    return PuzzleResult(
        pieces, width_mm, height_mm, x_offset, y_offset,
        outline=_outline_rect(x_offset, y_offset, x_offset + width_mm, y_offset + height_mm),
        edges=_unique_edges(H_edges, V_edges),
    )
