"""Aperçu 3D des pièces plates (porte-clés, boules de Noël) : imbrication des contours, extrusion, ordre de dessin,
gravure, veinage. Sans Qt : ce sont des contours quelconques (mm, Y vers le haut)."""
import math
import os
import sys
import time
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector import box_3d, plate_3d  # noqa: E402


def rect(x0, y0, x1, y1, ccw=True):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return pts if ccw else pts[::-1]


def circle(cx, cy, r, n=64, ccw=True):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return pts if ccw else pts[::-1]


def area_centroid(loop):
    """(aire positive, centroïde) d'un polygone."""
    a = plate_3d.signed_area(loop)
    cx = cy = 0.0
    for p, q in zip(loop, loop[1:] + loop[:1]):
        k = p[0] * q[1] - q[0] * p[1]
        cx += (p[0] + q[0]) * k
        cy += (p[1] + q[1]) * k
    return abs(a), (cx / (6 * a), cy / (6 * a))


def volume(faces):
    """Volume par le théorème de la divergence (F = p/3) : juste si les normales sortent bien de la matière et si
    les faces ferment la pièce. Les faces larges avec trous comptent leur aire moins celle des trous."""
    total = 0.0
    for f in faces:
        z = f.points[0][2]
        n = f.normal
        if abs(n[2]) > 0.5:                                   # dessus / dessous : plan z = const
            parts = [(f.points, 1.0)] + [(h, -1.0) for h in f.holes]
            for loop, sign in parts:
                xy = [(q[0], q[1]) for q in loop]
                area, (cx, cy) = area_centroid(xy)
                total += sign * area * (cx * n[0] + cy * n[1] + z * n[2]) / 3.0
        else:                                                 # paroi : quadrilatère vertical
            a, b, c, d = f.points
            area = math.dist(a[:2], b[:2]) * abs(c[2] - b[2])
            mid = [(a[i] + b[i] + c[i] + d[i]) / 4.0 for i in range(3)]
            total += area * sum(m * k for m, k in zip(mid, n)) / 3.0
    return total


class NestingTests(unittest.TestCase):
    def test_ring_is_one_outer_and_one_hole(self):
        regions = plate_3d.nest_contours([circle(0, 0, 10), circle(0, 0, 4)])
        self.assertEqual(len(regions), 1)
        outer, holes = regions[0]
        self.assertEqual(len(outer), 64)
        self.assertEqual(len(holes), 1)

    def test_island_in_a_hole_is_material_again(self):
        # disque, trou dedans, île dans le trou (l'intérieur d'un « o » découpé), trou dans l'île
        loops = [circle(0, 0, 20), circle(0, 0, 14), circle(0, 0, 8), circle(0, 0, 3)]
        regions = plate_3d.nest_contours(loops)
        self.assertEqual(len(regions), 2)
        sizes = sorted((abs(plate_3d.signed_area(o)), len(h)) for o, h in regions)
        self.assertEqual([n for _a, n in sizes], [1, 1])
        self.assertGreater(sizes[1][0], sizes[0][0])

    def test_separate_shapes_and_orientation_do_not_matter(self):
        regions = plate_3d.nest_contours([rect(0, 0, 10, 10, ccw=False), rect(20, 0, 30, 10), circle(5, 5, 2, ccw=True)])
        self.assertEqual(len(regions), 2)
        holes = sorted(len(h) for _o, h in regions)
        self.assertEqual(holes, [0, 1])

    def test_degenerate_contours_are_ignored(self):
        self.assertEqual(plate_3d.nest_contours([[(0, 0), (1, 1)], rect(0, 0, 5, 5)])[0][1], [])
        self.assertEqual(plate_3d.nest_contours([]), [])


