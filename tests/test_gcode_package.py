"""Paquet gcode/ : génération du G-Code sans Qt.

Vérifie que le paquet n'importe pas PyQt6, que les threads de controllers/workers.py
produisent exactement le G-Code des fonctions pures, et le contenu du G-Code
(puissance S, commande laser, surbalayage, décalage retour, en-tête et fin).
"""
import dataclasses
import os
import re
import subprocess
import sys
import unittest

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src")
sys.path.insert(0, SRC)

from laser_studio.core.constants import ORIGIN_CENTER  # noqa: E402
from laser_studio.gcode import (  # noqa: E402
    GcodeResult, JobParams, MATRIX_CUT, MATRIX_ENGRAVE, bidir_test_gcode, build_job_gcode, build_test_matrix_gcode,
    image_origin,
)
from laser_studio.gcode.common import (  # noqa: E402
    OVERSCAN_PERCENT, TIME_MARGIN, duration_parts, overscan_distance, power_value, scan_offset_mm,
    with_time_margin,
)

MODULES = ("laser_studio.gcode", "laser_studio.gcode.common", "laser_studio.gcode.raster",
           "laser_studio.gcode.vector", "laser_studio.gcode.job", "laser_studio.gcode.params",
           "laser_studio.gcode.test_matrix", "laser_studio.gcode.calibration", "laser_studio.gcode.preview",
           "laser_studio.models.layer_modes")


def job_params(**kw):
    p = {
        'width_mm': 4.0, 'height_mm': 2.0, 'origin_pos': "bottom_left", 'offset_x': 0.0, 'offset_y': 0.0,
        'speed_engrave': 1000, 'power_engrave': 35.0, 'laser_cmd': "M4", 'image_laser_cmd': "M4",
        # Dans l'application : surbalayage global ET calque de gravure (layer_overscan_enabled).
        'image_overscan': False, 'algo': "Floyd-Steinberg", 's_max': 1000, 'homing': False,
        'enable_overscan': False, 'overscan_mode': "Distance Fixe (mm)", 'overscan_dist': 2.5,
        'overscan_pct': 5.0, 'start_gcode': "", 'end_gcode': "", 'scan_offset_mm': 0.0,
        'safe_cut_order': True,
    }
    p.update(kw)
    return JobParams(**p)


def lines(result):
    return result.gcode.split("\n")


class NoQtTests(unittest.TestCase):
    def test_the_package_does_not_import_pyqt(self):
        code = ("import sys\n" + "".join(f"import {m}\n" for m in MODULES)
                + "print(sorted(m for m in sys.modules if m.startswith('PyQt')))")
        env = dict(os.environ, PYTHONPATH=SRC)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True)
        self.assertEqual(out.stdout.strip(), "[]")


class CommonTests(unittest.TestCase):
    def test_overscan_distance(self):
        self.assertEqual(overscan_distance("Distance Fixe (mm)", 5.0, 3.0, 40.0), 3.0)
        self.assertEqual(overscan_distance(OVERSCAN_PERCENT, 10.0, 3.0, 40.0), 4.0)

    def test_scan_offset_reads_unusable_values_as_zero(self):
        self.assertEqual(scan_offset_mm(0.15), 0.15)
        for value in (None, "", "abc"):
            self.assertEqual(scan_offset_mm(value), 0.0)

    def test_durations(self):
        self.assertEqual(TIME_MARGIN, 1.15)
        self.assertAlmostEqual(with_time_margin(600), 690.0)         # 15 % de marge des accélérations
        self.assertEqual(with_time_margin(-5), 0.0)
        self.assertEqual(duration_parts(46), (0, 0, 46))
        self.assertEqual(duration_parts(192.4), (0, 3, 12))
        self.assertEqual(duration_parts(7503), (2, 5, 3))           # plus d'une heure : des heures, pas « 125 min »

    def test_power_is_rounded_to_the_nearest_everywhere(self):
        # Issue #118 : avec S-Max 255, 10 % donne S26 (25,5 arrondi), plus S25 (arrondi vers le bas).
        self.assertEqual(power_value(10, 255), 26)
        self.assertEqual(power_value(47.5, 1000), 475)
        self.assertEqual(power_value(-3, 1000), 0)

    def test_test_matrix_and_layers_give_the_same_s(self):
        import re as _re
        matrix = build_test_matrix_gcode(MatrixTests.params(None, s_max=255, min_power=10, max_power=10,
                                                                 steps_power=1))
        values = {int(v) for v in _re.findall(r"\bS(\d+)", matrix.gcode)} - {0}
        self.assertIn(26, values)
        self.assertNotIn(25, values)


