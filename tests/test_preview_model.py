"""Modèle de l'aperçu 2D (gcode/preview.py), sans Qt : lecture du G-Code, choix
image ou traits, fond de matière, image reconstituée, suivi de la gravure."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.gcode.preview import (  # noqa: E402
    KIND_LAYER, KIND_MATRIX, KIND_RASTER, KIND_SVG_CUT, KIND_UNKNOWN, BurnTracker, is_cut_group,
    is_raster_group, material_background_rect, parse_preview, raster_image,
)

JOB = "\n".join([
    "; --- G-CODE HYBRIDE GRBL PRO ---",
    "M4 S0",                                   # ligne 0
    "; --- PHASE 1 : GRAVURE IMAGE (SURBALAYAGE ACTIF) ---",
    "F1000",                                   # 1
    "G0 X7.5 Y10 ; OVERSCAN_START",            # 2 : surbalayage
    "S0",                                      # 3
    "G1 X10 F1000 S0",                         # 4 : G1 à vide
    "G1 X12 F1000 S350",                       # 5 : gravé
    "G1 X14.5 F1000 S0 ; OVERSCAN_END",        # 6 : surbalayage
    "; --- CALQUE 'Découpe' [cut] ---",
    "G0 X0 Y0",                                # 7 : rapide
    "M4 S900",                                 # 8
    "G1 X5 Y0",                                # 9 : gravé (S modal)
    "G1 X5 Y5",                                # 10
    "M5",                                      # 11
    "G1 X9 Y9",                                # 12 : après M5, à vide
    "; --- CALQUE 'Gravure' [Gravure Remplie] ---",   # ancien libellé
    "G1 X1 Y1 S100",                           # 13
])


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.p = parse_preview(JOB, layer_colors={"Découpe": "#ff3b30"})

    def test_groups_kinds_and_colors(self):
        self.assertEqual([(g.kind, g.name, g.color, g.mode) for g in self.p.groups], [
            (KIND_RASTER, None, "#ffaa00", "engrave_fill"),
            (KIND_LAYER, "Découpe", "#ff3b30", "cut"),
            (KIND_LAYER, "Gravure", "#00ff88", "engrave_fill"),     # couleur inconnue : par défaut
        ])
        self.assertEqual(self.p.groups[1].strokes, [(0.0, 0.0, 5.0, 0.0, 900.0), (5.0, 0.0, 5.0, 5.0, 900.0)])

    def test_moves(self):
        self.assertEqual(len(self.p.overscan[0]) // 3, 2)
        # G0, puis « S0 » et « M4 S900 » : sans coordonnées, ils suivent le G modal (G0), longueur nulle.
        self.assertEqual(len(self.p.rapid[0]) // 3, 3)
        # G1 S0, « M5 » (suit le G1 modal, puissance nulle, longueur nulle) et le G1 après M5.
        self.assertEqual(len(self.p.travel[0]) // 3, 3)

    def test_burned_strokes_are_numbered_like_the_stream(self):
        self.assertEqual(self.p.burn_line_idx, [5, 9, 10, 13])
        self.assertEqual(self.p.burn_segments[0], (10.0, 10.0, 12.0, 10.0))

    def test_lines_the_stream_skips_are_not_numbered(self):
        # Commentaire indenté, texte qui n'est pas du G-Code : écartés par l'envoi (grbl.streaming.gcode_lines),
        # donc sans numéro, sinon le tracé « déjà gravé » prendrait de l'avance sur le laser.
        from laser_studio.grbl.streaming import gcode_lines
        text = "G21\n  ; commentaire\nConnecté à /dev/ttyUSB0\nM4 S0\nG1 X10 Y0 S500\nG1 X10 Y10\n"
        self.assertEqual(parse_preview(text).burn_line_idx, [2, 3])
        self.assertEqual(gcode_lines(text)[2:], ["G1 X10 Y0 S500", "G1 X10 Y10"])

    def test_cached_parse_is_reused_for_the_same_gcode_and_colours(self):
        # Une option d'affichage changée redessine sans relire tout le G-Code (0,6 s sur 500 000 lignes).
        from laser_studio.gcode.preview import parse_preview_cached
        first = parse_preview_cached(JOB, {"Découpe": "#ff3b30"})
        self.assertIs(parse_preview_cached("".join(JOB), {"Découpe": "#ff3b30"}), first)
        self.assertIsNot(parse_preview_cached(JOB, {"Découpe": "#000000"}), first)     # couleur changée
        self.assertIsNot(parse_preview_cached(JOB + "\nG1 X2 Y2 S10"), first)          # autre G-Code

    def test_malformed_lines_are_ignored(self):
        p = parse_preview("GXX\nG1 X\nG0 X5 Y5\nG1 X10 Y10 S100\n")
        self.assertEqual([g.kind for g in p.groups], [KIND_UNKNOWN])
        self.assertEqual(p.groups[0].strokes, [(5.0, 5.0, 10.0, 10.0, 100.0)])


def group_of(kind, mode=None, strokes=()):
    from laser_studio.gcode.preview import TraceGroup
    return TraceGroup(kind, None, "#ffffff", mode, strokes=list(strokes))


class RasterDecisionTests(unittest.TestCase):
    def test_decisions(self):
        self.assertTrue(is_raster_group(group_of(KIND_RASTER, "engrave_fill"), False))
        self.assertTrue(is_raster_group(group_of(KIND_MATRIX, "matrix"), True))
        self.assertFalse(is_raster_group(group_of(KIND_MATRIX, "matrix"), False))
        self.assertFalse(is_raster_group(group_of(KIND_SVG_CUT, "cut"), False))
        self.assertFalse(is_raster_group(group_of(KIND_LAYER, "cut"), False))
        self.assertFalse(is_raster_group(group_of(KIND_LAYER, "mark"), False))
        self.assertTrue(is_raster_group(group_of(KIND_LAYER, "engrave_fill"), False))

    def test_imported_gcode_looks_like_a_scan(self):
        scan = [(x, y * 0.2, x + 1, y * 0.2, 500) for y in range(10) for x in range(5)]   # 50 traits, 10 lignes
        self.assertTrue(is_raster_group(group_of(KIND_UNKNOWN, None, scan), False))
        self.assertFalse(is_raster_group(group_of(KIND_UNKNOWN, None, scan[:30]), False))   # trop peu de traits

    def test_cut_groups(self):
        self.assertTrue(is_cut_group(group_of(KIND_SVG_CUT, "cut")))
        self.assertTrue(is_cut_group(group_of(KIND_LAYER, "cut")))
        self.assertFalse(is_cut_group(group_of(KIND_LAYER, "mark")))


class MaterialAndImageTests(unittest.TestCase):
    def test_background_covers_the_job_with_a_margin(self):
        rect = material_background_rect([[(0, 0, 10, 0, 100)]], [([20, 30, float("nan")], [5, 5, float("nan")])])
        self.assertEqual(rect, (0.0, 0.0, 33.0, 8.0))            # pas de matière sous l'origine
        rect = material_background_rect([[(10, 10, 20, 10, 100)]], [])
        self.assertEqual(rect, (7.0, 7.0, 16.0, 6.0))
        rect = material_background_rect([[(-5, 0, 5, 0, 100)]], [])  # job déjà en négatif : marge entière
        self.assertEqual(rect, (-8.0, 0.0, 16.0, 3.0))
        self.assertIsNone(material_background_rect([], []))

    def test_raster_image(self):
        # 3 lignes espacées de 1 mm. L'image a 2 lignes : la hauteur suit l'écart entre lignes
        # (2 mm / 1 mm), la dernière ligne gravée est fusionnée avec la précédente (comportement
        # d'origine, conservé).
        strokes = [(0, 0, 10, 0, 1000), (0, 1, 5, 1, 500), (0, 2, 1, 2, 1000)]
        pixels, rect = raster_image(strokes, (200, 200, 200), (0, 0, 0))
        self.assertEqual(rect, (0, 0, 10, 2))
        self.assertEqual(pixels.shape, (1200, 2, 3))                  # pyqtgraph : colonnes, lignes, RVB
        self.assertEqual(tuple(pixels[0, 0]), (0, 0, 0))              # pleine puissance : brûlé
        self.assertEqual(tuple(pixels[300, 1]), (100, 100, 100))      # moitié de la puissance maxi
        self.assertEqual(tuple(pixels[1100, 1]), (200, 200, 200))     # non gravé : matière
        negative, _ = raster_image(strokes, (200, 200, 200), (0, 0, 0), negative=True)
        self.assertEqual(tuple(negative[0, 0]), (200, 200, 200))
        transparent, _ = raster_image(strokes, (200, 200, 200), (0, 0, 0), transparent_unburned=True)
        self.assertEqual(tuple(transparent[1100, 1]), (0, 0, 0, 0))   # non gravé : transparent
        flipped, _ = raster_image(strokes, (200, 200, 200), (0, 0, 0), flip=True)
        self.assertTrue(np.array_equal(flipped, pixels[:, ::-1]))

    def test_a_single_row_gives_no_image(self):
        self.assertIsNone(raster_image([(0, 0, 10, 0, 1000)], (200, 200, 200), (0, 0, 0)))


class BurnTrackerTests(unittest.TestCase):
    # Trois traits sur Y=0, lignes d'envoi 4, 5, 6.
    def tracker(self):
        return BurnTracker([4, 5, 6], [(0, 0, 10, 0), (10, 0, 20, 0), (20, 0, 30, 0)])

    def red_x(self, t):
        xs, _ys = t.points()
        return [round(float(v), 3) for v in xs if v == v]

    def test_head_in_the_middle_of_the_second_stroke(self):
        t = self.tracker()
        t.lines_acked = 7
        t.update(15.0, 0.0)
        self.assertEqual((t.done, self.red_x(t)), (1, [0.0, 10.0, 10.0, 15.0]))

    def test_nothing_before_grbl_accepts_the_lines(self):
        t = self.tracker()
        t.lines_acked = 4
        t.update(15.0, 0.0)
        self.assertEqual((t.done, self.red_x(t)), (0, []))

    def test_never_goes_back_then_finishes(self):
        t = self.tracker()
        t.lines_acked = 7
        t.update(25.0, 0.0)
        t.update(5.0, 0.0)
        self.assertEqual(t.done, 2)
        self.assertFalse(t.finish(False))
        self.assertTrue(t.finish(True))
        self.assertEqual((t.done, len(self.red_x(t))), (3, 6))

    def test_reset(self):
        t = self.tracker()
        t.lines_acked = 7
        t.update(25.0, 0.0)
        t.reset()
        self.assertEqual((t.done, t.lines_acked, self.red_x(t)), (0, 0, []))

    def test_empty_tracker(self):
        t = BurnTracker()
        self.assertFalse(t.update(1.0, 1.0))
        self.assertEqual(len(t.points()[0]), 0)


if __name__ == "__main__":
    unittest.main()
