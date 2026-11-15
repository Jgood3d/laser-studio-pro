"""Modèle 3D de la boîte (vector/box_3d.py) : placement des faces, ouverture du couvercle, tri pour l'affichage."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector import box_3d as b3  # noqa: E402
from laser_studio.vector import box_generator as bg  # noqa: E402


def box(**kw):
    base = dict(width=120.0, depth=90.0, height=60.0, thickness=3.0, kerf=0.0, clearance=0.0, pin_fit=0.0)
    base.update(kw)
    p = bg.BoxParams(**base)
    return p, bg.build_box(p)


def extent(faces):
    pts = [q for f in faces for q in f.points]
    return [(min(q[i] for q in pts), max(q[i] for q in pts)) for i in range(3)]


class ModelTests(unittest.TestCase):
    def test_closed_box_fills_its_outer_dimensions(self):
        for lid in ("finger", "lip", "sliding", "hinged", "none"):
            p, r = box(lid_type=lid, lid=lid != "none")
            (x0, x1), (y0, y1), (z0, z1) = extent(b3.build_faces(p, r))
            W, D, H = r.outer
            self.assertAlmostEqual(x0, 0.0, delta=1e-6, msg=lid)
            self.assertAlmostEqual(x1, W, delta=1e-6, msg=lid)
            self.assertAlmostEqual(y0, 0.0, delta=1e-6, msg=lid)
            self.assertAlmostEqual(y1, D, delta=1e-6, msg=lid)
            self.assertAlmostEqual(z0, 0.0, delta=1e-6, msg=lid)
            if lid != "none":
                self.assertAlmostEqual(z1, H, delta=0.01, msg=lid)

    def test_every_face_has_a_unit_normal_and_matching_panel(self):
        p, r = box(lid_type="pinned", dividers_x=1, magnets=True, hinge_style="butterfly")
        names = {x.name for x in r.panels}
        faces = b3.build_faces(p, r)
        self.assertTrue(faces)
        for f in faces:
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in f.normal)), 1.0, places=6)
            self.assertIn(f.name, names)
        self.assertEqual({f.name for f in faces}, names)               # aucune pièce oubliée

    def test_pinned_lid_turns_about_the_rod(self):
        p, r = box(lid_type="pinned")
        W, D, H = r.outer
        axis = (D - 1.5, H - 1.5)
        closed = [f for f in b3.build_faces(p, r, 0) if f.name == "top"]
        opened = [f for f in b3.build_faces(p, r, 90) if f.name == "top"]
        for a, b in zip(closed, opened):
            for q, w in zip(a.points, b.points):
                self.assertAlmostEqual(math.hypot(q[1] - axis[0], q[2] - axis[1]),
                                       math.hypot(w[1] - axis[0], w[2] - axis[1]), places=6)
        self.assertGreater(extent(opened)[2][1], H + 40)                # le bord avant est monté
        other = [f for f in b3.build_faces(p, r, 90) if f.name == "left"]
        self.assertEqual(extent(other), extent([f for f in b3.build_faces(p, r, 0) if f.name == "left"]))

    def test_living_hinge_bends_and_keeps_its_length(self):
        p, r = box(lid_type="hinged")
        W, D, H = r.outer
        living = b3.LivingHinge(p, r, 0.0)
        for angle in (0, 45, 90, 110):
            hinge = b3.LivingHinge(p, r, angle)
            steps = 200
            total = 0.0
            prev = hinge.centre(0.0)[:2]
            for i in range(1, steps + 1):
                cur = hinge.centre(hinge.length * i / steps)[:2]
                total += math.dist(prev, cur)
                prev = cur
            self.assertAlmostEqual(total, hinge.length, places=2)        # longueur constante
        closed = b3.build_faces(p, r, 0)
        self.assertAlmostEqual(extent(closed)[2][1], H, delta=0.01)
        lid_top = extent(b3.build_faces(p, r, 90))[2][1]
        self.assertGreater(lid_top, H + 30)
        self.assertAlmostEqual(living.length, p.hinge_length)

    def test_lid_follows_when_opened_without_gaps_in_the_hinge(self):
        p, r = box(lid_type="hinged", magnets=True)
        for angle in (0, 60, 110):
            faces = [f for f in b3.build_faces(p, r, angle) if f.name == "back"]
            # chaque tranche de la zone se raccorde à la suivante : les sommets se retrouvent à moins de 0,5 mm
            pts = [q for f in faces for q in f.points]
            tops = sorted({round(q[0], 3) for q in pts})
            self.assertTrue(tops)
            ends = [q for q in pts if abs(q[0] - tops[len(tops) // 2]) < 0.5]
            ordered = sorted(ends, key=lambda q: (q[1], q[2]))
            self.assertTrue(ordered)

    def test_hinged_lid_magnets_follow_the_lid(self):
        p, r = box(lid_type="hinged", magnets=True)
        z_closed = extent([f for f in b3.build_faces(p, r, 0) if f.name == "magnet_lid1"])[2][0]
        z_open = extent([f for f in b3.build_faces(p, r, 90) if f.name == "magnet_lid1"])[2][0]
        self.assertGreater(z_open, z_closed + 20)
        wall = extent([f for f in b3.build_faces(p, r, 90) if f.name == "magnet_wall1"])
        self.assertEqual(wall, extent([f for f in b3.build_faces(p, r, 0) if f.name == "magnet_wall1"]))

    def test_other_lids_do_not_open(self):
        for lid in ("finger", "lip", "sliding"):
            p, r = box(lid_type=lid)
            a, b = b3.build_faces(p, r, 0), b3.build_faces(p, r, 90)
            self.assertEqual(extent(a), extent(b))


class ViewTests(unittest.TestCase):
    def test_visible_faces_are_front_facing_and_sorted_far_to_near(self):
        p, r = box(lid_type="finger")
        faces = b3.build_faces(p, r)
        yaw, pitch = math.radians(-35), math.radians(25)
        vis = b3.visible_faces(faces, yaw, pitch)
        self.assertTrue(0 < len(vis) < len(faces))
        grad = b3.view_gradient(yaw, pitch)
        depths = []
        for face, pts, holes, shade in vis:
            self.assertLess(sum(a * b for a, b in zip(face.normal, grad)), 0)
            self.assertTrue(0.0 <= shade <= 1.0)
            depths.append(sum(q[2] for q in (b3.project_point(v, yaw, pitch) for v in face.points)) / len(face.points))
        self.assertEqual(depths, sorted(depths, reverse=True))

    def test_front_view_shows_the_front_wall_outside(self):
        p, r = box(lid_type="finger")
        vis = b3.visible_faces(b3.build_faces(p, r), 0.0, 0.0)
        fronts = [f for f, *_ in vis if f.name == "front" and f.normal == (0.0, -1.0, 0.0)]
        self.assertEqual(len(fronts), 1)
        order = [f.name for f, *_ in vis if f.normal == (0.0, -1.0, 0.0)]
        self.assertLess(order.index("back"), order.index("front"))        # la paroi avant se dessine par-dessus

    def test_a_small_part_is_drawn_as_one_block(self):
        p, r = box(lid_type="pinned", hinge_style="butterfly", plate_radius=7.0)
        vis = b3.visible_faces(b3.build_faces(p, r), math.radians(150), math.radians(25))
        order = [f.name for f, *_ in vis]
        for name in {n for n in order if n.startswith("hinge")}:
            idx = [i for i, n in enumerate(order) if n == name]
            self.assertEqual(idx, list(range(idx[0], idx[0] + len(idx))), msg=name)   # faces consécutives


class ExplodeAndMaterialTests(unittest.TestCase):
    def setUp(self):
        self.p = bg.BoxParams(width=100, depth=70, height=50, thickness=3, kerf=0.0, lid_type="lip")
        self.r = bg.build_box(self.p)

    def test_zero_explode_equals_closed_box(self):
        a = b3.build_faces(self.p, self.r, 0.0, 0.0)
        b = b3.build_faces(self.p, self.r, 0.0)
        self.assertEqual([f.points for f in a], [f.points for f in b])

    def test_explode_moves_walls_outward_and_keeps_dimensions_of_each_part(self):
        closed = b3.build_faces(self.p, self.r, 0.0, 0.0)
        exploded = b3.build_faces(self.p, self.r, 0.0, 1.0)
        self.assertEqual(len(closed), len(exploded))
        def box(faces, name):
            pts = [q for f in faces if f.name == name for q in f.points]
            return [(min(q[i] for q in pts), max(q[i] for q in pts)) for i in range(3)]
        for name in ("left", "right", "front", "back", "bottom"):
            c, e = box(closed, name), box(exploded, name)
            for (c0, c1), (e0, e1) in zip(c, e):
                self.assertAlmostEqual(c1 - c0, e1 - e0, places=6, msg=name)
        self.assertGreater(box(exploded, "right")[0][0], box(closed, "right")[0][0] + 1.0)
        self.assertLess(box(exploded, "left")[0][1], box(closed, "left")[0][1] - 1.0)

    def test_materials_have_valid_colours(self):
        self.assertIn(b3.DEFAULT_MATERIAL, b3.MATERIALS)
        for key, (rgb, grain) in b3.MATERIALS.items():
            self.assertTrue(all(0 <= c <= 255 for c in rgb), key)
            self.assertTrue(0.0 <= grain <= 1.0, key)


class FeetAndRatiosTests(unittest.TestCase):
    def test_feet_sit_under_the_floor_inside_the_footprint(self):
        p = bg.BoxParams(width=100, depth=70, height=50, thickness=3, kerf=0.0, lid_type="lip", feet=True,
                         foot_size=15.0, foot_layers=2)
        r = bg.build_box(p)
        faces = b3.build_faces(p, r)
        feet = [q for f in faces if f.name.startswith("foot") for q in f.points]
        self.assertAlmostEqual(min(q[2] for q in feet), -6.0, places=6)
        self.assertAlmostEqual(max(q[2] for q in feet), 0.0, places=6)
        self.assertTrue(all(0 <= q[0] <= 100 and 0 <= q[1] <= 70 for q in feet))

    def test_dividers_follow_the_ratios_in_3d(self):
        p = bg.BoxParams(width=100, depth=70, height=50, thickness=3, kerf=0.0, lid_type="lip", dividers_x=1,
                         ratios_x=(1, 3))
        r = bg.build_box(p)
        xs = [q[0] for f in b3.build_faces(p, r) if f.name == "divider_x1" for q in f.points]
        self.assertAlmostEqual(min(xs), bg.divider_positions(100, 1, 3, (1, 3))[0], places=6)
