"""Marge de l'image à graver (workers.IMAGE_MARGIN_MM) : avec un décalage du job à 0, le surbalayage
ne fait plus partir la tête en X négatif."""
import os
import re
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from laser_studio import workers
except ImportError:  # dépendance manquante (PyQt6, svg.path...)
    workers = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")


class _Params(dict):
    def __missing__(self, key):
        return ""


def _params(**kw):
    p = _Params(width_mm=20.0, height_mm=10.0, origin_pos="Bas-Gauche (0,0)", offset_x=0.0, offset_y=0.0,
                power_engrave=100.0, speed_engrave=1000, enable_overscan=True, overscan_mode="mm",
                overscan_dist=2.5, laser_cmd="M4", s_max=1000, algo="Seuil Simple (Binaire)", enable_cut=False)
    p.update(kw)
    return p


def _engraving_moves(gcode):
    """X et Y des déplacements G0/G1 de la gravure (avant le M5 final et le retour à l'origine)."""
    xs, ys = [], []
    for line in gcode[:gcode.rindex("M5")].splitlines():
        line = line.split(";")[0]
        if re.match(r"G[01]\b", line):
            xs += [float(v) for v in re.findall(r"X(-?[\d.]+)", line)]
            ys += [float(v) for v in re.findall(r"Y(-?[\d.]+)", line)]
    return xs, ys


@unittest.skipIf(workers is None, "workers non importable ici")
class ImageMarginTests(unittest.TestCase):
    def test_image_origin(self):
        m = workers.IMAGE_MARGIN_MM
        self.assertEqual(m, 10.0)                          # même marge qu'à l'import d'un SVG/DXF
        self.assertEqual(workers.image_origin(_params()), (m, m))
        self.assertEqual(workers.image_origin(_params(offset_x=5.0, offset_y=-3.0)), (5.0 + m, -3.0 + m))
        # Origine « Centre » : le décalage désigne le centre de l'image, sans marge.
        self.assertEqual(workers.image_origin(_params(origin_pos="Centre", offset_x=50.0, offset_y=40.0)),
                         (40.0, 35.0))

    def test_overscan_stays_positive_with_a_zero_offset(self):
        worker = workers.AdvancedGCodeWorker(np.zeros((10, 20), dtype=np.uint8), None, _params(), {})
        out = {}
        worker.finished.connect(lambda gcode, *_: out.update(gcode=gcode))
        worker.error.connect(lambda msg: out.update(error=msg))
        worker.run()
        self.assertNotIn("error", out)
        xs, ys = _engraving_moves(out["gcode"])
        self.assertAlmostEqual(min(xs), 10.0 - 2.5)       # départ du surbalayage
        self.assertAlmostEqual(max(xs), 10.0 + 20.0 + 2.5)
        self.assertAlmostEqual(min(ys), 10.0)

    def test_every_image_position_uses_the_margin(self):
        def source(name):
            return open(os.path.join(ROOT, name), encoding="utf-8").read()
        gen = source("gcode_generation_mixin.py")
        check = gen[gen.index("if params['enable_overscan'] and self.processed_array is not None"):]
        self.assertIn("image_origin(params)", check[:check.index("QMessageBox.critical")])  # contrôle
        frame = source("laser_control_mixin.py")
        frame = frame[frame.index("def run_frame"):]
        self.assertIn("image_origin(", frame[:frame.index("cmds = [")])                    # cadrage
        work = source("workers.py")
        # Calques vectoriels : décalage du job seul (leurs objets ont déjà leur marge à l'import).
        self.assertIn("self.vector_layers_data, base_offset_x, base_offset_y, h_mm", work)


if __name__ == "__main__":
    unittest.main()
