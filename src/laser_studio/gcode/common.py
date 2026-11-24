"""Éléments communs aux générateurs de G-Code : le résultat d'une génération, la puissance (valeur S),
la distance de surbalayage et la durée estimée (en secondes, marge comprise ; sa mise en forme traduite
est dans i18n/durations.py)."""
from typing import NamedTuple

# Mode de surbalayage (params['overscan_mode']) : valeur indépendante de la
# langue, fournie par la fenêtre (voir JobController.overscan_mode_value).
OVERSCAN_PERCENT = "Pourcentage (%)"
OVERSCAN_FIXED = "Distance Fixe (mm)"


class GcodeResult(NamedTuple):
    """Résultat d'une génération : le G-Code, son nombre de lignes, la
    puissance moyenne (%) des tracés gravés et la durée estimée en secondes,
    marge des accélérations comprise (with_time_margin).

    C'est un tuple : il se décompose comme les signaux `finished` des workers
    (gcode, nb_lignes, puissance_moyenne, durée)."""
    gcode: str
    line_count: int
    avg_power: float
    duration: float


def power_value(percent, s_max):
    """Valeur S de GRBL pour une puissance de `percent` % (S-Max = `s_max`), arrondie au plus proche.
    Seul calcul de la puissance du G-Code : une case de la matrice de test et un calque réglé au même
    pourcentage donnent ainsi le même S."""
    return max(0, int(round(float(percent) / 100.0 * float(s_max))))


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


# Marge ajoutée à toute durée calculée d'après le G-Code (job, matrice de test, motif aller/retour) : les
# accélérations et décélérations de la machine allongent le temps des trajets à vitesse constante.
# L'estimation rapide (bouton « Estimer ») n'en a pas : elle le dit dans son message.
TIME_MARGIN = 1.15


def with_time_margin(seconds):
    """Durée calculée d'après le G-Code (secondes), plus la marge des accélérations (TIME_MARGIN)."""
    return max(0.0, float(seconds)) * TIME_MARGIN


def duration_parts(seconds):
    """(heures, minutes, secondes) entières d'une durée, arrondie à la seconde."""
    total = max(0, int(round(float(seconds))))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return hours, minutes, secs


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
