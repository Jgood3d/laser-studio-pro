"""Imbrication : aucune collision, espacement et marges respectés, rotations, emboîtement dans les creux."""
import itertools
import math
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import nesting as ng
import vector_order as vo


def rect(w, h, x=0.0, y=0.0):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def circle(r, n=40, cx=None, cy=None):
    cx = r if cx is None else cx
    cy = r if cy is None else cy
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def l_shape(size=50, arm=20):
    return [(0, 0), (size, 0), (size, arm), (arm, arm), (arm, size), (0, size), (0, 0)]


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def min_distance(poly_a, poly_b):
    """Distance minimale entre deux contours (0 si l'un contient un point de l'autre)."""
    if any(vo.point_in_polygon(x, y, poly_b) for x, y in poly_a[:3]) or any(vo.point_in_polygon(x, y, poly_a) for x, y in poly_b[:3]):
        return 0.0
    best = float("inf")
    for pa, pb in ((poly_a, poly_b), (poly_b, poly_a)):
        for p in pa:
            for i in range(len(pb) - 1):
                best = min(best, seg_dist(p, pb[i], pb[i + 1]))
    return best


def moved(pieces, result):
    return {pl.index: [[pl.apply(p) for p in poly] for poly in pieces[pl.index]] for pl in result.placements}


def assert_valid(tc, pieces, result, spacing, margin, sheet_w, sheet_h, origin=(0.0, 0.0)):
    """Dans la zone utile, sans collision, à au moins `spacing` les unes des autres."""
    shapes = moved(pieces, result)
    x_lo, y_lo = origin[0] + margin, origin[1] + margin
    x_hi, y_hi = origin[0] + sheet_w - margin, origin[1] + sheet_h - margin
    for idx, polys in shapes.items():
        for poly in polys:
            for x, y in poly:
                tc.assertTrue(x_lo - 1e-6 <= x <= x_hi + 1e-6 and y_lo - 1e-6 <= y <= y_hi + 1e-6, f"pièce {idx} hors de la zone utile")
    for (i, a), (j, b) in itertools.combinations(shapes.items(), 2):
        tc.assertGreaterEqual(min_distance(max(a, key=vo.polygon_area), max(b, key=vo.polygon_area)), spacing - 1e-6,
                              f"pièces {i} et {j} trop proches ou superposées")


class PlacementTests(unittest.TestCase):
    def test_identical_rectangles_all_fit_without_collision(self):
        pieces = [[rect(20, 10)] for _ in range(12)]
        r = ng.nest(pieces, 100, 60, spacing=2, margin=1)
        self.assertEqual((len(r.placements), r.unplaced), (12, []))
        assert_valid(self, pieces, r, 2, 1, 100, 60)

    def test_mixed_shapes_respect_spacing_and_margins(self):
        random.seed(5)
        pieces = [[rect(random.randint(15, 50), random.randint(10, 35))] if random.random() < 0.5 else [circle(random.randint(6, 18))] for _ in range(25)]
        for spacing, margin, cell in ((2.0, 2.0, 1.0), (4.0, 0.0, 1.0), (1.0, 5.0, 0.5)):
            r = ng.nest(pieces, 250, 200, spacing=spacing, margin=margin, cell=cell)
            self.assertEqual(r.unplaced, [], (spacing, margin, cell))
            assert_valid(self, pieces, r, spacing, margin, 250, 200)

    def test_sheet_origin_offset_and_determinism(self):
        pieces = [[rect(30, 20)] for _ in range(4)]
        r = ng.nest(pieces, 100, 60, spacing=2, margin=0, origin=(50.0, 70.0))
        assert_valid(self, pieces, r, 2, 0, 100, 60, origin=(50.0, 70.0))
        a, b = ng.nest(pieces, 100, 60), ng.nest(pieces, 100, 60)
        self.assertEqual([(p.index, p.angle, p.tx, p.ty) for p in a.placements], [(p.index, p.angle, p.tx, p.ty) for p in b.placements])

    def test_pieces_too_big_are_reported_and_others_still_placed(self):
        r = ng.nest([[rect(500, 20)], [rect(20, 20)], [rect(30, 30)]], 100, 100)
        self.assertEqual(r.unplaced, [0])
        self.assertEqual([p.index for p in r.placements], [1, 2])

    def test_degenerate_inputs(self):
        r = ng.nest([[rect(5, 5)]], 20, 20, margin=10)
        self.assertEqual((r.placements, r.unplaced), ([], [0]))
        r = ng.nest([[], [rect(10, 10)]], 50, 50)
        self.assertEqual((r.unplaced, [p.index for p in r.placements]), ([0], [1]))
        with self.assertRaises(ValueError):
            ng.nest([[rect(5, 5)]], 50, 50, cell=0)
        r = ng.nest([], 50, 50)
        self.assertEqual((r.placements, r.unplaced, r.utilization), ([], [], 0.0))


