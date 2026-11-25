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


class AsIsTests(unittest.TestCase):
    """Image déjà tramée (Image-R…) gravée telle quelle."""

    def setUp(self):
        rng = np.random.default_rng(1)
        self.dots = (rng.random((20, 30)) > 0.5).astype(np.uint8) * 255           # tramage binaire
        self.img = Image.fromarray(self.dots)
        # 1 pixel = 1 ligne : 30 px sur 3 mm à 10 lignes/mm.
        self.params = dict(PARAMS, w_mm=3.0, h_mm=2.0, lmm=10.0, as_is=True, bright=80, contrast=-50, gamma=250,
                           sharp=100, algo="Atkinson")

    def test_points_are_kept_exactly_and_tones_are_ignored(self):
        arr, image = dithering.process_image(self.img, self.params)
        np.testing.assert_array_equal(arr, self.dots)
        np.testing.assert_array_equal(np.array(image), self.dots)

    def test_size_is_rounded_not_truncated(self):
        # 30 px / 3,0000001 mm donne 9,9999997 lignes/mm : int() perdrait un pixel.
        params = dict(self.params, w_mm=30 / 9.9999997, lmm=9.9999997, h_mm=20 / 9.9999997)
        arr, _ = dithering.process_image(self.img, params)
        self.assertEqual(arr.shape, (20, 30))

    def test_scaling_keeps_pure_black_and_white(self):
        arr, _ = dithering.process_image(self.img, dict(self.params, lmm=7.3))
        self.assertTrue(set(np.unique(arr)) <= {0, 255})

    def test_negative_and_mirror_still_apply(self):
        arr, _ = dithering.process_image(self.img, dict(self.params, invert=True, mirror_h=True))
        np.testing.assert_array_equal(arr, 255 - self.dots[:, ::-1])

    def test_off_by_default_dithers_as_before(self):
        params = {k: v for k, v in self.params.items() if k != "as_is"}
        arr, _ = dithering.process_image(Image.new("L", (30, 20), 128), dict(params, bright=0, contrast=0, gamma=100))
        self.assertTrue(set(np.unique(arr)) <= {0, 255})

    def test_is_binary(self):
        self.assertTrue(dithering.is_binary(self.img))
        self.assertTrue(dithering.is_binary(Image.new("L", (10, 10), 250)))             # presque blanc
        gradient = Image.fromarray(np.tile(np.linspace(0, 255, 64), (8, 1)).astype(np.uint8))
        self.assertFalse(dithering.is_binary(gradient))                                  # photo en gris


if __name__ == "__main__":
    unittest.main()
