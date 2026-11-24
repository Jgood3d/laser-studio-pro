"""Recadrage de l'image de « Graver une image » : ImageController.crop (échelle gardée, retour à l'image
entière, rotation) et fenêtre CropDialog (cadre tracé, déplacé, proportions)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PIL import Image
    from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.image import ImageController
    from laser_studio.models.image_settings import ImageSettings
    from laser_studio.models.machine import MachineConfig
    from laser_studio.ui.tabs.image.crop_dialog import CropDialog
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 / Pillow manquants
    ImageController = None


@unittest.skipIf(ImageController is None, "PyQt6 / Pillow non importables ici")
class CropControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.size = [100.0, 50.0]
        self.c = ImageController(ImageSettings(), MachineConfig(), FakeDialogs(),
                                 size_mm=lambda: tuple(self.size), set_size=self.set_size,
                                 keep_ratio=lambda: False, lines_mm=lambda: 2.0)
        self.c._set_source(Image.new("L", (200, 100), 128), (100.0, 50.0))     # 0,5 mm par pixel

    def set_size(self, w, h):
        self.size = [w, h]

    def test_crop_keeps_the_scale_and_can_be_undone(self):
        self.c.crop((20, 10, 120, 60))
        self.assertEqual(self.c.raw_image.size, (100, 50))
        self.assertEqual(self.size, [50.0, 25.0])                          # même échelle : 0,5 mm / px
        self.assertEqual(self.c.source_image.size, (200, 100))             # image entière gardée
        self.c.crop((0, 10, 200, 60))                                      # cadre élargi depuis l'image entière
        self.assertEqual((self.c.raw_image.size, self.size), ((200, 50), [100.0, 25.0]))
        self.c.crop(None)
        self.assertEqual((self.c.raw_image.size, self.c.crop_box, self.size), ((200, 100), None, [100.0, 50.0]))

    def test_invalid_or_full_frames(self):
        self.c.crop((0, 0, 200, 100))                                      # toute l'image : pas de cadre
        self.assertIsNone(self.c.crop_box)
        self.c.crop((50, 50, 50, 80))                                      # largeur nulle : ignoré
        self.assertIsNone(self.c.crop_box)
        self.c.crop((150, 80, 250, 130))                                   # dépasse : ramené dans l'image
        self.assertEqual(self.c.crop_box, (150, 80, 200, 100))

    def test_rotation_starts_from_the_cropped_image(self):
        self.c.crop((20, 10, 120, 60))
        self.c.rotate_left()
        self.assertEqual((self.c.source_image.size, self.c.crop_box), ((50, 100), None))


@unittest.skipIf(ImageController is None, "PyQt6 / Pillow non importables ici")
class CropDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, box=None):
        dialog = CropDialog(Image.new("L", (400, 200), 200), box, 0.25)
        dialog.resize(900, 600)
        dialog.show()
        self.app.processEvents()
        self.addCleanup(dialog.close)
        return dialog

    def at(self, dialog, x, y):
        p = dialog.view.mapFromScene(QPointF(x, y))
        return QPoint(p.x(), p.y())

    def drag(self, dialog, start, end):
        vp = dialog.view.viewport()
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, self.at(dialog, *start))
        QTest.mouseMove(vp, self.at(dialog, *end))
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, self.at(dialog, *end))

    def test_whole_image_by_default_and_existing_frame_shown(self):
        self.assertIsNone(self.make().box())
        self.assertEqual(self.make((10, 20, 110, 120)).box(), (10, 20, 110, 120))

    def test_draw_then_move_a_frame(self):
        dialog = self.make((0, 0, 50, 50))
        self.drag(dialog, (100, 50), (300, 150))                           # hors du cadre : nouveau cadre
        left, top, right, bottom = dialog.box()
        self.assertAlmostEqual(left, 100, delta=3)
        self.assertAlmostEqual(right, 300, delta=3)
        self.drag(dialog, (200, 100), (250, 120))                          # dans le cadre : déplacé
        moved = dialog.box()
        self.assertAlmostEqual(moved[0] - left, 50, delta=3)
        self.assertAlmostEqual(moved[2] - moved[0], right - left, delta=1)
        self.assertIn("mm", dialog.size_label.text())

    def test_keep_ratio_and_whole_image_button(self):
        dialog = self.make((100, 50, 300, 150))                            # 2 : 1
        dialog.keep_ratio.setChecked(True)
        self.drag(dialog, (300, 150), (340, 190))                          # coin bas-droit
        left, top, right, bottom = dialog.box()
        self.assertAlmostEqual((right - left) / (bottom - top), 2.0, delta=0.05)
        dialog.view.set_rect(QRectF(dialog.view.bounds))
        self.assertIsNone(dialog.box())


if __name__ == "__main__":
    unittest.main()
