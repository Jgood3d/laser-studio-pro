"""Générateur de boîte (vector/box_generator.py) : géométrie, couvercles, cloisons.

Contrôle 3D : chaque panneau est découpé en cellules rectangulaires, replacées dans l'espace de la
boîte (X largeur, Y profondeur, Z hauteur). Deux pièces ne doivent jamais se chevaucher, et, avec un
jeu nul, le volume total de matière est exactement celui de la boîte assemblée (aucun vide dans
les assemblages)."""
import itertools
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector import box_generator as bg  # noqa: E402

EPS = 1e-6


# ----------------------------------------------------------------------
# Passage d'un panneau (u, v, profondeur) à l'espace 3D
# ----------------------------------------------------------------------
def _mapping(name, p, result):
    """Fonction (u, v, f) -> (x, y, z), f = fraction d'épaisseur 0..1 (de l'extérieur vers l'intérieur
    pour les parois ; de bas en haut pour les plaques horizontales)."""
    W, D, H = result.outer
    t, cl = p.thickness, p.clearance
    kind = bg.lid_kind(p)
    half = cl / 2.0
    if name == "front":
        return lambda u, v, f: (u, f * t, v)
    if name == "back":
        return lambda u, v, f: (W - u, D - t + f * t, v)
    if name == "left":
        return lambda u, v, f: (f * t, D - u, v)
    if name == "right":
        return lambda u, v, f: (W - t + f * t, u, v)
    if name == "bottom":
        return lambda u, v, f: (W - u, v, f * t)
    if name == "top":
        if kind == "sliding":
            _, front_h = bg.wall_heights(p, H)
            return lambda u, v, f: (half + u, v, front_h + half + f * t)
        return lambda u, v, f: (u, v, H - t + f * t)
    if name == "lip":
        return lambda u, v, f: (t + half + u, t + half + v, H - 2 * t + f * t)
    if name.startswith("hinge"):                       # plaque de charnière à axe : plan YZ, hinge<i>_<j>
        i, j = (int(x) - 1 for x in name[len("hinge"):].split("_"))
        x0 = bg.pin_hinge_columns(p, W)[i][j][0]
        return lambda u, v, f: (x0 + f * t, u, v)
    if name.startswith("magnet_"):                    # plaques d'aimant : plan XY, sous le couvercle (lid) / sur la façade (wall)
        kind, number = name[len("magnet_"):].rstrip("0123456789"), int(name[len("magnet_"):].lstrip("lidwa"))
        s_, xs = bg.magnet_layout(p, W)
        x0 = xs[number - 1] - s_ / 2.0
        if kind == "lid":
            return lambda u, v, f: (x0 + u, t + half + v, H - 2 * t + f * t)
        return lambda u, v, f: (x0 + u, t + v, H - 3 * t + f * t)
    if name.startswith("divider_x"):
        k = int(name[len("divider_x"):]) - 1
        pos = bg.divider_positions(W, int(p.dividers_x), t)[k]
        return lambda u, v, f: (pos + f * t, u, v)
    if name.startswith("divider_y"):
        k = int(name[len("divider_y"):]) - 1
        pos = bg.divider_positions(D, int(p.dividers_y), t)[k]
        return lambda u, v, f: (u, pos + f * t, v)
    raise KeyError(name)


def _inside(poly, x, y):
    """Point dans un polygone (lancer de rayon)."""
    c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def _inside_many(poly, xs, ys):
    """_inside pour des tableaux de points d'un coup (numpy), même règle du lancer de rayon : le découpage des
    plaques de charnière en cellules de 0,1 mm appelait _inside plus d'un million de fois par boîte."""
    pts = np.asarray(poly, dtype=float)
    x0, y0 = np.roll(pts[:, 0], 1), np.roll(pts[:, 1], 1)
    x1, y1 = pts[:, 0], pts[:, 1]
    inside = np.zeros(xs.shape, dtype=bool)
    for a0, b0, a1, b1 in zip(x0, y0, x1, y1):
        crosses = (b0 > ys) != (b1 > ys)
        with np.errstate(divide="ignore", invalid="ignore"):
            inside ^= crosses & (xs < (a1 - a0) * (ys - b0) / (b1 - b0) + a0)
    return inside


def _cells(panel):
    """Rectangles (u0, v0, u1, v1) qui recouvrent la matière du panneau (contour moins trous)."""
    loops = [panel.cut] + list(panel.holes)
    us = sorted({round(q[0], 9) for loop in loops for q in loop})
    vs = sorted({round(q[1], 9) for loop in loops for q in loop})
    cells = []
    for u0, u1 in zip(us, us[1:]):
        for v0, v1 in zip(vs, vs[1:]):
            cu, cv = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            if _inside(panel.cut, cu, cv) and not any(_inside(h, cu, cv) for h in panel.holes):
                cells.append((u0, v0, u1, v1))
    return cells


def _fine_cells(panel, step=0.1):
    """Petites cellules carrées (u0, v0, u1, v1) pour un panneau à contour courbe (plaque de charnière)."""
    us, vs = [q[0] for q in panel.cut], [q[1] for q in panel.cut]
    # Mêmes abscisses et ordonnées qu'une boucle « u += step » (les arrondis de l'addition compris).
    grid_u, u = [], min(us)
    while u < max(us):
        grid_u.append(u)
        u += step
    grid_v, v = [], min(vs)
    while v < max(vs):
        grid_v.append(v)
        v += step
    u, v = (a.ravel() for a in np.meshgrid(np.array(grid_u), np.array(grid_v), indexing="ij"))
    # Cellule « intérieure » : ses quatre coins et son centre dans la matière, jamais de débordement du contour,
    # donc pas de faux chevauchement quand deux pièces se touchent exactement (au plus un pas d'indulgence).
    keep = np.ones(u.shape, dtype=bool)
    for a, b in ((u, v), (u + step, v), (u, v + step), (u + step, v + step), (u + step / 2.0, v + step / 2.0)):
        keep &= _inside_many(panel.cut, a, b)
        for hole in panel.holes:
            keep &= ~_inside_many(hole, a, b)
    return [(cu, cv, cu + step, cv + step) for cu, cv in zip(u[keep].tolist(), v[keep].tolist())]


def _clip(cell, v_min, v_max):
    u0, v0, u1, v1 = cell
    lo, hi = max(v0, v_min), min(v1, v_max)
    return (u0, lo, u1, hi) if hi - lo > EPS else None


def _boxes(cells, fn):
    boxes = []
    for u0, v0, u1, v1 in cells:
        a, b = fn(u0, v0, 0.0), fn(u1, v1, 1.0)
        boxes.append(tuple(min(a[i], b[i]) for i in range(3)) + tuple(max(a[i], b[i]) for i in range(3)))
    return boxes


