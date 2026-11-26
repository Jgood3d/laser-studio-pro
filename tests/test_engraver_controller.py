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
    from laser_studio.gcode.params import JobParams
    from laser_studio.i18n import tr
    from laser_studio.models import machine_state as ms
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

    def test_frame_goes_round_with_the_laser_barely_on(self):
        square = [(10.0, 5.0), (50.0, 5.0), (50.0, 35.0), (10.0, 35.0), (10.0, 5.0)]
        self.assertEqual(commands.frame_commands([square, [(0, 0), (1, 0), (0, 0)]], 5), [
            "G90", "G0 X10.000 Y5.000", "M3 S5", "G1 X50.000 Y5.000 F3000", "G1 X50.000 Y35.000",
            "G1 X10.000 Y35.000", "G1 X10.000 Y5.000", "M5",
            "G0 X0.000 Y0.000", "M3 S5", "G1 X1.000 Y0.000 F3000", "G1 X0.000 Y0.000", "M5",   # laser éteint entre deux
        ])

    def test_setting_lines(self):
        text = " $22=1 \n$32=1 (laser)\nGrbl 1.1h\n$$\nok\n"
        self.assertEqual(commands.setting_lines(text), ["$22=1", "$32=1"])          # commentaire écarté
        self.assertEqual(commands.response_setting_lines(text), ["$22=1", "$32=1 (laser)", "$$"])
        self.assertEqual(commands.setting_lines(None), [])

    def test_only_numeric_settings_are_ever_written(self):
        """Effacer la carte, une ligne de démarrage (le laser s'y allumerait), un déplacement ou la veille
        ont la même forme qu'un réglage : jamais importés ni envoyés."""
        text = "$110=6000\n$RST=*\n$N0=M3 S1000\n$J=G91 X50 F3000\n$SLP=1\n$32 = 1"
        self.assertEqual(commands.setting_lines(text), ["$110=6000", "$32=1"])

    def test_homing_support(self):
        self.assertEqual(commands.homing_support({"$22": "1"}), (True, None))
        self.assertEqual(commands.homing_support({"$22": "0"}), (False, "disabled"))
        self.assertEqual(commands.homing_support({"$32": "1"}), (False, "unsupported"))
        self.assertIsNone(commands.homing_support({"$22": "abc"}))


