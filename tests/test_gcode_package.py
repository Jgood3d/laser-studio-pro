"""Paquet gcode/ : génération du G-Code sans Qt.

Vérifie que le paquet n'importe pas PyQt6, que les threads de controllers/workers.py
produisent exactement le G-Code des fonctions pures, et le contenu du G-Code
(puissance S, commande laser, surbalayage, décalage retour, en-tête et fin).
"""
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
    GcodeResult, MATRIX_CUT, MATRIX_ENGRAVE, bidir_test_gcode, build_job_gcode, build_test_matrix_gcode,
    image_origin,
)
from laser_studio.gcode.common import (  # noqa: E402
    OVERSCAN_PERCENT, job_duration_text, matrix_duration_text, overscan_distance, scan_offset_mm,
)

MODULES = ("laser_studio.gcode", "laser_studio.gcode.common", "laser_studio.gcode.raster",
           "laser_studio.gcode.svg_cut", "laser_studio.gcode.vector", "laser_studio.gcode.job",
           "laser_studio.gcode.test_matrix", "laser_studio.gcode.calibration", "laser_studio.gcode.preview",
           "laser_studio.models.layer_modes")


def job_params(**kw):
    p = {
        'width_mm': 4.0, 'height_mm': 2.0, 'origin_pos': "bottom_left", 'offset_x': 0.0, 'offset_y': 0.0,
        'speed_engrave': 1000, 'power_engrave': 35.0, 'enable_cut': False, 'speed_cut': 300,
        'power_cut': 90.0, 'passes_cut': 1, 'laser_cmd': "M4", 'image_laser_cmd': "M4",
        # Dans l'application : surbalayage global ET calque de gravure (layer_overscan_enabled).
        'image_overscan': False, 'algo': "Floyd-Steinberg", 's_max': 1000, 'homing': False,
        'enable_overscan': False, 'overscan_mode': "Distance Fixe (mm)", 'overscan_dist': 2.5,
        'overscan_pct': 5.0, 'start_gcode': "", 'end_gcode': "", 'scan_offset_mm': 0.0,
        'safe_cut_order': True,
    }
    p.update(kw)
    return p


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
        self.assertEqual(overscan_distance({'overscan_dist': 3.0}, 40.0), 3.0)
        self.assertEqual(overscan_distance({}, 40.0), 2.5)
        self.assertEqual(overscan_distance({'overscan_mode': OVERSCAN_PERCENT, 'overscan_pct': 10.0}, 40.0), 4.0)

    def test_scan_offset_reads_unusable_values_as_zero(self):
        self.assertEqual(scan_offset_mm({'scan_offset_mm': 0.15}), 0.15)
        for value in (None, "", "abc"):
            self.assertEqual(scan_offset_mm({'scan_offset_mm': value}), 0.0)
        self.assertEqual(scan_offset_mm({}), 0.0)

    def test_durations(self):
        self.assertEqual(job_duration_text(30), "34 sec")            # 15 % de marge
        self.assertEqual(job_duration_text(600), "11 min 30 sec")
        self.assertEqual(matrix_duration_text(46), "0 min 46 sec")


class RasterTests(unittest.TestCase):
    def test_binary_pixels_get_the_layer_power(self):
        arr = np.array([[0, 0, 255, 255]], dtype=np.uint8)            # 2 pixels brûlés sur 4
        result = build_job_gcode(arr, None, job_params(height_mm=1.0))
        self.assertIsInstance(result, GcodeResult)
        self.assertIn("G1 X2.000 F1000 S350", lines(result))          # 35 % de S1000, jusqu'au bord du 2e pixel
        self.assertNotIn("OVERSCAN", result.gcode)
        self.assertEqual(result.avg_power, 35.0)

    def test_grayscale_power_follows_the_gray(self):
        arr = np.array([[0, 128, 255]], dtype=np.uint8)
        g = lines(build_job_gcode(arr, None, job_params(width_mm=3.0, height_mm=1.0, algo="Niveaux de Gris")))
        powers = [int(m) for line in g for m in re.findall(r"S(\d+)", line) if line.startswith("G1")]
        self.assertEqual(powers, [350, round(350 * 127 / 255)])       # le blanc (255) n'est pas parcouru

    def test_m4_is_sent_once_and_m3_on_every_line(self):
        arr = np.zeros((3, 4), dtype=np.uint8)
        m4 = lines(build_job_gcode(arr, None, job_params()))
        self.assertEqual(sum(line.startswith("M4") for line in m4), 1)
        m3 = lines(build_job_gcode(arr, None, job_params(laser_cmd="M3", image_laser_cmd="M3")))
        self.assertEqual(m3.count("M3 S0"), 3)
        self.assertEqual(m3.count("M5"), 3 + 1)                       # une par ligne, plus celle de la fin

    def test_overscan_and_return_offset(self):
        arr = np.zeros((2, 4), dtype=np.uint8)
        params = job_params(enable_overscan=True, image_overscan=True, scan_offset_mm=0.2)
        g = lines(build_job_gcode(arr, None, params))
        starts = [line for line in g if line.endswith("OVERSCAN_START")]
        x0, _ = image_origin(params)
        self.assertEqual(x0, 2.5)                                     # marge = surbalayage : départ à X0
        self.assertEqual(starts[0], f"G0 X{x0 - 2.5:.3f} Y{1.0:.3f} ; OVERSCAN_START")          # aller
        self.assertEqual(starts[1], f"G0 X{x0 + 0.2 + 4.0 + 2.5:.3f} Y{0.0:.3f} ; OVERSCAN_START")   # retour décalé

    def test_overscan_off_for_the_engrave_layer(self):
        arr = np.zeros((1, 4), dtype=np.uint8)
        g = build_job_gcode(arr, None, job_params(enable_overscan=True, image_overscan=False)).gcode
        self.assertNotIn("OVERSCAN", g)

    def test_image_origin(self):
        self.assertEqual(image_origin(job_params(offset_x=5.0, offset_y=-3.0)), (5.0, -3.0))   # sans surbalayage
        self.assertEqual(image_origin(job_params(offset_x=5.0, offset_y=-3.0, enable_overscan=True,
                                                 image_overscan=True)), (7.5, -3.0))
        self.assertEqual(image_origin(job_params(origin_pos=ORIGIN_CENTER, offset_x=50.0, offset_y=40.0)),
                         (48.0, 39.0))


