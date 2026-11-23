"""Tests pure-logique de l'alignement caméra (sans ouverture de webcam)."""
import math
import os
import sys
import tempfile
import unittest

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.camera.workspace_alignment import (  # noqa: E402
    AlignmentTarget,
    WorkspaceAlignment,
    generate_apriltag_targets,
    compute_alignment,
    compute_homography,
    detect_apriltag_corners,
    merge_detections,
    tag_cut_side_mm,
    warp_to_bed,
    apriltag_engrave_polygons,
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
        # La marge va du bord du plateau au bord du tag : le centre est à marge + taille/2.
        targets = generate_apriltag_targets(300, 200, margin_mm=20, tag_size_mm=18, grid=(3, 3))
        self.assertEqual(len(targets), 9)
        xs = sorted({t.cx_mm for t in targets})
        ys = sorted({t.cy_mm for t in targets})
        self.assertEqual(xs[0], 29.0)
        self.assertEqual(xs[-1], 271.0)
        self.assertEqual(ys[0], 29.0)
        self.assertEqual(ys[-1], 171.0)
        # IDs uniques 0..8
        self.assertEqual(sorted(t.tag_id for t in targets), list(range(9)))

    def test_default_is_four_corner_tags_of_40mm(self):
        targets = generate_apriltag_targets(400, 400)
        self.assertEqual(len(targets), 4)
        self.assertEqual({t.size_mm for t in targets}, {40.0})
        self.assertEqual(sorted((t.cx_mm, t.cy_mm) for t in targets),
                         [(40.0, 40.0), (40.0, 360.0), (360.0, 40.0), (360.0, 360.0)])
        # Le cadre du gabarit est de la taille du tag.
        self.assertEqual(tag_cut_side_mm(40.0), 40.0)

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


def _render_scene(targets, bed_w, bed_h, ppm=2.0, rotate=True, seed=1):
    """Plateau vu en perspective avec les tags (tournés au hasard) : renvoie (image, matrice mm→pixel)."""
    rng = np.random.default_rng(seed)
    W, H = int(bed_w * ppm), int(bed_h * ppm)
    img = np.full((H, W), 235, np.uint8)
    for t in targets:
        angle = rng.integers(0, 4) * np.pi / 2 if rotate else 0.0
        rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        for poly in apriltag_engrave_polygons(AlignmentTarget(t.tag_id, 0.0, 0.0, t.size_mm)):
            pts = np.array(poly) @ rot.T + [t.cx_mm, t.cy_mm]
            px = np.c_[pts[:, 0] * ppm, (bed_h - pts[:, 1]) * ppm]
            cv2.fillPoly(img, [np.round(px * 16).astype(np.int32)], 25, lineType=cv2.LINE_AA, shift=4)
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = np.float32([[40, 30], [W - 20, 50], [W - 50, H - 20], [25, H - 40]])
    persp = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(img, persp, (W + 40, H + 40), borderValue=100)
    return cv2.GaussianBlur(out, (0, 0), 0.8)


class CornerAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.targets = generate_apriltag_targets(400, 400)
        self.ids = [t.tag_id for t in self.targets]
        self.img = _render_scene(self.targets, 400, 400)

    def test_alignment_ignores_tag_orientation(self):
        det = detect_apriltag_corners(self.img, self.ids)
        self.assertEqual(sorted(det), self.ids)
        al = compute_alignment(self.targets, det, self.img.shape[::-1])
        self.assertLess(al.reprojection_error_mm, 1.0)

    def test_warp_puts_tags_at_their_bed_positions(self):
        """Régression : l'image de la caméra doit couvrir le plateau, tags à leur place (en mm)."""
        det = detect_apriltag_corners(self.img, self.ids)
        al = compute_alignment(self.targets, det, self.img.shape[::-1])
        out = warp_to_bed(cv2.cvtColor(self.img, cv2.COLOR_GRAY2BGR), al, 400, 400, px_per_mm=2.0)
        found = detect_apriltag_corners(out, self.ids)
        self.assertEqual(sorted(found), self.ids)
        for t in self.targets:
            u, v = found[t.tag_id].mean(axis=0)
            self.assertAlmostEqual(u / 2.0, t.cx_mm, delta=1.0)
            self.assertAlmostEqual(400.0 - v / 2.0, t.cy_mm, delta=1.0)

    def test_merging_captures_recovers_tags_hidden_by_the_gantry(self):
        h, w = self.img.shape
        left_hidden, right_hidden = self.img.copy(), self.img.copy()
        left_hidden[:, : w // 3] = 60
        right_hidden[:, 2 * w // 3:] = 60
        cap1 = detect_apriltag_corners(left_hidden, self.ids)
        cap2 = detect_apriltag_corners(right_hidden, self.ids)
        self.assertLess(len(cap1), 3)
        with self.assertRaises(ValueError):
            compute_alignment(self.targets, merge_detections([cap1]), (w, h))
        merged = merge_detections([cap1, cap2])
        self.assertEqual(sorted(merged), self.ids)
        compute_alignment(self.targets, merged, (w, h))

    def test_inconsistent_alignment_is_rejected(self):
        """Des tags qui ne sont pas aux positions du gabarit ne donnent pas d'alignement."""
        det = detect_apriltag_corners(self.img, self.ids)
        wrong = [AlignmentTarget(t.tag_id, t.cx_mm, t.cy_mm, t.size_mm * 3) for t in self.targets]
        with self.assertRaises(ValueError):
            compute_alignment(wrong, det, self.img.shape[::-1])


if __name__ == "__main__":
    unittest.main()
