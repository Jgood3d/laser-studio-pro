"""Placement d'un dessin importé dans l'éditeur vectoriel : marge de surbalayage à gauche
(vector/placement.py) et choix de l'utilisateur quand l'éditeur n'est pas vide
(VectorEditorController.import_objects)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from laser_studio.vector import placement  # noqa: E402  (sans Qt)

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.vector_editor import VectorEditorController
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.vector_document import VectorDocument
    from laser_studio.models.vector_objects import ShapeObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.vector.serial_apply import object_bounds
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 manquant
    VectorEditorController = None


class PlacementTests(unittest.TestCase):
    NEW = (10.0, 10.0, 40.0, 30.0)          # dessin de 30 x 20 mm dont le coin est en (10, 10)
    EXISTING = (0.0, 5.0, 100.0, 50.0)

    def test_add_and_replace_go_to_the_margin(self):
        for mode in (placement.ADD, placement.REPLACE):
            self.assertEqual(placement.placement_offset(self.NEW, self.EXISTING, mode, margin_x=2.5), (-7.5, -10.0))

    def test_right_and_above(self):
        self.assertEqual(placement.placement_offset(self.NEW, self.EXISTING, placement.RIGHT),
                         (100.0 + placement.GAP_MM - 10.0, 5.0 - 10.0))
        self.assertEqual(placement.placement_offset(self.NEW, self.EXISTING, placement.ABOVE),
                         (0.0 - 10.0, 50.0 + placement.GAP_MM - 10.0))
        # Rien de présent : comme « ajouter ».
        self.assertEqual(placement.placement_offset(self.NEW, None, placement.RIGHT, margin_x=1.0), (-9.0, -10.0))

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            placement.placement_offset(self.NEW, None, "diagonal")

    def test_overscan_margin(self):
        self.assertEqual(placement.overscan_margin(False, False, 2.5, 5.0, 100.0), 0.0)
        self.assertEqual(placement.overscan_margin(True, False, 2.5, 5.0, 100.0), 2.5)
        self.assertEqual(placement.overscan_margin(True, True, 2.5, 5.0, 100.0), 5.0)


@unittest.skipIf(VectorEditorController is None, "PyQt6 non importable ici")
class ImportObjectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.layer = self.layers.layers[0].id
        self.document = VectorDocument()
        self.canvas = VectorCanvasView(self.layers, document=self.document)
        self.addCleanup(self.canvas.deleteLater)
        self.dialogs = FakeDialogs()
        self.editor = VectorEditorController(self.document, self.canvas, self.layers, MachineConfig(),
                                             self.dialogs, overscan_margin=lambda width_mm: 3.0)

    def rect(self, x=10.0, y=10.0):
        return ShapeObject("Rectangle", 20.0, 10.0, layer_id=self.layer, x_mm=x, y_mm=y)

    def corner(self, obj):
        b = object_bounds(obj)
        return round(b[0], 6), round(b[1], 6)

    def test_first_import_goes_to_the_overscan_margin_without_question(self):
        obj = self.rect()
        self.editor.import_objects([obj])
        self.assertEqual(self.corner(obj), (3.0, 0.0))
        self.assertEqual(self.dialogs.kinds(), [])

    def test_each_choice(self):
        first = self.rect()
        self.editor.import_objects([first])                     # (3, 0) à (23, 10)
        expected = {placement.ADD: (3.0, 0.0), placement.RIGHT: (23.0 + placement.GAP_MM, 0.0),
                    placement.ABOVE: (3.0, 10.0 + placement.GAP_MM)}
        for mode, corner in expected.items():
            self.dialogs.choice = mode
            obj = self.rect(50.0, 50.0)
            self.editor.import_objects([obj])
            self.assertEqual(self.corner(obj), corner, mode)
            self.assertEqual(len(self.document.objects), 2)
            self.canvas.undo()                                  # une seule étape d'annulation
            self.assertEqual([o.id for o in self.document.objects], [first.id])
        self.assertEqual(self.dialogs.kinds(), ["choose"] * 3)

    def test_replace_removes_the_existing_objects_in_one_undo_step(self):
        self.editor.import_objects([self.rect()])
        self.dialogs.choice = placement.REPLACE
        obj = self.rect(50.0, 50.0)
        self.editor.import_objects([obj])
        self.assertEqual(self.document.objects, [obj])
        self.assertEqual(self.corner(obj), (3.0, 0.0))
        self.canvas.undo()
        self.assertEqual(len(self.document.objects), 1)
        self.assertIsNot(self.document.objects[0], obj)

    def test_cancel_adds_nothing(self):
        self.editor.import_objects([self.rect()])
        self.dialogs.choice = None
        self.assertEqual(self.editor.import_objects([self.rect()]), [])
        self.assertEqual(len(self.document.objects), 1)


if __name__ == "__main__":
    unittest.main()
