"""Image de la caméra en fond du plateau, sur le canevas que la fenêtre utilise
vraiment (ui/vector_editor/canvas.py) : le dialogue Caméra y branche
set_camera_background, clear_camera_background et
set_camera_background_opacity."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

try:
    import numpy as np
    from PyQt6.QtWidgets import QApplication, QGraphicsPixmapItem
    from laser_studio.models.layers import LayersModel
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
except ImportError:  # PyQt6 ou numpy manquant
    VectorCanvasView = None


@unittest.skipIf(VectorCanvasView is None, "PyQt6 non importable ici")
class CameraBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        canvas = VectorCanvasView(LayersModel())
        canvas.set_work_area(400, 300)
        return canvas

    def camera_items(self, canvas):
        return [item for item in canvas.scene_obj.items() if isinstance(item, QGraphicsPixmapItem)]

    def test_image_is_placed_under_the_grid_at_bed_scale(self):
        canvas = self.make()
        canvas.set_camera_background(np.zeros((60, 80, 3), dtype=np.uint8), 400, 300)
        items = self.camera_items(canvas)
        self.assertEqual(len(items), 1)
        rect = items[0].sceneBoundingRect()
        self.assertAlmostEqual(rect.width(), 400 * canvas.px_per_mm, places=3)
        self.assertAlmostEqual(rect.height(), 300 * canvas.px_per_mm, places=3)
        self.assertLess(items[0].zValue(), -95)          # sous la grille

    def test_new_image_replaces_the_previous_one_and_clear_removes_it(self):
        canvas = self.make()
        canvas.set_camera_background(np.zeros((60, 80), dtype=np.uint8), 400, 300)
        canvas.set_camera_background(np.zeros((60, 80, 3), dtype=np.uint8), 400, 300)
        self.assertEqual(len(self.camera_items(canvas)), 1)
        canvas.camera.clear()
        self.assertEqual(self.camera_items(canvas), [])

    def test_opacity_is_clamped(self):
        canvas = self.make()
        canvas.set_camera_background(np.zeros((60, 80, 3), dtype=np.uint8), 400, 300)
        canvas.camera.set_opacity(0.0)
        self.assertAlmostEqual(self.camera_items(canvas)[0].opacity(), 0.05, places=3)
        canvas.camera.set_opacity(3)
        self.assertAlmostEqual(self.camera_items(canvas)[0].opacity(), 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
