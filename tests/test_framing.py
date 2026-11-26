"""Parcours du cadrage (gcode/framing.py, sans Qt) : rectangle et tour au plus près de ce qui sera gravé."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.gcode.framing import box_path, burn_extent, contour_paths  # noqa: E402

L_SHAPE = [(0, 0, 20, 0), (20, 0, 20, 6), (20, 6, 6, 6), (6, 6, 6, 20), (6, 20, 0, 20), (0, 20, 0, 0)]


def near(path, x, y, tolerance=1.0):
    return any(abs(px - x) <= tolerance and abs(py - y) <= tolerance for px, py in path)


class FramingTests(unittest.TestCase):
    def test_box_goes_to_x_max_then_y_max_then_back(self):
        self.assertEqual(box_path(burn_extent(L_SHAPE)), [(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)])
        self.assertIsNone(burn_extent([]))

    def test_contour_follows_the_hollow_of_an_l(self):
        (path,) = contour_paths(L_SHAPE)
        self.assertEqual(path[0], path[-1])                                   # fermé
        self.assertTrue(near(path, 6, 6) and near(path, 20, 0) and near(path, 0, 20))
        self.assertFalse(near(path, 20, 20, tolerance=5))                     # ne coupe pas par le coin vide
        xs, ys = [p[0] for p in path], [p[1] for p in path]
        self.assertTrue(min(xs) >= -0.5 and max(xs) <= 20.5 and min(ys) >= -0.5 and max(ys) <= 20.5)

    def test_close_parts_are_framed_together_far_ones_apart(self):
        square = lambda x: [(x, 0, x + 5, 0), (x + 5, 0, x + 5, 5), (x + 5, 5, x, 5), (x, 5, x, 0)]
        self.assertEqual(len(contour_paths(square(0) + square(6))), 1)        # 1 mm d'écart : une pièce
        self.assertEqual(len(contour_paths(square(0) + square(30))), 2)       # loin : deux tours
        self.assertIsNone(contour_paths([]))

    def test_a_raster_block_is_one_rectangle(self):
        # Lignes d'une gravure d'image, 0,1 mm l'une de l'autre : un seul tour, aux bords de l'image.
        lines = [(0, y / 10, 30, y / 10) for y in range(101)]
        (path,) = contour_paths(lines)
        self.assertEqual(len(path), 5)
        self.assertTrue(near(path, 0, 0) and near(path, 30, 10))


if __name__ == "__main__":
    unittest.main()
