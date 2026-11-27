"""Accessibilité des thèmes : textes assez contrastés (WCAG AA) et focus clavier toujours visible."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QLineEdit, QPushButton, QRadioButton, QSlider,
                                 QTabBar, QToolButton, QVBoxLayout, QWidget)
    from laser_studio.ui.app.theme import THEMES, apply_app_theme, contrast_ratio, focus_color
except ImportError:  # PyQt6 manquant
    THEMES = None

BACKGROUNDS = ("window", "base", "group_bg", "toolbar_bg", "tab_bg", "alt")


@unittest.skipIf(THEMES is None, "PyQt6 non importable ici")
class ContrastTests(unittest.TestCase):
    def test_reference_values(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast_ratio("#777777", "#777777"), 1.0)

    def test_texts_are_readable_in_every_theme(self):
        # Texte et texte secondaire (titres des cadres, onglets inactifs, barre d'état, en-têtes) : 4,5 au moins.
        for name, c in THEMES.items():
            for role in ("text", "muted"):
                for background in BACKGROUNDS:
                    with self.subTest(theme=name, role=role, background=background):
                        self.assertGreaterEqual(contrast_ratio(c[role], c[background]), 4.5)

    def test_focus_outline_stands_out(self):
        for name, c in THEMES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast_ratio(focus_color(c), c["window"]), 3.0)


@unittest.skipIf(THEMES is None, "PyQt6 non importable ici")
class KeyboardFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.saved_style = cls.app.styleSheet()

    @classmethod
    def tearDownClass(cls):
        cls.app.setStyleSheet(cls.saved_style)

    def test_focused_widget_is_visible_in_every_theme(self):
        # Rendu du widget avec et sans le focus clavier : il doit changer (le cadre de focus avait été retiré).
        for theme in THEMES:
            apply_app_theme(self.app, theme)
            window = QWidget()
            self.addCleanup(window.deleteLater)
            layout = QVBoxLayout(window)
            tabs = QTabBar()
            tabs.addTab("Un")
            tabs.addTab("Deux")
            tool = QToolButton()
            tool.setText("Outil")
            combo = QComboBox()
            combo.addItem("a")
            widgets = [tabs, QPushButton("Bouton"), tool, QCheckBox("Case"), QRadioButton("Radio"),
                       QSlider(Qt.Orientation.Horizontal), QLineEdit("texte"), combo]
            other = QLineEdit()
            for widget in widgets + [other]:
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                layout.addWidget(widget)
            window.show()
            self.app.processEvents()
            for widget in widgets:
                other.setFocus(Qt.FocusReason.TabFocusReason)
                self.app.processEvents()
                before = widget.grab().toImage()
                widget.setFocus(Qt.FocusReason.TabFocusReason)
                self.app.processEvents()
                if not widget.hasFocus():                      # plateforme sans gestion du focus
                    self.skipTest("focus clavier indisponible ici")
                with self.subTest(theme=theme, widget=type(widget).__name__):
                    self.assertNotEqual(widget.grab().toImage(), before)
            window.close()


if __name__ == "__main__":
    unittest.main()
