"""Imbrication dans l'éditeur : groupes rigides (trous qui suivent leur pièce), rotation, fenêtre de réglage.
Les objets et le canevas Qt sont remplacés par de petites classes factices."""
import math
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import nesting as ng
import vector_order as vo

try:
    import nesting_apply as na
except ImportError:
    na = None


class Pt:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self): return self._x
    def y(self): return self._y


class FakePath:
    def __init__(self, polygons):
        self.polygons = polygons

    def toSubpathPolygons(self, transform):
        return [[Pt(x, y) for x, y in poly] for poly in self.polygons]


class FakeObj:
    """Comme VectorObject : monde = translation(x, y) puis rotation appliquées au contour local."""
    def __init__(self, local_polygons, x, y, rotation=0.0, name=""):
        self.local, self.x_mm, self.y_mm, self.rotation_deg, self.name = local_polygons, x, y, rotation, name

    def world_polygons(self):
        a = math.radians(self.rotation_deg)
        c, s = math.cos(a), math.sin(a)
        return [[(self.x_mm + px * c - py * s, self.y_mm + px * s + py * c) for px, py in poly] for poly in self.local]

    def world_path(self):
        return FakePath(self.world_polygons())


class FakeCanvas:
    def __init__(self):
        self.calls = []

    def set_object_position(self, obj, x, y, rotation_deg=None):
        self.calls.append((obj, x, y, rotation_deg))
        obj.x_mm, obj.y_mm = x, y
        if rotation_deg is not None:
            obj.rotation_deg = rotation_deg


def rect(w, h):
    return [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]


def circle(r, cx, cy, n=36):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)] + [(cx + r, cy)]


def distance(poly_a, poly_b):
    def seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
    if any(vo.point_in_polygon(x, y, poly_b) for x, y in poly_a[:3]) or any(vo.point_in_polygon(x, y, poly_a) for x, y in poly_b[:3]):
        return 0.0
    return min([seg(p, poly_b[i], poly_b[i + 1]) for p in poly_a for i in range(len(poly_b) - 1)] +
               [seg(p, poly_a[i], poly_a[i + 1]) for p in poly_b for i in range(len(poly_a) - 1)])


@unittest.skipIf(na is None, "nesting_apply non importable ici")
class RigidGroupTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(na, "QTransform", lambda: object())
        patcher.start()
        self.addCleanup(patcher.stop)

    def plates(self):
        """4 plaques 40 x 25 avec trou rond et trait gravé, empilées hors de la feuille, + 2 pièces simples."""
        objs = []
        for i in range(4):
            x0 = 300 + i * 7.0
            objs.append(FakeObj([rect(40, 25)], x0, 10.0 * i, name=f"plaque{i}"))
            objs.append(FakeObj([circle(5, 12, 12)], x0, 10.0 * i, name=f"trou{i}"))
            objs.append(FakeObj([[(5, 20), (30, 20)]], x0, 10.0 * i, name=f"gravure{i}"))
        objs.append(FakeObj([rect(60, 15)], 500, 0, name="longue"))
        objs.append(FakeObj([circle(9, 9, 9)], 600, 0, name="disque"))
        return objs

    def test_holes_and_engravings_are_grouped_with_their_plate(self):
        pieces, members = na.build_pieces(self.plates())
        self.assertEqual(len(pieces), 6)
        by_root = {m[0].name: sorted(o.name for o in m) for m in members}
        for i in range(4):
            self.assertEqual(by_root[f"plaque{i}"], sorted([f"plaque{i}", f"trou{i}", f"gravure{i}"]))

    def test_every_group_moves_rigidly_to_the_computed_place_without_collision(self):
        objs = self.plates()
        before = {o.name: o.world_polygons() for o in objs}
        pieces, members = na.build_pieces(objs)
        result = ng.nest(pieces, 220, 160, spacing=3, margin=2, angles=ng.ANGLE_SETS["quarters"])
        self.assertEqual(result.unplaced, [])
        self.assertEqual(len(na.apply_result(FakeCanvas(), members, result)), len(objs))
        outlines = {}
        for pl in result.placements:
            for obj in members[pl.index]:
                for exp_poly, got_poly in zip([[pl.apply(p) for p in poly] for poly in before[obj.name]], obj.world_polygons()):
                    for (ex, ey), (gx, gy) in zip(exp_poly, got_poly):
                        self.assertAlmostEqual(gx, ex, places=6, msg=obj.name)
                        self.assertAlmostEqual(gy, ey, places=6, msg=obj.name)
            outer = max((p for o in members[pl.index] for p in o.world_polygons()), key=vo.polygon_area)
            outlines[members[pl.index][0].name] = outer
            for x, y in outer:
                self.assertTrue(2 - 1e-6 <= x <= 218 + 1e-6 and 2 - 1e-6 <= y <= 158 + 1e-6)
        names = sorted(outlines)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertGreaterEqual(distance(outlines[a], outlines[b]), 3 - 1e-6, (a, b))

    def test_rotation_is_added_to_the_objects_own_rotation(self):
        obj = FakeObj([rect(50, 5)], 100, 100, rotation=30.0)
        pieces, members = na.build_pieces([obj])
        result = ng.nest(pieces, 40, 80, spacing=1, angles=ng.ANGLE_SETS["quarters"])    # ne tient qu'à 120° ou 300°
        self.assertEqual(result.unplaced, [])
        canvas = FakeCanvas()
        na.apply_result(canvas, members, result)
        (_, _, _, rot), = canvas.calls
        self.assertIn(result.placements[0].angle, (90.0, 270.0))          # relatif : 30 + 90 = 120
        self.assertIn(rot, (120.0, 300.0))

    def test_unplaced_groups_do_not_move(self):
        big, small = FakeObj([rect(500, 500)], 7, 8), FakeObj([rect(10, 10)], 600, 600)
        pieces, members = na.build_pieces([big, small])
        moved = na.apply_result(FakeCanvas(), members, ng.nest(pieces, 100, 100))
        self.assertEqual(moved, [small])
        self.assertEqual((big.x_mm, big.y_mm), (7, 8))


