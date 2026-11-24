import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector import text_presets as tp  # noqa: E402


class TextPresetsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "text_presets.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_is_empty(self):
        self.assertEqual(tp.load_user(self.path), {})

    def test_save_load_delete(self):
        values = {"font_family": "Arial", "bold": True, "size_mm": 8, "text_anchor": "below",
                  "text": "ignoré", "layer_id": "x"}
        self.assertTrue(tp.save_user("  Médaille  ", values, self.path))
        loaded = tp.load_user(self.path)
        self.assertEqual(list(loaded), ["Médaille"])
        self.assertEqual(loaded["Médaille"], {"font_family": "Arial", "bold": True, "size_mm": 8.0,
                                              "text_anchor": "below"})
        self.assertTrue(tp.delete_user("Médaille", self.path))
        self.assertEqual(tp.load_user(self.path), {})
        self.assertFalse(tp.delete_user("Médaille", self.path))

    def test_empty_name_refused(self):
        self.assertFalse(tp.save_user("   ", {"bold": True}, self.path))

    def test_corrupt_file_ignored(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{pas du json")
        self.assertEqual(tp.load_user(self.path), {})

    def test_bad_values_dropped(self):
        self.assertEqual(tp.clean({"size_mm": "abc", "bold": 1}), {"bold": True})


if __name__ == "__main__":
    unittest.main()
