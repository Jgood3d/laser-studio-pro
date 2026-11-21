"""Éléments communs aux générateurs de G-Code : le résultat d'une génération,
la distance de surbalayage et la mise en forme de la durée estimée."""
from typing import NamedTuple

# Mode de surbalayage (params['overscan_mode']) : valeur indépendante de la
# langue, fournie par la fenêtre (voir GcodeGenerationMixin._overscan_mode_value).
OVERSCAN_PERCENT = "Pourcentage (%)"
OVERSCAN_FIXED = "Distance Fixe (mm)"


class GcodeResult(NamedTuple):
    """Résultat d'une génération : le G-Code, son nombre de lignes, la
    puissance moyenne (%) des tracés gravés et la durée estimée (texte).

    C'est un tuple : il se décompose comme les signaux `finished` des workers
    (gcode, nb_lignes, puissance_moyenne, durée)."""
    gcode: str
    line_count: int
    avg_power: float
    duration: str


def overscan_distance(params, width_mm, default_dist=2.5):
    """Distance de surbalayage (mm) d'après les paramètres : un pourcentage de
    `width_mm` (largeur gravée) en mode « Pourcentage », sinon la distance
    fixe. Ne vérifie pas si le surbalayage est activé : c'est à l'appelant."""
    if params.get('overscan_mode') == OVERSCAN_PERCENT:
        return width_mm * (params.get('overscan_pct', 5.0) / 100.0)
    return params.get('overscan_dist', default_dist)


def scan_offset_mm(params):
    """Décalage des lignes retour (mm, voir bidir_test_gcode) ; 0 si absent ou
    illisible."""
    try:
        return float(params.get('scan_offset_mm', 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def job_duration_text(total_seconds):
    """Durée estimée d'un job, avec 15 % de marge (accélérations), par exemple
    « 3 min 12 sec » ou « 45 sec »."""
    time_minutes = (total_seconds / 60.0) * 1.15
    mins = int(time_minutes)
    secs = int((time_minutes - mins) * 60)
    return f"{mins} min {secs} sec" if mins > 0 else f"{secs} sec"


def matrix_duration_text(total_seconds):
    """Durée estimée d'une matrice de test, sans marge, toujours avec les
    minutes (« 0 min 46 sec »)."""
    mins = int(total_seconds / 60)
    secs = int(total_seconds % 60)
    return f"{mins} min {secs} sec"


def start_lines(params):
    """Lignes de début de job : homing ($H) et G-Code de début, s'ils sont
    demandés."""
    lines = []
    if params.get('homing'):
        lines.append("$H ; Homing initial")
    start = str(params.get('start_gcode', '') or '').strip()
    if start:
        lines.append("; --- G-Code de Début ---")
        lines.append(start)
    return lines
