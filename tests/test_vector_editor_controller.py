"""Contrôleur de l'éditeur vectoriel (controllers/vector_editor.py) avec un vrai
document et un vrai canevas hors écran, et calculs de disposition
(vector/arrange.py). Les boîtes de dialogue sont simulées (FakeDialogs)."""
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.vector_editor import VectorEditorController
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.vector_document import VectorDocument
    from laser_studio.models.vector_objects import ShapeObject, TextObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.vector import arrange
    from laser_studio.i18n import tr
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 manquant
    VectorEditorController = None


def rect(x, y, w=20.0, h=10.0, layer="L1"):
    return ShapeObject("Rectangle", w, h, layer_id=layer, x_mm=x, y_mm=y)


@unittest.skipIf(VectorEditorController is None, "PyQt6 non importable ici")
class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.document = VectorDocument()
        self.canvas = VectorCanvasView(self.layers, document=self.document)
        self.canvas.set_work_area(300.0, 200.0)
        self.dialogs = FakeDialogs()
        self.editor = VectorEditorController(self.document, self.canvas, self.layers, MachineConfig(),
                                             self.dialogs)
        self.refreshed = []
        self.editor.properties_changed.connect(self.refreshed.append)

    def tearDown(self):
        self.canvas.deleteLater()

    def add(self, *objects):
        for obj in objects:
            self.canvas.add_object(obj)
        return objects

    def select(self, *objects):
        self.canvas.scene_obj.clearSelection()
        for obj in objects:
            self.canvas.item_for(obj).setSelected(True)

    def bounds(self, obj):
        return arrange.group_bounds([obj])

    # -- tout supprimer

    def test_delete_all_confirmed_is_one_undo_step(self):
        self.add(rect(0, 0), rect(50, 0), rect(100, 0))
        self.editor.delete_all()
        self.assertEqual(self.document.objects, [])
        self.assertEqual(self.dialogs.kinds(), ["confirm_default_no"])
        self.assertEqual(self.refreshed, [None])
        self.document.undo()
        self.assertEqual(len(self.document.objects), 3)

    def test_delete_all_refused_keeps_everything(self):
        self.dialogs.answer = False
        self.add(rect(0, 0), rect(50, 0))
        self.editor.delete_all()
        self.assertEqual((len(self.document.objects), self.document.can_undo()), (2, False))

    def test_delete_all_on_empty_editor_asks_nothing(self):
        self.editor.delete_all()
        self.assertEqual(self.dialogs.calls, [])

    # -- alignement, répartition

    def test_align_left_and_undo(self):
        a, b = self.add(rect(10, 0), rect(60, 30))
        self.select(a, b)
        self.editor.align("left")
        self.assertAlmostEqual(self.bounds(b)[0], self.bounds(a)[0])
        self.assertTrue(self.refreshed)
        self.document.undo()
        moved = [o for o in self.document.objects if o.y_mm == 30][0]
        self.assertAlmostEqual(moved.x_mm, 60)

    def test_align_needs_two_objects(self):
        (a,) = self.add(rect(10, 0))
        self.select(a)
        self.editor.align("left")
        self.assertFalse(self.document.can_undo())

    def test_distribute_horizontally_keeps_the_ends(self):
        a, b, c = self.add(rect(0, 0), rect(30, 0), rect(100, 0))
        self.select(a, b, c)
        self.editor.distribute("h")
        self.assertEqual((a.x_mm, c.x_mm), (0, 100))
        gap_ab = self.bounds(b)[0] - self.bounds(a)[2]
        gap_bc = self.bounds(c)[0] - self.bounds(b)[2]
        self.assertAlmostEqual(gap_ab, gap_bc)

    # -- panneau des propriétés : position, calque, taille

    def test_move_selection_moves_the_group_corner(self):
        a, b = self.add(rect(10, 10), rect(50, 40))
        self.select(a, b)
        self.editor.move_selection_to(0.0, 0.0, 45.0)
        self.assertEqual(arrange.group_bounds([a, b])[:2], (0.0, 0.0))
        self.assertEqual((a.rotation_deg, b.rotation_deg), (0.0, 0.0))   # pas de rotation de groupe
        self.assertTrue(self.document.can_undo())

    def test_move_single_object_also_rotates(self):
        (a,) = self.add(rect(10, 10))
        self.select(a)
        self.editor.move_selection_to(5.0, 5.0, 30.0)
        self.assertEqual(a.rotation_deg, 30.0)

    def test_set_selected_layer(self):
        L0, L1 = self.layers.layers[0].id, self.layers.layers[1].id
        (a,) = self.add(rect(10, 10, layer=L0))
        self.select(a)
        self.editor.set_selected_layer(L1)
        self.assertEqual(a.layer_id, L1)
        self.editor.set_selected_layer(L1)                       # même calque : pas d'étape en plus
        self.assertEqual(len(self.document._undo_stack), 1)

    def test_resize_with_anchor_keeps_the_corner(self):
        (a,) = self.add(rect(10, 10))
        self.select(a)
        before = arrange.shape_world_anchor(a, "tr")
        self.assertIs(self.editor.resize_selected_shape(40.0, 25.0, "tr"), a)
        after = arrange.shape_world_anchor(a, "tr")
        self.assertEqual((a.width_mm, a.height_mm), (40.0, 25.0))
        self.assertAlmostEqual(before.x(), after.x())
        self.assertAlmostEqual(before.y(), after.y())

    def test_resize_same_size_or_no_shape_does_nothing(self):
        (a,) = self.add(rect(10, 10))
        self.select(a)
        self.assertIsNone(self.editor.resize_selected_shape(20.0, 10.0))
        self.canvas.scene_obj.clearSelection()
        self.assertIsNone(self.editor.resize_selected_shape(30.0, 10.0))
        self.assertFalse(self.document.can_undo())

    # -- rotation, absence de sélection, calques

    def test_rotate_without_selection_says_so(self):
        self.editor.rotate_selected()
        self.assertEqual(self.dialogs.kinds(), ["info"])

    def test_rotate_selected(self):
        (a,) = self.add(rect(10, 10))
        self.select(a)
        self.editor.rotate_selected()
        self.editor.rotate_selected()
        self.assertEqual(a.rotation_deg, 180.0)
        self.assertEqual(self.refreshed, [a, a])

    def test_no_layer_blocks_insertion_and_import(self):
        self.layers.layers.clear()
        self.editor.insert_shape()
        self.editor.importer.import_file("dessin.svg")
        self.assertEqual(self.dialogs.kinds(), ["warning", "warning"])
        self.assertEqual(self.document.objects, [])

    # -- import

    def test_import_svg_adds_objects_and_shows_the_editor(self):
        shown = []
        self.editor.show_editor.connect(lambda: shown.append(True))
        path = os.path.join(tempfile.mkdtemp(), "dessin.svg")
        with open(path, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="60mm" height="40mm" viewBox="0 0 60 40">'
                    '<path d="M 5 5 L 55 5 L 55 35 Z"/></svg>')
        self.editor.importer.import_file(path)
        self.assertEqual(len(self.document.objects), 1)
        self.assertEqual((shown, self.dialogs.kinds()), ([True], ["info"]))
        self.document.undo()
        self.assertEqual(self.document.objects, [])

    def test_unreadable_dxf_is_reported(self):
        path = os.path.join(tempfile.mkdtemp(), "casse.dxf")
        with open(path, "wb") as f:
            f.write(b"\x00\x01binaire")
        self.editor.importer.import_file(path)
        self.assertEqual((self.dialogs.kinds(), self.document.objects), (["error"], []))


