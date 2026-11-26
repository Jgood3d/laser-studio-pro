"""Surbalayage et commande laser (M4 dynamique / M3 constante) propres à chaque calque."""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL, layer_laser_cmd, layer_overscan_enabled
    from laser_studio.models.layers import LAYER_LASER_CMDS, LaserLayer, LayersModel, validated_settings
    HAS_MODEL = True
except ImportError:                       # PyQt6 non importable
    HAS_MODEL = False

try:
    from laser_studio.gcode.vector import build_vector_layers_gcode
    HAS_BUILD = callable(build_vector_layers_gcode) and not str(type(build_vector_layers_gcode)).endswith("MagicMock'>")
except ImportError:
    HAS_BUILD = False

try:
    import numpy as np
    from laser_studio.controllers.workers import AdvancedGCodeWorker
    HAS_WORKER = True
except ImportError:
    HAS_WORKER = False

RECT = [(5, 5), (15, 5), (15, 7), (5, 7), (5, 5)]


@unittest.skipUnless(HAS_MODEL, "modèle des calques non importable ici")
class LayerSettingsTests(unittest.TestCase):
    def test_new_layer_follows_the_global_settings(self):
        layer = LaserLayer()
        self.assertTrue(layer.overscan)
        self.assertEqual(layer.laser_cmd, "")
        self.assertEqual(LAYER_LASER_CMDS, ("", "M4", "M3"))

    def test_settings_are_converted_and_checked(self):
        self.assertEqual(validated_settings({"laser_cmd": " m3 ", "overscan": 0}), {"laser_cmd": "M3", "overscan": False})
        self.assertEqual(validated_settings({"laser_cmd": ""}), {"laser_cmd": ""})
        # Une commande inconnue est ignorée (le calque garde la sienne).
        self.assertEqual(validated_settings({"laser_cmd": "M7"}), {})
        self.assertEqual(validated_settings({"laser_cmd": "M7"}, LaserLayer(laser_cmd="M4")), {"laser_cmd": "M4"})

    def test_model_update_changes_and_notifies(self):
        model = LayersModel()
        layer = model.layers[0]
        seen = []
        model.layer_changed.connect(lambda lid, changes: seen.append((lid, dict(changes))))
        model.update(layer.id, overscan=False, laser_cmd="M3")
        self.assertFalse(layer.overscan)
        self.assertEqual(layer.laser_cmd, "M3")
        self.assertEqual(len(seen), 1)
        self.assertEqual(set(seen[0][1]), {"overscan", "laser_cmd"})

    def test_settings_survive_a_save_and_a_reload(self):
        layer = LaserLayer(overscan=False, laser_cmd="M3")
        again = LaserLayer.from_dict(layer.to_dict())
        self.assertEqual((again.overscan, again.laser_cmd), (False, "M3"))

    def test_old_project_without_the_settings_keeps_the_defaults(self):
        old = LaserLayer().to_dict()
        old.pop("overscan"), old.pop("laser_cmd")
        layer = LaserLayer.from_dict(old)
        self.assertEqual((layer.overscan, layer.laser_cmd), (True, ""))

    def test_resolution_helpers(self):
        self.assertTrue(layer_overscan_enabled({"overscan": True}, True))
        self.assertFalse(layer_overscan_enabled({"overscan": False}, True))
        self.assertFalse(layer_overscan_enabled({"overscan": True}, False))        # le réglage global reste maître
        self.assertTrue(layer_overscan_enabled({}, True))                          # ancien calque : suit le global
        self.assertTrue(layer_overscan_enabled(None, True))                        # pas de calque de gravure
        self.assertEqual(layer_laser_cmd({"laser_cmd": "M3"}, "M4"), "M3")
        self.assertEqual(layer_laser_cmd({"laser_cmd": ""}, "M4"), "M4")
        self.assertEqual(layer_laser_cmd({}, "M3"), "M3")
        self.assertEqual(layer_laser_cmd(LaserLayer(laser_cmd="M4"), "M3"), "M4")
        self.assertEqual(layer_laser_cmd(None, "M4"), "M4")


