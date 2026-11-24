"""Opérations booléennes sur des tracés (QPainterPath, QtGui sans widget) : ce que remplit un groupe
d'objets selon son opération.

Chaque tracé est pris en règle pair-impair, comme le remplissage d'un objet seul (un trou dans une lettre
reste un trou). L'ordre compte pour la différence : du dessous vers le dessus, le premier tracé moins
tous les autres.

    combine([dessous, dessus], DIFFERENCE)      # l'intérieur du dessous, moins celui du dessus
"""
from functools import reduce

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainterPath, QTransform

GROUP = "group"                  # simple groupe : chaque objet garde son remplissage et son calque
UNION = "union"                  # la surface couverte par au moins un objet
DIFFERENCE = "difference"        # l'objet du dessous moins ceux du dessus
INTERSECTION = "intersection"    # la surface commune à tous les objets
EXCLUSION = "exclusion"          # la surface couverte par un nombre impair d'objets
OPERATIONS = (GROUP, UNION, DIFFERENCE, INTERSECTION, EXCLUSION)
BOOLEAN_OPERATIONS = OPERATIONS[1:]

# Qt aplatit les courbes des opérations booléennes avec une tolérance d'environ une unité : en mm, un
# cercle de 5 mm s'écarterait de 0,1 mm. Les tracés sont donc combinés à cette échelle, puis ramenés en mm.
BOOLEAN_SCALE = 100.0


def _even_odd(path):
    path = QPainterPath(path)
    path.setFillRule(Qt.FillRule.OddEvenFill)
    return path


def _scaled(path, factor):
    mapped = QTransform.fromScale(factor, factor).map(path)
    mapped.setFillRule(path.fillRule())
    return mapped


def _xor(a, b):
    return a.united(b).subtracted(a.intersected(b))


def combine(paths, operation):
    """Tracé résultant de `paths` (du dessous vers le dessus) pour `operation`. GROUP juxtapose les tracés
    sans les fusionner."""
    if operation not in OPERATIONS:
        raise ValueError(f"opération inconnue : {operation!r}")
    paths = [_even_odd(p) for p in paths]
    if not paths:
        return QPainterPath()
    if operation == GROUP or len(paths) == 1:
        out = QPainterPath()
        for p in paths:
            out.addPath(p)
        return out
    paths = [_scaled(p, BOOLEAN_SCALE) for p in paths]
    if operation == UNION:
        result = reduce(lambda a, b: a.united(b), paths)
    elif operation == DIFFERENCE:
        result = paths[0].subtracted(reduce(lambda a, b: a.united(b), paths[1:]))
    elif operation == INTERSECTION:
        result = reduce(lambda a, b: a.intersected(b), paths)
    else:
        result = reduce(_xor, paths)
    return _even_odd(_scaled(result.simplified(), 1 / BOOLEAN_SCALE))


def paint_region(items):
    """Surface peinte par des tracés superposés, dans l'ordre du dessin : [(tracé, efface)] ; un tracé
    s'ajoute, ou efface ce qui est dessous (sert au contenu d'un <mask> SVG : clair visible, sombre caché).
    Chaque tracé en règle pair-impair ; tracé vide si rien ne reste."""
    region = None
    for path, light in items:
        scaled = _scaled(_even_odd(path), BOOLEAN_SCALE)
        if region is None:
            if not light:
                region = scaled
            continue
        region = region.subtracted(scaled) if light else region.united(scaled)
    if region is None:
        return QPainterPath()
    return _even_odd(_scaled(region.simplified(), 1 / BOOLEAN_SCALE))
