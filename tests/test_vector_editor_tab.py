"""Onglet de l'éditeur vectoriel (ui/vector_editor/tab.py) : l'interrupteur « Fond caméra » et son bouton
« Actualiser » émettent leurs demandes ; show_camera_background coche sans en émettre."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.i18n import tr
    from laser_studio.models.layers import LayersModel
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.ui.vector_editor.tab import VectorEditorTab
except ImportError:  # PyQt6 manquant
    VectorEditorTab = None


@unittest.skipIf(VectorEditorTab is None, "PyQt6 non importable ici")
class CameraBackgroundButtonsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tab = VectorEditorTab(VectorCanvasView(LayersModel()))
        self.addCleanup(self.tab.deleteLater)
        self.toggled, self.refreshed = [], []
        self.tab.camera_background_toggled.connect(self.toggled.append)
        self.tab.camera_refresh_requested.connect(lambda: self.refreshed.append(True))

    def test_toggle_and_refresh_emit(self):
        self.tab.camera_toggle.trigger()
        self.assertEqual(self.toggled, [True])
        refresh = next(a for a in self.tab.create_toolbar.actions() if a.text() == tr("ui.vector_camera_refresh"))
        refresh.trigger()
        self.assertEqual(self.refreshed, [True])

    def test_show_camera_background_does_not_emit(self):
        self.tab.show_camera_background(True)
        self.assertTrue(self.tab.camera_toggle.isChecked())
        self.assertEqual(self.toggled, [])


@unittest.skipIf(VectorEditorTab is None, "PyQt6 non importable ici")
class EmptyCanvasAndToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.canvas = VectorCanvasView(LayersModel())
        self.tab = VectorEditorTab(self.canvas)
        self.addCleanup(self.tab.deleteLater)

    def test_empty_canvas_offers_ways_to_start(self):
        from laser_studio.models.vector_objects import ShapeObject
        got, vectorize = [], []
        self.tab.command.connect(got.append)
        self.tab.vectorize_requested.connect(lambda: vectorize.append(True))
        hint = self.tab.empty_hint
        self.assertFalse(hint.isHidden())
        for button in hint.buttons.values():
            button.click()
        # Pour commencer, puis un bouton par générateur (sa page de la fenêtre des générateurs).
        self.assertEqual(got, ["import", "shape", "library", "box", "puzzle", "ornament", "keychain"])
        self.assertEqual(vectorize, [True])                                    # l'onglet Vectorisation
        self.canvas.add_object(ShapeObject("Rectangle", 10, 10))
        self.assertTrue(hint.isHidden())                                       # un objet : l'accueil s'efface
        self.canvas.document.load([])                                          # « Tout supprimer »
        self.assertFalse(hint.isHidden())

    def test_vectorize_button_asks_for_the_vectorization_tab(self):
        asked = []
        self.tab.vectorize_requested.connect(lambda: asked.append(True))
        self.tab.top_buttons["vectorize"].click()
        self.assertEqual(asked, [True])

    def test_selection_tool_comes_first(self):
        self.assertIs(self.tab.create_toolbar.actions()[0], self.tab.draw_buttons[None])


if __name__ == "__main__":
    unittest.main()
