"""Tramage sans Qt (image/dithering.py) : cas limites et anciens noms de workers.py."""
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


class OldNamesTests(unittest.TestCase):
    def test_workers_still_exports_the_old_names(self):
        try:
            from laser_studio import workers
        except ImportError:  # PyQt6 manquant
            self.skipTest("PyQt6 non importable ici")
        from laser_studio.image import gain_test
        self.assertIs(workers.build_gain_test_array, gain_test.build_gain_test_array)
        self.assertIs(workers.apply_error_diffusion, dithering.apply_error_diffusion)
        self.assertEqual(workers._HAS_NUMBA, dithering.HAS_NUMBA)


if __name__ == "__main__":
    unittest.main()
