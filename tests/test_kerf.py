"""Compensation du kerf des calques de découpe : décalage des contours, G-Code et réglages du calque."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.vector.kerf import compensate_kerf, offset_polygon, signed_area  # noqa: E402
from laser_studio.vector.tabs import closed_points  # noqa: E402

try:
    from laser_studio.gcode.vector import build_vector_layers_gcode
    from laser_studio.models.layer_modes import MODE_CUT, MODE_MARK
    from laser_studio.models.layers import LaserLayer, LayersModel, validated_settings
    HAS_MODEL = True
except ImportError:                       # PyQt6 non importable
    HAS_MODEL = False

SQUARE = [(0, 0), (40, 0), (40, 40), (0, 40), (0, 0)]
HOLE = [(10, 10), (30, 10), (30, 30), (10, 30), (10, 10)]
L_SHAPE = [(0, 0), (20, 0), (20, 10), (10, 10), (10, 20), (0, 20), (0, 0)]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcode_reader import burn_paths  # noqa: E402


def area(poly):
    return abs(signed_area(closed_points(poly)[:-1]))


def length(run):
    return sum(math.hypot(run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]) for i in range(len(run) - 1))


class OffsetTests(unittest.TestCase):
    def test_square_grows_and_shrinks_by_the_distance(self):
        self.assertAlmostEqual(area(offset_polygon(SQUARE, 0.1)), 40.2 ** 2)
        self.assertAlmostEqual(area(offset_polygon(SQUARE, -0.1)), 39.8 ** 2)

    def test_direction_of_travel_does_not_matter(self):
        clockwise = list(reversed(SQUARE))
        self.assertAlmostEqual(area(offset_polygon(clockwise, 0.1)), 40.2 ** 2)

    def test_concave_corner_is_joined_exactly(self):
        # Contour à angles droits : aire = A + P·d + d²·(angles convexes − angles rentrants) = 300 + 8 + 0,04.
        self.assertAlmostEqual(area(offset_polygon(L_SHAPE, 0.1)), 308.04)
        self.assertAlmostEqual(area(offset_polygon(L_SHAPE, -0.1)), 292.04)

    def test_circle_radius_changes_by_the_distance(self):
        circle = [(10 * math.cos(2 * math.pi * i / 90), 10 * math.sin(2 * math.pi * i / 90)) for i in range(91)]
        shifted = offset_polygon(circle, 0.075)
        self.assertAlmostEqual(min(math.hypot(*p) for p in shifted), 10.075, places=3)

    def test_sharp_corner_is_bevelled_not_spiked(self):
        spike = [(0, 0), (30, 0), (0, 3), (0, 0)]
        shifted = offset_polygon(spike, 0.1)
        self.assertGreater(len(shifted), 4)                      # le sommet très aigu est biseauté
        self.assertGreater(area(shifted), area(spike))
        # Un coude complet ferait une pointe de plusieurs mm (angle d'environ 6°) : le biseau la limite à 2 fois
        # le décalage au-delà du sommet d'origine.
        self.assertLess(max(x for x, _ in shifted), 30 + 2 * 0.1 + 1e-9)

    def test_detail_thinner_than_the_offset_is_refused(self):
        self.assertIsNone(offset_polygon([(0, 0), (40, 0), (40, 0.1), (0, 0.1), (0, 0)], -0.1))
        self.assertIsNone(offset_polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], -0.6))

    def test_degenerate_input_is_refused(self):
        self.assertIsNone(offset_polygon([(0, 0), (1, 1)], 0.1))
        self.assertIsNone(offset_polygon([(0, 0), (5, 0), (10, 0), (0, 0)], 0.1))     # aire nulle


class CompensationTests(unittest.TestCase):
    def test_pieces_grow_and_holes_shrink(self):
        result, done, failed = compensate_kerf([SQUARE, HOLE], 0.2)
        self.assertEqual((done, failed), (2, 0))
        self.assertAlmostEqual(area(result[0]), 40.2 ** 2)
        self.assertAlmostEqual(area(result[1]), 19.8 ** 2)

    def test_order_of_the_paths_is_kept(self):
        result, _, _ = compensate_kerf([HOLE, SQUARE], 0.2)
        self.assertAlmostEqual(area(result[0]), 19.8 ** 2)
        self.assertAlmostEqual(area(result[1]), 40.2 ** 2)

    def test_open_paths_are_left_alone(self):
        line = [(0, 0), (10, 0), (10, 10)]
        result, done, failed = compensate_kerf([line, SQUARE], 0.2)
        self.assertEqual(result[0], line)
        self.assertEqual((done, failed), (1, 0))

    def test_hole_smaller_than_the_kerf_is_kept_and_counted(self):
        tiny_hole = [(5, 5), (5.2, 5), (5.2, 5.2), (5, 5.2), (5, 5)]
        result, done, failed = compensate_kerf([SQUARE, tiny_hole], 0.5)
        self.assertEqual((done, failed), (1, 1))
        self.assertEqual(result[1], tiny_hole)

    def test_zero_kerf_changes_nothing(self):
        self.assertEqual(compensate_kerf([SQUARE], 0.0), ([SQUARE], 0, 0))


def _data(mode, polygons, **layer):
    base = {"name": "L", "mode": mode, "speed": 300, "power": 80.0, "passes": 1, "line_interval": 0.1}
    base.update(layer)
    return {"layer": base, "polygons": polygons, "polygon_groups": [polygons]}


def _build(data, **kwargs):
    return build_vector_layers_gcode({"a": data}, 0.0, 0.0, 100.0, "M4", 1000, **kwargs)[0]


def _cut_runs_of(gcode):
    """Tracés coupés (laser allumé), d'un seul tenant."""
    return burn_paths(gcode)


