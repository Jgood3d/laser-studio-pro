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


if __name__ == "__main__":
    unittest.main()