def make_engraver(connected=True, homed=True, dialogs=None, gcode="G0 X1\n", state=None, **kw):
    connection = mock.Mock()
    connection.is_connected.return_value = connected
    # État du graveur et permissions : la vraie table (models/machine_state.py).
    connection.state = state or (ms.READY if connected else ms.DISCONNECTED)
    connection.can.side_effect = lambda action: ms.allowed(connection.state, action)
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

    def test_without_homing_a_single_window_lists_it(self):
        # Une seule fenêtre : la sécurité, puis « À vérifier » avec ce qui pose problème (ici, pas de homing).
        engraver, connection, dialogs, _ = make_engraver(homed=False)
        self.assertTrue(engraver.send_job())
        self.assertEqual([c[1] for c in dialogs.calls], [tr("laser.confirm_title")])
        self.assertIn(tr("laser.check_not_homed"), dialogs.calls[0][2])
        engraver, connection, dialogs, _ = make_engraver()                  # rien à signaler : pas de liste
        engraver.send_job()
        self.assertNotIn(tr("laser.check_title"), dialogs.calls[0][2])

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

    def test_gcode_that_rewrites_the_board_is_confirmed_first(self):
        # Fichier d'un autre outil : « $130=… » change la taille du plateau, S au-delà du S-Max (1000).
        risky = "G21\n$130=500\nG1 X5 S1500\n"
        engraver, connection, dialogs, events = make_engraver(gcode=risky, dialogs=FakeDialogs(answer=False))
        self.assertFalse(engraver.send_job())
        self.assertEqual(dialogs.kinds(), ["confirm_default_no"])
        self.assertIn("$130=500", dialogs.calls[0][2])
        self.assertIn("G1 X5 S1500", dialogs.calls[0][2])
        connection.start_stream.assert_not_called()
        engraver, connection, dialogs, events = make_engraver(gcode=risky)
        self.assertTrue(engraver.send_job())                       # une seule fenêtre, lignes listées dedans
        self.assertEqual(dialogs.kinds(), ["confirm_default_no"])

    def test_risky_lines_ignore_comments_and_harmless_dollar_commands(self):
        from laser_studio.grbl.commands import risky_lines
        text = "; S5000\n(S9999) G1 X2 S10\n$H\n$$\n$X\n$J=G91 X1 F100\n$RST=*\n$N0=M3 S1000\n$SLP\n"
        self.assertEqual(risky_lines(text, 1000), ["$RST=*", "$N0=M3 S1000", "$SLP"])
        self.assertEqual(risky_lines("G1 X1 S1000\nG1 X2 S999.5\n", 1000), [])    # au S-Max : normal
        self.assertEqual(len(risky_lines("G1 S2000\n" * 50, 1000)), 10)           # liste bornée

    def test_a_stopped_job_can_be_resumed_where_it_stopped(self):
        job = "".join(f"G1 X{i} S100\n" for i in range(40))
        engraver, connection, dialogs, events = make_engraver(gcode=job)
        available = []
        engraver.resume_available.connect(available.append)
        engraver.start_stream(job, lambda clean: None)
        engraver._lines_acked(30)
        engraver.end_stream(False)                                 # alarme, arrêt, coupure
        self.assertEqual(available[-1], True)
        self.assertTrue(engraver.resume_job())
        sent = connection.start_stream.call_args_list[-1][0][0].split("\n")
        self.assertEqual(sent[:6], ["G21", "M5", "G90", "G0 X14.000 Y0.000", "G1", "G1 X15 S100"])   # 30 - 15
        self.assertIn("16", dialogs.calls[-1][2])                     # ligne de reprise annoncée
        engraver.end_stream(True)                                  # fin propre : plus rien à reprendre
        self.assertEqual((available[-1], engraver.resume_point), (False, None))

    def test_resume_starts_at_the_exact_stop_position(self):
        # La première position rapportée machine arrêtée est exacte : seul le reste du trait est regravé ; le
        # homing fait ensuite (tête à l'origine) ne la change plus.
        job = "".join(f"G1 X{i} Y0 S100 F1000\n" for i in range(40))
        engraver, connection, dialogs, events = make_engraver(gcode=job)
        engraver.start_stream(job, lambda clean: None)
        engraver._status_updated("Run", 25.0, 0.0, 0.0)
        engraver._lines_acked(30)
        engraver.end_stream(False)
        engraver._status_updated("Alarm", 27.4, 0.0, 0.0)            # position exacte à l'arrêt
        engraver._status_updated("Idle", 0.0, 0.0, 0.0)              # après le homing
        self.assertTrue(engraver.resume_job())
        sent = connection.start_stream.call_args_list[-1][0][0].split("\n")
        self.assertEqual(sent[3:6], ["G0 X27.400 Y0.000", "G1 F1000", "G1 X28 Y0 S100 F1000"])

    def test_resume_in_alarm_explains_what_to_do_first(self):
        # Après un arrêt d'urgence, GRBL est en alarme : la reprise ne part pas, elle explique (homing ou $X).
        job = "".join(f"G1 X{i} S100\n" for i in range(40))
        engraver, connection, dialogs, _events = make_engraver(gcode=job, state=ms.ALARM)
        engraver.start_stream(job, lambda clean: None)
        engraver._lines_acked(30)
        engraver.end_stream(False)
        self.assertFalse(engraver.resume_job())
        self.assertEqual(dialogs.kinds(), ["warning"])
        connection.start_stream.assert_called_once()                # seulement l'envoi d'origine
        self.assertIsNotNone(engraver.resume_point)                 # le point de reprise est gardé

    def test_green_resume_button_resumes_the_interrupted_job(self):
        # Le cas vécu : après l'arrêt d'urgence et le déverrouillage, on clique sur le bouton vert « Reprise »
        # (F8) ; ~ n'y ferait rien, c'est le job interrompu qui repart. Pendant un envoi, il reste la reprise ~.
        job = "".join(f"G1 X{i} S100\n" for i in range(40))
        engraver, connection, dialogs, _events = make_engraver(gcode=job)
        connection.is_streaming.return_value = False
        engraver.start_stream(job, lambda clean: None)
        engraver._lines_acked(30)
        engraver.end_stream(False)
        engraver.resume()
        connection.resume.assert_not_called()
        self.assertEqual(connection.start_stream.call_count, 2)       # le job repris
        self.assertEqual(dialogs.kinds(), ["confirm_default_no"])
        connection.is_streaming.return_value = True                  # en pause pendant l'envoi repris
        engraver.resume()
        connection.resume.assert_called_once()

    def test_pause_and_resume_keys_do_nothing_when_disconnected(self):
        engraver, connection, dialogs, events = make_engraver(connected=False)
        engraver.pause()
        engraver.resume()
        connection.pause.assert_not_called()
        connection.resume.assert_not_called()
        engraver, connection, dialogs, events = make_engraver(state=ms.STREAMING)
        engraver.pause()
        connection.pause.assert_called_once()

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

    def test_nothing_is_sent_while_a_job_runs(self):
        """Pendant un job : déplacement, console, cadrage, homing, $$ et second job refusés, avec un message."""
        engraver, connection, dialogs, _ = make_engraver(state=ms.STREAMING)
        engraver.jog(1.0, 0.0, 3000)
        engraver.send_console_command("G0 X0 Y0")
        engraver.frame()
        engraver.home()
        engraver.read_settings()
        self.assertFalse(engraver.send_job())
        self.assertEqual(dialogs.kinds(), ["warning"] * 6)
        connection.run_commands.assert_not_called()
        connection.start_stream.assert_not_called()
        connection.send_command.assert_not_called()

    def test_frame_follows_the_image_position(self):
        geometry = JobParams(width_mm=40.0, height_mm=30.0, origin_pos=ORIGIN_CENTER, offset_x=100.0,
                             offset_y=80.0, speed_engrave=1000, power_engrave=30.0, laser_cmd="M4", s_max=1000)
        engraver, connection, _, _ = make_engraver(job_geometry=lambda: geometry, gcode="")
        engraver.frame()                                           # pas encore de G-Code : le cadre de l'image
        square = [(80.0, 65.0), (120.0, 65.0), (120.0, 95.0), (80.0, 95.0), (80.0, 65.0)]
        connection.run_commands.assert_called_once_with(commands.frame_commands([square], 5.0))   # 0,5 % de S1000

    def test_frame_follows_what_will_be_engraved(self):
        # G-Code d'une pièce en L : le rectangle l'englobe, le contour suit son creux.
        job = "G90\nM4 S0\nG0 X0 Y0\nG1 X20 Y0 S500 F1000\nG1 X20 Y6\nG1 X6 Y6\nG1 X6 Y20\nG1 X0 Y20\nG1 X0 Y0\nM5\n"
        engraver, connection, dialogs, _ = make_engraver(gcode=job)
        engraver.frame()
        sent = connection.run_commands.call_args[0][0]
        self.assertEqual(sent[1:4], ["G0 X0.000 Y0.000", "M3 S5", "G1 X20.000 Y0.000 F3000"])
        self.assertIn("G1 X20.000 Y20.000", sent)                       # coin du rectangle, hors de la pièce
        engraver.frame(contour=True)
        sent = connection.run_commands.call_args[0][0]
        self.assertNotIn("G1 X20.000 Y20.000", sent)                    # le contour rentre dans le creux
        self.assertEqual((sent[-1], sent.count("M3 S5")), ("M5", 1))
        engraver.grbl.update(frame_power_pct=2.0)                       # diode qui ne s'allume qu'à 2 %
        engraver.frame()
        self.assertIn("M3 S20", connection.run_commands.call_args[0][0])
        engraver, connection, dialogs, _ = make_engraver(gcode="")
        engraver.frame(contour=True)                                    # contour sans G-Code : le dire
        self.assertEqual(dialogs.kinds(), ["warning"])
        connection.run_commands.assert_not_called()

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
            self.assertTrue(self.wait(lambda: not connection.is_busy()))
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
            stop = win.main_toolbar.stop_button_action
            self.assertFalse(stop.isVisible())
            self.assertTrue(win.app_actions.emergency_stop.isEnabled())     # F9 : graveur connecté
            panel.jog_panel.send_job_requested.emit()
            self.assertFalse(panel.jog_panel.send_button.isEnabled())       # pendant le job
            self.assertTrue(stop.isVisible())                               # arrêt d'urgence dans la barre
            self.assertTrue(self.wait(lambda: info.called), "le job ne s'est pas terminé")
        self.assertTrue(panel.jog_panel.send_button.isEnabled())
        self.assertFalse(stop.isVisible())
        self.assertEqual(panel.progress_bar.value(), 100)
        sent = panel.sent_gcode_log.text_edit.toPlainText()
        self.assertIn("G1 X5 Y5 F3000 S100", sent)
        self.assertEqual(win.tab_vector_2d.burn.done, len(win.tab_vector_2d.burn.segments))   # tout est rouge
        panel.connection_panel.connect_requested.emit()                   # déconnexion
        self.assertFalse(win.connection.is_connected())

    def test_resume_after_an_emergency_stop(self):
        # Le cas vécu : arrêt d'urgence en pleine gravure, alarme, déverrouillage, puis « Reprendre ».
        from PyQt6.QtWidgets import QMessageBox
        win, panel = self.win, self.win.machine_panel
        resume = panel.job_actions_panel.buttons["resume"]
        yes = QMessageBox.StandardButton.Yes
        with mock.patch.object(QMessageBox, "question", return_value=yes), \
                mock.patch.object(QMessageBox, "warning", return_value=yes) as warning, \
                mock.patch.object(QMessageBox, "information"):
            panel.connection_panel.refresh_requested.emit()
            panel.connection_panel.connect_requested.emit()
            job = "G21\nG90\nM4 S0\n" + "".join(f"G1 X{i % 50} Y{i // 50} F3000 S300\n" for i in range(400)) + "M5\n"
            win.tab_console_gcode.set_gcode(job)
            panel.jog_panel.send_job_requested.emit()
            self.assertTrue(self.wait(lambda: win.engraver._acked > 40))
            win.app_actions.emergency_stop.trigger()                       # F9
            self.assertTrue(self.wait(lambda: win.connection.state == ms.ALARM))
            self.assertTrue(self.wait(lambda: resume.isEnabled()))          # cliquable en alarme : il explique
            warning.reset_mock()
            resume.click()
            self.assertIn("homing", warning.call_args[0][2])
            self.assertFalse(win.connection.is_streaming())
            win.engraver.unlock()
            self.assertTrue(self.wait(lambda: win.connection.state == ms.READY and resume.isEnabled()))
            burn = win.tab_vector_2d.burn
            burned = burn.done
            panel.jog_panel.resume_requested.emit()                          # bouton vert « Reprise » (F8)
            self.assertTrue(self.wait(lambda: win.connection.is_streaming()), "la reprise n'est pas partie")
            first_lines = win.connection.last_sent_gcode.split("\n")[:4]
            self.assertEqual(first_lines[:3], ["G21", "M5", "G90"])
            self.assertTrue(first_lines[3].startswith("G0 X"))                # retour, laser éteint, au point d'arrêt
            # L'aperçu garde le job entier et le tracé déjà gravé, qui continue d'avancer (pas le reste seul).
            self.assertEqual(win.job_display.last_gcode_text, job)
            self.assertGreaterEqual(burn.done, burned)
            self.assertTrue(self.wait(lambda: burn.done > burned))
            win.engraver.emergency_stop()
            self.wait(lambda: not win.connection.is_streaming())
        panel.connection_panel.connect_requested.emit()
        self.assertEqual(len(win.tab_vector_2d.position_marker.getData()[0]), 0)   # plus de position


if __name__ == "__main__":
    unittest.main()
