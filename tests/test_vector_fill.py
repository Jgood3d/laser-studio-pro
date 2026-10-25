"""Remplissage vectoriel : objets qui se chevauchent (union, plus de vides aux croisements), trous conservés,
décalage aller/retour des lignes retour."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

try:
    from vector_layers import build_vector_layers_gcode, _scanline_fill_union
    HAS_BUILD = callable(build_vector_layers_gcode) and callable(_scanline_fill_union) and \
        not str(type(build_vector_layers_gcode)).endswith("MagicMock'>")
except ImportError:
    HAS_BUILD = False

from test_calibration_patterns import burn_segments


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def fill_layer(groups, interval=0.5, power=80.0):
    polys = [p for g in groups for p in g]
    layer = {"name": "Remplissage", "mode": "Gravure Remplie", "power": power, "speed": 1000, "passes": 1,
             "line_interval": interval}
    return {"L": {"layer": layer, "polygons": polys, "polygon_groups": groups}}


def burned(layers, **kw):
    """{y arrondi: [(x0, x1), ...]} des segments réellement gravés, fusionnés."""
    gcode = build_vector_layers_gcode(layers, 0.0, 0.0, 400.0, "M4", 1000, **kw)[0]
    rows = {}
    for y, a, b, s in burn_segments("\n".join(gcode)):
        rows.setdefault(round(y, 3), []).append((min(a, b), max(a, b)))
    return rows


@unittest.skipUnless(HAS_BUILD, "build_vector_layers_gcode non disponible ici")
class UnionTests(unittest.TestCase):
    def test_union_of_overlapping_segments(self):
        groups = [[rect(0, 0, 20, 10)], [rect(10, 0, 30, 10)]]
        self.assertEqual(_scanline_fill_union(groups, 5.0), [(0.0, 30.0)])

    def test_touching_and_separate_segments(self):
        self.assertEqual(_scanline_fill_union([[rect(0, 0, 10, 10)], [rect(10, 0, 20, 10)]], 5.0), [(0.0, 20.0)])
        self.assertEqual(_scanline_fill_union([[rect(0, 0, 10, 10)], [rect(15, 0, 20, 10)]], 5.0), [(0.0, 10.0), (15.0, 20.0)])
        self.assertEqual(_scanline_fill_union([], 5.0), [])

    def test_overlap_of_two_objects_is_engraved_in_the_gcode(self):
        """Avant : la zone commune de deux objets n'était PAS gravée (règle pair-impair mélangée)."""
        rows = burned(fill_layer([[rect(0, 0, 20, 10)], [rect(10, 0, 30, 10)]]))
        self.assertTrue(rows)
        for y, segs in rows.items():
            xs = sorted(segs)
            self.assertEqual((xs[0][0], xs[-1][1]), (0.0, 30.0), y)
            covered = 0.0
            last = 0.0
            for a, b in xs:
                self.assertLessEqual(a, last + 1e-6, f"trou non gravé à y={y} entre {last} et {a}")
                last = max(last, b)
            self.assertAlmostEqual(last, 30.0)

    def test_crossing_strokes_have_no_gap_at_the_crossing(self):
        horizontal = [rect(0, 9, 40, 11)]
        vertical = [rect(19, 0, 21, 20)]
        rows = burned(fill_layer([horizontal, vertical], interval=0.25))
        for y, segs in rows.items():
            if 9 <= y < 11:
                self.assertEqual(len(segs), 1, f"trait horizontal interrompu à y={y}: {segs}")
                self.assertEqual((segs[0][0], segs[0][1]), (0.0, 40.0))

    def test_holes_inside_one_object_are_kept(self):
        plate = [rect(0, 0, 40, 20), rect(15, 5, 25, 15)]            # un seul objet : plaque + trou
        rows = burned(fill_layer([plate], interval=1.0))
        for y, segs in rows.items():
            if 5 < y < 15:
                self.assertEqual(sorted(segs), [(0.0, 15.0), (25.0, 40.0)], y)

    def test_another_object_covering_the_hole_fills_it(self):
        plate = [rect(0, 0, 40, 20), rect(15, 5, 25, 15)]
        cover = [rect(10, 0, 30, 20)]
        rows = burned(fill_layer([plate, cover], interval=1.0))
        for y, segs in rows.items():
            if 5 < y < 15:
                self.assertEqual(sorted(segs), [(0.0, 40.0)], y)

    def test_without_groups_the_historic_behaviour_is_kept(self):
        layers = fill_layer([[rect(0, 0, 20, 10)]])
        del layers["L"]["polygon_groups"]
        self.assertTrue(burned(layers))

    def test_default_scan_offset_leaves_the_gcode_unchanged(self):
        layers = fill_layer([[rect(0, 0, 20, 10)], [rect(30, 0, 50, 10)]])
        a = build_vector_layers_gcode(layers, 0.0, 0.0, 400.0, "M4", 1000)[0]
        b = build_vector_layers_gcode(layers, 0.0, 0.0, 400.0, "M4", 1000, scan_offset=0.0)[0]
        self.assertEqual(a, b)


@unittest.skipUnless(HAS_BUILD, "build_vector_layers_gcode non disponible ici")
class ScanOffsetTests(unittest.TestCase):
    def test_return_rows_are_shifted_and_forward_rows_are_not(self):
        layers = fill_layer([[rect(10, 0, 30, 10)]], interval=1.0)
        base = burned(layers)
        shifted = burned(layers, scan_offset=0.3)
        ys = sorted(base)
        self.assertEqual(sorted(shifted), ys)
        for k, y in enumerate(ys):
            if k % 2 == 0:                               # sens aller : inchangé
                self.assertEqual(shifted[y], base[y])
            else:                                        # sens retour : décalé de +0,3 mm
                self.assertEqual([(round(a - 0.3, 6), round(b - 0.3, 6)) for a, b in shifted[y]],
                                 [(round(a, 6), round(b, 6)) for a, b in base[y]])

    def test_offset_applies_to_every_segment_of_a_return_row(self):
        layers = fill_layer([[rect(0, 0, 10, 10)], [rect(20, 0, 30, 10)]], interval=1.0)
        shifted = burned(layers, scan_offset=-0.2)
        y = sorted(shifted)[1]
        self.assertEqual(sorted(shifted[y]), [(-0.2, 9.8), (19.8, 29.8)])

    def test_offset_with_overscan_moves_the_whole_return_pass(self):
        layers = fill_layer([[rect(10, 0, 30, 10)]], interval=1.0)
        gcode = build_vector_layers_gcode(layers, 0.0, 0.0, 400.0, "M4", 1000, overscan_dist=2.0, scan_offset=0.5)[0]
        starts = [l for l in gcode if l.startswith("G0 X")]
        self.assertIn("G0 X32.500 Y1.000", starts)       # retour : départ 30 + 2 de surbalayage, décalé de 0,5
        self.assertIn("G0 X8.000 Y0.000", starts)        # aller : 10 - 2, inchangé


class WiringTests(unittest.TestCase):
    def src(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def test_groups_and_offset_are_wired_end_to_end(self):
        self.assertIn('"polygon_groups": []', self.src("vector_layers.py"))
        self.assertIn("_scanline_fill_union(groups, y)", self.src("vector_layers.py"))
        self.assertIn("scan_offset=float(self.params.get('scan_offset_mm', 0.0) or 0.0)", self.src("workers.py"))


if __name__ == "__main__":
    unittest.main()
