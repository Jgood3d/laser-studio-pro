"""Effet bande dessinée (image/filters.cartoon_filter), dans le traitement de l'image et ses réglages."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PIL import Image
    from laser_studio.image.dithering import comparison_thumbnails, process_image
    from laser_studio.image.filters import cartoon_filter, cartoon_radius_px
except ImportError:  # numpy, scipy ou Pillow manquant
    cartoon_filter = None


def line_image():
    arr = np.full((120, 120), 200, np.float32)
    arr[55:65, :] = 70                               # un trait sombre horizontal
    return arr


@unittest.skipIf(cartoon_filter is None, "scipy / Pillow non importables ici")
class CartoonFilterTests(unittest.TestCase):
    def test_no_effect_without_radius_or_black(self):
        arr = line_image()
        for radius, black in ((0, 20), (8, 0)):
            np.testing.assert_array_equal(cartoon_filter(arr, radius, black), arr)

    def test_flat_areas_are_kept_and_the_line_turns_black(self):
        out = cartoon_filter(line_image(), 8, 20)
        self.assertEqual(out[10, 60], 200)                                   # fond loin du trait
        self.assertLess(out[56, 60], 10)                                     # trait noirci
        self.assertEqual(line_image()[56, 60], 70)                           # entrée intacte

    def test_more_black_with_a_higher_percentage(self):
        photo = np.random.default_rng(1).uniform(0, 255, (150, 150)).astype(np.float32)
        dark = [float((cartoon_filter(photo, 6, k) < 5).mean()) for k in (5, 20, 50)]
        self.assertEqual(dark, sorted(dark))
        self.assertLess(dark[0], dark[2])

    def test_radius_follows_the_engraving_resolution(self):
        self.assertEqual(cartoon_radius_px(1.5, 10), 15.0)
        self.assertEqual(cartoon_radius_px(-1, 10), 0.0)


@unittest.skipIf(cartoon_filter is None, "scipy / Pillow non importables ici")
class CartoonInProcessingTests(unittest.TestCase):
    PARAMS = dict(w_mm=20, h_mm=20, lmm=6, mirror_h=False, mirror_v=False, bright=0, contrast=0, gamma=100,
                  sharp=0, invert=False, algo="Niveaux de Gris")

    def image(self):
        return Image.fromarray(np.clip(line_image(), 0, 255).astype(np.uint8))

    def test_off_by_default_and_applied_when_set(self):
        plain, _ = process_image(self.image(), self.PARAMS)
        same, _ = process_image(self.image(), dict(self.PARAMS, cartoon_r=0, cartoon_k=50))
        np.testing.assert_array_equal(plain, same)
        comic, _ = process_image(self.image(), dict(self.PARAMS, cartoon_r=20, cartoon_k=20))
        self.assertLess(int(comic.min()), int(plain.min()))

    def test_thumbnails_apply_it_too(self):
        plain = dict(comparison_thumbnails(self.image(), 0, 0, 100, 0, False))
        comic = dict(comparison_thumbnails(self.image(), 0, 0, 100, 0, False, cartoon=(20, 20, 20.0)))
        self.assertTrue(any((plain[k] != comic[k]).any() for k in plain))


class CartoonSettingsTests(unittest.TestCase):
    def test_saved_in_projects_and_old_projects_get_the_defaults(self):
        try:
            from laser_studio.models.image_settings import ImageSettings
        except ImportError:
            self.skipTest("PyQt6 non importable ici")
        settings = ImageSettings()
        settings.update(cartoon_radius=15, cartoon_black=35)
        data = settings.to_project()
        self.assertEqual((data["cartoon_r"], data["cartoon_k"]), (15, 35))
        self.assertEqual(settings.processing_params()["cartoon_r"], 15)
        settings.load_project({"bright": 0})
        self.assertEqual((settings.cartoon_radius, settings.cartoon_black), (0, 20))


if __name__ == "__main__":
    unittest.main()
