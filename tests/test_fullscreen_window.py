"""Fenêtre « Plein écran » (FullscreenWindow) : accueille puis rend le contenu."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
    from ui.widgets import FullscreenWindow
except ImportError:  # PyQt6 manquant
    FullscreenWindow = None


@unittest.skipIf(FullscreenWindow is None, "PyQt6 non importable ici")
class FullscreenWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        content = QLabel("contenu")
        window = FullscreenWindow(None, content, "Titre", "Fermer")
        self.addCleanup(window.deleteLater)
        return window, content

    def test_content_is_hosted_under_the_close_button(self):
        window, content = self.make()
        self.assertEqual(window.windowTitle(), "Titre")
        self.assertIs(content.parent(), window)
        button = window.findChildren(QPushButton)[0]
        self.assertEqual(button.text(), "Fermer")
        self.assertTrue(window.windowFlags() & Qt.WindowType.Window)

    def test_closing_releases_the_content(self):
        window, content = self.make()
        released = []
        window.content_released.connect(lambda: released.append(True))
        window.show_maximized()
        window.findChildren(QPushButton)[0].click()
        self.assertEqual(released, [True])
        self.assertIsNone(content.parent())


if __name__ == "__main__":
    unittest.main()
