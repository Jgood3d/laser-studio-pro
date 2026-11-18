"""Statut « référencé » après un RESET / KILL ou un arrêt sur erreur
(voir MachineConnection.soft_reset et check_position_after_stream)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from laser_studio.controllers.machine_connection import MachineConnection
except ImportError:  # PyQt6, pyserial... manquants
    MachineConnection = None


class _USB:
    def __init__(self, state):
        self.last_state = state
        self.sent = []

    def send_raw_byte(self, b):
        self.sent.append(b)


class _Streamer:
    def __init__(self, running):
        self._running = running
        self.stopped = False

    def isRunning(self):
        return self._running

    def stop(self):
        self.stopped = True


@unittest.skipIf(MachineConnection is None, "machine_connection non importable ici")
class SoftResetTests(unittest.TestCase):
    def make(self, state, streaming=False, homed=True):
        c = MachineConnection(usb=_USB(state))
        c.streamer = _Streamer(streaming) if streaming is not None else None
        c.homed = homed
        self.lost = []
        c.position_lost.connect(lambda: self.lost.append(True))
        return c

    def test_reset_when_idle_keeps_homed(self):
        c = self.make("Idle")
        self.assertFalse(c.soft_reset())
        self.assertEqual(c.usb.sent, [b"\x18"])
        self.assertTrue(c.homed)
        self.assertEqual(self.lost, [])

    def test_reset_while_streaming_loses_homed_and_stops_stream(self):
        c = self.make("Run", streaming=True)
        self.assertTrue(c.soft_reset())
        self.assertTrue(c.streamer.stopped)
        self.assertFalse(c.homed)
        self.assertEqual(self.lost, [True])

    def test_reset_in_motion_or_hold_loses_homed(self):
        for state in ("Run", "Hold:0", "Jog", None):
            c = self.make(state)
            c.soft_reset()
            self.assertFalse(c.homed, state)

    def test_no_streamer_at_all(self):
        c = self.make("Idle", streaming=None)
        c.soft_reset()
        self.assertTrue(c.homed)

    def test_error_stop_in_motion_loses_homed(self):
        for position_lost in (False, True):
            c = self.make("Idle", streaming=False)
            c.streamer.position_lost = position_lost
            self.assertEqual(c.check_position_after_stream(), position_lost)
            self.assertEqual(c.homed, not position_lost)


class _PortUSB:
    """Port série simulé : s'ouvre si `opens`, répond `response` à toute commande."""

    def __init__(self, opens=True, response=""):
        self.opens = opens
        self.response = response
        self.connected = False
        self.last_port = None

    def connect(self, port, baudrate=115200):
        self.connected = self.opens
        if self.opens:
            self.last_port = port
        return self.opens

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def send_command(self, cmd):
        return self.response


@unittest.skipIf(MachineConnection is None, "machine_connection non importable ici")
class ConnectionTests(unittest.TestCase):
    def make(self, **kwargs):
        c = MachineConnection(usb=_PortUSB(**kwargs))
        # Pas de vrai thread de sondage dans ces tests.
        c.start_status_poll = lambda: None
        self.changes = []
        c.connection_changed.connect(self.changes.append)
        return c

    def test_connect_and_disconnect_reset_homing(self):
        c = self.make()
        c.homed = True
        self.assertTrue(c.connect("/dev/ttyUSB0"))
        self.assertFalse(c.homed)
        self.assertEqual(c.port, "/dev/ttyUSB0")
        c.homed = True
        c.disconnect()
        self.assertFalse(c.homed)
        self.assertEqual(self.changes, [True, False])

    def test_port_that_does_not_open(self):
        c = self.make(opens=False)
        self.assertFalse(c.connect("/dev/ttyS0"))
        self.assertEqual(self.changes, [])

    def test_read_settings(self):
        c = self.make(response="$22=1 (homing)\n$32=1\nok")
        self.assertEqual(c.read_settings(), {"$22": "1", "$32": "1"})
        self.assertEqual(self.make(response="").read_settings(), {})

    def test_home_and_jog_commands(self):
        c = self.make()
        sent = []
        c.run_commands = sent.append
        c.home()
        c.jog(1.0, -0.5, 3000)
        c.unlock()
        self.assertEqual(sent, ["$H", "$J=G91 G21 X1.000 Y-0.500 F3000", "$X"])
        self.assertTrue(c.homed)

    def test_reconnection_after_a_cut_forgets_homing(self):
        c = self.make()
        c.usb.connected = True
        c.homed = True
        results = []
        c.reconnected.connect(results.append)
        c._on_reconnect_result(True)
        self.assertFalse(c.homed)
        self.assertEqual((results, self.changes), ([True], [True]))


if __name__ == "__main__":
    unittest.main()
