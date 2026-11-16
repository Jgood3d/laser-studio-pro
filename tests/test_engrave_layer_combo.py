"""Liste « Calque de gravure » de l'onglet « Graver une image » : contenu, signal, branchement."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.tabs.image import ImageSettingsPanel
    from laser_studio.ui.tabs.image.engrave_layer_combo import EngraveLayerComboBox
except ImportError:  # PyQt6 manquant
    EngraveLayerComboBox = None


class Layer:
    def __init__(self, id, name, mode, color="#ff0000"):
        self.id, self.name, self.mode, self.color = id, name, mode, color


FILL, CUT, MARK = "Gravure Remplie", "Découpe", "Marquage (Contour)"
LAYERS = [Layer("c", "Coupe", CUT), Layer("e1", "Gravure", FILL), Layer("m", "Marque", MARK),
          Layer("e2", "Photo bois", FILL, "#00ff00")]


def read(relative):
    with open(os.path.join(ROOT, relative), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


@unittest.skipIf(EngraveLayerComboBox is None, "PyQt6 non importable ici")
class EngraveLayerComboTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        combo = EngraveLayerComboBox()
        self.addCleanup(combo.deleteLater)
        return combo

    def test_lists_only_engraving_layers_in_order(self):
        combo = self.make()
        combo.set_layers(LAYERS, "e2")
        self.assertEqual([combo.itemText(i) for i in range(combo.count())], ["Gravure", "Photo bois"])
        self.assertEqual(combo.layer_id(), "e2")

    def test_unknown_current_layer_shows_the_first_engraving_layer(self):
        combo = self.make()
        combo.set_layers(LAYERS, "c")
        self.assertEqual(combo.layer_id(), "e1")

    def test_without_engraving_layer_it_is_empty_and_disabled(self):
        combo = self.make()
        combo.set_layers([Layer("c", "Coupe", CUT)], "c")
        self.assertFalse(combo.isEnabled())
        self.assertIsNone(combo.layer_id())

    def test_filling_the_list_does_not_emit_but_a_user_choice_does(self):
        combo = self.make()
        got = []
        combo.layer_selected.connect(got.append)
        combo.set_layers(LAYERS, "e1")
        self.assertEqual(got, [])
        combo.activated.emit(1)
        self.assertEqual(got, ["e2"])

    def test_the_panel_relays_the_choice(self):
        panel = ImageSettingsPanel()
        self.addCleanup(panel.deleteLater)
        got = []
        panel.engrave_layer_changed.connect(got.append)
        panel.engrave_layer_combo.set_layers(LAYERS, "e1")
        panel.engrave_layer_combo.activated.emit(1)
        self.assertEqual(got, ["e2"])


class WiringTests(unittest.TestCase):
    def test_window_is_subscribed_and_list_is_refreshed(self):
        main = read("main_window.py")
        self.assertIn("settings.engrave_layer_changed.connect(self._on_engrave_layer_chosen)", main)
        self.assertIn("self._refresh_engrave_layer_combo()", main)
        mixin = read("vector_editing_mixin.py")
        self.assertIn("def _on_engrave_layer_chosen(self, layer_id):", mixin)
        self.assertIn("self._refresh_engrave_layer_combo()", mixin)

    def test_translations_exist_in_all_languages(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("tr_data", os.path.join(ROOT, "i18n", "translations.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # dictionnaire pur : pas besoin de Qt
        TRANSLATIONS = module.TRANSLATIONS
        for key in ("img.engrave_layer", "img.engrave_layer_tip", "img.engrave_layer_none"):
            self.assertEqual(sorted(TRANSLATIONS[key]), ["de", "en", "es", "fr"], key)
            self.assertTrue(all(TRANSLATIONS[key].values()), key)


if __name__ == "__main__":
    unittest.main()
