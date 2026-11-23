"""Exports de Stencil Studio dans LSP : routage des objets dans les calques
(controllers/stencil_import.py) et import par l'éditeur vectoriel
(VectorEditorController.import_stencil_export)."""
import ast
import os
import sys
import tempfile
import types
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers import stencil_import as si
    from laser_studio.controllers.vector_editor import VectorEditorController
    from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL, MODE_MARK
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.vector_document import VectorDocument
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.i18n import tr
    from stencil_studio import core
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6, OpenCV manquants
    si = None


def square(x, y, side=10.0):
    return [(x, y), (x + side, y), (x + side, y + side), (x, y + side)]


@unittest.skipIf(si is None, "PyQt6 / OpenCV non importables ici")
class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_layer_names_of_the_studio(self):
        self.assertEqual(si.kind_for_layer_name("CUT"), ("cut", None))
        self.assertEqual(si.kind_for_layer_name("Cadrage"), ("mark", None))
        self.assertEqual(si.kind_for_layer_name("ENGRAVE"), ("engrave", None))
        self.assertEqual(si.kind_for_layer_name("LAYER_3"), ("multi", 3))
        self.assertEqual(si.kind_for_layer_name(""), ("cut", None))
        self.assertEqual(si.layer_key_from_source_tag("dxf:FRAME"), "FRAME")

    def test_objects_go_to_the_layer_of_their_mode(self):
        layers = LayersModel()
        objects = [types.SimpleNamespace(source_tag=tag, layer_id=None)
                   for tag in ("dxf:CUT", "dxf:FRAME", "dxf:ENGRAVE")]
        stats = si.route_objects(objects, layers, "defaut")
        modes = [layers.get(obj.layer_id).mode for obj in objects]
        self.assertEqual(modes, [MODE_CUT, MODE_MARK, MODE_FILL])
        self.assertEqual(stats["counts"], {"cut": 1, "mark": 1, "engrave": 1, "multi": 0})
        self.assertEqual(stats["missing_modes"], [])

    def test_a_plate_gets_its_own_layer_once(self):
        layers = LayersModel()
        added = []
        layers.layer_added.connect(added.append)
        objects = [types.SimpleNamespace(source_tag="dxf:LAYER_2", layer_id=None) for _ in range(3)]
        stats = si.route_objects(objects, layers, "defaut", focal=0.12)
        plate = layers.get(objects[0].layer_id)
        self.assertEqual((plate.name, plate.mode, plate.line_interval, plate.line_interval_linked),
                         ("LAYER_2", MODE_CUT, 0.12, True))
        self.assertEqual({obj.layer_id for obj in objects}, {plate.id})
        self.assertEqual(added, [plate.id])                     # annoncé au modèle : tableau et profil suivent
        self.assertEqual(stats["multi_created"], ["LAYER_2"])
        self.assertEqual(si.route_objects(objects, layers, "defaut")["multi_created"], [])   # déjà là

    def test_summary(self):
        text = si.import_summary("/tmp/motif.dxf", {"counts": {"cut": 2, "mark": 1}, "missing_modes": ["engrave"],
                                                    "multi_created": ["LAYER_1"]})
        for part in ("motif.dxf", "2", "LAYER_1"):
            self.assertIn(part, text)


@unittest.skipIf(si is None, "PyQt6 / OpenCV non importables ici")
class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.document = VectorDocument()
        self.canvas = VectorCanvasView(self.layers, document=self.document)
        self.dialogs = FakeDialogs()
        self.editor = VectorEditorController(self.document, self.canvas, self.layers, MachineConfig(), self.dialogs)
        self.messages = []
        self.editor.status.connect(self.messages.append)
        self.addCleanup(self.canvas.deleteLater)

    def export(self, text, name):
        folder = tempfile.mkdtemp(prefix="stencil_studio_")
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_dxf_of_the_studio_is_routed_and_the_temporary_file_removed(self):
        dxf = core.dxf_string([square(0, 0)], 50.0, frame=None, layers=[("LAYER_1", [square(20, 20)])])
        path = self.export(dxf, "pochoir.dxf")
        self.editor.import_stencil_export(path)
        self.assertTrue(self.document.objects)
        self.assertIn("LAYER_1", [layer.name for layer in self.layers.layers])
        self.assertIn("pochoir.dxf", self.messages[-1])
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.dialogs.kinds(), [])                # message dans la barre d'état seulement

    def test_unreadable_export_falls_back_to_the_standard_import(self):
        path = self.export("pas un dxf", "casse.dxf")
        self.editor.import_stencil_export(path)
        self.assertEqual(self.messages[0].split(":")[0], tr("stencil.import_fallback").split(":")[0])
        self.assertEqual(self.dialogs.kinds(), ["error"])         # l'import standard explique le problème
        self.assertFalse(os.path.exists(path))


class IndependenceTests(unittest.TestCase):
    def test_stencil_studio_does_not_import_laser_studio(self):
        """Stencil Studio se lance seul : il reçoit thème, langue et messages de LSP, sans l'importer."""
        root = os.path.join(REPO, "src", "stencil_studio")
        for folder, _dirs, files in os.walk(root):
            for name in (n for n in files if n.endswith(".py")):
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        modules = [node.module or ""]
                    else:
                        continue
                    for module in modules:
                        self.assertFalse(module.startswith("laser_studio"), f"{path} : import {module}")


if __name__ == "__main__":
    unittest.main()
