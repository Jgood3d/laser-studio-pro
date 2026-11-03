"""Arrêt de la machine quand GRBL renvoie une erreur pendant l'envoi (GCodeStreamerThread)."""
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from workers import GCodeStreamerThread
except ImportError:  # PyQt6, numpy... manquants
    GCodeStreamerThread = None


class FakeGrbl:
    """Port série simulé : répond « ok » à chaque ligne, sauf celles de `errors` (réponse
    donnée), et à « ? » par un rapport d'état qui dépend de `hold_state` après un « ! »."""

    def __init__(self, errors=None, hold_state="Hold:0"):
        self.errors = errors or {}
        self.hold_state = hold_state
        self.is_open = True
        self.written = []
        self._out = []
        self._held = False

    @property
    def in_waiting(self):
        return len(self._out)

    def readline(self):
        return (self._out.pop(0) + "\r\n").encode() if self._out else b""

    def reset_input_buffer(self):
        self._out.clear()

    def write(self, data):
        self.written.append(data)
        if data == b"!":
            self._held = True
        elif data == b"?":
            state = self.hold_state if self._held else "Idle"
            self._out.append(f"<{state}|MPos:1.000,2.000,0.000|FS:0,0>")
        elif data.endswith(b"\n"):
            self._out.append(self.errors.get(data.decode().strip(), "ok"))

    def realtime(self):
        return [b for b in self.written if b in (b"!", b"\x18")]


class FakeUSB:
    def __init__(self, ser):
        self.ser = ser
        self._lock = threading.Lock()
        self.last_state = None

    def update_last_status(self, line):
        from usb_controller import LaserUSBController
        parsed = LaserUSBController.parse_status_line(line)
        if parsed:
            self.last_state = parsed[0]
        return parsed


@unittest.skipIf(GCodeStreamerThread is None, "workers non importable ici")
class StreamErrorStopTests(unittest.TestCase):
    GCODE = "G21\nG90\nBAD LINE\nG1 X10 F1000\nM5\n"

    def run_stream(self, ser, gcode=None):
        streamer = GCodeStreamerThread(FakeUSB(ser), gcode or self.GCODE)
        streamer._hold_timeout = 0.3
        logs, results = [], []
        streamer.log_signal.connect(logs.append)
        streamer.finished_signal.connect(results.append)
        streamer.run()                      # synchrone : pas de thread pour le test
        return streamer, logs, results

    def test_error_sends_feed_hold_then_reset(self):
        ser = FakeGrbl(errors={"BAD LINE": "error:1"})
        streamer, logs, results = self.run_stream(ser)
        self.assertEqual(ser.realtime(), [b"!", b"\x18"])
        self.assertTrue(streamer.stopped_on_error)
        self.assertFalse(streamer.position_lost)     # Hold:0 reçu : arrêt complet avant le reset
        self.assertEqual(results, [False])
        self.assertTrue(any("error:1" in line for line in logs))

    def test_reset_without_confirmed_stop_marks_position_lost(self):
        ser = FakeGrbl(errors={"BAD LINE": "error:1"}, hold_state="Hold:1")   # jamais à l'arrêt complet
        streamer, _logs, results = self.run_stream(ser)
        self.assertEqual(ser.realtime(), [b"!", b"\x18"])
        self.assertTrue(streamer.position_lost)
        self.assertEqual(results, [False])

    def test_alarm_also_resets_and_marks_position_lost(self):
        ser = FakeGrbl(errors={"G1 X10 F1000": "ALARM:2"}, hold_state="Alarm")
        streamer, _logs, results = self.run_stream(ser)
        self.assertEqual(ser.realtime()[-1], b"\x18")
        self.assertTrue(streamer.position_lost)
        self.assertEqual(results, [False])

    def test_clean_job_sends_no_stop(self):
        ser = FakeGrbl()
        streamer, _logs, results = self.run_stream(ser, "G21\nG90\nG1 X10 F1000\nM5\n")
        self.assertEqual(ser.realtime(), [])
        self.assertFalse(streamer.stopped_on_error)
        self.assertEqual(results, [True])


if __name__ == "__main__":
    unittest.main()
