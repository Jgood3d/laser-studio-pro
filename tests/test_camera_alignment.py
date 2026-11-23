"""Tests pure-logique de l'alignement caméra (sans ouverture de webcam)."""
import os
import sys
import tempfile
import unittest

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.camera.workspace_alignment import (  # noqa: E402
    WorkspaceAlignment,
    generate_apriltag_targets,
    compute_homography,
    pixel_to_mm,
    mm_to_pixel,
)
from laser_studio.camera.lens_calibration import LensCalibration  # noqa: E402
from laser_studio.camera.storage import (  # noqa: E402
    CameraProfile,
    save_profile,
    load_profile,
    list_profiles,
    delete_profile,
)


class TargetLayoutTests(unittest.TestCase):
    def test_grid_3x3_covers_bed_with_margin(self):
        targets = generate_apriltag_targets(300, 200, margin_mm=20, tag_size_mm=18, grid=(3, 3))
        self.assertEqual(len(targets), 9)
        xs = sorted({t.cx_mm for t in targets})
        ys = sorted({t.cy_mm for t in targets})
        self.assertEqual(xs[0], 20.0)
        self.assertEqual(xs[-1], 280.0)
        self.assertEqual(ys[0], 20.0)
        self.assertEqual(ys[-1], 180.0)
        # IDs uniques 0..8
        self.assertEqual(sorted(t.tag_id for t in targets), list(range(9)))

    def test_rejects_tiny_bed(self):
        with self.assertRaises(ValueError):
            generate_apriltag_targets(30, 20, margin_mm=15, tag_size_mm=20)


class HomographyTests(unittest.TestCase):
    def _synthetic_alignment(self):
        """Homographie connue : simple échelle + décalage (pas de perspective)."""
        # pixel (u,v) → mm : x = u * 0.5, y = 200 - v * 0.5  (image 600×400 pour lit 300×200)
        targets = generate_apriltag_targets(300, 200, margin_mm=30, tag_size_mm=15, grid=(3, 3))
        detections = {}
        for t in targets:
            u = t.cx_mm / 0.5
            v = (200.0 - t.cy_mm) / 0.5
            detections[t.tag_id] = (u, v)
        return targets, detections, compute_homography(targets, detections, (600, 400))

    def test_roundtrip_pixel_mm(self):
        targets, detections, align = self._synthetic_alignment()
        self.assertGreaterEqual(len(align.used_tags), 4)
        self.assertLess(align.reprojection_error_mm, 0.05)
        for t in targets:
            u, v = detections[t.tag_id]
            x, y = pixel_to_mm(u, v, align)
            self.assertAlmostEqual(x, t.cx_mm, places=2)
            self.assertAlmostEqual(y, t.cy_mm, places=2)
            u2, v2 = mm_to_pixel(x, y, align)
            self.assertAlmostEqual(u2, u, places=1)
            self.assertAlmostEqual(v2, v, places=1)

    def test_too_few_tags_raises(self):
        targets = generate_apriltag_targets(300, 200, grid=(2, 2))
        detections = {targets[0].tag_id: (10.0, 10.0)}
        with self.assertRaises(ValueError):
            compute_homography(targets, detections, (640, 480), min_tags=4)


class StorageTests(unittest.TestCase):
    def setUp(self):
        # Redirige le dossier cameras vers un temporaire
        self._tmpdir = tempfile.mkdtemp()
        import laser_studio.camera.storage as st
        self._orig = st.get_autosave_dir
        st.get_autosave_dir = lambda: self._tmpdir

    def tearDown(self):
        import laser_studio.camera.storage as st
        st.get_autosave_dir = self._orig
        # Nettoyage best-effort
        for name in os.listdir(self._tmpdir):
            try:
                os.remove(os.path.join(self._tmpdir, name))
            except OSError:
                pass
        try:
            os.rmdir(os.path.join(self._tmpdir, "cameras"))
            os.rmdir(self._tmpdir)
        except OSError:
            pass

    def test_save_load_roundtrip(self):
        lens = LensCalibration(
            camera_matrix=np.eye(3),
            dist_coeffs=np.zeros((5, 1)),
            image_size=(640, 480),
            reprojection_error=0.12,
        )
        H = np.array([[0.5, 0, 0], [0, -0.5, 200], [0, 0, 1]], dtype=np.float64)
        align = WorkspaceAlignment(
            homography=H,
            inverse=np.linalg.inv(H),
            image_size=(640, 480),
            used_tags=[0, 1, 2, 3],
            reprojection_error_mm=0.3,
        )
        profile = CameraProfile(
            device_id="cam_test_0",
            display_name="Test Cam",
            lens=lens,
            alignment=align,
            preferred_width=1280,
            preferred_height=720,
        )
        path = save_profile(profile)
        self.assertTrue(os.path.isfile(path))

        loaded = load_profile("cam_test_0")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.display_name, "Test Cam")
        self.assertTrue(loaded.is_ready)
        self.assertEqual(loaded.preferred_width, 1280)
        np.testing.assert_allclose(loaded.lens.camera_matrix, np.eye(3))
        np.testing.assert_allclose(loaded.alignment.homography, H)

        profiles = list_profiles()
        self.assertTrue(any(p.device_id == "cam_test_0" for p in profiles))

        self.assertTrue(delete_profile("cam_test_0"))
        self.assertIsNone(load_profile("cam_test_0"))


if __name__ == "__main__":
    unittest.main()
