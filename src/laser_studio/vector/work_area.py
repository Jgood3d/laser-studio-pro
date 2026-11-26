"""Zone de travail de l'éditeur vectoriel, sans Qt : taille du plateau, échelle de la scène, passage du repère
machine (mm, origine en bas à gauche, Y vers le haut) au repère de la scène Qt (pixels, Y vers le bas), grille
graduée et zoom qui fait tenir un contenu dans la fenêtre. Le canevas (ui/vector_editor) dessine d'après elle.

    area = WorkArea(300.0, 200.0)
    area.to_scene(10.0, 5.0)        # (40.0, 780.0)
    area.to_mm(40.0, 780.0)         # (10.0, 5.0)
    area.grid().major_x             # (0.0, 20.0, 40.0, …, 300.0)
    fit_scale(120, 80, 900, 700, margin=60, max_scale=6.0)
"""
from dataclasses import dataclass

# Pixels de scène par millimètre : l'échelle de travail du canevas (le zoom de la vue s'y ajoute).
SCENE_PX_PER_MM = 4.0
# Pas des graduations principales selon le plus grand côté du plateau (mm) : (côté jusqu'à, pas).
GRID_STEPS = ((50, 5), (150, 10), (400, 20), (1000, 50))
GRID_STEP_MAX = 100
# Graduations secondaires (sans chiffre) entre deux graduations principales.
GRID_MINOR_DIVISIONS = 4
EPSILON_MM = 1e-6


def grid_step(span_mm):
    """Pas des graduations principales (mm) pour un plateau dont le plus grand côté mesure `span_mm`."""
    return next((step for limit, step in GRID_STEPS if span_mm <= limit), GRID_STEP_MAX)


def _marks(first, end, step, include_end):
    """Positions de `first` à `end` par pas de `step`, cumulées comme le canevas les a toujours tracées (même
    arrondi flottant) ; `end` compris si `include_end`."""
    marks, value = [], first
    while (value <= end + EPSILON_MM) if include_end else (value < end - EPSILON_MM):
        marks.append(value)
        value += step
    return tuple(marks)


@dataclass(frozen=True)
class Grid:
    """Graduations de la grille, en mm : principales (chiffrées, 0 et le bord compris) et secondaires."""
    step: float
    major_x: tuple
    major_y: tuple
    minor_x: tuple
    minor_y: tuple


@dataclass(frozen=True)
class WorkArea:
    """Plateau de `width_mm` × `height_mm`, à `px_per_mm` pixels de scène par mm."""
    width_mm: float = 100.0
    height_mm: float = 100.0
    px_per_mm: float = SCENE_PX_PER_MM

    @property
    def width_px(self):
        return self.width_mm * self.px_per_mm

    @property
    def height_px(self):
        return self.height_mm * self.px_per_mm

    def to_scene(self, x_mm, y_mm):
        """Point machine (mm, Y vers le haut) -> point de la scène (px, Y vers le bas)."""
        s = self.px_per_mm
        return x_mm * s, self.height_mm * s - y_mm * s

    def to_mm(self, x_px, y_px):
        """Point de la scène (px, Y vers le bas) -> point machine (mm, Y vers le haut)."""
        s = self.px_per_mm
        return x_px / s, (self.height_mm * s - y_px) / s

    def grid(self):
        """Graduations du plateau (voir grid_step)."""
        step = grid_step(max(self.width_mm, self.height_mm))
        minor = step / GRID_MINOR_DIVISIONS
        return Grid(step=step,
                    major_x=_marks(0.0, self.width_mm, step, True), major_y=_marks(0.0, self.height_mm, step, True),
                    minor_x=_marks(minor, self.width_mm, minor, False),
                    minor_y=_marks(minor, self.height_mm, minor, False))


def fit_scale(content_w, content_h, viewport_w, viewport_h, margin=60, max_scale=6.0):
    """Zoom qui fait tenir un contenu de `content_w` × `content_h` (px de scène) dans une fenêtre de
    `viewport_w` × `viewport_h` avec `margin` px de marge autour, plafonné à `max_scale` (un tout petit objet
    n'est pas agrandi démesurément) ; None tant que la fenêtre est plus petite que ses marges (pas encore
    affichée à sa taille)."""
    if viewport_w <= 2 * margin or viewport_h <= 2 * margin:
        return None
    return min((viewport_w - 2 * margin) / max(content_w, 1e-6),
               (viewport_h - 2 * margin) / max(content_h, 1e-6),
               max_scale)
