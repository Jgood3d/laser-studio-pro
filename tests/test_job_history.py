"""Historique des gravures : statistiques d'un G-Code (gcode/stats.py), fichier (models/job_history.py),
enregistrement de chaque envoi (controllers/job_history.py) et fenêtre."""
import csv
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.gcode.stats import gcode_statistics  # noqa: E402  (sans Qt)

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.job_history import (
        DONE, ERROR, STOPPED, JobHistoryRecorder, clear_history, export_history)
    from laser_studio.models.job_history import JobHistory
except ImportError:  # PyQt6 manquant
    JobHistory = None

GCODE = "G21\nG90\nM4 S0\nF1000\nG0 X10 Y0\nG1 X20 S500\nG1 X30 S0\nG91\nG0 Y5\nG90\nM5\n$H\n; fin"


class StatisticsTests(unittest.TestCase):
    def test_burn_travel_and_bounds(self):
        stats = gcode_statistics(GCODE)
        self.assertEqual((stats["g0"], stats["g1"], stats["burn_mm"], stats["travel_mm"]), (2, 2, 10.0, 25.0))
        self.assertEqual((stats["max_feed"], stats["max_power"], stats["bounds"]), (1000.0, 500.0, [10.0, 0.0, 30.0, 5.0]))
        self.assertEqual(stats["lines"], 11)                         # sans $H ni commentaire

    def test_laser_off_after_m5(self):
        stats = gcode_statistics("M3 S800\nG1 X10\nM5\nG1 X20\n")
        self.assertEqual((stats["burn_mm"], stats["travel_mm"]), (10.0, 10.0))
        self.assertIsNone(gcode_statistics("")["bounds"])


