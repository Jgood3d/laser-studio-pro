"""Groupes de l'éditeur vectoriel : opérations booléennes (vector/boolean_ops.py), GroupObject
(models/vector_objects.py), ordre du document, gravure (vector/layer_data.py), canevas, contrôleur et liste
des objets (ui/vector_editor/objects_panel.py)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtCore import QPointF
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.vector_editor import VectorEditorController
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.vector_document import VectorDocument, clone_object
    from laser_studio.models.vector_objects import GroupObject, ShapeObject, TextObject, VectorObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.ui.vector_editor.objects_panel import ObjectsPanel, object_label
    from laser_studio.vector import boolean_ops
    from laser_studio.vector.layer_data import extract_vector_layer_data
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 manquant
    GroupObject = None


def square(x, y, size, layer="L1"):
    return ShapeObject("Rectangle", size, size, layer_id=layer, x_mm=x, y_mm=y)


def inside(path, x, y):
    return path.contains(QPointF(x, y))


@unittest.skipIf(GroupObject is None, "PyQt6 non importable ici")
class GroupModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.big = square(10, 10, 40, layer="A")       # dessous : 10..50
        self.small = square(25, 25, 10, layer="B")     # dessus : 25..35

    def test_operations(self):
        paths = [self.big.world_path(), self.small.world_path()]
        union = boolean_ops.combine(paths, boolean_ops.UNION)
        self.assertTrue(inside(union, 30, 30) and inside(union, 15, 15))
        difference = boolean_ops.combine(paths, boolean_ops.DIFFERENCE)
        self.assertTrue(inside(difference, 15, 15))
        self.assertFalse(inside(difference, 30, 30))     # l'intérieur du dessus n'est pas gravé
        intersection = boolean_ops.combine(paths, boolean_ops.INTERSECTION)
        self.assertTrue(inside(intersection, 30, 30))
        self.assertFalse(inside(intersection, 15, 15))
        exclusion = boolean_ops.combine(paths, boolean_ops.EXCLUSION)
        self.assertTrue(inside(exclusion, 15, 15))
        self.assertFalse(inside(exclusion, 30, 30))
        with self.assertRaises(ValueError):
            boolean_ops.combine(paths, "fusion")

    def test_plain_group_keeps_each_object(self):
        group = GroupObject([self.big, self.small])
        self.assertEqual((group.x_mm, group.y_mm, group.layer_id), (10.0, 10.0, "A"))
        self.assertEqual([layer for layer, _path in group.engraving_parts()], ["A", "B"])
        self.assertEqual(group.world_path().boundingRect(), self.big.world_path().boundingRect())

    def test_boolean_group_engraves_one_path_on_the_bottom_layer(self):
        group = GroupObject([self.big, self.small], operation=boolean_ops.DIFFERENCE)
        parts = group.engraving_parts()
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0][0], "A")
        self.assertFalse(inside(parts[0][1], 30, 30))
        group.move_child(self.small, -1)                 # le petit carré passe dessous
        self.assertEqual(group.layer_id, "B")
        self.assertTrue(group.world_path().isEmpty())    # petit moins grand : rien

    def test_moved_rotated_group_roundtrips_and_releases_its_objects(self):
        text = TextObject("AB", "DejaVu Sans", 8.0, layer_id="A", x_mm=60, y_mm=10)
        group = GroupObject([self.big, text], operation=boolean_ops.UNION)
        group.x_mm += 100
        group.rotation_deg = 90
        copy = VectorObject.from_dict(group.to_dict())
        self.assertIsInstance(copy, GroupObject)
        self.assertEqual(copy.world_path().boundingRect(), group.world_path().boundingRect())
        released = copy.released_children()
        self.assertIsInstance(released[1], TextObject)            # un texte reste un texte
        self.assertEqual(released[0].rotation_deg, 90.0)
        box = released[0].world_path().boundingRect().united(released[1].world_path().boundingRect())
        target = group.world_path().boundingRect()
        for a, b in ((box.left(), target.left()), (box.top(), target.top()),
                     (box.width(), target.width()), (box.height(), target.height())):
            self.assertAlmostEqual(a, b, delta=0.6)

    def test_mirrored_group_releases_fixed_paths(self):
        group = GroupObject([self.big, self.small])
        group.mirror_h = True
        released = group.released_children()
        self.assertEqual([o.kind for o in released], ["svg_path", "svg_path"])
        self.assertEqual(released[1].layer_id, "B")

    def test_layer_and_clone(self):
        group = GroupObject([self.big, self.small])
        group.set_layer("C")
        self.assertEqual({layer for layer, _p in group.engraving_parts()}, {"C"})
        clone = clone_object(group)
        self.assertEqual(clone.x_mm, group.x_mm + 5)
        self.assertIsNot(clone.children[0], group.children[0])

    def test_engraving_data_by_layer(self):
        layers = LayersModel()
        first, second = layers.layers[0].id, layers.layers[1].id
        big, small = square(10, 10, 40, first), square(25, 25, 10, second)
        data = extract_vector_layer_data([GroupObject([big, small])], layers, optimize_path=False)
        self.assertEqual((len(data[first]["polygon_groups"]), len(data[second]["polygon_groups"])), (1, 1))
        data = extract_vector_layer_data([GroupObject([big, small], operation=boolean_ops.DIFFERENCE)], layers,
                                         optimize_path=False)
        self.assertEqual(len(data[first]["polygon_groups"]), 1)
        self.assertEqual(len(data[first]["polygon_groups"][0]), 2)      # contour et trou, règle pair-impair
        self.assertEqual(data[second]["polygon_groups"], [])


@unittest.skipIf(GroupObject is None, "PyQt6 non importable ici")
class DocumentOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_move_up_and_down(self):
        doc = VectorDocument()
        a, b, c, d = (doc.add(square(i * 10, 0, 5)) for i in range(4))
        events = []
        doc.order_changed.connect(lambda: events.append("order"))
        self.assertTrue(doc.move([a, b], 1))
        self.assertEqual(doc.objects, [c, a, b, d])
        self.assertFalse(doc.move([b, d], 1))              # d déjà en haut, b juste dessous : rien ne bouge
        self.assertEqual(doc.objects, [c, a, b, d])
        self.assertTrue(doc.move([d], -1))
        self.assertEqual(doc.objects, [c, a, d, b])
        self.assertFalse(doc.move([c], -1))                # déjà tout en bas
        self.assertEqual(events, ["order", "order"])


@unittest.skipIf(GroupObject is None, "PyQt6 non importable ici")
class EditorGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.document = VectorDocument()
        self.canvas = VectorCanvasView(self.layers, document=self.document)
        self.canvas.set_work_area(300.0, 200.0)
        self.editor = VectorEditorController(self.document, self.canvas, self.layers, MachineConfig(),
                                             FakeDialogs())
        self.addCleanup(self.canvas.deleteLater)
        self.a, self.b, self.c = (self.canvas.add_object(square(i * 30, 0, 20)).obj for i in range(3))

    def z(self, obj):
        return self.canvas.item_for(obj).zValue()

    def test_group_takes_the_place_of_its_highest_object_and_ungroups_in_place(self):
        self.canvas.select_objects([self.a, self.b])
        group = self.editor.group_selection(boolean_ops.GROUP)
        self.assertEqual(self.document.objects, [group, self.c])
        self.assertLess(self.z(group), self.z(self.c))
        self.assertEqual([i.obj for i in self.canvas.selected_items_vector()], [group])
        released = self.editor.ungroup_selection()
        self.assertEqual(self.document.objects, [self.a, self.b, self.c])
        self.assertEqual(len(released), 2)
        self.document.undo()
        self.assertEqual(len(self.document.objects), 2)

    def test_combine_then_change_the_operation(self):
        self.canvas.select_objects([self.a, self.b])
        group = self.editor.group_selection(boolean_ops.UNION)
        self.assertEqual(group.operation, boolean_ops.UNION)
        self.assertIs(self.editor.group_selection(boolean_ops.DIFFERENCE), group)
        self.assertEqual(group.operation, boolean_ops.DIFFERENCE)

    def test_move_objects_and_children(self):
        self.editor.move_objects([(None, self.a)], 1)
        self.assertEqual(self.document.objects, [self.b, self.a, self.c])
        self.assertGreater(self.z(self.a), self.z(self.b))
        self.assertFalse(self.editor.move_objects([(None, self.c)], 1))    # déjà tout en haut
        self.canvas.select_objects([self.b, self.a])
        group = self.editor.group_selection(boolean_ops.DIFFERENCE)
        bottom = group.children[0]
        self.editor.move_objects([(group, bottom)], 1)
        self.assertIs(group.children[1], bottom)

    def test_rename(self):
        self.editor.rename_object(self.a, " Plaque ")
        self.assertEqual(object_label(self.a), "Plaque")
        self.document.undo()
        self.assertNotEqual(object_label(self.document.objects[0]), "Plaque")


@unittest.skipIf(GroupObject is None, "PyQt6 non importable ici")
class ObjectsPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = ObjectsPanel()
        self.addCleanup(self.panel.deleteLater)
        self.a, self.b = square(0, 0, 10, "L1"), square(20, 0, 10, "L1")
        self.text = TextObject("Bonjour", "DejaVu Sans", 8.0, layer_id="L1")
        self.group = GroupObject([self.a, self.b], operation=boolean_ops.DIFFERENCE)
        self.panel.show_objects([self.text, self.group], lambda _id: None)

    def test_top_of_the_pile_first_and_group_children(self):
        tree = self.panel.tree
        self.assertEqual(tree.topLevelItemCount(), 2)
        self.assertEqual(tree.topLevelItem(0).text(0), "Différence")
        self.assertEqual(tree.topLevelItem(1).text(0), "« Bonjour »")
        self.assertEqual(tree.topLevelItem(0).childCount(), 2)

    def test_selecting_a_child_selects_its_group_and_signals(self):
        chosen, moves, groups = [], [], []
        self.panel.selection_requested.connect(chosen.append)
        self.panel.move_requested.connect(lambda entries, step: moves.append((entries, step)))
        self.panel.group_requested.connect(groups.append)
        child = self.panel.tree.topLevelItem(0).child(0)
        child.setSelected(True)
        self.assertEqual(chosen[-1], [self.group])
        self.panel.up_button.click()
        self.assertEqual(moves, [([(self.group, self.b)], 1)])
        self.assertTrue(self.panel.boolean_button.isEnabled())
        self.panel.boolean_actions[boolean_ops.UNION].trigger()
        self.assertEqual(groups, [boolean_ops.UNION])

    def test_canvas_selection_is_shown(self):
        self.panel.show_selection([self.text])
        self.assertEqual(self.panel.selected_objects(), [self.text])
        self.assertFalse(self.panel.group_button.isEnabled())
        self.assertFalse(self.panel.ungroup_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
