"""Ressources (images) : rangées dans resources/, retrouvées par find_resource."""
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

from laser_studio.core import paths  # noqa: E402

IMAGES = ("buy_me_a_coffee.png", "laser_studio_pro_banner.png",
          "laser_studio_pro_512.png", "laser_studio_pro.ico")


class ResourcesTests(unittest.TestCase):
    def test_every_image_is_in_the_resources_folder(self):
        for name in IMAGES:
            self.assertEqual(paths.find_resource(name),
                             os.path.join(ROOT, "resources", name), name)
            self.assertFalse(os.path.exists(os.path.join(ROOT, name)), name)   # plus à la racine

    def test_missing_resource_returns_none(self):
        self.assertIsNone(paths.find_resource("absente.png"))

    def test_search_order_executable_then_bundle(self):
        with tempfile.TemporaryDirectory() as app_dir, tempfile.TemporaryDirectory() as bundle:
            with mock.patch.object(paths, "get_app_dir", return_value=app_dir), \
                    mock.patch.object(paths, "get_bundle_dir", return_value=bundle):
                self.assertEqual(paths.resource_candidates("a.png"), [
                    os.path.join(app_dir, "resources", "a.png"), os.path.join(app_dir, "a.png"),
                    os.path.join(bundle, "resources", "a.png"), os.path.join(bundle, "a.png")])
                os.makedirs(os.path.join(bundle, "resources"))
                embedded = os.path.join(bundle, "resources", "a.png")
                open(embedded, "w").close()
                self.assertEqual(paths.find_resource("a.png"), embedded)
                # Image posée à côté de l'exécutable (ancien emplacement) : prioritaire.
                replaced = os.path.join(app_dir, "a.png")
                open(replaced, "w").close()
                self.assertEqual(paths.find_resource("a.png"), replaced)


if __name__ == "__main__":
    unittest.main()
