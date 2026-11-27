"""Compte à rebours avant la gravure : sons fabriqués, fenêtre (fin, annulation, un « tic » par seconde) et
lancement de la file d'attente."""
import io
import os
import sys
import unittest
import wave
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.core import sounds  # noqa: E402

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QDialog
    from laser_studio.ui.dialogs.countdown import CountdownDialog
except ImportError:  # PyQt6 manquant
    CountdownDialog = None


class SoundsTests(unittest.TestCase):
    def test_chime_is_a_soft_wav(self):
        with wave.open(io.BytesIO(sounds.chime((880.0,), 0.2)), "rb") as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, sounds.RATE))
            self.assertEqual(w.getnframes(), int(sounds.RATE * 0.2))
            frames = w.readframes(w.getnframes())
        samples = [int.from_bytes(frames[i:i + 2], "little", signed=True) for i in range(0, len(frames), 2)]
        self.assertEqual(samples[0], 0)                                  # attaque progressive : pas de clic
        self.assertLess(max(abs(s) for s in samples), 32767 * 0.4)        # volume modéré
        self.assertLess(abs(samples[-1]), max(abs(s) for s in samples) / 50)   # le son s'éteint

    def test_play_says_when_no_player_is_available(self):
        with mock.patch.object(sounds.sys, "platform", "linux"), \
                mock.patch.object(sounds.shutil, "which", return_value=None):
            self.assertFalse(sounds.play(sounds.TICK))                   # l'appelant fera un bip système
        with mock.patch.object(sounds.sys, "platform", "linux"), \
                mock.patch.object(sounds.shutil, "which", return_value="/usr/bin/aplay"), \
                mock.patch.object(sounds.subprocess, "Popen") as popen:
            self.assertTrue(sounds.play(sounds.GO))
        self.assertEqual(popen.call_args[0][0][-1], sounds.sound_file(sounds.GO))


@unittest.skipIf(CountdownDialog is None, "PyQt6 non importable ici")
class CountdownDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_ticks_every_second_then_starts(self):
        played = []
        dialog = CountdownDialog(2, play=lambda name: played.append(name) or True)
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.exec(), QDialog.DialogCode.Accepted)
        self.assertEqual(played, [sounds.TICK, sounds.TICK, sounds.GO])

    def test_cancel_stops_everything(self):
        played = []
        dialog = CountdownDialog(5, play=lambda name: played.append(name) or True)
        self.addCleanup(dialog.deleteLater)
        QTimer.singleShot(300, dialog.reject)                            # Annuler (ou Échap)
        self.assertEqual(dialog.exec(), QDialog.DialogCode.Rejected)
        self.assertEqual(played, [sounds.TICK])                          # pas de son de départ

    def test_system_beep_without_audio_player(self):
        dialog = CountdownDialog(1, play=lambda name: False)
        self.addCleanup(dialog.deleteLater)
        with mock.patch.object(QApplication, "beep") as beep:
            dialog.exec()
        self.assertEqual(beep.call_count, 2)                             # le « tic » et le départ


class QueueCountdownTests(unittest.TestCase):
    def test_cancelled_countdown_does_not_start_the_queue(self):
        try:
            from laser_studio.controllers import job_queue
        except ImportError:
            self.skipTest("controllers.job_queue non importable ici")
        src = open(job_queue.__file__, encoding="utf-8").read()
        start = src[src.index('log.info("File : annulée à la confirmation")'):src.index("self._run_next()")]
        self.assertIn("if not engraver.countdown():", start)            # après la confirmation, avant le 1er job


if __name__ == "__main__":
    unittest.main()
