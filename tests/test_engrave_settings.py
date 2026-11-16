"""Gravure d'une image : vitesse et puissance LUES dans le calque de gravure
(plus de copie séparée qui pourrait diverger du calque).
Découpe de l'ancien mode SVG : vitesse, puissance et passes."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from laser_studio.gcode_generation_mixin import GcodeGenerationMixin
    from laser_studio.vector_editing_mixin import VectorEditingMixin
    from laser_studio.models.layers import LayersModel
except ImportError:  # PyQt6... manquant
    GcodeGenerationMixin = None


@unittest.skipIf(GcodeGenerationMixin is None, "PyQt6 non importable ici")
class EngraveSettingsTests(unittest.TestCase):
    def make(self):
        class Fake(GcodeGenerationMixin, VectorEditingMixin):
            pass
        f = Fake.__new__(Fake)
        f.layer_manager = LayersModel()
        f.messages = []
        f.show_status_message = f.messages.append
        return f

    def fill_layer(self, f):
        return next(l for l in f.layer_manager.layers if l.mode == "Gravure Remplie")

    def test_values_are_whole_numbers_within_bounds(self):
        f = self.make()
        f.set_engrave_settings(1234.7, 55.2)
        self.assertEqual((f.engrave_speed, f.engrave_power), (1234, 55))
        f.set_engrave_settings(5, 150)
        self.assertEqual((f.engrave_speed, f.engrave_power), (10, 100))   # 100 % reste possible

    def test_set_engrave_settings_writes_the_engrave_layer(self):
        f = self.make()
        f.set_engrave_settings(1500, 60)
        fill = self.fill_layer(f)
        self.assertEqual((fill.speed, fill.power), (1500, 60.0))

    def test_cut_values_are_whole_numbers_within_bounds(self):
        f = self.make()
        f.set_cut_settings(250.9, 95.4, 2.7)
        self.assertEqual((f.cut_speed, f.cut_power, f.cut_passes), (250, 95, 2))
        f.set_cut_settings(5, 100, 0)                   # 100 % et 0 passe restent possibles
        self.assertEqual((f.cut_speed, f.cut_power, f.cut_passes), (10, 100, 0))
        f.set_cut_settings(9000, 150, 500)
        self.assertEqual((f.cut_speed, f.cut_power, f.cut_passes), (5000, 100, 99))

    def test_image_uses_the_first_engrave_layer(self):
        f = self.make()
        fill = self.fill_layer(f)
        f.layer_manager.update(fill.id, speed=1500, power=100)
        self.assertEqual(f.layer_manager.engrave_layer(), fill)
        self.assertEqual((f.engrave_speed, f.engrave_power), (1500, 100))
        self.assertEqual(f._engrave_layer_label(), f"{fill.name}  [Gravure Remplie]")

    def test_layer_change_is_seen_without_any_copy(self):
        """Le cas du bug : le calque est modifié (saisie, matériau, profil),
        la génération lit aussitôt la nouvelle valeur."""
        f = self.make()
        fill = self.fill_layer(f)
        f.layer_manager.update(fill.id, speed=1800, power=80)
        f._ensure_engrave_layer_for_image()
        self.assertEqual((f.engrave_speed, f.engrave_power), (1800, 80))
        self.assertEqual(f.messages, [])

    def test_without_engrave_layer_the_first_layer_is_used(self):
        f = self.make()
        for layer in [l for l in f.layer_manager.layers if l.mode == "Gravure Remplie"]:
            f.layer_manager.remove_layer(layer.id)
        self.assertEqual(f.layer_manager.engrave_layer(), f.layer_manager.layers[0])
        f._ensure_engrave_layer_for_image()             # simple message
        self.assertEqual(len(f.messages), 1)


if __name__ == "__main__":
    unittest.main()
