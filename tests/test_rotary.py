"""Axe rotatif : conversion du G-Code à plat vers la machine, position de la tête et réglages GRBL."""
import math
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.gcode.rotary import (  # noqa: E402
    AXES, DRIVES, RotaryConfig, RotaryError, machine_gcode, machine_lines, surface_y,
)

try:
    from laser_studio.controllers.engraver import EngraverController
    HAS_ENGRAVER = True
except ImportError:                       # PyQt6 ou pyserial non importables
    HAS_ENGRAVER = False

try:
    from laser_studio.gcode.vector import build_vector_layers_gcode
    from laser_studio.models.grbl import ROTARY_AXES, ROTARY_DRIVES, GrblConfig
    from laser_studio.models.layer_modes import MODE_CUT
    HAS_MODEL = True
except ImportError:                       # PyQt6 non importable
    HAS_MODEL = False

CHUCK_Y = RotaryConfig(enabled=True, axis="Y", drive="chuck", object_mm=80.0, mm_per_turn=360.0)
ROLLER_A = RotaryConfig(enabled=True, axis="A", drive="roller", object_mm=80.0, roller_mm=20.0)
FACTOR_Y = 360.0 / (math.pi * 80.0)


def lines(text):
    """Lignes du G-Code converti, sans l'en-tête de commentaire."""
    return [line for line in text.splitlines() if not line.startswith("; Axe rotatif")]


def words(line):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"([A-Z])(-?\d+\.?\d*)", line.split(";")[0])}


class ConfigTests(unittest.TestCase):
    def test_factor_for_a_chuck_on_y(self):
        self.assertAlmostEqual(CHUCK_Y.factor, FACTOR_Y)
        self.assertAlmostEqual(CHUCK_Y.circumference_mm, math.pi * 80.0)

    def test_chuck_depends_on_the_object_and_rollers_on_the_rollers(self):
        chuck = RotaryConfig(enabled=True, drive="chuck", object_mm=100.0, roller_mm=20.0, mm_per_turn=360.0)
        rollers = RotaryConfig(enabled=True, drive="roller", object_mm=100.0, roller_mm=20.0, mm_per_turn=360.0)
        self.assertAlmostEqual(chuck.factor, 360.0 / (math.pi * 100.0))
        self.assertAlmostEqual(rollers.factor, 360.0 / (math.pi * 20.0))      # le diamètre de l'objet n'intervient pas
        self.assertAlmostEqual(rollers.circumference_mm, math.pi * 100.0)     # mais c'est lui qui limite le motif

    def test_axis_a_is_in_degrees_per_mm(self):
        self.assertAlmostEqual(ROLLER_A.factor, 360.0 / (math.pi * 20.0))
        self.assertAlmostEqual(RotaryConfig(enabled=True, axis="A", object_mm=100.0).factor, 360.0 / (math.pi * 100.0))

    def test_a_disabled_or_unusable_config_is_inactive(self):
        self.assertFalse(RotaryConfig().active)
        self.assertFalse(RotaryConfig(enabled=True, object_mm=0.0).active)
        self.assertFalse(RotaryConfig(enabled=True, mm_per_turn=0.0).active)
        self.assertTrue(RotaryConfig(enabled=True, axis="A", mm_per_turn=0.0).active)   # sans effet en degrés

    def test_choices_match_the_settings_model(self):
        self.assertEqual(AXES, ("Y", "A"))
        self.assertEqual(DRIVES, ("chuck", "roller"))


