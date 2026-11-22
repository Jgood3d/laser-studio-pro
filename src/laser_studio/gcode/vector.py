"""G-Code des calques vectoriels (textes, formes, SVG/DXF importés) : gravure
remplie par balayage de lignes, découpe et marquage des contours (phase 3
d'un job).

Les données d'entrée sont déjà purement numériques (polygones en mm, réglages
des calques en dictionnaires) : voir vector_layers.extract_vector_layer_data,
qui les prépare dans le thread de l'interface."""
import math

from laser_studio.models.layer_modes import (
    MODE_CUT as CUT_MODE, MODE_FILL as ENGRAVE_MODE, layer_laser_cmd, layer_overscan_enabled,
)
from laser_studio.vector.order import order_layers_for_cutting, order_polygons_inner_first

# Écart (mm) sous lequel un tracé dont le dernier point n'est pas exactement le premier est tout de même
# considéré comme fermé (arrondis). Au-delà, c'est un vrai tracé ouvert, parcouru une seule fois.
CLOSE_GAP_MM = 0.01


def _scanline_fill_union(groups, y):
    """Segments remplis à la hauteur y : règle pair-impair à l'intérieur de chaque objet (trous), puis UNION
    des objets. Avant, tous les contours du calque étaient mélangés dans une seule règle pair-impair : deux
    objets qui se chevauchent (traits qui se croisent, lettres rapprochées) s'annulaient là où ils se
    recouvrent et laissaient un vide non gravé."""
    segments = []
    for group in groups:
        segments.extend(_scanline_fill_segments(group, y))
    if len(segments) < 2:
        return segments
    segments.sort()
    merged = [list(segments[0])]
    for a, b in segments[1:]:
        if a <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def _scanline_fill_segments(polygons, y):
    """Algorithme de balayage (pair-impair) : renvoie les segments [x_debut, x_fin]
    remplis par la ligne horizontale y, toutes contours confondus (gère les trous,
    ex. l'intérieur des lettres 'o', 'a', 'e'...)."""
    xs = []
    for poly in polygons:
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if y1 == y2:
                continue
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
    xs.sort()
    segments = []
    for i in range(0, len(xs) - 1, 2):
        if xs[i + 1] - xs[i] > 1e-6:
            segments.append((xs[i], xs[i + 1]))
    return segments


def _overscan_runs(segments, overscan):
    """Regroupe les segments d'une ligne (déjà dans le sens du balayage) qui seront gravés d'une seule passe.

    Deux segments voisins vont dans le même groupe quand l'écart qui les sépare ne dépasse pas deux fois le
    surbalayage : avec un surbalayage par segment, la sortie de l'un dépasserait l'entrée du suivant et la
    tête ferait demi-tour. Au-delà, chaque groupe garde son surbalayage et la tête saute en G0 vers le
    suivant, toujours vers l'avant. Sans surbalayage, chaque segment est seul dans son groupe."""
    runs = []
    for seg in segments:
        if runs and overscan > 0:
            prev_sx, prev_ex = runs[-1][-1]
            direction = 1.0 if prev_ex >= prev_sx else -1.0
            if (seg[0] - prev_ex) * direction <= 2.0 * overscan:
                runs[-1].append(seg)
                continue
        runs.append([seg])
    return runs


