"""Tests du statut « référencé » après un RESET / KILL (voir _soft_reset)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from laser_control_mixin import LaserControlMixin
except ImportError as exc:  # PyQt6, pyserial... manquants
    LaserControlMixin = None


class _Console:
    def __init__(self):
        self.lines = []

    def append(self, text):
        self.lines.append(text)


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


@unittest.skipIf(LaserControlMixin is None, "laser_control_mixin non importable ici")
class SoftResetTests(unittest.TestCase):
    def make(self, state, streaming=False, homed=True):
        class Fake(LaserControlMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = _USB(state)
        f.streamer = _Streamer(streaming) if streaming is not None else None
        f.txt_console = _Console()
        f.has_homed_since_connect = homed
        return f

    def test_reset_when_idle_keeps_homed(self):
        for action in ("send_reset", "send_kill"):
            f = self.make("Idle")
            getattr(f, action)()
            self.assertEqual(f.usb.sent, [b"\x18"])
            self.assertTrue(f.has_homed_since_connect, action)

    def test_reset_while_streaming_loses_homed_and_stops_stream(self):
        f = self.make("Idle", streaming=True)   # même si le dernier statut lu est « Idle »
        f.send_kill()
        self.assertTrue(f.streamer.stopped)
        self.assertFalse(f.has_homed_since_connect)

    def test_reset_in_motion_or_hold_loses_homed(self):
        for state in ("Run", "Hold", "Jog", "Alarm", None):
            f = self.make(state)
            f.send_reset()
            self.assertFalse(f.has_homed_since_connect, state)
            self.assertEqual(len(f.txt_console.lines) >= 2, True, state)  # log reset + avertissement

    def test_no_streamer_at_all(self):
        f = self.make("Idle", streaming=None)
        f.send_reset()
        self.assertTrue(f.has_homed_since_connect)


if __name__ == "__main__":
    unittest.main()
