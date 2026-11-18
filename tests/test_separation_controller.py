"""Séparation couleur / verre (controllers/separation.py) : image source,
réglages du verre partagés avec « Graver une image », tonalité, aperçus, export."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PIL import Image
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.separation import (
        PREVIEW_ENGRAVE, PREVIEW_ORIGINAL, PREVIEW_PRINT, PREVIEW_SIMULATION, SeparationController,
    )
    from laser_studio.models.image_settings import ImageSettings
    from laser_studio.models.separation import SeparationSettings
except ImportError:  # PyQt6, Pillow manquants
    SeparationController = None


@unittest.skipIf(SeparationController is None, "PyQt6 / Pillow non importables ici")
class SeparationControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "vitrail.png")
        image = Image.new("RGBA", (300, 200), (200, 40, 40, 255))
        image.paste((40, 40, 200, 0), (150, 0, 300, 200))      # moitié transparente
        image.save(self.path)
        self.image_settings = ImageSettings()
        self.settings = SeparationSettings()
        self.c = SeparationController(self.settings, self.image_settings,
                                      frame_args=lambda: (0, 1.0, 0.5, 0.5), engrave_lmm=lambda: 10.0)
        self.sources = []
        self.c.source_changed.connect(lambda ratio, name: self.sources.append((ratio, name)))

    def test_load_applies_the_glass_settings_and_release_gives_them_back(self):
        self.image_settings.update(material_bg="light", invert=False, mirror_h=False, brightness=12)
        self.c.load(self.path)
        self.assertEqual(self.sources, [(1.5, "vitrail.png")])
        self.assertEqual((self.image_settings.material_bg, self.image_settings.invert,
                          self.image_settings.mirror_h), ("dark", True, True))
        self.c.load(self.path)                    # 2e image : l'état d'avant reste le premier
        self.c.release_glass_settings()
        self.assertEqual((self.image_settings.material_bg, self.image_settings.invert,
                          self.image_settings.mirror_h, self.image_settings.brightness),
                         ("light", False, False, 12))

    def test_forget_glass_settings(self):
        self.c.load(self.path)
        self.c.forget_glass_settings()
        self.c.release_glass_settings()           # rien à rendre
        self.assertTrue(self.image_settings.invert)

    def test_transparency_is_flattened_on_white(self):
        self.c.load(self.path)
        self.assertEqual(self.c.source.getpixel((250, 100)), (255, 255, 255))

    def test_unreadable_file_changes_nothing(self):
        bad = os.path.join(self.dir.name, "pas_une_image.png")
        with open(bad, "w") as f:
            f.write("texte")
        with self.assertRaises(Exception):
            self.c.load(bad)
        self.assertFalse(self.c.has_image())
        self.assertFalse(self.image_settings.invert)

    def test_rotate_and_clear(self):
        self.assertFalse(self.c.rotate(90))
        self.c.load(self.path)
        self.assertTrue(self.c.rotate(90))
        self.assertEqual(self.c.source.size, (200, 300))
        self.c.clear()
        self.assertFalse(self.c.has_image())
        self.assertEqual(self.sources[-1], (None, ""))

    def test_tone_has_the_plate_size(self):
        tones = []
        self.c.tone_ready.connect(lambda image, w, h: tones.append((image.mode, w, h, image.size)))
        self.c.push_tone()                        # pas d'image : rien
        self.c.load(self.path)
        self.settings.update(plate_w=120.0, plate_h=80.0)
        self.c.push_tone()
        mode, w, h, size = tones[0]
        self.assertEqual((mode, w, h), ("L", 120.0, 80.0))
        self.assertAlmostEqual(size[0] / size[1], 1.5, places=2)

    def test_previews_and_export(self):
        self.c.load(self.path)
        engraved = np.full((80, 120), 255, dtype=np.uint8)
        engraved[:, :60] = 0
        self.c.invalidate_previews()
        for index in (PREVIEW_ORIGINAL, PREVIEW_ENGRAVE, PREVIEW_PRINT, PREVIEW_SIMULATION):
            self.assertTrue(self.c.needs_render(index))
            self.assertIsNotNone(self.c.render_preview(index, engraved))
            self.assertFalse(self.c.needs_render(index))
        files, pdf_ok = self.c.export(self.dir.name, engraved)
        names = sorted(os.path.basename(p) for p in files)
        self.assertIn("vitrail_gravure.png", names)
        self.assertIn("vitrail_couleur.png", names)
        self.assertEqual(pdf_ok, "vitrail_couleur.pdf" in names)
        for path in files:
            self.assertTrue(os.path.getsize(path) > 0)


if __name__ == "__main__":
    unittest.main()
