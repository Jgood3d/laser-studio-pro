"""Matrice de test : une grille de carrés gravés (vitesse x puissance) ou
découpés (vitesse x nombre de passes), avec leurs étiquettes, pour trouver
les bons réglages d'un matériau."""
import math

import numpy as np

from laser_studio.gcode.common import GcodeResult, LaserMoves, overscan_distance, power_value, scan_offset_mm
from laser_studio.gcode.timing import job_duration
from laser_studio.image.matrix import tile_raster_gcode
from laser_studio.vector.font import VectorFont

# Mode de la matrice de test (params['mode']) : codes indépendants de la langue.
MATRIX_ENGRAVE, MATRIX_CUT = "engrave", "cut"

# Place laissée aux étiquettes à gauche (vitesses) et en bas (puissances / passes) de la grille, en mm.
LABELS_OFFSET_X, LABELS_OFFSET_Y = 22.0, 14.0


def _round_half_up(value):
    """Arrondi arithmétique standard (.5 arrondit toujours vers le haut),
    contrairement à round() de Python qui arrondit .5 vers le nombre pair
    le plus proche (ex: round(62.5) donne 62, pas 63). Utilisé pour les
    étiquettes % puissance / vitesse de la matrice de test, afin qu'une
    valeur S625 s'affiche bien comme 63% (et S275 comme 28%)."""
    return math.floor(value + 0.5)

