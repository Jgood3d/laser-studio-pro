"""Lot A : homing automatique par défaut, taille d'origine des images, flèches du clavier."""
import ast
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_source  # noqa: E402

import image_size as isz
import vector_nudge as vn


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


class HomingTests(unittest.TestCase):
    def test_auto_homing_is_checked_by_default(self):
        self.assertIn("self.chk_homing.setChecked(True)", ui_source())
        self.assertNotIn("self.chk_homing.setChecked(False)", ui_source())

    def test_it_is_not_overridden_by_machine_profiles_or_projects(self):
        for name in ("machine_profiles_mixin.py", "project_io_mixin.py"):
            self.assertNotIn("chk_homing", read(name), name)


class NaturalSizeTests(unittest.TestCase):
    def test_read_dpi(self):
        self.assertEqual(isz.read_dpi({"dpi": (300.0, 300.0)}), 300.0)
        self.assertEqual(isz.read_dpi({"dpi": 150}), 150.0)
        self.assertAlmostEqual(isz.read_dpi({"jfif_unit": 2, "jfif_density": (118, 118)}), 118 * 2.54)
        self.assertEqual(isz.read_dpi({"jfif_unit": 1, "jfif_density": (96, 96)}), 96.0)
        for bad in ({}, {"dpi": (1, 1)}, {"dpi": (0, 0)}, {"dpi": ("x", "y")}, {"dpi": (99999, 99999)}, {"jfif_unit": 0, "jfif_density": (72, 72)}):
            self.assertIsNone(isz.read_dpi(bad), bad)

    def test_size_from_dpi_and_default(self):
        w, h, dpi, shrunk = isz.natural_size_mm(600, 300, 300.0)
        self.assertAlmostEqual((w, h), (50.8, 25.4))
        self.assertEqual((dpi, shrunk), (300.0, False))
        w, h, dpi, shrunk = isz.natural_size_mm(960, 480)
        self.assertAlmostEqual((w, h), (254.0, 127.0))
        self.assertEqual(dpi, 96.0)

    def test_big_image_is_reduced_to_the_bed_keeping_proportions(self):
        w, h, dpi, shrunk = isz.natural_size_mm(4000, 3000, 72.0, 400, 400)
        self.assertTrue(shrunk)
        self.assertAlmostEqual(w, 400.0)
        self.assertAlmostEqual(h, 300.0)
        w, h, _, shrunk = isz.natural_size_mm(3000, 4000, 72.0, 400, 300)
        self.assertAlmostEqual((w, h), (225.0, 300.0))
        self.assertTrue(shrunk)

    def test_small_image_is_not_enlarged_and_minimum_size(self):
        w, h, _, shrunk = isz.natural_size_mm(100, 50, 300.0, 400, 400)
        self.assertFalse(shrunk)
        self.assertAlmostEqual(w, 100 / 300 * 25.4)
        self.assertGreaterEqual(isz.natural_size_mm(1, 1, 5000.0)[0], 0.1)


try:
    import image_processing_mixin as ipm
except ImportError:
    ipm = None


class Spin:
    def __init__(self, value=0.0):
        self._v = value

    def value(self): return self._v
    def setValue(self, v): self._v = float(v)


@unittest.skipIf(ipm is None, "image_processing_mixin non importable ici")
class LoadImageTests(unittest.TestCase):
    def make(self, bed=(400.0, 400.0)):
        class Fake(ipm.ImageProcessingMixin):
            def display_source_image(self): pass
            def update_image_processing(self, *a): pass
        f = Fake.__new__(Fake)
        f.spin_w, f.spin_h = Spin(100.0), Spin(100.0)
        f.spin_machine_w, f.spin_machine_h = Spin(bed[0]), Spin(bed[1])
        f.block_aspect_signal = False
        f.console = []
        f.txt_console = types_ns(append=f.console.append)
        f.show_status_message = lambda text, tooltip=None: f.console.append(text)   # barre d'état
        return f

    def load(self, image, bed=(400.0, 400.0), **save_kw):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x." + save_kw.pop("ext", "png"))
            image.save(path, **save_kw)
            f = self.make(bed)
            f.load_image_from_path(path)
        return f

    def test_png_with_a_resolution_uses_its_real_size(self):
        f = self.load(Image.new("L", (600, 300), 128), dpi=(300, 300))
        self.assertAlmostEqual(f.spin_w.value(), 50.8, delta=0.05)
        self.assertAlmostEqual(f.spin_h.value(), 25.4, delta=0.05)
        self.assertTrue(any("50.8 x 25.4" in line for line in f.console))

    def test_image_without_resolution_is_taken_at_96_dpi(self):
        f = self.load(Image.new("L", (480, 240), 128))
        self.assertAlmostEqual(f.spin_w.value(), 127.0, delta=0.05)
        self.assertAlmostEqual(f.spin_h.value(), 63.5, delta=0.05)

    def test_transparent_png_keeps_its_resolution_after_flattening(self):
        f = self.load(Image.new("RGBA", (300, 150), (0, 0, 0, 0)), dpi=(150, 150))
        self.assertAlmostEqual(f.spin_w.value(), 50.8, delta=0.05)

    def test_jpeg_resolution(self):
        f = self.load(Image.new("RGB", (1500, 750), (10, 20, 30)), ext="jpg", dpi=(150, 150))
        self.assertAlmostEqual(f.spin_w.value(), 254.0, delta=0.1)

    def test_photo_larger_than_the_bed_is_reduced_and_it_is_said(self):
        f = self.load(Image.new("L", (4000, 3000), 128), bed=(400.0, 400.0), dpi=(72, 72))
        self.assertAlmostEqual(f.spin_w.value(), 400.0, delta=0.01)
        self.assertAlmostEqual(f.spin_h.value(), 300.0, delta=0.01)
        self.assertTrue(any("400.0 x 300.0" in line and "1411" in line for line in f.console), f.console)

    def test_aspect_flag_is_released_and_never_100_mm_by_default(self):
        f = self.load(Image.new("L", (200, 100), 128), dpi=(254, 254))
        self.assertFalse(f.block_aspect_signal)
        self.assertAlmostEqual(f.spin_w.value(), 20.0, delta=0.05)
        self.assertAlmostEqual(f.spin_h.value(), 10.0, delta=0.05)


