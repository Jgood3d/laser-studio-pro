"""Mémoire des calques par machine (controllers/layer_memory), sans Qt."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from controllers.layer_memory import (
        apply_saved_layers,
        coerce_layer_settings,
    )
    from vector_layers import LaserLayer, LayerManager
except ImportError:  # PyQt6 manquant (vector_layers)
    LayerManager = None


@unittest.skipIf(LayerManager is None, "vector_layers non importable ici")
class LayerMemoryTests(unittest.TestCase):
    def test_unusable_values_are_ignored_or_reset(self):
        layer = LaserLayer()
        layer.power = 42.0
        coerce_layer_settings(layer, {"power": "abc", "speed": "1200"})
        self.assertEqual((layer.power, layer.speed), (42.0, 1200))
        coerce_layer_settings(layer, {"power": "abc"}, reset_invalid=True)
        self.assertEqual(layer.power, LaserLayer().power)

    def test_without_saved_layers_nothing_changes(self):
        manager = LayerManager()
        before = manager.to_list()
        self.assertFalse(apply_saved_layers(manager, None))
        self.assertFalse(apply_saved_layers(manager, ["pas un dict"]))
        self.assertEqual(manager.to_list(), before)

    def test_settings_follow_layers_by_identifier(self):
        manager = LayerManager()
        first = manager.layers[0]
        saved = [{"id": first.id, "speed": 777}]
        self.assertTrue(apply_saved_layers(manager, saved, full=False))
        self.assertEqual(manager.layers[0].speed, 777)


if __name__ == "__main__":
    unittest.main()
