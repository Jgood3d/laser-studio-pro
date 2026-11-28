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


class InsideReadabilityTests(unittest.TestCase):
    """Texte de l'autre côté du trait : lisible à l'endroit en bas du contour, à l'envers en haut."""

    def _rotation_at(self, inside, center):
        pts = top.orient_path(circle(20))
        spots = top.path_placements([2.0, 2.0, 2.0], pts, center, 0.0, inside)
        return spots[1][2]

    def test_default_center_inside_is_bottom(self):
        pts = top.orient_path(circle(20))
        for inside, expected_y in ((False, 20.0), (True, -20.0)):
            f = top.default_center_fraction(pts, inside)
            x, y = top._locate(pts, top._cumulative(pts), True, f * top.path_length(pts))
            self.assertAlmostEqual(y, expected_y, delta=0.1)
            self.assertAlmostEqual(x, 0.0, delta=0.5)

    def test_inside_text_upright_at_bottom(self):
        pts = top.orient_path(circle(20))
        rot = self._rotation_at(True, top.default_center_fraction(pts, True))
        self.assertAlmostEqual(abs(((rot + 180) % 360) - 180), 0.0, delta=1.0)

    def test_inside_text_upside_down_at_top(self):
        pts = top.orient_path(circle(20))
        rot = self._rotation_at(True, top.default_center_fraction(pts, False))
        self.assertAlmostEqual(abs(rot), 180.0, delta=1.0)

    def test_outside_default_unchanged(self):
        pts = top.orient_path(circle(20))
        self.assertEqual(top.default_center_fraction(pts), top.default_center_fraction(pts, False))


class SideTests(unittest.TestCase):
    """Placement « en haut / en bas / à gauche / à droite »."""

    def _where(self, pts, side):
        f = top.side_center_fraction(pts, side)
        return top._locate(pts, top._cumulative(pts), top.is_closed(pts), f * top.path_length(pts))

    def test_circle_sides(self):
        for clockwise in (True, False):
            pts = top.orient_path(circle(20, clockwise=clockwise))
            for side, (ex, ey) in {"top": (0, 20), "bottom": (0, -20), "left": (-20, 0), "right": (20, 0)}.items():
                x, y = self._where(pts, side)
                self.assertAlmostEqual(x, ex, delta=0.3, msg=side)
                self.assertAlmostEqual(y, ey, delta=0.3, msg=side)

    def test_flat_side_straddling_start(self):
        # Carré dont le départ est au milieu du côté droit : la série « droite » est à cheval sur 0.
        pts = [(10, 0), (10, -10), (-10, -10), (-10, 10), (10, 10), (10, 0)]
        pts = top.orient_path(pts)
        x, y = self._where(pts, "right")
        self.assertAlmostEqual(x, 10, delta=1e-6)
        self.assertAlmostEqual(y, 0, delta=1e-6)

    def test_place_for_fraction(self):
        pts = top.orient_path(circle(20))
        for side in top.SIDES:
            self.assertEqual(top.place_for_fraction(pts, top.side_center_fraction(pts, side)), side)
        self.assertIsNone(top.place_for_fraction(pts, top.side_center_fraction(pts, "top") + 0.05))

    def test_open_path_side(self):
        pts = [(0.0, 0.0), (10.0, 5.0), (20.0, 0.0)]
        self.assertAlmostEqual(top.side_center_fraction(pts, "top"), 0.5, delta=0.01)
        self.assertEqual(top.side_center_fraction(pts, "left"), 0.0)
        self.assertEqual(top.side_center_fraction(pts, "right"), 1.0)

    def test_unknown_side(self):
        with self.assertRaises(ValueError):
            top.side_center_fraction(circle(5), "middle")


class HandleAndSpreadTests(unittest.TestCase):
    """Poignée de glissement, étalement du texte, ancrage."""

    def test_point_and_projection_round_trip(self):
        pts = top.orient_path(circle(20))
        for f in (0.1, 0.35, 0.6, 0.9):
            x, y = top.point_at_fraction(pts, f)
            self.assertAlmostEqual(top.project_fraction(pts, (x, y)), f, delta=0.002)

    def test_projection_from_off_path_point(self):
        pts = top.orient_path(circle(20))
        f_top = top.side_center_fraction(pts, "top")
        self.assertAlmostEqual(top.project_fraction(pts, (0.0, 50.0)), f_top, delta=0.01)
        self.assertAlmostEqual(top.project_fraction(pts, (0.0, 3.0)), f_top, delta=0.01)

    def test_projection_open_path_clamps(self):
        pts = [(0.0, 0.0), (10.0, 0.0)]
        self.assertEqual(top.project_fraction(pts, (-5.0, 2.0)), 0.0)
        self.assertEqual(top.project_fraction(pts, (50.0, 2.0)), 1.0)
        self.assertAlmostEqual(top.project_fraction(pts, (5.0, 9.0)), 0.5)

    def test_spacing_to_span(self):
        adv = [2.0, 2.0, 2.0, 2.0]
        self.assertAlmostEqual(top.spacing_to_span(adv, 20.0), 4.0)             # 3 espaces entre 4 lettres
        self.assertAlmostEqual(top.spacing_to_span(adv, 20.0, wrap=True), 3.0)  # 4 espaces (tour complet)
        self.assertEqual(top.spacing_to_span([3.0], 20.0), 0.0)
        self.assertEqual(top.spacing_to_span([], 20.0), 0.0)
        self.assertLess(top.spacing_to_span(adv, 5.0), 0.0)                     # texte trop long : resserre

    def test_anchor_offset(self):
        self.assertEqual(top.anchor_offset_mm("above", 8.0), 0.0)
        self.assertEqual(top.anchor_offset_mm("center", 8.0), -4.0)
        self.assertEqual(top.anchor_offset_mm("below", 8.0), -8.0)
        self.assertEqual(top.anchor_offset_mm("inconnu", 8.0), 0.0)

    def test_below_anchor_puts_text_inside_upright_at_top(self):
        """Lettres accrochées sous le trait : texte à l'endroit en haut, côté intérieur du contour."""
        pts = top.orient_path(circle(20))
        f = top.side_center_fraction(pts, "top")
        gap = top.anchor_offset_mm("below", 6.0)
        spots = top.path_placements([2.0, 2.0, 2.0], pts, f, 0.0, False, gap)
        x, y, rot = spots[1][:3]
        self.assertAlmostEqual(abs(((rot + 180) % 360) - 180), 0.0, delta=1.0)   # à l'endroit
        self.assertLess(math.hypot(x, y), 20.0 - 5.0)                            # à l'intérieur du cercle


if __name__ == "__main__":
    unittest.main()
