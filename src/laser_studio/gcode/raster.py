"""Gravure d'une image tramée, ligne par ligne, avec surbalayage et
décalage des lignes retour (phase 1 d'un job)."""
import numpy as np

from laser_studio.core.constants import ORIGIN_CENTER
from laser_studio.gcode.common import overscan_distance, scan_offset_mm

# Algorithme sans tramage : chaque pixel est gravé à une puissance
# proportionnelle à son gris (params['algo']).
GRAYSCALE_ALGO = "Niveaux de Gris"

# Marge de l'image à graver par rapport à l'origine du job (mm), comme à l'import d'un SVG/DXF
# (vector_layers.extract_svg_objects) : sans elle, le surbalayage de la première colonne ferait
# partir la tête en X négatif dès que le décalage du job vaut 0.
IMAGE_MARGIN_MM = 10.0


def image_origin(params):
    """Coin inférieur gauche de l'image à graver sur le plateau (mm). Origine « Centre » : le
    décalage du job désigne le centre de l'image, sans marge ; sinon, décalage + IMAGE_MARGIN_MM.
    Les calques vectoriels ne sont pas concernés : leurs objets ont déjà leur marge à l'import."""
    if params['origin_pos'] == ORIGIN_CENTER:
        return (params['offset_x'] - params['width_mm'] / 2.0,
                params['offset_y'] - params['height_mm'] / 2.0)
    return params['offset_x'] + IMAGE_MARGIN_MM, params['offset_y'] + IMAGE_MARGIN_MM


def image_overscan_distance(params):
    """Surbalayage (mm) de la gravure d'image : réglage global ET calque de
    gravure (params['image_overscan'], voir layer_overscan_enabled)."""
    if params.get('image_overscan', params['enable_overscan']):
        return overscan_distance(params, params['width_mm'], default_dist=params['overscan_dist'])
    return 0.0


