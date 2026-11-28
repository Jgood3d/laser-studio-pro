"""Statistiques d'un G-Code envoyé au graveur, sans Qt : de quoi garder la trace d'une gravure (historique)
et comparer plus tard la durée estimée à la durée réelle.

    stats = gcode_statistics(texte)
    stats["burn_mm"], stats["travel_mm"], stats["max_feed"], stats["bounds"]
"""
import math
import re

_WORD_RE = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")


def gcode_statistics(gcode_text):
    """Lignes de commande, déplacements G0 / G1, distance gravée (G1 laser allumé : M3 / M4 avec S > 0),
    distance à vide (G0, et G1 laser éteint), vitesse F et puissance S maximales, encombrement des
    déplacements (xmin, ymin, xmax, ymax) en mm. Coordonnées absolues (G90) et relatives (G91)."""
    x = y = 0.0
    absolute = True
    power = 0.0
    laser_on = False
    motion = 0
    stats = {"lines": 0, "g0": 0, "g1": 0, "burn_mm": 0.0, "travel_mm": 0.0, "max_feed": 0.0, "max_power": 0.0}
    xmin = ymin = math.inf
    xmax = ymax = -math.inf
    for raw in gcode_text.splitlines():
        line = re.sub(r"\([^)]*\)", "", raw.split(";", 1)[0]).strip().upper()
        if not line or line.startswith("$"):
            continue
        stats["lines"] += 1
        words = _WORD_RE.findall(line)
        target_x, target_y, moved = x, y, False
        for letter, value in words:
            number = float(value)
            if letter == "G":
                if number in (0.0, 1.0, 2.0, 3.0):
                    motion = int(number)
                elif number == 90.0:
                    absolute = True
                elif number == 91.0:
                    absolute = False
            elif letter == "M":
                if number in (3.0, 4.0):
                    laser_on = True
                elif number == 5.0:
                    laser_on = False
            elif letter == "S":
                power = number
                stats["max_power"] = max(stats["max_power"], number)
            elif letter == "F":
                stats["max_feed"] = max(stats["max_feed"], number)
            elif letter == "X":
                target_x = number if absolute else x + number
                moved = True
            elif letter == "Y":
                target_y = number if absolute else y + number
                moved = True
        if not moved:
            continue
        distance = math.hypot(target_x - x, target_y - y)
        if motion == 0:
            stats["g0"] += 1
            stats["travel_mm"] += distance
        else:
            stats["g1"] += 1
            if laser_on and power > 0:
                stats["burn_mm"] += distance
            else:
                stats["travel_mm"] += distance
        x, y = target_x, target_y
        xmin, ymin, xmax, ymax = min(xmin, x), min(ymin, y), max(xmax, x), max(ymax, y)
    stats["burn_mm"] = round(stats["burn_mm"], 1)
    stats["travel_mm"] = round(stats["travel_mm"], 1)
    stats["bounds"] = None if xmin == math.inf else [round(v, 2) for v in (xmin, ymin, xmax, ymax)]
    return stats
