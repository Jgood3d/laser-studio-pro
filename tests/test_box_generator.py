"""Générateur de boîte (vector/box_generator.py) : géométrie, couvercles, cloisons.

Contrôle 3D : chaque panneau est découpé en cellules rectangulaires, replacées dans l'espace de la
boîte (X largeur, Y profondeur, Z hauteur). Deux pièces ne doivent jamais se chevaucher, et, avec un
jeu nul, le volume total de matière est exactement celui de la boîte assemblée (aucun vide dans
les assemblages)."""
import itertools
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector import box_generator as bg  # noqa: E402

EPS = 1e-6


# ----------------------------------------------------------------------
# Passage d'un panneau (u, v, profondeur) à l'espace 3D
# ----------------------------------------------------------------------
def _mapping(name, p, result):
    """Fonction (u, v, f) -> (x, y, z), f = fraction d'épaisseur 0..1 (de l'extérieur vers l'intérieur
    pour les parois ; de bas en haut pour les plaques horizontales)."""
    W, D, H = result.outer
    t, cl = p.thickness, p.clearance
    kind = bg.lid_kind(p)
    half = cl / 2.0
    if name == "front":
        return lambda u, v, f: (u, f * t, v)
    if name == "back":
        return lambda u, v, f: (W - u, D - t + f * t, v)
    if name == "left":
        return lambda u, v, f: (f * t, D - u, v)
    if name == "right":
        return lambda u, v, f: (W - t + f * t, u, v)
    if name == "bottom":
        return lambda u, v, f: (W - u, v, f * t)
    if name == "top":
        if kind == "sliding":
            _, front_h = bg.wall_heights(p, H)
            return lambda u, v, f: (half + u, v, front_h + half + f * t)
        return lambda u, v, f: (u, v, H - t + f * t)
    if name == "lip":
        return lambda u, v, f: (t + half + u, t + half + v, H - 2 * t + f * t)
    if name.startswith("divider_x"):
        k = int(name[len("divider_x"):]) - 1
        pos = bg.divider_positions(W, int(p.dividers_x), t)[k]
        return lambda u, v, f: (pos + f * t, u, v)
    if name.startswith("divider_y"):
        k = int(name[len("divider_y"):]) - 1
        pos = bg.divider_positions(D, int(p.dividers_y), t)[k]
        return lambda u, v, f: (u, pos + f * t, v)
    raise KeyError(name)


def _inside(poly, x, y):
    """Point dans un polygone (lancer de rayon)."""
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def _cells(panel):
    """Rectangles (u0, v0, u1, v1) qui recouvrent la matière du panneau (contour moins trous)."""
    loops = [panel.cut] + list(panel.holes)
    us = sorted({round(q[0], 9) for loop in loops for q in loop})
    vs = sorted({round(q[1], 9) for loop in loops for q in loop})
    cells = []
    for u0, u1 in zip(us, us[1:]):
        for v0, v1 in zip(vs, vs[1:]):
            cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            if _inside(panel.cut, cu, cv) and not any(_inside(h, cu, cv) for h in panel.holes):
                cells.append((u0, v0, u1, v1))
    return cells


def solids(p, result):
    """{nom: [boîtes 3D (x0, y0, z0, x1, y1, z1)]}."""
    out = {}
    for panel in result.panels:
        fn = _mapping(panel.name, p, result)
        boxes = []
        for u0, v0, u1, v1 in _cells(panel):
            a, b = fn(u0, v0, 0.0), fn(u1, v1, 1.0)
            boxes.append(tuple(min(a[i], b[i]) for i in range(3)) + tuple(max(a[i], b[i]) for i in range(3)))
        out[panel.name] = boxes
    return out


def overlap_volume(a, b):
    dx = min(a[3], b[3]) - max(a[0], b[0])
    dy = min(a[4], b[4]) - max(a[1], b[1])
    dz = min(a[5], b[5]) - max(a[2], b[2])
    return dx * dy * dz if dx > EPS and dy > EPS and dz > EPS else 0.0


