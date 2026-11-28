"""Estimation rapide du temps de gravure (JobController.estimate) : le surbalayage est compté comme à la
génération — désactivé, distance fixe ou pourcentage de la largeur."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from laser_studio.controllers.job import estimate_duration_text
    from job_fakes import make_job
except ImportError:  # PyQt6 manquant
    make_job = None


@unittest.skipIf(make_job is None, "PyQt6 non importable ici")
class TimeEstimateOverscanTests(unittest.TestCase):
    def estimate(self, enabled, mode_index=0, dist=2.5, pct=5.0, array=None):
        arr = np.zeros((10, 100), np.uint8) if array is None else array
        # 10 lignes de 100 mm à 600 mm/min : 100 s sans surbalayage.
        job, dialogs = make_job(image=arr, geometry_kw={'width_mm': 100.0, 'height_mm': 10.0})
        job.layers.update(job.layers.engrave_layer().id, speed=600)
        job.grbl.update(overscan_enabled=enabled, overscan_mode=mode_index,   # 0 : distance fixe, 1 : %
                        overscan_dist_mm=dist, overscan_pct=pct)
        job.estimate()
        return dialogs.last_text("info")

    def test_overscan_disabled(self):
        self.assertIn(estimate_duration_text(100.0), self.estimate(False))

    def test_fixed_distance_overscan_is_counted(self):
        msg = self.estimate(True, 0, dist=5.0)              # 10 x (100 + 2 x 5) mm = 110 s
        self.assertIn(estimate_duration_text(110.0), msg)

    def test_percentage_overscan_is_counted(self):
        msg = self.estimate(True, 1, pct=10.0)              # 10 % de 100 mm de chaque côté : 120 s
        self.assertIn(estimate_duration_text(120.0), msg)

    def test_overscan_is_added_to_trimmed_rows_only(self):
        arr = np.full((10, 100), 255, np.uint8)
        arr[[2, 7], 20:50] = 0                                     # 2 lignes de 30 mm, 8 lignes vides
        msg = self.estimate(True, 0, dist=5.0, array=arr)         # 2 x (30 + 2 x 5) mm = 8 s
        self.assertIn(estimate_duration_text(8.0), msg)

    def test_nothing_to_estimate(self):
        job, dialogs = make_job()
        job.estimate()
        self.assertEqual(dialogs.kinds(), ["info"])


if __name__ == "__main__":
    unittest.main()
