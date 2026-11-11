"""Écran de démarrage (StartupSplash) : affichage réel avant de poursuivre,
messages, et fenêtre principale montrée seulement une fois la durée minimale
écoulée."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap
    from laser_studio.ui.splashscreen import StartupSplash
    from laser_studio.core.constants import SPLASH_SCREEN_WIDTH
    from laser_studio.i18n import tr
except ImportError:  # PyQt6 manquant
    StartupSplash = None


@unittest.skipIf(StartupSplash is None, "PyQt6 non importable ici")
class StartupSplashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        pixmap = QPixmap(60, 30)
        splash = StartupSplash(pixmap)
        self.addCleanup(splash.close)
        return splash

    def test_show_and_wait_never_blocks_the_start(self):
        # Ni l'attente interne de QSplashScreen (1 s, toujours vaine sous
        # Wayland), ni la nôtre au-delà de timeout_s. Hors écran (tests), Qt
        # ne signale jamais la fenêtre comme exposée : l'attente va jusqu'au
        # délai ; à l'écran, elle s'arrête dès l'affichage réel (≈ 0,02 s
        # sous Wayland).
        splash = self.make()
        start = time.monotonic()
        splash.show_and_wait(timeout_s=0.2)
        self.assertTrue(splash.isVisible())
        self.assertLess(time.monotonic() - start, 0.5)

    def test_default_banner_is_the_application_banner(self):
        # Sans pixmap : la bannière du projet, large de SPLASH_SCREEN_WIDTH.
        splash = StartupSplash()
        self.addCleanup(splash.close)
        pixmap = splash.pixmap()
        logical_width = pixmap.width() / pixmap.devicePixelRatio()
        self.assertEqual(round(logical_width), SPLASH_SCREEN_WIDTH)

    def test_missing_banner_is_replaced_by_a_grey_rectangle(self):
        from unittest import mock
        with mock.patch("laser_studio.ui.splashscreen.splash.find_resource", return_value=None):
            pixmap = StartupSplash.banner()
        self.assertEqual((pixmap.width(), pixmap.height()), (500, 250))

    def test_default_message(self):
        # Sans appel à show_progress() : message d'accueil traduit.
        splash = self.make()
        self.assertEqual(splash.message(), tr("splash.initializing"))

    def test_progress_message(self):
        splash = self.make()
        splash.show_and_wait(timeout_s=0.05)
        splash.show_progress("Prêt !")
        self.assertEqual(splash.message(), "Prêt !")

if __name__ == "__main__":
    unittest.main()
