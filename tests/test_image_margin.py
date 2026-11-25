"""Marge de l'image à graver (gcode.raster.image_origin) : la distance de surbalayage, en X seulement, quand
il est actif ; avec un décalage du job à 0, le surbalayage ne fait plus partir la tête en X négatif."""
import os
import re
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from laser_studio import gcode
    from laser_studio.gcode.common import OVERSCAN_PERCENT
    from laser_studio.controllers import workers
except ImportError:  # dépendance manquante (PyQt6, svg.path...)
    gcode = workers = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")


class _Params(dict):
    def __missing__(self, key):
        return ""


def _params(**kw):
    p = _Params(width_mm=20.0, height_mm=10.0, origin_pos="bottom_left", offset_x=0.0, offset_y=0.0,
                power_engrave=100.0, speed_engrave=1000, enable_overscan=True, overscan_mode="mm",
                overscan_dist=2.5, laser_cmd="M4", s_max=1000, algo="Seuil Simple (Binaire)", enable_cut=False)
    p.update(kw)
    return p


def _engraving_moves(gcode):
    """X et Y des déplacements G0/G1 de la gravure (avant le M5 final et le retour à l'origine)."""
    xs, ys = [], []
    for line in gcode[:gcode.rindex("M5")].splitlines():
        line = line.split(";")[0].strip()
        if re.match(r"G[01]\b", line) or line[:1] in ("X", "Y"):        # G0 / G1, ou mouvement modal
            xs += [float(v) for v in re.findall(r"X(-?[\d.]+)", line)]
            ys += [float(v) for v in re.findall(r"Y(-?[\d.]+)", line)]
    return xs, ys


@unittest.skipIf(workers is None, "workers non importable ici")
class ImageMarginTests(unittest.TestCase):
    def test_image_origin(self):
        m = 2.5                                            # distance de surbalayage de _params
        self.assertEqual(gcode.image_origin(_params()), (m, 0.0))
        self.assertEqual(gcode.image_origin(_params(offset_x=5.0, offset_y=-3.0)), (5.0 + m, -3.0))
        # Surbalayage désactivé (réglage global ou calque de gravure) : aucune marge.
        self.assertEqual(gcode.image_origin(_params(enable_overscan=False)), (0.0, 0.0))
        self.assertEqual(gcode.image_origin(_params(image_overscan=False)), (0.0, 0.0))
        # En pourcentage : de la largeur de l'image (20 mm).
        self.assertEqual(gcode.image_origin(_params(overscan_mode=OVERSCAN_PERCENT, overscan_pct=10.0)), (2.0, 0.0))
        # Taille et position seules (sans réglage du surbalayage) : aucune marge.
        self.assertEqual(gcode.image_origin({"origin_pos": "bottom_left", "offset_x": 1.0, "offset_y": 2.0,
                                             "width_mm": 20.0, "height_mm": 10.0}), (1.0, 2.0))
        # Origine « Centre » : le décalage désigne le centre de l'image, sans marge.
        self.assertEqual(gcode.image_origin(_params(origin_pos="center", offset_x=50.0, offset_y=40.0)),
                         (40.0, 35.0))

    def test_overscan_stays_positive_with_a_zero_offset(self):
        worker = workers.AdvancedGCodeWorker(np.zeros((10, 20), dtype=np.uint8), None, _params(), {})
        out = {}
        worker.finished.connect(lambda gcode, *_: out.update(gcode=gcode))
        worker.error.connect(lambda msg: out.update(error=msg))
        worker.run()
        self.assertNotIn("error", out)
        xs, ys = _engraving_moves(out["gcode"])
        self.assertAlmostEqual(min(xs), 0.0)              # départ du surbalayage, au bord du plateau
        self.assertAlmostEqual(max(xs), 2.5 + 20.0 + 2.5)
        self.assertAlmostEqual(min(ys), 0.0)

    def test_every_image_position_uses_the_margin(self):
        def source(name):
            with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                return f.read()
        gen = source(os.path.join("controllers", "job.py"))
        check = gen[gen.index("if params['image_overscan'] and processed_array is not None"):]
        self.assertIn("image_origin(params)", check[:check.index("self.dialogs.error")])    # contrôle
        frame = source(os.path.join("controllers", "engraver.py"))
        frame = frame[frame.index("    def frame(self):"):]
        self.assertIn("image_origin(", frame[:frame.index("commands.frame_commands(")])  # cadrage
        work = source(os.path.join("gcode", "job.py"))
        # Calques vectoriels : décalage du job seul (leurs objets ont déjà leur marge à l'import).
        self.assertIn("vector_layers_data, base_offset_x, base_offset_y, h_mm", work)


if __name__ == "__main__":
    unittest.main()
