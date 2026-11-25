"""Ponts de maintien (micro-joints) des calques de découpe : géométrie, G-Code et réglages du calque."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.vector.tabs import cut_runs, effective_count, is_closed, perimeter, tab_positions  # noqa: E402

try:
    from laser_studio.gcode.preview import cut_contours
    HAS_PREVIEW = True
except ImportError:
    HAS_PREVIEW = False

try:
    from laser_studio.gcode.vector import build_vector_layers_gcode
    from laser_studio.models.layer_modes import MODE_CUT, MODE_MARK
    from laser_studio.models.layers import LaserLayer, LayersModel, validated_settings
    HAS_MODEL = True
except ImportError:                       # PyQt6 non importable
    HAS_MODEL = False

SQUARE = [(0, 0), (40, 0), (40, 40), (0, 40), (0, 0)]
HOLE = [(10, 10), (30, 10), (30, 30), (10, 30), (10, 10)]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcode_reader import burn_paths  # noqa: E402


def length(run):
    return sum(math.hypot(run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]) for i in range(len(run) - 1))


class TabGeometryTests(unittest.TestCase):
    def test_square_gets_evenly_spaced_tabs(self):
        runs = cut_runs(SQUARE, 4, 1.0)
        self.assertEqual(len(runs), 4)
        self.assertAlmostEqual(sum(length(r) for r in runs), 160.0 - 4 * 1.0, places=6)
        # Un pont au milieu de chaque côté.
        centres = sorted(tab_positions(SQUARE, 4, 1.0))
        self.assertEqual([(round(x, 6), round(y, 6)) for x, y in centres],
                         [(0.0, 20.0), (20.0, 0.0), (20.0, 40.0), (40.0, 20.0)])

    def test_tab_gap_has_the_requested_width(self):
        runs = cut_runs(SQUARE, 1, 2.0)
        self.assertEqual(len(runs), 1)
        # Un seul pont : le tronçon coupé fait le contour moins la largeur du pont, et ses deux extrémités
        # sont à au plus 2 mm l'une de l'autre (à vol d'oiseau : le pont peut passer un angle).
        self.assertAlmostEqual(length(runs[0]), 158.0, places=6)
        start, end = runs[0][0], runs[0][-1]
        self.assertLessEqual(math.hypot(end[0] - start[0], end[1] - start[1]), 2.0 + 1e-9)

    def test_open_path_is_left_alone(self):
        path = [(0, 0), (10, 0), (10, 10)]
        self.assertEqual(cut_runs(path, 4, 1.0), [path])
        self.assertEqual(tab_positions(path, 4, 1.0), [])
        self.assertFalse(is_closed(path))

    def test_tiny_contour_gets_fewer_tabs_or_none(self):
        tiny = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]            # périmètre 4 mm
        self.assertEqual(effective_count(perimeter(tiny), 4, 0.5), 2)
        self.assertEqual(effective_count(perimeter(tiny), 4, 3.0), 0)
        self.assertEqual(cut_runs(tiny, 4, 3.0), [tiny])           # rien à poser : tracé d'origine

    def test_zero_settings_change_nothing(self):
        self.assertEqual(cut_runs(SQUARE, 0, 1.0), [SQUARE])
        self.assertEqual(cut_runs(SQUARE, 3, 0.0), [SQUARE])

    def test_curve_flattened_into_many_points(self):
        circle = [(10 * math.cos(2 * math.pi * i / 90), 10 * math.sin(2 * math.pi * i / 90)) for i in range(91)]
        runs = cut_runs(circle, 3, 0.5)
        self.assertEqual(len(runs), 3)
        self.assertAlmostEqual(sum(length(r) for r in runs), perimeter(circle) - 3 * 0.5, places=2)

    def test_run_crossing_the_start_point_is_not_split(self):
        # 3 ponts centrés à 1/6, 1/2 et 5/6 du périmètre : le tronçon qui contient le point de départ
        # (abscisse 0) reste d'un seul tenant.
        runs = cut_runs(SQUARE, 3, 1.0)
        self.assertEqual(len(runs), 3)
        spans_start = [r for r in runs if (0.0, 0.0) in [(round(x, 9), round(y, 9)) for x, y in r]]
        self.assertEqual(len(spans_start), 1)


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
class TabGcodeTests(unittest.TestCase):
    def test_without_tabs_the_contour_is_cut_in_one_run(self):
        runs = _cut_runs_of(_build(_data(MODE_CUT, [SQUARE])))
        self.assertEqual(len(runs), 1)
        self.assertAlmostEqual(length(runs[0]), 160.0)

    def test_tabs_leave_gaps_in_the_cut(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], tabs=True, tab_count=4, tab_width=1.0))
        runs = _cut_runs_of(gcode)
        self.assertEqual(len(runs), 4)
        self.assertAlmostEqual(sum(length(r) for r in runs), 156.0, places=2)
        self.assertTrue(any("Ponts de maintien : 4" in line for line in gcode))

    def test_holes_get_no_tabs_but_outer_contours_do(self):
        runs = _cut_runs_of(_build(_data(MODE_CUT, [SQUARE, HOLE], tabs=True, tab_count=2, tab_width=1.0)))
        self.assertEqual(len(runs), 3)                                     # trou entier + 2 tronçons
        whole = [r for r in runs if abs(length(r) - 80.0) < 1e-6]
        self.assertEqual(len(whole), 1)

    def test_tabs_are_repeated_on_every_pass(self):
        runs = _cut_runs_of(_build(_data(MODE_CUT, [SQUARE], tabs=True, tab_count=2, tab_width=1.0, passes=3)))
        self.assertEqual(len(runs), 6)

    def test_open_paths_keep_a_single_run(self):
        line = [(0, 0), (30, 0)]
        runs = _cut_runs_of(_build(_data(MODE_CUT, [line], tabs=True, tab_count=4, tab_width=1.0)))
        self.assertEqual(len(runs), 1)

    def test_marking_layer_ignores_tabs(self):
        runs = _cut_runs_of(_build(_data(MODE_MARK, [SQUARE], tabs=True, tab_count=4, tab_width=1.0)))
        self.assertEqual(len(runs), 1)

    def test_unchecked_tabs_keep_their_settings_but_cut_everything(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], tabs=False, tab_count=4, tab_width=1.0))
        self.assertEqual(len(_cut_runs_of(gcode)), 1)
        self.assertFalse(any("Ponts de maintien" in line for line in gcode))

    def test_old_layer_without_tab_settings_is_unchanged(self):
        data = _data(MODE_CUT, [SQUARE])
        self.assertNotIn("tab_count", data["layer"])
        self.assertEqual(len(_cut_runs_of(_build(data))), 1)

    def test_safe_cut_order_keeps_inner_contours_first(self):
        gcode = _build(_data(MODE_CUT, [SQUARE, HOLE], tabs=True, tab_count=2, tab_width=1.0), safe_cut_order=True)
        runs = _cut_runs_of(gcode)
        self.assertAlmostEqual(length(runs[0]), 80.0)                      # le trou d'abord, en entier


@unittest.skipUnless(HAS_MODEL, "modèle des calques non importable ici")
class TabLayerSettingsTests(unittest.TestCase):
    def test_new_layer_has_tabs_off_with_default_settings(self):
        layer = LaserLayer()
        self.assertFalse(layer.tabs)
        self.assertEqual(layer.tab_count, 4)
        self.assertGreater(layer.tab_width, 0)

    def test_settings_are_converted_and_clamped(self):
        self.assertEqual(validated_settings({"tabs": 1, "tab_count": "3", "tab_width": "0.8"}),
                         {"tabs": True, "tab_count": 3, "tab_width": 0.8})
        self.assertEqual(validated_settings({"tab_count": -2})["tab_count"], 0)
        self.assertEqual(validated_settings({"tab_count": 500})["tab_count"], 20)
        self.assertEqual(validated_settings({"tab_width": 0})["tab_width"], 0.1)
        self.assertEqual(validated_settings({"tab_width": 99})["tab_width"], 10.0)
        self.assertEqual(validated_settings({"tab_count": "abc", "tab_width": float("nan")}), {})

    def test_settings_survive_a_save_and_a_reload(self):
        model = LayersModel()
        model.update(model.layers[1].id, tabs=True, tab_count=6, tab_width=1.5)
        reloaded = LayersModel()
        reloaded.load_list(model.to_list())
        cut = next(layer for layer in reloaded.layers if layer.role == "cut")
        self.assertEqual((cut.tabs, cut.tab_count, cut.tab_width), (True, 6, 1.5))

    def test_project_saved_before_tabs_loads_with_no_tabs(self):
        saved = [{k: v for k, v in layer.items() if k not in ("tabs", "tab_count", "tab_width")}
                 for layer in LayersModel().to_list()]
        model = LayersModel()
        model.load_list(saved)
        self.assertTrue(all(not layer.tabs for layer in model.layers))


def _segments(runs):
    """Segments (départ, arrivée, NaN) des tracés `runs`, comme les liste l'aperçu pour un groupe."""
    xs, ys = [], []
    for run in runs:
        for a, b in zip(run, run[1:]):
            xs += [a[0], b[0], float("nan")]
            ys += [a[1], b[1], float("nan")]
    return xs, ys


@unittest.skipUnless(HAS_PREVIEW, "aperçu du G-Code non importable ici")
class TabPreviewTests(unittest.TestCase):
    """L'aperçu 2D dessine la matière à l'intérieur des contours fermés : un contour à ponts, coupé en
    plusieurs tronçons, doit rester UN contour."""

    def test_tabbed_contour_is_still_one_closed_contour(self):
        contours = cut_contours([_segments(cut_runs(SQUARE, 4, 1.0))])
        self.assertEqual(len(contours), 1)

    def test_several_passes_and_pieces_stay_separate(self):
        other = [(60, 0), (100, 0), (100, 40), (60, 40), (60, 0)]
        runs = cut_runs(SQUARE, 3, 1.0) + cut_runs(other, 3, 1.0)
        contours = cut_contours([_segments(runs + runs)])                 # deux passes
        self.assertEqual(len(contours), 2)

    def test_contour_without_tabs_is_unchanged(self):
        self.assertEqual(len(cut_contours([_segments([SQUARE])])), 1)

    def test_open_path_is_still_not_a_contour(self):
        self.assertEqual(cut_contours([_segments([[(0, 0), (30, 0), (30, 20)]])]), [])


if __name__ == "__main__":
    unittest.main()
