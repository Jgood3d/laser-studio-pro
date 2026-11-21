"""Matrice de test : une grille de carrés gravés (vitesse x puissance) ou
découpés (vitesse x nombre de passes), avec leurs étiquettes, pour trouver
les bons réglages d'un matériau."""
import math

import numpy as np

from laser_studio.gcode.common import GcodeResult, matrix_duration_text, overscan_distance, scan_offset_mm
from laser_studio.image.matrix import tile_raster_gcode
from laser_studio.vector.font import VectorFont

# Mode de la matrice de test (params['mode']) : codes indépendants de la langue.
MATRIX_ENGRAVE, MATRIX_CUT = "engrave", "cut"


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
        overscan_dist = overscan_distance(params, cell_w)
    else:
        overscan_dist = 0.0

    speeds = np.linspace(min_s, max_s, steps_s)

    total_time_sec = 0.0
    power_samples = []

    offset_labels_x = 22.0
    offset_labels_y = 14.0

    mat_off_x = params.get('matrix_offset_x', 0.0)
    mat_off_y = params.get('matrix_offset_y', 0.0)

    start_x = mat_off_x + offset_labels_x
    start_y = mat_off_y + offset_labels_y

    text_p_val = int((40.0 / 100.0) * s_max)

    if mode == MATRIX_ENGRAVE:
        min_p, max_p, steps_p = params['min_power'], params['max_power'], params['steps_power']
        lmm = params.get('lines_mm', 5.0)
        powers = np.linspace(min_p, max_p, steps_p)

        for j, p in enumerate(powers):
            lbl_x = start_x + j * (cell_w + gap) + (cell_w / 2.0) - 4.0
            lbl_y = start_y - 8.0
            p_text = f"{_round_half_up(p)}%"
            gcode.extend(VectorFont.generate_text_gcode(
                text=p_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_w = (steps_p * cell_w) + ((steps_p - 1) * gap)
        title_pow_x = start_x + (matrix_total_w / 2.0) - 25.0
        title_pow_y = start_y - offset_labels_y
        gcode.extend(VectorFont.generate_text_gcode(
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
            gcode.extend(VectorFont.generate_text_gcode(
                text=s_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_h = (steps_s * cell_h) + ((steps_s - 1) * gap)
        title_spd_x = max(0.0, mat_off_x)
        title_spd_y = start_y + (matrix_total_h / 2.0) + 18.0
        gcode.extend(VectorFont.generate_text_gcode(
            text="VITESSE", start_x=title_spd_x, start_y=title_spd_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3", vertical=True
        ))

        for i, s in enumerate(speeds):
            for j, p in enumerate(powers):
                x0 = start_x + j * (cell_w + gap)
                y0 = start_y + i * (cell_h + gap)

                p_val = int((p / 100.0) * s_max)
                power_samples.append(p)

                gcode.append(f"\n; --- Carré Speed={int(s)} mm/min | Power={p:.1f}% (Gravure) ---")

                if tile is not None:
                    # Test à partir d'une image : la zone tramée remplace le carré plein.
                    tile_lines, tile_sec, _tile_samples = tile_raster_gcode(
                        tile['arr'], x0, y0, cell_w, cell_h, s, p, s_max, laser_cmd,
                        overscan_dist=overscan_dist, grayscale=bool(tile.get('grayscale')),
                        scan_offset=scan_offset_mm(params))
                    gcode.extend(tile_lines)
                    total_time_sec += tile_sec
                    continue

                lines = max(1, int(cell_h * lmm))
                step_y = cell_h / lines

                for l in range(lines):
                    ly = y0 + l * step_y

                    if l % 2 == 0:
                        margin_start_x = x0 - overscan_dist
                        margin_end_x = x0 + cell_w + overscan_dist

                        if overscan_dist > 0:
                            gcode.append(f"G0 X{margin_start_x:.3f} Y{ly:.3f} ; OVERSCAN_START")
                            gcode.append(f"{laser_cmd} S0")
                            gcode.append(f"G1 X{x0:.3f} F{int(s)} S0")
                        else:
                            gcode.append(f"G0 X{x0:.3f} Y{ly:.3f}")
                            gcode.append(f"{laser_cmd} S0")

                        gcode.append(f"G1 X{x0 + cell_w:.3f} F{int(s)} S{p_val}")

                        if overscan_dist > 0:
                            gcode.append(f"G1 X{margin_end_x:.3f} F{int(s)} S0 ; OVERSCAN_END")
                    else:
                        margin_start_x = x0 + cell_w + overscan_dist
                        margin_end_x = x0 - overscan_dist

                        if overscan_dist > 0:
                            gcode.append(f"G0 X{margin_start_x:.3f} Y{ly:.3f} ; OVERSCAN_START")
                            gcode.append(f"{laser_cmd} S0")
                            gcode.append(f"G1 X{x0 + cell_w:.3f} F{int(s)} S0")
                        else:
                            gcode.append(f"G0 X{x0 + cell_w:.3f} Y{ly:.3f}")
                            gcode.append(f"{laser_cmd} S0")

                        gcode.append(f"G1 X{x0:.3f} F{int(s)} S{p_val}")

                        if overscan_dist > 0:
                            gcode.append(f"G1 X{margin_end_x:.3f} F{int(s)} S0 ; OVERSCAN_END")

                    gcode.append("M5")
                    total_time_sec += ((cell_w + (2 * overscan_dist)) / max(s, 1)) * 60.0
    else:
        single_p = params['single_power']
        min_passes = params['min_passes']
        max_passes = params['max_passes']
        steps_passes = params['steps_passes']

        passes_arr = np.unique(np.round(np.linspace(min_passes, max_passes, steps_passes))).astype(int)
        num_cols = len(passes_arr)
        num_rows = len(speeds)

        p_val = int((single_p / 100.0) * s_max)
        power_samples.append(single_p)

        for j, pass_val in enumerate(passes_arr):
            lbl_x = start_x + j * (sq_size + gap) + (sq_size / 2.0) - 4.0
            lbl_y = start_y - 8.0
            pass_text = f"{pass_val}p"
            gcode.extend(VectorFont.generate_text_gcode(
                text=pass_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_w = (num_cols * sq_size) + ((num_cols - 1) * gap)
        title_pass_x = start_x + (matrix_total_w / 2.0) - 30.0
        title_pass_y = start_y - offset_labels_y
        gcode.extend(VectorFont.generate_text_gcode(
            text="NOMBRE DE PASSES", start_x=title_pass_x, start_y=title_pass_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
        ))

        for i, s in enumerate(speeds):
            label_zone_x = max(0.0, mat_off_x)
            lbl_x = label_zone_x + 5.0
            lbl_y = start_y + i * (sq_size + gap) + (sq_size / 3.0)
            s_text = f"{_round_half_up(s)}"
            gcode.extend(VectorFont.generate_text_gcode(
                text=s_text, start_x=lbl_x, start_y=lbl_y, 
                char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

        matrix_total_h = (num_rows * sq_size) + ((num_rows - 1) * gap)
        title_spd_x = max(0.0, mat_off_x)
        title_spd_y = start_y + (matrix_total_h / 2.0) + 18.0
        gcode.extend(VectorFont.generate_text_gcode(
            text="VITESSE", start_x=title_spd_x, start_y=title_spd_y, 
            char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3", vertical=True
        ))

        for i, s in enumerate(speeds):
            for j, pass_val in enumerate(passes_arr):
                x0 = start_x + j * (sq_size + gap)
                y0 = start_y + i * (sq_size + gap)

                gcode.append(f"\n; --- Carré Speed={int(s)} mm/min | Passes={pass_val} | Power={single_p}% (Découpe) ---")
                for pass_num in range(pass_val):
                    gcode.append(f"; Passe {pass_num + 1}/{pass_val}")
                    gcode.append(f"G0 X{x0:.3f} Y{y0:.3f}")
                    gcode.append(f"F{int(s)}")
                    gcode.append(f"{laser_cmd} S{p_val}")
                    gcode.append(f"G1 X{x0 + sq_size:.3f}")
                    gcode.append(f"G1 Y{y0 + sq_size:.3f}")
                    gcode.append(f"G1 X{x0:.3f}")
                    gcode.append(f"G1 Y{y0:.3f}")
                    gcode.append("M5")
                    total_time_sec += ((sq_size * 4) / max(s, 1)) * 60.0

    gcode.append("\nM5\nG0 X0 Y0\n; FIN MATRICE DE TEST")

    avg_p = float(np.mean(power_samples)) if power_samples else 0.0
    return GcodeResult("\n".join(gcode), len(gcode), avg_p, matrix_duration_text(total_time_sec))