def solids(p, result):
    """{nom: [boîtes 3D (x0, y0, z0, x1, y1, z1)]}. Le couvercle à charnière, plié, est placé à plat sur la
    boîte ; la zone de charnière (courbe) n'est pas représentée."""
    out = {}
    W, D, H = result.outer
    for panel in result.panels:
        fn = _mapping(panel.name, p, result)
        cells = _fine_cells(panel) if panel.name.startswith("hinge") else _cells(panel)
        if panel.name == "back" and bg.lid_kind(p) == "hinged":
            wall_top = bg.wall_heights(p, H)[1]
            start = wall_top + p.hinge_length
            y_c = D - p.thickness / 2.0 - bg.hinge_radius(p)
            t = p.thickness
            lid_fn = lambda u, v, f: (W - u, y_c - (v - start), H - t + f * t)
            wall = [c for c in (_clip(c, 0.0, wall_top) for c in cells) if c]
            lid = [c for c in (_clip(c, start, 1e9) for c in cells) if c]
            out["back"] = _boxes(wall, fn)
            out["lid"] = _boxes(lid, lid_fn)
            continue
        out[panel.name] = _boxes(cells, fn)
    return out


def overlap_volume(a, b):
    dx = min(a[3], b[3]) - max(a[0], b[0])
    dy = min(a[4], b[4]) - max(a[1], b[1])
    dz = min(a[5], b[5]) - max(a[2], b[2])
    return dx * dy * dz if dx > EPS and dy > EPS and dz > EPS else 0.0


def volume(boxes):
    return sum((b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2]) for b in boxes)


def collisions(all_solids):
    """[(nom_a, nom_b, volume)] pour chaque paire de pièces qui se chevauchent."""
    found = []
    extents = {n: _extent(b) for n, b in all_solids.items()}
    for (na, ba), (nb, bb) in itertools.combinations(all_solids.items(), 2):
        ea, eb = extents[na], extents[nb]
        lo = [max(ea[i], eb[i]) for i in range(3)]
        hi = [min(ea[i + 3], eb[i + 3]) for i in range(3)]
        if any(hi[i] - lo[i] <= EPS for i in range(3)):
            continue                                                 # étendues disjointes : rien à comparer
        near = lambda b: all(b[i + 3] > lo[i] and b[i] < hi[i] for i in range(3))
        total = sum(overlap_volume(x, y) for x in ba if near(x) for y in bb if near(y))
        if total > 1e-4:
            found.append((na, nb, total))
    return found


def _extent(boxes):
    if not boxes:
        return (0, 0, 0, 0, 0, 0)
    return tuple(min(b[i] for b in boxes) for i in range(3)) + tuple(max(b[i + 3] for b in boxes) for i in range(3))


# ----------------------------------------------------------------------
# Ouverture du couvercle à charnière à axe : pièces mobiles contre pièces fixes
# ----------------------------------------------------------------------
def _inverse(fn):
    o = fn(0.0, 0.0, 0.0)
    axes = [tuple(fn(*e)[i] - o[i] for i in range(3)) for e in ((1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0))]

    def inv(q):
        d = [q[i] - o[i] for i in range(3)]
        return tuple(sum(d[i] * a[i] for i in range(3)) / sum(a[i] * a[i] for i in range(3)) for a in axes)
    return inv


def sweep_collisions(p, angles, region=14.0):
    """[(mobile, fixe, angle)] : points du couvercle (arrière) et des plaques du couvercle qui entrent dans une
    pièce fixe quand le couvercle pivote de `angle` degrés autour de la tige (l'avant monte)."""
    result = bg.build_box(p)
    W, D, H = result.outer
    t = p.thickness
    axis_y, axis_z = D - t / 2.0, H - t / 2.0
    columns = bg.pin_hinge_columns(p, W)
    panels = {pn.name: pn for pn in result.panels}
    moving = {"top"} | {f"hinge{i + 1}_{j + 1}" for i, h in enumerate(columns)
                        for j, (_x0, fixed) in enumerate(h) if not fixed}
    fwd = {n: _mapping(n, p, result) for n in panels}
    inv = {n: _inverse(fwd[n]) for n in panels}
    extent = {n: _extent(b) for n, b in solids(p, result).items()}

    def solid_has(name, q):
        e = extent[name]
        if any(not (e[i] - EPS <= q[i] <= e[i + 3] + EPS) for i in range(3)):
            return False
        u, v, f = inv[name](q)
        panel = panels[name]
        return 0.0 < f < 1.0 and _inside(panel.cut, u, v) and not any(_inside(h, u, v) for h in panel.holes)

    samples = []
    for name in moving:
        panel = panels[name]
        if name == "top":
            us = [0.5 + i for i in range(int(W))]
            vs = [axis_y - region + 0.25 + 0.5 * i for i in range(int(region / 0.5))]
            fs = (0.25, 0.75)
        else:
            step = 0.4
            us = [min(q[0] for q in panel.cut) + step * (i + 0.5) for i in range(40)]
            vs = [min(q[1] for q in panel.cut) + step * (i + 0.5) for i in range(40)]
            fs = (0.5,)
        for u in us:
            for v in vs:
                if _inside(panel.cut, u, v) and not any(_inside(h, u, v) for h in panel.holes):
                    samples += [(name, fwd[name](u, v, f)) for f in fs]
    found = set()
    for angle in angles:
        phi = -math.radians(angle)
        c, s_ = math.cos(phi), math.sin(phi)
        for name, (x, y, z) in samples:
            dy, dz = y - axis_y, z - axis_z
            q = (x, axis_y + dy * c - dz * s_, axis_z + dy * s_ + dz * c)
            for other in panels:
                if other not in moving and solid_has(other, q):
                    found.add((name, other, angle))
    return sorted(found)


def make(**kw):
    defaults = dict(width=100.0, depth=70.0, height=50.0, thickness=3.0, kerf=0.0, clearance=0.0, gap=3.0,
                    pin_fit=0.0)
    defaults.update(kw)
    return bg.BoxParams(**defaults)


def check(test, p):
    result = bg.build_box(p)
    s = solids(p, result)
    test.assertEqual(collisions(s), [])
    return result, s, sum(volume(b) for b in s.values())


def shell_volume(W, D, H, t):
    return W * D * H - (W - 2 * t) * (D - 2 * t) * (H - 2 * t)


