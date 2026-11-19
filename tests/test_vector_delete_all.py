"""Bouton « Tout supprimer » de l'éditeur vectoriel."""
import os
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)

try:
    from laser_studio import vector_editing_mixin as mixin
except ImportError:  # PyQt6 manquant
    mixin = None


class _Canvas:
    def __init__(self, count):
        self.objects = list(range(count))
        self.snapshots = 0

    def exit_node_edit(self):
        pass

    def push_undo_snapshot(self):
        self.snapshots += 1

    def load_objects(self, data):
        self.objects = list(data)


@unittest.skipIf(mixin is None, "vector_editing_mixin non importable ici")
class DeleteAllTests(unittest.TestCase):
    def window(self, count):
        class Fake(mixin.VectorEditingMixin):
            pass
        w = Fake.__new__(Fake)
        w.vector_canvas = _Canvas(count)
        w.on_vector_selection_changed = mock.Mock()
        return w

    def answer(self, button):
        return mock.patch.object(mixin.QMessageBox, "question", return_value=button)

    def test_confirmed_delete_all_is_undoable(self):
        w = self.window(3)
        with self.answer(mixin.QMessageBox.StandardButton.Yes):
            w.delete_all_vector_objects()
        self.assertEqual((w.vector_canvas.objects, w.vector_canvas.snapshots), ([], 1))
        w.on_vector_selection_changed.assert_called_once_with(None)

    def test_no_keeps_everything(self):
        w = self.window(3)
        with self.answer(mixin.QMessageBox.StandardButton.No):
            w.delete_all_vector_objects()
        self.assertEqual((len(w.vector_canvas.objects), w.vector_canvas.snapshots), (3, 0))

    def test_empty_canvas_asks_nothing(self):
        w = self.window(0)
        with self.answer(mixin.QMessageBox.StandardButton.Yes) as question:
            w.delete_all_vector_objects()
        question.assert_not_called()

    def test_button_is_in_the_vector_edit_toolbar(self):
        with open(os.path.join(REPO, "src", "laser_studio", "main_window.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('("ui.vector_delete_all", "edit-clear-all", self.delete_all_vector_objects)', src)
        self.assertTrue(os.path.exists(os.path.join(
            REPO, "src", "laser_studio", "resources", "icons", "breeze", "22x22", "actions", "edit-clear-all.svg")))


if __name__ == "__main__":
    unittest.main()
