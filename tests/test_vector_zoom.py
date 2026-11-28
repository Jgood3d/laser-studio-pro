"""Zoom de l'éditeur vectoriel : loupes + et - de la barre d'édition, Ctrl++ et Ctrl+-."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

try:
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtWidgets import QApplication
    from laser_studio.i18n import TRANSLATIONS
    from laser_studio.models.layers import LayersModel
    from laser_studio.ui.vector_editor import navigation as canvas_mod
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
except ImportError:  # PyQt6 manquant
    VectorCanvasView = None

CTRL = None if VectorCanvasView is None else Qt.KeyboardModifier.ControlModifier


@unittest.skipIf(VectorCanvasView is None, "PyQt6 non importable ici")
class ZoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.canvas = VectorCanvasView(LayersModel())
        self.canvas.resize(800, 600)
        self.canvas.set_work_area(300.0, 200.0)
        self.canvas.resetTransform()

    def tearDown(self):
        self.canvas.deleteLater()

    def scale(self):
        return self.canvas.transform().m11()

    def center(self):
        return self.canvas.mapToScene(self.canvas.viewport().rect().center())

    def press(self, key, modifiers=CTRL, text=""):
        self.canvas.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text))

    def test_buttons_zoom_in_and_out_around_the_middle(self):
        before = self.center()
        self.canvas.navigation.zoom_in()
        self.assertAlmostEqual(self.scale(), canvas_mod.BUTTON_ZOOM_STEP)
        self.assertLess((self.center() - before).manhattanLength(), 2.0)
        self.canvas.navigation.zoom_out()
        self.assertAlmostEqual(self.scale(), 1.0)

    def test_ctrl_plus_and_ctrl_minus(self):
        self.press(Qt.Key.Key_Plus, text="+")
        self.assertAlmostEqual(self.scale(), canvas_mod.BUTTON_ZOOM_STEP)
        self.press(Qt.Key.Key_Minus, text="-")
        self.assertAlmostEqual(self.scale(), 1.0)

    def test_ctrl_equal_and_keypad_also_zoom(self):
        self.press(Qt.Key.Key_Equal, text="=")                       # « + » d'un clavier QWERTY
        self.press(Qt.Key.Key_Plus, CTRL | Qt.KeyboardModifier.KeypadModifier, "+")
        self.assertAlmostEqual(self.scale(), canvas_mod.BUTTON_ZOOM_STEP ** 2)
        self.press(Qt.Key.Key_Minus, CTRL | Qt.KeyboardModifier.KeypadModifier, "-")
        self.assertAlmostEqual(self.scale(), canvas_mod.BUTTON_ZOOM_STEP)

    def test_plus_without_ctrl_does_not_zoom(self):
        self.press(Qt.Key.Key_Plus, Qt.KeyboardModifier.NoModifier, "+")
        self.assertAlmostEqual(self.scale(), 1.0)

    def test_buttons_are_in_the_edit_toolbar_with_their_icons(self):
        from laser_studio.ui.vector_editor.tab import EDIT_ACTIONS
        self.assertIn(("zoom_in", "ui.vector_zoom_in", "zoom-in"), EDIT_ACTIONS)
        self.assertIn(("zoom_out", "ui.vector_zoom_out", "zoom-out"), EDIT_ACTIONS)
        with open(os.path.join(ROOT, "controllers", "vector_editor.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('"zoom_in": canvas.navigation.zoom_in,', src)
        self.assertIn('"zoom_out": canvas.navigation.zoom_out,', src)
        for name in ("zoom-in", "zoom-out"):
            self.assertTrue(os.path.exists(os.path.join(
                ROOT, "resources", "icons", "breeze", "22x22", "actions", f"{name}.svg")), name)
        for key in ("ui.vector_zoom_in", "ui.vector_zoom_out"):
            self.assertEqual(sorted(TRANSLATIONS[key]), ["de", "en", "es", "fr"])


if __name__ == "__main__":
    unittest.main()