def raster_image_gcode(arr, params, image_cmd, progress=None):
    """G-Code de la gravure de l'image tramée `arr` (0 = brûlé, 255 = intact ;
    gris en mode « Niveaux de Gris »), à la taille params['width_mm'] x
    params['height_mm'], coin bas-gauche en image_origin(params).

    image_cmd : "M3" (renvoyé à chaque ligne) ou "M4" (activé une fois en tête
    de job par l'appelant ; ici, seule la puissance S est pilotée).
    progress : fonction appelée avec l'avancement (0 à 70 %), facultative.

    Renvoie (lignes, durée en secondes, puissances % des tracés gravés)."""
    gcode = []
    total_time_seconds = 0.0
    total_power_samples = []

    s_max = params['s_max']
    w_mm, h_mm = params['width_mm'], params['height_mm']
    image_x, image_y = image_origin(params)

    speed_engrave = params['speed_engrave']
    gcode.append(f"F{speed_engrave}")

    h, w = arr.shape
    step_x, step_y = w_mm / w, h_mm / h
    power_engrave = params['power_engrave']
    algo = params.get('algo', '')
    overscan_dist = image_overscan_distance(params)

    # Décalage aller/retour (mm) : la mécanique et le délai d'allumage du
    # laser font que les lignes gravées en balayage retour (droite ->
    # gauche) tombent légèrement à côté de celles de l'aller. On décale
    # donc toute la ligne retour de cette valeur (positif = vers la
    # droite) pour que les contours verticaux se superposent.
    # Réglage propre à la machine ; se calibre avec le motif de test
    # « aller/retour » (voir gcode.calibration.bidir_test_gcode).
    scan_offset = scan_offset_mm(params)

    def pixel_power_percent(val):
        if algo == GRAYSCALE_ALGO:
            return power_engrave * (255.0 - float(val)) / 255.0
        return power_engrave if val == 0 else 0.0

    scanned_rows = 0    # lignes réellement balayées (sens aller/retour, voir is_ltr)
    for y in range(h):
        if progress is not None and h > 0 and y % max(1, h // 50) == 0:
            # La gravure image occupe ~0-70% de la barre : c'est de très loin
            # la phase la plus longue (une ligne de gcode par transition de
            # puissance, sur potentiellement des centaines de milliers de pixels).
            progress(int((y / h) * 70))
        # Pixels à graver de la ligne (même calcul de puissance que la boucle plus bas, en
        # une fois) : une ligne vide n'est pas parcourue, et une ligne n'est balayée (avec
        # son surbalayage) que de son premier à son dernier pixel gravé.
        row_vals = arr[y, :].astype(np.float64)
        if algo == GRAYSCALE_ALGO:
            row_pct = power_engrave * (255.0 - row_vals) / 255.0
        else:
            row_pct = np.where(row_vals == 0, power_engrave, 0.0)
        burned = np.flatnonzero(np.rint((row_pct / 100.0) * s_max) > 0)
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

        if overscan_dist > 0:
            gcode.append(f"G0 X{margin_start_x:.3f} Y{actual_y:.3f} ; OVERSCAN_START")
        else:
            gcode.append(f"G0 X{margin_start_x:.3f} Y{actual_y:.3f}")

        if image_cmd == "M3":
            gcode.append(f"{image_cmd} S0")
        else:
            # Mode M4 déjà activé une fois en tête de job : ici on ne fait
            # plus que remettre la puissance à 0 avant d'attaquer la ligne,
            # sans renvoyer M4.
            gcode.append("S0")

        image_start_x = seg_left if is_ltr else seg_right

        if overscan_dist > 0:
            # Traverse la zone de surbalayage à puissance nulle avant
            # d'atteindre le premier pixel de l'image : sans cette
            # ligne, la première commande G1 du tramage (ci-dessous)
            # parcourait toute la distance (surbalayage + image)
            # directement à la puissance du premier pixel gravé.
            gcode.append(f"G1 X{image_start_x:.3f} F{speed_engrave} S0")
            total_time_seconds += (abs(image_start_x - margin_start_x) / max(speed_engrave, 1)) * 60.0

        pixels = range(first_px, last_px + 1) if is_ltr else range(last_px, first_px - 1, -1)

        cx = image_start_x
        last_p_val = 0

        for x_pixel in pixels:
            val = arr[y, x_pixel]

            p_percent = pixel_power_percent(val)
            p_val = int(round((p_percent / 100.0) * s_max))

            if p_val != last_p_val:
                # Frontière entre le pixel précédent et celui-ci, dans
                # le sens du balayage : bord gauche du pixel en
                # balayage gauche->droite, bord droit en droite->gauche.
                boundary_x = row_x0 + (x_pixel if is_ltr else x_pixel + 1) * step_x
                # GRBL applique le S d'une ligne G1 au déplacement de
                # CETTE ligne : le trajet jusqu'à la frontière
                # appartient au run qui se termine, donc on l'effectue
                # à SA puissance (last_p_val), pas à celle du run
                # suivant.
                if abs(boundary_x - cx) > 1e-9:
                    gcode.append(f"G1 X{boundary_x:.3f} F{speed_engrave} S{last_p_val}")
                    total_time_seconds += (abs(boundary_x - cx) / max(speed_engrave, 1)) * 60.0
                    cx = boundary_x
                last_p_val = p_val
                if p_val > 0:
                    total_power_samples.append(p_percent)

        if cx != image_edge_x:
            gcode.append(f"G1 X{image_edge_x:.3f} F{speed_engrave} S{last_p_val}")
            total_time_seconds += (abs(image_edge_x - cx) / max(speed_engrave, 1)) * 60.0
            cx = image_edge_x

        if overscan_dist > 0:
            gcode.append(f"G1 X{margin_end_x:.3f} F{speed_engrave} S0 ; OVERSCAN_END")
            total_time_seconds += (abs(margin_end_x - cx) / max(speed_engrave, 1)) * 60.0

        if image_cmd == "M3":
            gcode.append("M5")
        elif overscan_dist == 0 and last_p_val != 0:
            # Sécurité : sans surbalayage pour s'en charger, on
            # s'assure que la puissance est bien à 0 avant le
            # déplacement rapide (G0) vers la ligne suivante.
            gcode.append("S0")

    return gcode, total_time_seconds, total_power_samples
