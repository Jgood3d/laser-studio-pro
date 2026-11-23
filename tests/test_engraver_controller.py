"""Contrôleur du graveur (controllers/engraver.py) et commandes GRBL
(grbl/commands.py) : connexion, pilotage, envoi d'un job, configuration $$.
Sans fenêtre : connexion et boîtes de dialogue simulées. Et un parcours
complet avec le graveur GRBL simulé (grbl/simulator.py)."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from laser_studio.grbl import commands  # noqa: E402

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.engraver import EngraverController
    from laser_studio.core.constants import ORIGIN_CENTER
    from laser_studio.i18n import tr
    from laser_studio.models.grbl import GrblConfig
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 manquant
    EngraverController = None


class CommandsTests(unittest.TestCase):
    """Commandes GRBL, sans Qt."""

    def test_simple_commands(self):
        self.assertEqual((commands.HOME, commands.UNLOCK, commands.READ_SETTINGS), ("$H", "$X", "$$"))
        self.assertEqual((commands.SET_WORK_ZERO, commands.GO_TO_WORK_ZERO), ("G92 X0 Y0", "G0 X0 Y0"))

    def test_jog(self):
        self.assertEqual(commands.jog_command(10.0, -0.1, 3000), "$J=G91 G21 X10.000 Y-0.100 F3000")

    def test_frame_goes_round_and_back(self):
        self.assertEqual(commands.frame_commands(10.0, 5.0, 40.0, 30.0), [
            "G0 X10.000 Y5.000", "G0 X50.000 Y5.000", "G0 X50.000 Y35.000", "G0 X10.000 Y35.000",
            "G0 X10.000 Y5.000",
        ])

    def test_setting_lines(self):
        text = " $22=1 \n$32=1 (laser)\nGrbl 1.1h\n$$\nok\n"
        self.assertEqual(commands.setting_lines(text), ["$22=1", "$32=1 (laser)"])
        self.assertEqual(commands.response_setting_lines(text), ["$22=1", "$32=1 (laser)", "$$"])
        self.assertEqual(commands.setting_lines(None), [])

    def test_homing_support(self):
        self.assertEqual(commands.homing_support({"$22": "1"}), (True, None))
        self.assertEqual(commands.homing_support({"$22": "0"}), (False, "disabled"))
        self.assertEqual(commands.homing_support({"$32": "1"}), (False, "unsupported"))
        self.assertIsNone(commands.homing_support({"$22": "abc"}))


def make_engraver(connected=True, homed=True, dialogs=None, gcode="G0 X1\n", **kw):
    connection = mock.Mock()
    connection.is_connected.return_value = connected
    connection.homed = homed
    connection.last_state = "Idle"
    connection.port = "/dev/ttyUSB0"
    dialogs = dialogs or FakeDialogs()
    engraver = EngraverController(connection, GrblConfig(), dialogs, current_gcode=lambda: gcode, **kw)
    events = []
    for name in ("direct_job_started", "direct_job_finished", "job_done", "disconnected"):
        getattr(engraver, name).connect(lambda name=name: events.append(name))
    engraver.stream_starting.connect(lambda text: events.append(("stream_starting", text)))
    engraver.stream_ended.connect(lambda clean: events.append(("stream_ended", clean)))
    engraver.gcode_restored.connect(lambda text: events.append(("gcode_restored", text)))
    engraver.log.connect(lambda text: events.append(("log", text)))
    return engraver, connection, dialogs, events


@unittest.skipIf(EngraverController is None, "PyQt6 non importable ici")
class SendJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_job_starts_after_the_launch_confirmation(self):
        engraver, connection, dialogs, events = make_engraver()
        self.assertTrue(engraver.send_job())
        self.assertEqual(dialogs.kinds(), ["confirm_default_no"])
        self.assertTrue(dialogs.calls[0][2].startswith(tr("startup.safety.body")))   # rappel de sécurité
        self.assertEqual(events, ["direct_job_started", ("stream_starting", "G0 X1\n")])
        connection.pause_status_poll.assert_called_once()
        connection.start_stream.assert_called_once()
        self.assertEqual(connection.start_stream.call_args[0][0], "G0 X1\n")

    def test_refusals(self):
        cases = [
            (dict(gcode="  \n"), ["warning"]),                         # pas de G-Code
            (dict(connected=False), ["warning"]),                      # pas connecté
            (dict(homed=False, dialogs=FakeDialogs(answer=False)), ["confirm_default_no"]),   # pas de homing
            (dict(dialogs=FakeDialogs(answer=False)), ["confirm_default_no"]),                # lancement refusé
        ]
        for kw, kinds in cases:
            engraver, connection, dialogs, events = make_engraver(**kw)
            self.assertFalse(engraver.send_job(), kw)
            self.assertEqual(dialogs.kinds(), kinds, kw)
            connection.start_stream.assert_not_called()

    def test_without_homing_both_questions_are_asked(self):
        engraver, connection, dialogs, _ = make_engraver(homed=False)
        self.assertTrue(engraver.send_job())
        self.assertEqual([c[1] for c in dialogs.calls], [tr("laser.no_homing_title"), tr("laser.confirm_title")])

    def test_end_of_a_direct_job(self):
        engraver, connection, dialogs, events = make_engraver()
        engraver.send_job()
        on_finished = connection.start_stream.call_args[0][1]
        events.clear()
        on_finished(True)
        self.assertEqual(events, [("stream_ended", True), "direct_job_finished", "job_done"])
        connection.check_position_after_stream.assert_called_once()
        connection.resume_status_poll.assert_called_once()
        self.assertEqual(dialogs.kinds()[-1], "info")
        on_finished(False)                                              # job interrompu
        self.assertEqual(dialogs.kinds()[-1], "warning")

    def test_repeat_sends_the_last_gcode_again(self):
        engraver, connection, dialogs, events = make_engraver(gcode="G0 X9\n")
        connection.last_sent_gcode = "G0 X1\n"
        engraver.repeat_last_job()
        self.assertEqual(events[0], ("gcode_restored", "G0 X1\n"))
        self.assertEqual(connection.start_stream.call_args[0][0], "G0 X1\n")

    def test_repeat_without_previous_job(self):
        engraver, connection, dialogs, events = make_engraver()
        connection.last_sent_gcode = None
        engraver.repeat_last_job()
        self.assertEqual((events, dialogs.calls), ([], []))

    def test_queue_streams_use_the_same_path(self):
        engraver, connection, dialogs, events = make_engraver()
        engraver.start_stream("G1 X2\n", print)
        engraver.end_stream(False)
        self.assertEqual(events, [("stream_starting", "G1 X2\n"), ("stream_ended", False)])
        self.assertEqual(dialogs.calls, [])


@unittest.skipIf(EngraverController is None, "PyQt6 non importable ici")
class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_commands_need_a_connection(self):
        engraver, connection, dialogs, _ = make_engraver(connected=False)
        engraver.jog(1.0, 0.0, 3000)
        engraver.home()
        engraver.set_work_zero()
        engraver.frame()
        self.assertEqual(dialogs.kinds(), ["warning"] * 4)
        connection.run_commands.assert_not_called()
        connection.jog.assert_not_called()

    def test_frame_follows_the_image_position(self):
        geometry = {'width_mm': 40.0, 'height_mm': 30.0, 'origin_pos': ORIGIN_CENTER,
                    'offset_x': 100.0, 'offset_y': 80.0}
        engraver, connection, _, _ = make_engraver(job_geometry=lambda: geometry)
        engraver.frame()
        connection.run_commands.assert_called_once_with(commands.frame_commands(80.0, 65.0, 40.0, 30.0))

    def test_realtime_commands_are_logged(self):
        engraver, connection, _, events = make_engraver()
        engraver.pause()
        engraver.resume()
        engraver.reset()
        engraver.emergency_stop()
        self.assertEqual(connection.soft_reset.call_count, 2)
        self.assertEqual(len([e for e in events if e[0] == "log"]), 4)

    def test_unlock_only_when_connected(self):
        engraver, connection, _, _ = make_engraver(connected=False)
        engraver.unlock()
        connection.unlock.assert_not_called()

    def test_disconnect(self):
        engraver, connection, dialogs, events = make_engraver()
        engraver.toggle_connection()
        connection.disconnect.assert_called_once()
        self.assertIn("disconnected", events)

    def test_failed_connection_shows_an_error(self):
        engraver, connection, dialogs, _ = make_engraver(connected=False, selected_port=lambda: "/dev/ttyUSB9 - X")
        connection.connect.return_value = False
        engraver.toggle_connection()
        connection.connect.assert_called_once_with("/dev/ttyUSB9")
        self.assertEqual(dialogs.kinds(), ["error"])

    def test_no_port_selected(self):
        engraver, connection, dialogs, _ = make_engraver(connected=False)
        engraver.toggle_connection()
        self.assertEqual(dialogs.kinds(), ["warning"])
        connection.connect.assert_not_called()

    def test_reconnection_result_is_reported(self):
        connection = mock.Mock()
        dialogs = FakeDialogs()
        engraver = EngraverController(connection, GrblConfig(), dialogs)
        slot = connection.reconnected.connect.call_args[0][0]
        slot(True)
        slot(False)
        self.assertEqual(dialogs.kinds(), ["warning", "error"])
        self.assertIsNotNone(engraver)


@unittest.skipIf(EngraverController is None, "PyQt6 non importable ici")
class GrblSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_read_settings(self):
        engraver, connection, dialogs, _ = make_engraver()
        connection.send_command.return_value = "$22=1\n$32=1\nok\n"
        engraver.read_settings()
        connection.send_command.assert_called_once_with("$$")
        self.assertEqual(engraver.grbl.grbl_settings, "$22=1\n$32=1")

    def test_send_settings_asks_and_reports_errors(self):
        engraver, connection, dialogs, events = make_engraver()
        engraver.grbl.update(grbl_settings="$22=1\n$32=1\n")
        connection.send_command.side_effect = ["ok", "error:3"]
        engraver.send_settings()
        self.assertEqual(dialogs.kinds(), ["confirm_default_no", "warning"])
        self.assertEqual([c.args[0] for c in connection.send_command.call_args_list], ["$22=1", "$32=1"])

    def test_send_settings_refused(self):
        engraver, connection, dialogs, _ = make_engraver(dialogs=FakeDialogs(answer=False))
        engraver.grbl.update(grbl_settings="$22=1\n")
        engraver.send_settings()
        connection.send_command.assert_not_called()

    def test_export_then_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "grbl.txt")
            engraver, _, _, _ = make_engraver(dialogs=FakeDialogs(path=path))
            engraver.grbl.update(grbl_settings="$22=1\n$32=1")
            engraver.export_settings()
            engraver.grbl.update(grbl_settings="")
            engraver.import_settings()
            self.assertEqual(engraver.grbl.grbl_settings, "$22=1\n$32=1")


@unittest.skipIf(EngraverController is None, "PyQt6 non importable ici")
class SimulatedEngraverTests(unittest.TestCase):
    """Parcours complet avec le graveur GRBL simulé : connexion, réglages,
    homing, envoi d'un job jusqu'à sa fin."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = mock.patch.dict(os.environ, {"LASER_STUDIO_SIMULATION": "50",
                                               "XDG_CONFIG_HOME": cls.tmp.name})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def wait(self, condition, timeout=10.0):
        end = time.time() + timeout
        while not condition() and time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        return condition()

    def test_connect_home_and_send_a_job(self):
        from laser_studio.controllers.machine_connection import MachineConnection
        from laser_studio.grbl.simulator import SIMULATED_PORT
        connection = MachineConnection()
        dialogs = FakeDialogs()
        ports = []
        homing = []
        engraver = EngraverController(connection, GrblConfig(), dialogs,
                                      selected_port=lambda: ports[0][ports[1]] if ports else "",
                                      current_gcode=lambda: "G21\nG90\nM4 S0\nG1 X5 Y5 F3000 S100\nG0 X0 Y0\nM5\n",
                                      set_homing_available=lambda available, tip: homing.append(available) or False)
        engraver.ports_changed.connect(lambda labels, index: ports.extend([labels, index]))
        try:
            engraver.refresh_ports()
            self.assertTrue(ports[0][ports[1]].startswith(SIMULATED_PORT))
            engraver.toggle_connection()
            self.assertTrue(connection.is_connected())
            self.assertEqual(homing, [True])                      # le simulateur a le homing ($22=1)
            self.assertNotIn("warning", dialogs.kinds())          # mode laser actif ($32=1)
            engraver.home()
            self.assertTrue(self.wait(lambda: not connection._cmd_thread.isRunning()))
            ended = []
            engraver.stream_ended.connect(ended.append)
            self.assertTrue(engraver.send_job())
            self.assertTrue(self.wait(lambda: ended), "le job ne s'est pas terminé")
            self.assertEqual(ended, [True])
            self.assertEqual(dialogs.kinds()[-1], "info")         # « Gravure terminée »
        finally:
            connection.shutdown()


