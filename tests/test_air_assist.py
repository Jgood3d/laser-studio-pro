"""Air assist par calque : M8 au début d'un calque qui le demande, M9 dès qu'un calque ne le demande plus et en
fin de calques ; idem pour la gravure de l'image (calque de gravure)."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.gcode import JobParams, build_job_gcode  # noqa: E402
from laser_studio.gcode.vector import build_vector_layers_gcode  # noqa: E402
from laser_studio.models.layers import LaserLayer  # noqa: E402

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]


def _data(name, air):
    layer = {"name": name, "mode": "cut", "speed": 300, "power": 40.0, "passes": 1, "line_interval": 0.1,
             "air": air}
    return {"layer": layer, "polygons": [SQUARE], "polygon_groups": [[SQUARE]]}


def _air_lines(gcode):
    return [line.split(";")[0].strip() for line in gcode if line.startswith(("M8", "M9", "; --- CALQUE"))]


class AirAssistTests(unittest.TestCase):
    def test_air_follows_each_layer(self):
        gcode, _t, _p = build_vector_layers_gcode(
            {"a": _data("A", True), "b": _data("B", True), "c": _data("C", False), "d": _data("D", True)},
            0.0, 0.0, 100.0, "M4", 1000, safe_cut_order=False)
        self.assertEqual(_air_lines(gcode), ["", "M8", "", "", "M9", "", "M8", "M9"])   # "" : en-tête du calque

    def test_no_air_no_m8(self):
        gcode, _t, _p = build_vector_layers_gcode({"a": _data("A", False)}, 0.0, 0.0, 100.0, "M4", 1000)
        self.assertFalse([line for line in gcode if line.startswith(("M8", "M9"))])

    def test_image_with_air_on_the_engrave_layer(self):
        params = JobParams(width_mm=4, height_mm=4, origin_pos="bottom_left", offset_x=0, offset_y=0,
                           speed_engrave=1000, power_engrave=50, laser_cmd="M4", s_max=1000, image_air=True)
        lines = build_job_gcode(np.zeros((4, 4), np.uint8), params).gcode.split("\n")
        start = lines.index("M8 ; air assist")
        self.assertLess(start, lines.index("M9"))

    def test_layer_keeps_its_air_setting(self):
        self.assertFalse(LaserLayer().air)                          # ancien projet : sans soufflage
        self.assertTrue(LaserLayer.from_dict(LaserLayer(air=True).to_dict()).air)


if __name__ == "__main__":
    unittest.main()
