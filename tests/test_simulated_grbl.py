"""Graveur GRBL simulé (variable LASER_STUDIO_SIMULATION) : protocole, mouvements, temps réel, intégration."""
import os
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simulated_grbl as sim
from simulated_grbl import SimulatedGrblSerial


def lines(ser):
    out = []
    while ser.in_waiting:
        out.append(ser.readline().decode().strip())
    return out


def send(ser, text):
    ser.write((text + "\n").encode())


def wait_state(ser, state, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ser.write(b"?")
        reports = [l for l in lines(ser) if l.startswith("<")]
        if reports and reports[-1].startswith(f"<{state}"):
            return reports[-1]
        time.sleep(0.01)
    raise AssertionError(f"état {state} jamais atteint")


class SimulatedGrblTests(unittest.TestCase):
    def make(self, speed=50.0):
        ser = SimulatedGrblSerial(speed=speed)
        self.assertEqual(lines(ser), [sim.WELCOME])
        return ser

    def test_env_variable(self):
        for value, speed in (("", None), ("0", None), ("1", 1.0), ("20", 20.0), ("oui", 1.0)):
            with mock.patch.dict(os.environ, {"LASER_STUDIO_SIMULATION": value}):
                self.assertEqual(sim.simulation_speed(), speed, value)

    def test_settings_and_status(self):
        ser = self.make()
        send(ser, "$$")
        out = lines(ser)
        self.assertIn("$32=1", out)
        self.assertIn("$22=1", out)
        self.assertEqual(out[-1], "ok")
        send(ser, "$22=0")
        send(ser, "$H")
        self.assertEqual(lines(ser), ["ok", "error:5"])     # homing désactivé
        ser.write(b"?")
        self.assertTrue(lines(ser)[0].startswith("<Idle|MPos:0.000,0.000,0.000"))

    def test_motion_takes_time_and_reaches_target(self):
        ser = self.make(speed=20.0)
        send(ser, "G21 G90")
        send(ser, "G1 X10 Y0 F600 ; 1 s de mouvement")    # 10 mm à 10 mm/s, /20 = 0,05 s
        self.assertEqual(lines(ser), ["ok", "ok"])
        self.assertTrue(wait_state(ser, "Run").startswith("<Run"))
        report = wait_state(ser, "Idle")
        self.assertIn("MPos:10.000,0.000,0.000", report)

    def test_garbage_line_is_an_error(self):
        ser = self.make()
        send(ser, "Connecté au port /dev/ttyUSB0")
        self.assertEqual(lines(ser), ["error:1"])

    def test_feed_hold_resume_and_reset_in_motion(self):
        ser = self.make(speed=1.0)
        send(ser, "G1 X100 F600")                          # 10 s de mouvement
        lines(ser)
        ser.write(b"!")
        time.sleep(0.15)
        self.assertTrue(wait_state(ser, "Hold:0").startswith("<Hold:0"))
        ser.write(b"~")
        wait_state(ser, "Run")
        ser.write(b"\x18")                                 # reset en mouvement
        out = lines(ser)
        self.assertEqual(out[:2], ["ALARM:3", sim.WELCOME])
        send(ser, "G0 X0")
        self.assertEqual(lines(ser), ["error:9"])          # verrouillé
        send(ser, "$X")
        self.assertEqual(lines(ser)[-1], "ok")

    def test_homing_acknowledges_at_the_end(self):
        ser = self.make(speed=40.0)                        # 2 s de homing -> 0,05 s
        send(ser, "G0 X5")
        lines(ser)
        send(ser, "$H")
        self.assertEqual(lines(ser), [])                   # pas de « ok » avant la fin du cycle
        time.sleep(0.2)
        self.assertEqual(lines(ser), ["ok"])
        ser.write(b"?")
        self.assertIn("MPos:0.000,0.000,0.000", lines(ser)[0])

    def test_planner_full_delays_ok(self):
        ser = self.make(speed=1.0)
        for i in range(20):
            send(ser, f"G1 X{i + 1} F60")                  # 1 s par mouvement
        self.assertEqual(lines(ser).count("ok"), sim.PLANNER_SIZE)


try:
    from workers import GCodeStreamerThread
except ImportError:
    GCodeStreamerThread = None


@unittest.skipIf(GCodeStreamerThread is None, "workers non importable ici")
class StreamerWithSimulationTests(unittest.TestCase):
    def test_a_whole_job_streams_to_the_end(self):
        from usb_controller import LaserUSBController
        with mock.patch.dict(os.environ, {"LASER_STUDIO_SIMULATION": "500"}):
            usb = LaserUSBController()
            self.assertTrue(usb.connect(sim.SIMULATED_PORT))
        gcode = "G21\nG90\nM4 S0\n" + "\n".join(
            f"G1 X{(i % 50) * 0.5:.1f} Y{i * 0.1:.1f} S{(i * 7) % 1000} F3000" for i in range(300)) + "\nM5\n"
        streamer = GCodeStreamerThread(usb, gcode)
        results, batches = [], []
        streamer.finished_signal.connect(results.append)
        streamer.lines_sent.connect(batches.append)
        acked = []
        streamer.lines_acked.connect(acked.append)
        streamer.run()
        self.assertEqual(results, [True])
        self.assertEqual(usb.last_state, "Idle")
        # Suivi de l'envoi (onglet File d'attente) : toutes les lignes, dans l'ordre, par paquets.
        self.assertEqual([line for batch in batches for line in batch], streamer.lines)
        self.assertLess(len(batches), len(streamer.lines))
        # Lignes acceptées par GRBL (suivi de la gravure sur l'aperçu 2D) : croissant, jusqu'au total.
        self.assertEqual(acked, sorted(acked))
        self.assertEqual(acked[-1], len(streamer.lines))


if __name__ == "__main__":
    unittest.main()
