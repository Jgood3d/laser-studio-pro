"""Sélection traitée comme un groupe (vector/group_transform.py), texte sur contour (vector/text_follow.py)
et menu du clic droit du canevas (ui/vector_editor/context_menu.py)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.i18n import tr
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.vector_objects import ShapeObject, TextObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.ui.vector_editor.context_menu import build_context_menu
    from laser_studio.vector import group_transform, text_follow
except ImportError:  # PyQt6 manquant
    VectorCanvasView = None


def labels(menu):
    out = []
    for action in menu.actions():
        if action.menu() is not None:
            out.append(action.text())
            out.extend(labels(action.menu()))
        elif not action.isSeparator():
            out.append(action.text())
    return out


@unittest.skipIf(VectorCanvasView is None, "PyQt6 non importable ici")
class GroupTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_resize_keeps_relative_positions(self):
        a = ShapeObject("Rectangle", 10, 10, layer_id="L", x_mm=0, y_mm=0)
        b = ShapeObject("Rectangle", 10, 10, layer_id="L", x_mm=30, y_mm=0)
        self.assertEqual(tuple(round(v, 6) for v in group_transform.group_bounds([a, b])), (0, 0, 40, 10))
        group_transform.resize_group([a, b], 80, 20)
        self.assertEqual((b.x_mm, b.width_mm, b.height_mm), (60, 20, 20))
        self.assertEqual(tuple(round(v, 6) for v in group_transform.group_bounds([a, b])), (0, 0, 80, 20))

    def test_rotate_and_layer(self):
        a = ShapeObject("Rectangle", 10, 10, layer_id="L", rotation_deg=300)
        group_transform.rotate_quarter([a])
        group_transform.assign_layer([a], "M")
        self.assertEqual((a.rotation_deg, a.layer_id), (30.0, "M"))

    def test_medal_texts_on_a_closed_contour(self):
        circle = ShapeObject("Ellipse", 40, 40, layer_id="L")
        pts = text_follow.closed_follow_path(circle)
        self.assertIsNotNone(pts)
        created = text_follow.medal_texts(circle, pts, "HAUT", "  ", "DejaVu Sans", 4, 1, "L")
        self.assertEqual([o.text for o in created], ["HAUT"])
        self.assertEqual(created[0].follow_guide_id, circle.id)
        self.assertIsNone(text_follow.closed_follow_path(ShapeObject("Ligne", 40, 0.1, layer_id="L")))


@unittest.skipIf(VectorCanvasView is None, "PyQt6 non importable ici")
class ContextMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.canvas = VectorCanvasView(LayersModel())
        self.addCleanup(self.canvas.deleteLater)
        self.layer = self.canvas.layer_manager.layers[0].id

    def test_empty_canvas_offers_only_shapes(self):
        menu = build_context_menu(self.canvas, [], (10.0, 10.0))
        self.assertEqual(labels(menu)[0], tr("vector.ctx_add_shape"))
        self.assertNotIn(tr("ui.vector_delete"), labels(menu))

    def test_text_and_shape_offer_text_follow(self):
        text = self.canvas.add_object(TextObject(text="ABC", size_mm=5, layer_id=self.layer))
        ring = self.canvas.add_object(ShapeObject("Ellipse", 40, 40, layer_id=self.layer))
        text.setSelected(True)
        ring.setSelected(True)
        found = labels(build_context_menu(self.canvas, [text, ring], (0.0, 0.0)))
        self.assertIn(tr("vector.text_follow"), found)
        self.assertIn(tr("vector.group_objects").format(n=2), found)

    def test_menu_entries_act_on_the_selection(self):
        item = self.canvas.add_object(ShapeObject("Rectangle", 10, 10, layer_id=self.layer))
        item.setSelected(True)
        menu = build_context_menu(self.canvas, [item], (0.0, 0.0))
        rotate = next(a for a in menu.actions() if a.text() == tr("ui.vector_rotate_90"))
        rotate.trigger()
        self.assertEqual(item.obj.rotation_deg, 90.0)
        self.canvas.undo()
        self.assertEqual(self.canvas.objects[0].rotation_deg, 0.0)


if __name__ == "__main__":
    unittest.main()
