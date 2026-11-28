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
        for kind in ("box", "puzzle", "ornament", "keychain"):
            self.generators.open_generators(kind)
        self.generators.open_jig_generator()
        self.assertEqual(self.forms.opened, ["generators"] * 4 + ["jig"])
        self.assertEqual(self.document.objects, [])
        self.assertEqual(self.dialogs.calls, [])

    def test_box_is_built_placed_and_settings_remembered(self):
        params = box_generator.BoxParams(width=60, depth=40, height=30, lid=False)
        box = SimpleNamespace(params=params, cut_layer=None, engrave_layer=None, decors=[], settings={"w": 60})
        self.make(generators=("box", box))
        box.cut_layer = self.cut
        self.generators.open_generators("box")
        self.assertEqual(len(self.document.objects), 5)                 # boîte ouverte : 5 faces
        self.assertEqual(self.generators.box_settings, {"w": 60})
        self.assertEqual(self.dialogs.kinds(), ["info"])

    def test_box_error_is_translated(self):
        params = box_generator.BoxParams(width=60, depth=40, height=30, thickness=-1)
        self.make(generators=("box", SimpleNamespace(params=params, cut_layer="x", engrave_layer="x", decors=[],
                                                     settings={})))
        self.generators.open_generators("box")
        kind, _title, text = self.dialogs.calls[0]
        self.assertEqual(kind, "warning")
        self.assertNotIn("box.err.", text)                               # un vrai message, pas la clé

    def test_one_window_for_the_four_generators_reopens_on_the_last_one(self):
        class Forms(FakeForms):
            def generators(self, start, requests):
                self.opened.append((start, sorted(requests)))
                return self.answers.get("generators")
        params = box_generator.BoxParams(width=60, depth=40, height=30, lid=False)
        self.make()
        self.forms = Forms(generators=None)
        self.generators.forms = self.forms
        self.generators.open_generators("puzzle")                         # menu Outils › Puzzle : sa page
        self.generators.open_generators()                               # barre d'outils : la page par défaut
        self.forms.answers["generators"] = ("box", SimpleNamespace(params=params, cut_layer=self.cut,
                                                                   engrave_layer=None, decors=[], settings={}))
        self.generators.open_generators("puzzle")                       # l'utilisateur valide la boîte
        self.generators.open_generators()                               # rouvre sur la boîte
        kinds = ["box", "keychain", "ornament", "puzzle"]
        self.assertEqual(self.forms.opened, [("puzzle", kinds), ("box", kinds), ("puzzle", kinds), ("box", kinds)])
        self.assertEqual(len(self.document.objects), 10)                # deux boîtes de 5 faces

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

    def test_serial_duplicate_adds_copies_in_one_undoable_step(self):
        self.make()
        part = ShapeObject("Rectangle", 20, 10, layer_id=self.cut, x_mm=5, y_mm=5)
        self.canvas.add_object(part)
        self.canvas.item_for(part).setSelected(True)
        params = {"count": 3, "layout": "grid", "cols": 3, "gap_x": 2.0, "gap_y": 2.0, "names": [],
                  "text_index": None}
        self.forms.answers["serial"] = SimpleNamespace(params=params, settings={})
        self.layout.open_serial_duplicate()
        self.assertEqual(len(self.document.objects), 3)
        self.assertEqual(len({o.x_mm for o in self.document.objects}), 3)        # rangés côte à côte
        self.assertEqual(len(self.canvas.selected_items_vector()), 3)
        self.canvas.document.undo()                                              # l'annulation recrée les objets
        self.assertEqual([o.id for o in self.document.objects], [part.id])

    def test_failed_serial_duplicate_leaves_the_canvas_unchanged(self):
        self.make()
        part = ShapeObject("Rectangle", 20, 10, layer_id=self.cut, x_mm=5, y_mm=5)
        self.canvas.add_object(part)
        self.canvas.item_for(part).setSelected(True)
        self.forms.answers["serial"] = SimpleNamespace(params={"count": 3, "layout": "grid"}, settings={})  # incomplet
        self.layout.open_serial_duplicate()
        self.assertEqual(self.dialogs.kinds(), ["warning"])
        self.assertEqual([o.id for o in self.document.objects], [part.id])

    def test_nesting_moves_the_pieces_onto_the_sheet(self):
        self.make()
        parts = [ShapeObject("Rectangle", 20, 10, layer_id=self.cut, x_mm=500 + 30 * i, y_mm=500) for i in range(3)]
        for part in parts:
            self.canvas.add_object(part)
        options = {"sheet_w": 100.0, "sheet_h": 100.0, "spacing": 2.0, "margin": 2.0, "angles": (0.0,),
                   "cell": 1.0, "origin": (0.0, 0.0)}
        self.forms.answers["nesting"] = SimpleNamespace(scope="all", options=options, settings={})
        self.layout.open_nesting()
        for part in parts:
            self.assertLess(part.x_mm, 100)
            self.assertLess(part.y_mm, 100)
            self.assertEqual(self.canvas.item_for(part).obj, part)
        self.canvas.document.undo()
        self.assertEqual(sorted(o.x_mm for o in self.document.objects), [500, 530, 560])

    def test_sheet_size_is_shared_with_the_ornaments(self):
        self.make()
        self.assertEqual(self.layout.sheet_default(), (self.editor.machine.bed_w, self.editor.machine.bed_h))
        self.layout.remember_sheet(300.0, 200.0)
        self.assertEqual(self.layout.sheet_default(), (300.0, 200.0))
        self.generators.open_generators("ornament")                       # annulé : la feuille est proposée
        self.assertEqual(self.forms.opened, ["generators"])


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
