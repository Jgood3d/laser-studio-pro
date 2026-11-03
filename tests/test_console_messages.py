"""Envoi au laser : les messages de l'application mêlés au G-Code dans la console (connexion, mode
laser…) ne sont pas envoyés à GRBL, qui les refuserait (error:1) et interromprait la gravure."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import workers
except ImportError:  # PyQt6/svg.path manquants
    workers = None


@unittest.skipIf(workers is None, "workers.py non importable ici")
class ConsoleMessagesTests(unittest.TestCase):
    def test_application_messages_are_not_sent(self):
        console = "\n".join([
            "G21", "G90", "M4 S0", "G1 X52.500 Y90.000 F1500 S800", "M5 ; Extinction Laser",
            "G0 X0 Y0 ; Retour origine", "; ----- commentaire -----",
            "Connecté à SIMULATION avec succès.", ">>> Mode laser GRBL ($32) : 1",
            "Image chargée : /tmp/medaille.png", "",
        ])
        self.assertEqual(workers.gcode_lines(console), [
            "G21", "G90", "M4 S0", "G1 X52.500 Y90.000 F1500 S800", "M5 ; Extinction Laser",
            "G0 X0 Y0 ; Retour origine",
        ])

    def test_grbl_commands_are_kept(self):
        for line in ("$H", "$X", "$32=1", "g1 x1 y2", "G1X-1.5", "X10 Y10", "S1000", "F3000",
                     "(commentaire GRBL)", "%", "?", "!", "~", "N10 G1 X1", "  G0 X1  "):
            self.assertEqual(workers.gcode_lines(line), [line.strip()], line)

    def test_streamer_uses_the_filtered_lines(self):
        streamer = workers.GCodeStreamerThread(None, "G1 X1\nConnecté à COM3 avec succès.\nM5")
        self.assertEqual(streamer.lines, ["G1 X1", "M5"])


if __name__ == "__main__":
    unittest.main()