class ConversionTests(unittest.TestCase):
    def test_inactive_config_returns_the_text_untouched(self):
        text = "G90\nG1 X10 Y5 F1000\n"
        self.assertEqual(machine_gcode(text, None), text)
        self.assertEqual(machine_gcode(text, RotaryConfig()), text)

    def test_y_is_scaled_on_the_y_axis(self):
        out = lines(machine_gcode("G90\nG0 X10 Y10\n", CHUCK_Y))
        self.assertEqual(out[1], f"G0 X10 Y{FACTOR_Y * 10:.4f}".rstrip("0"))

    def test_y_becomes_a_on_a_dedicated_axis(self):
        out = lines(machine_gcode("G90\nG0 X10 Y10\n", ROLLER_A))
        self.assertIn("A", words(out[1]))
        self.assertNotIn("Y", words(out[1]))
        self.assertAlmostEqual(words(out[1])["A"], ROLLER_A.factor * 10, places=3)

    def test_x_only_lines_comments_and_settings_are_left_alone(self):
        text = "$H\n; commentaire Y10\nG21 ; Unités mm\nG90\nM4 S0\nG0 X10 ; Y50 dans un commentaire\n"
        out = lines(machine_gcode(text, CHUCK_Y))
        self.assertEqual(out, text.splitlines())

    def test_header_comment_describes_the_conversion(self):
        first = machine_gcode("G90\n", CHUCK_Y).splitlines()[0]
        self.assertTrue(first.startswith("; Axe rotatif : axe Y, mandrin, objet Ø 80 mm"))

    def test_streamed_text_keeps_the_lines_of_the_flat_gcode(self):
        # La reprise d'un job interrompu se repère par numéro de ligne dans le G-Code à plat.
        text = "G90\nM4 S0\nG0 X0 Y0\nG1 X10 Y10 S500 F1000\nX20 Y30\nM5\n"
        sent = machine_gcode(text, CHUCK_Y, header=False)
        self.assertEqual(len(sent.splitlines()), len(text.splitlines()))
        self.assertFalse(sent.startswith("; Axe rotatif"))
        self.assertTrue(machine_gcode(text, CHUCK_Y).startswith("; Axe rotatif"))   # le fichier enregistré l'a

    def test_factor_one_changes_nothing(self):
        same = RotaryConfig(enabled=True, axis="Y", object_mm=100.0, mm_per_turn=math.pi * 100.0)
        text = "G90\nG0 X1 Y2\nG1 X5 Y5 F1000 S500\nX9 Y9\n"
        self.assertEqual(lines(machine_gcode(text, same)), text.splitlines())

    def test_every_y_is_converted_and_round_trips(self):
        text = "G90\nG0 X0 Y0\nG1 X10 Y12.5 F800\nX20 Y-3.25\nG0 X0 Y40\n"
        out = lines(machine_gcode(text, CHUCK_Y))
        before = [words(line).get("Y") for line in text.splitlines()]
        after = [words(line).get("Y") for line in out]
        for original, converted in zip(before, after):
            if original is not None:
                self.assertAlmostEqual(converted / FACTOR_Y, original, places=3)

    def test_relative_moves_are_scaled_too(self):
        out = lines(machine_gcode("G91\nG1 X0 Y10 F1000\n", CHUCK_Y))
        self.assertAlmostEqual(words(out[1])["Y"], FACTOR_Y * 10, places=3)

    def test_arcs_and_inches_are_refused(self):
        with self.assertRaises(RotaryError):
            machine_gcode("G90\nG2 X5 Y5 I1 J0 F500\n", CHUCK_Y)
        with self.assertRaises(RotaryError):
            machine_gcode("G20\nG1 X1 Y1\n", CHUCK_Y)

    def test_frame_commands(self):
        out = machine_lines(["G0 X0 Y0", "G0 X40 Y0", "G0 X40 Y30"], CHUCK_Y)
        self.assertEqual(len(out), 3)
        self.assertAlmostEqual(words(out[2])["Y"], FACTOR_Y * 30, places=3)
        self.assertEqual(machine_lines(["G0 X1 Y1"], None), ["G0 X1 Y1"])


class FeedTests(unittest.TestCase):
    def test_a_move_along_x_keeps_its_feed(self):
        out = lines(machine_gcode("G90\nG1 X10 Y0 F1000\nX20 Y0\n", CHUCK_Y))
        self.assertEqual(words(out[1])["F"], 1000.0)
        self.assertNotIn("F", words(out[2]))                      # F est modal : inutile de le répéter

    def test_a_move_along_y_runs_faster_by_the_factor(self):
        out = lines(machine_gcode("G90\nG1 X0 Y0 F1000\nX0 Y10\n", CHUCK_Y))
        self.assertAlmostEqual(words(out[2])["F"], 1000.0 * FACTOR_Y, delta=0.1)

    def test_a_diagonal_keeps_the_surface_speed(self):
        out = lines(machine_gcode("G90\nG1 X0 Y0 F1000\nX10 Y10\n", CHUCK_Y))
        expected = 1000.0 * math.hypot(10, 10 * FACTOR_Y) / math.hypot(10, 10)
        self.assertAlmostEqual(words(out[2])["F"], expected, delta=0.1)

    def test_the_feed_is_restored_after_a_y_move(self):
        out = lines(machine_gcode("G90\nG1 X0 Y0 F1000\nX0 Y10\nX10 Y10\n", CHUCK_Y))
        self.assertAlmostEqual(words(out[3])["F"], 1000.0, delta=0.1)   # retour à la vitesse d'origine

    def test_rapid_moves_get_no_feed(self):
        out = lines(machine_gcode("G90\nG0 X10 Y10\n", CHUCK_Y))
        self.assertNotIn("F", words(out[1]))

    def test_the_comment_stays_after_an_added_feed(self):
        out = lines(machine_gcode("G90\nG1 X0 Y0 F1000\nX0 Y10 ; trait\n", CHUCK_Y))
        self.assertTrue(out[2].endswith("; trait"))
        self.assertIn("F", words(out[2]))


