"""Gravure d'une image tramée, ligne par ligne, avec surbalayage et
décalage des lignes retour (phase 1 d'un job)."""
import numpy as np

from laser_studio.core.constants import ORIGIN_CENTER
from laser_studio.gcode.common import LaserMoves

# Algorithme sans tramage : chaque pixel est gravé à une puissance
# proportionnelle à son gris (JobParams.algo).
GRAYSCALE_ALGO = "Niveaux de Gris"

def image_origin(params):
    """Coin inférieur gauche de l'image à graver sur le plateau (mm), d'après `params` (JobParams).
    Origine « Centre » : le décalage du job désigne le centre de l'image, sans marge. Sinon, décalage
    plus, en X seulement, la distance de surbalayage quand il est actif (image_overscan_distance) :
    sans cette marge, le surbalayage de la première colonne ferait partir la tête en X négatif dès que
    le décalage vaut 0.
    Les objets vectoriels reçoivent la même marge à leur import (vector/placement.py)."""
    if params.origin_pos == ORIGIN_CENTER:
        return params.vector_origin()
    return params.offset_x + image_overscan_distance(params), params.offset_y


def image_overscan_distance(params):
    """Surbalayage (mm) de la gravure d'image : réglage global et calque de gravure
    (JobParams.image_overscan_enabled) ; 0 s'il est désactivé."""
    if params.image_overscan_enabled:
        return params.overscan_for(params.width_mm)
    return 0.0


