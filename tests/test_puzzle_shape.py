"""Puzzle : forme des ergots, emboîtement, jeu entre traits et ordre de découpe (laser_studio.vector.puzzle_generator).

Complète test_puzzle_cut_once.py (une arête = un passage) : ici on vérifie que les ergots ont une vraie forme de
puzzle (tête plus large que le col) et que, sur TOUTE la plage des curseurs de la boîte de dialogue, deux traits
ne se croisent jamais en dehors des intersections de la grille et restent assez éloignés l'un de l'autre (un pont
de bois trop fin casse, ou le trait fond)."""
import os
import random
import sys
import unittest

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
from laser_studio.vector import puzzle_generator as pg  # noqa: E402
from laser_studio.vector import order as vo  # noqa: E402

# Réglages extrêmes des curseurs de la boîte de dialogue (ui/dialogs/puzzle/dialog.py).
EXTREMES = [
    dict(tab_depth=0.30, tab_span=0.46, neck_width=0.32, pos_random=1.0, jitter=0.30),
    dict(tab_depth=0.30, tab_span=0.22, neck_width=0.60, pos_random=1.0, jitter=0.30),
    dict(tab_depth=0.34, tab_span=0.46, neck_width=0.60, pos_random=1.0, jitter=0.30),   # 0,34 : plafonné à 0,30
    dict(tab_depth=0.14, tab_span=0.46, neck_width=0.60, pos_random=0.0, jitter=0.0),
    dict(tab_depth=0.22, tab_span=0.34, neck_width=0.45, pos_random=0.6, jitter=0.10),   # défauts
]
GRIDS = [(5, 4, 119.21, 65.02), (4, 4, 120.0, 120.0), (8, 3, 240.0, 90.0), (3, 8, 90.0, 240.0)]


def build(cols, rows, w, h, seed, **kw):
    return pg.build_puzzle(pg.PuzzleParams(width=w, height=h, nx=cols, ny=rows, seed=seed, kerf=0.0, **kw))


def crossings(a, b, same=False, closed=False):
    """Nombre d'intersections entre deux polylignes (tableaux (n, 2)). same=True : auto-intersections
    (segments voisins ignorés) ; closed=True : `a` est fermé (premier et dernier segment voisins)."""
    a0, a1, b0, b1 = a[:-1], a[1:], b[:-1], b[1:]

    def orient(p, q, r):
        return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])

    A0, A1, B0, B1 = a0[:, None, :], a1[:, None, :], b0[None, :, :], b1[None, :, :]
    d1, d2, d3, d4 = orient(B0, B1, A0), orient(B0, B1, A1), orient(A0, A1, B0), orient(A0, A1, B1)
    hit = ((d1 > 0) != (d2 > 0)) & ((d3 > 0) != (d4 > 0))
    if same:
        i, j = np.arange(len(a0))[:, None], np.arange(len(b0))[None, :]
        gap = np.abs(i - j)
        if closed:
            gap = np.minimum(gap, len(a0) - gap)
        hit &= gap > 1
        return int(hit.sum()) // 2
    return int(hit.sum())


def min_dist(points, poly):
    """Distance minimale des points (n, 2) à la polyligne poly (m, 2)."""
    p0, p1 = poly[:-1], poly[1:]
    d = p1 - p0
    l2 = np.maximum((d ** 2).sum(1), 1e-12)
    t = np.clip(((points[:, None, :] - p0[None]) * d[None]).sum(2) / l2[None], 0, 1)
    proj = p0[None] + t[..., None] * d[None]
    return np.sqrt(((points[:, None, :] - proj) ** 2).sum(2)).min(1)