class LidTypeTests(unittest.TestCase):
    def test_finger_lid_is_the_original_box(self):
        p = make()
        result, _s, vol = check(self, p)
        self.assertEqual(sorted(x.name for x in result.panels), sorted(bg.FACE_NAMES))
        self.assertAlmostEqual(vol, shell_volume(100, 70, 50, 3), places=3)

    def test_open_box_has_no_top(self):
        p = make(lid=False)
        result, _s, vol = check(self, p)
        self.assertNotIn("top", [x.name for x in result.panels])
        self.assertEqual(len(result.panels), 5)
        self.assertAlmostEqual(vol, 100 * 70 * 50 - 94 * 64 * 47, places=3)

    def test_lip_lid(self):
        p = make(lid_type="lip")
        result, _s, vol = check(self, p)
        names = [x.name for x in result.panels]
        self.assertIn("top", names)
        self.assertIn("lip", names)
        expected = (100 * 70 * 47 - 94 * 64 * 44) + 100 * 70 * 3 + 94 * 64 * 3
        self.assertAlmostEqual(vol, expected, places=3)
        top = next(x for x in result.panels if x.name == "top")
        self.assertEqual((top.width, top.height), (100, 70))

    def test_sliding_lid(self):
        p = make(lid_type="sliding", clearance=0.0)
        result, s, vol = check(self, p)
        front = next(x for x in result.panels if x.name == "front")
        self.assertAlmostEqual(front.height, 50 - 2 * 3)                  # façade abaissée
        lid = next(x for x in result.panels if x.name == "top")
        self.assertAlmostEqual(lid.height, 70 - 2 * 3)
        # La rainure est un trou dans le contour des parois gauche et droite : ils ne se touchent pas.
        for side in ("left", "right"):
            panel = next(x for x in result.panels if x.name == side)
            self.assertGreater(len(panel.outline), 4)

    def test_sliding_lid_slot_height_follows_clearance(self):
        p = make(lid_type="sliding", clearance=0.3)
        result, _s, _v = check(self, p)
        front = next(x for x in result.panels if x.name == "front")
        self.assertAlmostEqual(front.height, 50 - 2 * 3 - 0.3)
        left = next(x for x in result.panels if x.name == "left")
        ys = sorted({round(q[1], 6) for q in left.outline})
        # La rainure occupe [hauteur de la façade, hauteur - t] : épaisseur t + jeu.
        self.assertIn(round(front.height, 6), ys)
        self.assertIn(round(50 - 3, 6), ys)

    def test_closed_lid_flag_off_overrides_type(self):
        for kind in ("lip", "sliding", "finger"):
            result = bg.build_box(make(lid=False, lid_type=kind))
            self.assertEqual(result.lid_type, "none")
            self.assertEqual(len(result.panels), 5)

    def test_every_type_is_collision_free_with_kerf_and_clearance(self):
        for kind in bg.LID_TYPES:
            for dims in ((100, 70, 50), (60, 60, 40), (151.7, 83.3, 47.9)):
                p = make(width=dims[0], depth=dims[1], height=dims[2], lid_type=kind, kerf=0.12, clearance=0.15)
                bg.build_box(p)                                           # pas d'erreur de contour
                p0 = make(width=dims[0], depth=dims[1], height=dims[2], lid_type=kind, clearance=0.15)
                check(self, p0)

    def test_inner_dimensions_with_lid_types(self):
        for kind in ("lip", "sliding"):
            result = bg.build_box(make(dimensions="inner", lid_type=kind))
            self.assertEqual(result.outer, (106.0, 76.0, 56.0))


class HingedLidTests(unittest.TestCase):
    def test_hinged_lid_geometry_and_volume(self):
        p = make(lid_type="hinged", hinge_length=20.0)
        result, s, vol = check(self, p)
        names = [x.name for x in result.panels]
        self.assertEqual(sorted(names), sorted(["front", "left", "right", "bottom", "back"]))   # le couvercle est dans « back »
        t, H, D, W = 3.0, 50.0, 70.0, 100.0
        wall_top = bg.wall_heights(p, H)[1]
        lid_len = bg.lid_length(p, D)
        shell = W * D * (H - t) - (W - 2 * t) * (D - 2 * t) * (H - 2 * t)
        missing_back = (W - 2 * t) * t * ((H - t) - wall_top)           # l'arrière s'arrête sous l'arc
        self.assertAlmostEqual(vol, shell - missing_back + W * lid_len * t, places=3)

    def test_back_panel_is_wall_hinge_and_lid_in_one_piece(self):
        p = make(lid_type="hinged", hinge_length=20.0)
        result = bg.build_box(p)
        back = next(x for x in result.panels if x.name == "back")
        wall_top = bg.wall_heights(p, 50.0)[1]
        self.assertAlmostEqual(back.height, wall_top + 20.0 + bg.lid_length(p, 70.0))
        self.assertEqual(back.width, 100.0)
        u0, v0, u1, v1 = back.faces["top"]
        self.assertAlmostEqual(v0, wall_top + 20.0)
        self.assertAlmostEqual(v1, back.height)
        self.assertEqual((u0, u1), (0.0, 100.0))

    def test_hinge_radius_matches_quarter_turn(self):
        p = make(lid_type="hinged", hinge_length=20.0)
        import math
        self.assertAlmostEqual(math.pi / 2 * bg.hinge_radius(p), 20.0)
        # La plaque repose sur les parois : ligne neutre de la plaque à H - t / 2.
        wall_top = bg.wall_heights(p, 50.0)[1]
        self.assertAlmostEqual(wall_top + bg.hinge_radius(p), 50.0 - 3.0 / 2.0)

    def test_slits_stay_in_the_hinge_zone(self):
        p = make(lid_type="hinged", hinge_length=20.0)
        back = next(x for x in bg.build_box(p).panels if x.name == "back")
        wall_top = bg.wall_heights(p, 50.0)[1]
        self.assertGreater(len(back.slits), 20)
        for (ua, va), (ub, vb) in back.slits:
            self.assertAlmostEqual(va, vb)
            self.assertGreater(va, wall_top)
            self.assertLess(va, wall_top + 20.0)
            self.assertGreaterEqual(min(ua, ub), bg.HINGE_MARGIN - 1e-9)
            self.assertLessEqual(max(ua, ub), 100.0 - bg.HINGE_MARGIN + 1e-9)
            self.assertGreater(ub - ua, 0.5)

    def test_slit_rows_are_staggered(self):
        slits = bg.hinge_slits(100.0, 0.0, 20.0)
        rows = {}
        for (ua, va), (ub, _vb) in slits:
            rows.setdefault(round(va, 6), []).append((ua, ub))
        ordered = [sorted(rows[k]) for k in sorted(rows)]
        self.assertGreaterEqual(len(ordered), 2)
        for a, b in zip(ordered, ordered[1:]):
            gaps_a = [y[0] - x[1] for x, y in zip(a, a[1:])]
            centres_a = [(x[1] + y[0]) / 2 for x, y in zip(a, a[1:])]
            for c in centres_a:                       # le pont d'une rangée tombe au milieu d'une fente de la suivante
                self.assertTrue(any(s0 < c < s1 for s0, s1 in b))
            for g in gaps_a:
                self.assertAlmostEqual(g, bg.HINGE_BRIDGE)

    def test_slits_cover_the_row_without_overlap_or_bridges_in_line(self):
        for width in (30.0, 61.3, 100.0, 250.0):
            for row in bg.hinge_slits(width, 0.0, 10.0):
                pass
            by_row = {}
            for (ua, va), (ub, _v) in bg.hinge_slits(width, 0.0, 10.0):
                by_row.setdefault(round(va, 6), []).append((ua, ub))
            for segs in by_row.values():
                segs.sort()
                for (a0, a1), (b0, b1) in zip(segs, segs[1:]):
                    self.assertLessEqual(a1, b0 + 1e-9)

    def test_decor_face_top_is_the_lid(self):
        result = bg.build_box(make(lid_type="hinged"))
        faces = result.face_panels()
        self.assertIn("top", faces)
        cx, cy = faces["top"].face_center()
        back = next(x for x in result.panels if x.name == "back")
        u0, v0, u1, v1 = back.faces["top"]
        self.assertAlmostEqual(cx, back.x + (u0 + u1) / 2)
        self.assertAlmostEqual(cy, back.y + (v0 + v1) / 2)
        self.assertIs(faces["front"], next(x for x in result.panels if x.name == "front"))

    def test_hinged_with_kerf_clearance_and_sizes_is_collision_free(self):
        for dims in ((100, 70, 50), (150, 110, 60), (151.7, 83.3, 57.9)):
            for hinge in (12.0, 20.0, 30.0):
                p = make(width=dims[0], depth=dims[1], height=dims[2], lid_type="hinged", hinge_length=hinge,
                         clearance=0.1)
                check(self, p)
                bg.build_box(make(width=dims[0], depth=dims[1], height=dims[2], lid_type="hinged",
                                  hinge_length=hinge, kerf=0.12, clearance=0.1))

    def test_dividers_with_hinged_lid(self):
        for nx, ny in ((1, 0), (0, 2), (2, 2)):
            p = make(width=140, depth=110, height=70, lid_type="hinged", dividers_x=nx, dividers_y=ny,
                     clearance=0.1)
            check(self, p)
            result = bg.build_box(p)
            back = next(x for x in result.panels if x.name == "back")
            wall_top = bg.wall_heights(p, 70.0)[1]
            for hole in back.holes:                     # les fentes restent dans la partie murale de l'arrière
                self.assertLess(max(q[1] for q in hole), wall_top - 3.0 + 1e-6)

    def test_slits_are_not_laid_out_inside_other_panels(self):
        result = bg.build_box(make(lid_type="hinged", max_width=300.0))
        back = next(x for x in result.panels if x.name == "back")
        x0, y0, x1, y1 = back.bounds()
        for slit in back.placed_slits():
            for sx, sy in slit:
                self.assertTrue(x0 - 1e-6 <= sx <= x1 + 1e-6 and y0 - 1e-6 <= sy <= y1 + 1e-6)

    def test_hinge_validation(self):
        for kw, code in ((dict(hinge_length=5.0), "hinge_length"), (dict(hinge_length=150.0), "hinge_length"),
                         (dict(hinge_length=60.0, depth=45.0), "hinge_too_long")):
            with self.assertRaises(bg.BoxError) as ctx:
                bg.build_box(make(lid_type="hinged", **kw))
            self.assertEqual(ctx.exception.code, code, kw)

    def test_hinge_length_ignored_for_other_lids(self):
        bg.build_box(make(lid_type="finger", hinge_length=1.0))

    def test_open_box_flag_overrides_hinged(self):
        result = bg.build_box(make(lid=False, lid_type="hinged"))
        self.assertEqual(result.lid_type, "none")
        back = next(x for x in result.panels if x.name == "back")
        self.assertEqual(back.slits, [])


