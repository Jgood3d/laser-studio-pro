"""Netteté du traitement photo : filtre pur, pipeline du worker, sauvegarde et annulation."""
import os
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import image_filters as imf

try:
    import workers
except ImportError:
    workers = None


def blurred_edge(size=64):
    """Transition noir -> blanc adoucie (comme une photo légèrement floue)."""
    a = np.zeros((size, size), np.float32)
    ramp = np.clip((np.arange(size) - size / 2 + 4) / 8.0, 0, 1) * 255
    a[:] = ramp
    return Image.fromarray(a.astype(np.uint8), "L")


def edge_strength(img):
    a = np.array(img, dtype=np.float32)
    return float(np.abs(np.diff(a, axis=1)).max())


class SharpenFilterTests(unittest.TestCase):
    def test_zero_is_the_identity_and_returns_the_same_object(self):
        img = blurred_edge()
        self.assertIs(imf.sharpen_image(img, 0), img)
        self.assertIs(imf.sharpen_image(img, -5), img)

    def test_higher_amount_sharpens_more(self):
        img = blurred_edge()
        strengths = [edge_strength(imf.sharpen_image(img, a)) for a in (0, 20, 50, 100)]
        self.assertEqual(strengths, sorted(strengths))
        self.assertGreater(strengths[-1], strengths[0] * 1.1)          # +19 % mesuré à 100 pour un contour de 8 px

    def test_flat_image_stays_flat(self):
        flat = Image.new("L", (40, 40), 128)
        np.testing.assert_array_equal(np.array(imf.sharpen_image(flat, 100)), np.array(flat))

    def test_output_keeps_size_and_mode(self):
        out = imf.sharpen_image(blurred_edge(50), 60, 8.0)
        self.assertEqual((out.size, out.mode), ((50, 50), "L"))

    def test_amount_is_clamped(self):
        img = blurred_edge()
        np.testing.assert_array_equal(np.array(imf.sharpen_image(img, 100)), np.array(imf.sharpen_image(img, 5000)))

    def test_radius_follows_the_resolution_and_is_bounded(self):
        self.assertEqual(imf.sharpen_radius(None), 1.0)
        self.assertEqual(imf.sharpen_radius(0), 1.0)
        self.assertAlmostEqual(imf.sharpen_radius(10), 2.0)
        self.assertEqual(imf.sharpen_radius(1), 0.8)
        self.assertEqual(imf.sharpen_radius(100), 4.0)


@unittest.skipIf(workers is None, "workers.py non importable ici")
class WorkerPipelineTests(unittest.TestCase):
    def params(self, **kw):
        p = dict(w_mm=20.0, h_mm=20.0, lmm=3.2, mirror_h=False, mirror_v=False, bright=0, contrast=0,
                 gamma=100, invert=False, algo="Niveaux de Gris")
        p.update(kw)
        return p

    def run_worker(self, raw, **kw):
        out = {}
        w = workers.ImageProcessingWorker(raw, self.params(**kw))
        w.finished.connect(lambda arr, img: out.update(arr=arr))
        w.run()
        return out["arr"]

    def test_sharp_zero_or_missing_gives_the_historic_result(self):
        raw = blurred_edge()
        base = self.run_worker(raw)
        np.testing.assert_array_equal(base, self.run_worker(raw, sharp=0))
        self.assertNotIn("sharp", self.params())        # anciens appels sans la clé : toujours acceptés

    def test_sharpness_increases_edge_contrast_in_the_final_array(self):
        raw = blurred_edge()
        soft = self.run_worker(raw, sharp=0)
        crisp = self.run_worker(raw, sharp=70)
        self.assertGreater(edge_strength(Image.fromarray(crisp)), edge_strength(Image.fromarray(soft)))

    def test_works_with_every_dither_mode_and_invert(self):
        raw = blurred_edge()
        for algo in ("Niveaux de Gris", "Seuil Simple (Binaire)", "Floyd-Steinberg"):
            for invert in (False, True):
                arr = self.run_worker(raw, sharp=50, algo=algo, invert=invert)
                self.assertEqual(arr.shape, (int(20 * 3.2), int(20 * 3.2)))

    def test_sharpening_happens_before_inversion(self):
        raw = blurred_edge()
        normal = self.run_worker(raw, sharp=60)
        inverted = self.run_worker(raw, sharp=60, invert=True)
        np.testing.assert_array_equal(inverted.astype(np.int16), 255 - normal.astype(np.int16))


class IntegrationSourceTests(unittest.TestCase):
    """Le curseur doit être branché partout où les autres réglages le sont."""

    def src(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def test_slider_is_created_and_shown_after_gamma(self):
        ui = self.src("ui_setup_mixin.py")
        self.assertIn("self.slider_sharp = QSlider", ui)
        self.assertLess(ui.index('layout_img.addRow(tr("img.gamma")'), ui.index('layout_img.addRow(tr("img.sharpness")'))

    def test_reset_undo_params_and_comparison_use_it(self):
        ip = self.src("image_processing_mixin.py")
        for needle in ("self.slider_sharp.setValue(0)", '"sharp": self.slider_sharp.value()',
                       "(self.slider_sharp, \"sharp\")", "'sharp': self.slider_sharp.value()",
                       "sharpen_image(Image.fromarray"):
            self.assertIn(needle, ip)

    def test_project_saves_and_restores_it_with_a_default(self):
        pj = self.src("project_io_mixin.py")
        self.assertIn('"sharp": self.slider_sharp.value()', pj)
        self.assertIn('self.slider_sharp.setValue(proj_data.get("sharp", 0))', pj)


if __name__ == "__main__":
    unittest.main()
