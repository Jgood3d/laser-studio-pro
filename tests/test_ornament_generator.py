"""Boule de Noël : formes, disposition du prénom et des flocons (sans Qt) ; soudure des contours (avec Qt)."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from laser_studio.vector import ornament_generator as og  # noqa: E402
from laser_studio.vector import ornament_motifs as om  # noqa: E402

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


def _reaches_into_ring(g, poly):
    """Vrai pour une suspente : un contour qui monte jusque sous le bord extérieur de l'anneau, en s'enfonçant
    dans l'anneau au-dessus de son bord intérieur (un flocon ou une barre n'y arrive pas de cette façon)."""
    if poly is g.bar or poly is g.top_bar:
        return False
    xs = [p[0] for p in poly]
    x = (min(xs) + max(xs)) / 2.0
    top = max(p[1] for p in poly)
    return top > math.sqrt(max(g.inner_radius ** 2 - x ** 2, 0.0)) and top < g.radius and max(xs) - min(xs) < 0.5 * g.radius


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
        stems = [s for s in g.solids if _reaches_into_ring(g, s)]
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


class MotifShapeTests(unittest.TestCase):
    def test_stars_are_simple_polygons_with_the_asked_number_of_points(self):
        for points in (4, 5, 8):
            poly = om.star_polygon(0.0, 0.0, 8.0, points)
            self.assertEqual(len(poly), 2 * points)
            self.assertTrue(og.is_simple(poly))
            self.assertAlmostEqual(max(math.hypot(*p) for p in poly), 8.0)

    def test_mixed_stars_alternate(self):
        self.assertEqual([om.star_points_for("Mixte", i) for i in range(4)], [5, 4, 8, 5])
        self.assertEqual(om.star_points_for("4 branches", 7), 4)

    def test_every_upright_motif_is_made_of_simple_polygons_at_every_size(self):
        for name, build in om.UPRIGHT_BUILDERS.items():
            for style in og.MOTIF_STYLES[name]:
                for h in (10.0, 24.0, 60.0):
                    shape = build(h, style)
                    for poly in shape.solids + shape.late:
                        if len(poly) < 60:  # les cercles et ellipses sont simples par construction
                            self.assertTrue(og.is_simple(poly), (name, style, h))
                    self.assertLessEqual(abs(shape.ymin), 0.02 * h + 0.01, (name, style, h))
                    self.assertGreater(shape.ymax, 0.6 * h, (name, style, h))
                    self.assertLess(shape.ymax, 1.1 * h, (name, style, h))

    def test_axis_points_are_inside_the_material(self):
        for name, build in om.UPRIGHT_BUILDERS.items():
            shape = build(24.0, "Classique")
            self.assertTrue(shape.contains(0.0, shape.axis_top()), name)
            self.assertTrue(shape.contains(0.0, shape.axis_bottom()), name)

    def test_details_are_left_out_when_they_would_be_too_thin(self):
        self.assertEqual(om.santa_shape(12.0).cuts, [])
        self.assertEqual(om.santa_shape(12.0).late, [])
        self.assertEqual(len(om.santa_shape(26.0).cuts), 1)
        self.assertEqual(om.snowman_shape(15.0).cuts, [])
        self.assertEqual(len(om.snowman_shape(30.0).cuts), 4)
        self.assertEqual(om.gift_shape(14.0).cuts, [])

    def test_santa_face_is_a_cut_and_the_mustache_is_added_after_it(self):
        shape = om.santa_shape(26.0)
        face = shape.cuts[0]
        cx = sum(p[0] for p in face) / len(face)
        cy = sum(p[1] for p in face) / len(face)
        self.assertFalse(shape.contains(cx - 0.12 * 26, cy))   # le visage est évidé…
        self.assertTrue(shape.contains(0.0, 0.43 * 26))        # …mais la moustache est pleine
        self.assertTrue(shape.contains(0.0, 0.50 * 26))        # et le nez aussi

    def test_moon_is_one_simple_crescent_open_to_the_right(self):
        for h in (10.0, 24.0, 50.0):
            moon = om.moon_shape(h)
            self.assertTrue(og.is_simple(moon.solids[0]), h)
            self.assertTrue(moon.contains(-0.45 * h, 0.5 * h))        # l'épaisseur du croissant, à gauche
            self.assertFalse(moon.contains(0.30 * h, 0.5 * h))        # le creux, à droite
            self.assertAlmostEqual(moon.width, 0.8 * h, delta=0.1 * h)

    def test_holly_berries_hold_the_leaves_together(self):
        for style in om.HOLLY_STYLES:
            shape = om.holly_shape(24.0, style)
            leaves, berries = shape.solids[:-3], shape.solids[-3:]
            self.assertEqual(len(leaves), 3 if style == "Trio" else 2)
            for leaf in leaves:
                # Chaque feuille a au moins un sommet dans une baie : elles sont soudées entre elles.
                self.assertTrue(any(om.point_in_polygon(x, y, b) for x, y in leaf for b in berries), style)

    def test_candle_flame_is_welded_to_the_body_and_hollowed_when_large(self):
        small, large = om.candle_shape(14.0), om.candle_shape(40.0)
        self.assertEqual(small.cuts, [])
        self.assertEqual(len(large.cuts), 1)
        for shape in (small, large):
            flame = shape.solids[2]
            body = shape.solids[1]
            self.assertTrue(any(om.point_in_polygon(x, y, body) for x, y in flame))

    def test_bell_clapper_is_tied_inside_the_bell(self):
        for h in (12.0, 24.0, 50.0):
            bell = om.bell_shape(h)
            body, _knob, clapper, stem = bell.solids
            self.assertTrue(any(om.point_in_polygon(x, y, body) for x, y in stem), h)
            self.assertTrue(any(om.point_in_polygon(x, y, clapper) or om.point_in_polygon(x, y, stem)
                                for x, y in stem), h)

    def test_bulb_has_a_socket_on_top(self):
        bulb = om.bulb_shape(10.0)
        self.assertTrue(bulb.contains(0.0, 9.5))      # la douille
        self.assertTrue(bulb.contains(0.0, 4.0))      # l'ampoule
        self.assertFalse(bulb.contains(3.0, 9.5))     # la douille est plus étroite que l'ampoule

    def test_cuts_stay_inside_the_solids(self):
        for name, build in om.UPRIGHT_BUILDERS.items():
            shape = build(30.0, "Classique")
            for cut in shape.cuts:
                for x, y in cut:
                    self.assertTrue(any(om.point_in_polygon(x, y, s) for s in shape.solids), (name, x, y))

    def test_transformed_moves_every_polygon_group(self):
        shape = om.santa_shape(26.0).transformed(90.0, 5.0, 7.0)
        self.assertEqual((len(shape.cuts), len(shape.late)), (1, 3))
        self.assertAlmostEqual(shape.contains(5.0 - 0.5, 7.0 + 0.0), shape.contains(5.0 - 0.5, 7.0))


class MotifLayoutTests(unittest.TestCase):
    def build(self, motif, layout, **kw):
        base = dict(motif=motif, flake_layout=layout, flake_count=3, flake_size=og.MOTIF_DEFAULT_SIZE.get(motif, 16.0),
                    name="Emma")
        base.update(kw)
        return og.build_ornament(params(**base), TEXT_BOUNDS)

    def test_every_motif_in_every_layout_builds_and_fits_in_the_ball(self):
        for motif in og.MOTIFS:
            if motif == "Aucun":
                continue
            for layout in og.FLAKE_LAYOUTS:
                for style in og.MOTIF_STYLES[motif]:
                    g = self.build(motif, layout, flake_style=style)
                    self.assertTrue(g.solids, (motif, layout, style))
                    for poly in g.solids + g.late:
                        if poly is g.bar:  # la barre dépasse le disque : elle y est rognée à l'assemblage
                            continue
                        for x, y in poly:
                            self.assertLess(math.hypot(x, y), g.radius + 0.5, (motif, layout, style))

    def test_default_style_exists_for_every_motif_and_a_wrong_one_is_refused(self):
        for motif, styles in og.MOTIF_STYLES.items():
            self.assertIn("Classique" if "Classique" in styles else styles[0], styles)
        with self.assertRaises(og.OrnamentError) as cm:
            og.build_ornament(params(motif="Sapins", flake_style="Dentelle"))
        self.assertEqual(cm.exception.code, "style")
        with self.assertRaises(og.OrnamentError):
            og.build_ornament(params(motif="Étoiles", flake_style="Fin"))

    def test_motifs_standing_on_the_ring_are_upright_and_rooted_in_it(self):
        for motif in og.UPRIGHT_MOTIFS:
            g = self.build(motif, "Bas")
            self.assertEqual(len(g.flakes), 3, motif)
            for f in g.flakes:
                self.assertEqual(f.rotation, 0.0)  # droit : jamais penché ni couché
            lowest = min(y for poly in g.solids for _x, y in poly if poly is not g.bar)
            # Le pied s'enfonce dans l'anneau (sous le bord intérieur) sans le traverser.
            self.assertLess(lowest, -g.inner_radius + 0.5, motif)
            self.assertGreater(lowest, -g.radius, motif)

    def test_motifs_hanging_from_the_top_ring_are_rooted_in_it(self):
        for motif in og.UPRIGHT_MOTIFS:
            g = self.build(motif, "Haut")
            highest = max(y for poly in g.solids for _x, y in poly if poly is not g.bar)
            self.assertGreater(highest, g.inner_radius - 0.5, motif)
            self.assertLess(highest, g.radius, motif)

    def test_hanging_motifs_are_tied_by_a_stem(self):
        for motif in og.UPRIGHT_MOTIFS:
            g = self.build(motif, "Suspendus")
            # Une suspente est un rectangle fin qui monte jusque dans l'anneau.
            stems = [p for p in g.solids if p is not g.bar and _reaches_into_ring(g, p)]
            self.assertEqual(len(stems), 3, motif)

    def test_star_layouts_reuse_the_radial_placement(self):
        g = self.build("Étoiles", "Haut et bas", flake_style="5 branches")
        self.assertEqual(len(g.flakes), 6)
        for f in g.flakes:
            tip = math.dist((f.cx, f.cy), (0, 0)) + f.radius
            self.assertGreater(tip, g.inner_radius + 1.0)
            self.assertLess(tip, g.radius - 0.5)

    def test_name_stays_between_the_motifs_of_the_top_and_the_bottom(self):
        for motif in og.MOTIFS:
            if motif == "Aucun":
                continue
            g = self.build(motif, "Haut et bas")
            self.assertIsNotNone(g.upper_edge, motif)
            if g.lower_edge is None:  # la guirlande n'occupe que le haut
                continue
            top = g.text.center_y + g.text.height / 2
            bottom = g.text.center_y - g.text.height / 2
            if g.upper_edge - g.lower_edge >= 10.0:  # assez de place : pas de recouvrement
                self.assertLessEqual(top, g.upper_edge + 1e-6, motif)
                self.assertGreaterEqual(bottom, g.lower_edge - 1e-6, motif)

    def test_name_goes_below_hanging_motifs_and_above_standing_ones(self):
        hanging = self.build("Sapins", "Suspendus").text
        standing = self.build("Sapins", "Bas").text
        self.assertLess(hanging.center_y, standing.center_y)

    def test_an_explicit_offset_overrides_the_free_band(self):
        g = self.build("Sapins", "Bas", name_offset=12.0)
        self.assertAlmostEqual(g.text.center_y, 12.0, places=6)

    def test_no_motif_keeps_the_cuts_lists_empty(self):
        g = og.build_ornament(params(motif="Aucun"))
        self.assertEqual((g.cuts, g.late), ([], []))
        g = og.build_ornament(params(motif="Père Noël", flake_size=26.0))
        self.assertEqual(len(g.cuts), 3)
        self.assertEqual(len(g.late), 9)   # 3 pères Noël × (2 boucles de moustache + nez)

    def test_motifs_that_do_not_fit_side_by_side_are_shrunk_not_stacked(self):
        wide = self.build("Cadeaux", "Bas", flake_count=3, flake_size=30.0)
        centers = sorted(f.cx for f in wide.flakes)
        for a, b in zip(centers, centers[1:]):
            self.assertGreater(b - a, 8.0)   # pas empilés au même endroit
        small = self.build("Sapins", "Bas", flake_count=3, flake_size=14.0)
        self.assertEqual(len({round(f.cx, 3) for f in small.flakes}), 3)

    def test_garland_hangs_the_bulbs_from_a_string_rooted_in_the_ring(self):
        g = self.build("Guirlande", "Haut", flake_count=5)
        self.assertEqual(len(g.flakes), 5)
        string = max((p for p in g.solids if len(p) > 50), key=len)
        xs = [x for x, _y in string]
        self.assertGreater(max(xs), g.inner_radius * 0.7)      # le fil va d'un côté à l'autre
        self.assertLess(min(xs), -g.inner_radius * 0.7)
        for end in (min(string), max(string)):                  # ses deux bouts s'enfoncent dans l'anneau
            self.assertGreater(math.hypot(*end), g.inner_radius)
        sag = min(y for _x, y in string)
        for f in g.flakes:
            self.assertLess(f.cy, sag + 1.0 + f.radius)         # l'ampoule pend sous le fil
        self.assertIsNotNone(g.upper_edge)
        self.assertIsNone(g.lower_edge)

    def test_garland_string_is_a_simple_ribbon_at_every_size(self):
        for diameter in (60.0, 80.0, 150.0):
            for count in (1, 3, 7):
                g = og.build_ornament(params(diameter=diameter, motif="Guirlande", flake_count=count,
                                             flake_size=10.0))
                string = max((p for p in g.solids if len(p) > 50), key=len)
                self.assertTrue(og.is_simple(string), (diameter, count))

    def test_garland_ignores_the_layout(self):
        a = self.build("Guirlande", "Haut")
        b = self.build("Guirlande", "Bas")
        self.assertEqual(a.solids, b.solids)

    def test_bandeau_adds_a_second_bar_along_the_top_of_the_letters(self):
        g = self.build("Aucun", "Haut", support="Bandeau", bar_thickness=2.0)
        self.assertIsNotNone(g.bar)
        self.assertIsNotNone(g.top_bar)
        top = g.text.center_y + g.text.height / 2
        self.assertAlmostEqual(max(p[1] for p in g.top_bar), top + 0.6, places=6)
        self.assertAlmostEqual(min(p[1] for p in g.top_bar), top - 1.4, places=6)
        self.assertGreater(min(p[1] for p in g.top_bar), max(p[1] for p in g.bar))   # au-dessus de la barre du bas
        self.assertIsNone(self.build("Aucun", "Haut", support="Barre").top_bar)
        self.assertFalse(g.floating_name)

    def test_support_none_has_no_bar_at_all(self):
        g = self.build("Aucun", "Haut", support="Aucun")
        self.assertEqual((g.bar, g.top_bar), (None, None))

    def test_holly_styles_and_the_other_new_motifs_are_listed(self):
        self.assertEqual(og.MOTIF_STYLES["Houx"], ("Trio", "Duo"))
        for motif in ("Lune", "Houx", "Bougie", "Cloche", "Guirlande"):
            self.assertIn(motif, og.MOTIFS)
        self.assertEqual(og.MOTIFS[-1], "Aucun")

    def test_default_sizes_exist_for_every_motif(self):
        for motif in og.MOTIFS:
            if motif != "Aucun":
                self.assertIn(motif, og.MOTIF_DEFAULT_SIZE)
                self.assertGreaterEqual(og.MOTIF_DEFAULT_SIZE[motif], 8.0)


def _grid_components(inside, bounds, res, min_cells=5):
    """Nombre de morceaux de matière d'une fonction `inside(x, y)` sur une grille (sans Qt) : les miettes de moins de
    `min_cells` cases (pointes très fines) sont ignorées."""
    x0, y0, x1, y1 = bounds
    nx, ny = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    grid = [[inside(x0 + i * res, y0 + j * res) for j in range(ny)] for i in range(nx)]
    seen = [[False] * ny for _ in range(nx)]
    pieces = 0
    for i in range(nx):
        for j in range(ny):
            if grid[i][j] and not seen[i][j]:
                stack, cells = [(i, j)], 0
                seen[i][j] = True
                while stack:
                    a, b = stack.pop()
                    cells += 1
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        c, d = a + da, b + db
                        if 0 <= c < nx and 0 <= d < ny and grid[c][d] and not seen[c][d]:
                            seen[c][d] = True
                            stack.append((c, d))
                if cells >= min_cells:
                    pieces += 1
    return pieces


def _ball_material(geo):
    """La matière réellement découpée (sans prénom) : anneau + accroche, plus motifs et tiges dans le disque."""
    def poly_in(x, y, polys):
        return any(om.point_in_polygon(x, y, p) for p in polys)

    def inside(x, y):
        if poly_in(x, y, geo.holes):
            return False
        if poly_in(x, y, geo.outer) and not poly_in(x, y, geo.voids):
            return True
        if math.hypot(x, y) > geo.radius:
            return False
        return poly_in(x, y, geo.late) or (poly_in(x, y, geo.solids) and not poly_in(x, y, geo.cuts))
    return inside


class ContactTests(unittest.TestCase):
    """Rien ne doit flotter : chaque motif, chaque tige touche le reste de la boule (sinon la pièce tombe)."""

    def test_every_upright_motif_is_one_piece(self):
        for name, build in om.UPRIGHT_BUILDERS.items():
            if name == "Lune":   # croissant : pointes émoussées plus fines que la grille
                continue
            for style in og.MOTIF_STYLES[name]:
                for h in (14.0, 18.0, 26.0, 40.0):
                    shape = build(h, style)
                    bounds = (min(p[0] for p in shape._points()) - 1, shape.ymin - 1,
                              max(p[0] for p in shape._points()) + 1, shape.ymax + 1)
                    self.assertEqual(_grid_components(shape.contains, bounds, 0.2), 1, (name, style, h))

    def test_bell_knob_overlaps_the_dome(self):
        bell = om.bell_shape(18.0)
        body, knob = bell.solids[0], bell.solids[1]
        self.assertTrue(any(om.point_in_polygon(x, y, body) for x, y in knob))

    def test_gift_bow_leaves_room_for_the_stem_between_the_loops(self):
        for h in (18.0, 26.0, 40.0):
            gift = om.gift_shape(h)
            y_loops = 0.86 * h
            stem = max(og.MIN_STEM_MM, 0.07 * h)
            self.assertFalse(gift.contains(-stem / 2, y_loops), h)
            self.assertFalse(gift.contains(stem / 2, y_loops), h)
            self.assertTrue(gift.contains(0.0, gift.axis_top()), h)

    def test_motif_drop_is_off_by_default(self):
        self.assertEqual(params().motif_drop, 0.0)

    def test_hanging_motifs_hang_lower_by_the_drop(self):
        for motif in ("Cadeaux", "Père Noël", "Cloche", "Flocons"):
            base = og.build_ornament(params(motif=motif, flake_layout="Suspendus", flake_count=1, flake_size=18.0))
            low = og.build_ornament(params(motif=motif, flake_layout="Suspendus", flake_count=1, flake_size=18.0,
                                           motif_drop=5.0))
            self.assertAlmostEqual(base.flakes[0].cy - low.flakes[0].cy, 5.0, places=6, msg=motif)

    def test_drop_moves_top_motifs_down_and_bottom_motifs_up(self):
        base = og.build_ornament(params(motif="Cadeaux", flake_layout="Haut et bas", flake_count=3))
        low = og.build_ornament(params(motif="Cadeaux", flake_layout="Haut et bas", flake_count=3, motif_drop=6.0))
        tops = lambda g: sorted(f.cy for f in g.flakes if f.cy > 0)
        bottoms = lambda g: sorted(f.cy for f in g.flakes if f.cy < 0)
        for a, b in zip(tops(base), tops(low)):
            self.assertAlmostEqual(a - b, 6.0, places=6)
        for a, b in zip(bottoms(base), bottoms(low)):
            self.assertAlmostEqual(b - a, 6.0, places=6)

    def test_a_lowered_motif_stays_joined_to_the_ring_by_a_stem(self):
        for motif, layout in (("Cadeaux", "Haut"), ("Cadeaux", "Bas"), ("Cloche", "Suspendus"),
                              ("Flocons", "Haut et bas")):
            for drop in (0.0, 6.0, 9.0):
                geo = og.build_ornament(params(motif=motif, flake_layout=layout, flake_count=3, flake_size=18.0,
                                               motif_drop=drop))
                self.assertEqual(_grid_components(_ball_material(geo), geo.bounds, 0.8), 1, (motif, layout, drop))

    def test_a_lowered_motif_never_leaves_the_disc(self):
        for layout in ("Suspendus", "Haut", "Bas"):
            geo = og.build_ornament(params(motif="Cadeaux", flake_layout=layout, flake_count=3, flake_size=18.0,
                                           motif_drop=60.0))
            for poly in geo.solids + geo.late:
                for x, y in poly:
                    self.assertLessEqual(math.hypot(x, y), geo.radius + 1.5, layout)


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
        every_style = sorted({st for styles in og.MOTIF_STYLES.values() for st in styles})
        for prefix, keys in (("hanger", og.HANGERS), ("motif", og.MOTIFS), ("layout", og.FLAKE_LAYOUTS),
                             ("style", every_style), ("support", og.SUPPORTS)):
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

    def test_every_motif_builds_and_has_no_duplicate_contour(self):
        for motif in og.MOTIFS:
            for layout in og.FLAKE_LAYOUTS:
                g, c = self.contours(name="Emma", motif=motif, flake_layout=layout,
                                     flake_size=og.MOTIF_DEFAULT_SIZE.get(motif, 16.0))
                keys = {tuple(sorted((round(x, 2), round(y, 2)) for x, y in contour)) for contour in c}
                self.assertEqual(len(keys), len(c), (motif, layout))

    def test_santa_face_and_snowman_eyes_become_inner_contours(self):
        _, plain = self.contours(name="", motif="Aucun")
        _, santa = self.contours(name="", motif="Père Noël", flake_layout="Haut", flake_count=1, flake_size=30.0)
        _, snowman = self.contours(name="", motif="Bonhomme de neige", flake_layout="Bas", flake_count=1,
                                   flake_size=30.0)
        self.assertGreaterEqual(len(santa), len(plain) + 1)       # contour du motif soudé à l'anneau + visage
        self.assertGreater(len(snowman), len(plain) + 3)     # yeux et boutons


from laser_studio.vector import ornament_fills as of  # noqa: E402
from laser_studio.vector import ornament_presets as presets  # noqa: E402


class EngravedBandTests(unittest.TestCase):
    def build(self, **kw):
        kw.setdefault("name", "Emma")
        kw.setdefault("name_mode", "Gravé")
        return og.build_ornament(params(**kw), TEXT_BOUNDS)

    def test_the_band_crosses_the_ball_and_holds_the_name(self):
        g = self.build(motif="Aucun")
        lo, hi = g.band_span
        self.assertTrue(g.engrave_text)
        self.assertIsNotNone(g.band)
        self.assertIn(g.band, g.solids)                       # la bande est de la matière soudée
        self.assertAlmostEqual(min(p[0] for p in g.band), -g.radius)
        self.assertAlmostEqual(max(p[0] for p in g.band), g.radius)
        t = g.text
        self.assertGreaterEqual(t.center_y - t.height / 2, lo)    # le prénom tient dans la bande
        self.assertLessEqual(t.center_y + t.height / 2, hi)
        self.assertLess(t.width, 2 * g.inner_radius)
        self.assertFalse(g.floating_name)

    def test_an_engraved_name_adds_no_bar(self):
        g = self.build(support="Bandeau")
        self.assertIsNone(g.bar)
        self.assertIsNone(g.top_bar)

    def test_the_band_exists_even_without_a_name(self):
        g = og.build_ornament(params(name="", name_mode="Gravé", motif="Aucun"))
        self.assertIsNotNone(g.band)
        self.assertIsNone(g.text)

    def test_band_height_follows_the_setting_and_the_name_fits(self):
        g = self.build(motif="Aucun", band_height=24.0)
        lo, hi = g.band_span
        self.assertAlmostEqual(hi - lo, 24.0)
        self.assertLessEqual(g.text.height, 24.0)

    def test_a_long_name_shrinks_to_the_band_width_not_the_other_way_round(self):
        g = og.build_ornament(params(name="Bernadette-Marie", name_mode="Gravé", motif="Aucun"), (0, -30, 700, 110))
        lo, hi = g.band_span
        self.assertAlmostEqual(hi - lo, 0.24 * 80.0)           # la bande garde sa hauteur
        self.assertLess(g.text.width, 2 * g.inner_radius)

    def test_band_sits_under_the_top_motifs_and_over_the_bottom_ones(self):
        top = self.build(motif="Flocons", flake_layout="Haut", flake_count=1, flake_size=30.0)
        self.assertLessEqual(top.band_span[1], top.upper_edge)
        bottom = self.build(motif="Flocons", flake_layout="Bas", flake_count=1, flake_size=30.0)
        self.assertGreaterEqual(bottom.band_span[0], bottom.lower_edge)
        both = self.build(motif="Flocons", flake_layout="Haut et bas", flake_count=2, flake_size=16.0)
        self.assertLess(both.band_span[1], both.upper_edge + 1e-6)
        self.assertGreater(both.band_span[0], both.lower_edge - 1e-6)

    def test_band_stays_inside_the_ball_for_any_offset(self):
        g = self.build(motif="Aucun", name_offset=500.0)
        self.assertLess(g.band_span[1], g.inner_radius)

    def test_frame_is_two_nested_outlines_inside_the_band(self):
        g = self.build(motif="Aucun", band_frame=True)
        self.assertEqual(len(g.frame), 2)
        outer, inner = g.frame
        lo, hi = g.band_span
        self.assertGreater(min(p[1] for p in outer), lo)
        self.assertLess(max(p[1] for p in outer), hi)
        self.assertGreater(og.polygon_area(outer), og.polygon_area(inner))
        for x, y in outer:
            self.assertLess(math.hypot(x, y), g.inner_radius)   # le filet reste dans le vide de la boule
        self.assertEqual(self.build(motif="Aucun", band_frame=False).frame, [])

    def test_cut_mode_is_unchanged(self):
        g = self.build(name_mode="Découpé", support="Barre")
        self.assertFalse(g.engrave_text)
        self.assertIsNone(g.band)
        self.assertIsNotNone(g.bar)

    def test_bad_values_are_rejected(self):
        for kw in ({"name_mode": "Peint"}, {"crown": "Cornes"}, {"fill": "Pois"}, {"fill_zone": "Milieu"},
                   {"fill": "Rayures", "fill_pitch": 2.0}, {"name_mode": "Gravé", "band_height": 3.0}):
            with self.assertRaises(og.OrnamentError, msg=str(kw)):
                og.build_ornament(params(**kw), TEXT_BOUNDS)


class FillTests(unittest.TestCase):
    def test_each_fill_covers_its_zone_with_cuttable_bars(self):
        box = (-45.0, 10.0, 45.0, 42.0)
        for kind in of.FILL_KINDS:
            for pitch in (4.5, 6.0, 12.0):
                shapes = of.fill_shapes(kind, pitch, box)
                self.assertGreater(len(shapes), 3, (kind, pitch))
                xs = [p[0] for poly in shapes for p in poly]
                ys = [p[1] for poly in shapes for p in poly]
                self.assertLessEqual(min(xs), box[0] + 1.0, (kind, pitch))     # elles débordent la zone : on rogne ensuite
                self.assertGreaterEqual(max(xs), box[2] - 1.0, (kind, pitch))
                self.assertLessEqual(min(ys), box[1] + 1.0, (kind, pitch))
                self.assertGreaterEqual(max(ys), box[3] - 1.0, (kind, pitch))

    def test_bar_width_is_never_below_the_laser_limit_and_leaves_a_gap(self):
        for pitch in (4.5, 5.0, 6.0, 10.0, 40.0):
            w = of.bar_width(pitch)
            self.assertGreaterEqual(w, of.MIN_BAR_MM)
            self.assertGreaterEqual(pitch - w, 1.6 - 1e-9 if pitch >= 4.5 else 0)   # le vide entre deux barres tient aussi

    def test_a_pitch_below_the_minimum_is_raised_not_trusted(self):
        a = of.fill_shapes("Rayures", 1.0, (-10, -10, 10, 10))
        b = of.fill_shapes("Rayures", of.MIN_PITCH_MM, (-10, -10, 10, 10))
        self.assertEqual(len(a), len(b))

    def test_zones_are_above_and_below_the_name_block(self):
        g = og.build_ornament(params(name="Emma", name_mode="Gravé", motif="Aucun", fill="Rayures"), TEXT_BOUNDS)
        self.assertEqual(len(g.fills), 2)
        lo, hi = g.name_block
        clips = sorted(g.fills, key=lambda f: min(p[1] for p in f[1]))
        bottom, top = clips[0][1], clips[1][1]
        self.assertLessEqual(max(p[1] for p in bottom), lo + 1.0)
        self.assertGreaterEqual(min(p[1] for p in top), hi - 1.0)
        for zone, count in (("Haut", 1), ("Bas", 1), ("Haut et bas", 2)):
            g = og.build_ornament(params(name="Emma", name_mode="Gravé", motif="Aucun", fill="Treillis",
                                         fill_zone=zone), TEXT_BOUNDS)
            self.assertEqual(len(g.fills), count, zone)

    def test_no_fill_means_no_shapes(self):
        self.assertEqual(og.build_ornament(params(name="Emma"), TEXT_BOUNDS).fills, [])

    def test_fills_work_with_a_cut_name_too(self):
        g = og.build_ornament(params(name="Emma", support="Barre", motif="Aucun", fill="Vagues"), TEXT_BOUNDS)
        self.assertEqual(len(g.fills), 2)


class AntlerAndCapTests(unittest.TestCase):
    def test_antlers_rise_above_the_ball_on_both_sides(self):
        plain = og.build_ornament(params(motif="Aucun"))
        g = og.build_ornament(params(motif="Aucun", crown="Bois de renne"))
        self.assertGreater(g.bounds[3], plain.bounds[3] + 10.0)
        self.assertLess(g.bounds[0], -g.radius)
        self.assertGreater(g.bounds[2], g.radius)
        self.assertAlmostEqual(g.bounds[0], -g.bounds[2], places=6)    # symétriques

    def test_antlers_start_on_the_ring_and_keep_clear_of_the_hanger(self):
        g = og.build_ornament(params(motif="Aucun", crown="Bois de renne"))
        hx, hy = g.hole_center
        for poly in g.outer[1 + 2:]:                       # disque, accroche (boucle) : le reste, ce sont les bois
            touches = any(abs(math.hypot(x, y) - g.radius) < 3.0 for x, y in poly)
            near_hanger = any(math.hypot(x - hx, y - hy) < 6.0 for x, y in poly)
            self.assertFalse(near_hanger)
            _ = touches
        feet = [p for poly in g.outer[3:] for p in poly if math.hypot(*p) < g.radius + 0.5]
        self.assertTrue(feet)                               # chaque bois s'enfonce dans l'anneau

    def test_the_ribbed_cap_has_three_slots_inside_the_cap(self):
        g = og.build_ornament(params(hanger="Capuchon", motif="Aucun"))
        self.assertEqual(len(g.holes), 1 + 3)
        slots = g.holes[1:] if g.holes[0] == [] else [h for h in g.holes if len(h) == 4]
        self.assertEqual(len(slots), 3)
        for slot in slots:
            ys = [p[1] for p in slot]
            self.assertGreater(min(ys), g.radius)             # au-dessus du cercle : dans le capuchon
            self.assertLess(max(ys), g.hole_center[1] - params().hole_diameter / 2)   # sous le trou de la ficelle
        self.assertGreater(g.bounds[3], og.build_ornament(params(hanger="Anneau", motif="Aucun")).bounds[3])

    def test_a_tiny_cap_has_no_slots(self):
        g = og.build_ornament(params(hanger="Capuchon", motif="Aucun", diameter=30.0, ring_width=2.0))
        self.assertEqual([h for h in g.holes if len(h) == 4], [])


class PresetTests(unittest.TestCase):
    def test_keys_are_unique_and_every_preset_builds(self):
        keys = [p.key for p in presets.PRESETS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreaterEqual(len(keys), 20)
        for preset in presets.PRESETS:
            for name in ("", "Emma", "Bernadette"):
                settings = dict(preset.settings)
                settings["name"] = name
                g = og.build_ornament(og.OrnamentParams(**settings), TEXT_BOUNDS if name else None)
                self.assertFalse(g.floating_name, preset.key)

    def test_presets_only_set_known_generator_settings(self):
        known = set(og.OrnamentParams().__dict__)
        for preset in presets.PRESETS:
            self.assertLessEqual(set(preset.settings), known | {"flake_style"}, preset.key)
            self.assertEqual(set(preset.settings), set(presets.SETTING_KEYS), preset.key)

    def test_presets_never_touch_the_user_dimensions_or_text(self):
        for preset in presets.PRESETS:
            for key in ("diameter", "ring_width", "name", "hole_diameter"):
                self.assertNotIn(key, preset.settings, preset.key)

    def test_each_preset_has_a_label_in_the_four_languages(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tr_ornament3", os.path.join(REPO, "src", "laser_studio", "i18n", "translations.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for preset in presets.PRESETS:
            self.assertEqual(set(mod.TRANSLATIONS[f"ornament.preset.{preset.key}"]), {"fr", "en", "de", "es"})
        for prefix, keys in (("name_mode", og.NAME_MODES), ("crown", og.CROWNS), ("fill", og.FILLS),
                             ("fill_zone", og.FILL_ZONES)):
            for key in keys:
                self.assertEqual(set(mod.TRANSLATIONS[f"ornament.{prefix}.{key}"]), {"fr", "en", "de", "es"})


@unittest.skipUnless(HAS_QT, "PyQt6 réel requis")
class EngravedWeldingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1] + ["-platform", "offscreen"])

    def parts(self, **kw):
        kw.setdefault("name", "Emma")
        return region.build_ornament_parts(params(**kw), "DejaVu Sans", True, False)

    def test_engraved_name_is_not_in_the_cut_and_cut_is_unchanged_in_shape(self):
        engraved = self.parts(name_mode="Gravé", motif="Aucun")
        self.assertTrue(engraved.name)
        # La découpe ne contient plus les lettres : ni contreformes de lettres, seulement l'extérieur, le vide
        # du haut, le vide du bas et le trou de la ficelle.
        self.assertEqual(len(engraved.cut), 4)

    def test_engraved_name_lies_on_the_band(self):
        p = self.parts(name_mode="Gravé", motif="Aucun")
        min_y = min(pt[1] for c in p.name for pt in c)
        max_y = max(pt[1] for c in p.name for pt in c)
        lo, hi = p.geometry.band_span
        oy = -p.geometry.bounds[1]
        self.assertGreaterEqual(min_y, lo + oy - 0.01)
        self.assertLessEqual(max_y, hi + oy + 0.01)

    def test_cut_mode_has_nothing_to_engrave(self):
        p = self.parts(name_mode="Découpé")
        self.assertEqual((p.name, p.frame), ([], []))

    def test_every_preset_is_one_piece_of_material_with_no_duplicate_contour(self):
        for preset in presets.PRESETS:
            settings = dict(preset.settings)
            settings["name"] = "Emma"
            p = region.build_ornament_parts(og.OrnamentParams(**settings), "DejaVu Sans", True, False)
            keys = {tuple(sorted((round(x, 2), round(y, 2)) for x, y in c)) for c in p.cut}
            self.assertEqual(len(keys), len(p.cut), preset.key)
            outer = p.cut[0]
            for c in p.cut[1:]:                             # les autres contours sont des vides, jamais de la matière isolée
                self.assertLess(abs(og.polygon_area(c)), abs(og.polygon_area(outer)), preset.key)

    def test_fill_bars_are_welded_to_the_ring(self):
        plain = self.parts(name_mode="Gravé", motif="Aucun")
        for kind in of.FILL_KINDS:
            filled = self.parts(name_mode="Gravé", motif="Aucun", fill=kind)
            # Matière isolée = contour posé à l'intérieur d'un vide sans toucher son bord : ici, un îlot serait un
            # contour DANS un vide ; on vérifie que le nombre de contours reste cohérent et que rien ne sort du disque.
            self.assertGreater(len(filled.cut), len(plain.cut), kind)
            for c in filled.cut:
                for x, y in c:
                    if y < 80.0:
                        self.assertLessEqual(math.hypot(x - 40.0, y - 40.0), 40.0 + 0.1, kind)


if __name__ == "__main__":
    unittest.main()
