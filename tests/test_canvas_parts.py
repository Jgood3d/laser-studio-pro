"""Parties du canevas de l'éditeur vectoriel, testées chacune seule : zone de travail et repère (sans Qt), suivi
du document par les éléments graphiques (une scène, sans vue), raccourcis clavier (vrais événements), et le
canevas qui replace ses objets quand le plateau change de taille."""
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.vector.work_area import WorkArea, fit_scale, grid_step  # noqa: E402

try:
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtWidgets import QApplication, QGraphicsScene
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.vector_document import VectorDocument
    from laser_studio.models.vector_objects import ShapeObject
    from laser_studio.ui.vector_editor import shortcuts
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.ui.vector_editor.document_items import DocumentItems
    from laser_studio.ui.vector_editor.item import VectorGraphicsItem
except ImportError:  # PyQt6 manquant
    DocumentItems = None


class WorkAreaTests(unittest.TestCase):
    def test_machine_and_scene_frames(self):
        area = WorkArea(300.0, 200.0)                          # 4 px par mm, Y machine vers le haut
        self.assertEqual(area.to_scene(0, 0), (0.0, 800.0))     # origine : coin bas-gauche
        self.assertEqual(area.to_scene(10, 5), (40.0, 780.0))
        self.assertEqual(area.to_mm(*area.to_scene(123.5, -7.25)), (123.5, -7.25))
        self.assertEqual((area.width_px, area.height_px), (1200.0, 800.0))

    def test_grid_follows_the_size_of_the_bed(self):
        self.assertEqual([grid_step(s) for s in (30, 50, 120, 300, 900, 1500)], [5, 5, 10, 20, 50, 100])
        grid = WorkArea(300.0, 200.0).grid()
        self.assertEqual(grid.step, 20)
        self.assertEqual((grid.major_x[0], grid.major_x[-1], len(grid.major_x)), (0.0, 300.0, 16))   # bords compris
        self.assertEqual(len(grid.major_y), 11)
        self.assertEqual((grid.minor_x[0], grid.minor_x[-1]), (5.0, 295.0))     # bords exclus
        self.assertNotIn(300.0, grid.minor_x)

    def test_fit_scale(self):
        self.assertAlmostEqual(fit_scale(100, 50, 900, 700, margin=60, max_scale=99), 7.8)
        self.assertEqual(fit_scale(1, 1, 900, 700, margin=60, max_scale=6.0), 6.0)       # petit objet : plafond
        self.assertIsNone(fit_scale(100, 100, 100, 700, margin=60))                      # fenêtre pas affichée


