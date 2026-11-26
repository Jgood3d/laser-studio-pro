"""JobController (controllers/job.py) : contrôles avant génération, lancement du
thread, export et import du G-Code, motif aller/retour, matrice de test et clic
sur une de ses cases. Sans fenêtre : boîtes de dialogue simulées (job_fakes)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication as QCoreApplication  # QApplication : la fenêtre est créée dans le même processus
    from laser_studio.controllers import job as job_module
    from laser_studio.gcode import MATRIX_CUT, MATRIX_ENGRAVE
    from laser_studio.gcode.test_matrix import matrix_cell_at
    from job_fakes import FakeDialogs, make_job
except ImportError:  # PyQt6 manquant
    job_module = None


def matrix_page(**kw):
    p = {"min_power": 20.0, "max_power": 80.0, "steps_power": 4, "single_power": 85.0,
         "min_passes": 1, "max_passes": 3, "steps_passes": 3, "min_speed": 500.0, "max_speed": 1500.0,
         "steps_speed": 3, "size_square": 10.0, "gap": 2.0, "lines_mm": 5.0,
         "matrix_offset_x": 0.0, "matrix_offset_y": 0.0, "laser_cmd": "M4", "homing": False}
    p.update(kw)
    return p


@unittest.skipIf(job_module is None, "PyQt6 non importable ici")
class GenerateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.worker = mock.Mock()
        patcher = mock.patch.object(job_module, "AdvancedGCodeWorker", return_value=self.worker)
        self.worker_class = patcher.start()
        self.addCleanup(patcher.stop)

    def run_generate(self, job):
        events = []
        job.started.connect(lambda: events.append("started"))
        self.worker.start.side_effect = lambda: events.append("worker.start")
        return job.generate(), events

    def test_image_job_starts_after_the_engrave_confirmation(self):
        job, dialogs = make_job(image=np.zeros((4, 4), np.uint8), geometry_kw={'offset_x': 5.0})
        started, events = self.run_generate(job)
        self.assertTrue(started)
        self.assertEqual(events, ["started", "worker.start"])          # l'aperçu est montré avant
        self.assertEqual(dialogs.kinds(), ["confirm"])                 # rappel puissance / vitesse
        arr, params, vector_data = self.worker_class.call_args[0]
        self.assertIs(arr, job.holder["image"])
        self.assertEqual((params['offset_x'], params['speed_engrave']), (5.0, job.engrave_speed))
        self.assertTrue(all(not d["polygons"] for d in vector_data.values()))   # aucun objet vectoriel

    def test_cancelled_confirmation_does_not_start(self):
        job, dialogs = make_job(image=np.zeros((4, 4), np.uint8), dialogs=FakeDialogs(answer=False))
        started, events = self.run_generate(job)
        self.assertFalse(started)
        self.assertEqual(events, [])

    def test_job_larger_than_the_bed_is_refused(self):
        job, dialogs = make_job(geometry_kw={'width_mm': 10000.0})
        self.assertFalse(job.generate())
        self.assertEqual(dialogs.kinds(), ["warning"])
        self.worker_class.assert_not_called()

    def test_speed_over_the_machine_limit_asks_first(self):
        job, dialogs = make_job(dialogs=FakeDialogs(answer=False))
        layer = job.layers.layers[0]
        job.layers.update(layer.id, speed=int(job.machine.max_speed) + 100)
        self.assertFalse(job.generate())
        self.assertEqual(dialogs.kinds(), ["ask_yes_no"])
        self.assertIn(layer.name, dialogs.last_text("ask_yes_no"))

    def test_overscan_starting_off_the_bed_is_refused(self):
        job, dialogs = make_job(image=np.zeros((4, 4), np.uint8), geometry_kw={'offset_x': -9.0})
        job.grbl.update(overscan_enabled=True, overscan_dist_mm=5.0)      # 10 mm de marge - 9 - 5 < 0
        self.assertFalse(job.generate())
        self.assertEqual(dialogs.kinds(), ["error"])

    def test_vector_only_job_has_no_confirmation(self):
        job, dialogs = make_job()
        started, events = self.run_generate(job)
        self.assertTrue(started)
        self.assertEqual(dialogs.kinds(), [])

    def test_worker_signals_are_relayed(self):
        job, _ = make_job()
        job.generate()
        self.worker.finished.connect.assert_called_once_with(job.generated)
        self.worker.progress.connect.assert_called_once_with(job.progress)
        self.worker.error.connect.assert_called_once_with(job.failed)

    def test_unexpected_error_is_reported(self):
        job, dialogs = make_job()
        logs = []
        job.log.connect(logs.append)
        with mock.patch.object(job, "build_params", side_effect=RuntimeError("boum")):
            self.assertFalse(job.generate())
        self.assertEqual(dialogs.kinds(), ["error"])
        self.assertIn("boum", logs[0])


@unittest.skipIf(job_module is None, "PyQt6 non importable ici")
class ParamsTests(unittest.TestCase):
    def test_params_follow_the_models(self):
        job, _ = make_job(geometry_kw={'width_mm': 12.0})
        job.grbl.update(laser_cmd="M3", overscan_enabled=True, overscan_mode=1, overscan_pct=7.0,
                        scan_offset_mm=0.2, safe_cut_order=False)
        p = job.build_params()
        self.assertEqual(p['width_mm'], 12.0)
        self.assertEqual((p['laser_cmd'], p['image_laser_cmd']), ("M3", "M3"))
        self.assertEqual((p['overscan_mode'], p['overscan_pct'], p['scan_offset_mm']), ("Pourcentage (%)", 7.0, 0.2))
        self.assertNotIn('enable_cut', p)                 # ancienne découpe SVG supprimée
        self.assertFalse(p['safe_cut_order'])
        self.assertTrue(p['image_overscan'])

    def test_machine_limits_come_from_the_grbl_settings_then_the_machine_page(self):
        job, _ = make_job()
        job.machine.update(max_speed=4000.0, accel=800.0)
        limits = job.build_params()['machine_limits']
        self.assertEqual((limits['max_rate_x'], limits['accel_y']), (4000.0, 800.0))
        job.grbl.update(grbl_settings="$110=9000\n$121=300\n")                   # lu avec « Lire la config »
        limits = job.machine_limits()
        self.assertEqual((limits['max_rate_x'], limits['max_rate_y'], limits['accel_y']), (9000.0, 4000.0, 300.0))


@unittest.skipIf(job_module is None, "PyQt6 non importable ici")
class FileTests(unittest.TestCase):
    def test_export_adds_the_extension_and_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, dialogs = make_job(dialogs=FakeDialogs(path=os.path.join(tmp, "job")))
            path = job.export_gcode(".nc", "G0 X0\n")
            self.assertEqual(path, os.path.join(tmp, "job.nc"))
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "G0 X0\n")
            self.assertEqual(dialogs.kinds(), ["save_file", "info"])

    def test_export_of_an_empty_gcode_is_refused(self):
        job, dialogs = make_job()
        self.assertEqual(job.export_gcode(".gcode", "  \n"), "")
        self.assertEqual(dialogs.kinds(), ["warning"])

    def test_export_cancelled(self):
        job, dialogs = make_job(dialogs=FakeDialogs(path=""))
        self.assertEqual(job.export_gcode(".gcode", "G0"), "")
        self.assertEqual(dialogs.kinds(), ["save_file"])

    def test_import_emits_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "autre.nc")
            with open(path, "w", encoding="utf-8") as f:
                f.write("G1 X1\n")
            job, _ = make_job(dialogs=FakeDialogs(path=path))
            got = []
            job.imported.connect(lambda text, p: got.append((text, p)))
            job.import_gcode()
            self.assertEqual(got, [("G1 X1\n", path)])

    def test_unreadable_import_shows_an_error(self):
        job, dialogs = make_job(dialogs=FakeDialogs(path="/chemin/introuvable.nc"))
        job.import_gcode()
        self.assertEqual(dialogs.kinds(), ["open_file", "error"])


@unittest.skipIf(job_module is None, "PyQt6 non importable ici")
class TestPatternTests(unittest.TestCase):
    def test_bidir_test_is_generated_and_forgets_the_matrix(self):
        job, dialogs = make_job()
        job.last_test_matrix_params = {"mode": MATRIX_ENGRAVE}
        got = []
        job.generated.connect(lambda *a: got.append(a))
        job.generate_bidir_test()
        self.assertIn("TEST DE DÉCALAGE ALLER/RETOUR", got[0][0])
        self.assertIsNone(job.last_test_matrix_params)
        self.assertEqual(dialogs.kinds(), ["info"])

    def test_gain_test_is_generated_with_a_header(self):
        """Test du gain de point (onglet Séparation) : grille tramée à la résolution actuelle, en
        miroir comme la gravure du verre, puis G-Code précédé de son mode d'emploi."""
        job, dialogs = make_job()
        job.image_settings.update(mirror_h=True)
        worker = mock.Mock()
        with mock.patch.object(job_module, "AdvancedGCodeWorker", return_value=worker) as cls:
            self.assertTrue(job.generate_gain_test())
        arr, params, vectors = cls.call_args[0]
        self.assertEqual((vectors, params["algo"]), (None, "Floyd-Steinberg"))
        self.assertEqual(arr.shape[1], round(params["width_mm"] * 10.0))      # 10 lignes/mm (make_job)
        worker.start.assert_called_once()
        got = []
        job.generated.connect(lambda *a: got.append(a))
        job._on_gain_test_ready("G1 X1\n", 1, 50.0, 60.0)
        self.assertTrue(got[0][0].startswith("; --- TEST DU GAIN DE POINT ---\n"))
        self.assertTrue(got[0][0].endswith("G1 X1\n"))
        self.assertEqual(got[0][1], 5)                                      # 4 lignes d'en-tête + 1
        self.assertEqual(dialogs.kinds(), ["info"])

    def test_gain_test_larger_than_the_bed_is_refused(self):
        job, dialogs = make_job()
        job.machine.update(bed_w=20.0, bed_h=20.0)
        with mock.patch.object(job_module, "AdvancedGCodeWorker") as cls:
            self.assertFalse(job.generate_gain_test())
        cls.assert_not_called()
        self.assertEqual(dialogs.kinds(), ["warning"])

    def test_matrix_is_generated_with_the_machine_settings(self):
        job, _ = make_job()
        job.grbl.update(smax=255, overscan_enabled=True)
        worker = mock.Mock()
        with mock.patch.object(job_module, "TestMatrixWorker", return_value=worker) as cls:
            self.assertTrue(job.generate_test_matrix(matrix_page(), engraving=True))
        params = cls.call_args[0][0]
        self.assertEqual((params['mode'], params['s_max'], params['enable_overscan']), (MATRIX_ENGRAVE, 255, True))
        worker.finished.connect.assert_called_once_with(job.generated)
        worker.start.assert_called_once()
        self.assertEqual(job.last_test_matrix_params, params)

    def test_image_matrix_without_image_does_not_start(self):
        job, _ = make_job()
        with mock.patch.object(job_module, "TestMatrixWorker") as cls:
            self.assertFalse(job.generate_test_matrix(matrix_page(), True, image_test=True,
                                                      build_tile=lambda lmm: None))
        cls.assert_not_called()

    def test_click_on_an_engrave_cell_applies_it(self):
        job, _ = make_job()
        job.last_test_matrix_params = dict(matrix_page(), mode=MATRIX_ENGRAVE)
        # 2e colonne (40 %), 3e ligne (1500 mm/min) : x = 22 + 12 + 5, y = 14 + 24 + 5
        job.apply_matrix_cell(39.0, 43.0)
        self.assertEqual((job.engrave_speed, job.engrave_power), (1500, 40))

    def test_click_on_a_cut_cell_applies_it(self):
        job, _ = make_job()
        job.last_test_matrix_params = dict(matrix_page(), mode=MATRIX_CUT)
        job.apply_matrix_cell(51.0, 19.0)                               # 3e colonne (3 passes), 1re ligne
        self.assertEqual((job.cut_speed, job.cut_power, job.cut_passes), (500, 85, 3))

    def test_click_without_matrix_changes_nothing(self):
        job, _ = make_job()
        before = (job.engrave_speed, job.engrave_power)
        job.apply_matrix_cell(39.0, 43.0)
        self.assertEqual((job.engrave_speed, job.engrave_power), before)


