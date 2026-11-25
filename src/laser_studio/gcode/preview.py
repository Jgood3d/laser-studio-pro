"""Aperçu 2D du G-Code, sans Qt : lecture du G-Code (traits gravés,
déplacements, surbalayage, calques), choix d'un rendu en image ou en traits,
contours de découpe, image reconstituée de la gravure et suivi de la gravure
en direct. L'onglet Visualisation 2D (ui/tabs/preview_2d) dessine le résultat.

    preview = parse_preview(gcode, layer_colors={"Découpe": "#ff3b30"})
    for group in preview.groups:
        if is_raster_group(group, matrix_engrave=False):
            ...
"""
import math
import re
from dataclasses import dataclass, field

import numpy as np

from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL, MODE_MARK, normalize_mode

# Presets matière : fond + couleur de la zone gravée.
# lightens=False : plus de puissance = plus sombre (bois, papier).
# lightens=True  : plus de puissance = plus clair (ardoise, acrylique noir).
PREVIEW_MATERIALS = {
    "light": {"material_rgb": (225, 225, 225), "burn_rgb": (25, 25, 25), "lightens": False},
    "wood": {"material_rgb": (194, 155, 105), "burn_rgb": (55, 35, 20), "lightens": False},
    "bamboo": {"material_rgb": (210, 180, 130), "burn_rgb": (70, 45, 25), "lightens": False},
    "slate": {"material_rgb": (40, 40, 45), "burn_rgb": (230, 220, 200), "lightens": True},
    "acrylic_black": {"material_rgb": (25, 25, 28), "burn_rgb": (245, 245, 245), "lightens": True},
}
PREVIEW_MATERIAL_ORDER = ("light", "wood", "bamboo", "slate", "acrylic_black")
DEFAULT_PREVIEW_MATERIAL = "light"

# Nature d'un groupe de traits gravés, d'après les commentaires du G-Code généré.
KIND_RASTER = "raster"        # « PHASE 1 : GRAVURE IMAGE »
KIND_SVG_CUT = "svg_cut"      # « PHASE 2 : DÉCOUPE VECTORIELLE SVG »
KIND_MATRIX = "matrix"        # « MATRICE DE TEST LASER »
KIND_LAYER = "layer"          # « CALQUE 'nom' [mode] »
KIND_UNKNOWN = "unknown"      # G-Code sans repère (importé d'un autre logiciel)

RASTER_COLOR = "#ffaa00"
SVG_CUT_COLOR = "#ff00ff"
DEFAULT_LAYER_COLOR = "#00ff88"
MATRIX_MODE = "matrix"

# Marge du fond de matière autour du job, en mm.
MATERIAL_BACKGROUND_MARGIN_MM = 3.0

_TOKEN_RE = re.compile(r'([A-Za-z])\s*(-?\d*\.?\d+)')
_LAYER_RE = re.compile(r"; --- CALQUE '(.+)' \[(.+)\] ---")
_NAN = float('nan')


@dataclass
class TraceGroup:
    """Traits gravés (G1 à puissance non nulle) d'une même section du G-Code.

    xs, ys : départ, arrivée, NaN pour chaque trait ; strokes : (x1, y1, x2, y2, S)."""
    kind: str
    name: str
    color: str
    mode: object
    xs: list = field(default_factory=list)
    ys: list = field(default_factory=list)
    strokes: list = field(default_factory=list)

    @property
    def key(self):
        return (self.kind, self.name, self.color)


@dataclass
class PreviewData:
    """Contenu du G-Code pour l'aperçu. Chaque liste xs / ys : départ, arrivée,
    NaN pour chaque trait."""
    rapid: tuple = field(default_factory=lambda: ([], []))       # G0
    overscan: tuple = field(default_factory=lambda: ([], []))    # lignes marquées OVERSCAN_
    travel: tuple = field(default_factory=lambda: ([], []))      # G1 à puissance nulle
    groups: list = field(default_factory=list)                  # TraceGroup, dans l'ordre d'apparition
    burn_line_idx: list = field(default_factory=list)            # ligne d'envoi de chaque trait gravé
    burn_segments: list = field(default_factory=list)            # (x1, y1, x2, y2) de chaque trait gravé


