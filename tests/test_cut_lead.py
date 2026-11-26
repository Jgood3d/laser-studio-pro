"""Arcs d'entrée et de sortie des calques de découpe : géométrie, G-Code, aperçu et réglages du calque."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcode_reader import burn_paths  # noqa: E402
from laser_studio.vector.lead import add_leads, lead_path, _edges  # noqa: E402
from laser_studio.vector.tabs import closed_points  # noqa: E402

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


def length(run):
    return sum(math.hypot(run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]) for i in range(len(run) - 1))


def inside(point, poly):
    """Point dans un contour (lancer de rayon)."""
    x, y = point
    pts = closed_points(poly)
    hit = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


class LeadGeometryTests(unittest.TestCase):
    def test_outer_contour_gets_arcs_on_the_outside(self):
        led = lead_path(SQUARE, 0, 1.0, _edges([SQUARE]))
        self.assertIsNotNone(led)
        arc_in, arc_out = led[:6], led[-6:]
        self.assertTrue(all(not inside(p, SQUARE) for p in arc_in + arc_out))
        self.assertEqual(led[6], (0, 0))                          # le contour garde son départ
        self.assertEqual(led[-7], (0, 0))

    def test_arc_is_tangent_to_the_contour(self):
        led = lead_path(SQUARE, 0, 1.0, _edges([SQUARE]))
        (x0, y0), (x1, y1) = led[5], led[6]                      # dernier pas de l'arc d'entrée
        angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
        self.assertLess(abs(angle), 20.0)                         # arrive presque dans le sens du côté
        (x0, y0), (x1, y1) = led[-7], led[-6]                    # premier pas de l'arc de sortie
        self.assertLess(abs(math.degrees(math.atan2(y1 - y0, x1 - x0))), 20.0)

    def test_arc_has_the_requested_radius(self):
        led = lead_path(SQUARE, 0, 2.0, _edges([SQUARE]))
        self.assertAlmostEqual(led[0][0], -2.0)                  # début de l'arc d'entrée, R derrière le départ
        self.assertAlmostEqual(led[0][1], -2.0)
        self.assertAlmostEqual(length(led[:7]), math.pi * 2.0 / 2, delta=0.05)     # quart de cercle

    def test_direction_of_travel_does_not_change_the_side(self):
        clockwise = list(reversed(SQUARE))
        led = lead_path(clockwise, 0, 1.0, _edges([clockwise]))
        self.assertTrue(all(not inside(p, SQUARE) for p in led[:6] + led[-6:]))

    def test_hole_gets_arcs_on_the_inside_and_starts_mid_edge(self):
        edges = _edges([SQUARE, HOLE])
        led = lead_path(HOLE, 1, 1.0, edges)
        self.assertIsNotNone(led)
        self.assertTrue(all(inside(p, HOLE) for p in led[:6] + led[-6:]))
        # Au coin d'un trou l'arc sortirait du trou : le contour est repris du milieu de son plus long côté.
        self.assertEqual(led[6], (20.0, 10.0))

    def test_radius_is_reduced_when_a_neighbour_is_close(self):
        # À 0,6 mm de la pièce de gauche, un arc de 2 mm ne passe pas, un de 0,5 mm passe.
        left = [(-10.6, 0), (-0.6, 0), (-0.6, 10), (-10.6, 10), (-10.6, 0)]
        piece = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        mid_start = [(0, 5), (0, 10), (10, 10), (10, 0), (0, 0), (0, 5)]      # départ sur le côté gauche
        led = lead_path(mid_start, 0, 2.0, _edges([left, piece]))
        self.assertIsNotNone(led)
        self.assertAlmostEqual(led[0][0], -0.5)                  # rayon ramené de 2 à 0,5 mm
        self.assertAlmostEqual(led[0][1], 4.5)
        self.assertTrue(all(not inside(p, left) for p in led))

    def test_no_room_means_no_arc(self):
        tiny_hole = [(5, 5), (5.3, 5), (5.3, 5.3), (5, 5.3), (5, 5)]
        result, done, skipped = add_leads([tiny_hole, SQUARE], [tiny_hole, SQUARE], 1.0)
        self.assertEqual((done, skipped), (1, 1))
        self.assertEqual(result[0], tiny_hole)

    def test_open_paths_are_left_alone(self):
        line = [(0, 0), (10, 0), (10, 10)]
        result, done, skipped = add_leads([line], [line], 1.0)
        self.assertEqual((result[0], done, skipped), (line, 0, 0))

    def test_zero_radius_changes_nothing(self):
        self.assertEqual(add_leads([SQUARE], [SQUARE], 0.0), ([SQUARE], 0, 0))

    def test_skipped_paths_are_not_touched(self):
        result, done, _ = add_leads([SQUARE], [SQUARE], 1.0, skip=[True])
        self.assertEqual((result[0], done), (SQUARE, 0))

    def test_circle_keeps_its_smooth_start(self):
        circle = [(10 * math.cos(2 * math.pi * i / 72), 10 * math.sin(2 * math.pi * i / 72)) for i in range(73)]
        result, done, skipped = add_leads([circle], [circle], 1.5)
        self.assertEqual((done, skipped), (1, 0))
        self.assertTrue(all(math.hypot(*p) >= 10.0 - 1e-6 for p in result[0][:6] + result[0][-6:]))


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
class LeadGcodeTests(unittest.TestCase):
    def test_without_lead_the_contour_starts_on_itself(self):
        runs = _cut_runs_of(_build(_data(MODE_CUT, [SQUARE])))
        self.assertEqual(runs[0][0], (0.0, 0.0))

    def test_lead_starts_beside_the_contour_and_adds_the_arcs(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], lead=True, lead_radius=1.0))
        run = _cut_runs_of(gcode)[0]
        self.assertEqual(run[0], (-1.0, -1.0))
        self.assertGreater(length(run), 160.0 + 2.5)               # contour + deux quarts de cercle de ~1,57 mm
        self.assertTrue(any("Arcs d'entrée/sortie : rayon 1 mm (1 contours)" in line for line in gcode))

    def test_unchecked_lead_keeps_its_radius_but_changes_nothing(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], lead=False, lead_radius=1.0))
        self.assertEqual(_cut_runs_of(gcode)[0][0], (0.0, 0.0))
        self.assertFalse(any("Arcs d'entrée" in line for line in gcode))

    def test_marking_layer_ignores_lead(self):
        runs = _cut_runs_of(_build(_data(MODE_MARK, [SQUARE], lead=True, lead_radius=1.0)))
        self.assertEqual(runs[0][0], (0.0, 0.0))

    def test_contours_with_tabs_get_no_arcs(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], lead=True, lead_radius=1.0, tabs=True, tab_count=4, tab_width=1.0))
        runs = _cut_runs_of(gcode)
        self.assertEqual(len(runs), 4)
        self.assertAlmostEqual(sum(length(r) for r in runs), 156.0, places=2)

    def test_lead_follows_the_kerf_shifted_contour(self):
        gcode = _build(_data(MODE_CUT, [SQUARE], lead=True, lead_radius=1.0, kerf=True, kerf_width=0.2))
        run = _cut_runs_of(gcode)[0]
        self.assertEqual(run[0], (-1.1, -1.1))                     # contour décalé de 0,1 : départ à (−0,1 ; −0,1)

    def test_every_pass_has_its_arcs(self):
        runs = _cut_runs_of(_build(_data(MODE_CUT, [SQUARE], lead=True, lead_radius=1.0, passes=2)))
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0][0], runs[1][0])

    def test_contour_without_room_is_reported(self):
        tiny_hole = [(5, 5), (5.3, 5), (5.3, 5.3), (5, 5.3), (5, 5)]
        gcode = _build(_data(MODE_CUT, [SQUARE, tiny_hole], lead=True, lead_radius=1.0))
        self.assertTrue(any("ATTENTION : 1 contour(s) sans arc" in line for line in gcode))

    def test_old_layer_without_lead_settings_is_unchanged(self):
        data = _data(MODE_CUT, [SQUARE])
        self.assertNotIn("lead", data["layer"])
        self.assertEqual(_cut_runs_of(_build(data))[0][0], (0.0, 0.0))

    def test_inner_contours_are_still_cut_first(self):
        gcode = _build(_data(MODE_CUT, [SQUARE, HOLE], lead=True, lead_radius=1.0), safe_cut_order=True)
        first = _cut_runs_of(gcode)[0]
        self.assertTrue(inside(first[0], HOLE))                    # le trou d'abord : l'arc d'entrée est dans le trou


def _segments(runs):
    xs, ys = [], []
    for run in runs:
        for a, b in zip(run, run[1:]):
            xs += [a[0], b[0], float("nan")]
            ys += [a[1], b[1], float("nan")]
    return xs, ys


@unittest.skipUnless(HAS_PREVIEW, "aperçu du G-Code non importable ici")
class LeadPreviewTests(unittest.TestCase):
    def test_arcs_are_not_part_of_the_drawn_contour(self):
        led, _, _ = add_leads([HOLE, SQUARE], [HOLE, SQUARE], 1.0)
        contours = cut_contours([_segments(led)])
        self.assertEqual(len(contours), 2)
        xs = sorted((min(p[0] for p in c), max(p[0] for p in c)) for c in contours)
        self.assertEqual([(round(a, 2), round(b, 2)) for a, b in xs], [(0.0, 40.0), (10.0, 30.0)])


@unittest.skipUnless(HAS_MODEL, "modèle des calques non importable ici")
class LeadLayerSettingsTests(unittest.TestCase):
    def test_new_layer_has_lead_off_with_a_default_radius(self):
        layer = LaserLayer()
        self.assertFalse(layer.lead)
        self.assertAlmostEqual(layer.lead_radius, 1.0)

    def test_settings_are_converted_and_clamped(self):
        self.assertEqual(validated_settings({"lead": 1, "lead_radius": "1.5"}), {"lead": True, "lead_radius": 1.5})
        self.assertEqual(validated_settings({"lead_radius": 0})["lead_radius"], 0.2)
        self.assertEqual(validated_settings({"lead_radius": 99})["lead_radius"], 10.0)
        self.assertEqual(validated_settings({"lead_radius": "abc"}), {})
        self.assertEqual(validated_settings({"lead_radius": float("nan")}), {})

    def test_settings_survive_a_save_and_a_reload(self):
        model = LayersModel()
        model.update(model.layers[1].id, lead=True, lead_radius=2.5)
        reloaded = LayersModel()
        reloaded.load_list(model.to_list())
        cut = next(layer for layer in reloaded.layers if layer.role == "cut")
        self.assertEqual((cut.lead, cut.lead_radius), (True, 2.5))

    def test_project_saved_before_lead_loads_with_lead_off(self):
        saved = [{k: v for k, v in layer.items() if k not in ("lead", "lead_radius")}
                 for layer in LayersModel().to_list()]
        model = LayersModel()
        model.load_list(saved)
        self.assertTrue(all(not layer.lead for layer in model.layers))


if __name__ == "__main__":
    unittest.main()
