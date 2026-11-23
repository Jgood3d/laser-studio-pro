"""Préférences mémorisées (core/preferences.py) : valeurs relues converties, écriture,
isolation des tests (in_memory)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from laser_studio.core import preferences
    from laser_studio.core.preferences import MemoryStore, Preferences
except ImportError:  # PyQt6 manquant
    preferences = None


@unittest.skipIf(preferences is None, "PyQt6 non importable ici")
class PreferencesTests(unittest.TestCase):
    def test_values_read_back_as_qsettings_gives_them(self):
        # Selon le système, QSettings rend des chaînes : "true", "12", une chaîne seule pour une liste.
        prefs = Preferences(MemoryStore({"flag": "true", "off": "false", "count": "12", "bad": "abc",
                                         "ratio": "0.5", "one": "/projet.lsp", "many": ["a", "b"]}))
        self.assertTrue(prefs.get_bool("flag"))
        self.assertFalse(prefs.get_bool("off", True))
        self.assertTrue(prefs.get_bool("absent", True))           # absent : la valeur par défaut
        self.assertEqual(prefs.get_int("count"), 12)
        self.assertEqual(prefs.get_int("bad", 7), 7)              # illisible : la valeur par défaut
        self.assertEqual(prefs.get_float("ratio"), 0.5)
        self.assertEqual(prefs.get_list("one"), ["/projet.lsp"])
        self.assertEqual(prefs.get_list("many"), ["a", "b"])
        self.assertEqual(prefs.get_list("absent"), [])

    def test_set_and_remove(self):
        prefs = Preferences(MemoryStore())
        prefs.set("app_theme", "dark")
        self.assertEqual(prefs.get("app_theme"), "dark")
        prefs.remove("app_theme")
        self.assertIsNone(prefs.get("app_theme"))

    def test_in_memory_keeps_the_user_settings_untouched(self):
        with preferences.in_memory(ui={"language": "de"}) as stores:
            self.assertEqual(preferences.ui_preferences().get("language"), "de")
            preferences.machine_preferences().set("machine_bed_w_mm", 400.0)
            preferences.app_preferences().set("preview_material", "slate")
            self.assertEqual(stores[preferences.MACHINE_CONFIG].values, {"machine_bed_w_mm": 400.0})
            self.assertEqual(stores[preferences.APP_CONFIG].values, {"preview_material": "slate"})
            self.assertIsInstance(preferences.ui_preferences().store, MemoryStore)
        self.assertNotIsInstance(preferences.ui_preferences().store, MemoryStore)   # vrais fichiers ensuite


if __name__ == "__main__":
    unittest.main()
