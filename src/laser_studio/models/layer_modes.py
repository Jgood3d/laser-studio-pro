"""Modes des calques : des codes indépendants de la langue, sans Qt.

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

LAYER_MODES = (MODE_FILL, MODE_CUT, MODE_MARK)
# Modes qui ne tracent que le contour : le pas de remplissage n'y sert pas.
CONTOUR_MODES = (MODE_CUT, MODE_MARK)

LAYER_MODE_TR_KEYS = {
    MODE_CUT: "layers.mode.cut",
    MODE_FILL: "layers.mode.fill",
    MODE_MARK: "layers.mode.mark",
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