@unittest.skipIf(DocumentItems is None, "PyQt6 non importable ici")
class DocumentItemsTests(unittest.TestCase):
    """Les éléments suivent le document, avec une simple scène : aucune vue n'est nécessaire."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.document = VectorDocument()
        self.scene = QGraphicsScene()
        geometry = SimpleNamespace(px_per_mm=4.0, work_h_mm=100.0)     # ce que lit VectorGraphicsItem
        self.items = DocumentItems(self.document, self.scene,
                                   lambda obj: VectorGraphicsItem(obj, self.layers, geometry))

    def shape(self, x):
        obj = ShapeObject(layer_id=self.layers.layers[0].id)
        obj.x_mm = x
        return obj

    def test_items_follow_added_removed_and_reset_objects(self):
        a, b = self.shape(10), self.shape(50)
        for obj in (a, b):
            self.document.add(obj)
        self.assertEqual([item.obj for item in self.items.all()], [a, b])
        self.assertEqual([self.items.item_for(o).zValue() for o in (a, b)], [0, 1])   # le dernier au-dessus
        self.assertIs(self.items.item_for(a).scene(), self.scene)
        self.document.push_snapshot()
        self.document.remove(a)
        self.assertIsNone(self.items.item_for(a))
        self.document.undo()                                        # remise à zéro : de nouveaux éléments
        self.assertEqual(len(self.items.all()), 2)
        self.assertEqual(len([i for i in self.scene.items() if isinstance(i, VectorGraphicsItem)]), 2)

    def test_select_is_exact_silent_and_in_document_order(self):
        a, b, c = self.shape(1), self.shape(2), self.shape(3)
        for obj in (a, b, c):
            self.document.add(obj)
        signals = []
        self.scene.selectionChanged.connect(lambda: signals.append(True))
        self.assertEqual(self.items.select([c, a]), [a, c])
        self.assertEqual(signals, [])                                # l'appelant prévient une seule fois
        self.assertEqual({item.obj for item in self.items.selected()}, {a, c})
        self.items.select([b])
        self.assertEqual(self.items.selected_object()[1], b)

    def test_refresh_redraws_changed_objects(self):
        obj = self.shape(10)
        self.document.add(obj)
        before = self.items.item_for(obj).sceneBoundingRect().x()
        obj.x_mm = 30
        self.document.notify_changed([obj])
        self.assertAlmostEqual(self.items.item_for(obj).sceneBoundingRect().x() - before, 80.0)   # 20 mm × 4


@unittest.skipIf(DocumentItems is None, "PyQt6 non importable ici")
class ShortcutsTests(unittest.TestCase):
    @staticmethod
    def key(key, modifiers=Qt.KeyboardModifier.NoModifier, text=""):
        return QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)

    def test_commands(self):
        control = Qt.KeyboardModifier.ControlModifier
        self.assertEqual(shortcuts.key_command(self.key(Qt.Key.Key_G, control)), "group")
        self.assertEqual(shortcuts.key_command(self.key(Qt.Key.Key_D, control)), "duplicate")
        self.assertEqual(shortcuts.key_command(self.key(Qt.Key.Key_Z, control)), "undo")
        self.assertEqual(shortcuts.key_command(self.key(Qt.Key.Key_Delete)), "delete")
        self.assertIsNone(shortcuts.key_command(self.key(Qt.Key.Key_G)))            # G seul : rien

    def test_zoom_and_nudge(self):
        control, shift = Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier
        self.assertEqual(shortcuts.zoom_direction(self.key(Qt.Key.Key_Equal, control, "=")), 1)   # QWERTY
        self.assertEqual(shortcuts.zoom_direction(self.key(Qt.Key.Key_Minus, control, "-")), -1)
        self.assertEqual(shortcuts.zoom_direction(self.key(Qt.Key.Key_Minus)), 0)
        self.assertEqual(shortcuts.arrow_nudge(self.key(Qt.Key.Key_Up, shift)), (0, 1, True, False))
        self.assertIsNone(shortcuts.arrow_nudge(self.key(Qt.Key.Key_A)))


@unittest.skipIf(DocumentItems is None, "PyQt6 non importable ici")
class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_objects_stay_on_the_bed_when_it_changes_size(self):
        # Bug : le Y d'écran d'un objet dépend de la hauteur du plateau ; un plateau agrandi laissait les objets
        # dessinés à l'ancienne place jusqu'au prochain redessin.
        layers = LayersModel()
        canvas = VectorCanvasView(layers)
        self.addCleanup(canvas.deleteLater)
        obj = ShapeObject(layer_id=layers.layers[0].id, width_mm=10, height_mm=10)
        obj.x_mm, obj.y_mm = 20, 10
        item = canvas.add_object(obj)
        canvas.set_work_area(300, 400)
        self.assertAlmostEqual(canvas.scene_to_mm(item.sceneBoundingRect().bottomLeft())[1], 10, delta=0.5)

    def test_arrow_keys_ask_to_nudge_the_selection(self):
        layers = LayersModel()
        canvas = VectorCanvasView(layers)
        self.addCleanup(canvas.deleteLater)
        nudges = []
        canvas.nudge_requested.connect(lambda *args: nudges.append(args))
        canvas.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier))
        self.assertEqual(nudges, [])                               # rien de sélectionné : la vue défile
        obj = ShapeObject(layer_id=layers.layers[0].id)
        canvas.add_object(obj)
        canvas.select_objects([obj])
        canvas.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier))
        self.assertEqual(nudges, [(-1, 0, False, True)])


if __name__ == "__main__":
    unittest.main()
