"""Barre d'état (StatusBar) : messages d'information et progression."""
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtWidgets import QApplication
    from ui.statusbar import StatusBar
except ImportError:  # PyQt6 manquant
    StatusBar = None


@unittest.skipIf(StatusBar is None, "PyQt6 non importable ici")
class StatusBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        status_bar = StatusBar()
        self.addCleanup(status_bar.deleteLater)
        return status_bar

    def wait(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.01)

    def test_progress_is_hidden_after_the_delay(self):
        status_bar = self.make()
        status_bar.show_progress(100, "Terminé")
        status_bar.hide_progress(delay_ms=50)
        self.assertFalse(status_bar.progress_bar.isHidden())   # pas tout de suite
        self.wait(0.2)
        self.assertTrue(status_bar.progress_bar.isHidden())
        self.assertEqual(status_bar.progress_label.text(), "")

    def test_new_progress_cancels_a_pending_hide(self):
        # Une génération relancée pendant le délai ne doit pas être masquée
        # par la fin de la précédente.
        status_bar = self.make()
        status_bar.show_progress(100, "Terminé")
        status_bar.hide_progress(delay_ms=50)
        status_bar.show_progress(10, "Génération en cours… 10%")
        self.wait(0.2)
        self.assertFalse(status_bar.progress_bar.isHidden())
        self.assertEqual(status_bar.progress_bar.value(), 10)
        self.assertEqual(status_bar.progress_label.text(), "Génération en cours… 10%")

    def test_immediate_hide(self):
        status_bar = self.make()
        status_bar.show_progress(30, "En cours")
        status_bar.hide_progress()
        self.assertTrue(status_bar.progress_bar.isHidden())


if __name__ == "__main__":
    unittest.main()
