"""Boule de Noël : formes, disposition du prénom et des flocons (sans Qt) ; soudure des contours (avec Qt)."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from laser_studio.vector import ornament_generator as og  # noqa: E402

try:
    from PyQt6.QtGui import QGuiApplication, QPainterPath
    from laser_studio.vector import ornament_region as region
    HAS_QT = isinstance(QPainterPath, type) and "stub" not in (QPainterPath.__module__ or "").lower() \
        and callable(getattr(QPainterPath, "simplified", None))
except Exception:  # pragma: no cover - sans Qt
    HAS_QT = False

TEXT_BOUNDS = (0.0, -30.0, 220.0, 110.0)  # un prénom 2,2 fois plus large que haut, avec jambages


def params(**kw):
    return og.OrnamentParams(**kw)


class SnowflakeTests(unittest.TestCase):
    def test_every_style_is_one_simple_polygon(self):
        for style in og.FLAKE_STYLES:
            for radius in (4.0, 8.0, 25.0):
                for rot in (0.0, 17.0, 90.0):
                    poly = og.snowflake_polygon(1.0, 2.0, radius, rot, style)
                    self.assertTrue(og.is_simple(poly), f"{style} r={radius} rot={rot}")
                    self.assertGreater(og.polygon_area(poly), 0)

    def test_tips_reach_the_radius_and_stay_centered(self):
        poly = og.snowflake_polygon(10.0, -5.0, 8.0, 90.0, "Classique")
        reach = max(math.dist(p, (10.0, -5.0)) for p in poly)
        self.assertAlmostEqual(reach, 8.0, places=6)
        cx = sum(p[0] for p in poly) / len(poly)
        self.assertAlmostEqual(cx, 10.0, places=6)

    def test_six_fold_symmetry(self):
        poly = og.snowflake_polygon(0.0, 0.0, 10.0, 0.0, "Dentelle")
        rotated = og._rotate(poly, 60.0)
        keys = lambda pts: sorted((round(x, 6), round(y, 6)) for x, y in pts)  # noqa: E731
        self.assertEqual(keys(poly), keys(rotated))

    def test_a_small_flake_keeps_a_cuttable_stem(self):
        # Au rayon minimal autorisé, la tige fait encore au moins MIN_STEM_MM de large.
        poly = og.snowflake_polygon(0, 0, 4.0, 0.0, "Étoile")
        base = min(math.dist(p, (0, 0)) for p in poly)
        self.assertGreaterEqual(2 * base, og.MIN_STEM_MM * 0.9)


class LayoutTests(unittest.TestCase):
    def test_body_is_a_ring_with_the_string_hole_above_it(self):
        g = og.build_ornament(params(diameter=80, ring_width=4, name=""))
        self.assertAlmostEqual(g.radius, 40.0)
        self.assertAlmostEqual(g.inner_radius, 36.0)
        hx, hy = g.hole_center
        self.assertEqual(hx, 0.0)
        self.assertGreater(hy - 1.5, g.inner_radius)       # le trou n'entame pas le vide intérieur
        self.assertGreater(hy, g.radius)                   # et il est au-dessus du cercle
        self.assertGreater(g.bounds[3], g.radius)          # l'accroche dépasse
        self.assertAlmostEqual(g.bounds[0], -40.0, places=1)

    def test_no_hanger_means_no_hole_and_a_round_bounding_box(self):
        g = og.build_ornament(params(hanger="Aucun"))
        self.assertEqual(g.holes, [])
        self.assertAlmostEqual(g.bounds[3], 40.0, places=1)

    def test_cap_hanger_is_taller_than_the_plain_ring(self):
        ring = og.build_ornament(params(hanger="Anneau"))
        cap = og.build_ornament(params(hanger="Bouchon"))
        self.assertGreater(cap.bounds[3], ring.bounds[3])

    def test_hanging_flakes_are_tied_to_the_ring_by_a_stem(self):
        g = og.build_ornament(params(flake_layout="Suspendus", flake_count=3, flake_size=16))
        self.assertEqual(len(g.flakes), 3)
        stems = [s for s in g.solids if len(s) == 4]
        self.assertEqual(len(stems), 3)
        for f, stem in zip(g.flakes, stems):
            top = max(p[1] for p in stem)
            self.assertGreater(top, math.sqrt(g.inner_radius ** 2 - f.cx ** 2))  # s'enfonce dans l'anneau
            self.assertLess(top, g.radius)
            self.assertLess(min(p[1] for p in stem), f.cy + f.radius)            # et rejoint le flocon
            self.assertLess(math.dist((f.cx, f.cy), (0, 0)) + f.radius, g.inner_radius)

    def test_ring_flakes_are_welded_into_the_ring_but_stay_inside_the_ball(self):
        for layout, expected in (("Haut et bas", 6), ("Haut", 3), ("Bas", 3)):
            g = og.build_ornament(params(flake_layout=layout, flake_count=3, flake_size=14))
            self.assertEqual(len(g.flakes), expected, layout)
            for f in g.flakes:
                tip = math.dist((f.cx, f.cy), (0, 0)) + f.radius
                self.assertGreater(tip, g.inner_radius + 1.0, layout)   # pénètre dans l'anneau
                self.assertLess(tip, g.radius - 0.5, layout)            # sans le traverser

    def test_ring_flakes_do_not_overlap_each_other(self):
        g = og.build_ornament(params(flake_layout="Haut et bas", flake_count=4, flake_size=14))
        for i, a in enumerate(g.flakes):
            for b in g.flakes[i + 1:]:
                self.assertGreaterEqual(math.dist((a.cx, a.cy), (b.cx, b.cy)), a.radius + b.radius - 0.5)

    def test_no_motif_means_no_flake(self):
        g = og.build_ornament(params(motif="Aucun"))
        self.assertEqual((g.flakes, g.solids), ([], []))

    def test_name_is_centered_and_fits_inside_the_ball(self):
        g = og.build_ornament(params(name="Emma"), TEXT_BOUNDS)
        t = g.text
        self.assertIsNotNone(t)
        mid_x = t.scale * (TEXT_BOUNDS[0] + TEXT_BOUNDS[2]) / 2 + t.tx
        mid_y = t.scale * (TEXT_BOUNDS[1] + TEXT_BOUNDS[3]) / 2 + t.ty
        self.assertAlmostEqual(mid_x, 0.0, places=6)
        self.assertAlmostEqual(mid_y, t.center_y, places=6)
        self.assertLess(t.width, 2 * g.radius)
        self.assertLessEqual(t.height, 0.34 * 80 + 1e-6)

    def test_name_follows_an_explicit_size_and_offset(self):
        g = og.build_ornament(params(name="Emma", name_size=20.0, name_offset=5.0), TEXT_BOUNDS)
        self.assertAlmostEqual(g.text.height, 20.0, places=6)
        self.assertAlmostEqual(g.text.center_y, 5.0, places=6)

    def test_default_offset_leaves_room_for_the_flakes(self):
        top = og.build_ornament(params(name="Emma", flake_layout="Suspendus"), TEXT_BOUNDS).text.center_y
        mid = og.build_ornament(params(name="Emma", flake_layout="Haut et bas"), TEXT_BOUNDS).text.center_y
        bottom = og.build_ornament(params(name="Emma", flake_layout="Bas"), TEXT_BOUNDS).text.center_y
        self.assertLess(top, mid)
        self.assertLess(mid, bottom)

    def test_bar_straddles_the_baseline_and_spans_the_ball(self):
        g = og.build_ornament(params(name="Emma", support="Barre", bar_thickness=2.0), TEXT_BOUNDS)
        ys = [p[1] for p in g.bar]
        self.assertAlmostEqual(min(ys), g.text.baseline - 0.6, places=6)
        self.assertAlmostEqual(max(ys), g.text.baseline + 1.4, places=6)
        self.assertAlmostEqual(min(p[0] for p in g.bar), -g.radius)
        self.assertFalse(g.floating_name)

    def test_without_a_bar_a_short_name_is_reported_as_floating(self):
        short = og.build_ornament(params(name="Li", support="Aucun", name_size=10.0), (0, 0, 40, 40))
        self.assertTrue(short.floating_name)
        self.assertIsNone(short.bar)
        wide = og.build_ornament(params(name="Emma", support="Aucun", flake_layout="Haut et bas"), (0, 0, 400, 100))
        self.assertFalse(wide.floating_name)

    def test_empty_name_adds_nothing(self):
        g = og.build_ornament(params(name="   "), TEXT_BOUNDS)
        self.assertIsNone(g.text)
        self.assertIsNone(g.bar)

    def test_same_parameters_give_the_same_shapes(self):
        a = og.build_ornament(params(name="Emma", flake_layout="Haut et bas"), TEXT_BOUNDS)
        b = og.build_ornament(params(name="Emma", flake_layout="Haut et bas"), TEXT_BOUNDS)
        self.assertEqual([f.polygon for f in a.flakes], [f.polygon for f in b.flakes])


class ValidationTests(unittest.TestCase):
    def check(self, code, **kw):
        with self.assertRaises(og.OrnamentError) as cm:
            og.build_ornament(params(**kw))
        self.assertEqual(cm.exception.code, code)

    def test_invalid_values_are_refused_with_a_code(self):
        self.check("diameter", diameter=10)
        self.check("ring_width", ring_width=0.5)
        self.check("hole", hole_diameter=20)
        self.check("flake_count", flake_count=9)
        self.check("flake_size", flake_size=2)
        self.check("flake_size", flake_size=70)
        self.check("name_too_long", name="x" * 41)
        self.check("bar", bar_thickness=0.2)
        self.check("hanger", hanger="Crochet")
        self.check("layout", flake_layout="Partout")

    def test_every_error_code_has_a_translation(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tr_ornament", os.path.join(REPO, "src", "laser_studio", "i18n", "translations.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for code in ("diameter", "ring_width", "hole", "flake_count", "flake_size", "bar", "name_too_long"):
            entry = mod.TRANSLATIONS[f"ornament.err.{code}"]
            self.assertEqual(set(entry), {"fr", "en", "de", "es"}, code)

    def test_every_choice_has_a_label_in_the_four_languages(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tr_ornament2", os.path.join(REPO, "src", "laser_studio", "i18n", "translations.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for prefix, keys in (("hanger", og.HANGERS), ("motif", og.MOTIFS), ("layout", og.FLAKE_LAYOUTS),
                             ("style", og.FLAKE_STYLES), ("support", og.SUPPORTS)):
            for key in keys:
                self.assertEqual(set(mod.TRANSLATIONS[f"ornament.{prefix}.{key}"]), {"fr", "en", "de", "es"})


@unittest.skipUnless(HAS_QT, "PyQt6 réel requis")
class WeldingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1] + ["-platform", "offscreen"])

    def contours(self, **kw):
        geometry, contours = region.build_ornament_contours(params(**kw), "DejaVu Sans", True, False)
        return geometry, contours

    @staticmethod
    def area(c):
        return abs(og.polygon_area(c))

    def test_plain_ring_is_two_contours_plus_the_string_hole(self):
        g, c = self.contours(name="", motif="Aucun")
        self.assertEqual(len(c), 3)  # extérieur (disque + boucle), vide intérieur, trou
        self.assertGreater(self.area(c[0]), self.area(c[1]))
        self.assertAlmostEqual(min(p[0] for p in c[0]), 0.0, places=2)
        self.assertAlmostEqual(min(p[1] for p in c[0]), 0.0, places=2)
        self.assertAlmostEqual(max(p[0] for p in c[0]), 80.0, places=1)

    def test_no_contour_is_cut_twice(self):
        g, c = self.contours(name="Emma", flake_layout="Haut et bas")
        keys = set()
        for contour in c:
            key = tuple(sorted((round(x, 2), round(y, 2)) for x, y in contour))
            self.assertNotIn(key, keys)
            keys.add(key)

    def test_name_bar_and_ring_are_welded_into_one_piece(self):
        g, c = self.contours(name="Emma", motif="Aucun", support="Barre")
        # Une seule pièce de matière : le contour extérieur ; tout le reste est un vide (intérieur, trou,
        # contreformes des lettres) et aucun contour ne reste isolé à l'intérieur d'un vide.
        outer = c[0]
        self.assertGreater(self.area(outer), 0.9 * math.pi * 40 ** 2)
        # Les vides sont plus petits que la boule et strictement à l'intérieur de sa boîte.
        for contour in c[1:]:
            self.assertLess(self.area(contour), self.area(outer))
            self.assertGreaterEqual(min(p[0] for p in contour), -1e-6)
            self.assertLessEqual(max(p[0] for p in contour), 80.0 + 1e-6)

    def test_text_never_leaves_the_ball(self):
        g, c = self.contours(name="Daniela Bernadette", name_size=40.0)
        for contour in c:
            for x, y in contour:
                cx, cy = x - 40.0, y - 40.0
                self.assertLessEqual(math.hypot(cx, cy), 40.0 + 0.1 if y < 80.0 else 1e9)

    def test_a_letter_counter_is_kept_as_its_own_contour(self):
        _, without = self.contours(name="", motif="Aucun")
        _, with_o = self.contours(name="oo", motif="Aucun")
        self.assertGreaterEqual(len(with_o), len(without) + 1)

    def test_each_style_and_layout_builds(self):
        for style in og.FLAKE_STYLES:
            for layout in og.FLAKE_LAYOUTS:
                g, c = self.contours(name="Emma", flake_style=style, flake_layout=layout)
                self.assertGreater(len(c), 2, (style, layout))


if __name__ == "__main__":
    unittest.main()
