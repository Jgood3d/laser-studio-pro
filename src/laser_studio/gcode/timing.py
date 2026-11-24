"""Durée d'un G-Code sur une machine GRBL, calculée comme GRBL planifie ses déplacements (sans Qt).

Ce qui compte, et que la somme « distance ÷ vitesse » ignorait :
- les déplacements rapides G0, à la vitesse maximale de la machine ;
- l'accélération : chaque déplacement suit un trapèze (accélère, palier, freine) ;
- la vitesse de passage d'un segment au suivant, d'après l'angle entre les deux (« déviation de
  jonction » de GRBL, $11) : un demi-tour en bout de ligne s'arrête complètement, une ligne droite
  découpée en morceaux (changements de puissance d'une image) ne ralentit pas ;
- le tampon de GRBL, qui ne prévoit que quelques déplacements à l'avance : sur une image très fine,
  la machine doit toujours pouvoir freiner avant la fin de ce qu'elle voit, et n'atteint pas sa vitesse ;
- les vitesses et accélérations propres à X et à Y ($110, $111, $120, $121) ;
- les pauses G4.

    limits = MachineLimits.from_grbl_settings(parse_grbl_settings(texte_de_$$), max_speed, accel)
    secondes = estimate_seconds(gcode_text, limits)
"""
import math
import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")
# Déplacements plus courts : négligés (pas de bloc dans GRBL).
_MIN_LENGTH_MM = 1e-6


@dataclass
class MachineLimits:
    """Vitesses maximales (mm/min) et accélérations (mm/s²) par axe, déviation de jonction (mm) et nombre
    de déplacements que GRBL prévoit à l'avance (taille utile de son tampon de planification)."""
    max_rate_x: float = 6000.0
    max_rate_y: float = 6000.0
    accel_x: float = 500.0
    accel_y: float = 500.0
    junction_deviation: float = 0.01
    planner_blocks: int = 15

    @classmethod
    def from_grbl_settings(cls, settings, max_speed=None, accel=None):
        """Réglages lus avec « $$ » ({"$110": "6000", ...}) ; à défaut, `max_speed` (mm/min) et `accel`
        (mm/s²) de « Paramètres du graveur » ; à défaut, les valeurs par défaut."""
        def value(key, fallback):
            try:
                number = float((settings or {}).get(key, ""))
            except (TypeError, ValueError):
                return fallback
            return number if number > 0 else fallback

        base = cls()
        rate = float(max_speed) if max_speed and max_speed > 0 else base.max_rate_x
        acc = float(accel) if accel and accel > 0 else base.accel_x
        return cls(max_rate_x=value("$110", rate), max_rate_y=value("$111", rate),
                   accel_x=value("$120", acc), accel_y=value("$121", acc),
                   junction_deviation=value("$11", base.junction_deviation))

    def to_dict(self):
        return dict(self.__dict__)


def _segments(gcode_text, limits):
    """(longueur mm, vitesse de croisière mm/s, accélération mm/s², vecteur unitaire, pause s) de chaque
    déplacement ; une pause G4 est un segment de longueur nulle."""
    x = y = 0.0
    absolute = True
    motion = 0
    feed = None
    out = []
    for raw in gcode_text.splitlines():
        line = re.sub(r"\([^)]*\)", "", raw.split(";", 1)[0]).strip().upper()
        if not line or line[0] in "$%":
            continue
        words = _WORD_RE.findall(line)
        target_x, target_y, moved, dwell = x, y, False, None
        letters = {letter for letter, _v in words}
        for letter, value in words:
            number = float(value)
            if letter == "G":
                if number in (0.0, 1.0, 2.0, 3.0):
                    motion = int(number)
                elif number == 4.0:
                    dwell = 0.0
                elif number == 90.0:
                    absolute = True
                elif number == 91.0:
                    absolute = False
            elif letter == "F":
                feed = number
            elif letter == "X":
                target_x = number if absolute else x + number
                moved = True
            elif letter == "Y":
                target_y = number if absolute else y + number
                moved = True
            elif letter == "P" and dwell is not None:
                dwell = number
        if dwell is not None and "P" in letters:
            out.append((0.0, 0.0, 0.0, (0.0, 0.0), dwell))
            continue
        if not moved:
            continue
        dx, dy = target_x - x, target_y - y
        length = math.hypot(dx, dy)
        x, y = target_x, target_y
        if length < _MIN_LENGTH_MM:
            continue
        ux, uy = dx / length, dy / length
        # Limites de la machine ramenées à la direction du déplacement (comme GRBL) : l'axe le plus
        # contraint décide.
        rate_limit = min(limits.max_rate_x / abs(ux) if ux else math.inf,
                         limits.max_rate_y / abs(uy) if uy else math.inf)
        accel = min(limits.accel_x / abs(ux) if ux else math.inf, limits.accel_y / abs(uy) if uy else math.inf)
        speed = rate_limit if motion == 0 or not feed else min(feed, rate_limit)
        out.append((length, speed / 60.0, accel, (ux, uy), 0.0))
    return out