class PinnedHingeTests(unittest.TestCase):
    def pin(self, **kw):
        base = dict(width=120.0, depth=90.0, height=60.0, lid_type="pinned", clearance=0.25)
        base.update(kw)
        return make(**base)

    def test_panels_and_pin_info(self):
        result = bg.build_box(self.pin(hinge_count=2, hinge_plates=3, pin_diameter=3.0))
        names = [x.name for x in result.panels]
        self.assertEqual(len([n for n in names if n.startswith("hinge")]), 6)
        self.assertIn("top", names)
        self.assertEqual(result.pin, (1, 3.0, 120.0))              # une tige sur toute la largeur
        self.assertEqual(bg.build_box(self.pin(pin_through=False)).pin, (2, 3.0, 9.0))
        self.assertEqual(result.lid_type, "pinned")
        self.assertEqual(bg.build_box(self.pin(lid=False)).pin, ())

    def test_plates_alternate_between_box_and_lid(self):
        p = self.pin(hinge_count=1, hinge_plates=5)
        result = bg.build_box(p)
        W, D, H = result.outer
        pin = bg.pin_geometry(p)
        axis_y, axis_z = D - 1.5, H - 1.5
        plates = {x.name: x for x in result.panels if x.name.startswith("hinge")}
        self.assertEqual(sorted(plates), [f"hinge1_{j}" for j in range(1, 6)])
        for j in range(1, 6):
            xs = [q[0] for q in plates[f"hinge1_{j}"].outline]
            zs = [q[1] for q in plates[f"hinge1_{j}"].outline]
            if j % 2 == 1:                                       # plaque de la boîte : pied vers le bas
                self.assertAlmostEqual(min(zs), (H - 3) - pin.foot, places=6)
                self.assertAlmostEqual(min(xs), axis_y - pin.radius, delta=0.02)      # cercle discrétisé
            else:                                                # plaque du couvercle : bras vers l'avant
                self.assertAlmostEqual(min(xs), axis_y - pin.arm, places=6)
                self.assertAlmostEqual(min(zs), axis_z - pin.radius, delta=0.02)

    def test_plate_has_one_round_hole_for_the_pin(self):
        p = self.pin(pin_diameter=4.0, clearance=0.2, kerf=0.1, pin_through=False)
        plate = next(x for x in bg.build_box(p).panels if x.name == "hinge1_1")
        self.assertEqual(len(plate.holes), 1)
        area = abs(bg.polygon_area(plate.holes[0]))
        radius = math.sqrt(area / math.pi)
        self.assertAlmostEqual(radius, (4.0 + 0.2) / 2 - 0.05, delta=0.03)       # trou : jeu compris, kerf retranché
        self.assertLess(bg.polygon_area(plate.holes[0]), 0)                       # horaire = trou

    def test_kerf_grows_the_plate_and_keeps_the_nominal_outline(self):
        thin = next(x for x in bg.build_box(self.pin(kerf=0.0)).panels if x.name == "hinge1_2")
        fat = next(x for x in bg.build_box(self.pin(kerf=0.2)).panels if x.name == "hinge1_2")
        self.assertAlmostEqual(thin.outline[0][0], fat.outline[0][0])
        self.assertGreater(bg.polygon_area(fat.cut), bg.polygon_area(fat.outline))
        self.assertGreater(bg.polygon_area(fat.outline), 0)                       # anti-horaire

    def test_back_wall_is_notched_and_lid_has_matching_notches(self):
        p = self.pin(hinge_count=1, hinge_plates=3, clearance=0.0)
        result = bg.build_box(p)
        s = solids(p, result)
        W, D, H = result.outer
        pin = bg.pin_geometry(p)
        x0 = bg.pin_hinge_columns(p, W)[0][0][0]
        top = H - 3
        def wall_has(x, z):
            return any(b[0] < x < b[3] and b[2] < z < b[5] for b in s["back"])
        self.assertFalse(wall_has(x0 + 1.5, top - pin.foot + 0.1))               # colonne 1 (plaque fixe) : pied
        self.assertTrue(wall_has(x0 + 1.5, top - pin.foot - 0.1))
        self.assertFalse(wall_has(x0 + 4.5, top - pin.ring_depth + 0.1))         # colonne 2 (couvercle) : passage
        self.assertTrue(wall_has(x0 + 4.5, top - pin.ring_depth - 0.1))
        self.assertTrue(wall_has(x0 - 5, top - 0.1))                             # ailleurs : paroi pleine
        lid = next(x for x in result.panels if x.name == "top")
        self.assertEqual((lid.width, lid.height), (120.0, D - 1.5))
        self.assertGreater(len(lid.outline), 4)

    def test_closed_pinned_box_is_collision_free_in_many_sizes(self):
        for dims, kw in (((120, 90, 60), {}), ((200, 150, 80), dict(hinge_count=3, hinge_plates=5)),
                         ((90, 70, 45), dict(hinge_count=1, pin_diameter=2.0)),
                         ((130.3, 77.7, 52.1), dict(hinge_plates=7, hinge_count=1, pin_diameter=3.0, pin_through=False, hinge_style="butterfly"))):
            p = self.pin(width=dims[0], depth=dims[1], height=dims[2], **kw)
            check(self, p)
            bg.build_box(self.pin(width=dims[0], depth=dims[1], height=dims[2], kerf=0.12, **kw))

    def test_lid_opens_to_110_degrees_without_touching_anything(self):
        for kw in ({}, dict(hinge_count=1, hinge_plates=5), dict(dividers_x=1, dividers_y=1)):
            p = self.pin(**kw)
            self.assertEqual(sweep_collisions(p, range(0, 111, 10)), [], msg=str(kw))

    def test_sweep_detects_a_collision_when_the_clearance_is_missing(self):
        """Garde-fou du test d'ouverture : sans dégagement dans la paroi arrière, les anneaux la heurtent."""
        p = self.pin()
        pin = bg.pin_geometry(p)
        shallow = bg.PinGeometry(r_hole=pin.r_hole, radius=pin.radius, ring_depth=0.0, foot=pin.foot, arm=pin.arm,
                                 r_ear=pin.r_ear, ear=pin.ear)
        original = bg.pin_geometry
        bg.pin_geometry = lambda params: shallow
        try:
            self.assertTrue(sweep_collisions(p, (60, 110)))
        finally:
            bg.pin_geometry = original

    def test_dividers_with_pinned_lid(self):
        for nx, ny in ((1, 0), (3, 1), (0, 2)):
            check(self, self.pin(dividers_x=nx, dividers_y=ny, width=150, depth=110, height=70))

    def test_divider_tabs_stay_below_the_hinge_notches(self):
        p = self.pin(dividers_x=2, width=150, depth=110, height=70)
        result = bg.build_box(p)
        back = next(x for x in result.panels if x.name == "back")
        floor = (70 - 3) - bg.pin_geometry(p).foot
        for hole in back.holes:
            self.assertLessEqual(max(q[1] for q in hole), floor - 3 + 1e-6)

    def test_decor_face_top_and_layout(self):
        result = bg.build_box(self.pin(max_width=400.0))
        self.assertIn("top", result.face_panels())
        self.assertLessEqual(result.width, 400.0 + 1e-6)
        boxes = [x.bounds() for x in result.panels]
        for (a0, b0, a1, b1), (c0, d0, c1, d1) in itertools.combinations(boxes, 2):
            self.assertTrue(a1 <= c0 + 1e-9 or c1 <= a0 + 1e-9 or b1 <= d0 + 1e-9 or d1 <= b0 + 1e-9)

    def test_hinge_settings_ignored_for_other_lids(self):
        result = bg.build_box(make(hinge_plates=4, pin_diameter=99.0, hinge_count=9))
        self.assertEqual(sorted(x.name for x in result.panels), sorted(bg.FACE_NAMES))

    def test_validation(self):
        cases = (("pin_diameter", dict(pin_diameter=0.1)), ("pin_diameter", dict(pin_diameter=20.0)),
                 ("hinge_count", dict(hinge_count=0)), ("hinge_count", dict(hinge_count=bg.MAX_HINGES + 1)),
                 ("hinge_plates", dict(hinge_plates=4)), ("hinge_plates", dict(hinge_plates=1)),
                 ("hinge_plates", dict(hinge_plates=11)),
                 ("hinges_dont_fit", dict(width=60.0, hinge_count=3)),
                 ("too_small", dict(height=15.0)),
                 ("hinge_too_long", dict(depth=18.0)))
        for code, kw in cases:
            with self.assertRaises(bg.BoxError, msg=str(kw)) as ctx:
                bg.build_box(self.pin(**kw))
            self.assertEqual(ctx.exception.code, code, msg=str(kw))


