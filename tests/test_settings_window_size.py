"""Fenêtre de réglages (SettingsWindow) : assez large pour toute la page."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from job_fakes import memory_preferences
    from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget
    from laser_studio.ui.settings.window import SettingsWindow
except ImportError:  # PyQt6 manquant
    SettingsWindow = None


def wide_page(width):
    page = QWidget()
    layout = QHBoxLayout(page)
    label = QLabel("x")
    label.setMinimumWidth(width)
    layout.addWidget(label)
    return page


@unittest.skipIf(SettingsWindow is None, "PyQt6 non importable ici")
class SettingsWindowSizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        memory_preferences(self)                 # rien d'écrit dans les vrais réglages

    def make(self, page):
        window = SettingsWindow(None, "Test", page, "test")
        self.addCleanup(window.deleteLater)
        return window

    # Sans écran, Qt simule un écran de 800 px : la fenêtre est limitée à
    # 90 % de sa largeur, d'où une page de 600 px.
    def test_a_wide_page_widens_the_window(self):
        window = self.make(wide_page(600))
        window.show()
        self.app.processEvents()
        self.assertGreater(window.width(), 600)
        self.assertFalse(window.scroll.horizontalScrollBar().isVisible())

    def test_a_narrow_page_keeps_the_default_width(self):
        self.assertEqual(self.make(wide_page(100)).width(), 560)

    def test_a_saved_width_that_is_too_narrow_is_widened(self):
        window = self.make(wide_page(600))
        window.resize(400, 500)
        window.close()  # mémorise 400 px
        again = self.make(wide_page(600))
        self.assertGreater(again.width(), 600)


if __name__ == "__main__":
    unittest.main()