@unittest.skipUnless(HAS_BUILD and HAS_MODEL, "build_vector_layers_gcode non disponible ici")
class VectorGcodeTests(unittest.TestCase):
    def layer(self, mode=MODE_FILL, **kw):
        d = {"name": "L", "mode": mode, "power": 50.0, "speed": 1000, "passes": 1, "line_interval": 1.0}
        d.update(kw)
        return d

    def build(self, layers, global_cmd="M4", overscan=2.0):
        data = {f"l{i}": {"layer": layer, "polygons": [RECT]} for i, layer in enumerate(layers)}
        return build_vector_layers_gcode(data, 0.0, 0.0, 100.0, global_cmd, 1000, overscan_dist=overscan)[0]

    @staticmethod
    def xs(gcode):
        return [float(m) for line in gcode for m in re.findall(r"X(-?[\d.]+)", line.split(";")[0])]

    def test_overscan_applies_by_default(self):
        self.assertEqual((min(self.xs(self.build([self.layer()]))), max(self.xs(self.build([self.layer()])))), (3.0, 17.0))

    def test_overscan_can_be_turned_off_for_one_layer(self):
        xs = self.xs(self.build([self.layer(overscan=False)]))
        self.assertEqual((min(xs), max(xs)), (5.0, 15.0))

    def test_overscan_is_per_layer(self):
        gcode = self.build([self.layer(overscan=False, name="A"), self.layer(overscan=True, name="B")])
        first, second = "\n".join(gcode).split("; --- CALQUE 'B'")
        self.assertEqual(min(self.xs(first.splitlines())), 5.0)
        self.assertEqual(min(self.xs(second.splitlines())), 3.0)

    def test_no_overscan_when_the_global_distance_is_zero(self):
        xs = self.xs(self.build([self.layer(overscan=True)], overscan=0.0))
        self.assertEqual((min(xs), max(xs)), (5.0, 15.0))

    def test_layer_command_overrides_the_global_one(self):
        gcode = "\n".join(self.build([self.layer(laser_cmd="M3")], global_cmd="M4"))
        self.assertIn("M3 S0", gcode)                     # laser en M3, puissance portée par les G1
        self.assertIn("S500", gcode)
        self.assertNotIn("M4", gcode)

    def test_auto_follows_the_global_command(self):
        gcode = "\n".join(self.build([self.layer(laser_cmd="")], global_cmd="M3"))
        self.assertIn("M3 S0", gcode)
        self.assertNotIn("M4", gcode)

    def test_each_layer_uses_its_own_command(self):
        gcode = self.build([self.layer(laser_cmd="M4", name="A"), self.layer(laser_cmd="M3", name="B")], global_cmd="M4")
        text = "\n".join(gcode)
        first, second = text.split("; --- CALQUE 'B'")
        self.assertIn("M4 S0", first)
        self.assertNotIn("M3", first)
        self.assertIn("M3 S0", second)
        self.assertNotIn("M4", second)

    def test_cut_layer_command(self):
        gcode = "\n".join(self.build([self.layer(mode=MODE_CUT, laser_cmd="M3", power=80.0)], global_cmd="M4"))
        self.assertIn("M3 S0", gcode)
        self.assertIn("S800", gcode)
        self.assertNotIn("M4", gcode)


@unittest.skipUnless(HAS_WORKER, "worker de génération non disponible ici")
class ImageGcodeTests(unittest.TestCase):
    PARAMS = dict(width_mm=20.0, height_mm=2.0, origin_pos="Bas-gauche", offset_x=10.0, offset_y=10.0,
                  speed_engrave=1000, power_engrave=50.0, enable_cut=False, speed_cut=300, power_cut=90.0,
                  passes_cut=1, laser_cmd="M4", algo="Noir et Blanc", s_max=1000, homing=False,
                  enable_overscan=True, overscan_mode="Distance (mm)", overscan_dist=2.0, overscan_pct=5.0,
                  start_gcode="", end_gcode="", scan_offset_mm=0.0, safe_cut_order=True)

    def run_worker(self, **overrides):
        params = dict(self.PARAMS, **overrides)
        array = np.full((2, 20), 255, dtype=np.uint8)
        array[:, 5:15] = 0                                   # 10 mm gravés au milieu de chaque ligne
        out = []
        worker = AdvancedGCodeWorker(array, params)
        worker.finished.connect(lambda gcode, *_: out.append(gcode))
        worker.error.connect(lambda message: self.fail(message))
        worker.run()
        self.assertTrue(out, "aucun G-Code généré")
        return out[0].splitlines()

    @staticmethod
    def xs(gcode):
        # Hors « G0 X0 Y0 » : le retour à l'origine du G-Code de fin n'est pas du balayage.
        return [float(line.split("X")[1].split()[0]) for line in gcode
                if line.startswith(("G0 X", "G1 X")) and not line.startswith("G0 X0 Y0")]

    def test_image_follows_the_global_settings_without_overrides(self):
        gcode = self.run_worker()
        self.assertTrue(any(line.startswith("M4 S0") for line in gcode))
        self.assertLess(min(self.xs(gcode)), 25.0)           # les pixels gravés commencent à X25 : surbalayage présent

    def test_engrave_layer_without_overscan_disables_it_for_the_image(self):
        with_overscan = self.xs(self.run_worker())
        without = self.xs(self.run_worker(image_overscan=False))
        # Balayage plus large des deux côtés (l'image est aussi décalée de la marge de surbalayage).
        self.assertGreater(max(with_overscan) - min(with_overscan), max(without) - min(without))
        self.assertGreater(max(with_overscan), max(without))

    def test_engrave_layer_command_replaces_the_global_one_for_the_image(self):
        gcode = self.run_worker(image_laser_cmd="M3")
        text = "\n".join(gcode)
        self.assertIn("M3", text)
        self.assertNotIn("M4", text)

    def test_m4_is_switched_on_once_when_the_image_layer_is_dynamic(self):
        gcode = self.run_worker(laser_cmd="M3", image_laser_cmd="M4")
        self.assertEqual(sum(1 for line in gcode if line.startswith("M4 S0")), 1)


if __name__ == "__main__":
    unittest.main()