def parse_preview(gcode_text, layer_colors=None):
    """Lit le G-Code pour l'aperçu. `layer_colors` : couleur de chaque calque
    vectoriel, par nom. Une ligne mal formée est ignorée.

    Les traits gravés sont numérotés comme les envoie GCodeStreamerThread
    (lignes non vides, hors commentaires) pour le suivi de la gravure."""
    layer_colors = layer_colors or {}
    data = PreviewData()
    groups = {}
    kind, name, color, mode = KIND_UNKNOWN, None, DEFAULT_LAYER_COLOR, None
    cx, cy = 0.0, 0.0
    last_modal_g = None
    last_modal_s = None
    stream_count = 0

    for line in gcode_text.split('\n'):
        raw_line = line.strip()
        if not raw_line:
            continue
        line_idx = None
        if not line.startswith(';'):
            line_idx = stream_count
            stream_count += 1

        try:
            if raw_line.startswith(';'):
                if 'PHASE 1' in raw_line and 'GRAVURE IMAGE' in raw_line:
                    kind, name, color, mode = KIND_RASTER, None, RASTER_COLOR, MODE_FILL
                elif 'PHASE 2' in raw_line and 'DÉCOUPE VECTORIELLE SVG' in raw_line:
                    kind, name, color, mode = KIND_SVG_CUT, None, SVG_CUT_COLOR, MODE_CUT
                elif raw_line.startswith('; --- MATRICE DE TEST LASER'):
                    kind, name, color, mode = KIND_MATRIX, None, DEFAULT_LAYER_COLOR, MATRIX_MODE
                elif raw_line.startswith('; --- CALQUE'):
                    m = _LAYER_RE.match(raw_line)
                    if m:
                        # Code du mode ; ancien libellé français dans un G-Code d'avant 2.6.
                        kind, name = KIND_LAYER, m.group(1)
                        color = layer_colors.get(name, DEFAULT_LAYER_COLOR)
                        mode = normalize_mode(m.group(2))
                continue

            is_overscan = 'OVERSCAN_' in raw_line.upper()
            code_part = raw_line.split(';')[0].strip()
            if not code_part:
                continue
            tokens = _TOKEN_RE.findall(code_part)
            if not tokens:
                continue

            nx, ny, g_word, s_word, m_word = cx, cy, None, None, None
            for letter, value in tokens:
                letter = letter.upper()
                try:
                    if letter == 'G':
                        g_word = int(float(value))
                    elif letter == 'M':
                        m_word = int(float(value))
                    elif letter == 'X':
                        nx = float(value)
                    elif letter == 'Y':
                        ny = float(value)
                    elif letter == 'S':
                        s_word = float(value)
                except ValueError:
                    pass

            if g_word is not None:
                last_modal_g = g_word
            cmd_g = g_word if g_word is not None else last_modal_g

            if s_word is not None:
                last_modal_s = s_word
            elif m_word == 5:
                last_modal_s = 0.0

            if is_overscan:
                _add(data.overscan, cx, cy, nx, ny)
            elif cmd_g == 0:
                _add(data.rapid, cx, cy, nx, ny)
            elif cmd_g == 1:
                if last_modal_s is not None and last_modal_s > 0:
                    # Gravure réelle, dans la couleur de sa section.
                    key = (kind, name, color)
                    group = groups.get(key)
                    if group is None:
                        group = groups[key] = TraceGroup(kind, name, color, mode)
                        data.groups.append(group)
                    group.xs.extend([cx, nx, _NAN])
                    group.ys.extend([cy, ny, _NAN])
                    group.strokes.append((cx, cy, nx, ny, last_modal_s))
                    if line_idx is not None:
                        data.burn_line_idx.append(line_idx)
                        data.burn_segments.append((cx, cy, nx, ny))
                else:
                    # G1 à puissance nulle (laser éteint / M5) : un vrai déplacement, jamais de la
                    # gravure ; affiché comme un G0 pour ne pas se confondre avec un tracé gravé.
                    _add(data.travel, cx, cy, nx, ny)

            cx, cy = nx, ny
        except Exception:
            # Une ligne isolée mal formée ne doit jamais faire échouer tout l'aperçu.
            continue
    return data


