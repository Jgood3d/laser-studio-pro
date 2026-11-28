"""Contrôleur de « Graver une image » (controllers/image.py) : image source,
taille, traitement dans un thread, comparaison des algorithmes. Sans fenêtre."""
import os
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PIL import Image
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.image import ImageController
    from laser_studio.image.dithering import COMPARED_ALGORITHMS
    from laser_studio.models.image_settings import ImageSettings
    from laser_studio.models.machine import MachineConfig
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6, Pillow manquants
    ImageController = None


@unittest.skipIf(ImageController is None, "PyQt6 / Pillow non importables ici")
class ImageControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.size = [100.0, 100.0]
        self.keep_ratio = True
        self.settings = ImageSettings()
        self.dialogs = FakeDialogs()
        self.c = ImageController(
            self.settings, MachineConfig(), self.dialogs,
            size_mm=lambda: tuple(self.size), set_size=self.set_size,
            keep_ratio=lambda: self.keep_ratio, lines_mm=lambda: 2.0)
        self.events = []
        self.c.source_changed.connect(lambda image: self.events.append(("source", image and image.size)))
        self.c.processed.connect(lambda arr, image: self.events.append(("processed", arr.shape)))
        self.c.status.connect(lambda text, tooltip: self.events.append(("status", text)))
        self.c.resetting.connect(lambda: self.events.append(("resetting", self.settings.brightness)))
        self.c.loading_file.connect(lambda: self.events.append("loading"))

    def set_size(self, w, h):
        # Comme les vrais champs : chaque changement prévient la règle des proportions.
        self.size[0] = w
        self.c.dimension_changed("w", w)
        self.size[1] = h
        self.c.dimension_changed("h", h)

    def wait_processed(self, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end and not any(e[0] == "processed" for e in self.events if isinstance(e, tuple)):
            self.app.processEvents()
            time.sleep(0.01)

    def give_image(self, size=(200, 100)):
        self.c.set_image(Image.new("L", size, 128), 40.0, 20.0)
        self.events.clear()

    def test_image_from_another_tab_takes_its_size_and_is_processed(self):
        self.c.set_image(Image.new("L", (200, 100), 128), 40.0, 20.0)
        self.assertEqual(self.size, [40.0, 20.0])               # proportions non « corrigées »
        self.assertTrue(self.c.is_busy())                       # traitement prévu
        self.wait_processed()
        self.assertEqual(self.events, [("source", (200, 100)), ("processed", (40, 80))])   # 2 lignes/mm
        self.assertEqual(self.c.processed_array.shape, (40, 80))

    def test_rotation_restarts_at_100_mm_wide(self):
        self.c.rotate_left()                                    # sans image : rien
        self.give_image()
        self.c.rotate_left()
        self.assertEqual(self.c.raw_image.size, (100, 200))
        self.assertEqual(self.size, [100.0, 200.0])
        self.c.rotate_right()
        self.assertEqual((self.c.raw_image.size, self.size), ((200, 100), [100.0, 50.0]))

    def test_width_typed_keeps_the_proportions(self):
        self.give_image()
        self.size[0] = 60.0
        self.c.dimension_changed("w", 60.0)
        self.assertEqual(self.size, [60.0, 30.0])
        self.size[1] = 10.0
        self.c.dimension_changed("h", 10.0)
        self.assertEqual(self.size, [20.0, 10.0])
        self.keep_ratio = False
        self.size[0] = 70.0
        self.c.dimension_changed("w", 70.0)
        self.assertEqual(self.size, [70.0, 10.0])

    def test_clear_asks_first(self):
        self.c.clear()                                          # rien à retirer : pas de question
        self.give_image()
        self.dialogs.answer = False
        self.c.clear()
        self.assertTrue(self.c.has_image())
        self.dialogs.answer = True
        self.c.clear()
        self.assertFalse(self.c.has_image())
        self.assertIsNone(self.c.processed_array)
        self.assertEqual(self.events[0], ("source", None))
        self.assertEqual(self.dialogs.kinds(), ["confirm_yes_no", "confirm_yes_no"])

    def test_unreadable_file(self):
        self.assertFalse(self.c.load_path(os.path.join(REPO, "absent.png")))
        self.assertEqual(self.events, ["loading"])              # la Séparation rend quand même ses réglages
        self.assertEqual(self.dialogs.kinds(), ["error"])

    def test_open_image_goes_through_the_dialog(self):
        with tempfile.TemporaryDirectory() as d:
            self.dialogs.path = os.path.join(d, "photo.png")
            Image.new("L", (96, 48), 0).save(self.dialogs.path)
            self.c.open_image()
        self.assertEqual(self.c.raw_image.size, (96, 48))
        self.assertEqual(self.events[:2], ["loading", ("source", (96, 48))])
        self.assertIn("photo.png", self.events[2][1])

    def test_changes_during_processing_are_not_lost(self):
        self.give_image()
        self.c._process()
        self.c._process()                                       # thread en cours : demande mémorisée
        self.assertTrue(self.c.pending_reprocess)
        self.wait_processed()
        self.c.worker.wait(10000)
        self.assertFalse(self.c.pending_reprocess)

    def test_settings_change_schedules_a_processing(self):
        self.c.timer.stop()
        self.settings.update(brightness=20)
        self.assertTrue(self.c.timer.isActive())

    def test_comparison(self):
        self.assertIsNone(self.c.comparison())
        self.assertEqual(self.dialogs.kinds(), ["info"])
        self.give_image()
        thumbnails = self.c.comparison()
        self.assertEqual([name for name, _ in thumbnails], list(COMPARED_ALGORITHMS))
        self.assertLessEqual(max(arr.shape[1] for _, arr in thumbnails), 220)

    def test_reset_warns_before_resetting(self):
        self.settings.update(brightness=30)
        self.c.reset_settings()
        self.assertEqual(self.events, [("resetting", 30)])      # prévenue avant la remise à zéro
        self.assertEqual(self.settings.brightness, 0)

    def test_material_summary_reflects_the_real_negative(self):
        self.settings.update(material_bg="dark", invert=False)
        text = self.c.material_summary()
        self.assertIn("noir", text.lower())


if __name__ == "__main__":
    unittest.main()