def volume(boxes):
    return sum((b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2]) for b in boxes)


def collisions(all_solids):
    """[(nom_a, nom_b, volume)] pour chaque paire de pièces qui se chevauchent."""
    found = []
    for (na, ba), (nb, bb) in itertools.combinations(all_solids.items(), 2):
        total = sum(overlap_volume(x, y) for x in ba for y in bb)
        if total > 1e-4:
            found.append((na, nb, total))
    return found


def make(**kw):
    defaults = dict(width=100.0, depth=70.0, height=50.0, thickness=3.0, kerf=0.0, clearance=0.0, gap=3.0)
    defaults.update(kw)
    return bg.BoxParams(**defaults)


def check(test, p):
    result = bg.build_box(p)
    s = solids(p, result)
    test.assertEqual(collisions(s), [])
    return result, s, sum(volume(b) for b in s.values())


def shell_volume(W, D, H, t):
    return W * D * H - (W - 2 * t) * (D - 2 * t) * (H - 2 * t)


class LidTypeTests(unittest.TestCase):
    def test_finger_lid_is_the_original_box(self):
        p = make()
        result, _s, vol = check(self, p)
        self.assertEqual(sorted(x.name for x in result.panels), sorted(bg.FACE_NAMES))
        self.assertAlmostEqual(vol, shell_volume(100, 70, 50, 3), places=3)

    def test_open_box_has_no_top(self):
        p = make(lid=False)
        result, _s, vol = check(self, p)
        self.assertNotIn("top", [x.name for x in result.panels])
        self.assertEqual(len(result.panels), 5)
        self.assertAlmostEqual(vol, 100 * 70 * 50 - 94 * 64 * 47, places=3)

    def test_lip_lid(self):
        p = make(lid_type="lip")
        result, _s, vol = check(self, p)
        names = [x.name for x in result.panels]
        self.assertIn("top", names)
        self.assertIn("lip", names)
        expected = (100 * 70 * 47 - 94 * 64 * 44) + 100 * 70 * 3 + 94 * 64 * 3
        self.assertAlmostEqual(vol, expected, places=3)
        top = next(x for x in result.panels if x.name == "top")
        self.assertEqual((top.width, top.height), (100, 70))

    def test_sliding_lid(self):
        p = make(lid_type="sliding", clearance=0.0)
        result, s, vol = check(self, p)
        front = next(x for x in result.panels if x.name == "front")
        self.assertAlmostEqual(front.height, 50 - 2 * 3)                  # façade abaissée
        lid = next(x for x in result.panels if x.name == "top")
        self.assertAlmostEqual(lid.height, 70 - 2 * 3)
        # La rainure est un trou dans le contour des parois gauche et droite : ils ne se touchent pas.
        for side in ("left", "right"):
            panel = next(x for x in result.panels if x.name == side)
            self.assertGreater(len(panel.outline), 4)

    def test_sliding_lid_slot_height_follows_clearance(self):
        p = make(lid_type="sliding", clearance=0.3)
        result, _s, _v = check(self, p)
        front = next(x for x in result.panels if x.name == "front")
        self.assertAlmostEqual(front.height, 50 - 2 * 3 - 0.3)
        left = next(x for x in result.panels if x.name == "left")
        ys = sorted({round(q[1], 6) for q in left.outline})
        # La rainure occupe [hauteur de la façade, hauteur - t] : épaisseur t + jeu.
        self.assertIn(round(front.height, 6), ys)
        self.assertIn(round(50 - 3, 6), ys)

    def test_closed_lid_flag_off_overrides_type(self):
        for kind in ("lip", "sliding", "finger"):
            result = bg.build_box(make(lid=False, lid_type=kind))
            self.assertEqual(result.lid_type, "none")
            self.assertEqual(len(result.panels), 5)

    def test_every_type_is_collision_free_with_kerf_and_clearance(self):
        for kind in bg.LID_TYPES:
            for dims in ((100, 70, 50), (60, 60, 30), (151.7, 83.3, 47.9)):
                p = make(width=dims[0], depth=dims[1], height=dims[2], lid_type=kind, kerf=0.12, clearance=0.15)
                bg.build_box(p)                                           # pas d'erreur de contour
                p0 = make(width=dims[0], depth=dims[1], height=dims[2], lid_type=kind, clearance=0.15)
                check(self, p0)

    def test_inner_dimensions_with_lid_types(self):
        for kind in ("lip", "sliding"):
            result = bg.build_box(make(dimensions="inner", lid_type=kind))
            self.assertEqual(result.outer, (106.0, 76.0, 56.0))


