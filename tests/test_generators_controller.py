"""Générateurs et mise en page de l'éditeur vectoriel (controllers/generators.py, controllers/layout.py),
pilotés sans aucune fenêtre : un faux EditorForms répond à la place de l'utilisateur."""
import os
import re
import sys
import unittest
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.generators import GeneratorsController
    from laser_studio.controllers.layout import LayoutController
    from laser_studio.controllers.vector_editor import VectorEditorController
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.vector_document import VectorDocument
    from laser_studio.models.vector_objects import ShapeObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.vector import box_generator, jig
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 manquant
    GeneratorsController = None

ROOT = os.path.join(REPO, "src", "laser_studio")


class FakeForms:
    """Même interface qu'EditorForms : renvoie la réponse préparée pour chaque fenêtre (None = annulé) et
    note les fenêtres ouvertes."""

    def __init__(self, **answers):
        self.answers = answers
        self.opened = []

    def __getattr__(self, name):
        def form(*args, **kwargs):
            self.opened.append(name)
            return self.answers.get(name)
        return form


@unittest.skipIf(GeneratorsController is None, "PyQt6 non importable ici")
class GeneratorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, **answers):
        self.layers = LayersModel()
        self.cut = self.layers.layers[0].id
        self.document = VectorDocument()
        self.canvas = VectorCanvasView(self.layers, document=self.document)
        self.addCleanup(self.canvas.deleteLater)
        self.dialogs = FakeDialogs()
        self.forms = FakeForms(**answers)
        self.editor = VectorEditorController(self.document, self.canvas, self.layers, MachineConfig(), self.dialogs,
                                             forms=self.forms)
        self.layout = LayoutController(self.editor, self.forms)
        self.generators = GeneratorsController(self.editor, self.layout, self.forms)

    def test_cancelled_window_changes_nothing(self):
        self.make()
        for open_window in (self.generators.open_box_generator, self.generators.open_puzzle_generator,
                            self.generators.open_ornament_generator, self.generators.open_keychain_generator,
                            self.generators.open_jig_generator):
            open_window()
        self.assertEqual(self.forms.opened, ["box", "puzzle", "ornament", "keychain", "jig"])
        self.assertEqual(self.document.objects, [])
        self.assertEqual(self.dialogs.calls, [])

    def test_box_is_built_placed_and_settings_remembered(self):
        params = box_generator.BoxParams(width=60, depth=40, height=30, lid=False)
        self.make(box=SimpleNamespace(params=params, cut_layer=None, engrave_layer=None, decors=[],
                                      settings={"w": 60}))
        self.forms.answers["box"].cut_layer = self.cut
        self.generators.open_box_generator()
        self.assertEqual(len(self.document.objects), 5)                 # boîte ouverte : 5 faces
        self.assertEqual(self.generators.box_settings, {"w": 60})
        self.assertEqual(self.dialogs.kinds(), ["info"])

    def test_box_error_is_translated(self):
        params = box_generator.BoxParams(width=60, depth=40, height=30, thickness=-1)
        self.make(box=SimpleNamespace(params=params, cut_layer="x", engrave_layer="x", decors=[], settings={}))
        self.generators.open_box_generator()
        kind, _title, text = self.dialogs.calls[0]
        self.assertEqual(kind, "warning")
        self.assertNotIn("box.err.", text)                               # un vrai message, pas la clé

    def test_jig_beside_the_selection(self):
        self.make()
        part = ShapeObject("Rectangle", 20, 10, layer_id=self.cut, x_mm=30, y_mm=5)
        self.canvas.add_object(part)
        self.canvas.item_for(part).setSelected(True)
        self.forms.answers["jig"] = SimpleNamespace(
            params=jig.JigParams(obj_w=20, obj_h=10), position_mode="beside", position_xy=(0, 0), with_base=False,
            cut_layer=self.cut, settings={})
        self.generators.open_jig_generator()
        self.assertGreater(len(self.document.objects), 1)
        self.assertEqual(self.dialogs.kinds(), ["info"])


@unittest.skipIf(GeneratorsController is None, "PyQt6 non importable ici")
class LayoutTests(GeneratorsTests.__base__):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    make = GeneratorsTests.make

    def test_nesting_without_objects_says_so(self):
        self.make()
        self.layout.open_nesting()
        self.assertEqual(self.dialogs.kinds(), ["info"])
        self.assertEqual(self.forms.opened, [])

    def test_sheet_size_is_shared_with_the_ornaments(self):
        self.make()
        self.assertEqual(self.layout.sheet_default(), (self.editor.machine.bed_w, self.editor.machine.bed_h))
        self.layout.remember_sheet(300.0, 200.0)
        self.assertEqual(self.layout.sheet_default(), (300.0, 200.0))
        self.generators.open_ornament_generator()                       # annulé : la feuille est proposée
        self.assertEqual(self.forms.opened, ["ornament"])


class NoWindowInControllersTests(unittest.TestCase):
    """Les contrôleurs ne construisent pas de fenêtre : ils passent par EditorForms ou UserDialogs."""

    def test_controllers_import_no_dialog_module(self):
        pattern = re.compile(r"from laser_studio\.ui\.(dialogs|vector_editor)\b|QDialog")
        offenders = []
        for name in sorted(os.listdir(os.path.join(ROOT, "controllers"))):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(ROOT, "controllers", name), encoding="utf-8") as f:
                if pattern.search(f.read()):
                    offenders.append(name)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
