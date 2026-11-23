"""Polices des modèles de la bibliothèque : embarquées (resources/fonts/) avec leur licence, ou fournies
par le système (paquet Fedora, qui retire les copies embarquées au profit des paquets de polices)."""
import glob
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
FONTS = os.path.join(REPO, "src", "laser_studio", "resources", "fonts")
LIBRARY = os.path.join(REPO, "src", "laser_studio", "resources", "library")
# Polices courantes que les modèles peuvent citer sans les embarquer : Arial est présente sous Windows et
# macOS, et remplacée sous Linux par Liberation Sans, aux mêmes dimensions.
STANDARD_FONTS = {"Arial"}

try:
    from PyQt6.QtGui import QFont, QFontInfo
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.fonts import SCRIPT_FONT, bundled_font_files, load_bundled_fonts
except ImportError:  # PyQt6 manquant
    load_bundled_fonts = None


def library_font_families():
    """Familles de polices citées par les textes des modèles de la bibliothèque."""
    families = set()
    for path in glob.glob(os.path.join(LIBRARY, "**", "*.svg"), recursive=True):
        with open(path, encoding="utf-8") as f:
            for family in re.findall(r"font-family:\s*([^;\"]+)", f.read()):
                families.add(family.split(",")[0].strip().strip("'\""))
    return families


@unittest.skipIf(load_bundled_fonts is None, "PyQt6 non importable ici")
class BundledFontsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.bundled = load_bundled_fonts()

    def assert_available(self, family, bold=False):
        """La police est trouvée telle quelle (embarquée, ou installée sur le système) : sans elle, la
        police de remplacement, plus large, fait déborder les textes des modèles."""
        if os.path.isdir(FONTS):
            self.assertIn(family, self.bundled)
        font = QFont(family)
        font.setBold(bold)
        self.assertEqual(QFontInfo(font).family(), family)

    def test_script_font_is_available_everywhere(self):
        """Dancing Script (boule de Noël prénom)."""
        self.assert_available(SCRIPT_FONT)

    def test_title_font_is_available_everywhere(self):
        """Rubik en gras (médailles et totems sportifs)."""
        self.assert_available("Rubik", bold=True)

    def test_library_uses_only_available_fonts(self):
        """Un modèle ne cite qu'une police embarquée ou une police courante (STANDARD_FONTS)."""
        self.assertEqual(library_font_families() - STANDARD_FONTS, {SCRIPT_FONT, "Rubik"})

    def test_every_font_has_its_license(self):
        if not os.path.isdir(FONTS):
            self.skipTest("polices embarquées retirées (paquet Fedora : polices du système)")
        self.assertTrue(bundled_font_files())
        licenses = [f for f in os.listdir(FONTS) if f.upper().startswith(("OFL", "LICEN"))]
        self.assertTrue(licenses)

    def test_startup_loads_the_fonts(self):
        with open(os.path.join(REPO, "src", "laser_studio", "main.py"), encoding="utf-8") as f:
            self.assertIn("load_bundled_fonts()", f.read())


if __name__ == "__main__":
    unittest.main()