class JobTests(unittest.TestCase):
    def test_empty_job(self):
        result = build_job_gcode(None, None, job_params())
        self.assertEqual(lines(result), ["; --- G-CODE HYBRIDE GRBL PRO ---",
                                         "M4 S0 ; Mode laser dynamique activé pour tout le job",
                                         "M5", "G0 X0 Y0", "; FIN DU TRAVAIL"])
        self.assertEqual((result.line_count, result.avg_power, result.duration), (3, 0.0, "0 sec"))

    def test_homing_start_and_end_gcode(self):
        g = lines(build_job_gcode(None, None, job_params(homing=True, start_gcode=" G21 ", end_gcode=" M5 ")))
        self.assertEqual(g[1:4], ["$H ; Homing initial", "; --- G-Code de Début ---", "G21"])
        self.assertEqual(g[-2:], ["; --- G-Code de Fin ---", "M5"])

    def test_progress_ends_at_100(self):
        seen = []
        build_job_gcode(np.zeros((60, 4), dtype=np.uint8), None, job_params(), progress=seen.append)
        self.assertEqual(seen[-3:], [70, 85, 100])
        self.assertEqual(seen, sorted(seen))

    def test_vector_layers_use_the_job_offset(self):
        layer = {"name": "Découpe", "mode": "cut", "speed": 250, "power": 90.0, "passes": 1}
        square = [(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)]
        data = {"c": {"layer": layer, "polygons": [square], "polygon_groups": [[square]]}}
        g = lines(build_job_gcode(None, None, job_params(offset_x=3.0, offset_y=4.0), data))
        self.assertIn("G0 X3.000 Y4.000", g)
        self.assertIn("M4 S900", g)


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
        self.assertRegex(result.duration, r"^\d+ min \d+ sec$")


class CalibrationTests(unittest.TestCase):
    def test_bidir_pattern(self):
        p = {"origin_pos": "bottom_left", "offset_x": 0.0, "offset_y": 0.0, "speed_engrave": 1000,
             "power_engrave": 30.0, "s_max": 1000, "laser_cmd": "M4", "offsets": [-0.1, 0.0, 0.1], "rows": 3}
        gcode, count, avg, _duration = bidir_test_gcode(p)
        self.assertIn("; 3 colonnes", gcode)
        # 3 barres de 4 mm espacées de 2 mm (16 mm), surbalayage de 2,5 mm de chaque côté
        rows = [line for line in gcode.split("\n") if re.match(r"G0 X(-2.500|18.500) ", line)]
        self.assertEqual(len(rows), 4)                                # 3 lignes demandées -> 4 (paire)
        self.assertEqual(sum(line.startswith("G0 X-2.500") for line in rows), 2)   # 2 aller, 2 retour
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
        expected = tuple(build_job_gcode(arr, None, params))
        self.assertEqual(self.run_worker(workers.AdvancedGCodeWorker(arr, None, params)), expected)

    def test_matrix_worker(self):
        params = MatrixTests().params()
        self.assertEqual(self.run_worker(workers.TestMatrixWorker(params)), tuple(build_test_matrix_gcode(params)))


if __name__ == "__main__":
    unittest.main()