def types_ns(**kw):
    import types
    return types.SimpleNamespace(**kw)


# --- flèches du clavier -----------------------------------------------------------------------
def load_nudge():
    with open(os.path.join(ROOT, "vector_layers.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    func = next(n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "VectorCanvasView"
                for n in c.body if isinstance(n, ast.FunctionDef) and n.name == "nudge_selection")

    class Item:
        def __init__(self, obj):
            self.obj, self.refreshed = obj, 0

        def refresh(self):
            self.refreshed += 1

    class Qt:
        class KeyboardModifier:
            ShiftModifier, AltModifier = 1, 2

    ns = {"time": time, "Qt": Qt, "VectorGraphicsItem": Item, "nudge_step": vn.nudge_step,
          "NUDGE_UNDO_WINDOW_S": vn.NUDGE_UNDO_WINDOW_S}
    exec(compile(ast.Module(body=[func], type_ignores=[]), "nudge", "exec"), ns)
    return ns["nudge_selection"], Item


nudge_selection, FakeItem = load_nudge()


class Obj:
    def __init__(self, x=10.0, y=20.0):
        self.x_mm, self.y_mm = x, y


class FakeCanvas:
    def __init__(self, items):
        self.items, self.snapshots = items, 0
        self.scene_obj = types_ns(selectedItems=lambda: self.items)

    def push_undo_snapshot(self):
        self.snapshots += 1


class NudgeTests(unittest.TestCase):
    def canvas(self, n=1):
        return FakeCanvas([FakeItem(Obj(10.0 + i, 20.0)) for i in range(n)])

    def test_step_sizes(self):
        self.assertEqual((vn.nudge_step(), vn.nudge_step(shift=True), vn.nudge_step(alt=True), vn.nudge_step(shift=True, alt=True)),
                         (1.0, 10.0, 0.1, 0.1))

    def test_nothing_selected_lets_the_view_scroll(self):
        c = self.canvas(0)
        self.assertFalse(nudge_selection(c, 1, 0, 0))
        self.assertEqual(c.snapshots, 0)

    def test_directions_use_a_y_up_world(self):
        c = self.canvas()
        for dx, dy, expected in ((1, 0, (11.0, 20.0)), (-1, 0, (10.0, 20.0)), (0, 1, (10.0, 21.0)), (0, -1, (10.0, 20.0))):
            self.assertTrue(nudge_selection(c, dx, dy, 0))
            o = c.items[0].obj
            self.assertEqual((round(o.x_mm, 6), round(o.y_mm, 6)), expected)

    def test_modifiers_and_refresh(self):
        c = self.canvas()
        nudge_selection(c, 1, 0, 1)                     # Maj
        self.assertAlmostEqual(c.items[0].obj.x_mm, 20.0)
        nudge_selection(c, 0, 1, 2)                     # Alt
        self.assertAlmostEqual(c.items[0].obj.y_mm, 20.1)
        nudge_selection(c, 0, 1, 3)                     # Maj + Alt : pas fin
        self.assertAlmostEqual(c.items[0].obj.y_mm, 20.2)
        self.assertEqual(c.items[0].refreshed, 3)

    def test_every_selected_object_moves_together(self):
        c = self.canvas(3)
        nudge_selection(c, 1, 1, 0)
        self.assertEqual([(o.obj.x_mm, o.obj.y_mm) for o in c.items], [(11.0, 21.0), (12.0, 21.0), (13.0, 21.0)])

    def test_a_held_key_makes_a_single_undo_step_and_a_later_press_a_new_one(self):
        c = self.canvas()
        clock = [100.0]
        with mock.patch.object(time, "monotonic", lambda: clock[0]):
            for _ in range(10):
                nudge_selection(c, 1, 0, 0)
                clock[0] += 0.05
            self.assertEqual(c.snapshots, 1)
            clock[0] += 2.0
            nudge_selection(c, 1, 0, 0)
            self.assertEqual(c.snapshots, 2)
        self.assertAlmostEqual(c.items[0].obj.x_mm, 21.0)

    def test_unrelated_selected_items_are_ignored(self):
        c = FakeCanvas([object()])
        self.assertFalse(nudge_selection(c, 1, 0, 0))

    def test_key_handler_is_wired_to_the_four_arrows(self):
        src = read("vector_layers.py")
        body = src[src.index("def keyPressEvent", src.index("class VectorCanvasView")):src.index("def nudge_selection")]
        for key in ("Key_Left", "Key_Right", "Key_Up", "Key_Down"):
            self.assertIn(f"Qt.Key.{key}", body)
        self.assertIn("self.nudge_selection(direction[0], direction[1], event.modifiers())", body)


if __name__ == "__main__":
    unittest.main()
