"""Découpe des tracés d'un fichier SVG autour de l'image gravée (phase 2
d'un job, option « découpe » de la gravure d'image)."""
import math
from xml.dom import minidom

from svg.path import parse_path

from laser_studio.gcode.common import LaserMoves, power_value


def svg_cut_gcode(svg_path, params, image_x, image_y):
    """G-Code de découpe de chaque <path> du SVG `svg_path`, dont l'origine
    (haut-gauche, Y vers le bas) est placée sur l'image : coin bas-gauche en
    (image_x, image_y), hauteur params['height_mm']. Les courbes sont
    échantillonnées tous les 0,2 mm environ (au moins 10 points).

    Commande laser : params['cut_laser_cmd'] (M3 ou M4), M3 par défaut.

    Renvoie (lignes, durée en secondes, puissances % des tracés)."""
    gcode = []
    total_time_seconds = 0.0
    total_power_samples = []
    h_mm = params['height_mm']
    s_max = params['s_max']

    speed_cut = params['speed_cut']
    moves = LaserMoves(gcode)
    p_cut_percent = params['power_cut']
    p_cut_val = power_value(p_cut_percent, s_max)
    # Commande laser du calque de découpe (sinon celle de la Configuration GRBL), comme les calques
    # vectoriels ; M3 si les paramètres n'en disent rien (ancien comportement).
    cut_cmd = params.get('cut_laser_cmd') or "M3"
    moves.laser(cut_cmd)

    doc = minidom.parse(svg_path)
    path_strings = [path.getAttribute('d') for path in doc.getElementsByTagName('path')]
    doc.unlink()

    for pass_num in range(params['passes_cut']):
        gcode.append(f"; --- Passe Découpe {pass_num + 1}/{params['passes_cut']} ---")
        for path_str in path_strings:
            if not path_str:
                continue
            parsed = parse_path(path_str)

            start_pt = parsed.point(0)
            sx = image_x + start_pt.real
            sy = image_y + (h_mm - start_pt.imag)

            moves.travel(sx, sy)

            curr_x, curr_y = sx, sy

            try:
                path_len = parsed.length()
                num_samples = max(10, int(path_len / 0.2))
            except Exception:   # longueur incalculable (tracé dégénéré) : échantillonnage par défaut
                num_samples = 50

            for i in range(1, num_samples + 1):
                pt = parsed.point(i / num_samples)
                nx = image_x + pt.real
                ny = image_y + (h_mm - pt.imag)

                dist = math.hypot(nx - curr_x, ny - curr_y)
                total_time_seconds += (dist / max(speed_cut, 1)) * 60.0
                total_power_samples.append(p_cut_percent)
                curr_x, curr_y = nx, ny

                moves.move(nx, ny, p_cut_val, speed_cut)

    moves.off()
    return gcode, total_time_seconds, total_power_samples
