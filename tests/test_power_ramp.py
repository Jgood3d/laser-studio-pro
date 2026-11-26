"""Rampe de puissance par passe (calques de contour) : calcul, G-Code et réglages du calque."""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from laser_studio.gcode.vector import _pass_power, build_vector_layers_gcode
    from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL, MODE_MARK, MODE_PERF
    from laser_studio.models.layers import LaserLayer, LayersModel, validated_settings
    HAS_MODEL = True
except ImportError:                       # PyQt6 non importable
    HAS_MODEL = False

SQUARE = [(0, 0), (40, 0), (40, 40), (0, 40), (0, 0)]
LINE = [(0, 0), (30, 0)]


def _data(mode, polygons, **layer):
    base = {"name": "L", "mode": mode, "speed": 300, "power": 40.0, "passes": 4, "line_interval": 0.1}
    base.update(layer)
    return {"layer": base, "polygons": polygons, "polygon_groups": [polygons]}


def _build(data):
    """(G-Code, durée, puissances) pour S-Max = 1000 : S vaut alors dix fois la puissance en %."""
    return build_vector_layers_gcode({"a": data}, 0.0, 0.0, 100.0, "M4", 1000)


def _burn_powers(gcode):
    """Valeur S de chaque changement de puissance sur un déplacement gravé (G1). G1 et S sont modaux : une
    ligne « X40 Y0 S600 » est un G1 qui passe la puissance à 600."""
    out, motion = [], None
    for raw in gcode:
        words = re.findall(r"([A-Z])(-?\d+\.?\d*)", raw.split(";")[0])
        moved = False
        power = None
        for letter, value in words:
            if letter == "G" and float(value) in (0, 1):
                motion = int(float(value))
            elif letter in "XY":
                moved = True
            elif letter == "S":
                power = int(float(value))
        if moved and motion == 1 and power is not None:
            out.append(power)
    return out


@unittest.skipUnless(HAS_MODEL, "génération du G-Code non importable ici")
class PassPowerTests(unittest.TestCase):
    def test_power_goes_linearly_from_the_layer_to_the_final_power(self):
        layer = {"power": 40.0, "ramp": True, "ramp_power": 100.0}
        self.assertEqual([round(_pass_power(layer, k, 4), 6) for k in range(4)], [40.0, 60.0, 80.0, 100.0])

    def test_ramp_can_go_down(self):
        layer = {"power": 100.0, "ramp": True, "ramp_power": 40.0}
        self.assertEqual([round(_pass_power(layer, k, 4), 6) for k in range(4)], [100.0, 80.0, 60.0, 40.0])

    def test_unchecked_ramp_keeps_the_layer_power(self):
        layer = {"power": 40.0, "ramp": False, "ramp_power": 100.0}
        self.assertEqual([_pass_power(layer, k, 4) for k in range(4)], [40.0] * 4)

    def test_a_single_pass_is_never_ramped(self):
        self.assertEqual(_pass_power({"power": 40.0, "ramp": True, "ramp_power": 100.0}, 0, 1), 40.0)

    def test_old_layer_without_ramp_settings(self):
        self.assertEqual(_pass_power({"power": 40.0}, 2, 4), 40.0)

    def test_unusable_final_power_keeps_the_layer_power(self):
        self.assertEqual(_pass_power({"power": 40.0, "ramp": True, "ramp_power": "abc"}, 3, 4), 40.0)


@unittest.skipUnless(HAS_MODEL, "génération du G-Code non importable ici")
class RampGcodeTests(unittest.TestCase):
    def test_each_pass_has_its_own_power(self):
        gcode, _, _ = _build(_data(MODE_CUT, [SQUARE], ramp=True, ramp_power=100.0))
        self.assertEqual(_burn_powers(gcode), [400, 600, 800, 1000])

    def test_each_pass_is_labelled_with_its_power(self):
        gcode, _, _ = _build(_data(MODE_CUT, [SQUARE], ramp=True, ramp_power=100.0))
        self.assertTrue(any("; Passe 2/4 (puissance 60 %)" in line for line in gcode))
        self.assertTrue(any("; Passe 4/4 (puissance 100 %)" in line for line in gcode))

    def test_without_ramp_every_pass_keeps_the_layer_power_and_the_old_label(self):
        gcode, _, _ = _build(_data(MODE_CUT, [SQUARE], ramp=False, ramp_power=100.0))
        self.assertEqual(set(_burn_powers(gcode)), {400})          # S est modal : écrit une seule fois
        self.assertTrue(any(line == "; Passe 2/4" for line in gcode))

    def test_one_pass_is_not_ramped(self):
        gcode, _, _ = _build(_data(MODE_CUT, [SQUARE], passes=1, ramp=True, ramp_power=100.0))
        self.assertEqual(_burn_powers(gcode), [400])
        self.assertFalse(any("puissance" in line and line.startswith("; Passe") for line in gcode))

    def test_perforation_and_marking_layers_are_ramped_too(self):
        for mode in (MODE_PERF, MODE_MARK):
            gcode, _, _ = _build(_data(mode, [LINE], passes=2, ramp=True, ramp_power=80.0, perf_dash=40.0, perf_gap=1.0))
            self.assertEqual(sorted(set(_burn_powers(gcode))), [400, 800], mode)

    def test_fill_layers_ignore_the_ramp(self):
        gcode, _, _ = _build(_data(MODE_FILL, [SQUARE], passes=2, ramp=True, ramp_power=100.0))
        self.assertEqual(set(_burn_powers(gcode)), {400})

    def test_average_power_follows_the_ramp(self):
        _, _, samples = _build(_data(MODE_CUT, [SQUARE], ramp=True, ramp_power=100.0))
        self.assertEqual(sorted(set(round(s) for s in samples)), [40, 60, 80, 100])


@unittest.skipUnless(HAS_MODEL, "modèle des calques non importable ici")
class RampLayerSettingsTests(unittest.TestCase):
    def test_new_layer_has_the_ramp_off_with_a_default_final_power(self):
        layer = LaserLayer()
        self.assertFalse(layer.ramp)
        self.assertEqual(layer.ramp_power, 100.0)

    def test_settings_are_converted_and_clamped(self):
        self.assertEqual(validated_settings({"ramp": 1, "ramp_power": "70"}), {"ramp": True, "ramp_power": 70.0})
        self.assertEqual(validated_settings({"ramp_power": 0})["ramp_power"], 1.0)
        self.assertEqual(validated_settings({"ramp_power": 500})["ramp_power"], 100.0)
        self.assertEqual(validated_settings({"ramp_power": "abc"}), {})
        self.assertEqual(validated_settings({"ramp_power": float("nan")}), {})

    def test_settings_survive_a_save_and_a_reload(self):
        model = LayersModel()
        model.update(model.layers[1].id, ramp=True, ramp_power=65.0)
        reloaded = LayersModel()
        reloaded.load_list(model.to_list())
        cut = next(layer for layer in reloaded.layers if layer.role == "cut")
        self.assertEqual((cut.ramp, cut.ramp_power), (True, 65.0))

    def test_project_saved_before_the_ramp_loads_with_the_ramp_off(self):
        saved = [{k: v for k, v in layer.items() if k not in ("ramp", "ramp_power")}
                 for layer in LayersModel().to_list()]
        model = LayersModel()
        model.load_list(saved)
        self.assertTrue(all(not layer.ramp for layer in model.layers))


if __name__ == "__main__":
    unittest.main()
