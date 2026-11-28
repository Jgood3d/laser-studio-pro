"""Thèmes (ui/app/theme.py) : les quatre thèmes gardés, anciens noms ramenés au plus proche, icônes d'une seule
couleur des thèmes modernes."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from laser_studio.i18n import TRANSLATIONS
    from laser_studio.ui.app.theme import (DEFAULT_THEME, THEMES, available_themes, has_mono_drawing, monochrome_svg,
                                           normalize_theme_name)
except ImportError:          # PyQt6 absent
    THEMES = None


@unittest.skipIf(THEMES is None, "PyQt6 non importable ici")
class ThemeChoiceTests(unittest.TestCase):
    def test_four_themes_dark_by_default(self):
        self.assertEqual([code for code, _key in available_themes()], ["new_dusk", "new_dusk_petrol", "new_dawn", "jarvis"])
        self.assertEqual(DEFAULT_THEME, "new_dusk")
        self.assertEqual(TRANSLATIONS["theme.new_dusk"]["fr"], "Sombre")
        self.assertEqual(TRANSLATIONS["theme.new_dawn"]["fr"], "Clair")
        self.assertEqual((normalize_theme_name(None), normalize_theme_name("inconnu")), ("new_dusk", "new_dusk"))

    def test_removed_themes_fall_back_to_the_closest(self):
        # Un thème retiré, encore enregistré dans les préférences, donne le plus proche au lancement.
        for old in ("dark", "dusk", "warm", "neon", "retro80", "Sombre"):
            self.assertEqual(normalize_theme_name(old), "new_dusk", old)
        for old in ("light", "Clair"):
            self.assertEqual(normalize_theme_name(old), "new_dawn", old)
        self.assertEqual(normalize_theme_name("jarvis"), "jarvis")


@unittest.skipIf(THEMES is None, "PyQt6 non importable ici")
class MonochromeIconTests(unittest.TestCase):

    def test_every_color_of_the_icon_takes_the_theme_color(self):
        svg = ('<svg><style>.ColorScheme-Text { color:#232629; } .ColorScheme-NegativeText { color:#da4453; }</style>'
               '<path fill="#fcfcfc"/><path style="fill:#3daee9"/><path fill="#fff"/></svg>')
        mono = monochrome_svg("edit-delete", svg, "#cdd8da")
        self.assertEqual(set(re.findall(r"#[0-9a-fA-F]{3,6}\b", mono)), {"#cdd8da"})

    def test_icons_with_several_hues_are_redrawn(self):
        # La roue chromatique d'une seule couleur ne serait qu'un disque : dessin au trait à la place.
        self.assertTrue(has_mono_drawing("color-management"))
        mono = monochrome_svg("color-management", "<svg><circle fill='#ff0000'/></svg>", "#cdd8da")
        self.assertNotIn("#ff0000", mono)
        self.assertEqual(mono.count("<circle"), 3)

    def test_only_the_new_themes_have_monochrome_icons(self):
        self.assertEqual([name for name, colors in THEMES.items() if colors.get("mono_icons")],
                         ["new_dusk", "new_dusk_petrol", "new_dawn"])

    def test_new_dawn_defines_every_colour_of_new_dusk(self):
        # Même jeu de couleurs : la feuille moderne et les zones de dessin n'en manquent aucune.
        for name in ("new_dusk_petrol", "new_dawn"):
            self.assertLessEqual(set(THEMES["new_dusk"]) - {"label_key"}, set(THEMES[name]), name)
        self.assertLessEqual(set(THEMES["new_dusk_petrol"]) - {"label_key"}, set(THEMES["new_dusk"]))



@unittest.skipIf(THEMES is None, "PyQt6 non importable ici")
class LiveIconTests(unittest.TestCase):
    """Les icônes recolorées suivent un changement de thème à chaud (sinon claires sur fond clair)."""

    def test_icon_follows_the_application_palette(self):
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QColor, QPalette
        from PyQt6.QtWidgets import QApplication
        from laser_studio.ui.utils import palette_icon
        app = QApplication.instance() or QApplication([])
        saved = app.palette()
        self.addCleanup(app.setPalette, saved)
        icon = palette_icon("edit-undo", saved)

        def darkest(color):
            palette = QPalette(saved)
            palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
            app.setPalette(palette)
            image = icon.pixmap(QSize(22, 22)).toImage()
            return min(image.pixelColor(x, y).lightness() for x in range(22) for y in range(22)
                       if image.pixelColor(x, y).alpha() > 200)

        self.assertLess(darkest("#202020"), 60)                   # thème clair : icône sombre
        self.assertGreater(darkest("#f0f0f0"), 180)               # thème sombre : la même icône, claire


if __name__ == "__main__":
    unittest.main()
