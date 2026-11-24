"""Stencil Studio sans serveur ni fenêtre : API de calcul (controllers/api.py)
sur une session (models/session.py), et réglages mémorisés (models/presets.py)."""
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from stencil_studio.controllers.api import StudioApi, parse_sbox
    from stencil_studio.models.presets import PresetsStore
    from stencil_studio.models.session import StudioSession
except ImportError:  # OpenCV, SciPy manquants
    StudioApi = None

EXAMPLE = os.path.join(REPO, "src", "stencil_studio", "exemple", "girl1.png")
FRAME = {"cx": 0.43, "cy": 0.45, "w": 0.49}


@unittest.skipIf(StudioApi is None, "OpenCV / SciPy non importables ici")
class StudioApiTests(unittest.TestCase):
    def setUp(self):
        self.api = StudioApi(StudioSession())
        with open(EXAMPLE, "rb") as f:
            self.api.load_image(f.read(), "girl1.png")

    def request(self, **extra):
        return {"params": {"output": "stencil", "ai_subject": False}, "frame": FRAME, "work": 300, **extra}

    def test_preview_and_cache(self):
        out = self.api.preview(self.request(seq=1))
        self.assertTrue(out["image"].startswith("data:image/png;base64,"))
        self.assertGreater(out["stats"]["contours"], 0)
        first = self.api.cache.result
        self.api.preview(self.request(seq=2))
        self.assertIs(self.api.cache.result, first)               # même demande : depuis le cache

    def test_outdated_preview_is_not_computed(self):
        self.api.preview(self.request(seq=5))
        self.assertEqual(self.api.preview(self.request(seq=3)), {"stale": True})

    def test_export_gives_svg_and_dxf_named_after_the_image(self):
        out = self.api.export(self.request())
        self.assertIn("<svg", out["svg"])
        self.assertIn("POLYLINE", out["dxf"])
        self.assertEqual(out["name"], "girl1")

    def test_new_image_empties_the_cache(self):
        self.api.preview(self.request(seq=1))
        with open(EXAMPLE, "rb") as f:
            self.api.load_image(f.read(), "autre.png")
        self.assertIsNone(self.api.cache.sig)
        self.assertEqual(self.api.session.img_id, 2)

    def test_subject_rectangle_is_validated(self):
        self.assertEqual(parse_sbox({"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.5}), (0.1, 0.2, 0.5, 0.5))
        self.assertIsNone(parse_sbox({"x": 0.1, "y": 0.2, "w": 0.01, "h": 0.5}))   # trop petit
        self.assertIsNone(parse_sbox(None))


@unittest.skipIf(StudioApi is None, "OpenCV / SciPy non importables ici")
class PresetsTests(unittest.TestCase):
    def test_round_trip_and_unreadable_file(self):
        with tempfile.TemporaryDirectory() as folder:
            store = PresetsStore(os.path.join(folder, "presets.json"))
            self.assertEqual(store.load(), {})                    # absent
            store.save({"Bois": {"size_mm": 80}})
            self.assertEqual(store.load(), {"Bois": {"size_mm": 80}})
            with open(store.path, "w", encoding="utf-8") as f:
                f.write("pas du json")
            self.assertEqual(store.load(), {})                    # illisible : rien, sans erreur


if __name__ == "__main__":
    unittest.main()
