"""Ordre de découpe sûr : gravure avant découpe, intérieur avant extérieur."""
import math
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import vector_order as vo

try:
    from vector_layers import build_vector_layers_gcode
    HAS_BUILD = callable(build_vector_layers_gcode) and not str(type(build_vector_layers_gcode)).endswith("MagicMock'>")
except ImportError:
    HAS_BUILD = False


def rect(x0, y0, x1, y1, closed=True):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return pts + [pts[0]] if closed else pts


def circle(cx, cy, r, n=48):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return pts + [pts[0]]


class DepthTests(unittest.TestCase):
    def test_nested_contours_get_increasing_depth(self):
        polys = [rect(0, 0, 100, 100), rect(10, 10, 90, 90), rect(30, 30, 60, 60), rect(200, 200, 220, 220)]
        self.assertEqual(vo.nesting_depths(polys), [0, 1, 2, 0])

    def test_circle_hole_inside_a_square(self):
        self.assertEqual(vo.nesting_depths([rect(0, 0, 50, 50), circle(25, 25, 10)]), [0, 1])

    def test_overlapping_but_not_contained_is_not_nested(self):
        self.assertEqual(vo.nesting_depths([rect(0, 0, 50, 50), rect(25, 25, 80, 80)]), [0, 0])
        self.assertEqual(vo.nesting_depths([rect(0, 0, 50, 50), rect(40, 10, 60, 20)]), [0, 0])

    def test_inside_the_bounding_box_but_outside_the_shape(self):
        l_shape = [(0, 0), (60, 0), (60, 20), (20, 20), (20, 60), (0, 60), (0, 0)]
        self.assertEqual(vo.nesting_depths([l_shape, rect(35, 35, 50, 50)]), [0, 0])
        self.assertEqual(vo.nesting_depths([l_shape, rect(5, 5, 15, 15)]), [0, 1])

    def test_duplicates_lines_and_empty_inputs(self):
        self.assertEqual(vo.nesting_depths([rect(0, 0, 10, 10), rect(0, 0, 10, 10)]), [0, 0])
        line = [(10, 10), (20, 20)]
        self.assertEqual(vo.nesting_depths([rect(0, 0, 50, 50), line, [(30, 30)]]), [0, 1, 1])
        self.assertEqual(vo.nesting_depths([line, rect(30, 30, 40, 40)]), [0, 0])
        self.assertEqual(vo.nesting_depths([]), [])
        self.assertEqual(vo.nesting_depths([[]]), [0])

    def test_open_polygons_still_work_as_containers_like_the_generator_treats_them(self):
        self.assertEqual(vo.nesting_depths([rect(0, 0, 50, 50, closed=False), circle(25, 25, 5)]), [0, 1])


class OrderTests(unittest.TestCase):
    def test_inner_before_outer_and_stable(self):
        outer_a, hole_a = rect(0, 0, 100, 100), circle(50, 50, 10)
        outer_b, hole_b = rect(200, 0, 300, 100), circle(250, 50, 10)
        self.assertEqual(vo.order_polygons_inner_first([outer_a, hole_a, outer_b, hole_b]), [hole_a, hole_b, outer_a, outer_b])
        self.assertEqual(vo.order_polygons_inner_first([outer_a]), [outer_a])
        self.assertEqual(vo.order_polygons_inner_first([]), [])

    def test_three_levels_and_input_untouched(self):
        a, b, c = rect(0, 0, 100, 100), rect(10, 10, 90, 90), rect(20, 20, 80, 80)
        self.assertEqual(vo.order_polygons_inner_first([a, b, c]), [c, b, a])
        self.assertEqual(vo.order_polygons_inner_first([c, a, b]), [c, b, a])
        polys = [a, c]
        copy = list(polys)
        vo.order_polygons_inner_first(polys)
        self.assertEqual(polys, copy)

    def test_layers_engraving_first_then_cutting_keeping_relative_order(self):
        mk = lambda name, mode: (name, {"layer": {"mode": mode}, "polygons": []})
        items = [mk("cut1", "Découpe"), mk("fill", "Gravure Remplie"), mk("cut2", "Découpe"), mk("mark", "Marquage (Contour)")]
        self.assertEqual([i[0] for i in vo.order_layers_for_cutting(items)], ["fill", "mark", "cut1", "cut2"])
        self.assertEqual(vo.order_layers_for_cutting([]), [])


