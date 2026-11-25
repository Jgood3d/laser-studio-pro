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


def burn_paths(gcode):
    """Tracés gravés d'un seul tenant : [[(x, y), ...], ...], dans l'ordre du G-Code. `gcode` : texte ou
    liste de lignes. Même lecture que GRBL : G0 / G1 et S modaux, laser allumé par M3 / M4, éteint par M5 ;
    un G0, ou un G1 à puissance nulle, termine le tracé en cours."""
    if not isinstance(gcode, str):
        gcode = "\n".join(gcode)
    x = y = 0.0
    power, laser_on, motion = 0.0, False, None
    paths, current = [], None
    for raw in gcode.splitlines():
        line = re.sub(r"\(.*?\)", "", raw.split(";")[0]).strip().upper()
        if not line:
            continue
        new_x, new_y, moved = x, y, False
        for letter, value in _WORD.findall(line):
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
        if moved:
            if motion == 1 and laser_on and power > 0:
                if current is None:
                    current = [(x, y)]
                    paths.append(current)
                current.append((new_x, new_y))
            else:
                current = None
        x, y = new_x, new_y
    return paths


def head_moves(gcode):
    """Déplacements de la tête : [(G, x, y)] (G = 0 ou 1, position d'arrivée), lus comme GRBL (G, X et Y
    modaux). `gcode` : texte ou liste de lignes."""
    if not isinstance(gcode, str):
        gcode = "\n".join(gcode)
    x = y = 0.0
    motion, out = None, []
    for raw in gcode.splitlines():
        line = re.sub(r"\(.*?\)", "", raw.split(";")[0]).strip().upper()
        moved = False
        for letter, value in _WORD.findall(line):
            number = float(value)
            if letter == "G" and number in (0, 1):
                motion = int(number)
            elif letter == "X":
                x, moved = number, True
            elif letter == "Y":
                y, moved = number, True
        if moved:
            out.append((motion, x, y))
    return out
