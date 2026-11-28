"""Issues #119 (une seule mise en forme des durées, une seule marge) et #118 (commande laser de la
découpe SVG autour de l'image)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from laser_studio.i18n import get_current_language, set_language
    from laser_studio.i18n.durations import duration_text
    from job_fakes import memory_preferences
except ImportError:  # PyQt6 manquant (préférences)
    duration_text = None


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


if __name__ == "__main__":
    unittest.main()