@unittest.skipUnless(HAS_BUILD, "build_vector_layers_gcode non disponible ici")
class GcodeOrderTests(unittest.TestCase):
    def layer(self, name, mode):
        return {"name": name, "mode": mode, "power": 80.0, "speed": 300, "passes": 1, "line_interval": 0.2}

    def build(self, layers, safe):
        return build_vector_layers_gcode(layers, 0.0, 0.0, 400.0, "M4", 1000, safe_cut_order=safe)[0]

    def cut_starts(self, gcode):
        starts, take = [], False
        for line in gcode:
            if line.startswith("; --- CALQUE"):
                take = "[Découpe]" in line
            if take and line.startswith("G0 X"):
                starts.append(line)
        return starts

    def test_holes_are_cut_before_the_outline_in_the_gcode(self):
        layers = {"L": {"layer": self.layer("Découpe", "Découpe"), "polygons": [rect(0, 0, 100, 100), circle(50, 50, 10)]}}
        off, on = self.cut_starts(self.build(layers, False)), self.cut_starts(self.build(layers, True))
        self.assertEqual(len(off), 2)
        self.assertEqual(on, [off[1], off[0]])

    def test_engraving_runs_before_cutting_even_if_listed_after(self):
        layers = {"C": {"layer": self.layer("Contour", "Découpe"), "polygons": [rect(0, 0, 50, 50)]},
                  "G": {"layer": self.layer("Détails", "Marquage (Contour)"), "polygons": [rect(10, 10, 20, 20)]}}
        names = lambda g: [re.search(r"'([^']+)'", l).group(1) for l in g if l.startswith("; --- CALQUE")]
        self.assertEqual(names(self.build(layers, False)), ["Contour", "Détails"])
        self.assertEqual(names(self.build(layers, True)), ["Détails", "Contour"])

    def test_disabled_option_keeps_the_historic_gcode_and_all_geometry(self):
        layers = {"L": {"layer": self.layer("Découpe", "Découpe"), "polygons": [rect(0, 0, 100, 100), circle(50, 50, 10), rect(200, 0, 260, 60), rect(210, 10, 250, 50)]}}
        old = build_vector_layers_gcode(layers, 0.0, 0.0, 400.0, "M4", 1000)
        off, on = self.build(layers, False), self.build(layers, True)
        self.assertEqual(old[0], off)
        on = [l for l in on if not l.startswith("; Ordre de découpe")]
        self.assertEqual(sorted(off), sorted(on))
        self.assertIn("; Ordre de découpe : intérieur avant extérieur", self.build(layers, True))
        self.assertNotIn("; Ordre de découpe : intérieur avant extérieur", off)


class WiringTests(unittest.TestCase):
    def src(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def test_option_is_passed_from_ui_to_worker_to_generator(self):
        self.assertIn("self.chk_safe_cut_order = QCheckBox", self.src("ui_setup_mixin.py"))
        self.assertIn("'safe_cut_order':", self.src("gcode_generation_mixin.py"))
        self.assertIn("safe_cut_order=bool(self.params.get('safe_cut_order', True))", self.src("workers.py"))
        self.assertIn("safe_cut_order=False", self.src("vector_layers.py"))

    def test_project_saves_and_restores_it_with_a_default_of_true(self):
        pj = self.src("project_io_mixin.py")
        self.assertIn('"safe_cut_order": self.chk_safe_cut_order.isChecked()', pj)
        self.assertIn('self.chk_safe_cut_order.setChecked(proj_data.get("safe_cut_order", True))', pj)


if __name__ == "__main__":
    unittest.main()
