"""Gravure d'une image : vitesse et puissance reprises du calque de gravure.
Découpe de l'ancien mode SVG : vitesse, puissance et passes."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from gcode_generation_mixin import GcodeGenerationMixin
    from vector_editing_mixin import VectorEditingMixin
    from vector_layers import LayerManager
except ImportError:  # PyQt6... manquant
    GcodeGenerationMixin = None


@unittest.skipIf(GcodeGenerationMixin is None, "PyQt6 non importable ici")
class EngraveSettingsTests(unittest.TestCase):
    def make(self):
        class Fake(GcodeGenerationMixin, VectorEditingMixin):
            pass
        f = Fake.__new__(Fake)
        f.layer_manager = LayerManager()
        f.engrave_speed, f.engrave_power, f.engrave_layer_id = 2000, 30, None
        f.messages = []
        f.show_status_message = f.messages.append
        return f

    def test_values_are_whole_numbers_within_bounds(self):
        f = self.make()
        f.set_engrave_settings(1234.7, 55.2)
        self.assertEqual((f.engrave_speed, f.engrave_power), (1234, 55))
        f.set_engrave_settings(5, 150)
        self.assertEqual((f.engrave_speed, f.engrave_power), (10, 100))   # 100 % reste possible

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
        fill = next(l for l in f.layer_manager.layers if l.mode == "Gravure Remplie")
        fill.speed, fill.power = 1500, 100
        f._refresh_engrave_layer()
        f._on_engrave_layer_selected()
        self.assertEqual(f.engrave_layer_id, fill.id)
        self.assertEqual((f.engrave_speed, f.engrave_power), (1500, 100))
        self.assertEqual(f._engrave_layer_label(), f"{fill.name}  [Gravure Remplie]")

    def test_without_engrave_layer_the_first_layer_is_used(self):
        f = self.make()
        for layer in [l for l in f.layer_manager.layers if l.mode == "Gravure Remplie"]:
            f.layer_manager.remove_layer(layer.id)
        f._refresh_engrave_layer()
        self.assertEqual(f.engrave_layer_id, f.layer_manager.layers[0].id)
        f._ensure_engrave_layer_for_image()             # rien à basculer : simple message
        self.assertEqual(len(f.messages), 1)

    def test_ensure_switches_to_an_engrave_layer(self):
        f = self.make()
        cut = next(l for l in f.layer_manager.layers if l.mode == "Découpe")
        f.engrave_layer_id = cut.id
        f._ensure_engrave_layer_for_image()
        layer = f.layer_manager.get(f.engrave_layer_id)
        self.assertEqual(layer.mode, "Gravure Remplie")
        self.assertEqual((f.engrave_speed, f.engrave_power), (int(layer.speed), int(layer.power)))


if __name__ == "__main__":
    unittest.main()
