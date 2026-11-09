"""Gravure d'image : lignes vides sautées, chaque ligne balayée (avec son surbalayage) seulement de son
premier à son dernier pixel gravé — sans changer les pixels gravés (rejeu de test_gcode_burn_map)."""
import os
import re
import sys
import types
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # test_gcode_burn_map

from test_gcode_burn_map import generate_gcode, power_map, workers  # noqa: E402

try:
    import gcode_generation_mixin as ggm
except ImportError:  # PyQt6 manquant
    ggm = None


def disc(size=60, ring=4):
    """Anneau noir (à graver) sur fond blanc, comme une médaille : coins et bords vides."""
    yy, xx = np.mgrid[:size, :size]
    r = np.hypot(xx - (size - 1) / 2.0, yy - (size - 1) / 2.0)
    arr = np.full((size, size), 255, np.uint8)
    arr[(r <= size / 2.0 - 2) & (r >= size / 2.0 - 2 - ring)] = 0
    return arr


def moves(gcode):
    """[(G, x0, y0, x1, y1)] de chaque déplacement G0/G1, avant le M5 final."""
    out, x, y = [], 0.0, 0.0
    for raw in gcode[:gcode.rindex("M5")].splitlines():
        line = raw.split(";")[0].strip()
        m = re.match(r"(G0|G1)\b(.*)", line)
        if not m:
            continue
        mx, my = re.search(r"X(-?[\d.]+)", m.group(2)), re.search(r"Y(-?[\d.]+)", m.group(2))
        nx = float(mx.group(1)) if mx else x
        ny = float(my.group(1)) if my else y
        out.append((m.group(1), x, y, nx, ny))
        x, y = nx, ny
    return out


@unittest.skipIf(workers is None, "workers.py non importable ici (PyQt6/svg.path manquants ?)")
class RasterTrimTests(unittest.TestCase):
    def assert_same_burn(self, arr, overscan, algo="Seuil Simple (Binaire)"):
        h, w = arr.shape
        got = power_map(generate_gcode(arr, overscan, algo), w, h)
        want = (255.0 - arr) / 255.0 if algo == "Niveaux de Gris" else (arr == 0).astype(float)
        self.assertLess(np.abs(got - want).max(), 0.01)

    def test_disc_burns_the_same_pixels(self):
        for overscan in (0.0, 3.0):
            self.assert_same_burn(disc(), overscan)
        gray = disc().astype(np.float64)
        gray[gray == 0] = 90
        self.assert_same_burn(gray.astype(np.uint8), 3.0, "Niveaux de Gris")

    def test_empty_rows_are_not_visited(self):
        arr = np.full((5, 20), 255, np.uint8)
        arr[[0, 4], 5:15] = 0                       # y = 0 et 4 ; lignes 1 à 3 vides
        ys = {round(m[4], 3) for m in moves(generate_gcode(arr, 2.0))}
        self.assertEqual(ys, {4.0, 0.0})            # Y d'une ligne = h - 1 - y
        blank = generate_gcode(np.full((5, 20), 255, np.uint8), 2.0)
        self.assertEqual(moves(blank), [])          # rien à graver : la tête ne bouge pas

    def test_row_is_swept_only_around_its_burned_pixels(self):
        arr = np.full((1, 40), 255, np.uint8)
        arr[0, 10:20] = 0
        xs = [x for m in moves(generate_gcode(arr, 2.0)) for x in (m[3],)]
        self.assertAlmostEqual(min(xs), 10.0 - 2.0)  # surbalayage avant le 1er pixel gravé
        self.assertAlmostEqual(max(xs), 20.0 + 2.0)  # … et après le dernier

    def test_direction_alternates_over_swept_rows(self):
        arr = np.full((4, 20), 255, np.uint8)
        arr[[0, 3], 5:15] = 0                       # deux lignes gravées séparées par deux vides
        starts = [m for m in moves(generate_gcode(arr, 2.0)) if m[0] == "G0"]
        self.assertEqual([round(m[3], 3) for m in starts], [3.0, 17.0])   # aller puis retour

    def test_disc_travel_is_much_shorter(self):
        arr = disc()
        h, w = arr.shape
        swept = sum(abs(m[3] - m[1]) for m in moves(generate_gcode(arr, 2.5)) if m[0] == "G1")
        full = h * (w + 2 * 2.5)                    # ancien balayage : toute la largeur, chaque ligne
        self.assertLess(swept, 0.8 * full)


class _Spin:
    def __init__(self, v):
        self.v = v

    def value(self):
        return self.v


@unittest.skipIf(ggm is None, "gcode_generation_mixin non importable ici")
class QuickEstimateTests(unittest.TestCase):
    def test_estimate_follows_the_trimmed_rows(self):
        class App(ggm.GcodeGenerationMixin):
            pass
        app = App()
        arr = np.full((10, 60), 255, np.uint8)
        arr[[2, 7], 10:40] = 0                      # 2 lignes de 30 px (30 mm), 8 lignes vides
        app.processed_array = arr
        app.spin_w, app.engrave_speed = _Spin(60.0), 600
        app.chk_overscan = types.SimpleNamespace(isChecked=lambda: False)
        app.loaded_svg_path = None
        with mock.patch.object(ggm.QMessageBox, "information") as box:
            app.estimate_job_time()
        # 2 x 30 mm à 600 mm/min = 6 s (avant : 10 lignes x 60 mm = 60 s)
        self.assertIn(app._format_duration(6.0), box.call_args[0][2])


if __name__ == "__main__":
    unittest.main()
