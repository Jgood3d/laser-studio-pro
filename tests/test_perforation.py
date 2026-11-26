"""Mode de calque Perforation (découpe en pointillé) : géométrie, G-Code, aperçu et réglages du calque."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcode_reader import burn_paths  # noqa: E402
from laser_studio.vector.perforate import dashes, pattern, perforate  # noqa: E402

try:
    from laser_studio.gcode.preview import KIND_LAYER, is_raster_group
    HAS_PREVIEW = True
except ImportError:
    HAS_PREVIEW = False

try:
    from laser_studio.gcode.vector import build_vector_layers_gcode
    from laser_studio.models.layer_modes import (
        CONTOUR_MODES, LAYER_MODE_TR_KEYS, LAYER_MODES, MODE_CUT, MODE_MARK, MODE_PERF, normalize_mode,
    )
    from laser_studio.models.layers import LaserLayer, LayersModel, validated_settings
    HAS_MODEL = True
except ImportError:                       # PyQt6 non importable
    HAS_MODEL = False

SQUARE = [(0, 0), (40, 0), (40, 40), (0, 40), (0, 0)]
LINE = [(0, 0), (100, 0)]


def length(run):
    return sum(math.hypot(run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]) for i in range(len(run) - 1))


class PatternTests(unittest.TestCase):
    def test_closed_path_gets_a_whole_number_of_periods(self):
        n, d, g = pattern(160.0, 2.0, 1.0, closed=True)
        self.assertEqual(n, 53)
        self.assertAlmostEqual(n * (d + g), 160.0)
        self.assertAlmostEqual(d / g, 2.0)                       # le rapport trait / vide est conservé

    def test_open_path_starts_and_ends_with_a_dash(self):
        n, d, g = pattern(100.0, 2.0, 1.0, closed=False)
        self.assertAlmostEqual(n * d + (n - 1) * g, 100.0)
        self.assertAlmostEqual(d / g, 2.0)

    def test_path_shorter_than_a_dash_is_one_dash(self):
        self.assertEqual(pattern(1.5, 2.0, 1.0, closed=False), (1, 1.5, 0.0))

    def test_senseless_settings_give_one_dash(self):
        self.assertEqual(pattern(50.0, 0.0, 1.0, closed=False)[0], 1)
        self.assertEqual(pattern(50.0, 2.0, 0.0, closed=True)[0], 1)


class DashGeometryTests(unittest.TestCase):
    def test_closed_contour_keeps_the_dash_share_of_its_length(self):
        runs = dashes(SQUARE, 2.0, 1.0)
        self.assertEqual(len(runs), 53)
        self.assertAlmostEqual(sum(length(r) for r in runs), 160.0 * 2 / 3, places=6)

    def test_closed_contour_is_not_closed_by_a_dash(self):
        runs = dashes(SQUARE, 2.0, 1.0)
        self.assertEqual(runs[0][0], (0.0, 0.0))                  # le premier trait part du point de départ
        end = runs[-1][-1]
        self.assertGreater(math.hypot(end[0], end[1]), 0.5)       # le dernier finit avant : un vide les sépare

    def test_open_line_starts_and_ends_on_a_dash(self):
        runs = dashes(LINE, 2.0, 1.0)
        self.assertEqual(runs[0][0], (0.0, 0.0))
        self.assertAlmostEqual(runs[-1][-1][0], 100.0)
        self.assertEqual(len(runs), 34)

    def test_gaps_are_even(self):
        runs = dashes(LINE, 2.0, 1.0)
        gaps = [runs[i + 1][0][0] - runs[i][-1][0] for i in range(len(runs) - 1)]
        self.assertAlmostEqual(max(gaps), min(gaps), places=6)

    def test_dash_follows_a_corner(self):
        runs = dashes([(0, 0), (10, 0), (10, 10)], 6.0, 2.0)
        self.assertIn((10.0, 0.0), runs[1])                       # le trait du milieu passe l'angle

    def test_short_path_is_cut_in_full(self):
        path = [(0, 0), (1.5, 0)]
        self.assertEqual(dashes(path, 2.0, 1.0), [path])

    def test_zero_settings_change_nothing(self):
        self.assertEqual(dashes(SQUARE, 0.0, 1.0), [SQUARE])
        self.assertEqual(dashes(SQUARE, 2.0, 0.0), [SQUARE])

    def test_perforate_counts_the_dashes(self):
        runs, count = perforate([LINE, SQUARE], 2.0, 1.0)
        self.assertEqual(count, len(runs))
        self.assertEqual(count, 34 + 53)


def _data(mode, polygons, **layer):
    base = {"name": "L", "mode": mode, "speed": 300, "power": 80.0, "passes": 1, "line_interval": 0.1}
    base.update(layer)
    return {"layer": base, "polygons": polygons, "polygon_groups": [polygons]}


def _build(data, **kwargs):
    return build_vector_layers_gcode({"a": data}, 0.0, 0.0, 100.0, "M4", 1000, **kwargs)[0]


@unittest.skipUnless(HAS_MODEL, "génération du G-Code non importable ici")
class PerforationGcodeTests(unittest.TestCase):
    def test_a_perforated_line_is_cut_as_dashes(self):
        gcode = _build(_data(MODE_PERF, [LINE], perf_dash=2.0, perf_gap=1.0))
        paths = burn_paths(gcode)
        self.assertEqual(len(paths), 34)
        self.assertAlmostEqual(sum(length(p) for p in paths), 34 * 2.0 * 100.0 / 101.0, delta=0.01)   # 34 traits ajustés
        self.assertTrue(any("Perforation : trait 2 mm, vide 1 mm (34 traits)" in line for line in gcode))

    def test_a_cut_layer_is_not_perforated(self):
        paths = burn_paths(_build(_data(MODE_CUT, [LINE], perf_dash=2.0, perf_gap=1.0)))
        self.assertEqual(len(paths), 1)

    def test_a_marking_layer_is_not_perforated(self):
        paths = burn_paths(_build(_data(MODE_MARK, [LINE], perf_dash=2.0, perf_gap=1.0)))
        self.assertEqual(len(paths), 1)

    def test_cut_only_options_do_not_apply(self):
        data = _data(MODE_PERF, [SQUARE], perf_dash=2.0, perf_gap=1.0, kerf=True, kerf_width=0.2,
                     tabs=True, tab_count=4, tab_width=1.0, lead=True, lead_radius=1.0)
        gcode = _build(data)
        self.assertFalse(any(word in line for line in gcode
                             for word in ("Compensation du kerf", "Ponts de maintien", "Arcs d'entrée")))
        self.assertAlmostEqual(sum(length(p) for p in burn_paths(gcode)), 160.0 * 2 / 3, places=2)

    def test_every_pass_is_perforated(self):
        paths = burn_paths(_build(_data(MODE_PERF, [LINE], perf_dash=2.0, perf_gap=1.0, passes=2)))
        self.assertEqual(len(paths), 68)

    def test_layer_without_perforation_settings_uses_the_defaults(self):
        data = _data(MODE_PERF, [LINE])
        self.assertNotIn("perf_dash", data["layer"])
        self.assertEqual(len(burn_paths(_build(data))), 34)       # 2 mm de trait, 1 mm de vide

    def test_perforation_runs_before_the_cuts(self):
        cut = [(0, 10), (100, 10)]
        items = {"cut": _data(MODE_CUT, [cut]), "perf": _data(MODE_PERF, [LINE], perf_dash=2.0, perf_gap=1.0)}
        gcode = build_vector_layers_gcode(items, 0.0, 0.0, 100.0, "M4", 1000, safe_cut_order=True)[0]
        paths = burn_paths(gcode)
        self.assertEqual(paths[-1][0], (0.0, 10.0))               # la découpe pleine passe en dernier


@unittest.skipUnless(HAS_MODEL, "modèle des calques non importable ici")
class PerforationLayerTests(unittest.TestCase):
    def test_mode_is_registered(self):
        self.assertIn(MODE_PERF, LAYER_MODES)
        self.assertIn(MODE_PERF, CONTOUR_MODES)                   # contour seulement : pas de pas de remplissage
        self.assertIn(MODE_PERF, LAYER_MODE_TR_KEYS)
        self.assertEqual(normalize_mode("perforate"), MODE_PERF)

    def test_new_layer_has_default_perforation(self):
        layer = LaserLayer(mode=MODE_PERF)
        self.assertEqual(layer.mode, MODE_PERF)
        self.assertAlmostEqual(layer.perf_dash, 2.0)
        self.assertAlmostEqual(layer.perf_gap, 1.0)

    def test_settings_are_converted_and_clamped(self):
        self.assertEqual(validated_settings({"mode": "perforate", "perf_dash": "3", "perf_gap": "1.5"}),
                         {"mode": MODE_PERF, "perf_dash": 3.0, "perf_gap": 1.5})
        self.assertEqual(validated_settings({"perf_dash": 0})["perf_dash"], 0.1)
        self.assertEqual(validated_settings({"perf_gap": 500})["perf_gap"], 50.0)
        self.assertEqual(validated_settings({"perf_dash": "abc", "perf_gap": float("nan")}), {})

    def test_settings_survive_a_save_and_a_reload(self):
        model = LayersModel()
        model.update(model.layers[1].id, mode=MODE_PERF, perf_dash=4.0, perf_gap=2.0)
        reloaded = LayersModel()
        reloaded.load_list(model.to_list())
        layer = next(layer for layer in reloaded.layers if layer.mode == MODE_PERF)
        self.assertEqual((layer.perf_dash, layer.perf_gap), (4.0, 2.0))

    def test_project_saved_before_perforation_loads_with_defaults(self):
        saved = [{k: v for k, v in layer.items() if k not in ("perf_dash", "perf_gap")}
                 for layer in LayersModel().to_list()]
        model = LayersModel()
        model.load_list(saved)
        self.assertTrue(all(layer.perf_dash == 2.0 and layer.perf_gap == 1.0 for layer in model.layers))


@unittest.skipUnless(HAS_PREVIEW, "aperçu du G-Code non importable ici")
class PerforationPreviewTests(unittest.TestCase):
    def test_a_perforation_group_is_drawn_as_strokes_not_as_an_image(self):
        class Group:
            kind = KIND_LAYER
            mode = "perforate"
            strokes = []
        self.assertFalse(is_raster_group(Group(), False))


if __name__ == "__main__":
    unittest.main()