class SimplifyTests(unittest.TestCase):
    def test_collinear_points_are_dropped(self):
        pts = [(x, 0.0) for x in range(0, 50)] + [(50.0, y) for y in range(0, 20)] + [(x, 20.0) for x in range(50, 0, -1)] \
            + [(0.0, y) for y in range(20, 0, -1)]
        out = plate_3d.simplify_loop(pts)
        self.assertEqual(sorted(out), sorted([(0.0, 0.0), (50.0, 0.0), (50.0, 20.0), (0.0, 20.0)]))

    def test_circle_keeps_its_shape_within_tolerance(self):
        out = plate_3d.simplify_loop(circle(0, 0, 40, 720))
        self.assertLess(len(out), 400)
        self.assertGreaterEqual(len(out), 40)
        for q in out:
            self.assertAlmostEqual(math.hypot(*q), 40.0, delta=1e-6)       # les sommets restent sur le cercle
        self.assertAlmostEqual(abs(plate_3d.signed_area(out)), math.pi * 1600, delta=math.pi * 1600 * 0.01)

    def test_small_and_closing_point(self):
        self.assertEqual(len(plate_3d.simplify_loop(rect(0, 0, 4, 4) + [(0, 0)])), 4)
        self.assertGreaterEqual(len(plate_3d.simplify_loop(circle(0, 0, 0.05, 40))), 3)


class ExtrusionTests(unittest.TestCase):
    def test_square_plate_has_two_caps_and_four_walls(self):
        faces = plate_3d.extrude(plate_3d.regions_of([rect(0, 0, 10, 6)]), 0.0, 3.0, "p")
        self.assertEqual(len(faces), 6)
        self.assertAlmostEqual(volume(faces), 10 * 6 * 3, places=6)

    def test_normals_point_out_of_the_material(self):
        faces = plate_3d.extrude(plate_3d.regions_of([circle(0, 0, 20), circle(0, 0, 5, ccw=False)]), 0.0, 3.0, "p")
        for f in faces:
            if abs(f.normal[2]) > 0.5:
                continue
            mid = [sum(q[i] for q in f.points) / 4 for i in range(2)]
            radial = (mid[0] * f.normal[0] + mid[1] * f.normal[1])          # > 0 : la normale s'éloigne du centre
            self.assertGreater(radial, 0) if math.hypot(*mid) > 10 else self.assertLess(radial, 0)

    def test_volume_with_holes_and_islands_matches_the_area_times_thickness(self):
        loops = [circle(0, 0, 20, 128), circle(0, 0, 14, 128), circle(0, 0, 8, 128), circle(0, 0, 3, 128),
                 rect(30, 0, 40, 10)]
        for orient in (False, True):                                           # le sens des contours est sans effet
            cut = [c[::-1] if orient else c for c in loops]
            faces = plate_3d.plate_faces(cut, thickness=2.0)
            expected = 2.0 * (circle_area(20) - circle_area(14) + circle_area(8) - circle_area(3) + 100.0)
            self.assertAlmostEqual(volume(faces), expected, delta=expected * 0.01)

    def test_thickness_is_clamped(self):
        faces = plate_3d.plate_faces([rect(0, 0, 10, 10)], thickness=500)
        self.assertAlmostEqual(max(q[2] for f in faces for q in f.points), plate_3d.MAX_THICKNESS)
        faces = plate_3d.plate_faces([rect(0, 0, 10, 10)], thickness=0)
        self.assertAlmostEqual(max(q[2] for f in faces for q in f.points), plate_3d.MIN_THICKNESS)


def circle_area(r):
    return math.pi * r * r


