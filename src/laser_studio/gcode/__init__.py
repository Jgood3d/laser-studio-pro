"""Génération du G-Code, sans Qt : fonctions pures, testables sans fenêtre ni
machine. Les threads de controllers/workers.py ne font que les appeler.

- job.build_job_gcode : un job complet (image, calques vectoriels), d'après params.JobParams ;
- raster : gravure d'une image tramée ;
- vector : calques vectoriels (gravure remplie, découpe, marquage) ;
- test_matrix.build_test_matrix_gcode : matrice de test vitesse x puissance / passes ;
- calibration.bidir_test_gcode : motif de calibrage du décalage aller/retour.

Aucun module de ce paquet n'importe PyQt6 (vérifié par tests/test_gcode_package.py).
"""
from laser_studio.gcode.calibration import BIDIR_TEST_DEFAULT_OFFSETS, bidir_test_gcode
from laser_studio.gcode.common import GcodeResult
from laser_studio.gcode.job import build_job_gcode
from laser_studio.gcode.params import JobParams
from laser_studio.gcode.raster import image_origin
from laser_studio.gcode.test_matrix import MATRIX_CUT, MATRIX_ENGRAVE, build_test_matrix_gcode
from laser_studio.gcode.vector import build_vector_layers_gcode

__all__ = [
    "BIDIR_TEST_DEFAULT_OFFSETS",
    "GcodeResult",
    "JobParams",
    "MATRIX_CUT",
    "MATRIX_ENGRAVE",
    "bidir_test_gcode",
    "build_job_gcode",
    "build_test_matrix_gcode",
    "build_vector_layers_gcode",
    "image_origin",
]
