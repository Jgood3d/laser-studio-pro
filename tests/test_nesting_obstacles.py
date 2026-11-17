"""Imbrication avec obstacles : les pièces ne recouvrent pas les contours déjà présents sur la feuille."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
from laser_studio.vector import nesting as ng


def rect(w, h, x=0.0, y=0.0):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def placed_box(piece, placement):
    pts = [placement.apply(p) for poly in piece for p in poly]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def overlap(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


class ObstacleTests(unittest.TestCase):
    def nest(self, pieces, obstacles, **kw):
        return ng.nest(pieces, 100, 50, spacing=2.0, margin=0.0, angles=ng.ANGLE_SETS["none"], cell=1.0,
                       obstacles=obstacles, **kw)

    def test_pieces_avoid_obstacle(self):
        obstacle = [rect(50, 50)]                                  # moitié gauche de la feuille occupée
        pieces = [[rect(20, 20)] for _ in range(4)]
        result = self.nest(pieces, obstacle)
        self.assertGreaterEqual(len(result.placements), 2)          # la moitié libre ne peut pas tout contenir
        for pl in result.placements:
            box = placed_box(pieces[pl.index], pl)
            self.assertFalse(overlap(box, (0, 0, 50, 50)), box)
            self.assertGreaterEqual(box[0], 50 - 1e-6)

    def test_spacing_is_kept_from_obstacle(self):
        result = self.nest([[rect(10, 10)]], [rect(30, 50)])
        box = placed_box([rect(10, 10)], result.placements[0])
        self.assertGreaterEqual(box[0] - 30, 2.0 - 1.0)            # espacement voulu, à une cellule près

    def test_without_obstacle_pieces_start_bottom_left(self):
        result = self.nest([[rect(20, 20)]], None)
        self.assertEqual(placed_box([rect(20, 20)], result.placements[0])[:2], (0.0, 0.0))

    def test_full_sheet_obstacle_leaves_nothing_placed(self):
        result = self.nest([[rect(20, 20)], [rect(10, 10)]], [rect(100, 50)])
        self.assertEqual(result.placements, [])
        self.assertEqual(result.unplaced, [0, 1])

    def test_obstacle_outside_the_sheet_is_ignored(self):
        result = self.nest([[rect(20, 20)]], [rect(30, 30, x=500, y=500), rect(10, 10, x=-80, y=-80)])
        self.assertEqual(len(result.placements), 1)

    def test_open_line_obstacle_is_respected(self):
        line = [(0.0, 10.0), (100.0, 10.0)]                        # trait ouvert : un fil de découpe tout en bas
        result = self.nest([[rect(20, 20)]], [line])
        box = placed_box([rect(20, 20)], result.placements[0])
        self.assertFalse(box[1] < 10 < box[3], box)                # la pièce ne chevauche pas le trait


if __name__ == "__main__":
    unittest.main()
