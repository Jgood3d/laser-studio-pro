"""Aperçu 2D : matière à l'intérieur des découpes (contours reconstitués à partir du G-code)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from laser_studio.gcode_generation_mixin import GcodeGenerationMixin
except ImportError:  # PyQt6, pyqtgraph manquants
    GcodeGenerationMixin = None

NAN = float("nan")


def segments(points):
    """Segments G1 d'un tracé, au format de l'aperçu : x / y avec un NaN entre deux segments."""
    xs, ys = [], []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        xs += [x1, x2, NAN]
        ys += [y1, y2, NAN]
    return xs, ys


def circle(cx, cy, r, n=24):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return pts + [pts[0]]


@unittest.skipIf(GcodeGenerationMixin is None, "gcode_generation_mixin non importable ici")
class CutContoursTests(unittest.TestCase):
    def test_contour_hole_passes_and_open_paths(self):
        outer, hole = circle(40, 40, 40), circle(40, 75, 2)
        xs, ys = segments(outer)
        hx, hy = segments(hole)
        open_line = segments([(0, 0), (10, 0), (10, 5)])
        # Deux passes : chaque contour figure deux fois.
        layer = (xs + hx + xs + hx + open_line[0], ys + hy + ys + hy + open_line[1])
        contours = GcodeGenerationMixin._cut_contours([layer])
        self.assertEqual(len(contours), 2)                            # contour et trou, une fois chacun
        widths = sorted(round(max(x for x, _ in c) - min(x for x, _ in c)) for c in contours)
        self.assertEqual(widths, [4, 80])

    def test_no_cut(self):
        self.assertEqual(GcodeGenerationMixin._cut_contours([]), [])


if __name__ == "__main__":
    unittest.main()