class DividerTests(unittest.TestCase):
    def test_one_divider_each_way_is_exact_with_zero_clearance(self):
        p = make(dividers_x=1, dividers_y=1)
        result, s, vol = check(self, p)
        names = [x.name for x in result.panels]
        self.assertIn("divider_x1", names)
        self.assertIn("divider_y1", names)
        height = 50 - 3 - 3                                                # entre fond et couvercle
        inner = 94 * 64 * height
        union = 3 * 64 * height + 3 * 94 * height - 3 * 3 * height
        self.assertAlmostEqual(vol, shell_volume(100, 70, 50, 3) + union, places=3)
        self.assertEqual(inner and result.dividers, (1, 1))

    def test_several_dividers_open_box(self):
        p = make(lid=False, dividers_x=3, dividers_y=2)
        result, s, vol = check(self, p)
        self.assertEqual(len(result.panels), 5 + 5)
        height = 50 - 3
        union = 3 * (3 * 64 * height) + 2 * (3 * 94 * height) - 3 * 2 * 3 * 3 * height
        self.assertAlmostEqual(vol, 100 * 70 * 50 - 94 * 64 * 47 + union, places=3)

    def test_walls_get_slots_as_holes(self):
        p = make(dividers_x=2, dividers_y=0)
        result = bg.build_box(p)
        by = {x.name: x for x in result.panels}
        self.assertEqual(len(by["front"].holes), 2)
        self.assertEqual(len(by["back"].holes), 2)
        self.assertEqual(len(by["bottom"].holes) % 2, 0)                  # mêmes languettes pour chaque cloison
        self.assertGreaterEqual(len(by["bottom"].holes), 2)
        self.assertEqual(by["left"].holes, [])
        self.assertEqual(by["top"].holes, [])

    def test_holes_shrink_with_kerf(self):
        thin = bg.build_box(make(dividers_x=1, kerf=0.0)).panels
        fat = bg.build_box(make(dividers_x=1, kerf=0.2)).panels
        w_thin = _width(next(x for x in thin if x.name == "front").holes[0])
        w_fat = _width(next(x for x in fat if x.name == "front").holes[0])
        self.assertAlmostEqual(w_thin - w_fat, 0.2, places=6)

    def test_clearance_widens_slots_and_notches(self):
        a = bg.build_box(make(dividers_x=1, dividers_y=1, clearance=0.0))
        b = bg.build_box(make(dividers_x=1, dividers_y=1, clearance=0.2))
        wa = _width(next(x for x in a.panels if x.name == "front").holes[0])
        wb = _width(next(x for x in b.panels if x.name == "front").holes[0])
        self.assertAlmostEqual(wb - wa, 0.2, places=6)

    def test_dividers_with_every_lid_type_do_not_collide(self):
        for kind in bg.LID_TYPES:
            for lid in (True, False):
                for nx, ny in ((1, 0), (0, 2), (2, 2), (3, 1)):
                    p = make(width=140, depth=110, height=60, lid=lid, lid_type=kind,
                             dividers_x=nx, dividers_y=ny, clearance=0.1)
                    check(self, p)
                    bg.build_box(make(width=140, depth=110, height=60, lid=lid, lid_type=kind,
                                      dividers_x=nx, dividers_y=ny, clearance=0.1, kerf=0.15))

    def test_divider_tops_stay_under_the_lid(self):
        for kind, lid, top in (("finger", True, 47), ("lip", True, 44), ("sliding", True, 44), ("finger", False, 50)):
            p = make(lid=lid, lid_type=kind, dividers_x=1, clearance=0.0)
            result = bg.build_box(p)
            divider = next(x for x in result.panels if x.name == "divider_x1")
            self.assertAlmostEqual(divider.height, top - 3 + 3, msg=f"{kind} {lid}")      # hauteur + languettes du bas

    def test_odd_sizes_and_fractional_positions(self):
        p = make(width=137.3, depth=91.7, height=58.1, thickness=2.5, dividers_x=2, dividers_y=3, clearance=0.0)
        check(self, p)

    def test_compartments_are_equal(self):
        positions = bg.divider_positions(100, 3, 3)
        gaps = [positions[0] - 3] + [b - a - 3 for a, b in zip(positions, positions[1:])] + [100 - 3 - (positions[-1] + 3)]
        for g in gaps:
            self.assertAlmostEqual(g, gaps[0])
        self.assertAlmostEqual(sum(gaps) + 3 * 3, 94)

    def test_layout_contains_dividers_and_fits_max_width(self):
        p = make(dividers_x=2, dividers_y=2, max_width=300.0)
        result = bg.build_box(p)
        self.assertLessEqual(result.width, 300.0 + 1e-6)
        boxes = [x.bounds() for x in result.panels]
        for (a0, b0, a1, b1), (c0, d0, c1, d1) in itertools.combinations(boxes, 2):
            apart = a1 <= c0 + 1e-9 or c1 <= a0 + 1e-9 or b1 <= d0 + 1e-9 or d1 <= b0 + 1e-9
            self.assertTrue(apart)