class PuzzleShapeTests(unittest.TestCase):
    def test_a_tab_has_a_neck_and_a_round_head_wider_than_the_neck(self):
        """Un vrai ergot : la tête est plus large que le col, sinon les pièces ne s'emboîtent pas."""
        e = pg.generate_jigsaw_edge((0, 0), (40, 0), 1)          # le tenon monte côté y > 0
        top = max(y for _x, y in e)
        self.assertGreater(top, 3.0)

        def width_at(level):
            xs = []
            for (x0, y0), (x1, y1) in zip(e, e[1:]):
                if (y0 - level) * (y1 - level) < 0:
                    xs.append(x0 + (level - y0) * (x1 - x0) / (y1 - y0))
            xs = [x for x in xs if abs(x - 20.0) < 12.0]
            return max(xs) - min(xs) if len(xs) >= 2 else None

        low = [w for w in (width_at(top * f / 20.0) for f in range(2, 12)) if w is not None]
        high = [w for w in (width_at(top * f / 20.0) for f in range(10, 19)) if w is not None]
        self.assertTrue(low and high)
        neck, head = min(low), max(high)
        self.assertGreater(head, neck * 1.15, f"tête {head:.2f} mm, col {neck:.2f} mm")
        self.assertGreater(neck, 0.8)                            # un col assez large pour ne pas casser

    def test_edge_without_tab_is_straight(self):
        e = pg.generate_jigsaw_edge((0, 0), (40, 0), 0)
        self.assertTrue(all(abs(y) < 1e-9 for _x, y in e))

    def test_tab_height_is_capped(self):
        """Au-delà de MAX_TAB_DEPTH l'ergot ne grandit plus (deux ergots voisins se toucheraient)."""
        a = pg.generate_jigsaw_edge((0, 0), (40, 0), 1, tab_depth=0.30)
        b = pg.generate_jigsaw_edge((0, 0), (40, 0), 1, tab_depth=0.40)
        self.assertEqual(a, b)

    def test_tab_size_follows_the_smaller_piece_side(self):
        """Sur des pièces rectangulaires, les ergots horizontaux et verticaux ont la même hauteur."""
        r = build(4, 4, 160.0, 80.0, seed=2)                     # pièces 40 x 20
        heights = []
        for e in r.edges:
            xs = [p[0] for p in e]
            ys = [p[1] for p in e]
            horizontal = (max(ys) - min(ys)) < (max(xs) - min(xs))
            heights.append(max(ys) - min(ys) if horizontal else max(xs) - min(xs))
        self.assertLess(max(heights) / min(heights), 1.6)

    def test_same_seed_same_puzzle(self):
        self.assertEqual(build(5, 4, 120, 80, 7).edges, build(5, 4, 120, 80, 7).edges)
        self.assertNotEqual(build(5, 4, 120, 80, 7).edges, build(5, 4, 120, 80, 8).edges)

    def test_everything_stays_inside_the_rectangle(self):
        for ext in EXTREMES:
            for seed in (1, 2, 3):
                r = build(5, 4, 119.21, 65.02, seed, **ext)
                for e in r.edges:
                    for x, y in e:
                        self.assertTrue(-1e-6 <= x <= 119.21 + 1e-6 and -1e-6 <= y <= 65.02 + 1e-6)