class HeadPositionTests(unittest.TestCase):
    def test_surface_y_is_the_inverse_of_the_conversion(self):
        self.assertAlmostEqual(surface_y(FACTOR_Y * 25.0, CHUCK_Y), 25.0)

    def test_no_conversion_without_rotary_or_on_a_dedicated_axis(self):
        self.assertEqual(surface_y(12.0, None), 12.0)
        self.assertEqual(surface_y(12.0, RotaryConfig()), 12.0)
        self.assertEqual(surface_y(12.0, ROLLER_A), 12.0)         # A n'est pas rapporté dans Y


@unittest.skipUnless(HAS_ENGRAVER, "contrôleur du graveur non importable ici")
class ResumeHeadTests(unittest.TestCase):
    """Reprise d'un job : la position de la tête rapportée par la machine est reconvertie à plat."""

    class Fake:
        def __init__(self, config):
            self._config = config

        def _rotary_config(self):
            return self._config

    def head(self, config, x, y):
        return EngraverController._surface_head(self.Fake(config), x, y)

    def test_without_rotary_the_position_is_unchanged(self):
        self.assertEqual(self.head(RotaryConfig(), 12.0, 7.0), (12.0, 7.0))

    def test_on_a_y_rotary_y_is_converted_back(self):
        x, y = self.head(CHUCK_Y, 12.0, FACTOR_Y * 20.0)
        self.assertEqual(x, 12.0)
        self.assertAlmostEqual(y, 20.0)

    def test_on_a_dedicated_axis_the_position_is_unknown(self):
        self.assertIsNone(self.head(ROLLER_A, 12.0, 0.0))        # Y n'y bouge pas : jamais une fausse position


@unittest.skipUnless(HAS_MODEL, "génération du G-Code non importable ici")
class JobIntegrationTests(unittest.TestCase):
    def _job(self):
        square = [(0, 0), (30, 0), (30, 30), (0, 30), (0, 0)]
        layer = {"name": "L", "mode": MODE_CUT, "speed": 600, "power": 50.0, "passes": 1, "line_interval": 0.1}
        data = {"layer": layer, "polygons": [square], "polygon_groups": [[square]]}
        return "\n".join(build_vector_layers_gcode({"a": data}, 0.0, 0.0, 100.0, "M4", 1000)[0])

    def test_a_generated_job_converts_without_error(self):
        out = machine_gcode(self._job(), CHUCK_Y)
        ys = [words(line)["Y"] for line in out.splitlines() if "Y" in words(line)]
        self.assertAlmostEqual(max(ys), FACTOR_Y * 30.0, places=3)

    def test_a_generated_job_on_axis_a_has_no_y_left(self):
        out = machine_gcode(self._job(), ROLLER_A)
        self.assertFalse(any("Y" in words(line) for line in out.splitlines()))
        self.assertTrue(any("A" in words(line) for line in out.splitlines()))


@unittest.skipUnless(HAS_MODEL, "modèle GRBL non importable ici")
class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        grbl = GrblConfig()
        self.assertFalse(grbl.rotary_enabled)
        self.assertEqual((grbl.rotary_axis, grbl.rotary_drive), ("Y", "chuck"))
        self.assertEqual((grbl.rotary_object_mm, grbl.rotary_roller_mm, grbl.rotary_mm_per_turn), (60.0, 20.0, 360.0))

    def test_choices_match_the_conversion_module(self):
        self.assertEqual(ROTARY_AXES, AXES)
        self.assertEqual(ROTARY_DRIVES, DRIVES)

    def test_an_unknown_axis_is_ignored(self):
        grbl = GrblConfig()
        grbl.update(rotary_axis="Z")
        self.assertEqual(grbl.rotary_axis, "Y")

    def test_the_machine_profile_keeps_the_dimensions_but_not_the_activation(self):
        self.assertNotIn("rotary_enabled", GrblConfig.PROFILE_FIELDS)
        for name in ("rotary_axis", "rotary_drive", "rotary_object_mm", "rotary_roller_mm", "rotary_mm_per_turn"):
            self.assertIn(name, GrblConfig.MECHANICAL_FIELDS)

    def test_profile_round_trip(self):
        grbl = GrblConfig()
        grbl.update(rotary_axis="A", rotary_drive="roller", rotary_object_mm=75.0, rotary_enabled=True)
        saved = grbl.to_profile()
        other = GrblConfig()
        other.apply_profile(saved)
        self.assertEqual((other.rotary_axis, other.rotary_drive, other.rotary_object_mm), ("A", "roller", 75.0))
        self.assertFalse(other.rotary_enabled)                    # jamais repris d'un profil

    def test_config_from_settings(self):
        grbl = GrblConfig()
        grbl.update(rotary_enabled=True, rotary_axis="A", rotary_object_mm=90.0)
        config = RotaryConfig.from_settings(grbl)
        self.assertTrue(config.active)
        self.assertEqual((config.axis, config.object_mm), ("A", 90.0))


if __name__ == "__main__":
    unittest.main()