def _width(loop):
    xs = [q[0] for q in loop]
    ys = [q[1] for q in loop]
    return min(max(xs) - min(xs), max(ys) - min(ys))


class ValidationTests(unittest.TestCase):
    def code(self, **kw):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(make(**kw))
        return ctx.exception.code

    def test_bad_lid_type(self):
        self.assertEqual(self.code(lid_type="nope"), "lid_type")

    def test_bad_clearance(self):
        self.assertEqual(self.code(clearance=-0.1), "clearance")
        self.assertEqual(self.code(clearance=3.0), "clearance")

    def test_bad_divider_count(self):
        self.assertEqual(self.code(dividers_x=-1), "dividers")
        self.assertEqual(self.code(dividers_y=bg.MAX_DIVIDERS + 1), "dividers")

    def test_compartment_too_small(self):
        self.assertEqual(self.code(dividers_x=9), "compartment_too_small")

    def test_dividers_too_low(self):
        self.assertEqual(self.code(height=14, dividers_x=1), "dividers_too_low")

    def test_sliding_lid_needs_height_for_the_front(self):
        self.assertEqual(self.code(height=14, lid_type="sliding"), "too_small")

    def test_legacy_defaults_unchanged(self):
        result = bg.build_box(make(clearance=0.1))
        self.assertEqual(sorted(x.name for x in result.panels), sorted(bg.FACE_NAMES))
        self.assertEqual(result.finger_counts, {"W": 11, "D": 7, "H": 5})


class OutlineTests(unittest.TestCase):
    def test_loops_report_holes_clockwise(self):
        loops = bg.rectilinear_loops([(0, 0, 10, 10)], [(3, 3, 6, 6)])
        areas = sorted(bg.polygon_area(l) for l in loops)
        self.assertAlmostEqual(areas[0], -9.0)
        self.assertAlmostEqual(areas[1], 100.0)

    def test_outline_wrapper_still_rejects_several_outlines(self):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.rectilinear_outline(10, 10, [(3, 3, 6, 6)])
        self.assertEqual(ctx.exception.code, "several_outlines")

    def test_touching_hole_is_pinched(self):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.rectilinear_loops([(0, 0, 10, 10)], [(0, 0, 3, 3), (3, 3, 6, 6)])
        self.assertEqual(ctx.exception.code, "pinched_panel")


def _poly_has(panel, u, v):
    return _inside(panel.cut, u, v) and not any(_inside(h, u, v) for h in panel.holes)