class BuildersTests(unittest.TestCase):
    def keychain(self, two_layers):
        base = [rect(0, 0, 60, 20), circle(5, 10, 2, ccw=False)]
        text = [rect(15, 5, 25, 15), rect(35, 5, 45, 15)]
        return types.SimpleNamespace(base_contours=base, text_contours=text, two_layers=two_layers)

    def test_classic_keychain_is_a_plate_with_engraved_name(self):
        faces = plate_3d.keychain_faces(self.keychain(False), 3.0)
        engraved = [f for f in faces if f.kind == "engrave"]
        self.assertEqual(len(engraved), 2)
        for f in engraved:
            self.assertGreater(f.points[0][2], 3.0)                         # posée sur le dessus
            self.assertLess(f.points[0][2], 3.1)
        body = [f for f in faces if f.kind == "body"]
        self.assertAlmostEqual(max(q[2] for f in body for q in f.points), 3.0)
        self.assertAlmostEqual(volume(body), (60 * 20 - circle_area(2)) * 3.0, delta=3.0)

    def test_two_layer_keychain_has_a_top_plate_with_the_name_cut_through(self):
        faces = plate_3d.keychain_faces(self.keychain(True), 3.0)
        self.assertFalse([f for f in faces if f.kind == "engrave"])
        base = [f for f in faces if f.tier == 0]
        top = [f for f in faces if f.tier == 1]
        self.assertEqual({f.name for f in base}, {"base"})
        self.assertEqual({f.name for f in top}, {"top"})
        self.assertAlmostEqual(min(q[2] for f in top for q in f.points), 3.0)
        self.assertAlmostEqual(max(q[2] for f in top for q in f.points), 6.0)
        # fond plein (sauf l'anneau) ; dessus = même plaque moins les deux lettres
        self.assertAlmostEqual(volume(base), (60 * 20 - circle_area(2)) * 3.0, delta=3.0)
        self.assertAlmostEqual(volume(top), (60 * 20 - circle_area(2) - 2 * 100) * 3.0, delta=3.0)
        caps = [f for f in top if f.normal == (0.0, 0.0, 1.0)]
        self.assertEqual(len(caps), 1)
        self.assertEqual(len(caps[0].holes), 3)                              # anneau + 2 lettres

    def test_glue_letters_keychain_puts_the_cut_letters_on_the_plate(self):
        res = self.keychain(False)
        res.glue_letters = True
        faces = plate_3d.keychain_faces(res, 3.0)
        self.assertFalse([f for f in faces if f.kind == "engrave"])          # la gravure de placement est cachée dessous
        base = [f for f in faces if f.tier == 0]
        letters = [f for f in faces if f.tier == 1]
        self.assertEqual({f.name for f in letters}, {"letters"})
        self.assertAlmostEqual(min(q[2] for f in letters for q in f.points), 3.0)
        self.assertAlmostEqual(max(q[2] for f in letters for q in f.points), 6.0)
        self.assertAlmostEqual(volume(base), (60 * 20 - circle_area(2)) * 3.0, delta=3.0)   # plaque pleine
        self.assertAlmostEqual(volume(letters), 2 * 100 * 3.0, places=6)

    def test_ornament_engraves_name_and_frame(self):
        parts = types.SimpleNamespace(cut=[circle(0, 0, 40), circle(0, 0, 36, ccw=False)],
                                      name=[rect(-10, -3, 10, 3)], frame=[rect(-15, -8, 15, 8), rect(-14, -7, 14, 7)])
        faces = plate_3d.ornament_faces(parts, 3.0)
        self.assertEqual(len([f for f in faces if f.kind == "engrave"]), 2)       # le prénom, le filet (anneau)
        ring = [f for f in faces if f.kind == "engrave" and f.holes]
        self.assertEqual(len(ring), 1)

    def test_cut_name_ornament_has_no_engraving(self):
        parts = types.SimpleNamespace(cut=[circle(0, 0, 40)], name=[], frame=[])
        self.assertFalse([f for f in plate_3d.ornament_faces(parts) if f.kind == "engrave"])

    def test_extent_covers_everything(self):
        faces = plate_3d.plate_faces([rect(0, 0, 100, 40)], thickness=3.0)
        centre, radius = plate_3d.extent(faces)
        self.assertEqual(centre, (50.0, 20.0, 1.5))
        self.assertGreaterEqual(radius, math.dist(centre, (0, 0, 0)) - 1e-9)
        self.assertEqual(plate_3d.extent([]), ((0.0, 0.0, 0.0), 1.0))