def raster_image_gcode(arr, params, progress=None):
    """G-Code de la gravure de l'image tramée `arr` (0 = brûlé, 255 = intact ;
    gris en mode « Niveaux de Gris »), à la taille params.width_mm x params.height_mm (JobParams),
    coin bas-gauche en image_origin(params).

    Commande laser : params.image_cmd ("M3" ou "M4", celle du calque de gravure), écrite une fois au
    début ; ensuite, seule la puissance S de chaque mouvement est pilotée (voir LaserMoves), et M5 à la fin.
    progress : fonction appelée avec l'avancement (0 à 70 %), facultative.

    Renvoie (lignes, durée en secondes, puissances % des tracés gravés)."""
    gcode = []
    total_time_seconds = 0.0
    total_power_samples = []

    s_max = params.s_max
    w_mm, h_mm = params.width_mm, params.height_mm
    image_x, image_y = image_origin(params)

    speed_engrave = params.speed_engrave
    moves = LaserMoves(gcode)
    moves.laser(params.image_cmd)

    h, w = arr.shape
    step_x, step_y = w_mm / w, h_mm / h
    power_engrave = params.power_engrave
    algo = params.algo
    overscan_dist = image_overscan_distance(params)

    # Décalage aller/retour (mm) : la mécanique et le délai d'allumage du
    # laser font que les lignes gravées en balayage retour (droite ->
    # gauche) tombent légèrement à côté de celles de l'aller. On décale
    # donc toute la ligne retour de cette valeur (positif = vers la
    # droite) pour que les contours verticaux se superposent.
    # Réglage propre à la machine ; se calibre avec le motif de test
    # « aller/retour » (voir gcode.calibration.bidir_test_gcode).
    scan_offset = params.scan_offset_mm

    scanned_rows = 0    # lignes réellement balayées (sens aller/retour, voir is_ltr)
    for y in range(h):
        if progress is not None and h > 0 and y % max(1, h // 50) == 0:
            # La gravure image occupe ~0-70% de la barre : c'est de très loin
            # la phase la plus longue (une ligne de gcode par transition de
            # puissance, sur potentiellement des centaines de milliers de pixels).
            progress(int((y / h) * 70))
        # Puissance de chaque pixel de la ligne, en une fois (même arrondi que power_value) : une
        # ligne vide n'est pas parcourue, et une ligne n'est balayée (avec son surbalayage) que de
        # son premier à son dernier pixel gravé.
        row_vals = arr[y, :].astype(np.float64)
        if algo == GRAYSCALE_ALGO:
            row_pct = power_engrave * (255.0 - row_vals) / 255.0
        else:
            row_pct = np.where(row_vals == 0, power_engrave, 0.0)
        row_s = np.maximum(0, np.rint((row_pct / 100.0) * s_max)).astype(np.int64)
        burned = np.flatnonzero(row_s > 0)
        if burned.size == 0:
            continue
        first_px, last_px = int(burned[0]), int(burned[-1])

        actual_y = image_y + (h - 1 - y) * step_y
        # Aller/retour alterné sur les lignes balayées (et non sur y) : deux lignes
        # séparées par des lignes vides ne partent pas du même bord.
        is_ltr = (scanned_rows % 2 == 0)
        scanned_rows += 1
        # Origine X de CETTE ligne : décalée du réglage aller/retour
        # pour les lignes retour (voir scan_offset plus haut).
        row_x0 = image_x if is_ltr else image_x + scan_offset
        seg_left = row_x0 + first_px * step_x
        seg_right = row_x0 + (last_px + 1) * step_x

        margin_start_x = seg_left - overscan_dist if is_ltr else seg_right + overscan_dist
        margin_end_x = seg_right + overscan_dist if is_ltr else seg_left - overscan_dist
        image_edge_x = seg_right if is_ltr else seg_left

        moves.travel(margin_start_x, actual_y, "OVERSCAN_START" if overscan_dist > 0 else "")
        image_start_x = seg_left if is_ltr else seg_right

        if overscan_dist > 0:
            # Traverse la zone de surbalayage à puissance nulle avant d'atteindre le premier pixel : la
            # tête y prend sa vitesse.
            moves.move(image_start_x, power=0, feed=speed_engrave)
            total_time_seconds += (abs(image_start_x - margin_start_x) / max(speed_engrave, 1)) * 60.0

        pixels = np.arange(first_px, last_px + 1) if is_ltr else np.arange(last_px, first_px - 1, -1)
        powers = row_s[pixels]
        # Seuls les pixels où la puissance change produisent une ligne de G-Code : la boucle ne passe que
        # par eux (une image de 2000 px de côté se génère plusieurs fois plus vite qu'en visitant chaque pixel).
        changes = np.flatnonzero(powers != np.concatenate(([0], powers[:-1])))

        cx = image_start_x
        last_p_val = 0

        for k in changes:
            x_pixel = int(pixels[k])
            p_val = int(powers[k])
            p_percent = float(row_pct[x_pixel])

            if p_val != last_p_val:
                # Frontière entre le pixel précédent et celui-ci, dans le sens du balayage : bord gauche du
                # pixel en balayage gauche->droite, bord droit en droite->gauche.
                boundary_x = row_x0 + (x_pixel if is_ltr else x_pixel + 1) * step_x
                # GRBL applique le S d'une ligne G1 au déplacement de CETTE ligne : le trajet jusqu'à la
                # frontière appartient au run qui se termine, donc il se fait à SA puissance (last_p_val).
                if abs(boundary_x - cx) > 1e-9:
                    moves.move(boundary_x, power=last_p_val, feed=speed_engrave)
                    total_time_seconds += (abs(boundary_x - cx) / max(speed_engrave, 1)) * 60.0
                    cx = boundary_x
                last_p_val = p_val
                if p_val > 0:
                    total_power_samples.append(p_percent)

        if cx != image_edge_x:
            moves.move(image_edge_x, power=last_p_val, feed=speed_engrave)
            total_time_seconds += (abs(image_edge_x - cx) / max(speed_engrave, 1)) * 60.0
            cx = image_edge_x

        if overscan_dist > 0:
            moves.move(margin_end_x, power=0, feed=speed_engrave, comment="OVERSCAN_END")
            total_time_seconds += (abs(margin_end_x - cx) / max(speed_engrave, 1)) * 60.0

    moves.off()
    return gcode, total_time_seconds, total_power_samples
