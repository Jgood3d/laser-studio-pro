"""Lecture de G-Code des tests (gcode_reader.burn_segments)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcode_reader import burn_segments  # noqa: E402


class BurnSegmentsTests(unittest.TestCase):
    def test_g1_with_laser_on_and_power_is_burned(self):
        gcode = "G0 X0 Y0\nM4 S800\nG1 X20 Y0 F1000\nM4 S0\nG0 X20 Y5\n"
        self.assertEqual(burn_segments(gcode), [(0.0, 0.0, 20.0, 800.0)])

    def test_moves_without_power_or_laser_are_not_burned(self):
        gcode = (
            "M4 S0\nG1 X10 Y0\n"  # puissance nulle
            "M5\nS500\nG1 X20 Y0\n"  # laser éteint
            "M3\nG0 X30 Y0\n"  # déplacement rapide
        )
        self.assertEqual(burn_segments(gcode), [])

    def test_power_on_the_g1_line_and_modal_motion(self):
        # Le premier G1 va en diagonale (0, 0) -> (5, 2) : pas rendu ; le
        # « X9 » suivant reste un G1 (modal), horizontal, à la puissance 300.
        gcode = "M3\nG1 X5 Y2 S300\nX9\n"
        self.assertEqual(burn_segments(gcode), [(2.0, 5.0, 9.0, 300.0)])

    def test_comments_are_ignored(self):
        gcode = "M4 S100 ; allume\nG1 X3 (gravure) Y0\n"
        self.assertEqual(burn_segments(gcode), [(0.0, 0.0, 3.0, 100.0)])


if __name__ == "__main__":
    unittest.main()
