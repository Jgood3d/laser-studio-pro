"""G-Code des calques vectoriels (textes, formes, SVG/DXF importés) : gravure
remplie par balayage de lignes, découpe et marquage des contours (phase 3
d'un job).

Les données d'entrée sont déjà purement numériques (polygones en mm, réglages
des calques en dictionnaires) : voir vector.layer_data.extract_vector_layer_data,
qui les prépare dans le thread de l'interface."""
import math

from laser_studio.gcode.common import LaserMoves, power_value
from laser_studio.models.layer_modes import (
    MODE_CUT as CUT_MODE, MODE_FILL as ENGRAVE_MODE, MODE_PERF as PERF_MODE, layer_laser_cmd, layer_overscan_enabled,
)
from laser_studio.vector.kerf import compensate_kerf
from laser_studio.vector.lead import add_leads
from laser_studio.vector.order import nesting_depths, order_layers_for_cutting, order_polygons_inner_first
from laser_studio.vector.perforate import perforate
from laser_studio.vector.tabs import cut_runs, effective_count, is_closed, perimeter

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


def _layer_tabs(layer):
    """(nombre de ponts par contour, largeur en mm) du calque ; (0, 0.0) si le calque n'en a pas
    (ponts désactivés, ancien projet, valeurs inutilisables)."""
    if not layer.get("tabs", False):
        return 0, 0.0
    try:
        count = max(0, int(layer.get("tab_count") or 0))
        width = max(0.0, float(layer.get("tab_width") or 0.0))
    except (TypeError, ValueError):
        return 0, 0.0
    return (count, width) if count > 0 and width > 0 else (0, 0.0)


def _pass_power(layer, pass_num, n_passes):
    """Puissance (%) de la passe `pass_num` (0, 1, …) sur `n_passes` : celle du calque, ou, si la rampe est
    activée, une montée (ou une descente) linéaire de la puissance du calque (première passe) à la puissance
    finale `ramp_power` (dernière passe). Sans effet à une seule passe."""
    power = float(layer["power"])
    if n_passes < 2 or not layer.get("ramp", False):
        return power
    try:
        final = float(layer.get("ramp_power") or power)
    except (TypeError, ValueError):
        return power
    return power + (final - power) * pass_num / (n_passes - 1)


def _layer_perf(layer):
    """(trait, vide) en mm de la perforation d'un calque ; valeurs par défaut si le calque ne les a pas
    (ancien projet, valeur inutilisable)."""
    try:
        dash, gap = float(layer.get("perf_dash") or 2.0), float(layer.get("perf_gap") or 1.0)
    except (TypeError, ValueError):
        return 2.0, 1.0
    return (dash, gap) if dash > 0 and gap > 0 else (2.0, 1.0)


