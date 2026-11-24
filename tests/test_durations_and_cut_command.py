"""Issues #119 (une seule mise en forme des durées, une seule marge) et #118 (commande laser de la
découpe SVG autour de l'image)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from laser_studio.i18n import get_current_language, set_language
    from laser_studio.i18n.durations import duration_text
    from job_fakes import memory_preferences
except ImportError:  # PyQt6 manquant (préférences)
    duration_text = None
from laser_studio.gcode.svg_cut import svg_cut_gcode  # noqa: E402  (sans Qt)


@unittest.skipIf(duration_text is None, "PyQt6 non importable ici")
class DurationTextTests(unittest.TestCase):
    def setUp(self):
        memory_preferences(self)                      # langue changée sans toucher aux réglages de l'utilisateur
        previous = get_current_language()
        self.addCleanup(set_language, previous)
        set_language("fr")

    def test_one_format_everywhere(self):
        self.assertEqual(duration_text(46), "46 s")
        self.assertEqual(duration_text(192), "3 min 12 s")
        self.assertEqual(duration_text(65), "1 min 05 s")
        self.assertEqual(duration_text(7503), "2 h 05 min")
        self.assertEqual(duration_text(0), "0 s")

    def test_estimate_uses_the_same_format(self):
        try:
            from laser_studio.controllers.job import estimate_duration_text
        except ImportError:
            self.skipTest("PyQt6 non importable ici")
        self.assertEqual(estimate_duration_text(192), duration_text(192))


class SvgCutCommandTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 L 10 0 L 10 10 Z"/></svg>')
        self.addCleanup(os.remove, self.path)

    def lines(self, **params):
        base = {"height_mm": 10.0, "s_max": 255, "speed_cut": 300, "power_cut": 10.0, "passes_cut": 1}
        base.update(params)
        return svg_cut_gcode(self.path, base, 0.0, 0.0)[0]

    def test_follows_the_cut_layer_command_and_rounds_the_power(self):
        self.assertIn("M4 S26", self.lines(cut_laser_cmd="M4"))         # 10 % de 255 : S26, plus S25
        self.assertIn("M3 S26", self.lines(cut_laser_cmd="M3"))
        self.assertIn("M3 S26", self.lines())                           # sans réglage : M3, comme avant


if __name__ == "__main__":
    unittest.main()
