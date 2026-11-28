"""Arbre des objets du dessin (vector/object_tree.py, sans Qt) : groupes qui contiennent un objet, recalcul,
retrait d'un objet d'un groupe imbriqué ; et l'étape d'annulation commune de l'éditeur (changing)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector import object_tree  # noqa: E402


class Obj:
    def __init__(self, name):
        self.name = name


class Group(Obj):
    """Juste ce que lit object_tree : `children` et le recalcul après un changement d'un de ses objets."""

    def __init__(self, name, children):
        super().__init__(name)
        self.children = list(children)
        self.refreshed = 0

    def child_ignored_changed(self):
        self.refreshed += 1


class ObjectTreeTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.c, self.d = Obj("a"), Obj("b"), Obj("c"), Obj("d")
        self.inner = Group("inner", [self.c])
        self.outer = Group("outer", [self.b, self.inner])
        self.top = [self.a, self.outer, self.d]

    def test_ancestors_from_the_top_of_the_stack(self):
        self.assertEqual(object_tree.ancestors(self.top, self.c), [self.outer, self.inner])
        self.assertEqual(object_tree.ancestors(self.top, self.b), [self.outer])
        self.assertEqual(object_tree.ancestors(self.top, self.a), [])               # en haut de la pile
        self.assertEqual(object_tree.ancestors(self.top, Obj("absent")), [])

    def test_refresh_ancestors_returns_the_top_object(self):
        self.assertIs(object_tree.refresh_ancestors(self.top, self.c), self.outer)
        self.assertEqual((self.inner.refreshed, self.outer.refreshed), (1, 1))
        self.assertIs(object_tree.refresh_ancestors(self.top, self.a), self.a)

    def test_remove_from_a_group_that_keeps_objects(self):
        changed, removed = object_tree.remove_from_group(self.top, self.b)
        self.assertEqual((changed, removed), (self.outer, None))
        self.assertEqual(self.outer.children, [self.inner])

    def test_an_emptied_group_is_removed_from_its_parent(self):
        changed, removed = object_tree.remove_from_group(self.top, self.c)     # inner se vide
        self.assertEqual((changed, removed), (self.outer, None))
        self.assertEqual(self.outer.children, [self.b])

    def test_when_the_top_group_empties_it_is_removed_from_the_document(self):
        object_tree.remove_from_group(self.top, self.c)
        changed, removed = object_tree.remove_from_group(self.top, self.b)
        self.assertEqual((changed, removed), (None, self.outer))


try:
    from PyQt6.QtWidgets import QApplication
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from laser_studio.controllers.vector_editor import VectorEditorController
except ImportError:  # PyQt6 manquant
    VectorEditorController = None


@unittest.skipIf(VectorEditorController is None, "PyQt6 non importable ici")
class ChangingTests(unittest.TestCase):
    """Une modification de l'éditeur : étape d'annulation avant, vues et panneau prévenus après."""

    def test_changing_wraps_one_undo_step(self):
        from types import SimpleNamespace
        app = QApplication.instance() or QApplication([])  # noqa: F841
        calls = []
        canvas = SimpleNamespace(push_undo_snapshot=lambda: calls.append("snapshot"))
        document = SimpleNamespace(notify_changed=lambda objects: calls.append(("changed", list(objects))))
        editor = VectorEditorController(document, canvas, None, None, None)
        editor.properties_changed.connect(lambda obj: calls.append(("panel", obj)))
        obj = Obj("x")
        with editor.changing([obj]):
            calls.append("edit")
        self.assertEqual(calls, ["snapshot", "edit", ("changed", [obj]), ("panel", obj)])
        calls.clear()
        with editor.changing([obj], show=False):
            pass
        self.assertEqual(calls, ["snapshot", ("changed", [obj])])


if __name__ == "__main__":
    unittest.main()
