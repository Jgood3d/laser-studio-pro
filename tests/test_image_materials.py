"""Matières de « Graver une image » : matières fournies, matières de l'utilisateur enregistrées à part
(models/image_materials.py) et leur effet sur les réglages de l'image (ImageSettings)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.models import image_materials as im  # noqa: E402

try:
    from laser_studio.models.image_settings import ImageSettings
except ImportError:  # PyQt6 manquant
    ImageSettings = None


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "image_materials.json")

    def test_builtin_materials_are_complete_and_consistent(self):
        self.assertGreaterEqual(len(im.BUILTIN), 10)
        for key, preset in im.BUILTIN.items():
            self.assertEqual(set(preset), set(im.PRESET_FIELDS), key)
            self.assertEqual(preset["invert"], preset["material_bg"] == "dark", key)
            self.assertEqual(im.clean(preset), preset, key)          # valeurs dans les bornes, algorithme connu

    def test_every_builtin_material_has_a_matching_2d_preview(self):
        """Choisir une matière dans « Graver une image » affiche la matière de même clé dans l'aperçu 2D."""
        from laser_studio.gcode.preview import PREVIEW_MATERIAL_ORDER, PREVIEW_MATERIALS
        for key in im.BUILTIN:
            self.assertIn(key, PREVIEW_MATERIALS, key)
            self.assertIn(key, PREVIEW_MATERIAL_ORDER, key)
        self.assertEqual(set(PREVIEW_MATERIAL_ORDER), set(PREVIEW_MATERIALS))

    def test_save_get_delete_user_material(self):
        lib = im.ImageMaterials(self.path)
        self.assertEqual(lib.user_names(), [])
        key = lib.save_user("  Mon bois ", {"material_bg": "light", "contrast": 40, "algorithm": "Stucki"})
        self.assertEqual(key, "user:Mon bois")
        self.assertEqual(lib.get(key)["contrast"], 40)
        self.assertEqual(lib.user_names(), ["Mon bois"])
        self.assertEqual(im.ImageMaterials(self.path).get(key)["algorithm"], "Stucki")   # relu depuis le fichier
        self.assertTrue(lib.delete_user(key))
        self.assertIsNone(lib.get(key))
        self.assertFalse(lib.delete_user(key))

    def test_builtin_materials_are_never_overwritten(self):
        lib = im.ImageMaterials(self.path)
        before = dict(im.BUILTIN["wood"])
        key = lib.save_user("wood", {"material_bg": "dark", "contrast": -50})
        self.assertEqual(key, "user:wood")                       # une matière à soi, d'un autre type de clé
        self.assertEqual(im.BUILTIN["wood"], before)
        self.assertEqual(lib.get("wood"), before)
        self.assertFalse(lib.delete_user("wood"))                # une matière fournie ne se supprime pas

    def test_empty_name_and_unwritable_file_change_nothing(self):
        lib = im.ImageMaterials(self.path)
        self.assertIsNone(lib.save_user("   ", {"contrast": 1}))
        bad = im.ImageMaterials(os.path.join(self.dir.name, "absent", "x.json"))
        self.assertIsNone(bad.save_user("A", {"contrast": 1}))
        self.assertEqual(bad.user_names(), [])

    def test_damaged_file_is_ignored_and_values_are_cleaned(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("pas du json")
        self.assertEqual(im.ImageMaterials(self.path).user_names(), [])
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"A": {"brightness": 999, "algorithm": "inconnu", "material_bg": "bois", "x": 1}, "B": 3}, fh)
        a = im.ImageMaterials(self.path).get("user:A")
        self.assertEqual((a["brightness"], a["material_bg"], a["invert"]), (100, "light", False))
        self.assertNotIn("algorithm", a)
        self.assertNotIn("x", a)
        self.assertEqual(im.ImageMaterials(self.path).user_names(), ["A"])

    def test_generic_and_unknown_keys_have_no_preset(self):
        lib = im.ImageMaterials(self.path)
        for key in ("dark", "light", "user:absente", "inconnue"):
            self.assertIsNone(lib.get(key))


@unittest.skipIf(ImageSettings is None, "PyQt6 non importable ici")
class SettingsTests(unittest.TestCase):
    def test_choosing_a_material_sets_only_the_image_correction(self):
        s = ImageSettings()
        s.update(mirror_h=True)
        changes = s.choose_material("slate", im.BUILTIN["slate"])
        self.assertEqual(s.material, "slate")
        for name, value in im.BUILTIN["slate"].items():
            self.assertEqual(s.get(name), value, name)
        self.assertTrue(s.mirror_h)                              # le miroir n'est pas touché
        self.assertIn("material", changes)

    def test_no_material_is_chosen_at_first_and_dark_light_are_not_materials(self):
        s = ImageSettings()
        self.assertEqual(s.material, "")
        s.update(material="slate")
        s.update(material="light")                               # ancienne valeur (liste d'avant) : « aucune »
        self.assertEqual(s.material, "")

    def test_choose_material_without_preset_only_sets_background_and_negative(self):
        s = ImageSettings()
        s.choose_material("slate", im.BUILTIN["slate"])
        s.choose_material("dark")                                # comportement historique, plus dans la liste
        self.assertEqual((s.material, s.material_bg, s.invert), ("", "dark", True))
        s.choose_material("light")
        self.assertEqual((s.material, s.material_bg, s.invert), ("", "light", False))
        s.choose_material("user:disparue")                       # matière de l'utilisateur introuvable
        self.assertEqual((s.material, s.material_bg), ("user:disparue", "light"))

    def test_background_changed_from_elsewhere_resets_the_list(self):
        s = ImageSettings()
        s.choose_material("wood", im.BUILTIN["wood"])
        s.update(brightness=30)
        self.assertEqual(s.material, "wood")                     # tons modifiés : la matière reste affichée
        s.update(material_bg="dark")                             # ex. la Séparation (verre peint)
        self.assertEqual(s.material, "")
        s.choose_material("slate", im.BUILTIN["slate"])
        s.update(material_bg="dark")                             # même fond : la matière reste
        self.assertEqual(s.material, "slate")

    def test_current_settings_become_a_user_material(self):
        s = ImageSettings()
        s.update(brightness=12, contrast=34, gamma=120, sharpness=5, algorithm="Atkinson", material_bg="dark",
                 invert=True)
        preset = s.material_preset()
        self.assertEqual(set(preset), set(im.PRESET_FIELDS))
        other = ImageSettings()
        other.choose_material("user:x", preset)
        self.assertEqual((other.brightness, other.contrast, other.gamma, other.algorithm, other.invert),
                         (12, 34, 120, "Atkinson", True))

    def test_project_keeps_the_material_and_old_projects_open(self):
        s = ImageSettings()
        s.choose_material("user:Mon bois", {"material_bg": "light", "contrast": 20})
        data = s.to_project()
        self.assertEqual(data["material"], "user:Mon bois")
        other = ImageSettings()
        other.load_project(data)
        self.assertEqual(other.to_dict(), s.to_dict())
        other.load_project({"invert": True})                     # projet d'avant les matières nommées
        self.assertEqual((other.material, other.material_bg), ("", "dark"))
        self.assertNotIn("material", s.processing_params())      # n'est pas un paramètre du traitement

    def test_reset_puts_the_light_background_back(self):
        s = ImageSettings()
        s.choose_material("glass", im.BUILTIN["glass"])
        s.reset()
        self.assertEqual((s.material, s.material_bg, s.contrast), ("", "light", 0))


if __name__ == "__main__":
    unittest.main()