class RotationTests(unittest.TestCase):
    def test_long_piece_needs_a_rotation_to_fit(self):
        pieces = [[rect(90, 10)]]
        self.assertEqual(ng.nest(pieces, 20, 100, angles=ng.ANGLE_SETS["none"]).unplaced, [0])
        r = ng.nest(pieces, 20, 100, angles=ng.ANGLE_SETS["flip"])
        self.assertEqual(r.unplaced, [])
        self.assertIn(r.placements[0].angle, (90.0, 270.0))
        assert_valid(self, pieces, r, 2, 0, 20, 100)

    def test_rotations_improve_the_packing(self):
        pieces = [[rect(40, 10)] for _ in range(10)]
        fixed = ng.nest(pieces, 60, 120, spacing=2, angles=ng.ANGLE_SETS["none"])
        free = ng.nest(pieces, 60, 120, spacing=2, angles=ng.ANGLE_SETS["quarters"])
        self.assertGreaterEqual(len(free.placements), len(fixed.placements))

    def test_diagonal_angles(self):
        pieces = [[rect(70, 5)]]
        r = ng.nest(pieces, 55, 55, spacing=0, angles=ng.ANGLE_SETS["eighths"])
        self.assertEqual(r.unplaced, [])
        self.assertEqual(r.placements[0].angle % 90, 45.0)
        assert_valid(self, pieces, r, 0, 0, 55, 55)

    def test_apply_rotates_about_the_pivot_then_translates(self):
        pl = ng.Placement(0, 90.0, (10.0, 10.0), 5.0, -3.0)
        x, y = pl.apply((20.0, 10.0))
        self.assertAlmostEqual(x, 15.0)
        self.assertAlmostEqual(y, 17.0)
        self.assertEqual(pl.apply((10.0, 10.0)), (15.0, 7.0))


class ShapeAwareTests(unittest.TestCase):
    def test_small_piece_goes_into_the_notch_of_an_l_shape(self):
        big, small = [l_shape(60, 20)], [rect(25, 25)]
        r = ng.nest([big, small], 62, 62, spacing=2, angles=ng.ANGLE_SETS["none"])
        self.assertEqual(r.unplaced, [])
        assert_valid(self, [big, small], r, 2, 0, 62, 62)
        pts = moved([big, small], r)[1][0]
        self.assertGreater(min(p[0] for p in pts), 20 - 1e-6)
        self.assertGreater(min(p[1] for p in pts), 20 - 1e-6)

    def test_group_by_containment(self):
        plate, hole, other = rect(40, 40), circle(8, cx=20, cy=20), rect(30, 30, 100, 0)
        self.assertEqual(ng.group_by_containment([[plate], [hole], [other]]), [[0, 1], [2]])
        outer, hole2 = rect(100, 100), rect(20, 20, 10, 10)
        shapes = [[outer, hole2], [rect(5, 5, 15, 15)], [[(60, 60), (80, 70)]], [rect(30, 30, 200, 0)]]
        groups = ng.group_by_containment([[outer, hole2], [rect(5, 5, 15, 15)], [[(60, 60), (80, 70)]][0:1] and [[(60, 60), (80, 70)]], [rect(30, 30, 200, 0)]])
        self.assertIn([0, 2], groups)       # le trait gravé suit la plaque
        self.assertIn([1], groups)          # l'îlot dans le trou est une pièce à part
        self.assertIn([3], groups)
        a, b, c = rect(100, 100), rect(60, 60, 20, 20), rect(20, 20, 40, 40)
        self.assertEqual(ng.group_by_containment([[c], [a], [b]]), [[1, 0, 2]])
        self.assertEqual((ng.group_by_containment([]), ng.group_by_containment([[]])), ([], [[0]]))


class StatsAndGridTests(unittest.TestCase):
    def test_utilization_extent_progress_and_order(self):
        pieces = [[rect(20, 10)] for _ in range(4)]
        r = ng.nest(pieces, 100, 60, spacing=2)
        self.assertAlmostEqual(r.piece_area, 800.0)
        self.assertTrue(0 < r.extent[0] <= 100 and 0 < r.extent[1] <= 60 and 0 < r.utilization <= 1.0)
        calls = []
        ng.nest([[rect(10, 10)] for _ in range(6)], 100, 100, progress=lambda d, t: calls.append((d, t)))
        self.assertEqual(calls, [(i, 6) for i in range(1, 7)])
        r = ng.nest([[rect(10, 10)] for _ in range(6)], 100, 100, progress=lambda d, t: d < 2)
        self.assertEqual((len(r.placements), len(r.unplaced)), (2, 4))
        r = ng.nest([[rect(10, 10)], [rect(40, 40)]], 100, 100, spacing=2, angles=ng.ANGLE_SETS["none"])
        big = next(p for p in r.placements if p.index == 1)
        self.assertAlmostEqual(big.tx, 0.0, places=6)
        self.assertAlmostEqual(big.ty, 0.0, places=6)

    def test_thin_lines_are_kept_apart_and_finer_cells_keep_the_guarantees(self):
        r = ng.nest([[[(0, 0), (60, 0)]] for _ in range(4)], 70, 40, spacing=3, angles=ng.ANGLE_SETS["none"])
        self.assertEqual(r.unplaced, [])
        ys = sorted(round(pl.ty, 3) for pl in r.placements)
        for a, b in zip(ys, ys[1:]):
            self.assertGreaterEqual(b - a, 3 - 1e-6)
        random.seed(11)
        pieces = [[circle(random.randint(5, 15))] for _ in range(12)]
        for cell in (2.0, 1.0, 0.5):
            assert_valid(self, pieces, ng.nest(pieces, 150, 100, spacing=3, margin=1, cell=cell), 3, 1, 150, 100)


if __name__ == "__main__":
    unittest.main()
