"""Texte sur un arc : position et rotation des lettres (sans Qt)."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from laser_studio.vector import text_on_arc as toa  # noqa: E402


class PlacementTests(unittest.TestCase):
    def test_single_letter_outside_sits_on_top_unrotated(self):
        (x, y, rot), = toa.arc_placements([5.0], 20.0)
        self.assertAlmostEqual(x, 0.0, places=9)
        self.assertAlmostEqual(y, 20.0, places=9)
        self.assertAlmostEqual(rot, 0.0, places=9)

    def test_single_letter_inside_sits_at_bottom_unrotated(self):
        (x, y, rot), = toa.arc_placements([5.0], 20.0, inside=True)
        self.assertAlmostEqual(x, 0.0, places=9)
        self.assertAlmostEqual(y, -20.0, places=9)
        self.assertAlmostEqual(rot, 0.0, places=9)

    def test_outside_text_reads_left_to_right_and_tilts_clockwise(self):
        left, middle, right = toa.arc_placements([4.0, 4.0, 4.0], 30.0)
        self.assertLess(left[0], middle[0])
        self.assertLess(middle[0], right[0])
        self.assertGreater(left[2], 0)       # la lettre de gauche penche vers la gauche
        self.assertAlmostEqual(middle[2], 0.0, places=9)
        self.assertLess(right[2], 0)         # celle de droite penche vers la droite

    def test_inside_text_reads_left_to_right_at_the_bottom(self):
        left, middle, right = toa.arc_placements([4.0, 4.0, 4.0], 30.0, inside=True)
        self.assertLess(left[0], right[0])
        self.assertLess(left[2], 0)
        self.assertGreater(right[2], 0)

    def test_text_is_centered_on_the_requested_angle(self):
        # Deux lettres identiques : leurs angles sont symétriques autour de l'angle demandé.
        first, second = toa.arc_placements([4.0, 4.0], 25.0, center_deg=180.0)
        angle_first = math.degrees(math.atan2(first[1], first[0])) % 360
        angle_second = math.degrees(math.atan2(second[1], second[0])) % 360
        self.assertAlmostEqual((angle_first + angle_second) / 2.0, 180.0, places=9)
        self.assertGreater(angle_first, angle_second)   # sens horaire : l'angle diminue

    def test_every_letter_stays_on_the_circle(self):
        for inside in (False, True):
            for x, y, _ in toa.arc_placements([2.0, 7.0, 3.5], 18.0, inside=inside, spacing_mm=1.0):
                self.assertAlmostEqual(math.hypot(x, y), 18.0, places=9)

    def test_gap_between_letters_follows_their_widths_and_spacing(self):
        radius = 40.0
        a, b = toa.arc_placements([6.0, 10.0], radius, spacing_mm=2.0)
        angle_a = math.atan2(a[1], a[0])
        angle_b = math.atan2(b[1], b[0])
        arc_between = (angle_a - angle_b) * radius       # de gauche à droite, on tourne dans le sens horaire
        self.assertAlmostEqual(arc_between, 6.0 / 2 + 2.0 + 10.0 / 2, places=9)

    def test_span_and_length(self):
        self.assertAlmostEqual(toa.text_length([3.0, 4.0, 5.0], 1.0), 14.0)
        self.assertAlmostEqual(toa.arc_span_deg([math.pi], 1.0), 180.0)
        self.assertEqual(toa.text_length([]), 0.0)
        self.assertEqual(toa.arc_placements([], 10.0), [])

    def test_invalid_radius(self):
        for radius in (0.0, -5.0):
            with self.assertRaises(ValueError):
                toa.arc_placements([3.0], radius)
            with self.assertRaises(ValueError):
                toa.arc_span_deg([3.0], radius)


if __name__ == "__main__":
    unittest.main()
