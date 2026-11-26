"""Modes des calques : des codes indépendants de la langue, sans Qt.

Aussi la lecture, sans Qt, de la commande laser et du surbalayage d'un calque
(objet LaserLayer ou dictionnaire to_dict) : utilisée par la génération du
G-Code (paquet gcode/).

Les codes sont enregistrés dans les projets, les profils machine et les
commentaires du G-Code (« ; --- CALQUE 'Nom' [cut] --- »), et comparés par
la génération. Seul leur AFFICHAGE est traduit (LAYER_MODE_TR_KEYS).

Jusqu'à la version 2.5, les modes étaient enregistrés sous leur libellé
français (« Gravure Remplie », « Découpe », « Marquage (Contour) ») :
normalize_mode() les convertit à la lecture (projets, profils, matériaux,
G-Code rechargé).
"""

MODE_FILL = "engrave_fill"     # gravure remplie (balayage)
MODE_CUT = "cut"               # découpe (contour, passes)
MODE_MARK = "mark"             # marquage (contour)
MODE_PERF = "perforate"        # perforation (contour en pointillé : traits séparés de vides)

LAYER_MODES = (MODE_FILL, MODE_CUT, MODE_MARK, MODE_PERF)
# Modes qui ne tracent que le contour : le pas de remplissage n'y sert pas.
CONTOUR_MODES = (MODE_CUT, MODE_MARK, MODE_PERF)

LAYER_MODE_TR_KEYS = {
    MODE_CUT: "layers.mode.cut",
    MODE_FILL: "layers.mode.fill",
    MODE_MARK: "layers.mode.mark",
    MODE_PERF: "layers.mode.perforate",
}

# Anciens libellés enregistrés -> code.
LEGACY_MODE_CODES = {
    "Gravure Remplie": MODE_FILL,
    "Découpe": MODE_CUT,
    "Marquage (Contour)": MODE_MARK,
}


def normalize_mode(value):
    """Code du mode `value` : un code est rendu tel quel, un ancien libellé
    français est converti ; toute autre valeur est rendue inchangée (elle
    sera refusée par la validation des calques)."""
    if isinstance(value, str):
        return LEGACY_MODE_CODES.get(value, value)
    return value


# Commande laser propre à un calque : "" = celle de Configuration GRBL (réglage global), sinon "M4"
# (puissance dynamique) ou "M3" (puissance constante) pour ce calque seulement.
LAYER_LASER_CMDS = ("", "M4", "M3")


def _layer_value(layer, key, default):
    """Réglage `key` d'un calque donné comme objet (LaserLayer) ou comme dictionnaire (to_dict) ;
    `default` si le calque ne l'a pas (projet enregistré avant l'ajout du réglage)."""
    if isinstance(layer, dict):
        return layer.get(key, default)
    return getattr(layer, key, default)


def layer_overscan_enabled(layer, global_enabled):
    """True si le surbalayage s'applique à ce calque : activé dans Configuration GRBL (`global_enabled`)
    ET pour le calque. Un calque sans ce réglage (ancien projet) suit le réglage global."""
    return bool(global_enabled) and bool(_layer_value(layer, "overscan", True))


def layer_laser_cmd(layer, global_cmd):
    """Commande laser ("M4" ou "M3") de ce calque : la sienne, sinon celle de Configuration GRBL."""
    cmd = _layer_value(layer, "laser_cmd", "")
    return cmd if cmd in ("M4", "M3") else global_cmd
