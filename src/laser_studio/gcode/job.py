"""G-Code d'un job complet : en-tête, gravure de l'image (phase 1), calques
vectoriels (phase 3), fin de job. La phase 2 (découpe d'un SVG entier, ancien mode) n'existe plus : elle
traçait au laser un trait entre les contours d'un même chemin ; les calques de découpe la remplacent."""
import numpy as np

from laser_studio.gcode.common import GcodeResult, start_lines
from laser_studio.gcode.timing import job_duration
from laser_studio.gcode.raster import raster_image_gcode
from laser_studio.gcode.vector import build_vector_layers_gcode


def build_job_gcode(processed_array, params, vector_layers_data=None, progress=None):
    """G-Code du job.

    processed_array : image tramée à graver (tableau numpy), ou None.
    vector_layers_data : calques vectoriels (voir
    vector.layer_data.extract_vector_layer_data), ou None.
    params : réglages du job (gcode.params.JobParams, voir JobController.build_params).
    progress : fonction appelée avec l'avancement (0 à 100), facultative.

    Renvoie un GcodeResult."""
    def report(pct):
        if progress is not None:
            progress(pct)

    gcode = ["; --- G-CODE HYBRIDE GRBL PRO ---"]
    gcode.extend(start_lines(params.homing, params.start_gcode))

    total_power_samples = []
    total_time_seconds = 0.0
    base_offset_x, base_offset_y = params.vector_origin()

    if processed_array is not None:
        gcode.append("; --- PHASE 1 : GRAVURE IMAGE (SURBALAYAGE ACTIF) ---")
        lines, seconds, samples = raster_image_gcode(processed_array, params, progress=report)
        gcode.extend(lines)
        total_time_seconds += seconds
        total_power_samples.extend(samples)

    report(70)

    report(85)

    if vector_layers_data:
        gcode.append("; --- PHASE 3 : CALQUES VECTORIELS (TEXTE & FORMES) ---")
        vector_overscan_dist = params.overscan_for(params.width_mm) if params.enable_overscan else 0.0
        layer_gcode, layer_time, layer_power_samples = build_vector_layers_gcode(
            vector_layers_data, base_offset_x, base_offset_y, params.height_mm,
            params.laser_cmd, params.s_max, overscan_dist=vector_overscan_dist,
            safe_cut_order=params.safe_cut_order, scan_offset=params.scan_offset_mm,
        )
        gcode.extend(layer_gcode)
        total_time_seconds += layer_time
        total_power_samples.extend(layer_power_samples)

    end_gcode = params.end_gcode.strip()
    if end_gcode:
        gcode.append("; --- G-Code de Fin ---")
        gcode.append(end_gcode)
    else:
        if gcode[-1] != "M5":                 # chaque phase se termine déjà laser éteint
            gcode.append("M5")
        gcode.append("G0 X0 Y0\n; FIN DU TRAVAIL")

    avg_power = float(np.mean(total_power_samples)) if total_power_samples else 0.0
    text = "\n".join(gcode)
    seconds = job_duration(text, params.machine_limits, total_time_seconds)
    report(100)
    return GcodeResult(text, len(gcode), avg_power, seconds)
