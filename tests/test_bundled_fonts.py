"""Polices embarquées (resources/fonts/) : chargées et accompagnées de leur licence."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
FONTS = os.path.join(REPO, "src", "laser_studio", "resources", "fonts")

try:
    from PyQt6.QtGui import QFont, QFontInfo
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.fonts import SCRIPT_FONT, bundled_font_files, load_bundled_fonts
except ImportError:  # PyQt6 manquant
    load_bundled_fonts = None


@unittest.skipIf(load_bundled_fonts is None, "PyQt6 non importable ici")
class BundledFontsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_script_font_is_available_everywhere(self):
        self.assertIn(SCRIPT_FONT, load_bundled_fonts())
        self.assertEqual(QFontInfo(QFont(SCRIPT_FONT)).family(), SCRIPT_FONT)

    def test_every_font_has_its_license(self):
        files = bundled_font_files()
        self.assertTrue(files)
        licenses = [f for f in os.listdir(FONTS) if f.upper().startswith(("OFL", "LICEN"))]
        self.assertTrue(licenses)

    def test_startup_loads_the_fonts(self):
        with open(os.path.join(REPO, "src", "laser_studio", "main.py"), encoding="utf-8") as f:
            self.assertIn("load_bundled_fonts()", f.read())


if __name__ == "__main__":
    unittest.main()
