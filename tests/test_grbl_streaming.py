"""Protocole d'envoi à GRBL sans Qt ni port série (grbl/streaming.py) : lignes envoyables, comptage des
octets du tampon de 127 octets, « ok » et classement des réponses."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.grbl.streaming import (  # noqa: E402
    EMPTY, ERROR, OK, OTHER, STATUS, CharacterCountingStream, classify, gcode_lines,
)


class GcodeLinesTests(unittest.TestCase):
    def test_application_messages_and_comments_are_dropped(self):
        text = "; titre\nConnecté à /dev/ttyUSB0\n  G1 X1 \n>>> Mode laser\n$H\n(note)\n%\n\n?\nM5"
        self.assertEqual(gcode_lines(text), ["G1 X1", "$H", "(note)", "%", "?", "M5"])


class ClassifyTests(unittest.TestCase):
    def test_responses(self):
        cases = {"": EMPTY, "ok": OK, "error:22": ERROR, "ALARM:1": ERROR, "ERROR:5": ERROR,
                 "<Idle|MPos:0,0,0>": STATUS, "[MSG:Caution]": OTHER, "Grbl 1.1h": OTHER}
        for response, kind in cases.items():
            self.assertEqual(classify(response), kind, response)


class CharacterCountingTests(unittest.TestCase):
    def send_all_possible(self, stream):
        sent = []
        while (data := stream.next_to_send()) is not None:
            sent.append(data)
            stream.mark_sent()
        return sent

    def test_lines_are_sent_while_they_fit_in_the_buffer(self):
        stream = CharacterCountingStream(["G1X10"] * 30, buffer_size=20)    # 6 octets par ligne
        self.assertEqual(len(self.send_all_possible(stream)), 3)            # 18 < 20 ; 24 ne tient plus
        self.assertEqual((stream.pending, stream.occupancy), (3, 18))
        self.assertTrue(stream.acknowledge())
        self.assertEqual(len(self.send_all_possible(stream)), 1)
        self.assertEqual((stream.acked, stream.next_index, stream.first_pending), (1, 4, "G1X10"))

    def test_spaces_and_end_comments_are_not_sent(self):
        """GRBL les retire lui-même : moins d'octets sur la liaison série, mais les lignes gardées (console,
        suivi de la gravure) restent lisibles."""
        stream = CharacterCountingStream(["G1 X12.5 S300 ; OVERSCAN_END", "G0 X1 (repère)"])
        self.assertEqual(self.send_all_possible(stream), [b"G1X12.5S300\n", b"G0 X1 (rep\xc3\xa8re)\n"])
        self.assertEqual(stream.first_pending, "G1 X12.5 S300 ; OVERSCAN_END")
        self.assertEqual(stream.occupancy, len(b"G1X12.5S300\n") + len("G0 X1 (repère)\n".encode()))

    def test_a_line_longer_than_the_buffer_goes_alone(self):
        stream = CharacterCountingStream(["G1 " + "X1" * 80, "M5"], buffer_size=127)
        self.assertEqual(len(self.send_all_possible(stream)), 1)
        stream.acknowledge()
        self.assertEqual(self.send_all_possible(stream), [b"M5\n"])
        self.assertTrue(stream.all_sent)

    def test_unexpected_ok(self):
        stream = CharacterCountingStream([])
        self.assertFalse(stream.acknowledge())
        self.assertEqual((stream.acked, stream.next_to_send(), stream.first_pending), (0, None, None))



class ResumeTests(unittest.TestCase):
    """Reprise d'un job arrêté (resume_gcode) : état du G-Code au point de reprise, puis la suite."""

    JOB = "G21\nG90\nM4 S0\nF1500\nG0 X10 Y5\nG1 X20 S300\nG1 X25 S500\n; commentaire\nG1 Y8\nM5\nG0 X0 Y0\n"

    def test_resumes_with_the_state_of_the_stopped_line(self):
        from laser_studio.grbl.streaming import resume_gcode
        text, line, total = resume_gcode(self.JOB, 6, planner_blocks=0)
        self.assertEqual((line, total), (7, 10))                  # commentaire écarté, comme à l'envoi
        self.assertEqual(text.split("\n"), ["G21", "M5", "G90", "G0 X20.000 Y5.000", "M4 S300", "G1 F1500",
                                            "G1 X25 S500", "G1 Y8", "M5", "G0 X0 Y0"])

    def test_restarts_before_the_blocks_grbl_had_planned(self):
        # Les blocs acquittés mais encore dans le planificateur de GRBL sont perdus à l'arrêt.
        from laser_studio.grbl.streaming import resume_gcode
        self.assertEqual(resume_gcode(self.JOB, 9, planner_blocks=2)[1], 8)
        self.assertEqual(resume_gcode(self.JOB, 3)[1], 1)          # tout au début : le job entier
        self.assertIsNone(resume_gcode(self.JOB, 99, planner_blocks=0))

    def test_known_stop_position_resumes_on_the_stroke_in_progress(self):
        from laser_studio.grbl.streaming import resume_gcode
        job = "".join(f"G1 X{i} Y0 S100 F1000\n" for i in range(40))
        text, line, _total = resume_gcode(job, 30, head=(27.4, 0.0))
        self.assertEqual(line, 29)                                  # le trait X27 -> X28, en cours à l'arrêt
        self.assertEqual(text.split("\n")[3:6], ["G0 X27.400 Y0.000", "G1 F1000", "G1 X28 Y0 S100 F1000"])
        self.assertEqual(resume_gcode(job, 30, head=(27.4, 3.0))[1], 16)      # sur aucun trait : 15 lignes avant
        relative = "G91\n" + "G1 X1 S100 F1000\n" * 40
        self.assertEqual(resume_gcode(relative, 30, head=(27.4, 0.0))[1], 16)  # relatif : repli sûr

    def test_relative_moves_and_laser_off(self):
        from laser_studio.grbl.streaming import resume_gcode
        text = resume_gcode("G91\nG0 X5 Y5\nG1 X2 F800\nM5\nG1 X1\n", 4, planner_blocks=0)[0]
        self.assertEqual(text.split("\n"), ["G21", "M5", "G90", "G0 X7.000 Y5.000", "G91", "G1 F800", "G1 X1"])

if __name__ == "__main__":
    unittest.main()