class DividerTests(unittest.TestCase):
    def test_one_divider_each_way_is_exact_with_zero_clearance(self):
        p = make(dividers_x=1, dividers_y=1)
        result, s, vol = check(self, p)
        names = [x.name for x in result.panels]
        self.assertIn("divider_x1", names)
        self.assertIn("divider_y1", names)
        height = 50 - 3 - 3                                                # entre fond et couvercle
        inner = 94 * 64 * height
        union = 3 * 64 * height + 3 * 94 * height - 3 * 3 * height
        self.assertAlmostEqual(vol, shell_volume(100, 70, 50, 3) + union, places=3)
        self.assertEqual(inner and result.dividers, (1, 1))

    def test_several_dividers_open_box(self):
        p = make(lid=False, dividers_x=3, dividers_y=2)
        result, s, vol = check(self, p)
        self.assertEqual(len(result.panels), 5 + 5)
        height = 50 - 3
        union = 3 * (3 * 64 * height) + 2 * (3 * 94 * height) - 3 * 2 * 3 * 3 * height
        self.assertAlmostEqual(vol, 100 * 70 * 50 - 94 * 64 * 47 + union, places=3)

    def test_walls_get_slots_as_holes(self):
        p = make(dividers_x=2, dividers_y=0)
        result = bg.build_box(p)
        by = {x.name: x for x in result.panels}
        self.assertEqual(len(by["front"].holes), 2)
        self.assertEqual(len(by["back"].holes), 2)
        self.assertEqual(len(by["bottom"].holes) % 2, 0)                  # mêmes languettes pour chaque cloison
        self.assertGreaterEqual(len(by["bottom"].holes), 2)
        self.assertEqual(by["left"].holes, [])
        self.assertEqual(by["top"].holes, [])

    def test_holes_shrink_with_kerf(self):
        thin = bg.build_box(make(dividers_x=1, kerf=0.0)).panels
        fat = bg.build_box(make(dividers_x=1, kerf=0.2)).panels
        w_thin = _width(next(x for x in thin if x.name == "front").holes[0])
        w_fat = _width(next(x for x in fat if x.name == "front").holes[0])
        self.assertAlmostEqual(w_thin - w_fat, 0.2, places=6)

    def test_clearance_widens_slots_and_notches(self):
        a = bg.build_box(make(dividers_x=1, dividers_y=1, clearance=0.0))
        b = bg.build_box(make(dividers_x=1, dividers_y=1, clearance=0.2))
        wa = _width(next(x for x in a.panels if x.name == "front").holes[0])
        wb = _width(next(x for x in b.panels if x.name == "front").holes[0])
        self.assertAlmostEqual(wb - wa, 0.2, places=6)

    def test_dividers_with_every_lid_type_do_not_collide(self):
        for kind in bg.LID_TYPES:
            for lid in (True, False):
                for nx, ny in ((1, 0), (0, 2), (2, 2), (3, 1)):
                    p = make(width=140, depth=110, height=60, lid=lid, lid_type=kind,
                             dividers_x=nx, dividers_y=ny, clearance=0.1)
                    check(self, p)
                    bg.build_box(make(width=140, depth=110, height=60, lid=lid, lid_type=kind,
                                      dividers_x=nx, dividers_y=ny, clearance=0.1, kerf=0.15))

    def test_divider_tops_stay_under_the_lid(self):
        for kind, lid, top in (("finger", True, 47), ("lip", True, 44), ("sliding", True, 44), ("finger", False, 50)):
            p = make(lid=lid, lid_type=kind, dividers_x=1, clearance=0.0)
            result = bg.build_box(p)
            divider = next(x for x in result.panels if x.name == "divider_x1")
            self.assertAlmostEqual(divider.height, top - 3 + 3, msg=f"{kind} {lid}")      # hauteur + languettes du bas

    def test_odd_sizes_and_fractional_positions(self):
        p = make(width=137.3, depth=91.7, height=58.1, thickness=2.5, dividers_x=2, dividers_y=3, clearance=0.0)
        check(self, p)

    def test_compartments_are_equal(self):
        positions = bg.divider_positions(100, 3, 3)
        gaps = [positions[0] - 3] + [b - a - 3 for a, b in zip(positions, positions[1:])] + [100 - 3 - (positions[-1] + 3)]
        for g in gaps:
            self.assertAlmostEqual(g, gaps[0])
        self.assertAlmostEqual(sum(gaps) + 3 * 3, 94)

    def test_layout_contains_dividers_and_fits_max_width(self):
        p = make(dividers_x=2, dividers_y=2, max_width=300.0)
        result = bg.build_box(p)
        self.assertLessEqual(result.width, 300.0 + 1e-6)
        boxes = [x.bounds() for x in result.panels]
        for (a0, b0, a1, b1), (c0, d0, c1, d1) in itertools.combinations(boxes, 2):
            apart = a1 <= c0 + 1e-9 or c1 <= a0 + 1e-9 or b1 <= d0 + 1e-9 or d1 <= b0 + 1e-9
            self.assertTrue(apart)