def build_vector_layers_gcode(layers_data, base_offset_x, base_offset_y, h_mm,
                               laser_cmd, s_max, overscan_dist=0.0, safe_cut_order=False, scan_offset=0.0):
    """Construit le G-Code (Phase "Calques Vectoriels") pour tous les calques actifs,
    à partir des données géométriques déjà extraites (voir extract_vector_layer_data).
    Les coordonnées des objets vectoriels sont déjà exprimées dans le repère
    machine (origine bas-gauche, Y croissant vers le haut) via
    VectorObject.world_transform : aucune inversion supplémentaire n'est
    nécessaire ici (contrairement à la gravure image / découpe SVG importée,
    qui restent en haut-gauche/Y descendant).

    overscan_dist (mm) : distance de surbalayage appliquée aux lignes de
    remplissage (mode ENGRAVE_MODE, gravure remplie), comme pour la gravure image —
    le laser reste éteint pendant le dépassement de part et d'autre.

    safe_cut_order : graver avant de découper (les calques de découpe passent après les autres) et, dans
    un calque de découpe, couper les contours intérieurs avant ceux qui les contiennent (voir
    vector_order) : une pièce ne bouge plus avant que ses détails soient faits.

    scan_offset : décalage (mm) des lignes de remplissage parcourues en sens retour, pour compenser le jeu
    mécanique et le délai d'allumage du laser (même réglage que pour les images ; sinon les contours des
    remplissages sont en escalier et les petits traits se cassent)."""
    gcode = []
    total_time_seconds = 0.0
    power_samples = []

    def to_gcode_xy(x_mm, y_mm):
        return base_offset_x + x_mm, base_offset_y + y_mm

    items = list(layers_data.items())
    if safe_cut_order:
        items = order_layers_for_cutting(items)
    for layer_id, data in items:
        layer = data["layer"]
        polygons = data["polygons"]
        if not polygons:
            continue
        if safe_cut_order and layer["mode"] == CUT_MODE:
            polygons = order_polygons_inner_first(polygons)

        gcode.append(f"; --- CALQUE '{layer['name']}' [{layer['mode']}] ---")
        if safe_cut_order and layer["mode"] == CUT_MODE:
            gcode.append("; Ordre de découpe : intérieur avant extérieur")
        speed = layer["speed"]
        power_val = int(round((layer["power"] / 100.0) * s_max))
        gcode.append(f"F{speed}")
        # Commande laser et surbalayage de CE calque (réglages globaux si le calque n'a pas les siens).
        cmd = layer_laser_cmd(layer, laser_cmd)
        layer_overscan = overscan_dist if layer_overscan_enabled(layer, True) else 0.0

        if layer["mode"] == ENGRAVE_MODE:
            ys = [p[1] for poly in polygons for p in poly]
            if not ys:
                continue
            y_min, y_max = min(ys), max(ys)
            step = max(layer["line_interval"], 0.02)
            y = y_min
            line_idx = 0
            groups = data.get("polygon_groups") or [polygons]
            while y <= y_max:
                segments = _scanline_fill_union(groups, y)
                if segments:
                    ordered = segments if line_idx % 2 == 0 else list(reversed(
                        [(b + scan_offset, a + scan_offset) for a, b in segments]))
                    for run in _overscan_runs(ordered, layer_overscan):
                        if layer_overscan > 0:
                            # Une seule passe pour tout le groupe : surbalayage avant le premier segment et
                            # après le dernier ; entre deux segments, la tête continue dans le même sens,
                            # laser à 0 (comme la gravure d'image). Avant, chaque segment avait son propre
                            # surbalayage : entre deux lettres proches, la tête dépassait la lettre puis
                            # revenait en arrière pour reprendre l'élan avant la suivante.
                            first_sx, last_ex = run[0][0], run[-1][1]
                            direction = 1.0 if run[0][1] >= first_sx else -1.0
                            pre_x, pre_y = to_gcode_xy(first_sx - direction * layer_overscan, y)
                            post_x, post_y = to_gcode_xy(last_ex + direction * layer_overscan, y)

                            # Déplacement avant balayage avec laser éteint.
                            gcode.append(f"G0 X{pre_x:.3f} Y{pre_y:.3f}")
                            for k, (sx_mm, ex_mm) in enumerate(run):
                                real_sx, real_sy = to_gcode_xy(sx_mm, y)
                                real_ex, real_ey = to_gcode_xy(ex_mm, y)
                                # Approche (surbalayage, ou écart depuis le segment précédent) laser éteint.
                                gcode.append(f"{cmd} S0")
                                gcode.append(f"G1 X{real_sx:.3f} Y{real_sy:.3f} F{speed}")
                                # Gravure du segment réel.
                                gcode.append(f"{cmd} S{power_val}")
                                gcode.append(f"G1 X{real_ex:.3f} Y{real_ey:.3f} F{speed}")
                                power_samples.append(layer["power"])

                            # Sortie de balayage avec laser éteint.
                            gcode.append(f"{cmd} S0")
                            gcode.append(f"G1 X{post_x:.3f} Y{post_y:.3f} F{speed}")

                            total_time_seconds += (abs(post_x - pre_x) / max(speed, 1)) * 60.0
                        else:
                            sx_mm, ex_mm = run[0]
                            real_sx, real_sy = to_gcode_xy(sx_mm, y)
                            real_ex, real_ey = to_gcode_xy(ex_mm, y)
                            gcode.append(f"G0 X{real_sx:.3f} Y{real_sy:.3f}")
                            gcode.append(f"{cmd} S{power_val}")
                            gcode.append(f"G1 X{real_ex:.3f} Y{real_ey:.3f} F{speed}")

                            total_time_seconds += (abs(real_ex - real_sx) / max(speed, 1)) * 60.0

                            # Prépare le prochain déplacement avec le laser
                            # éteint, sans arrêter complètement le mode M4.
                            gcode.append(f"{cmd} S0")
                            power_samples.append(layer["power"])
                y += step
                line_idx += 1
        else:
            # Découpe ou Marquage : contour(s) uniquement
            # Garde-fou : passes <= 0 (ancien matériau pass_c=0, profil mal
            # migré…) produisait un calque « vide » alors que la géométrie
            # était bien présente. On force au moins 1 passe.
            n_passes = max(1, int(layer.get("passes") or 1))
            for pass_num in range(n_passes):
                if n_passes > 1:
                    gcode.append(f"; Passe {pass_num + 1}/{n_passes}")
                for poly in polygons:
                    if len(poly) < 2:
                        continue
                    sx, sy = to_gcode_xy(*poly[0])
                    gcode.append(f"G0 X{sx:.3f} Y{sy:.3f}")
                    gcode.append(f"{cmd} S{power_val}")
                    cx, cy = sx, sy
                    # Un tracé ouvert (ligne, fente, arête de puzzle) reste ouvert : le refermer faisait
                    # repasser le laser sur tout le tracé, en sens inverse. On ne ferme que les tracés
                    # quasi fermés (écart d'arrondi, moins de CLOSE_GAP_MM).
                    if poly[0] != poly[-1] and math.hypot(poly[0][0] - poly[-1][0],
                                                          poly[0][1] - poly[-1][1]) <= CLOSE_GAP_MM:
                        pts = poly + [poly[0]]
                    else:
                        pts = poly
                    for (px, py) in pts[1:]:
                        nx, ny = to_gcode_xy(px, py)
                        gcode.append(f"G1 X{nx:.3f} Y{ny:.3f}")
                        total_time_seconds += (math.hypot(nx - cx, ny - cy) / max(speed, 1)) * 60.0
                        power_samples.append(layer["power"])
                        cx, cy = nx, ny
                    gcode.append("M5")

    return gcode, total_time_seconds, power_samples