class JobParamsTests(unittest.TestCase):
    def test_an_unknown_or_removed_setting_is_refused(self):
        """Un réglage mal écrit ou disparu (l'ancienne « découpe SVG ») était ignoré en silence dans un
        dictionnaire ; JobParams le refuse, et ses champs ne se modifient pas par mégarde."""
        with self.assertRaises(TypeError):
            job_params(enable_cut=True)
        with self.assertRaises(TypeError):
            job_params(widht_mm=10.0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            job_params().width_mm = 10.0

    def test_defaults_follow_the_global_settings(self):
        p = job_params(image_laser_cmd=None, image_overscan=None, enable_overscan=True,
                       overscan_mode=OVERSCAN_PERCENT, overscan_pct=10.0, laser_cmd="M3")
        self.assertEqual((p.image_cmd, p.image_overscan_enabled, p.overscan_for(40.0)), ("M3", True, 4.0))
        self.assertEqual(job_params(origin_pos=ORIGIN_CENTER, offset_x=50.0, offset_y=40.0).vector_origin(),
                         (48.0, 39.0))


class RasterTests(unittest.TestCase):
    def test_binary_pixels_get_the_layer_power(self):
        arr = np.array([[0, 0, 255, 255]], dtype=np.uint8)            # 2 pixels brûlés sur 4
        result = build_job_gcode(arr, job_params(height_mm=1.0))
        self.assertIsInstance(result, GcodeResult)
        self.assertIn("G1 X2 F1000 S350", lines(result))              # 35 % de S1000, jusqu'au bord du 2e pixel
        self.assertNotIn("OVERSCAN", result.gcode)
        self.assertEqual(result.avg_power, 35.0)

    def test_grayscale_power_follows_the_gray(self):
        arr = np.array([[0, 128, 255]], dtype=np.uint8)
        g = lines(build_job_gcode(arr, job_params(width_mm=3.0, height_mm=1.0, algo="Niveaux de Gris")))
        powers = [int(m) for line in g for m in re.findall(r"S(\d+)", line) if line.startswith(("G1", "X"))]
        self.assertEqual(powers, [350, round(350 * 127 / 255)])       # le blanc (255) n'est pas parcouru

    def test_the_laser_command_is_sent_once_and_power_rides_on_the_moves(self):
        """GRBL vide son tampon (la tête s'arrête) à chaque M3 / M4 / M5, et à chaque S changé sans
        mouvement : M3 ou M4 une fois, M5 une fois, et aucune ligne « S » seule."""
        arr = np.zeros((3, 4), dtype=np.uint8)
        for cmd in ("M4", "M3"):
            g = lines(build_job_gcode(arr, job_params(laser_cmd=cmd, image_laser_cmd=cmd)))
            self.assertEqual(sum(line.startswith(cmd) for line in g), 1, cmd)
            self.assertEqual(g.count("M5"), 1, cmd)
            self.assertFalse([line for line in g if re.fullmatch(r"S\d+", line.split(";")[0].strip())])

    def test_overscan_and_return_offset(self):
        arr = np.zeros((2, 4), dtype=np.uint8)
        params = job_params(enable_overscan=True, image_overscan=True, scan_offset_mm=0.2)
        g = lines(build_job_gcode(arr, params))
        starts = [line for line in g if line.endswith("OVERSCAN_START")]
        x0, _ = image_origin(params)
        self.assertEqual(x0, 2.5)                                     # marge = surbalayage : départ à X0
        self.assertEqual(starts[0], "G0 X0 Y1 ; OVERSCAN_START")                     # aller
        self.assertEqual(starts[1], f"G0 X{x0 + 0.2 + 4.0 + 2.5:g} Y0 ; OVERSCAN_START")   # retour décalé

    def test_overscan_off_for_the_engrave_layer(self):
        arr = np.zeros((1, 4), dtype=np.uint8)
        g = build_job_gcode(arr, job_params(enable_overscan=True, image_overscan=False)).gcode
        self.assertNotIn("OVERSCAN", g)

    def test_image_origin(self):
        self.assertEqual(image_origin(job_params(offset_x=5.0, offset_y=-3.0)), (5.0, -3.0))   # sans surbalayage
        self.assertEqual(image_origin(job_params(offset_x=5.0, offset_y=-3.0, enable_overscan=True,
                                                 image_overscan=True)), (7.5, -3.0))
        self.assertEqual(image_origin(job_params(origin_pos=ORIGIN_CENTER, offset_x=50.0, offset_y=40.0)),
                         (48.0, 39.0))


class JobTests(unittest.TestCase):
    def test_empty_job(self):
        result = build_job_gcode(None, job_params())
        self.assertEqual(lines(result), ["; --- G-CODE HYBRIDE GRBL PRO ---", "M5", "G0 X0 Y0", "; FIN DU TRAVAIL"])
        self.assertEqual((result.line_count, result.avg_power, result.duration), (3, 0.0, 0.0))

    def test_homing_start_and_end_gcode(self):
        g = lines(build_job_gcode(None, job_params(homing=True, start_gcode=" G21 ", end_gcode=" M5 ")))
        self.assertEqual(g[1:4], ["$H ; Homing initial", "; --- G-Code de Début ---", "G21"])
        self.assertEqual(g[-2:], ["; --- G-Code de Fin ---", "M5"])

    def test_progress_ends_at_100(self):
        seen = []
        build_job_gcode(np.zeros((60, 4), dtype=np.uint8), job_params(), progress=seen.append)
        self.assertEqual(seen[-3:], [70, 85, 100])
        self.assertEqual(seen, sorted(seen))

    def test_vector_layers_use_the_job_offset(self):
        layer = {"name": "Découpe", "mode": "cut", "speed": 250, "power": 90.0, "passes": 1}
        square = [(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)]
        data = {"c": {"layer": layer, "polygons": [square], "polygon_groups": [[square]]}}
        g = lines(build_job_gcode(None, job_params(offset_x=3.0, offset_y=4.0), data))
        self.assertIn("G0 X3 Y4", g)
        self.assertIn("G1 X8 F250 S900", g)


class NoBufferStopTests(unittest.TestCase):
    """GRBL vide son tampon de mouvements (la tête s'arrête net) à chaque M3 / M4 / M5 et à chaque puissance S
    changée sans mouvement. Avant, les calques vectoriels en faisaient deux par segment gravé : gravure
    saccadée, et plus longue que la durée estimée."""

    def assert_continuous(self, gcode, name):
        code = [line.split(";")[0].strip() for line in gcode.split("\n")]
        self.assertFalse([line for line in code if re.fullmatch(r"S\d+", line)], name)
        self.assertLessEqual(sum(bool(re.match(r"M[345]\b", line)) for line in code), 3, name)

    def test_every_generator_keeps_the_head_moving(self):
        from laser_studio.gcode.vector import build_vector_layers_gcode
        square = [(0, 0), (20, 0), (20, 10), (0, 10), (0, 0)]
        letters = [[[(x, 0), (x + 4, 0), (x + 4, 8), (x, 8), (x, 0)]] for x in (0, 6, 12)]
        layers = {
            "f": {"layer": {"name": "R", "mode": "engrave_fill", "power": 60.0, "speed": 2000, "passes": 1,
                            "line_interval": 0.5}, "polygons": [p for g in letters for p in g],
                  "polygon_groups": letters},
            "c": {"layer": {"name": "D", "mode": "cut", "power": 90.0, "speed": 400, "passes": 2,
                            "line_interval": 0.1}, "polygons": [square, [(5, 5), (6, 5), (6, 6), (5, 5)]]},
        }
        arr = np.where(np.random.default_rng(0).random((20, 40)) < 0.5, 0, 255).astype(np.uint8)
        for cmd in ("M4", "M3"):
            self.assert_continuous(build_job_gcode(arr, job_params(
                laser_cmd=cmd, image_laser_cmd=cmd, enable_overscan=True, image_overscan=True)).gcode, f"image {cmd}")
            for overscan in (0.0, 2.0):
                self.assert_continuous("\n".join(build_vector_layers_gcode(
                    layers, 0.0, 0.0, 50.0, cmd, 1000, overscan_dist=overscan)[0]), f"calques {cmd} {overscan}")
        bidir = {"origin_pos": "bottom_left", "offset_x": 0.0, "offset_y": 0.0, "speed_engrave": 1000,
                 "power_engrave": 30.0, "s_max": 1000, "laser_cmd": "M4"}
        self.assert_continuous(bidir_test_gcode(bidir)[0], "aller-retour")


class MatrixTests(unittest.TestCase):
    def params(self, **kw):
        p = {"min_power": 20.0, "max_power": 80.0, "steps_power": 3, "single_power": 85.0,
             "min_passes": 1, "max_passes": 3, "steps_passes": 3, "min_speed": 500.0, "max_speed": 1500.0,
             "steps_speed": 2, "size_square": 5.0, "gap": 2.0, "lines_mm": 2.0, "matrix_offset_x": 0.0,
             "matrix_offset_y": 0.0, "laser_cmd": "M4", "homing": False, "mode": MATRIX_ENGRAVE, "s_max": 1000}
        p.update(kw)
        return p

    def test_engrave_matrix_has_one_square_per_speed_and_power(self):
        g = build_test_matrix_gcode(self.params()).gcode
        self.assertEqual(g.count("; --- Carré Speed="), 2 * 3)
        self.assertIn("Power=50.0% (Gravure)", g)
        self.assertIn("S500", g)                                      # 50 % de S1000

    def test_cut_matrix_repeats_the_passes(self):
        result = build_test_matrix_gcode(self.params(mode=MATRIX_CUT))
        self.assertEqual(result.gcode.count("; Passe 3/3"), 2)
        self.assertEqual(result.avg_power, 85.0)
        self.assertGreater(result.duration, 0.0)                      # secondes, marge comprise


class CalibrationTests(unittest.TestCase):
    def test_bidir_pattern(self):
        p = {"origin_pos": "bottom_left", "offset_x": 0.0, "offset_y": 0.0, "speed_engrave": 1000,
             "power_engrave": 30.0, "s_max": 1000, "laser_cmd": "M4", "offsets": [-0.1, 0.0, 0.1], "rows": 3}
        gcode, count, avg, _duration = bidir_test_gcode(p)
        self.assertIn("; 3 colonnes", gcode)
        # 3 barres de 4 mm espacées de 2 mm (16 mm), surbalayage de 2,5 mm de chaque côté
        # Départ de chaque ligne de barres (G0 ; X inchangé n'est pas répété) : X et Y comme les suit GRBL.
        starts, x = [], 0.0
        for line in gcode.split("\n"):
            m = re.search(r"X(-?[\d.]+)", line)
            x = float(m.group(1)) if m else x
            if line.startswith("G0") and x in (-2.5, 18.5) and "X0 Y0" not in line:
                starts.append(x)
        self.assertEqual(len(starts), 4)                              # 3 lignes demandées -> 4 (paire)
        self.assertEqual(starts.count(-2.5), 2)                       # 2 aller, 2 retour
        self.assertEqual(avg, 30.0)
        self.assertEqual(count, len(gcode.split("\n")))


try:
    from PyQt6.QtWidgets import QApplication as QCoreApplication  # QApplication : la fenêtre est créée dans le même processus
    from laser_studio.controllers import workers
except ImportError:  # PyQt6 absent
    workers = None


@unittest.skipIf(workers is None, "PyQt6 non disponible ici")
class WorkerWrapperTests(unittest.TestCase):
    """Les threads ne font qu'appeler les fonctions pures : même résultat."""

    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def run_worker(self, worker):
        out = []
        worker.finished.connect(lambda *a: out.append(a))
        worker.run()
        return out[0]

    def test_job_worker(self):
        arr = np.where(np.random.default_rng(1).random((8, 10)) > 0.5, 255, 0).astype(np.uint8)
        params = job_params(enable_overscan=True, scan_offset_mm=0.1)
        expected = tuple(build_job_gcode(arr, params))
        self.assertEqual(self.run_worker(workers.AdvancedGCodeWorker(arr, params)), expected)

    def test_matrix_worker(self):
        params = MatrixTests().params()
        self.assertEqual(self.run_worker(workers.TestMatrixWorker(params)), tuple(build_test_matrix_gcode(params)))


if __name__ == "__main__":
    unittest.main()