class RetentionButterflyHandleTests(unittest.TestCase):
    def pin(self, **kw):
        base = dict(width=120.0, depth=90.0, height=60.0, lid_type="pinned", clearance=0.25)
        base.update(kw)
        return make(**base)

    # --- tige traversante -------------------------------------------------
    def test_side_walls_carry_the_rod_hole_whatever_the_priority(self):
        for priority in (bg.DEFAULT_PRIORITY, ("left", "right", "front", "back", "top", "bottom"),
                         ("top", "bottom", "right", "left", "front", "back")):
            p = self.pin(priority=priority, kerf=0.1, pin_fit=0.1)
            result = bg.build_box(p)
            pin = bg.pin_geometry(p)
            D, H = result.outer[1], result.outer[2]
            for name, axis_u in (("right", D - 1.5), ("left", 1.5)):
                panel = next(x for x in result.panels if x.name == name)
                self.assertEqual(len(panel.holes), 1)
                hole = panel.holes[0]
                cu = sum(q[0] for q in hole) / len(hole)
                cv = sum(q[1] for q in hole) / len(hole)
                self.assertAlmostEqual(cu, axis_u, places=6)
                self.assertAlmostEqual(cv, H - 1.5, places=6)
                self.assertAlmostEqual(math.sqrt(abs(bg.polygon_area(hole)) / math.pi), pin.r_ear - 0.05, delta=0.03)
                self.assertGreater(max(q[1] for q in panel.outline), H - 1.5 + pin.ear - 0.02)   # l'oreille dépasse

    def test_ears_and_collisions(self):
        for priority in (bg.DEFAULT_PRIORITY, ("left", "right", "front", "back", "top", "bottom")):
            check(self, self.pin(priority=priority))
            check(self, self.pin(priority=priority, dividers_x=2, dividers_y=1, width=150, depth=110, height=70))

    def test_lid_opens_with_ears(self):
        self.assertEqual(sweep_collisions(self.pin(), range(0, 111, 10)), [])
        self.assertEqual(sweep_collisions(self.pin(hinge_style="butterfly", plate_radius=7.0), range(0, 111, 10)), [])

    def test_through_rod_is_limited_to_the_thickness(self):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(self.pin(pin_diameter=4.0))
        self.assertEqual(ctx.exception.code, "pin_diameter")
        bg.build_box(self.pin(pin_diameter=4.0, pin_through=False))

    def test_press_fit_narrows_the_foot_slot(self):
        loose, tight = (bg.build_box(self.pin(pin_fit=f)) for f in (0.0, 0.2))
        def slot_width(result):
            back = next(x for x in result.panels if x.name == "back")
            top = max(q[1] for q in back.outline)
            deep = top - bg.pin_geometry(self.pin()).foot + 0.1          # sous le passage des anneaux
            xs = sorted({q[0] for q in back.outline if q[1] < deep + 1.0 and q[1] > deep - 1.0})
            return xs
        self.assertEqual(len(slot_width(loose)), len(slot_width(tight)))
        back_l = next(x for x in loose.panels if x.name == "back")
        back_t = next(x for x in tight.panels if x.name == "back")
        self.assertGreater(bg.polygon_area(back_t.outline), bg.polygon_area(back_l.outline))   # fente plus étroite
        with self.assertRaises(bg.BoxError):
            bg.build_box(self.pin(pin_fit=1.0))

    # --- papillon ----------------------------------------------------------
    def test_butterfly_plates_stay_inside_the_hinge_circle(self):
        p = self.pin(hinge_style="butterfly", plate_radius=7.0, kerf=0.1)
        result = bg.build_box(p)
        pin = bg.pin_geometry(p)
        self.assertAlmostEqual(pin.radius, 7.0)
        axis = (90 - 1.5, 60 - 1.5)
        for panel in result.panels:
            if not panel.name.startswith("hinge"):
                continue
            self.assertEqual(len(panel.holes), 1)
            self.assertGreater(bg.polygon_area(panel.outline), 0)
            for u, v in panel.outline:
                d = math.hypot(u - axis[0], v - axis[1])
                near_stub = abs(u - axis[0]) <= 1.5 + 1e-6 or abs(v - axis[1]) <= 1.5 + 1e-6
                if not near_stub:
                    self.assertLessEqual(d, pin.radius + 1e-6)
        round_plate = next(x for x in bg.build_box(self.pin(plate_radius=7.0)).panels if x.name == "hinge1_2")
        wings = next(x for x in result.panels if x.name == "hinge1_2")
        self.assertLess(bg.polygon_area(wings.outline), bg.polygon_area(round_plate.outline))

    def test_butterfly_box_is_collision_free(self):
        check(self, self.pin(hinge_style="butterfly", plate_radius=7.0))
        check(self, self.pin(hinge_style="butterfly", plate_radius=6.0))

    def test_hinge_style_and_radius_are_validated(self):
        for kw, code in ((dict(hinge_style="star"), "hinge_style"), (dict(plate_radius=2.0), "plate_radius"),
                         (dict(plate_radius=40.0), "plate_radius")):
            with self.assertRaises(bg.BoxError) as ctx:
                bg.build_box(self.pin(**kw))
            self.assertEqual(ctx.exception.code, code)

    # --- encoche d'ouverture ----------------------------------------------
    def test_handle_notch_on_every_lid_that_allows_it(self):
        for lid in ("lip", "sliding", "hinged", "pinned"):
            plain = bg.build_box(make(width=120.0, depth=90.0, height=60.0, lid_type=lid, clearance=0.2))
            for kerf in (0.0, 0.15):
                p = make(width=120.0, depth=90.0, height=60.0, lid_type=lid, clearance=0.2, handle=True,
                         handle_radius=10.0, kerf=kerf)
                result = bg.build_box(p)
                check(self, make(width=120.0, depth=90.0, height=60.0, lid_type=lid, clearance=0.2, handle=True,
                                 handle_radius=10.0))
                name = "back" if lid == "hinged" else "top"
                with_h = next(x for x in result.panels if x.name == name)
                without = next(x for x in plain.panels if x.name == name)
                self.assertNotEqual(len(with_h.outline), len(without.outline), msg=lid)
                if kerf == 0.0 and lid != "lip":
                    lost = abs(bg.polygon_area(without.outline)) - abs(bg.polygon_area(with_h.outline))
                    self.assertAlmostEqual(lost, math.pi * 100 / 2.0, delta=1.0, msg=lid)

    def test_handle_kerf_shrinks_the_cut_circle(self):
        p = make(width=120.0, depth=90.0, height=60.0, lid_type="sliding", handle=True, handle_radius=10.0, kerf=0.2)
        top = next(x for x in bg.build_box(p).panels if x.name == "top")
        cu = (120.0 - 0.0) / 2.0
        arc = [q for q in top.cut if q[1] > 0.5 and abs(q[0] - cu) < 10.5]
        self.assertTrue(arc)
        for u, v in arc:
            self.assertAlmostEqual(math.hypot(u - cu, v), 10.0 - 0.1, delta=1e-6)
        self.assertAlmostEqual(max(q[1] for q in arc), 10.0 - 0.1, delta=0.05)     # arc discrétisé

    def test_handle_rules(self):
        base = dict(width=120.0, depth=90.0, height=60.0, handle=True)
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(make(lid_type="finger", **base))
        self.assertEqual(ctx.exception.code, "handle_finger")
        bg.build_box(make(lid_type="finger", lid=False, **base))              # boîte ouverte : sans effet
        for radius in (1.0, 500.0):
            with self.assertRaises(bg.BoxError) as ctx:
                bg.build_box(make(lid_type="sliding", handle_radius=radius, **base))
            self.assertEqual(ctx.exception.code, "handle_radius")
        low, high = bg.handle_limit(make(lid_type="sliding", **base), 120.0, 90.0)
        self.assertLess(low, high)