def _add(pair, x1, y1, x2, y2):
    xs, ys = pair
    xs.extend([x1, x2, _NAN])
    ys.extend([y1, y2, _NAN])


def is_raster_group(group, matrix_engrave):
    """True si les traits du groupe sont affichés comme une image (gravure
    balayée), False s'ils restent des traits (contours).

    - image de l'application, calque en gravure remplie : image ;
    - matrice de test : image en mode gravure (`matrix_engrave`), sinon traits ;
    - découpe SVG, calques en découpe ou marquage : traits ;
    - G-Code importé sans repère : image s'il ressemble à un balayage."""
    if group.kind == KIND_RASTER:
        return True
    if group.kind == KIND_MATRIX:
        return bool(matrix_engrave)
    if group.kind == KIND_SVG_CUT:
        return False
    if group.mode in (MODE_CUT, MODE_MARK):
        return False
    if group.mode == MODE_FILL:
        return True
    if group.kind == KIND_UNKNOWN:
        strokes = group.strokes
        n_rows = len({round((y1 + y2) / 4.0, 4) for (_, y1, _, y2, _) in strokes})
        avg_segs_per_row = len(strokes) / n_rows if n_rows else 0
        return n_rows >= 2 and len(strokes) >= 40 and avg_segs_per_row >= 4.0
    # Groupe identifié mais non reconnu : traits, pour éviter une fausse image.
    return False


def is_cut_group(group):
    """True pour les traits de découpe (calque en découpe ou découpe SVG)."""
    return group.mode == MODE_CUT or group.kind == KIND_SVG_CUT


# Écart maximal (mm) entre deux tronçons de découpe qu'un pont de maintien sépare (largeur maximale d'un
# pont : models.layers.TAB_WIDTH_MAX_MM). Au-delà, les tronçons ne forment pas un même contour.
TAB_BRIDGE_MAX_MM = 10.0