class FakeForms:
    """Répond à la place des fenêtres de saisie (EditorForms)."""

    def __init__(self, resize=None, medal=None, text=True):
        self.resize, self.medal_values, self.text_answer = resize, medal, text

    def group_resize(self, width_mm, height_mm):
        return self.resize

    def medal(self, layers):
        return self.medal_values

    def text(self, layers, obj, on_preview, is_new=False, before_apply=lambda: None):
        return self.text_answer


@unittest.skipIf(VectorEditorController is None, "PyQt6 non importable ici")
class SelectionCommandsTests(unittest.TestCase):
    """Opérations sur la sélection reprises du canevas (VectorEditorController) : elles passent par le
    document, une étape d'annulation chacune."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.document = VectorDocument()
        self.canvas = VectorCanvasView(self.layers, document=self.document)
        self.addCleanup(self.canvas.deleteLater)
        self.editor = VectorEditorController(self.document, self.canvas, self.layers, MachineConfig(),
                                             FakeDialogs(), forms=FakeForms())

    def add(self, *objects):
        for obj in objects:
            self.canvas.add_object(obj)
        return objects

    def test_copy_paste_duplicate_delete(self):
        a, = self.add(rect(0, 0))
        self.canvas.select_objects([a])
        self.editor.copy_selected()
        pasted = self.editor.paste_clipboard()
        self.assertEqual(len(self.document.objects), 2)
        self.assertEqual(self.editor.selected_objects(), pasted)              # la copie collée est choisie
        copies = self.editor.duplicate_selected()
        self.assertEqual(len(self.document.objects), 3)
        self.canvas.select_objects(copies)
        self.editor.delete_selected()
        self.assertEqual(len(self.document.objects), 2)
        self.document.undo()
        self.assertEqual(len(self.document.objects), 3)

    def test_explode_and_basic_shape(self):
        a, = self.add(rect(0, 0))
        self.canvas.select_objects([a])
        self.assertEqual(len(self.editor.grouping.explode_selection()), 4)               # un rectangle : 4 segments
        shape = self.editor.add_basic_shape("Cercle", 50.0, 50.0, size_mm=10.0)
        self.assertEqual((shape.shape_type, shape.x_mm, shape.y_mm), ("Ellipse", 45.0, 45.0))
        self.assertEqual(self.editor.selected_objects(), [shape])

    def test_resize_through_the_form(self):
        a, b = self.add(rect(0, 0), rect(30, 0))
        self.canvas.select_objects([a, b])
        self.editor.forms.resize = (100.0, 20.0)
        self.editor.resize_group()
        self.assertEqual((round(b.x_mm, 6), round(b.width_mm, 6)), (60.0, 40.0))
        self.editor.forms.resize = None                                      # annulé : rien ne change
        self.editor.resize_group()
        self.assertEqual(round(b.width_mm, 6), 40.0)

    def test_text_follow_resync_and_medal(self):
        text = TextObject(text="ABC", size_mm=5, layer_id="L1")
        ring = ShapeObject("Ellipse", 40, 40, layer_id="L1", x_mm=0, y_mm=0)
        self.add(text, ring)
        self.canvas.select_objects([text, ring])
        self.assertIs(self.editor.text_follow.follow(), text)
        self.assertEqual(text.follow_guide_id, ring.id)
        ring.x_mm += 10
        self.assertEqual(self.editor.text_follow.resync_linked([ring]), 1)            # le texte suit le contour
        self.canvas.select_objects([ring])
        self.editor.forms.medal_values = dict(top_text="HAUT", bottom_text="BAS", font_family="DejaVu Sans",
                                              size_mm=4, margin_mm=1, layer_id="L1")
        self.editor.text_follow.medal()
        self.assertEqual(sorted(o.text for o in self.editor.selected_objects()), ["BAS", "HAUT"])


@unittest.skipIf(VectorEditorController is None, "PyQt6 non importable ici")
class ArrangeTests(unittest.TestCase):
    def test_align_offsets(self):
        a, b = rect(10, 0), rect(60, 30)
        self.assertEqual(arrange.align_offsets([a, b], "left"), [(0.0, 0.0), (-50.0, 0.0)])
        self.assertEqual(arrange.align_offsets([a, b], "bottom"), [(0.0, 0.0), (0.0, -30.0)])

    def test_distribute_offsets_vertical(self):
        a, b, c = rect(0, 0), rect(0, 50), rect(0, 60)
        moves = dict((id(o), d) for o, d in arrange.distribute_offsets([c, a, b], "v"))
        self.assertEqual((moves[id(a)], moves[id(c)]), (0.0, 0.0))
        self.assertAlmostEqual(moves[id(b)], -20.0)              # écart de 20 mm de part et d'autre

    def test_resize_without_anchor_keeps_the_origin(self):
        a = rect(10, 10)
        arrange.resize_shape(a, 40.0, 30.0)
        self.assertEqual((a.x_mm, a.y_mm, a.width_mm, a.height_mm), (10, 10, 40.0, 30.0))


@unittest.skipIf(VectorEditorController is None, "PyQt6 non importable ici")
class TabCommandsTests(unittest.TestCase):
    """Onglet de l'éditeur (ui/vector_editor/tab.py) : chaque bouton a son action dans le contrôleur."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from laser_studio.ui.vector_editor.tab import VectorEditorTab
        self.layers = LayersModel()
        self.canvas = VectorCanvasView(self.layers, document=VectorDocument())
        self.dialogs = FakeDialogs()
        self.editor = VectorEditorController(self.canvas.document, self.canvas, self.layers, MachineConfig(),
                                             self.dialogs)
        self.tab = VectorEditorTab(self.canvas)
        self.addCleanup(self.tab.deleteLater)

    def test_every_command_of_the_tab_has_an_action(self):
        from laser_studio.ui.vector_editor.tab import COMMANDS
        from laser_studio.controllers.generators import GeneratorsController
        from laser_studio.controllers.layout import LayoutController
        layout = LayoutController(self.editor, forms=None)
        parts = [self.editor.commands(), GeneratorsController(self.editor, layout, forms=None).commands(),
                 layout.commands()]
        names = [name for part in parts for name in part]
        self.assertEqual(len(names), len(set(names)))                  # aucune commande traitée deux fois
        # Les boutons de l'onglet, plus les commandes du clavier et du clic droit du canevas.
        keyboard = {"copy", "paste", "group", "ungroup", "resize"}
        self.assertEqual(sorted(set(COMMANDS) | keyboard), sorted(names))   # « library » : page des générateurs
        self.assertTrue(all(callable(action) for part in parts for action in part.values()))

    def test_buttons_emit_their_command(self):
        got = []
        self.tab.command.connect(got.append)
        self.tab.top_buttons["import"].click()
        next(a for a in self.tab.edit_toolbar.actions() if a.text() == tr("ui.vector_generators")).trigger()
        next(a for a in self.tab.edit_toolbar.actions() if a.text() == tr("ui.vector_nesting")).trigger()
        next(a for a in self.tab.edit_toolbar.actions() if a.text() == tr("ui.vector_rotate_90")).trigger()
        self.assertEqual(got, ["import", "generators", "nesting", "rotate"])

    def test_draw_tool_goes_through_the_controller(self):
        self.tab.draw_tool_requested.connect(self.editor.choose_draw_tool)
        self.editor.draw_tool_changed.connect(self.tab.show_draw_tool)
        self.tab.draw_buttons["circle"].trigger()
        self.assertEqual(self.canvas.draw_tool, "circle")
        self.assertEqual([k for k, a in self.tab.draw_buttons.items() if a.isChecked()], ["circle"])
        self.layers.layers.clear()                              # sans calque : outil refusé, sélection cochée
        self.tab.draw_buttons["line"].trigger()
        self.assertIsNone(self.canvas.draw_tool)
        self.assertEqual([k for k, a in self.tab.draw_buttons.items() if a.isChecked()], [None])
        self.assertEqual(self.dialogs.kinds(), ["warning"])

    def test_snap_settings_reach_the_canvas(self):
        self.tab.snap_check.setChecked(True)
        self.tab.snap_step_spin.setValue(2.5)
        self.assertEqual((self.canvas.snap_enabled, self.canvas.snap_step_mm), (True, 2.5))


if __name__ == "__main__":
    unittest.main()
