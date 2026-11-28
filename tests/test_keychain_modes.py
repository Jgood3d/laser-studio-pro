"""Porte-clés prénom : les trois modes (classique, 2 couches, lettres à coller) et leur passage en objets vectoriels.
Demande Qt (contours de texte, soudure) : ignoré sans lui."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtGui import QGuiApplication, QPainterPath
    from laser_studio.vector import importers
    from laser_studio.vector import keychain_generator as kg
    HAS_QT = isinstance(QPainterPath, type) and "stub" not in (QPainterPath.__module__ or "").lower() \
        and callable(getattr(QPainterPath, "simplified", None))
except Exception:  # pragma: no cover - sans Qt
    HAS_QT = False

GAP = 5.0


def x_range(contours):
    xs = [p[0] for c in contours for p in c]
    return min(xs), max(xs)


class ParamsTests(unittest.TestCase):
    @unittest.skipUnless(HAS_QT, "Qt requis")
    def test_modes_are_exclusive(self):
        p = kg.KeychainParams(two_layers=True, glue_letters=True)
        self.assertTrue(p.glue_letters)
        self.assertFalse(p.two_layers)
        self.assertTrue(kg.KeychainParams(two_layers=True).two_layers)
        self.assertFalse(kg.KeychainParams().glue_letters)


@unittest.skipUnless(HAS_QT, "Qt requis")
class KeychainModesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1] + ["-platform", "offscreen"])

    def build(self, text="Emma", **kw):
        return kg.build_keychain(kg.KeychainParams(text=text, **kw), "Sans Serif", True, False)

    def tags(self, result):
        objects = importers.keychain_to_objects(result, "cut", "engrave", 0.0, 0.0)
        return [(o.source_tag, o.layer_id) for o in objects]

    def test_glue_letters_layout(self):
        res = self.build(glue_letters=True)
        self.assertTrue(res.glue_letters)
        self.assertFalse(res.two_layers)
        self.assertTrue(res.text_contours)                       # le prénom, gravé sur la plaque
        self.assertEqual(res.top_base_contours, [])             # pas de seconde plaque
        self.assertEqual(res.outline_contours, [])
        _x0, base_right = x_range(res.base_contours)
        letters_left, _letters_right = x_range(res.top_text_contours)
        self.assertGreaterEqual(letters_left, base_right + GAP - 1e-6)   # les lettres sont à droite de la plaque
        self.assertAlmostEqual(res.width, 2 * base_right + GAP, delta=0.01)
        # mêmes lettres que celles gravées, simplement décalées
        self.assertEqual(len(res.top_text_contours), len(res.text_contours))
        shift = res.top_text_contours[0][0][0] - res.text_contours[0][0][0]
        self.assertAlmostEqual(shift, base_right + GAP, delta=0.01)

    def test_other_modes_have_no_loose_letters_unless_two_layers(self):
        classic = self.build()
        self.assertFalse(classic.glue_letters)
        self.assertEqual(classic.top_text_contours, [])
        two = self.build(two_layers=True)
        self.assertTrue(two.top_base_contours)

    def test_glue_letters_objects(self):
        tags = self.tags(self.build(glue_letters=True))
        self.assertIn(("keychain:text", "engrave"), tags)        # prénom gravé = repère de placement
        self.assertIn(("keychain:letters", "cut"), tags)         # lettres seules découpées
        self.assertIn(("keychain:plate", "cut"), tags)           # la plaque
        self.assertEqual(len(tags), 3)
        self.assertNotIn("keychain:top:plate", [t for t, _ in tags])

    def test_classic_objects_unchanged(self):
        self.assertEqual(sorted(self.tags(self.build())), [("keychain:plate", "cut"), ("keychain:text", "engrave")])

    def test_batch_glue_letters_one_set_per_name(self):
        res = self.build(text="Emma\nLéa", glue_letters=True)
        self.assertEqual(len(res.pieces), 2)
        self.assertTrue(all(p.glue_letters for p in res.pieces))
        letters = [t for t in self.tags(res) if t == ("keychain:letters", "cut")]
        self.assertEqual(len(letters), 2)


if __name__ == "__main__":
    unittest.main()