class DrawingOrderTests(unittest.TestCase):
    def test_from_above_walls_come_before_the_cap_and_engraving_last(self):
        faces = plate_3d.plate_faces([circle(0, 0, 30), circle(5, 5, 4, ccw=False)], [rect(-10, -3, 10, 3)], 3.0)
        order = plate_3d.visible_faces(faces, math.radians(-30), math.radians(40))
        kinds = [("cap" if abs(f.normal[2]) > 0.5 else "wall", f.kind) for f, *_ in order]
        first_cap = kinds.index(("cap", "body"))
        self.assertTrue(all(k == ("wall", "body") for k in kinds[:first_cap]))
        self.assertEqual(kinds[-1], ("cap", "engrave"))
        self.assertEqual(kinds.count(("cap", "body")), 1)                     # le dessous est de dos

    def test_stacked_layers_are_drawn_bottom_up_from_above_and_reversed_from_below(self):
        base = plate_3d.extrude(plate_3d.regions_of([rect(0, 0, 40, 20)]), 0, 3, "base", 0)
        letters = plate_3d.extrude(plate_3d.regions_of([rect(10, 5, 30, 15)]), 3, 6, "letters", 1)
        faces = base + letters
        above = [f.name for f, *_ in plate_3d.visible_faces(faces, 0.3, math.radians(35))]
        self.assertLess(max(i for i, n in enumerate(above) if n == "base"), min(i for i, n in enumerate(above) if n == "letters"))
        below = [f.name for f, *_ in plate_3d.visible_faces(faces, 0.3, -math.radians(35))]
        self.assertLess(max(i for i, n in enumerate(below) if n == "letters"), min(i for i, n in enumerate(below) if n == "base"))

    def test_engraving_hidden_from_below(self):
        faces = plate_3d.plate_faces([rect(0, 0, 40, 20)], [rect(5, 5, 15, 15)], 3.0)
        order = plate_3d.visible_faces(faces, 0.0, -math.radians(40))
        self.assertFalse([f for f, *_ in order if f.kind == "engrave"])

    def test_shade_is_between_dark_and_bright(self):
        faces = plate_3d.plate_faces([rect(0, 0, 40, 20)], thickness=3.0)
        for _f, _pts, _holes, shade in plate_3d.visible_faces(faces, -0.5, 0.7):
            self.assertGreaterEqual(shade, 0.45)
            self.assertLessEqual(shade, 1.0)

    def test_large_outline_is_fast_enough_to_rotate(self):
        loops = [circle(0, 0, 60, 3000)] + [circle(-45 + 9 * i, 0, 3, 400, ccw=False) for i in range(11)]
        started = time.perf_counter()
        faces = plate_3d.plate_faces(loops, thickness=3.0)
        build = time.perf_counter() - started
        started = time.perf_counter()
        for k in range(5):
            plate_3d.visible_faces(faces, 0.1 * k, 0.7)
        draw = (time.perf_counter() - started) / 5
        self.assertLess(build, 3.0)
        self.assertLess(draw, 0.5)


class MaterialTests(unittest.TestCase):
    def test_every_material_has_an_engraving_colour(self):
        for key in box_3d.MATERIALS:
            self.assertIn(key, plate_3d.ENGRAVE_COLORS)
            self.assertEqual(len(plate_3d.engrave_color(key)), 3)
        self.assertEqual(plate_3d.engrave_color("inconnu"), plate_3d.ENGRAVE_COLORS[box_3d.DEFAULT_MATERIAL])

    def test_engraving_is_darker_on_wood_and_lighter_on_black_acrylic(self):
        for key in ("plywood", "birch", "oak", "walnut", "mdf"):
            self.assertLess(sum(plate_3d.engrave_color(key)), sum(box_3d.MATERIALS[key][0]))
        self.assertGreater(sum(plate_3d.engrave_color("acrylic_black")), sum(box_3d.MATERIALS["acrylic_black"][0]))

    def test_grain_only_on_big_wood_caps(self):
        big = plate_3d.plate_faces([rect(0, 0, 80, 30)], thickness=3.0)
        cap = next(f for f in big if f.normal == (0.0, 0.0, 1.0))
        wall = next(f for f in big if abs(f.normal[2]) < 0.5)
        lines = plate_3d.grain_lines(cap, 1.0)
        self.assertGreater(len(lines), 10)
        for a, b, alpha in lines:
            self.assertEqual(a[2], 3.0)
            self.assertAlmostEqual(a[1], b[1])                                  # lignes parallèles à X
            self.assertTrue(0 <= alpha <= 255)
        self.assertEqual(plate_3d.grain_lines(cap, 0.0), [])                    # acrylique : uni
        self.assertEqual(plate_3d.grain_lines(wall, 1.0), [])
        small = plate_3d.plate_faces([rect(0, 0, 5, 5)], thickness=3.0)
        self.assertEqual(plate_3d.grain_lines(next(f for f in small if f.normal == (0.0, 0.0, 1.0)), 1.0), [])


if __name__ == "__main__":
    unittest.main()
