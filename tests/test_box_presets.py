import os
import tempfile
import unittest

from laser_studio.vector import box_presets as bp


class PresetFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "p.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_save_load_delete_roundtrip_without_project_keys(self):
        self.assertEqual(bp.load_user(self.path), {})
        self.assertTrue(bp.save_user("Ma boîte", {"width": 90.0, "cut_layer": 3, "decors": [1], "lid_type": "lip"}, self.path))
        self.assertEqual(bp.load_user(self.path), {"Ma boîte": {"width": 90.0, "lid_type": "lip"}})
        self.assertTrue(bp.delete_user("Ma boîte", self.path))
        self.assertEqual(bp.load_user(self.path), {})
        self.assertFalse(bp.delete_user("absent", self.path))

    def test_empty_name_and_broken_file(self):
        self.assertFalse(bp.save_user("  ", {"width": 1}, self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{pas du json")
        self.assertEqual(bp.load_user(self.path), {})

    def test_builtin_presets_build(self):
        from laser_studio.vector import box_generator as bg
        names = {f.name for f in bg.BoxParams.__dataclass_fields__.values()}
        for key, values in bp.BUILTIN.items():
            kwargs = {k: v for k, v in values.items() if k in names}
            result = bg.build_box(bg.BoxParams(**kwargs))
            self.assertTrue(result.panels, key)


if __name__ == "__main__":
    unittest.main()
