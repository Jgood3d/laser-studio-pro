"""Commandes GRBL et lecture des réglages du graveur, sans Qt.

Toutes les commandes envoyées par les boutons de pilotage sont construites
ici, à partir de valeurs métier (mm, mm/min) : le panneau de pilotage émet
des intentions, le contrôleur du graveur les traduit avec ce module. Les
futurs boutons « macros » s'appuieront dessus.

    jog_command(10.0, 0.0, 3000)        # "$J=G91 G21 X10.000 Y0.000 F3000"
    frame_commands([[(10, 10), (50, 10), (50, 40), (10, 40), (10, 10)]], 5)   # tour du cadre, laser à S5
    parse_grbl_settings(reponse_a_dollar_dollar)   # {"$22": "1", "$32": "1", ...}
"""

import re

HOME = "$H"                         # cycle de homing
UNLOCK = "$X"                       # déverrouillage après une alarme
READ_SETTINGS = "$$"                # réglages du graveur
SET_WORK_ZERO = "G92 X0 Y0"         # origine de travail à la position actuelle
GO_TO_WORK_ZERO = "G0 X0 Y0"        # retour à l'origine de travail

# Réglages GRBL lus après la connexion.
HOMING_SETTING = "$22"              # 0 : homing désactivé
LASER_MODE_SETTING = "$32"          # 1 : mode laser (M4 dynamique, coupure pendant les G0)


def jog_command(dx_mm, dy_mm, speed):
    """Déplacement relatif de `dx_mm`, `dy_mm`, à `speed` mm/min."""
    return f"$J=G91 G21 X{dx_mm:.3f} Y{dy_mm:.3f} F{speed}"


# Cadrage : vitesse (la puissance est un réglage de la machine, GrblConfig.frame_power_pct).
FRAME_SPEED = 3000                  # mm/min


def frame_commands(paths, s_value, speed=FRAME_SPEED):
    """Tour des tracés fermés `paths` ([(x, y)…] en mm, voir gcode.framing) avec le laser allumé à
    `s_value` (M3, puissance constante) pour voir le parcours, en G1 à `speed` mm/min. Rejoint chaque départ
    laser éteint (G0) et éteint le laser (M5) à la fin de chaque tracé."""
    lines = ["G90"]
    for path in paths:
        (x, y), rest = path[0], path[1:]
        lines += [f"G0 X{x:.3f} Y{y:.3f}", f"M3 S{s_value:g}"]
        lines += [f"G1 X{px:.3f} Y{py:.3f}" + (f" F{speed}" if i == 0 else "") for i, (px, py) in enumerate(rest)]
        lines.append("M5")
    return lines


# Lignes qui modifient la carte GRBL au lieu de graver : réglage « $N=… », effacement « $RST=… », ligne de
# démarrage « $N0=… », veille « $SLP ».
_BOARD_CHANGE_RE = re.compile(r"\$(?:\d+\s*=|RST|N|SLP)", re.IGNORECASE)
_POWER_RE = re.compile(r"S\s*(\d+(?:\.\d*)?)", re.IGNORECASE)


def risky_lines(gcode_text, s_max, limit=10):
    """Lignes d'un G-Code (fichier venu d'un autre outil, console retouchée) qui modifient la configuration de
    GRBL ou demandent une puissance au-delà de `s_max` : à faire confirmer avant l'envoi. Au plus `limit`
    lignes, dans l'ordre du fichier ; commentaires « ; » et « (…) » ignorés."""
    # Cas courant (G-Code généré ici) en un seul passage sur le texte : ni « $ » ni puissance au-delà du S-Max.
    if "$" not in gcode_text and all(float(v) <= s_max for v in _POWER_RE.findall(gcode_text)):
        return []
    found = []
    for raw in gcode_text.split("\n"):
        line = re.sub(r"\(.*?\)", "", raw.split(";", 1)[0]).strip()
        if not line:
            continue
        if line.startswith("$"):
            risky = _BOARD_CHANGE_RE.match(line) is not None
        else:
            risky = any(float(value) > s_max for value in _POWER_RE.findall(line))
        if risky:
            found.append(raw.strip())
            if len(found) >= limit:
                break
    return found


def homing_succeeded(response):
    """Vrai si la réponse de GRBL à « $H » se termine par « ok ». « ALARM:9 » (fin de course non atteinte),
    « error:5 » (homing désactivé), « Pas de réponse » ou une réponse coupée : position toujours inconnue."""
    lines = [line.strip() for line in (response or "").splitlines() if line.strip()]
    return bool(lines) and lines[-1] == "ok"


def parse_grbl_settings(response):
    """Réponse de « $$ » -> {"$32": "1", "$22": "0", ...} (commentaires
    « (...) » ignorés)."""
    grbl_settings = {}
    for line in (response or "").splitlines():
        line = line.strip()
        if line.startswith("$") and "=" in line:
            key, value = line.split("=", 1)
            grbl_settings[key.strip()] = value.split("(", 1)[0].strip()
    return grbl_settings


# Réglage numérique « $110=6000 », commentaire « (…) » éventuel écarté. Les autres commandes qui ont
# la même forme ne sont jamais écrites : $RST=* efface la carte, $N0=… s'exécute à chaque démarrage
# (un M3 y allumerait le laser), $J=… déplace la tête, $SLP=… met la carte en veille.
_SETTING_RE = re.compile(r"\s*\$(\d+)\s*=\s*([^\s(]+)")


def setting_lines(text):
    """Réglages numériques « $N=valeur » d'un texte (réglages affichés, fichier importé), sans espaces
    ni commentaire ; toute autre ligne est ignorée."""
    lines = []
    for line in (text or "").splitlines():
        match = _SETTING_RE.match(line)
        if match:
            lines.append(f"${match.group(1)}={match.group(2)}")
    return lines


def response_setting_lines(response):
    """Lignes de réglage d'une réponse à « $$ » (toute ligne qui commence
    par « $ »)."""
    return [line.strip() for line in (response or "").splitlines() if line.strip().startswith("$")]


def without_homing(gcode_text):
    """G-Code pour un graveur sans homing : chaque ligne « $H » devient « G4 P0 » (pause nulle, acceptée par
    GRBL), que GRBL aurait refusée (error:5) en arrêtant le job. Le nombre de lignes ne change pas : suivi de
    la gravure et reprise restent alignés sur le G-Code affiché. Renvoie (texte, nombre de lignes remplacées)."""
    lines = gcode_text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.strip().upper() == HOME:
            lines[index] = "G4 P0"
            replaced += 1
    return "\n".join(lines), replaced


def homing_support(grbl_settings):
    """Homing d'après les réglages lus ($22) :
    - None : valeur illisible, rien ne change ;
    - (True, None) : homing disponible ;
    - (False, "disabled") : $22=0, homing désactivé ;
    - (False, "unsupported") : $22 absent, homing non supporté."""
    value = grbl_settings.get(HOMING_SETTING)
    if value is not None and not value.isdigit():
        return None
    if value is None:
        return False, "unsupported"
    if value == "0":
        return False, "disabled"
    return True, None
