"""Estimation rapide du temps de gravure (estimate_job_time) : le surbalayage est compté comme à la
génération — désactivé, distance fixe ou pourcentage de la largeur."""
import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import gcode_generation_mixin as ggm
except ImportError:  # PyQt6 manquant
    ggm = None


class _Widget:
    def __init__(self, value=0.0, checked=False, index=0):
        self.v, self.checked, self.index = value, checked, index

    def value(self):
        return self.v

    def isChecked(self):
        return self.checked

    def currentIndex(self):
        return self.index


@unittest.skipIf(ggm is None, "gcode_generation_mixin non importable ici")
class TimeEstimateOverscanTests(unittest.TestCase):
    def estimate(self, enabled, mode_index=0, dist=2.5, pct=5.0, array=None):
        class App(ggm.GcodeGenerationMixin):
            pass
        app = App()
        app.processed_array = np.zeros((10, 100), np.uint8) if array is None else array
        # 10 lignes de 100 mm à 600 mm/min : 100 s sans surbalayage.
        app.spin_w, app.spin_h, app.spin_lmm = _Widget(100.0), _Widget(10.0), _Widget(1.0)
        app.spin_speed_engrave = _Widget(600)
        app.chk_overscan = _Widget(checked=enabled)
        app.combo_overscan_mode = _Widget(index=mode_index)       # 0 : distance fixe, 1 : pourcentage
        app.spin_overscan_dist, app.spin_overscan_pct = _Widget(dist), _Widget(pct)
        app.loaded_svg_path = None
        with mock.patch.object(ggm.QMessageBox, "information") as box:
            app.estimate_job_time()
        return app, box.call_args[0][2]

    def test_overscan_disabled(self):
        app, msg = self.estimate(False)
        self.assertIn(app._format_duration(100.0), msg)

    def test_fixed_distance_overscan_is_counted(self):
        app, msg = self.estimate(True, 0, dist=5.0)              # 10 x (100 + 2 x 5) mm = 110 s
        self.assertIn(app._format_duration(110.0), msg)

    def test_percentage_overscan_is_counted(self):
        app, msg = self.estimate(True, 1, pct=10.0)              # 10 % de 100 mm de chaque côté : 120 s
        self.assertIn(app._format_duration(120.0), msg)

    def test_overscan_is_added_to_trimmed_rows_only(self):
        arr = np.full((10, 100), 255, np.uint8)
        arr[[2, 7], 20:50] = 0                                     # 2 lignes de 30 mm, 8 lignes vides
        app, msg = self.estimate(True, 0, dist=5.0, array=arr)    # 2 x (30 + 2 x 5) mm = 8 s
        self.assertIn(app._format_duration(8.0), msg)


if __name__ == "__main__":
    unittest.main()