class PuzzleGeometryTests(unittest.TestCase):
    def test_no_stray_crossings_and_enough_clearance_over_the_whole_slider_range(self):
        for (cols, rows, w, h) in GRIDS:
            pw, ph = w / cols, h / rows
            k = min(pw, ph)
            verts = np.array([(c * pw, r * ph) for c in range(cols + 1) for r in range(rows + 1)])
            for ext in EXTREMES:
                for seed in (1,):
                    edges = [np.array(e) for e in build(cols, rows, w, h, seed, **ext).edges]
                    for e in edges:
                        self.assertEqual(crossings(e, e, same=True), 0, "une arête se recoupe elle-même")
                    for i in range(len(edges)):
                        for j in range(i + 1, len(edges)):
                            a, b = edges[i], edges[j]
                            self.assertEqual(crossings(a[1:-1], b[1:-1]), 0,
                                             f"croisement parasite {cols}x{rows} {ext} seed {seed}")
                            for p, q in ((a, b), (b, a)):
                                far = np.sqrt(((p[:, None, :] - verts[None]) ** 2).sum(2)).min(1) > 0.30 * k
                                if far.any():
                                    self.assertGreaterEqual(min_dist(p[far], q).min(), 0.10 * k,
                                                            f"jeu trop faible {cols}x{rows} {ext} seed {seed}")

    def test_random_sliders_never_break_the_puzzle(self):
        rng = random.Random(11)
        for _ in range(15):
            ext = dict(tab_depth=rng.uniform(.14, .34), tab_span=rng.uniform(.22, .46),
                       neck_width=rng.uniform(.32, .60), pos_random=rng.uniform(0, 1), jitter=rng.uniform(0, .30))
            cols, rows, w, h = rng.choice(GRIDS)
            pw, ph = w / cols, h / rows
            k = min(pw, ph)
            verts = np.array([(c * pw, r * ph) for c in range(cols + 1) for r in range(rows + 1)])
            edges = [np.array(e) for e in build(cols, rows, w, h, rng.randint(1, 999), **ext).edges]
            for i in range(len(edges)):
                for j in range(i + 1, len(edges)):
                    a, b = edges[i], edges[j]
                    self.assertEqual(crossings(a[1:-1], b[1:-1]), 0, str(ext))
                    for p, q in ((a, b), (b, a)):
                        far = np.sqrt(((p[:, None, :] - verts[None]) ** 2).sum(2)).min(1) > 0.30 * k
                        if far.any():
                            self.assertGreaterEqual(min_dist(p[far], q).min(), 0.10 * k, str(ext))

    def test_neighbouring_pieces_share_their_edge_exactly(self):
        r = build(4, 3, 120, 90, seed=5)
        piece = {pc.id: pc.cut for pc in r.pieces}
        for row in range(3):
            for col in range(3):
                x_edge = (col + 1) * 120 / 4
                a = {(round(x, 6), round(y, 6)) for x, y in piece[(col, row)] if abs(x - x_edge) < 20}
                b = {(round(x, 6), round(y, 6)) for x, y in piece[(col + 1, row)] if abs(x - x_edge) < 20}
                self.assertGreater(len(a & b), 40, "les deux pièces ne partagent pas leur arête")

    def test_every_piece_outline_is_simple(self):
        for ext in (EXTREMES[0], EXTREMES[-1]):
            r = build(5, 4, 119.21, 65.02, 3, **ext)
            for pc in r.pieces:
                cut = list(pc.cut)
                if cut[0] == cut[-1]:
                    cut = cut[:-1]
                pts = np.array(cut + [cut[0]])
                self.assertEqual(crossings(pts, pts, same=True, closed=True), 0, f"pièce {pc.id} qui se recoupe")

    def test_crossing_helper_detects_a_real_self_intersection(self):
        bowtie = np.array([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)], dtype=float)
        self.assertEqual(crossings(bowtie, bowtie, same=True, closed=True), 1)
        square = np.array([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)], dtype=float)
        self.assertEqual(crossings(square, square, same=True, closed=True), 0)


class PuzzleCutOrderTests(unittest.TestCase):
    def test_outline_is_always_cut_last_whatever_the_incoming_order(self):
        """Le contour extérieur doit sortir DERNIER : une fois coupé, le puzzle n'est plus tenu par la planche,
        donc tout le reste doit déjà être découpé (sinon pièce qui bouge, coupes décalées)."""
        for kerf in (0.0, 0.1):
            for (cols, rows, w, h) in GRIDS:
                for seed in (1, 2, 3):
                    r = pg.build_puzzle(pg.PuzzleParams(width=w, height=h, nx=cols, ny=rows, seed=seed, kerf=kerf))
                    polygons = [list(r.outline)] + [list(e) for e in r.edges]
                    rng = random.Random(seed)
                    for _ in range(6):
                        mixed = polygons[:]
                        rng.shuffle(mixed)
                        self.assertEqual(vo.order_polygons_inner_first(mixed)[-1], list(r.outline))


if __name__ == "__main__":
    unittest.main()