@unittest.skipIf(JobHistory is None, "PyQt6 non importable ici")
class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.history = JobHistory(os.path.join(self.dir.name, "h.jsonl"))
        self.now = [1000.0]
        self.streamer = SimpleNamespace(stopped_on_error=False, stopped_by_user=False, acked=42)
        self.recorder = JobHistoryRecorder(self.history, SimpleNamespace(streamer=self.streamer),
                                           context=lambda: {"profile": "Atomstack", "accel": 500.0},
                                           clock=lambda: self.now[0])

    def run_job(self, clean, seconds=90.0, gcode=GCODE):
        self.recorder.job_started(gcode)
        self.now[0] += seconds
        return self.recorder.job_ended(clean)

    def test_a_finished_job_is_recorded_with_its_estimate(self):
        self.recorder.remember_estimate(GCODE, 13, 50.0, 80.0)
        entry = self.run_job(True)
        self.assertEqual((entry["result"], entry["duration_s"], entry["estimated_s"]), (DONE, 90.0, 80.0))
        self.assertEqual((entry["profile"], entry["accel"], entry["acked_lines"], entry["burn_mm"]),
                         ("Atomstack", 500.0, 42, 10.0))
        self.assertEqual(self.history.entries(), [entry])

    def test_simulated_engraver_duration_is_scaled(self):
        """Graveur simulé à ×20 : 90 s mesurées = 1 800 s sur la machine simulée."""
        connection = SimpleNamespace(streamer=self.streamer, simulation_speed=lambda: 20.0)
        self.recorder = JobHistoryRecorder(self.history, connection, clock=lambda: self.now[0])
        entry = self.run_job(True)
        self.assertEqual((entry["duration_s"], entry["simulation"]), (1800.0, 20.0))

    def test_simulation_speed_of_the_connection(self):
        from laser_studio.controllers.machine_connection import MachineConnection
        from laser_studio.grbl.simulator import SimulatedGrblSerial
        usb = SimpleNamespace(ser=SimulatedGrblSerial(speed=20.0), is_connected=lambda: True)
        self.assertEqual(MachineConnection(usb).simulation_speed(), 20.0)
        usb.ser = SimpleNamespace(is_open=True)                          # vrai port série
        self.assertIsNone(MachineConnection(usb).simulation_speed())
        usb.is_connected = lambda: False
        self.assertIsNone(MachineConnection(usb).simulation_speed())

    def test_outcomes_and_unknown_estimate(self):
        self.streamer.stopped_on_error = True
        self.assertEqual(self.run_job(False, gcode="G1 X1")["result"], ERROR)
        self.streamer.stopped_on_error, self.streamer.stopped_by_user = False, True
        entry = self.run_job(False, gcode="G1 X2")
        self.assertEqual((entry["result"], entry["estimated_s"]), (STOPPED, None))   # G-Code jamais généré ici
        self.assertIsNone(self.recorder.job_ended(True))                             # pas d'envoi en cours

    def test_export_and_clear_go_through_the_controller(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from job_fakes import FakeDialogs
        self.run_job(True)
        out = os.path.join(self.dir.name, "export.csv")
        self.assertEqual(export_history(self.history, FakeDialogs(path=out)), out)
        self.assertTrue(os.path.exists(out))
        self.assertIsNone(export_history(self.history, FakeDialogs(path="")))          # annulé
        self.assertFalse(clear_history(self.history, FakeDialogs(answer=False)))        # Non : rien d'effacé
        self.assertEqual(len(self.history.entries()), 1)
        self.assertTrue(clear_history(self.history, FakeDialogs(answer=True)))
        self.assertEqual(self.history.entries(), [])

    def test_file_survives_a_bad_line_exports_and_clears(self):
        self.run_job(True)
        with open(self.history.path, "a", encoding="utf-8") as f:
            f.write("ceci n'est pas du JSON\n")
        self.run_job(True)
        self.assertEqual(len(self.history.entries()), 2)
        out = os.path.join(self.dir.name, "h.csv")
        self.history.export_csv(out)
        with open(out, encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        self.assertEqual((len(rows), rows[0]["result"], rows[0]["bounds"]), (2, DONE, "10.0 0.0 30.0 5.0"))
        self.history.clear()
        self.assertEqual(self.history.entries(), [])

    def test_dialog_lists_the_newest_first_with_the_gap(self):
        from laser_studio.ui.dialogs.job_history import JobHistoryDialog
        from laser_studio.ui.dialogs.job_history.dialog import gap_text
        self.recorder.remember_estimate(GCODE, 13, 50.0, 80.0)
        self.run_job(True, 100.0)
        self.run_job(False, 10.0, gcode="G1 X1")
        dialog = JobHistoryDialog(self.history)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.table.rowCount(), 2)
        self.assertEqual(dialog.table.item(1, 4).text(), "-20 %")      # 80 s estimées pour 100 s réelles
        self.assertEqual(gap_text({"result": "done", "duration_s": 100, "estimated_s": None}), "")
        self.assertEqual(gap_text({"result": "stopped", "duration_s": 10, "estimated_s": 80}), "")   # pas allée au bout
        self.run_job(True, 5.0)
        self.assertEqual(dialog.table.rowCount(), 3)                    # suit le modèle



@unittest.skipIf(JobHistory is None, "PyQt6 non importable ici")
class DurationFactorTests(unittest.TestCase):
    """Estimation recalée sur les durées réelles des gravures terminées de la même machine."""

    @staticmethod
    def entry(real, estimate, result="done", profile="Phecda", **extra):
        return {"result": result, "duration_s": real, "estimated_s": estimate, "profile": profile, **extra}

    def test_median_ratio_of_finished_jobs_of_this_machine(self):
        from laser_studio.controllers.job_history import duration_factor
        entries = [self.entry(120, 100), self.entry(150, 100), self.entry(130, 100),
                   self.entry(999, 100, result="stopped"),                  # arrêtée : ne compte pas
                   self.entry(999, 100, profile="Atomstack"),               # autre machine
                   self.entry(999, 100, simulation=50),                     # simulation
                   self.entry(20, 10)]                                      # trop court
        self.assertEqual(duration_factor(entries, "Phecda"), (1.3, 3))
        self.assertIsNone(duration_factor(entries[:2], "Phecda"))            # pas encore assez de gravures

if __name__ == "__main__":
    unittest.main()