def build_test_matrix_gcode(params):
    """G-Code de la matrice de test.

    params : mode (MATRIX_ENGRAVE ou MATRIX_CUT), vitesses (min_speed,
    max_speed, steps_speed), puissances (min_power, max_power, steps_power)
    ou passes (single_power, min_passes, max_passes, steps_passes),
    size_square, gap, lines_mm, matrix_offset_x / _y, laser_cmd, homing,
    s_max, surbalayage (enable_overscan, overscan_mode, overscan_dist,
    overscan_pct), scan_offset_mm ; en option image_tile, cell_w, cell_h
    pour un test à partir d'une image (voir MatrixImageController.build_tile).

    Renvoie un GcodeResult."""
    mode = params.get('mode', MATRIX_ENGRAVE)
    gcode = [f"; --- MATRICE DE TEST LASER ({mode.upper()}) ---"]

    if params.get('homing', False):
        gcode.append("$H ; Homing initial")

    gcode.append("G21 ; Unités en mm")
    gcode.append("G90 ; Positionnement absolu")

    s_max = params['s_max']
    laser_cmd = params['laser_cmd']

    min_s, max_s, steps_s = params['min_speed'], params['max_speed'], params['steps_speed']
    sq_size = params['size_square']
    gap = params['gap']
    # Case de la matrice : carré de `sq_size`, ou, pour un test à partir d'une image
    # (params['image_tile']), la zone d'image gravée (largeur x hauteur en mm).
    cell_w = float(params.get('cell_w') or sq_size)
    cell_h = float(params.get('cell_h') or sq_size)
    tile = params.get('image_tile')

    enable_overscan = params.get('enable_overscan', False)
    if enable_overscan and mode == MATRIX_ENGRAVE:
        overscan_dist = overscan_distance(params.get('overscan_mode'), params.get('overscan_pct', 5.0),
                                          params.get('overscan_dist', 2.5), cell_w)
    else:
        overscan_dist = 0.0

    speeds = np.linspace(min_s, max_s, steps_s)

    total_time_sec = 0.0
    power_samples = []

    offset_labels_x = LABELS_OFFSET_X
    offset_labels_y = LABELS_OFFSET_Y

    mat_off_x = params.get('matrix_offset_x', 0.0)
    mat_off_y = params.get('matrix_offset_y', 0.0)

    start_x = mat_off_x + offset_labels_x
    start_y = mat_off_y + offset_labels_y

    text_p_val = power_value(40.0, s_max)
    moves = LaserMoves(gcode)

    if mode == MATRIX_ENGRAVE:
        min_p, max_p, steps_p = params['min_power'], params['max_power'], params['steps_power']
        lmm = params.get('lines_mm', 5.0)
        powers = np.linspace(min_p, max_p, steps_p)

        for j, p in enumerate(powers):
            lbl_x = start_x + j * (cell_w + gap) + (cell_w / 2.0) - 4.0
            lbl_y = start_y - 8.0
            p_text = f"{_round_half_up(p)}%"
            moves.extend(VectorFont.generate_text_gcode(
                text=p_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_w = (steps_p * cell_w) + ((steps_p - 1) * gap)
        title_pow_x = start_x + (matrix_total_w / 2.0) - 25.0
        title_pow_y = start_y - offset_labels_y
        moves.extend(VectorFont.generate_text_gcode(
            text="PUISSANCE (%)", start_x=title_pow_x, start_y=title_pow_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
        ))

        for i, s in enumerate(speeds):
            # La zone d'étiquettes ne descend jamais sous X=0, même avec
            # un décalage matrice négatif — et laisse la place au titre
            # "VITESSE" (tracé verticalement, ~2.3 mm de large) à sa gauche.
            label_zone_x = max(0.0, mat_off_x)
            lbl_x = label_zone_x + 5.0
            lbl_y = start_y + i * (cell_h + gap) + (cell_h / 3.0)
            s_text = f"{_round_half_up(s)}"
            moves.extend(VectorFont.generate_text_gcode(
                text=s_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_h = (steps_s * cell_h) + ((steps_s - 1) * gap)
        title_spd_x = max(0.0, mat_off_x)
        title_spd_y = start_y + (matrix_total_h / 2.0) + 18.0
        moves.extend(VectorFont.generate_text_gcode(
            text="VITESSE", start_x=title_spd_x, start_y=title_spd_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3", vertical=True
        ))

        for i, s in enumerate(speeds):
            for j, p in enumerate(powers):
                x0 = start_x + j * (cell_w + gap)
                y0 = start_y + i * (cell_h + gap)

                p_val = power_value(p, s_max)
                power_samples.append(p)

                gcode.append(f"\n; --- Carré Speed={int(s)} mm/min | Power={p:.1f}% (Gravure) ---")

                if tile is not None:
                    # Test à partir d'une image : la zone tramée remplace le carré plein.
                    tile_lines, tile_sec, _tile_samples = tile_raster_gcode(
                        tile['arr'], x0, y0, cell_w, cell_h, s, p, s_max, laser_cmd,
                        overscan_dist=overscan_dist, grayscale=bool(tile.get('grayscale')),
                        scan_offset=scan_offset_mm(params.get('scan_offset_mm')))
                    moves.extend(tile_lines)
                    total_time_sec += tile_sec
                    continue

                lines = max(1, int(cell_h * lmm))
                step_y = cell_h / lines
                moves.laser(laser_cmd)
                feed = int(s)

                for line in range(lines):
                    ly = y0 + line * step_y
                    # Aller sur les lignes paires, retour sur les impaires.
                    first, last = (x0, x0 + cell_w) if line % 2 == 0 else (x0 + cell_w, x0)
                    direction = 1.0 if line % 2 == 0 else -1.0
                    if overscan_dist > 0:
                        moves.travel(first - direction * overscan_dist, ly, "OVERSCAN_START")
                        moves.move(first, power=0, feed=feed)
                    else:
                        moves.travel(first, ly)
                    moves.move(last, power=p_val, feed=feed)
                    if overscan_dist > 0:
                        moves.move(last + direction * overscan_dist, power=0, feed=feed, comment="OVERSCAN_END")
                    total_time_sec += ((cell_w + (2 * overscan_dist)) / max(s, 1)) * 60.0
    else:
        single_p = params['single_power']
        min_passes = params['min_passes']
        max_passes = params['max_passes']
        steps_passes = params['steps_passes']

        passes_arr = np.unique(np.round(np.linspace(min_passes, max_passes, steps_passes))).astype(int)
        num_cols = len(passes_arr)
        num_rows = len(speeds)

        p_val = power_value(single_p, s_max)
        power_samples.append(single_p)

        for j, pass_val in enumerate(passes_arr):
            lbl_x = start_x + j * (sq_size + gap) + (sq_size / 2.0) - 4.0
            lbl_y = start_y - 8.0
            pass_text = f"{pass_val}p"
            moves.extend(VectorFont.generate_text_gcode(
                text=pass_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_w = (num_cols * sq_size) + ((num_cols - 1) * gap)
        title_pass_x = start_x + (matrix_total_w / 2.0) - 30.0
        title_pass_y = start_y - offset_labels_y
        moves.extend(VectorFont.generate_text_gcode(
            text="NOMBRE DE PASSES", start_x=title_pass_x, start_y=title_pass_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
        ))

        for i, s in enumerate(speeds):
            label_zone_x = max(0.0, mat_off_x)
            lbl_x = label_zone_x + 5.0
            lbl_y = start_y + i * (sq_size + gap) + (sq_size / 3.0)
            s_text = f"{_round_half_up(s)}"
            moves.extend(VectorFont.generate_text_gcode(
                text=s_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_h = (num_rows * sq_size) + ((num_rows - 1) * gap)
        title_spd_x = max(0.0, mat_off_x)
        title_spd_y = start_y + (matrix_total_h / 2.0) + 18.0
        moves.extend(VectorFont.generate_text_gcode(
            text="VITESSE", start_x=title_spd_x, start_y=title_spd_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3", vertical=True
        ))

        for i, s in enumerate(speeds):
            for j, pass_val in enumerate(passes_arr):
                x0 = start_x + j * (sq_size + gap)
                y0 = start_y + i * (sq_size + gap)

                gcode.append(f"\n; --- Carré Speed={int(s)} mm/min | Passes={pass_val} | Power={single_p}% (Découpe) ---")
                moves.laser(laser_cmd)
                for pass_num in range(pass_val):
                    gcode.append(f"; Passe {pass_num + 1}/{pass_val}")
                    moves.travel(x0, y0)
                    for cx, cy in ((x0 + sq_size, y0), (x0 + sq_size, y0 + sq_size), (x0, y0 + sq_size), (x0, y0)):
                        moves.move(cx, cy, p_val, int(s))
                    total_time_sec += ((sq_size * 4) / max(s, 1)) * 60.0

    moves.off()
    gcode.append("G0 X0 Y0\n; FIN MATRICE DE TEST")

    avg_p = float(np.mean(power_samples)) if power_samples else 0.0
    text = "\n".join(gcode)
    return GcodeResult(text, len(gcode), avg_p, job_duration(text, params.get('machine_limits'), total_time_sec))


def matrix_cell_at(params, x_mm, y_mm):
    """Case de la matrice `params` (ceux de build_test_matrix_gcode) au point
    (x_mm, y_mm) du plateau : (vitesse mm/min, puissance %) en gravure,
    (vitesse mm/min, passes) en découpe, valeurs arrondies. None hors des
    cases (marges, étiquettes, espace entre deux cases)."""
    start_x = params.get('matrix_offset_x', 0.0) + LABELS_OFFSET_X
    start_y = params.get('matrix_offset_y', 0.0) + LABELS_OFFSET_Y
    # Case : carré, ou zone d'image (largeur x hauteur) pour un test à partir d'une image.
    cell_w = float(params.get('cell_w') or params['size_square'])
    cell_h = float(params.get('cell_h') or params['size_square'])
    gap = params['gap']

    speeds = np.linspace(params['min_speed'], params['max_speed'], int(params['steps_speed']))
    mode = params.get('mode', MATRIX_ENGRAVE)
    if mode == MATRIX_ENGRAVE:
        col_values = np.linspace(params['min_power'], params['max_power'], int(params['steps_power']))
    else:
        col_values = np.unique(np.round(np.linspace(
            params['min_passes'], params['max_passes'], int(params['steps_passes'])))).astype(int)

    col = int((x_mm - start_x) // (cell_w + gap))
    row = int((y_mm - start_y) // (cell_h + gap))
    if not (0 <= col < len(col_values) and 0 <= row < len(speeds)):
        return None
    cell_x0 = start_x + col * (cell_w + gap)
    cell_y0 = start_y + row * (cell_h + gap)
    if not (cell_x0 <= x_mm <= cell_x0 + cell_w and cell_y0 <= y_mm <= cell_y0 + cell_h):
        return None  # clic dans l'espace entre les cases, pas dans une case

    speed = round(float(speeds[row]))
    if mode == MATRIX_ENGRAVE:
        return speed, round(float(col_values[col]))
    return speed, int(col_values[col])
