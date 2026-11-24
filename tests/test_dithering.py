"""Tramage sans Qt (image/dithering.py) : cas limites."""
import os
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.image import dithering  # noqa: E402

PARAMS = dict(w_mm=10.0, h_mm=5.0, lmm=4.0, mirror_h=False, mirror_v=False, bright=0, contrast=0,
              gamma=100, invert=False, algo="Floyd-Steinberg")


class ProcessImageTests(unittest.TestCase):
    def test_nothing_to_process(self):
        self.assertIsNone(dithering.process_image(None, PARAMS))
        self.assertIsNone(dithering.process_image(Image.new("L", (10, 10)), dict(PARAMS, w_mm=0.1)))

    def test_size_at_the_engraving_resolution(self):
        arr, image = dithering.process_image(Image.new("L", (300, 100), 90), PARAMS)
        self.assertEqual(arr.shape, (20, 40))
        self.assertEqual(set(np.unique(arr)) <= {0, 255}, True)
        np.testing.assert_array_equal(np.array(image), arr)

    def test_every_algorithm_of_the_list_runs(self):
        raw = Image.fromarray(np.tile(np.linspace(0, 255, 64), (32, 1)).astype(np.uint8))
        for algo in dithering.ALGORITHMS:
            arr, _ = dithering.process_image(raw, dict(PARAMS, algo=algo))
            self.assertEqual(arr.dtype, np.uint8, algo)

    def test_grayscale_keeps_the_tones(self):
        arr, _ = dithering.process_image(Image.new("L", (40, 20), 100), dict(PARAMS, algo=dithering.GRAYSCALE))
        self.assertTrue(np.all(np.abs(arr.astype(int) - 100) <= 1))


class TonePreviewTests(unittest.TestCase):
    def setUp(self):
        self.img = Image.fromarray(np.tile(np.linspace(20, 230, 64), (32, 1)).astype(np.uint8))

    def test_neutral_settings_keep_the_image(self):
        np.testing.assert_array_equal(np.array(dithering.tone_preview(self.img, 0, 0, 100, 0)), np.array(self.img))

    def test_each_setting_changes_the_preview(self):
        base = np.array(dithering.tone_preview(self.img, 0, 0, 100, 0))
        for name, args in (("luminosité", (50, 0, 100, 0)), ("contraste", (0, 50, 100, 0)),
                           ("gamma", (0, 0, 200, 0)), ("netteté", (0, 0, 100, 60))):
            self.assertFalse(np.array_equal(base, np.array(dithering.tone_preview(self.img, *args))), name)

    def test_no_dithering_and_no_negative(self):
        out = np.array(dithering.tone_preview(self.img, 0, 0, 100, 0))
        self.assertGreater(len(np.unique(out)), 2)          # niveaux de gris, pas tramé
        self.assertEqual(out.shape, (32, 64))


if __name__ == "__main__":
    unittest.main()
