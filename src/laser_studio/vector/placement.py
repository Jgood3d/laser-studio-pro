"""Placement d'un dessin importé dans l'éditeur vectoriel (fichier SVG / DXF, bibliothèque, générateurs,
Stencil Studio, vectorisation) : marge à gauche pour le surbalayage, et choix de l'utilisateur quand
l'éditeur contient déjà des objets. Calcul sur des rectangles (xmin, ymin, xmax, ymax) en mm, Y vers le
haut ; aucune dépendance à Qt."""

# Choix proposés quand l'éditeur n'est pas vide.
ADD = "add"          # ajouter sans toucher aux objets présents (à l'emplacement habituel)
REPLACE = "replace"  # supprimer les objets présents, puis ajouter
RIGHT = "right"      # ajouter à droite des objets présents
ABOVE = "above"      # ajouter au-dessus des objets présents
MODES = (ADD, REPLACE, RIGHT, ABOVE)

# Écart entre les objets présents et le dessin ajouté à droite ou au-dessus (mm).
GAP_MM = 5.0


def placement_offset(new_bounds, existing_bounds, mode, margin_x=0.0, margin_y=0.0, gap=GAP_MM):
    """Déplacement (dx, dy) à appliquer au dessin importé, d'encombrement `new_bounds`.

    ADD et REPLACE : coin bas-gauche du dessin en (margin_x, margin_y).
    RIGHT : à droite de `existing_bounds`, à `gap` mm, bas aligné sur celui des objets présents.
    ABOVE : au-dessus de `existing_bounds`, à `gap` mm, gauche alignée sur celle des objets présents.
    Sans objets présents (`existing_bounds` None), RIGHT et ABOVE se comportent comme ADD."""
    if mode not in MODES:
        raise ValueError(f"placement inconnu : {mode}")
    x0, y0 = new_bounds[0], new_bounds[1]
    if existing_bounds is None or mode in (ADD, REPLACE):
        target = (margin_x, margin_y)
    elif mode == RIGHT:
        target = (existing_bounds[2] + gap, existing_bounds[1])
    else:
        target = (existing_bounds[0], existing_bounds[3] + gap)
    return target[0] - x0, target[1] - y0


def overscan_margin(enabled, mode_percent, distance_mm, percent, width_mm):
    """Marge à gauche (mm) qui laisse la place au surbalayage : 0 s'il est désactivé, sinon la distance
    fixe, ou le pourcentage de `width_mm` (largeur du dessin) en mode pourcentage."""
    if not enabled:
        return 0.0
    if mode_percent:
        return max(0.0, width_mm) * percent / 100.0
    return float(distance_mm)