from test_box_dialog_smoke import fake_widgets_module  # noqa: E402


def load_dialog():
    with mock.patch.dict(sys.modules, {"PyQt6.QtWidgets": fake_widgets_module()}):
        sys.modules.pop("nesting_dialog", None)
        module = __import__("nesting_dialog")
    sys.modules.pop("nesting_dialog", None)
    return module


try:
    nd = load_dialog()
except ImportError:
    nd = None


@unittest.skipIf(nd is None, "nesting_dialog non importable ici")
class DialogTests(unittest.TestCase):
    def test_defaults_scope_and_round_trip(self):
        d = nd.NestingDialog(None, 400.0, 300.0, 3, 10)
        o = d.options()
        self.assertEqual((d.scope(), o["sheet_w"], o["sheet_h"], o["origin"], o["angles"], o["cell"], o["spacing"], o["margin"]),
                         ("selection", 400.0, 300.0, (0.0, 0.0), ng.ANGLE_SETS["quarters"], 1.0, 2.0, 3.0))
        self.assertEqual(nd.NestingDialog(None, 400.0, 300.0, 0, 10).scope(), "all")
        d.spin_sheet_w.setValue(250)
        d.spin_spacing.setValue(4.5)
        d.combo_rotations.setCurrentIndex(d.combo_rotations.findData("none"))
        d.combo_precision.setCurrentIndex(d.combo_precision.findData(0.5))
        o2 = nd.NestingDialog(None, 400.0, 300.0, 0, 5, d.settings()).options()
        self.assertEqual((o2["sheet_w"], o2["spacing"], o2["angles"], o2["cell"]), (250.0, 4.5, ng.ANGLE_SETS["none"], 0.5))

    def test_every_rotation_choice_maps_to_an_angle_set(self):
        d = nd.NestingDialog(None, 400.0, 300.0, 0, 5)
        for key in ng.ANGLE_SETS:
            d.combo_rotations.setCurrentIndex(d.combo_rotations.findData(key))
            self.assertEqual(d.options()["angles"], ng.ANGLE_SETS[key])


class WiringTests(unittest.TestCase):
    def src(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def test_button_method_undo_and_active_layers(self):
        ui = self.src("ui_setup_mixin.py")
        self.assertIn("btn_nesting.clicked.connect(self.open_nesting)", ui)
        self.assertIn("toolbar_vector.addWidget(btn_nesting)", ui)
        src = self.src("vector_editing_mixin.py")
        body = src[src.index("def open_nesting"):src.index("def open_box_generator")]
        self.assertLess(body.index("canvas.push_undo_snapshot()"), body.index("apply_result(canvas, members, result)"))
        self.assertIn("layer.enabled", body)
        self.assertIn("QApplication.restoreOverrideCursor()", body)


if __name__ == "__main__":
    unittest.main()
