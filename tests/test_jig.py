"""Gabarit de placement : taille des poches, plaque, rangement comme « Dupliquer en série » (sans Qt)."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
from laser_studio.vector import jig as jg
from laser_studio.vector import serial_duplicate as sd


def box(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


class GeometryTests(unittest.TestCase):
    def test_single_pocket_has_object_size_plus_clearance(self):
        j = jg.build_jig(jg.JigParams(obj_w=50, obj_h=25, clearance=0.3, margin=8))
        self.assertAlmostEqual(j.pocket_w, 50.6)
        self.assertAlmostEqual(j.pocket_h, 25.6)
        self.assertEqual(j.count, 1)
        self.assertAlmostEqual(j.plate_w, 50.6 + 16)
        self.assertAlmostEqual(j.plate_h, 25.6 + 16)
        x0, y0, x1, y1 = box(j.pockets[0])
        self.assertAlmostEqual(x0, 8)
        self.assertAlmostEqual(y0, 8)
        self.assertAlmostEqual(x1 - x0, 50.6)
        self.assertEqual(j.object_origins[0], (8.3, 8.3))

    def test_grid_pitch_wall_and_plate_size(self):
        j = jg.build_jig(jg.JigParams(obj_w=40, obj_h=20, cols=3, rows=2, clearance=0.5, gap_x=6, gap_y=4, margin=5))
        self.assertEqual(j.count, 6)
        self.assertEqual((j.pitch_x, j.pitch_y), (46, 24))
        self.assertAlmostEqual(j.wall_x, 46 - 41)
        self.assertAlmostEqual(j.wall_y, 24 - 21)
        self.assertAlmostEqual(j.plate_w, 10 + 2 * 46 + 41)
        self.assertAlmostEqual(j.plate_h, 10 + 24 + 21)
        boxes = [box(p) for p in j.pockets]
        for b in boxes:                                              # tout reste dans la plaque
            self.assertTrue(0 <= b[0] and b[2] <= j.plate_w and 0 <= b[1] and b[3] <= j.plate_h)
        for a in range(6):                                           # aucune poche ne chevauche une autre
            for b in range(a + 1, 6):
                A, B = boxes[a], boxes[b]
                self.assertFalse(A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3])

    def test_downward_puts_first_pocket_at_top(self):
        up = jg.build_jig(jg.JigParams(obj_w=10, obj_h=10, cols=1, rows=3, upward=True))
        down = jg.build_jig(jg.JigParams(obj_w=10, obj_h=10, cols=1, rows=3, upward=False))
        self.assertLess(up.object_origins[0][1], up.object_origins[2][1])
        self.assertGreater(down.object_origins[0][1], down.object_origins[2][1])

    def test_rounded_rect_is_closed_and_inside_its_box(self):
        poly = jg.rounded_rect(2, 3, 20, 10, radius=4)
        self.assertEqual(poly[0], poly[-1])
        x0, y0, x1, y1 = box(poly)
        self.assertAlmostEqual(x0, 2)
        self.assertAlmostEqual(y0, 3)
        self.assertAlmostEqual(x1, 22)
        self.assertAlmostEqual(y1, 13)
        self.assertGreater(len(poly), 10)

    def test_radius_is_clamped_to_half_the_smallest_side(self):
        poly = jg.rounded_rect(0, 0, 20, 10, radius=999)
        x0, y0, x1, y1 = box(poly)
        self.assertAlmostEqual(x1 - x0, 20)
        self.assertAlmostEqual(y1 - y0, 10)

    def test_zero_radius_is_a_plain_rectangle(self):
        self.assertEqual(jg.rounded_rect(0, 0, 4, 2, 0), [(0, 0), (4, 0), (4, 2), (0, 2), (0, 0)])

    def test_ellipse_pocket(self):
        j = jg.build_jig(jg.JigParams(obj_w=30, obj_h=30, clearance=0, pocket_shape="ellipse", margin=5))
        x0, y0, x1, y1 = box(j.pockets[0])
        self.assertAlmostEqual(x0, 5)
        self.assertAlmostEqual(x1, 35)
        pts = j.pockets[0]
        for x, y in pts:
            self.assertAlmostEqual(math.hypot(x - 20, y - 20), 15)


class ErrorTests(unittest.TestCase):
    def code(self, **kw):
        with self.assertRaises(jg.JigError) as ctx:
            jg.build_jig(jg.JigParams(**kw))
        return ctx.exception.code

    def test_invalid_size(self):
        self.assertEqual(self.code(obj_w=0, obj_h=10), "size")
        self.assertEqual(self.code(obj_w=10, obj_h=-1), "size")

    def test_too_many_pockets(self):
        self.assertEqual(self.code(obj_w=10, obj_h=10, cols=30, rows=30), "count")

    def test_overlapping_pockets(self):
        self.assertEqual(self.code(obj_w=10, obj_h=10, cols=2, clearance=2, gap_x=3), "overlap")

    def test_overlap_ignored_when_there_is_a_single_column(self):
        jg.build_jig(jg.JigParams(obj_w=10, obj_h=10, cols=1, rows=2, clearance=2, gap_x=0, gap_y=6))

    def test_thin_wall_warning(self):
        thin = jg.build_jig(jg.JigParams(obj_w=10, obj_h=10, cols=2, clearance=0.5, gap_x=2))
        self.assertTrue(thin.thin_wall())
        ok = jg.build_jig(jg.JigParams(obj_w=10, obj_h=10, cols=2, clearance=0.5, gap_x=6))
        self.assertFalse(ok.thin_wall())
        single = jg.build_jig(jg.JigParams(obj_w=10, obj_h=10, clearance=0.5, gap_x=0))
        self.assertFalse(single.thin_wall())


class SerialAlignmentTests(unittest.TestCase):
    """Le gabarit et « Dupliquer en série » (mêmes colonnes / espacements) doivent tomber sur les mêmes cases."""

    class Obj:
        def __init__(self, x, y, w, h):
            self.x_mm, self.y_mm, self.w, self.h = x, y, w, h

    def test_serial_copies_land_in_the_pockets(self):
        for upward in (True, False):
            j = jg.build_jig(jg.JigParams(obj_w=40, obj_h=20, cols=3, rows=2, clearance=0.4, gap_x=7, gap_y=5,
                                          margin=6, upward=upward))
            objs = [self.Obj(100, 50, 40, 20)]
            bounds = lambda o: (o.x_mm, o.y_mm, o.x_mm + o.w, o.y_mm + o.h)
            clone = lambda o: self.Obj(o.x_mm, o.y_mm, o.w, o.h)
            copies = sd.build_copies(objs, 6, clone=clone, bounds=bounds)
            sd.layout_grid(copies, bounds, cols=3, gap_x=7, gap_y=5, upward=upward)
            ox, oy = jg.plate_origin_around(j, 100, 50)
            for k, copy in enumerate(copies):
                want = (ox + j.object_origins[k][0], oy + j.object_origins[k][1])
                got = (copy[0].x_mm, copy[0].y_mm)
                self.assertAlmostEqual(got[0], want[0])
                self.assertAlmostEqual(got[1], want[1])
                px0, py0, px1, py1 = box(j.pockets[k])             # et l'objet est bien dans sa poche
                self.assertTrue(ox + px0 <= got[0] and got[0] + 40 <= ox + px1)
                self.assertTrue(oy + py0 <= got[1] and got[1] + 20 <= oy + py1)


if __name__ == "__main__":
    unittest.main()