@unittest.skipIf(job_module is None, "PyQt6 non importable ici")
class MatrixCellTests(unittest.TestCase):
    def test_cells(self):
        p = dict(matrix_page(), mode=MATRIX_ENGRAVE)
        self.assertEqual(matrix_cell_at(p, 23.0, 15.0), (500, 20))           # première case
        self.assertEqual(matrix_cell_at(p, 22 + 3 * 12 + 9.9, 14 + 2 * 12 + 9.9), (1500, 80))   # dernière
        self.assertIsNone(matrix_cell_at(p, 33.0, 15.0))                     # entre deux cases
        self.assertIsNone(matrix_cell_at(p, 10.0, 15.0))                     # étiquettes
        self.assertIsNone(matrix_cell_at(p, 23.0, 60.0))                     # au-delà

    def test_image_cells_use_their_own_size(self):
        p = dict(matrix_page(), mode=MATRIX_ENGRAVE, cell_w=20.0, cell_h=5.0)
        self.assertEqual(matrix_cell_at(p, 22 + 22 + 1, 14 + 7 + 1), (1000, 40))


try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None


@unittest.skipIf(job_module is None or QApplication is None, "PyQt6 non importable ici")
class WindowTests(unittest.TestCase):
    """De bout en bout dans la fenêtre : image tramée -> G-Code dans la console."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": cls.tmp.name, "XDG_DATA_HOME": cls.tmp.name})
        cls.env.start()
        from laser_studio.ui.app import main_window
        cls.app = QApplication.instance() or QApplication([])
        cls.stencil = mock.patch("stencil_studio.controllers.studio.StencilStudioController.preload")
        cls.stencil.start()
        from job_fakes import start_memory_preferences
        start_memory_preferences(cls)           # rien d'écrit dans les réglages de l'utilisateur
        cls.win = main_window.FullLaserStudio()

    @classmethod
    def tearDownClass(cls):
        # La fenêtre n'est pas fermée : closeEvent demande s'il faut enregistrer le projet.
        cls.stencil.stop()
        cls.env.stop()
        cls.tmp.cleanup()

    def test_generated_gcode_reaches_the_console_and_the_2d_tab(self):
        win = self.win
        win.image.processed_array = np.zeros((6, 8), np.uint8)
        win.tab_previews.settings.set_size(8.0, 6.0)
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
                mock.patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Yes):
            self.assertTrue(win.job.generate())
        win.job.worker.wait(10000)
        self.app.processEvents()
        self.assertIn("PHASE 1 : GRAVURE IMAGE", win.tab_console_gcode.gcode())
        self.assertIs(win.main_tabs_view.currentWidget(), win.tab_vector_2d)


if __name__ == "__main__":
    unittest.main()
