"""Paramètres d'un job : un objet figé à champs nommés plutôt qu'un dictionnaire à clés texte. Un nom mal
écrit ou disparu (l'ancienne « découpe SVG ») lève une erreur au lieu d'être ignoré en silence, et chaque
réglage a un seul défaut, ici. Sans Qt.

    params = JobParams(width_mm=100, height_mm=80, origin_pos=ORIGIN_BOTTOM_LEFT, offset_x=0, offset_y=0,
                       speed_engrave=3000, power_engrave=40, laser_cmd="M4", s_max=1000)
    smaller = dataclasses.replace(params, width_mm=50)

Construits par JobController.build_params ; lus par gcode.job, gcode.raster et le cadrage du graveur.
"""
from dataclasses import dataclass
from typing import Optional

from laser_studio.core.constants import ORIGIN_CENTER
from laser_studio.gcode.common import OVERSCAN_FIXED, overscan_distance


@dataclass(frozen=True)
class JobParams:
    # Taille et position du job sur le plateau (mm).
    width_mm: float
    height_mm: float
    origin_pos: str                 # ORIGIN_BOTTOM_LEFT ou ORIGIN_CENTER (le décalage désigne alors le centre)
    offset_x: float
    offset_y: float
    # Gravure de l'image : celle de son calque de gravure.
    speed_engrave: float            # mm/min
    power_engrave: float            # %
    laser_cmd: str                  # commande de Configuration GRBL : "M4" (dynamique) ou "M3"
    s_max: int                      # S-Max de GRBL ($30)
    image_laser_cmd: Optional[str] = None     # commande du calque de gravure ; None : laser_cmd
    image_overscan: Optional[bool] = None     # surbalayage du calque de gravure ; None : enable_overscan
    algo: str = ""                  # algorithme de tramage (raster.GRAYSCALE_ALGO : puissance selon le gris)
    # En-tête et fin du job.
    homing: bool = False
    start_gcode: str = ""
    end_gcode: str = ""
    # Graver avant de découper ; intérieurs avant extérieurs (vector/order.py).
    safe_cut_order: bool = True
    # Limites de la machine (gcode.timing.MachineLimits en dictionnaire) pour la durée ; None : estimation simple.
    machine_limits: Optional[dict] = None
    # Surbalayage et décalage des lignes retour (Configuration GRBL).
    enable_overscan: bool = False
    overscan_mode: str = OVERSCAN_FIXED
    overscan_dist: float = 2.5      # mm, mode distance fixe
    overscan_pct: float = 5.0       # % de la largeur gravée, mode pourcentage
    scan_offset_mm: float = 0.0

    @property
    def image_cmd(self):
        """Commande laser de la gravure d'image."""
        return self.image_laser_cmd or self.laser_cmd

    @property
    def image_overscan_enabled(self):
        """Surbalayage de la gravure d'image : celui de son calque, sinon le réglage global."""
        return self.enable_overscan if self.image_overscan is None else self.image_overscan

    def overscan_for(self, width_mm):
        """Distance de surbalayage (mm) pour une largeur gravée `width_mm`, qu'il soit activé ou non."""
        return overscan_distance(self.overscan_mode, self.overscan_pct, self.overscan_dist, width_mm)

    def vector_origin(self):
        """Origine des calques vectoriels sur le plateau (coin bas-gauche du job, sans marge de surbalayage) :
        le décalage, ou le décalage moins la demi-taille en origine « Centre »."""
        if self.origin_pos == ORIGIN_CENTER:
            return self.offset_x - self.width_mm / 2.0, self.offset_y - self.height_mm / 2.0
        return self.offset_x, self.offset_y
