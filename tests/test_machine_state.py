"""État du graveur (models/machine_state.py) : ce qui est permis dans chaque état, et MachineConnection qui le
tient à jour (activité notée au départ d'un thread, effacée à sa fin avant les fonctions de l'appelant)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.models import machine_state as ms  # noqa: E402  (sans Qt)

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers import machine_connection as mc
except ImportError:  # PyQt6, pyserial... manquants
    mc = None


class TableTests(unittest.TestCase):
    def test_state_comes_from_what_is_true_now(self):
        self.assertEqual(ms.machine_state(False), ms.DISCONNECTED)
        self.assertEqual(ms.machine_state(False, reconnecting=True), ms.RECONNECTING)
        self.assertEqual(ms.machine_state(True, None, "Idle"), ms.READY)
        self.assertEqual(ms.machine_state(True, None, "Alarm"), ms.ALARM)
        self.assertEqual(ms.machine_state(True, ms.ACTIVITY_COMMANDS, "Alarm"), ms.COMMANDS)    # $X tapé en alarme
        self.assertEqual(ms.machine_state(True, ms.ACTIVITY_HOMING, "Home"), ms.HOMING)
        self.assertEqual(ms.machine_state(True, ms.ACTIVITY_STREAMING, "Run"), ms.STREAMING)

    def test_only_realtime_commands_during_a_job_or_a_homing(self):
        """Tout le reste se glisserait entre les lignes du job, ou fausserait la prise d'origine."""
        for state in (ms.STREAMING, ms.HOMING):
            self.assertEqual(ms.ALLOWED[state], {ms.REALTIME}, state)

    def test_alarm_allows_unlocking_but_no_motion(self):
        for action in (ms.UNLOCK, ms.HOME, ms.CONSOLE, ms.SETTINGS, ms.REALTIME):
            self.assertTrue(ms.allowed(ms.ALARM, action), action)
        for action in (ms.JOG, ms.MACRO, ms.SEND_JOB):
            self.assertFalse(ms.allowed(ms.ALARM, action), action)

    def test_short_commands_keep_jog_and_console_but_no_job(self):
        self.assertTrue(ms.allowed(ms.COMMANDS, ms.JOG))
        self.assertTrue(ms.allowed(ms.COMMANDS, ms.CONSOLE))
        for action in (ms.SEND_JOB, ms.HOME, ms.MACRO):
            self.assertFalse(ms.allowed(ms.COMMANDS, action), action)

    def test_disconnected_only_connects(self):
        self.assertEqual(ms.ALLOWED[ms.DISCONNECTED], {ms.CONNECT})
        self.assertFalse(ms.allowed(ms.READY, ms.CONNECT))
        self.assertFalse(ms.allowed("inconnu", ms.JOG))


class _USB:
    last_state = "Idle"
    last_port = "/dev/ttyUSB0"

    def is_connected(self):
        return True


if mc is not None:
    class _Streamer(QObject):
        """Thread d'envoi simulé : ne fait rien tant que le test n'émet pas sa fin."""
        finished_signal = pyqtSignal(bool)
        lines_sent = pyqtSignal(list)
        lines_acked = pyqtSignal(int)
        progress = pyqtSignal(int, int)
        log_signal = pyqtSignal(str)
        status_updated = pyqtSignal(str, float, float, float)
        connection_lost = pyqtSignal()

        def __init__(self, usb, gcode):
            super().__init__()

        def start(self):
            pass


@unittest.skipIf(mc is None, "machine_connection non importable ici")
class ConnectionStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_next_queue_job_can_start_as_soon_as_the_previous_one_ends(self):
        """La file lance le job suivant depuis la fin du précédent : le graveur doit déjà être libre à ce
        moment-là (avant, l'état venait de isRunning(), parfois encore vrai)."""
        c = mc.MachineConnection(usb=_USB())
        states, seen = [], []
        c.state_changed.connect(states.append)
        with mock.patch.object(mc, "GCodeStreamerThread", _Streamer):
            first = c.start_stream("G1 X1\n", lambda clean: seen.append((clean, c.is_busy(), c.can(ms.SEND_JOB))))
            self.assertEqual(c.state, ms.STREAMING)
            self.assertIsNone(c.start_stream("G1 X2\n", lambda clean: None))       # pas deux envois
            self.assertFalse(c.can(ms.JOG))
            first.finished_signal.emit(True)
        self.assertEqual(seen, [(True, False, True)])
        self.assertEqual(states, [ms.STREAMING, ms.READY])

    def test_alarm_reported_by_grbl_changes_the_state(self):
        c = mc.MachineConnection(usb=_USB())
        states = []
        c.state_changed.connect(states.append)
        c.usb.last_state = "Alarm"
        c.status_updated.emit("Alarm", 0.0, 0.0, 0.0)
        self.assertEqual((c.state, states), (ms.ALARM, [ms.ALARM]))
        self.assertTrue(c.can(ms.UNLOCK))
        self.assertFalse(c.can(ms.JOG))


if __name__ == "__main__":
    unittest.main()
