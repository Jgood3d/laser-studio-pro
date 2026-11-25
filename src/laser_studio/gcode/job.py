"""G-Code d'un job complet : en-tête, gravure de l'image (phase 1), découpe
du contour SVG (phase 2), calques vectoriels (phase 3), fin de job."""
import numpy as np

from laser_studio.core.constants import ORIGIN_CENTER
from laser_studio.gcode.common import (
    GcodeResult, overscan_distance, scan_offset_mm, start_lines,
)
from laser_studio.gcode.timing import job_duration
from laser_studio.gcode.raster import image_origin, raster_image_gcode
from laser_studio.gcode.svg_cut import svg_cut_gcode
from laser_studio.gcode.vector import build_vector_layers_gcode


def build_job_gcode(processed_array, svg_path, params, vector_layers_data=None, progress=None):
    """G-Code du job.

    processed_array : image tramée à graver (tableau numpy), ou None.
    svg_path : SVG dont les tracés sont découpés autour de l'image si
    params['enable_cut'] (ou None).
    vector_layers_data : calques vectoriels (voir
    vector.layer_data.extract_vector_layer_data), ou None.
    params : réglages du job (voir JobController.build_params).
    progress : fonction appelée avec l'avancement (0 à 100), facultative.

    Renvoie un GcodeResult."""
    def report(pct):
        if progress is not None:
            progress(pct)

    gcode = ["; --- G-CODE HYBRIDE GRBL PRO ---"]
    gcode.extend(start_lines(params))

    total_power_samples = []
    total_time_seconds = 0.0
    laser_cmd = params['laser_cmd']
    # Commande laser de la gravure d'image : celle de son calque de gravure (voir
    # layer_laser_cmd), sinon la commande globale. Les calques vectoriels ont chacun la leur.
    image_cmd = params.get('image_laser_cmd', laser_cmd) if processed_array is not None else laser_cmd
    s_max = params['s_max']

    w_mm, h_mm = params['width_mm'], params['height_mm']
    if params['origin_pos'] == ORIGIN_CENTER:
        base_offset_x = params['offset_x'] - (w_mm / 2.0)
        base_offset_y = params['offset_y'] - (h_mm / 2.0)
    else:
        base_offset_x = params['offset_x']
        base_offset_y = params['offset_y']

    if processed_array is not None:
        gcode.append("; --- PHASE 1 : GRAVURE IMAGE (SURBALAYAGE ACTIF) ---")
        lines, seconds, samples = raster_image_gcode(processed_array, params, image_cmd, progress=report)
        gcode.extend(lines)
        total_time_seconds += seconds
        total_power_samples.extend(samples)

    report(70)

    if params['enable_cut'] and svg_path:
        gcode.append("; --- PHASE 2 : DÉCOUPE VECTORIELLE SVG ---")
        # Découpe du contour de l'image : avec la marge de l'image (voir image_origin).
        image_x, image_y = image_origin(params)
        lines, seconds, samples = svg_cut_gcode(svg_path, params, image_x, image_y)
        gcode.extend(lines)
        total_time_seconds += seconds
        total_power_samples.extend(samples)

    report(85)

    if vector_layers_data:
        gcode.append("; --- PHASE 3 : CALQUES VECTORIELS (TEXTE & FORMES) ---")
        if params.get('enable_overscan', False):
            vector_overscan_dist = overscan_distance(params, w_mm)
        else:
            vector_overscan_dist = 0.0
        layer_gcode, layer_time, layer_power_samples = build_vector_layers_gcode(
            vector_layers_data, base_offset_x, base_offset_y, h_mm,
            laser_cmd, s_max, overscan_dist=vector_overscan_dist,
            safe_cut_order=bool(params.get('safe_cut_order', True)),
            scan_offset=scan_offset_mm(params),
        )
        gcode.extend(layer_gcode)
        total_time_seconds += layer_time
        total_power_samples.extend(layer_power_samples)

    end_gcode = params['end_gcode'].strip()
    if end_gcode:
        gcode.append("; --- G-Code de Fin ---")
        gcode.append(end_gcode)
    else:
        if gcode[-1] != "M5":                 # chaque phase se termine déjà laser éteint
            gcode.append("M5")
        gcode.append("G0 X0 Y0\n; FIN DU TRAVAIL")

    avg_power = float(np.mean(total_power_samples)) if total_power_samples else 0.0
    text = "\n".join(gcode)
    seconds = job_duration(text, params, total_time_seconds)
    report(100)
    return GcodeResult(text, len(gcode), avg_power, seconds)
