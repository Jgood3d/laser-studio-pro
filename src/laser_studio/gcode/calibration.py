"""Motif de calibrage du décalage aller/retour (réglage « Décalage lignes
retour » de la Configuration GRBL)."""
import math

from laser_studio.core.constants import ORIGIN_CENTER
from laser_studio.gcode.common import LaserMoves, power_value
from laser_studio.gcode.timing import job_duration
from laser_studio.vector.font import VectorFont


def _text_segments(text, x, y, height_mm):
    """Traits (x1, y1, x2, y2) en mm d'un texte en police vectorielle 5x7
    (chiffres et lettres de VectorFont), le coin bas-gauche en (x, y)."""
    scale = height_mm / 7.0
    advance = (5 + 2) * scale
    segments = []
    for i, char in enumerate(str(text).upper()):
        for x1, y1, x2, y2 in VectorFont.FONT_5X7.get(char, []):
            ox = x + i * advance
            segments.append((ox + x1 * scale, y + y1 * scale, ox + x2 * scale, y + y2 * scale))
    return segments


BIDIR_TEST_DEFAULT_OFFSETS = tuple(round(-0.40 + 0.05 * i, 2) for i in range(17))   # -0,40 ... +0,40 mm


def bidir_test_gcode(params):
    """Motif de calibrage du décalage aller/retour.

    Une rangée de colonnes numérotées ; chaque colonne est une barre pleine
    gravée en lignes alternées aller (gauche -> droite) / retour (droite ->
    gauche), exactement comme une gravure d'image. Les lignes ALLER sont
    gravées sans décalage, les lignes RETOUR avec le décalage propre à la
    colonne (-0,40 ... +0,40 mm par pas de 0,05). Sur la colonne dont le
    décalage compense celui de la machine, le bord vertical de la barre est
    parfaitement droit ; sur les autres il est en dents de scie.

    params : origin_pos, offset_x, offset_y, speed_engrave, power_engrave,
    s_max, laser_cmd, homing, start_gcode, end_gcode, overscan_dist (mm, déjà
    calculée), line_pitch_mm (= 1 / lignes par mm), et en option offsets,
    rows (lignes par colonne, paire), bar_w, gap, label_h.
    Renvoie (gcode, nb_lignes, puissance_moyenne_%, durée) comme le font les
    workers de génération.
    """
    offsets = [float(o) for o in params.get("offsets", BIDIR_TEST_DEFAULT_OFFSETS)]
    rows = int(params.get("rows", 16))
    rows += rows % 2                                   # paire : autant d'aller que de retour
    bar_w = float(params.get("bar_w", 4.0))
    gap = float(params.get("gap", 2.0))
    label_h = float(params.get("label_h", 2.0))
    pitch = max(float(params.get("line_pitch_mm", 0.1)), 0.02)
    speed = max(int(params["speed_engrave"]), 1)
    power_pct = float(params["power_engrave"])
    s_max = int(params["s_max"])
    s_on = power_value(power_pct, s_max)
    laser_cmd = params["laser_cmd"]
    overscan = max(float(params.get("overscan_dist", 0.0)), 2.5)   # le laser doit être à vitesse avant la barre

    n = len(offsets)
    pitch_x = bar_w + gap
    total_w = n * pitch_x - gap
    bars_h = (rows - 1) * pitch
    label_gap = 2.0
    total_h = bars_h + label_gap + label_h
    if params.get("origin_pos") == ORIGIN_CENTER:
        base_x = params.get("offset_x", 0.0) - total_w / 2.0
        base_y = params.get("offset_y", 0.0) - total_h / 2.0
    else:
        base_x = params.get("offset_x", 0.0)
        base_y = params.get("offset_y", 0.0)

    gcode = ["; --- TEST DE DÉCALAGE ALLER/RETOUR ---",
             f"; {n} colonnes, décalages des lignes retour de {offsets[0]:+.2f} à {offsets[-1]:+.2f} mm",
             "; Grave avec la vitesse et la puissance habituelles, puis repère la colonne au bord le plus droit."]
    if params.get("homing"):
        gcode.append("$H ; Homing initial")
    start = str(params.get("start_gcode", "")).strip()
    if start:
        gcode.append("; --- G-Code de Début ---")
        gcode.append(start)
    moves = LaserMoves(gcode)
    moves.laser(laser_cmd)

    total_time = 0.0
    burn_len = 0.0

    # Numéros de colonnes (au-dessus des barres)
    label_y = base_y + bars_h + label_gap
    for i in range(n):
        text = str(i + 1)
        text_w = len(text) * (5 + 2) * (label_h / 7.0) - 2 * (label_h / 7.0)
        tx = base_x + i * pitch_x + (bar_w - text_w) / 2.0
        for x1, y1, x2, y2 in _text_segments(text, tx, label_y, label_h):
            moves.travel(x1, y1)
            moves.move(x2, y2, s_on, speed)
            seg = math.hypot(x2 - x1, y2 - y1)
            total_time += seg / speed * 60.0
            burn_len += seg

    # Lignes de barres : une passe pleine largeur par ligne, comme une vraie gravure
    for j in range(rows):
        y = base_y + (rows - 1 - j) * pitch
        ltr = (j % 2 == 0)
        if ltr:
            runs = [(base_x + i * pitch_x, base_x + i * pitch_x + bar_w) for i in range(n)]
            start_x, end_x = base_x - overscan, base_x + total_w + overscan
        else:
            runs = [(base_x + i * pitch_x + offsets[i], base_x + i * pitch_x + offsets[i] + bar_w)
                    for i in range(n)][::-1]
            start_x, end_x = base_x + total_w + overscan, base_x - overscan
        moves.travel(start_x, y)
        cursor = start_x
        for a, b in runs:
            first, second = (a, b) if ltr else (b, a)          # entrée puis sortie dans le sens du balayage
            moves.move(first, power=0, feed=speed)              # trajet à puissance nulle jusqu'à la barre
            moves.move(second, power=s_on, feed=speed)          # la barre elle-même
            total_time += (abs(first - cursor) + abs(second - first)) / speed * 60.0
            burn_len += abs(second - first)
            cursor = second
        moves.move(end_x, power=0, feed=speed)
        total_time += abs(end_x - cursor) / speed * 60.0

    end = str(params.get("end_gcode", "")).strip()
    if end:
        gcode.append("; --- G-Code de Fin ---")
        gcode.append(end)
    else:
        gcode.append("M5\nG0 X0 Y0\n; FIN DU TEST")
    avg_power = power_pct if burn_len > 0 else 0.0
    text = "\n".join(gcode)
    return text, len(text.split("\n")), avg_power, job_duration(text, params, total_time)