@unittest.skipUnless(HAS_MODEL, "génération du G-Code non importable ici")
class KerfGcodeTests(unittest.TestCase):
    def test_without_kerf_the_contours_are_cut_as_drawn(self):
        runs = _cut_runs_of(_build(_data(MODE_CUT, [SQUARE])))
        self.assertAlmostEqual(length(runs[0]), 160.0)

    def test_kerf_shifts_the_cut_paths(self):
        gcode = _build(_data(MODE_CUT, [SQUARE, HOLE], kerf=True, kerf_width=0.2))
        runs = _cut_runs_of(gcode)
        self.assertEqual(sorted(round(length(r), 3) for r in runs), [79.2, 160.8])    # trou 19,8 · pièce 40,2
        self.assertTrue(any("Compensation du kerf : 0.2 mm (2 contours" in line for line in gcode))

    def test_unchecked_kerf_keeps_the_width_but_changes_nothing(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], kerf=False, kerf_width=0.2))
        self.assertAlmostEqual(length(_cut_runs_of(gcode)[0]), 160.0)
        self.assertFalse(any("Compensation du kerf" in line for line in gcode))

    def test_marking_layer_ignores_kerf(self):
        runs = _cut_runs_of(_build(_data(MODE_MARK, [SQUARE], kerf=True, kerf_width=0.2)))
        self.assertAlmostEqual(length(runs[0]), 160.0)

    def test_skipped_contour_is_reported_in_the_gcode(self):
        tiny_hole = [(5, 5), (5.2, 5), (5.2, 5.2), (5, 5.2), (5, 5)]
        gcode = _build(_data(MODE_CUT, [SQUARE, tiny_hole], kerf=True, kerf_width=0.5))
        self.assertTrue(any("ATTENTION : 1 contour(s)" in line for line in gcode))

    def test_old_layer_without_kerf_settings_is_unchanged(self):
        data = _data(MODE_CUT, [SQUARE])
        self.assertNotIn("kerf", data["layer"])
        self.assertAlmostEqual(length(_cut_runs_of(_build(data))[0]), 160.0)

    def test_kerf_and_tabs_work_together(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], kerf=True, kerf_width=0.2, tabs=True, tab_count=4, tab_width=1.0))
        runs = _cut_runs_of(gcode)
        self.assertEqual(len(runs), 4)
        self.assertAlmostEqual(sum(length(r) for r in runs), 160.8 - 4.0, places=2)

    def test_inner_contours_are_still_cut_first(self):
        gcode = _build(_data(MODE_CUT, [SQUARE, HOLE], kerf=True, kerf_width=0.2), safe_cut_order=True)
        self.assertAlmostEqual(length(_cut_runs_of(gcode)[0]), 79.2)


@unittest.skipUnless(HAS_MODEL, "modèle des calques non importable ici")
class KerfLayerSettingsTests(unittest.TestCase):
    def test_new_layer_has_kerf_off_with_a_default_width(self):
        layer = LaserLayer()
        self.assertFalse(layer.kerf)
        self.assertAlmostEqual(layer.kerf_width, 0.15)

    def test_settings_are_converted_and_clamped(self):
        self.assertEqual(validated_settings({"kerf": 1, "kerf_width": "0.2"}), {"kerf": True, "kerf_width": 0.2})
        self.assertEqual(validated_settings({"kerf_width": 0})["kerf_width"], 0.01)
        self.assertEqual(validated_settings({"kerf_width": 50})["kerf_width"], 2.0)
        self.assertEqual(validated_settings({"kerf_width": "abc"}), {})
        self.assertEqual(validated_settings({"kerf_width": float("nan")}), {})

    def test_settings_survive_a_save_and_a_reload(self):
        model = LayersModel()
        model.update(model.layers[1].id, kerf=True, kerf_width=0.22)
        reloaded = LayersModel()
        reloaded.load_list(model.to_list())
        cut = next(layer for layer in reloaded.layers if layer.role == "cut")
        self.assertEqual((cut.kerf, cut.kerf_width), (True, 0.22))

    def test_project_saved_before_kerf_loads_with_kerf_off(self):
        saved = [{k: v for k, v in layer.items() if k not in ("kerf", "kerf_width")}
                 for layer in LayersModel().to_list()]
        model = LayersModel()
        model.load_list(saved)
        self.assertTrue(all(not layer.kerf for layer in model.layers))


if __name__ == "__main__":
    unittest.main()
