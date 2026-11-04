"""Écran de démarrage (StartupSplash) : affichage réel avant de poursuivre,
messages, et fenêtre principale montrée seulement une fois la durée minimale
écoulée."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtGui import QPixmap
    from splash_screen import StartupSplash
except ImportError:  # PyQt6 manquant
    StartupSplash = None


class FakeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.shown_at = None

    def showMaximized(self):
        self.shown_at = time.monotonic()
        super().show()


@unittest.skipIf(StartupSplash is None, "PyQt6 non importable ici")
class StartupSplashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, min_duration_s):
        pixmap = QPixmap(60, 30)
        splash = StartupSplash(pixmap, min_duration_s)
        self.addCleanup(splash.close)
        return splash

    def wait_until(self, condition, timeout_s=3.0):
        deadline = time.monotonic() + timeout_s
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

    def test_show_now_never_blocks_the_start(self):
        # Ni l'attente interne de QSplashScreen (1 s, toujours vaine sous
        # Wayland), ni la nôtre au-delà de timeout_s. Hors écran (tests), Qt
        # ne signale jamais la fenêtre comme exposée : l'attente va jusqu'au
        # délai ; à l'écran, elle s'arrête dès l'affichage réel (≈ 0,02 s
        # sous Wayland).
        splash = self.make(0.0)
        start = time.monotonic()
        splash.show_now(timeout_s=0.2)
        self.assertTrue(splash.isVisible())
        self.assertLess(time.monotonic() - start, 0.5)

    def test_status_message(self):
        splash = self.make(0.0)
        splash.show_now(timeout_s=0.05)
        splash.set_status("Prêt !")
        self.assertEqual(splash.message(), "Prêt !")

    def test_remaining_time(self):
        splash = self.make(5.0)
        # Pas encore affiché : rien à attendre.
        self.assertEqual(splash.remaining_s(), 0.0)
        splash.show_now(timeout_s=0.05)
        self.assertGreater(splash.remaining_s(), 4.5)
        self.assertLessEqual(splash.remaining_s(), 5.0)

    def test_window_waits_for_the_minimum_duration(self):
        splash = self.make(0.3)
        splash.show_now(timeout_s=0.05)
        window = FakeWindow()
        self.addCleanup(window.close)
        splash.finish_with(window)
        self.app.processEvents()
        self.assertIsNone(window.shown_at)  # pas tout de suite
        self.wait_until(lambda: window.shown_at is not None)
        self.assertIsNotNone(window.shown_at)
        self.assertGreaterEqual(window.shown_at - splash._shown_at, 0.29)
        self.wait_until(lambda: not splash.isVisible())
        # Le splash est fermé avec l'apparition de la fenêtre.
        self.assertFalse(splash.isVisible())

    def test_elapsed_duration_shows_the_window_at_once(self):
        splash = self.make(0.0)
        splash.show_now(timeout_s=0.05)
        window = FakeWindow()
        self.addCleanup(window.close)
        splash.finish_with(window)
        self.wait_until(lambda: window.shown_at is not None, timeout_s=0.5)
        self.assertIsNotNone(window.shown_at)


if __name__ == "__main__":
    unittest.main()
