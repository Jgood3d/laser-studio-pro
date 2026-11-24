"""Document de l'éditeur vectoriel (models/vector_document.py) et opérations de
géométrie (vector/path_ops.py), sans canevas ; puis le canevas comme vue du
document (éléments graphiques créés et retirés d'après ses signaux)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtGui import QPainterPath
    from PyQt6.QtWidgets import QApplication
    from laser_studio.models.vector_document import MAX_UNDO, VectorDocument, clone_object
    from laser_studio.models.vector_objects import ShapeObject, SvgPathObject, TextObject
    from laser_studio.vector import path_ops
except ImportError:  # PyQt6 manquant
    VectorDocument = None


def rect(x=10.0, y=10.0, layer="L1"):
    return ShapeObject("Rectangle", 30.0, 20.0, layer_id=layer, x_mm=x, y_mm=y)


def two_squares(layer="L2"):
    path = QPainterPath()
    path.addRect(0, 0, 10, 10)
    path.addRect(20, 0, 10, 10)
    return SvgPathObject(local_path_data=path, source_tag="group", layer_id=layer, x_mm=50, y_mm=50)


@unittest.skipIf(VectorDocument is None, "PyQt6 non importable ici")
class DocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        doc = VectorDocument()
        events = []
        doc.object_added.connect(lambda o: events.append(("added", o)))
        doc.object_removed.connect(lambda o: events.append(("removed", o)))
        doc.objects_reset.connect(lambda: events.append(("reset",)))
        return doc, events

    def test_add_remove_replace(self):
        doc, events = self.make()
        a, b, c = rect(), rect(50), rect(90)
        doc.add(a)
        doc.add(b)
        self.assertTrue(doc.remove(a))
        self.assertFalse(doc.remove(a))                    # déjà retiré : pas de signal
        doc.replace([b], [c])
        self.assertEqual(doc.objects, [c])
        self.assertEqual(events, [("added", a), ("added", b), ("removed", a), ("removed", b), ("added", c)])
        self.assertIs(doc.object_by_id(c.id), c)
        self.assertIsNone(doc.object_by_id("inconnu"))

    def test_undo_redo(self):
        doc, events = self.make()
        doc.push_snapshot()
        doc.add(rect())
        doc.push_snapshot()
        doc.add(rect(50))
        self.assertTrue(doc.undo())
        self.assertEqual(len(doc.objects), 1)
        self.assertTrue(doc.redo())
        self.assertEqual(len(doc.objects), 2)
        self.assertEqual(events[-1], ("reset",))
        doc.push_snapshot()                                # une nouvelle action vide Refaire
        self.assertFalse(doc.can_redo())
        while doc.undo():
            pass
        self.assertEqual(doc.objects, [])
        self.assertFalse(doc.undo())

    def test_undo_is_capped(self):
        doc, _ = self.make()
        for _ in range(MAX_UNDO + 10):
            doc.push_snapshot()
        self.assertEqual(len(doc._undo_stack), MAX_UNDO)

    def test_dropped_snapshot(self):
        doc, _ = self.make()
        doc.push_snapshot()
        doc.add(rect())
        doc.drop_last_snapshot()                           # aperçu annulé : plus d'étape
        self.assertFalse(doc.can_undo())
        doc.drop_last_snapshot()                           # sans étape : rien

    def test_copy_paste_duplicate(self):
        doc, _ = self.make()
        a = doc.add(rect(10, 20))
        self.assertFalse(doc.has_clipboard())
        doc.copy([])
        self.assertFalse(doc.has_clipboard())
        doc.copy([a])
        (pasted,) = doc.paste()
        (dup,) = doc.duplicate([a])
        for clone in (pasted, dup):
            self.assertNotEqual(clone.id, a.id)
            self.assertEqual((clone.x_mm, clone.y_mm), (15, 25))
        self.assertEqual(doc.objects, [a, pasted, dup])

    def test_serialize_and_load(self):
        doc, events = self.make()
        doc.add(rect())
        doc.add(two_squares())
        doc.add(TextObject("ABC", "DejaVu Sans", 8.0, layer_id="L1"))
        data = doc.serialize()
        other, other_events = self.make()
        other.load(data)
        self.assertEqual([o.to_dict()["kind"] for o in other.objects], ["shape", "svg_path", "text"])
        self.assertEqual(other_events, [("reset",)])
        self.assertEqual(clone_object(doc.objects[0], 0).x_mm, doc.objects[0].x_mm)

    def test_broken_object(self):
        doc, _ = self.make()
        with self.assertRaises(Exception):
            doc.load([{"kind": "shape"}, {"kind": "inconnu", "x": object()}, None])
        doc._undo_stack.append([{"kind": "shape", "x_mm": 1.0}, None])   # instantané abîmé
        doc.undo()                                          # l'objet illisible est ignoré


@unittest.skipIf(VectorDocument is None, "PyQt6 non importable ici")
class PathOpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_ungroup(self):
        children = path_ops.ungroup_object(two_squares())
        self.assertEqual(len(children), 2)
        self.assertTrue(all(c.layer_id == "L2" for c in children))
        self.assertFalse(path_ops.can_ungroup(rect()))
        self.assertEqual(path_ops.ungroup_object(children[0]), [])   # un seul morceau

    def test_explode_and_bake(self):
        self.assertTrue(path_ops.can_explode(rect()))
        segments = path_ops.explode_object(rect())
        self.assertEqual(len(segments), 4)                 # les 4 côtés du rectangle
        baked = path_ops.bake_object(rect())
        self.assertIsInstance(baked, SvgPathObject)
        self.assertEqual(baked.source_tag, "shape")


try:
    from laser_studio.models.layers import LayersModel
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
except ImportError:
    VectorCanvasView = None


@unittest.skipIf(VectorDocument is None or VectorCanvasView is None, "PyQt6 non importable ici")
class CanvasViewTests(unittest.TestCase):
    """Le canevas suit le document : un élément graphique par objet."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def items(self, canvas):
        from laser_studio.ui.vector_editor.item import VectorGraphicsItem
        return [it for it in canvas.scene_obj.items() if isinstance(it, VectorGraphicsItem)]

    def test_items_follow_the_document(self):
        doc = VectorDocument()
        canvas = VectorCanvasView(LayersModel(), document=doc)
        self.addCleanup(canvas.deleteLater)
        a = doc.add(rect())
        b = canvas.add_object(rect(60)).obj                 # par le canevas : même document
        self.assertIs(canvas.objects, doc.objects)
        self.assertEqual({it.obj.id for it in self.items(canvas)}, {a.id, b.id})
        self.assertIs(canvas.item_for(a).obj, a)
        doc.remove(a)
        self.assertEqual([it.obj for it in self.items(canvas)], [b])
        doc.push_snapshot()
        doc.load([])
        self.assertEqual(self.items(canvas), [])
        canvas.undo()
        self.assertEqual(len(self.items(canvas)), 1)

    def test_selection_operations_go_through_the_document(self):
        doc = VectorDocument()
        canvas = VectorCanvasView(LayersModel(), document=doc)
        self.addCleanup(canvas.deleteLater)
        removed = []
        doc.object_removed.connect(removed.append)
        a, b = doc.add(rect()), doc.add(rect(60))
        from laser_studio.controllers.vector_editor import VectorEditorController
        editor = VectorEditorController(doc, canvas, LayersModel(), machine=None, dialogs=None)
        canvas.select_objects([a, b])
        group = editor.group_selection()
        self.assertEqual(removed, [a, b])
        self.assertEqual(doc.objects, [group])
        editor.delete_selected()
        self.assertEqual(doc.objects, [])
        canvas.undo()
        self.assertEqual(len(doc.objects), 1)


if __name__ == "__main__":
    unittest.main()
