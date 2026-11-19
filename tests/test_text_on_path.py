"""Texte le long d'un tracé : position et rotation des lettres (sans Qt)."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from laser_studio.vector import text_on_path as top  # noqa: E402


def circle(radius, n=720, clockwise=False, cx=0.0, cy=0.0):
    """Cercle fermé (dernier point = premier), départ à 3 heures."""
    sign = -1.0 if clockwise else 1.0
    pts = [(cx + radius * math.cos(sign * 2 * math.pi * i / n),
            cy + radius * math.sin(sign * 2 * math.pi * i / n)) for i in range(n)]
    return pts + [pts[0]]


class OrientTests(unittest.TestCase):
    def test_closed_path_becomes_clockwise(self):
        ccw = circle(10, clockwise=False)
        cw = circle(10, clockwise=True)
        self.assertLess(top.signed_area(top.orient_path(ccw)[:-1]), 0)
        self.assertLess(top.signed_area(top.orient_path(cw)[:-1]), 0)

    def test_open_path_reads_left_to_right(self):
        pts = [(10.0, 0.0), (0.0, 0.0)]
        self.assertEqual(top.orient_path(pts), [(0.0, 0.0), (10.0, 0.0)])

    def test_vertical_open_path_reads_bottom_to_top(self):
        self.assertEqual(top.orient_path([(0.0, 5.0), (0.0, 0.0)]), [(0.0, 0.0), (0.0, 5.0)])

    def test_closed_detection(self):
        self.assertTrue(top.is_closed(circle(5)))
        self.assertFalse(top.is_closed([(0, 0), (5, 0), (5, 5)]))

    def test_default_center_is_top_of_closed_path_and_middle_of_open_path(self):
        pts = top.orient_path(circle(10))
        (x, y, rot), = top.path_placements([4.0], pts)
        self.assertAlmostEqual(x, 0.0, delta=0.02)
        self.assertAlmostEqual(y, 10.0, delta=0.02)
        self.assertAlmostEqual(rot, 0.0, delta=0.5)
        self.assertEqual(top.default_center_fraction([(0, 0), (10, 0)]), 0.5)


class PlacementTests(unittest.TestCase):
    def test_straight_path_places_letters_in_a_row(self):
        placed = top.path_placements([2.0, 2.0, 2.0], [(0.0, 0.0), (20.0, 0.0)])
        xs = [p[0] for p in placed]
        self.assertAlmostEqual(xs[1], 10.0, places=6)
        self.assertAlmostEqual(xs[1] - xs[0], 2.0, places=6)
        self.assertAlmostEqual(xs[2] - xs[1], 2.0, places=6)
        for _x, y, rot in placed:
            self.assertAlmostEqual(y, 0.0, places=9)
            self.assertAlmostEqual(rot, 0.0, places=9)

    def test_letter_spacing_widens_the_row(self):
        tight = top.path_placements([2.0, 2.0], [(0.0, 0.0), (20.0, 0.0)])
        loose = top.path_placements([2.0, 2.0], [(0.0, 0.0), (20.0, 0.0)], spacing_mm=1.0)
        self.assertAlmostEqual((loose[1][0] - loose[0][0]) - (tight[1][0] - tight[0][0]), 1.0, places=6)

    def test_sloped_path_rotates_letters(self):
        (x, y, rot), = top.path_placements([2.0], [(0.0, 0.0), (10.0, 10.0)])
        self.assertAlmostEqual(rot, 45.0, places=6)
        self.assertAlmostEqual(x, 5.0, places=6)
        self.assertAlmostEqual(y, 5.0, places=6)

    def test_closed_clockwise_circle_text_is_outside_and_reads_clockwise(self):
        pts = top.orient_path(circle(20))
        left, mid, right = top.path_placements([4.0, 4.0, 4.0], pts)
        self.assertLess(left[0], mid[0])
        self.assertLess(mid[0], right[0])
        self.assertGreater(left[2], 0)     # la lettre de gauche penche vers la gauche
        self.assertLess(right[2], 0)
        for x, y, _r in (left, mid, right):
            self.assertAlmostEqual(math.hypot(x, y), 20.0, delta=0.02)   # sur le cercle

    def test_reverse_puts_the_text_on_the_other_side(self):
        pts = [(0.0, 0.0), (20.0, 0.0)]
        (x, y, rot), = top.path_placements([2.0], pts, reverse=True)
        self.assertAlmostEqual(abs(rot), 180.0, places=6)    # à l'envers : lu de droite à gauche
        self.assertAlmostEqual(x, 10.0, places=6)

    def test_center_fraction_moves_the_text_along_the_path(self):
        (x, _y, _r), = top.path_placements([2.0], [(0.0, 0.0), (20.0, 0.0)], center_fraction=0.25)
        self.assertAlmostEqual(x, 5.0, places=6)

    def test_gap_moves_letters_toward_the_top_of_the_letters(self):
        (x, y, _r), = top.path_placements([2.0], [(0.0, 0.0), (20.0, 0.0)], gap_mm=3.0)
        self.assertAlmostEqual(y, 3.0, places=6)
        (x, y, _r), = top.path_placements([2.0], [(0.0, 0.0), (20.0, 0.0)], gap_mm=-3.0)
        self.assertAlmostEqual(y, -3.0, places=6)

    def test_text_longer_than_an_open_path_continues_straight(self):
        placed = top.path_placements([6.0, 6.0, 6.0], [(0.0, 0.0), (10.0, 0.0)])
        self.assertLess(placed[0][0], 0.0)
        self.assertGreater(placed[2][0], 10.0)
        for _x, y, rot in placed:
            self.assertAlmostEqual(y, 0.0, places=9)
            self.assertAlmostEqual(rot, 0.0, places=9)

    def test_closed_path_wraps_around(self):
        pts = top.orient_path(circle(5))
        length = top.path_length(pts)
        placed = top.path_placements([length / 4.0] * 5, pts)     # 1,25 tour : la lettre 5 recouvre la 1re
        self.assertAlmostEqual(math.hypot(placed[4][0], placed[4][1]), 5.0, delta=0.02)

    def test_invalid_path_is_refused(self):
        with self.assertRaises(ValueError):
            top.path_placements([1.0], [(0.0, 0.0)])
        with self.assertRaises(ValueError):
            top.path_placements([1.0], [(1.0, 1.0), (1.0, 1.0)])


class HelperTests(unittest.TestCase):
    def test_relative_and_scaled_points(self):
        self.assertEqual(top.relative_points([(5.0, 7.0), (6.0, 9.0)], (5.0, 7.0)), [(0.0, 0.0), (1.0, 2.0)])
        self.assertEqual(top.scaled_points([(1.0, 2.0)], 2.0, 3.0), [(2.0, 6.0)])


if __name__ == "__main__":
    unittest.main()