def _layer_kerf(layer):
    """Largeur de la saignée (mm) à compenser pour ce calque ; 0.0 si la compensation est désactivée
    (case décochée, ancien projet, valeur inutilisable)."""
    if not layer.get("kerf", False):
        return 0.0
    try:
        return max(0.0, float(layer.get("kerf_width") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _layer_lead(layer):
    """Rayon (mm) des arcs d'entrée et de sortie de ce calque ; 0.0 s'ils sont désactivés (case décochée,
    ancien projet, valeur inutilisable)."""
    if not layer.get("lead", False):
        return 0.0
    try:
        return max(0.0, float(layer.get("lead_radius") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _tabbed_polygons(polygons, count, width):
    """Tracés de découpe avec leurs ponts de maintien : (nouvelle liste de tracés, nombre de ponts posés,
    liste parallèle : True pour un tronçon issu d'un contour à ponts).

    Seuls les contours extérieurs fermés reçoivent des ponts : les trous (contour contenu dans un nombre
    impair d'autres contours) tombent avec leur chute, et un pont n'y retiendrait que la chute. Un contour
    trop court pour porter un pont est coupé en entier (voir vector.tabs.effective_count). Les tronçons à
    couper d'un même contour restent côte à côte, dans l'ordre d'origine des tracés : l'ordre de découpe
    (intérieur avant extérieur, plus proche voisin) n'est pas modifié."""
    depths = nesting_depths(polygons)
    result, placed, is_run = [], 0, []
    for poly, depth in zip(polygons, depths):
        if depth % 2 == 0 and is_closed(poly):
            n = effective_count(perimeter(poly), count, width)
            if n:
                runs = cut_runs(poly, count, width)
                result.extend(runs)
                is_run.extend([True] * len(runs))
                placed += n
                continue
        result.append(poly)
        is_run.append(False)
    return result, placed, is_run


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
    moves = LaserMoves(gcode)
    total_time_seconds = 0.0
    power_samples = []

    def to_gcode_xy(x_mm, y_mm):
        return base_offset_x + x_mm, base_offset_y + y_mm

    items = list(layers_data.items())
    if safe_cut_order:
        items = order_layers_for_cutting(items)
    air_on = False                      # air assist (M8) allumé par un calque précédent
    for layer_id, data in items:
        layer = data["layer"]
        polygons = data["polygons"]
        if not polygons:
            continue
        # Compensation du kerf (calque de découpe seulement) : avant l'ordre de coupe et les ponts, qui
        # travaillent sur les contours décalés.
        kerf_note = None
        kerf_width = _layer_kerf(layer) if layer["mode"] == CUT_MODE else 0.0
        if kerf_width > 0:
            polygons, n_shifted, n_skipped = compensate_kerf(polygons, kerf_width)
            kerf_note = f"; Compensation du kerf : {kerf_width:g} mm ({n_shifted} contours décalés)"
            if n_skipped:
                kerf_note += f" ; ATTENTION : {n_skipped} contour(s) trop fin(s), non compensé(s)"
        if safe_cut_order and layer["mode"] == CUT_MODE:
            polygons = order_polygons_inner_first(polygons)

        gcode.append(f"; --- CALQUE '{layer['name']}' [{layer['mode']}] ---")
        if bool(layer.get("air", False)) != air_on:
            air_on = not air_on
            gcode.append("M8 ; air assist" if air_on else "M9")
        if kerf_note:
            gcode.append(kerf_note)
        if safe_cut_order and layer["mode"] == CUT_MODE:
            gcode.append("; Ordre de découpe : intérieur avant extérieur")
        speed = layer["speed"]
        power_val = power_value(layer["power"], s_max)
        # Commande laser et surbalayage de CE calque (réglages globaux si le calque n'a pas les siens).
        cmd = layer_laser_cmd(layer, laser_cmd)
        moves.laser(cmd)
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
                            moves.travel(pre_x, pre_y)
                            for sx_mm, ex_mm in run:
                                real_sx, real_sy = to_gcode_xy(sx_mm, y)
                                real_ex, real_ey = to_gcode_xy(ex_mm, y)
                                # Approche (surbalayage, ou écart depuis le segment précédent) laser à 0,
                                # puis le segment gravé : la tête ne s'arrête pas entre les deux.
                                moves.move(real_sx, real_sy, 0, speed)
                                moves.move(real_ex, real_ey, power_val, speed)
                                power_samples.append(layer["power"])

                            # Sortie de balayage avec laser éteint.
                            moves.move(post_x, post_y, 0, speed)

                            total_time_seconds += (abs(post_x - pre_x) / max(speed, 1)) * 60.0
                        else:
                            sx_mm, ex_mm = run[0]
                            real_sx, real_sy = to_gcode_xy(sx_mm, y)
                            real_ex, real_ey = to_gcode_xy(ex_mm, y)
                            moves.travel(real_sx, real_sy)
                            moves.move(real_ex, real_ey, power_val, speed)
                            total_time_seconds += (abs(real_ex - real_sx) / max(speed, 1)) * 60.0
                            power_samples.append(layer["power"])
                y += step
                line_idx += 1
        else:
            # Découpe ou Marquage : contour(s) uniquement
            # Garde-fou : passes <= 0 (ancien matériau pass_c=0, profil mal
            # migré…) produisait un calque « vide » alors que la géométrie
            # était bien présente. On force au moins 1 passe.
            n_passes = max(1, int(layer.get("passes") or 1))
            # Ponts de maintien (calque de découpe seulement) : voir _tabbed_polygons.
            tab_count, tab_width = _layer_tabs(layer)
            is_tab_run = [False] * len(polygons)
            if layer["mode"] == CUT_MODE and tab_count > 0:
                cut_polygons, n_tabs, is_tab_run = _tabbed_polygons(polygons, tab_count, tab_width)
                if n_tabs:
                    gcode.append(f"; Ponts de maintien : {n_tabs} (largeur {tab_width:g} mm)")
            else:
                cut_polygons = polygons
            # Arcs d'entrée et de sortie (calque de découpe seulement) : sur les contours fermés qui n'ont
            # pas de ponts (un tronçon de pont démarre sur le pont même, la marque n'y gêne pas).
            lead_radius = _layer_lead(layer) if layer["mode"] == CUT_MODE else 0.0
            if lead_radius > 0:
                cut_polygons, n_led, n_no_room = add_leads(cut_polygons, polygons, lead_radius, is_tab_run)
                note = f"; Arcs d'entrée/sortie : rayon {lead_radius:g} mm ({n_led} contours)"
                if n_no_room:
                    note += f" ; ATTENTION : {n_no_room} contour(s) sans arc, faute de place"
                gcode.append(note)
            # Perforation : le tracé est coupé par traits séparés de vides.
            if layer["mode"] == PERF_MODE:
                perf_dash, perf_gap = _layer_perf(layer)
                cut_polygons, n_dashes = perforate(cut_polygons, perf_dash, perf_gap)
                gcode.append(f"; Perforation : trait {perf_dash:g} mm, vide {perf_gap:g} mm ({n_dashes} traits)")
            ramped = n_passes > 1 and bool(layer.get("ramp", False))
            for pass_num in range(n_passes):
                pass_percent = _pass_power(layer, pass_num, n_passes)
                pass_val = power_value(pass_percent, s_max)
                if ramped:
                    gcode.append(f"; Passe {pass_num + 1}/{n_passes} (puissance {pass_percent:.0f} %)")
                elif n_passes > 1:
                    gcode.append(f"; Passe {pass_num + 1}/{n_passes}")
                for poly in cut_polygons:
                    if len(poly) < 2:
                        continue
                    sx, sy = to_gcode_xy(*poly[0])
                    moves.travel(sx, sy)
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
                        moves.move(nx, ny, pass_val, speed)
                        total_time_seconds += (math.hypot(nx - cx, ny - cy) / max(speed, 1)) * 60.0
                        power_samples.append(pass_percent)
                        cx, cy = nx, ny

    moves.off()
    if air_on:
        gcode.append("M9")
    return gcode, total_time_seconds, power_samples