def _width(loop):
    xs = [q[0] for q in loop]
    ys = [q[1] for q in loop]
    return min(max(xs) - min(xs), max(ys) - min(ys))


class ValidationTests(unittest.TestCase):
    def code(self, **kw):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(make(**kw))
        return ctx.exception.code

    def test_bad_lid_type(self):
        self.assertEqual(self.code(lid_type="nope"), "lid_type")

    def test_bad_clearance(self):
        self.assertEqual(self.code(clearance=-0.1), "clearance")
        self.assertEqual(self.code(clearance=3.0), "clearance")

    def test_bad_divider_count(self):
        self.assertEqual(self.code(dividers_x=-1), "dividers")
        self.assertEqual(self.code(dividers_y=bg.MAX_DIVIDERS + 1), "dividers")

    def test_compartment_too_small(self):
        self.assertEqual(self.code(dividers_x=9), "compartment_too_small")

    def test_dividers_too_low(self):
        self.assertEqual(self.code(height=14, dividers_x=1), "dividers_too_low")

    def test_sliding_lid_needs_height_for_the_front(self):
        self.assertEqual(self.code(height=14, lid_type="sliding"), "too_small")

    def test_legacy_defaults_unchanged(self):
        result = bg.build_box(make(clearance=0.1))
        self.assertEqual(sorted(x.name for x in result.panels), sorted(bg.FACE_NAMES))
        self.assertEqual(result.finger_counts, {"W": 11, "D": 7, "H": 5})


class OutlineTests(unittest.TestCase):
    def test_loops_report_holes_clockwise(self):
        loops = bg.rectilinear_loops([(0, 0, 10, 10)], [(3, 3, 6, 6)])
        areas = sorted(bg.polygon_area(l) for l in loops)
        self.assertAlmostEqual(areas[0], -9.0)
        self.assertAlmostEqual(areas[1], 100.0)

    def test_outline_wrapper_still_rejects_several_outlines(self):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.rectilinear_outline(10, 10, [(3, 3, 6, 6)])
        self.assertEqual(ctx.exception.code, "several_outlines")

    def test_touching_hole_is_pinched(self):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.rectilinear_loops([(0, 0, 10, 10)], [(0, 0, 3, 3), (3, 3, 6, 6)])
        self.assertEqual(ctx.exception.code, "pinched_panel")


if __name__ == "__main__":
    unittest.main()