def _gap(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def cut_contours(segment_lists):
    """Contours fermés des découpes, à partir de leurs segments G1 (listes
    x / y, un NaN entre deux segments) : les segments qui se suivent sont
    chaînés bout à bout. Un contour répété (découpe en plusieurs passes)
    n'est gardé qu'une fois.

    Un contour à ponts de maintien est coupé en plusieurs tronçons séparés par un petit vide : des
    tronçons consécutifs, chacun ouvert, dont le vide ne dépasse pas TAB_BRIDGE_MAX_MM sont rejoints en
    un seul contour (fermé par le dernier vide), pour que la matière de la pièce reste dessinée."""
    contours, seen = [], set()
    for xs, ys in segment_lists:
        chain = []
        for i in range(0, len(xs) - 1, 3):          # (départ, arrivée, NaN)
            start, end = (xs[i], ys[i]), (xs[i + 1], ys[i + 1])
            if chain and abs(chain[-1][0] - start[0]) < 1e-3 and abs(chain[-1][1] - start[1]) < 1e-3:
                chain.append(end)
            else:
                if len(chain) > 2:
                    contours.append(chain)
                chain = [start, end]
        if len(chain) > 2:
            contours.append(chain)

    def is_closed(chain, tolerance=0.05):
        return _gap(chain[0], chain[-1]) < tolerance

    def without_leads(chain):
        """Un contour muni d'arcs d'entrée et de sortie repasse deux fois par son point de départ (à la fin
        de l'arc d'entrée, puis au début de l'arc de sortie) : le contour fermé est ce qui les sépare."""
        seen = {}
        for index, (x, y) in enumerate(chain):
            key = (round(x, 2), round(y, 2))
            if key in seen and index - seen[key] >= 3:
                return chain[seen[key]:index + 1]
            seen.setdefault(key, index)
        return chain

    contours = [chain if is_closed(chain) else without_leads(chain) for chain in contours]

    # Rejoint les tronçons qu'un pont sépare : [contour, nombre de tronçons, départ de chaque tronçon].
    # Un tronçon qui repart d'un départ déjà vu est la passe suivante du même contour : il en commence un
    # nouveau (sinon les passes s'enchaîneraient en un seul tracé qui fait deux fois le tour).
    merged = []
    for chain in contours:
        if merged:
            current, n_runs, starts = merged[-1]
            gap = _gap(current[-1], chain[0])
            if (not is_closed(current) and not is_closed(chain) and 1e-3 < gap <= TAB_BRIDGE_MAX_MM
                    and not any(_gap(chain[0], start) < 1e-3 for start in starts)):
                merged[-1] = [current + chain, n_runs + 1, starts + [chain[0]]]
                continue
        merged.append([chain, 1, [chain[0]]])

    result = []
    for chain, n_runs, _starts in merged:
        # Un contour rejoint se ferme par le dernier vide (celui du dernier pont).
        closed = is_closed(chain) or (n_runs >= 2 and _gap(chain[0], chain[-1]) <= TAB_BRIDGE_MAX_MM)
        key = (round(min(x for x, _ in chain), 2), round(min(y for _, y in chain), 2),
               round(max(x for x, _ in chain), 2), round(max(y for _, y in chain), 2))
        if closed and key not in seen:
            seen.add(key)
            result.append(chain)
    return result


def material_background_rect(raster_stroke_lists, segment_lists, margin=MATERIAL_BACKGROUND_MARGIN_MM):
    """Rectangle (x, y, largeur, hauteur) couvrant tout le job (traits gravés
    et tracés vectoriels) plus une marge, ou None s'il n'y a rien. La marge ne
    descend pas sous 0 : un job posé à l'origine n'a pas de matière en X ou Y
    négatif (le plateau commence là)."""
    xs, ys = [], []
    for strokes in raster_stroke_lists:
        for x1, y1, x2, y2, _s in strokes:
            xs += (x1, x2)
            ys += (y1, y2)
    for seg_xs, seg_ys in segment_lists:
        xs += [v for v in seg_xs if v == v]          # NaN : séparateur de tracés
        ys += [v for v in seg_ys if v == v]
    if not xs or not ys:
        return None
    x0 = min(xs) - margin if min(xs) < 0 else max(0.0, min(xs) - margin)
    y0 = min(ys) - margin if min(ys) < 0 else max(0.0, min(ys) - margin)
    return x0, y0, max(xs) + margin - x0, max(ys) + margin - y0


def raster_image(raster_strokes, material_rgb, burn_rgb, gamma=1.0, negative=False,
                 transparent_unburned=False, flip=False):
    """Image de la gravure reconstituée à partir des traits (position +
    puissance S), façon LaserGRBL : (tableau prêt pour pyqtgraph, rectangle
    (x, y, largeur, hauteur) en mm), ou None s'il y a moins de deux lignes.

    À appeler avec les traits d'UN SEUL groupe : chaque calque a sa propre
    étendue et sa propre densité de balayage.

    Chaque ligne de balayage est placée à sa position Y RÉELLE : sinon, les
    espaces vides entre motifs (ex. les cases d'une matrice de test) seraient
    comprimés comme les lignes serrées d'un motif.

    `gamma` < 1 relève les faibles puissances (aperçu seulement) ; `negative`
    inverse zones gravées et non gravées ; `transparent_unburned` : seule la
    brûlure est peinte (la matière est dessinée dessous), son opacité suivant
    la puissance ; `flip` retourne l'image verticalement."""
    rows = {}
    for (x1, y1, x2, y2, s_val) in raster_strokes:
        y_key = round((y1 + y2) / 2.0, 4)
        rows.setdefault(y_key, []).append((min(x1, x2), max(x1, x2), s_val))

    row_ys = sorted(rows.keys())
    if len(row_ys) < 2:
        return None

    all_x = [seg[0] for segs in rows.values() for seg in segs] + \
            [seg[1] for segs in rows.values() for seg in segs]
    min_x, max_x = min(all_x), max(all_x)
    bbox_w = max(max_x - min_x, 0.01)

    min_y_data, max_y_data = row_ys[0], row_ys[-1]
    bbox_h = max(max_y_data - min_y_data, 0.01)

    target_cols = 1200
    px_per_mm_x = target_cols / bbox_w
    img_w = max(1, int(round(bbox_w * px_per_mm_x)))

    # Densité verticale calée sur l'écart RÉEL entre deux lignes de balayage
    # consécutives, pas sur la largeur : sinon certaines lignes de l'image ne
    # reçoivent aucune ligne source (bandes horizontales).
    row_gaps = [b - a for a, b in zip(row_ys[:-1], row_ys[1:]) if b - a > 0.001]
    min_row_spacing = min(row_gaps) if row_gaps else bbox_h
    px_per_mm_y_needed = 1.0 / min_row_spacing
    img_h = max(1, min(6000, int(round(bbox_h * px_per_mm_y_needed))))
    px_per_mm_y = img_h / bbox_h

    s_all = [seg[2] for segs in rows.values() for seg in segs if seg[2]]
    max_s = max(s_all) if s_all else 1.0
    if max_s <= 0:
        max_s = 1.0

    # power[ligne, colonne] : puissance normalisée (0-1), ligne 0 = Y le plus
    # petit. Les chevauchements gardent la puissance la plus forte.
    power_arr = np.zeros((img_h, img_w), dtype=np.float32)
    for y_key in row_ys:
        row_idx = int(round((y_key - min_y_data) * px_per_mm_y))
        row_idx = max(0, min(img_h - 1, row_idx))
        for (xa, xb, s_val) in rows[y_key]:
            if not s_val or s_val <= 0:
                continue
            power = min(max(s_val / max_s, 0.0), 1.0)
            col_a = max(0, min(img_w - 1, int(round((xa - min_x) * px_per_mm_x))))
            col_b = max(col_a + 1, min(img_w, int(round((xb - min_x) * px_per_mm_x)) + 1))
            np.maximum(power_arr[row_idx, col_a:col_b], power, out=power_arr[row_idx, col_a:col_b])

    if gamma != 1.0:
        power_arr = np.power(power_arr, gamma, dtype=np.float32)
    if negative:
        power_arr = 1.0 - power_arr

    material = np.array(material_rgb, dtype=np.float32)
    burn = np.array(burn_rgb, dtype=np.float32)
    if transparent_unburned and not negative:
        rgba = np.empty(power_arr.shape + (4,), dtype=np.float32)
        rgba[..., :3] = burn
        rgba[..., 3] = power_arr * 255.0
        arr = np.clip(rgba, 0, 255).astype(np.uint8)
    else:
        rgb = material + power_arr[..., None] * (burn - material)
        arr = np.clip(rgb, 0, 255).astype(np.uint8)
    pg_array = arr.transpose(1, 0, 2)
    if flip:
        pg_array = pg_array[:, ::-1]
    return pg_array, (min_x, min_y_data, bbox_w, bbox_h)


class BurnTracker:
    """Suivi de la gravure en direct : quels traits gravés du G-Code affiché
    sont déjà faits, d'après la position de la tête (rapports d'état GRBL) et
    les lignes acceptées par GRBL (« ok »).

        tracker = BurnTracker(preview.burn_line_idx, preview.burn_segments)
        tracker.lines_acked = 120
        tracker.update(x, y)
        xs, ys = tracker.points()      # traits déjà gravés, à dessiner en rouge
    """

    WINDOW = 200          # traits examinés au plus autour de la position de la tête
    ON_PATH_MM = 0.5      # distance tête / trait en dessous de laquelle la tête est « sur » le trait
    PLANNER_LEAD = 15     # mouvements que GRBL peut avoir acceptés (« ok ») sans les avoir faits

    def __init__(self, burn_line_idx=(), burn_segments=()):
        self.line_idx = np.asarray(burn_line_idx, dtype=np.int64)
        self.segments = np.asarray(burn_segments, dtype=float).reshape(-1, 4)
        n = len(self.segments)
        # Données prêtes à tracer : x1, x2, NaN pour chaque trait.
        self._xs = np.column_stack([self.segments[:, 0], self.segments[:, 2], np.full(n, np.nan)]).ravel()
        self._ys = np.column_stack([self.segments[:, 1], self.segments[:, 3], np.full(n, np.nan)]).ravel()
        self.done = 0
        self.lines_acked = 0
        self._partial = None

    def reset(self):
        """Nouveau job sur le même G-Code : plus rien n'est gravé."""
        self.done = 0
        self.lines_acked = 0
        self._partial = None

    def update(self, x, y):
        """Avance d'après la position (x, y) de la tête.

        Les « ok » disent jusqu'à quelle ligne GRBL a pu aller : la tête est sur
        un des traits acceptés et pas encore marqués gravés. On prend le plus
        proche d'elle (le premier en cas d'égalité, pour les passes
        superposées) : les traits précédents sont gravés, et celui-ci l'est
        jusqu'à la tête. Si la tête n'est sur aucun trait (déplacement à vide,
        surbalayage, position décalée par G92), on avance au moins jusqu'aux
        traits que GRBL a forcément terminés (les « ok » moins les mouvements
        qu'il peut garder en mémoire). Renvoie False s'il n'y a aucun trait."""
        segs = self.segments
        if not len(segs):
            return False
        done = self.done
        accepted = int(np.searchsorted(self.line_idx, self.lines_acked))
        partial = None
        done = max(done, accepted - self.PLANNER_LEAD)
        hi = min(accepted, done + self.WINDOW)
        if hi > done:
            window = segs[done:hi]
            ax, ay, bx, by = window[:, 0], window[:, 1], window[:, 2], window[:, 3]
            dx, dy = bx - ax, by - ay
            length2 = dx * dx + dy * dy
            t = np.where(length2 > 0, ((x - ax) * dx + (y - ay) * dy) / np.where(length2 > 0, length2, 1), 0.0)
            t = np.clip(t, 0.0, 1.0)
            px, py = ax + t * dx, ay + t * dy
            dist = np.hypot(x - px, y - py)
            best = float(dist.min())
            if best <= self.ON_PATH_MM:
                k = int(np.flatnonzero(dist <= best + 0.05)[0])
                done += k
                partial = (ax[k], ay[k], px[k], py[k])
        self.done = done
        self._partial = partial
        return True

    def finish(self, clean_finish):
        """Fin du job : tout est gravé si le job s'est terminé normalement,
        sinon le suivi reste tel quel (il montre jusqu'où la gravure est
        allée). Renvoie True si le suivi a changé."""
        if clean_finish:
            self.done = len(self.segments)
            self._partial = None
            return True
        return False

    def points(self):
        """(xs, ys) des traits déjà gravés, dont la partie du trait en cours
        jusqu'à la tête ; NaN entre deux traits."""
        n = 3 * self.done
        xs, ys = self._xs[:n], self._ys[:n]
        if self._partial is not None:
            ax, ay, px, py = self._partial
            xs = np.concatenate([xs, [ax, px, np.nan]])
            ys = np.concatenate([ys, [ay, py, np.nan]])
        return xs, ys
