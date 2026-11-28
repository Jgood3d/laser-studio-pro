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


@unittest.skipIf(SettingsWindow is None, "PyQt6 non importable ici")
class SettingsCategoriesTests(unittest.TestCase):
    """Fenêtre « Paramètres » : liste des catégories à gauche, page choisie à droite."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        memory_preferences(self)

    def test_the_list_chooses_the_page_and_the_window_scrolls_only_once(self):
        from laser_studio.ui.settings.categories import SettingsCategories
        machine, grbl = wide_page(100), wide_page(100)
        categories = SettingsCategories([("machine_params", "Graveur", machine), ("grbl", "GRBL", grbl)])
        window = SettingsWindow(None, "Paramètres", categories, "settings")
        self.addCleanup(window.deleteLater)
        self.assertIs(window.scroll, categories)                     # pas de zone défilante autour de la liste
        categories.show_page("grbl")
        self.assertIs(categories.stack.currentWidget().widget(), grbl)
        self.assertEqual(categories.list.currentRow(), 1)
        categories.list.setCurrentRow(0)
        self.assertIs(categories.stack.currentWidget().widget(), machine)


@unittest.skipIf(SettingsWindow is None, "PyQt6 non importable ici")
class AppearancePageTests(unittest.TestCase):
    """Page « Langue et thème » : les listes déclenchent les actions de langue et de thème, et suivent leur coche."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_choosing_a_theme_triggers_its_action_and_the_list_follows_the_checked_one(self):
        from PyQt6.QtGui import QAction
        from laser_studio.ui.settings.appearance import AppearancePage
        def actions(codes, checked):
            made = {}
            for code in codes:
                made[code] = QAction(code)
                made[code].setCheckable(True)
                made[code].setChecked(code == checked)
            return made
        languages, themes = actions(("fr", "en"), "fr"), actions(("dark", "new_dusk"), "dark")
        page = AppearancePage(languages, themes)
        self.addCleanup(page.deleteLater)
        self.assertEqual((page.language.currentData(), page.theme.currentData()), ("fr", "dark"))
        triggered = []
        themes["new_dusk"].triggered.connect(lambda: triggered.append("new_dusk"))
        page.theme.activated.emit(1)                                # l'utilisateur choisit New Dusk
        self.assertEqual(triggered, ["new_dusk"])
        for code, action in themes.items():                         # le contrôleur coche le seul thème choisi
            action.setChecked(code == "new_dusk")
        self.assertEqual(page.theme.currentData(), "new_dusk")
        for code, action in themes.items():                         # puis revient au thème sombre
            action.setChecked(code == "dark")
        self.assertEqual(page.theme.currentData(), "dark")


if __name__ == "__main__":
    unittest.main()
