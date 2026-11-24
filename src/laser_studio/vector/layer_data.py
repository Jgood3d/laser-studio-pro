"""Objets de l'éditeur vectoriel -> polygones en mm groupés par calque, pour la
génération du G-Code (gcode/vector.py). À appeler dans le thread de
l'interface : le résultat ne contient plus d'objet Qt."""
from PyQt6.QtGui import QTransform
from laser_studio.models.layers import ENGRAVE_MODE, LayersModel
from laser_studio.vector.boolean_ops import paint_region

# Ancien nom du modèle des calques (models/layers.py).


def _optimize_polygon_order(polygons):
    """Réordonne une liste de polygones par plus proche voisin (glouton) en
    partant du premier tracé : à chaque étape, choisit le polygone restant
    dont le point de départ est le plus proche du dernier point du tracé
    précédent. Ne change JAMAIS la géométrie elle-même, seulement l'ordre
    de passage — réduit les déplacements G0 entre les tracés d'un même
    calque (Découpe/Marquage), qui suivaient sinon l'ordre de création/
    import des objets, souvent loin d'être optimal.

    Plafonné en pratique par l'appelant (voir extract_vector_layer_data) :
    algorithme glouton en O(n²), appelé dans le thread principal Qt — pas
    de coût significatif pour un nombre raisonnable de tracés, mais à
    éviter sur des milliers d'objets."""
    if len(polygons) < 2:
        return polygons
    remaining = list(polygons)
    ordered = [remaining.pop(0)]
    current_end = ordered[-1][-1]
    while remaining:
        best_idx = min(
            range(len(remaining)),
            key=lambda i: (remaining[i][0][0] - current_end[0]) ** 2
                        + (remaining[i][0][1] - current_end[1]) ** 2
        )
        nxt = remaining.pop(best_idx)
        ordered.append(nxt)
        current_end = nxt[-1]
    return ordered


# Au-delà de ce nombre de tracés dans un même calque, l'optimisation
# glouton (O(n²)) est sautée pour ce calque — évite de bloquer l'UI
# plusieurs secondes sur un design très complexe (des milliers d'objets),
# puisque extract_vector_layer_data s'exécute dans le thread principal Qt.
MAX_POLYGONS_FOR_PATH_OPTIMIZATION = 1500

def _path_polygons(path):
    """Polygones (listes de (x, y) en mm) d'un tracé, sans les morceaux de moins de 2 points."""
    polygons = []
    for poly in path.toSubpathPolygons(QTransform()):
        pts = [(p.x(), p.y()) for p in poly]
        if len(pts) >= 2:
            polygons.append(pts)
    return polygons


def extract_vector_layer_data(objects, layer_manager: LayersModel, optimize_path=True):
    """À appeler dans le thread principal (Qt). Convertit chaque VectorObject en
    polygones purement numériques (mm), groupés par calque. Aucun objet Qt
    n'est conservé ensuite -> peut être passé sans risque à un QThread.

    optimize_path (défaut True) : réordonne les tracés de chaque calque par
    plus proche voisin pour réduire les déplacements G0 (voir
    _optimize_polygon_order) — sans effet sur les calques en mode 'Gravure
    Remplie' (balayage scanline sur toute la zone, l'ordre des tracés n'y
    change rien au trajet réel).
    """
    layers_data = {}
    for layer in layer_manager.layers:
        if not layer.enabled:
            continue
        layers_data[layer.id] = {"layer": layer.to_dict(), "polygons": [], "polygon_groups": []}

    # Un simple groupe donne chacun de ses objets, sur son calque ; un groupe booléen (union, différence…)
    # donne son tracé résultant (GroupObject.engraving_items). Dans l'ordre du dessin.
    items = [item for obj in objects for item in obj.engraving_items()]
    with_knockout = {layer_id for layer_id, _path, knockout in items if knockout}
    for layer_id in layers_data:
        layer_items = [(path, knockout) for lid, path, knockout in items if lid == layer_id]
        if layer_id in with_knockout:
            # Objets blancs sur ce calque : la surface gravée est celle qu'on voit à l'écran (le blanc efface
            # ce qui est dessous), d'un seul tenant.
            layer_items = [(paint_region(layer_items), False)]
        for path, knockout in layer_items:
            if knockout:
                continue
            poly_points = _path_polygons(path)
            if poly_points:
                layers_data[layer_id]["polygons"].extend(poly_points)
                # Un groupe par objet : le remplissage applique la règle pair-impair DANS un objet (trous),
                # puis réunit les objets entre eux (voir _scanline_fill_union).
                layers_data[layer_id]["polygon_groups"].append(poly_points)

    if optimize_path:
        for layer_id, data in layers_data.items():
            if data["layer"].get("mode") == ENGRAVE_MODE:
                continue  # balayage scanline : l'ordre des tracés n'a pas d'effet
            polys = data["polygons"]
            if 1 < len(polys) <= MAX_POLYGONS_FOR_PATH_OPTIMIZATION:
                data["polygons"] = _optimize_polygon_order(polys)

    return layers_data