class EngraveAndMagnetTests(unittest.TestCase):
    def box(self, **kw):
        base = dict(width=120.0, depth=90.0, height=60.0, lid_type="pinned", clearance=0.2)
        base.update(kw)
        return make(**base)

    def test_motif_is_centred_on_the_top_face_and_inside_it(self):
        for lid in ("finger", "lip", "sliding", "hinged", "pinned"):
            p = self.box(lid_type=lid, engrave_motif=True, motif_size=30.0)
            result = bg.build_box(p)
            self.assertEqual(len(result.motif), 2, msg=lid)
            cx, cy = result.face_panels()["top"].face_center()
            xs = [q[0] for q in result.motif[0]]
            ys = [q[1] for q in result.motif[0]]
            self.assertAlmostEqual(max(xs) - min(xs), 30.0, delta=0.5, msg=lid)
            self.assertAlmostEqual((max(xs) + min(xs)) / 2.0, cx, delta=0.5, msg=lid)
            self.assertLess(abs((max(ys) + min(ys)) / 2.0 - cy), 5.0, msg=lid)
        self.assertEqual(bg.build_box(self.box(engrave_motif=True, lid=False)).motif, [])      # boîte ouverte
        self.assertEqual(bg.build_box(self.box()).motif, [])

    def test_motif_size_limits(self):
        for size in (2.0, 500.0):
            with self.assertRaises(bg.BoxError) as ctx:
                bg.build_box(self.box(engrave_motif=True, motif_size=size))
            self.assertEqual(ctx.exception.code, "motif_size")
        # avec une encoche, le papillon reste à distance
        low, free = bg.motif_limit(self.box(), 120.0, 90.0)
        _low, with_handle = bg.motif_limit(self.box(handle=True, handle_radius=12.0), 120.0, 90.0)
        self.assertLess(with_handle, free)

    def test_index_numbers_sit_inside_their_panel(self):
        p = self.box(engrave_index=True, index_size=4.0, dividers_x=1)
        result = bg.build_box(p)
        self.assertGreaterEqual(len(result.index), 5)
        seen = set()
        for text, x, y, size in result.index:
            number = int(text)
            self.assertNotIn(number, seen)
            seen.add(number)
            panel = result.panels[number - 1]
            w, h = 0.7 * size * len(text), size
            for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (-w / 2, h / 2), (w / 2, h / 2)):
                self.assertTrue(_inside(panel.placed(), x + dx, y + dy), msg=f"{text} {dx},{dy}")
                self.assertFalse(any(_inside(hole, x + dx, y + dy) for hole in panel.placed_holes()))
        self.assertEqual(bg.build_box(self.box()).index, [])
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(self.box(engrave_index=True, index_size=0.5))
        self.assertEqual(ctx.exception.code, "index_size")

    def test_index_avoids_the_hinge_zone(self):
        p = self.box(lid_type="hinged", engrave_index=True, index_size=4.0)
        result = bg.build_box(p)
        back = next(x for x in result.panels if x.name == "back")
        ys = [q[1] for sl in back.placed_slits() for q in sl]
        number = result.panels.index(back) + 1
        for text, x, y, size in result.index:
            if int(text) == number:
                self.assertFalse(min(ys) - size / 2 < y < max(ys) + size / 2)

    def test_magnet_plates_are_collision_free_and_face_to_face(self):
        for lid in ("pinned", "hinged"):
            for extra in ({}, dict(dividers_x=2, dividers_y=1, width=160.0, depth=120.0, height=70.0),
                          dict(magnet_count=1, magnet_diameter=8.0)):
                p = self.box(lid_type=lid, magnets=True, **extra)
                result, solid, _vol = check(self, p)
                names = [x.name for x in result.panels if x.name.startswith("magnet")]
                self.assertEqual(len(names), 2 * int(p.magnet_count))
                self.assertEqual(result.magnets, (int(p.magnet_count), p.magnet_diameter))
                a = solid["magnet_lid1"]
                b = solid["magnet_wall1"]
                top_b = max(box[5] for box in b)
                bottom_a = min(box[2] for box in a)
                self.assertAlmostEqual(top_b, bottom_a, places=6)            # les deux aimants se touchent

    def test_magnet_hole_matches_the_magnet(self):
        p = self.box(magnets=True, magnet_diameter=6.0, clearance=0.2, kerf=0.1)
        plate = next(x for x in bg.build_box(p).panels if x.name == "magnet_lid1")
        self.assertEqual(len(plate.holes), 1)
        radius = math.sqrt(abs(bg.polygon_area(plate.holes[0])) / math.pi)
        self.assertAlmostEqual(radius, (6.0 + 0.2) / 2 - 0.05, delta=0.03)

    def test_magnet_rules(self):
        cases = ((dict(lid_type="finger"), "magnet_lid"), (dict(lid_type="sliding"), "magnet_lid"),
                 (dict(magnet_diameter=1.0), "magnet_size"), (dict(magnet_count=9), "magnet_size"),
                 (dict(lid_type="hinged", width=40.0, magnet_count=3), "magnet_room"),
                 (dict(dividers_x=1, magnet_count=1), "magnet_dividers"),
                 (dict(handle=True, handle_radius=12.0, magnet_count=1), "magnet_handle"))
        for kw, code in cases:
            with self.assertRaises(bg.BoxError, msg=str(kw)) as ctx:
                bg.build_box(self.box(magnets=True, **kw))
            self.assertEqual(ctx.exception.code, code, msg=str(kw))
        bg.build_box(self.box(lid_type="finger", magnets=True, lid=False))          # boîte ouverte : sans effet


if __name__ == "__main__":
    unittest.main()



class MotifShapeTests(unittest.TestCase):
    def test_every_shape_is_centred_inside_its_width(self):
        for shape in bg.MOTIF_SHAPES:
            loops = bg.motif_loops(shape, 50.0, 40.0, 30.0)
            self.assertTrue(loops, shape)
            xs = [q[0] for loop in loops for q in loop]
            ys = [q[1] for loop in loops for q in loop]
            self.assertLessEqual(max(xs) - min(xs), 30.0 + 1e-6, shape)
            if shape != "mandala":
                self.assertAlmostEqual(max(xs) - min(xs), 30.0, places=6, msg=shape)
            self.assertAlmostEqual((max(xs) + min(xs)) / 2.0, 50.0, places=6, msg=shape)
            if shape != "butterfly":                         # les ailes hautes du papillon sont plus grandes
                self.assertAlmostEqual((max(ys) + min(ys)) / 2.0, 40.0, delta=0.6, msg=shape)

    def test_build_box_uses_the_chosen_shape_and_rejects_unknown(self):
        p = make(lid_type="lip", engrave_motif=True, motif_size=30.0, motif_shape="star")
        self.assertEqual(len(bg.build_box(p).motif), 1)
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(make(lid_type="lip", engrave_motif=True, motif_shape="dragon"))
        self.assertEqual(ctx.exception.code, "motif_shape")


class VariableDividersAndFeetTests(unittest.TestCase):
    def test_ratios_split_the_room_proportionally(self):
        t = 3.0
        widths = bg.compartment_widths(100.0, 2, t, (1, 2, 1))
        self.assertAlmostEqual(sum(widths), 100.0 - 2 * t - 2 * t)
        self.assertAlmostEqual(widths[1], 2 * widths[0])
        pos = bg.divider_positions(100.0, 2, t, (1, 2, 1))
        self.assertAlmostEqual(pos[0], t + widths[0])
        self.assertAlmostEqual(pos[1] - pos[0], t + widths[1])
        self.assertEqual(bg.divider_positions(100.0, 3, t), bg.divider_positions(100.0, 3, t, ()))

    def test_box_with_ratios_builds_and_bad_ratios_are_rejected(self):
        p = make(dividers_x=2, dividers_y=1, ratios_x=(1, 2, 1), ratios_y=(3, 1))
        self.assertEqual(len(bg.build_box(p).panels), len(bg.build_box(make(dividers_x=2, dividers_y=1)).panels))
        for bad in ((1, 2), (1, 0, 1), (1, -2, 1)):
            with self.assertRaises(bg.BoxError) as ctx:
                bg.build_box(make(dividers_x=2, ratios_x=bad))
            self.assertEqual(ctx.exception.code, "divider_ratios")

    def test_too_narrow_compartment_is_rejected(self):
        with self.assertRaises(bg.BoxError) as ctx:
            bg.build_box(make(dividers_x=1, ratios_x=(1, 60)))
        self.assertEqual(ctx.exception.code, "compartment_too_small")

    def test_feet_panels_and_limits(self):
        r = bg.build_box(make(feet=True, foot_size=15.0, foot_layers=2))
        feet = [pn for pn in r.panels if pn.name.startswith("foot")]
        self.assertEqual(len(feet), 8)
        self.assertEqual(len([pn for pn in bg.build_box(make()).panels if pn.name.startswith("foot")]), 0)
        for kw, code in (({"foot_size": 4.0}, "foot_size"), ({"foot_size": 80.0}, "foot_size"),
                         ({"foot_layers": 0}, "foot_layers"), ({"foot_layers": 5}, "foot_layers")):
            with self.assertRaises(bg.BoxError) as ctx:
                bg.build_box(make(feet=True, **kw))
            self.assertEqual(ctx.exception.code, code)