def _junction_speed(prev, nxt, limits, accel):
    """Vitesse maximale au passage du segment `prev` au segment `nxt` (mm/s), méthode de GRBL."""
    cos_theta = -(prev[0] * nxt[0] + prev[1] * nxt[1])
    if cos_theta >= 0.999999:            # demi-tour : arrêt complet
        return 0.0
    if cos_theta <= -0.999999:           # tout droit : pas de limite due à l'angle
        return math.inf
    sin_half = math.sqrt(0.5 * (1.0 - cos_theta))
    return math.sqrt(accel * limits.junction_deviation * sin_half / (1.0 - sin_half))


def _trapezoid_time(length, v_entry, v_exit, v_cruise, accel):
    """Temps d'un déplacement : accélère de v_entry, palier à v_cruise si la distance le permet, freine
    jusqu'à v_exit."""
    if length <= 0:
        return 0.0
    accel_dist = max(0.0, (v_cruise ** 2 - v_entry ** 2) / (2 * accel))
    decel_dist = max(0.0, (v_cruise ** 2 - v_exit ** 2) / (2 * accel))
    if accel_dist + decel_dist <= length:
        return ((v_cruise - v_entry) + (v_cruise - v_exit)) / accel + (length - accel_dist - decel_dist) / v_cruise
    peak = math.sqrt(max((2 * accel * length + v_entry ** 2 + v_exit ** 2) / 2.0, 0.0))
    return (max(peak - v_entry, 0.0) + max(peak - v_exit, 0.0)) / accel


def estimate_seconds(gcode_text, limits=None):
    """Durée estimée (secondes) du G-Code `gcode_text` sur une machine de limites `limits`."""
    limits = limits or MachineLimits()
    segments = _segments(gcode_text, limits)
    moves = [s for s in segments if s[0] > 0]
    dwell_total = sum(s[4] for s in segments if s[0] == 0)
    n = len(moves)
    if n == 0:
        return dwell_total
    # Vitesse maximale à chaque jonction j (entre moves[j-1] et moves[j]) ; départ et fin à l'arrêt.
    junction = [0.0] * (n + 1)
    for j in range(1, n):
        prev, nxt = moves[j - 1], moves[j]
        junction[j] = min(_junction_speed(prev[3], nxt[3], limits, min(prev[2], nxt[2])), prev[1], nxt[1])
    # Tampon limité : à chaque jonction, la machine doit pouvoir s'arrêter avant la fin des
    # `planner_blocks` déplacements suivants.
    horizon = max(1, int(limits.planner_blocks))
    lengths = [m[0] for m in moves]
    window = sum(lengths[:horizon])
    for j in range(n):
        if j > 0:
            window -= lengths[j - 1]
            if j - 1 + horizon < n:
                window += lengths[j - 1 + horizon]
        junction[j] = min(junction[j], math.sqrt(2 * moves[j][2] * window))
    # Passe arrière puis passe avant : on doit pouvoir freiner vers la jonction suivante et accélérer
    # depuis la précédente.
    for j in range(n - 1, -1, -1):
        length, _speed, accel = moves[j][0], moves[j][1], moves[j][2]
        junction[j] = min(junction[j], math.sqrt(junction[j + 1] ** 2 + 2 * accel * length))
    for j in range(n):
        length, _speed, accel = moves[j][0], moves[j][1], moves[j][2]
        junction[j + 1] = min(junction[j + 1], math.sqrt(junction[j] ** 2 + 2 * accel * length))
    total = dwell_total
    for j, (length, speed, accel, _unit, _dwell) in enumerate(moves):
        total += _trapezoid_time(length, junction[j], junction[j + 1], speed, accel)
    return total


def job_duration(gcode_text, params, simple_seconds):
    """Durée affichée d'un G-Code généré : estimate_seconds avec les limites de la machine
    (params['machine_limits'], dictionnaire de MachineLimits) ; sans elles, l'ancienne somme
    « distance ÷ vitesse » `simple_seconds` plus la marge des accélérations (common.with_time_margin)."""
    limits = params.get("machine_limits") if isinstance(params, dict) else None
    if not limits:
        from laser_studio.gcode.common import with_time_margin    # import local : common ne dépend pas d'ici
        return with_time_margin(simple_seconds)
    return estimate_seconds(gcode_text, MachineLimits(**limits))


def straight_lines_seconds(lengths_mm, feed_mm_min, accel_mm_s2):
    """Temps total de lignes droites parcourues chacune départ et arrivée arrêtés (lignes d'une image,
    demi-tour à chaque bout), à `feed_mm_min` : estimation rapide sans G-Code (bouton « Estimer »)."""
    import numpy as np        # import local : seul l'outil d'estimation rapide en a besoin

    lengths = np.asarray(lengths_mm, dtype=float)
    lengths = lengths[lengths > 0]
    if lengths.size == 0:
        return 0.0
    v = max(float(feed_mm_min), 1.0) / 60.0
    a = max(float(accel_mm_s2), 1.0)
    ramp = v * v / a                                   # distance pour accélérer puis freiner (2 × v²/2a)
    full = lengths >= ramp
    t_full = (lengths[full] / v + v / a).sum()         # palier + (accélération + freinage) - distance gagnée
    t_short = (2.0 * np.sqrt(lengths[~full] / a)).sum()
    return float(t_full + t_short)
