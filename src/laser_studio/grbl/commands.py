"""Commandes GRBL et lecture des réglages du graveur, sans Qt.

Toutes les commandes envoyées par les boutons de pilotage sont construites
ici, à partir de valeurs métier (mm, mm/min) : le panneau de pilotage émet
des intentions, le contrôleur du graveur les traduit avec ce module. Les
futurs boutons « macros » s'appuieront dessus.

    jog_command(10.0, 0.0, 3000)        # "$J=G91 G21 X10.000 Y0.000 F3000"
    frame_commands(10, 10, 40, 30)      # tour du cadre, en G0
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


def frame_commands(x, y, width, height):
    """Tour du rectangle (coin bas-gauche en x, y), laser éteint (G0), en
    revenant au point de départ."""
    return [
        f"G0 X{x:.3f} Y{y:.3f}",
        f"G0 X{x + width:.3f} Y{y:.3f}",
        f"G0 X{x + width:.3f} Y{y + height:.3f}",
        f"G0 X{x:.3f} Y{y + height:.3f}",
        f"G0 X{x:.3f} Y{y:.3f}",
    ]


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