@unittest.skipIf(EngraverController is None, "PyQt6 non importable ici")
class SimulatedWindowTests(unittest.TestCase):
    """Le même parcours dans la fenêtre : boutons, suivi d'envoi, aperçu 2D."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = mock.patch.dict(os.environ, {"LASER_STUDIO_SIMULATION": "50", "XDG_CONFIG_HOME": cls.tmp.name,
                                               "XDG_DATA_HOME": cls.tmp.name})
        cls.env.start()
        from laser_studio import main_window
        cls.app = QApplication.instance() or QApplication([])
        cls.stencil = mock.patch("stencil_studio.controllers.studio.StencilStudioController.preload")
        cls.stencil.start()
        cls.win = main_window.FullLaserStudio()

    @classmethod
    def tearDownClass(cls):
        # La fenêtre n'est pas fermée : closeEvent demande s'il faut enregistrer le projet.
        cls.win.connection.shutdown()
        cls.stencil.stop()
        cls.env.stop()
        cls.tmp.cleanup()

    def wait(self, condition, timeout=10.0):
        end = time.time() + timeout
        while not condition() and time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        return condition()

    def test_connect_and_send_from_the_panels(self):
        from PyQt6.QtWidgets import QMessageBox
        from laser_studio.grbl.simulator import SIMULATED_PORT
        win, panel = self.win, self.win.machine_panel
        yes = QMessageBox.StandardButton.Yes
        with mock.patch.object(QMessageBox, "question", return_value=yes), \
                mock.patch.object(QMessageBox, "warning", return_value=yes), \
                mock.patch.object(QMessageBox, "information") as info:
            panel.connection_panel.refresh_requested.emit()
            self.assertTrue(panel.connection_panel.selected_port().startswith(SIMULATED_PORT))
            panel.connection_panel.connect_requested.emit()
            self.assertTrue(win.connection.is_connected())
            self.assertTrue(panel.jog_panel.isEnabled())                    # commandes déverrouillées
            win.tab_console_gcode.set_gcode("G21\nG90\nM4 S0\nG1 X5 Y5 F3000 S100\nG0 X0 Y0\nM5\n")
            panel.jog_panel.send_job_requested.emit()
            self.assertFalse(panel.jog_panel.send_button.isEnabled())       # pendant le job
            self.assertTrue(self.wait(lambda: info.called), "le job ne s'est pas terminé")
        self.assertTrue(panel.jog_panel.send_button.isEnabled())
        self.assertEqual(panel.progress_bar.value(), 100)
        sent = panel.sent_gcode_log.text_edit.toPlainText()
        self.assertIn("G1 X5 Y5 F3000 S100", sent)
        self.assertEqual(win.tab_vector_2d.burn.done, len(win.tab_vector_2d.burn.segments))   # tout est rouge
        panel.connection_panel.connect_requested.emit()                   # déconnexion
        self.assertFalse(win.connection.is_connected())
        self.assertEqual(len(win.tab_vector_2d.position_marker.getData()[0]), 0)   # plus de position


if __name__ == "__main__":
    unittest.main()
