"""Puzzle : chaque arête est découpée UNE seule fois (pas de contour fermé par pièce, qui doublait les
arêtes internes), et un tracé ouvert n'est plus refermé par le G-Code (aller-retour)."""
import math
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from laser_studio.vector import puzzle_generator as pg  # noqa: E402

try:
    from laser_studio.gcode.vector import build_vector_layers_gcode
    HAS_BUILD = callable(build_vector_layers_gcode) and not str(type(build_vector_layers_gcode)).endswith("MagicMock'>")
except ImportError:
    HAS_BUILD = False
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcode_reader import burn_paths  # noqa: E402


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def segments(pts, ndigits=3):
    """Segments non orientés, arrondis : deux segments identiques ont la même clé."""
    out = []
    for a, b in zip(pts, pts[1:]):
        ka, kb = (round(a[0], ndigits), round(a[1], ndigits)), (round(b[0], ndigits), round(b[1], ndigits))
        if ka != kb:
            out.append(tuple(sorted((ka, kb))))
    return out


def params(**kw):
    base = dict(width=100.0, height=60.0, nx=5, ny=4, seed=7, kerf=0.0)
    base.update(kw)
    return pg.PuzzleParams(**base)


class PuzzleCutsOnceTests(unittest.TestCase):
    def test_edge_count_is_one_per_internal_border(self):
        for style in ("Classique", "Organique"):
            r = pg.build_puzzle(params(style=style))
            self.assertEqual(len(r.edges), (5 - 1) * 4 + 5 * (4 - 1), style)

    def test_no_segment_is_cut_twice(self):
        for style in ("Classique", "Organique"):
            for kerf in (0.0, 0.1):
                r = pg.build_puzzle(params(style=style, kerf=kerf))
                segs = segments(r.outline)
                for e in r.edges:
                    segs += segments(e)
                self.assertEqual(len(segs), len(set(segs)), f"{style} kerf={kerf}")

    def test_total_cut_length_is_much_shorter_than_one_closed_contour_per_piece(self):
        r = pg.build_puzzle(params())
        once = length(r.outline) + sum(length(e) for e in r.edges)
        per_piece = sum(length(p.cut) for p in r.pieces)
        self.assertLess(once, per_piece * 0.65)
        # Chaque arête interne est comptée deux fois dans les pièces, une fois dans le tracé unique.
        perimeter = 2 * (100.0 + 60.0)
        self.assertAlmostEqual(per_piece - perimeter, 2 * (once - perimeter), delta=0.5)

    def test_internal_edges_are_open_and_run_border_to_border(self):
        r = pg.build_puzzle(params())
        xs = [100.0 * c / 5 for c in range(6)]
        ys = [60.0 * k / 4 for k in range(5)]
        for e in r.edges:
            self.assertNotEqual(e[0], e[-1])
            for x, y in (e[0], e[-1]):
                self.assertTrue(any(abs(x - gx) < 1e-6 for gx in xs) and any(abs(y - gy) < 1e-6 for gy in ys),
                                f"extrémité hors grille : {(x, y)}")

    def test_outline_is_a_closed_rectangle_grown_by_half_a_kerf(self):
        r = pg.build_puzzle(params(kerf=0.0))
        self.assertEqual(r.outline[0], r.outline[-1])
        self.assertEqual((min(p[0] for p in r.outline), max(p[0] for p in r.outline)), (0.0, 100.0))
        r = pg.build_puzzle(params(kerf=0.2))
        xs = [p[0] for p in r.outline]
        ys = [p[1] for p in r.outline]
        self.assertAlmostEqual(min(xs), -0.1)
        self.assertAlmostEqual(max(xs), 100.1)
        self.assertAlmostEqual(min(ys), -0.1)
        self.assertAlmostEqual(max(ys), 60.1)

    def test_internal_edges_are_not_compensated_by_the_kerf(self):
        a = pg.build_puzzle(params(kerf=0.0))
        b = pg.build_puzzle(params(kerf=0.3))
        self.assertEqual(a.edges, b.edges)

    def test_pieces_stay_available_for_the_preview(self):
        r = pg.build_puzzle(params(kerf=0.1))
        self.assertEqual(len(r.pieces), 20)
        for p in r.pieces:
            self.assertEqual(p.cut[0], p.cut[-1])

    def test_single_cell_has_no_internal_edge(self):
        r = pg.build_puzzle(params(nx=1, ny=1))
        self.assertEqual(r.edges, [])
        self.assertTrue(r.outline)


@unittest.skipUnless(HAS_BUILD, "build_vector_layers_gcode non disponible ici")
class OpenPathsAreNotClosedTests(unittest.TestCase):
    def build(self, polys, passes=1):
        layer = {"name": "Découpe", "mode": "Découpe", "power": 80.0, "speed": 300, "passes": passes,
                 "line_interval": 0.2}
        data = {"L": {"layer": layer, "polygons": polys}}
        return build_vector_layers_gcode(data, 0.0, 0.0, 400.0, "M4", 1000)[0]

    def g1(self, gcode):
        """Déplacements gravés."""
        return [step for path in burn_paths(gcode) for step in path[1:]]

    def test_open_polyline_is_cut_once_not_there_and_back(self):
        self.assertEqual(len(self.g1(self.build([[(0, 0), (10, 0), (10, 5)]]))), 2)

    def test_two_point_line_is_cut_once(self):
        self.assertEqual(len(self.g1(self.build([[(0, 0), (10, 0)]]))), 1)

    def test_closed_contour_is_still_closed(self):
        sq = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
        self.assertEqual(len(self.g1(self.build([sq]))), 4)

    def test_contour_with_a_rounding_gap_is_still_closed(self):
        sq = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 1e-6)]
        # Refermé : retour au point de départ ; (0, 1e-6) et (0, 0) sont le même point au millième près,
        # ce déplacement nul n'est pas écrit (GRBL l'ignorerait).
        paths = burn_paths(self.build([sq]))
        self.assertEqual((len(paths), paths[0][0], paths[0][-1]), (1, (0.0, 0.0), (0.0, 0.0)))

    def test_passes_are_still_honoured(self):
        self.assertEqual(len(self.g1(self.build([[(0, 0), (10, 0)]], passes=2))), 2)


if __name__ == "__main__":
    unittest.main()
