"""Durée d'un G-Code calculée comme GRBL planifie ses déplacements (gcode/timing.py) : accélération,
jonctions, tampon de planification, G0, pauses, limites par axe, réglages $$."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.gcode.common import TIME_MARGIN  # noqa: E402
from laser_studio.gcode.timing import (  # noqa: E402
    MachineLimits, estimate_seconds, job_duration, straight_lines_seconds,
)

LIMITS = MachineLimits(max_rate_x=6000, max_rate_y=6000, accel_x=500, accel_y=500, junction_deviation=0.01)


class EstimateTests(unittest.TestCase):
    def test_a_slow_line_is_almost_distance_over_speed(self):
        self.assertAlmostEqual(estimate_seconds("G1 X100 F600", LIMITS), 10.0, delta=0.05)

    def test_a_fast_line_pays_its_acceleration(self):
        # 100 mm/s, 500 mm/s² : 0,2 s pour accélérer, 0,2 s pour freiner, 10 mm de chaque côté.
        self.assertAlmostEqual(estimate_seconds("G1 X100 F6000", LIMITS), 1.2, places=3)

    def test_rapids_go_at_the_maximum_rate(self):
        self.assertAlmostEqual(estimate_seconds("G0 X100", LIMITS), estimate_seconds("G1 X100 F6000", LIMITS))
        self.assertGreater(estimate_seconds("G0 X100\nG0 X0", LIMITS), estimate_seconds("G0 X200", LIMITS))  # demi-tour

    def test_a_straight_line_cut_in_pieces_does_not_slow_down(self):
        pieces = "F1500\n" + "\n".join(f"G1 X{(i + 1) * 0.5:.1f} S{(i % 2) * 500}" for i in range(200))
        self.assertAlmostEqual(estimate_seconds(pieces, LIMITS), estimate_seconds("G1 X100 F1500", LIMITS), delta=0.01)

    def test_short_lookahead_limits_speed_on_fine_rasters(self):
        fine = "F6000\n" + "\n".join(f"G1 X{(i + 1) * 0.1:.1f} S{(i % 2) * 500}" for i in range(1000))
        self.assertGreater(estimate_seconds(fine, LIMITS), 2.0)                       # 1,2 s sans tampon limité
        wide = MachineLimits(**{**LIMITS.to_dict(), "planner_blocks": 10000})
        self.assertAlmostEqual(estimate_seconds(fine, wide), 1.2, delta=0.02)

    def test_corners_slow_down_with_the_junction_deviation(self):
        square = "F3000\nG1 X50\nG1 Y50\nG1 X0\nG1 Y0"
        tight = MachineLimits(**{**LIMITS.to_dict(), "junction_deviation": 0.001})
        loose = MachineLimits(**{**LIMITS.to_dict(), "junction_deviation": 0.5})
        self.assertGreater(estimate_seconds(square, tight), estimate_seconds(square, loose))

    def test_axis_limits_dwell_and_relative_moves(self):
        slow_y = MachineLimits(**{**LIMITS.to_dict(), "max_rate_y": 600})
        self.assertAlmostEqual(estimate_seconds("G0 Y10", slow_y), 1.0, delta=0.05)
        self.assertAlmostEqual(estimate_seconds("G4 P2\nG1 X10 F600", LIMITS), 3.0, delta=0.05)
        self.assertAlmostEqual(estimate_seconds("G91\nG1 X10 F600\nG1 X10", LIMITS), 2.0, delta=0.05)
        self.assertEqual(estimate_seconds("; rien\n$H\nM5", LIMITS), 0.0)


class SettingsAndFallbackTests(unittest.TestCase):
    def test_limits_come_from_grbl_settings_then_machine_page(self):
        limits = MachineLimits.from_grbl_settings({"$110": "8000", "$121": "250", "$11": "abc"}, 3000, 800)
        self.assertEqual((limits.max_rate_x, limits.max_rate_y, limits.accel_x, limits.accel_y),
                         (8000.0, 3000.0, 800.0, 250.0))
        self.assertEqual(limits.junction_deviation, 0.01)                             # illisible : défaut
        self.assertEqual(MachineLimits.from_grbl_settings(None).max_rate_x, 6000.0)

    def test_without_limits_the_old_margin_is_kept(self):
        self.assertAlmostEqual(job_duration("G1 X100 F600", {}, 10.0), 10.0 * TIME_MARGIN)
        self.assertAlmostEqual(job_duration("G1 X100 F600", {"machine_limits": LIMITS.to_dict()}, 0.0), 10.0,
                               delta=0.05)

    def test_quick_estimate_matches_the_planner_for_isolated_lines(self):
        lines = [50.0, 2.0, 120.0]
        gcode = "\n".join(f"G1 X{length} F3000\nG4 P0\nG1 X0" for length in lines)   # aller-retour, arrêt à chaque bout
        planner = estimate_seconds(gcode, LIMITS)
        self.assertAlmostEqual(straight_lines_seconds(lines * 2, 3000, 500), planner, delta=0.02)


if __name__ == "__main__":
    unittest.main()
