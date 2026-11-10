"""Lecture de G-Code pour les tests : segments réellement gravés."""

import re

_WORD = re.compile(r"([A-Z])\s*(-?\d*\.?\d+)")


def burn_segments(gcode):
    """Segments horizontaux gravés : [(y, x_début, x_fin, puissance)].

    Suit l'état du G-Code ligne par ligne : déplacement G0 / G1 (modal),
    laser allumé par M3 / M4 et éteint par M5, puissance S (modale, sur une
    ligne M3 / M4 ou sur un G1). Un segment est gravé par un G1 laser
    allumé, puissance > 0, qui déplace la tête. Seuls les segments
    horizontaux (y constant), ceux des lignes de remplissage et de
    tramage, sont rendus, dans l'ordre du G-Code. Les commentaires (après
    « ; » ou entre parenthèses) sont ignorés.
    """
    x = y = 0.0
    power = 0.0
    laser_on = False
    motion = None
    segments = []
    for raw in gcode.splitlines():
        line = re.sub(r"\(.*?\)", "", raw.split(";")[0]).strip().upper()
        if not line:
            continue
        words = _WORD.findall(line)
        new_x, new_y = x, y
        moved = False
        for letter, value in words:
            number = float(value)
            if letter == "G" and number in (0, 1):
                motion = int(number)
            elif letter == "M" and number in (3, 4):
                laser_on = True
            elif letter == "M" and number == 5:
                laser_on = False
            elif letter == "S":
                power = number
            elif letter == "X":
                new_x, moved = number, True
            elif letter == "Y":
                new_y, moved = number, True
        if (moved and motion == 1 and laser_on and power > 0
                and new_y == y and new_x != x):
            segments.append((y, x, new_x, power))
        x, y = new_x, new_y
    return segments
