"""Outils de la souris du canevas vectoriel (ui/vector_editor/tools/), pilotés par de vrais événements
souris et clavier sur un VectorCanvasView hors écran : dessin, dimensions au clavier, accroche,
mesure, déplacement avec grille, panoramique, édition des nœuds."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent, QPainterPath
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QGraphicsEllipseItem, QGraphicsSimpleTextItem
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.vector_objects import ShapeObject, SvgPathObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
except ImportError:  # PyQt6 manquant
    VectorCanvasView = None

L = None if VectorCanvasView is None else Qt.MouseButton.LeftButton


@unittest.skipIf(VectorCanvasView is None, "PyQt6 non importable ici")
class CanvasToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.layers = LayersModel()
        self.canvas = VectorCanvasView(self.layers)
        self.addCleanup(self.canvas.deleteLater)
        self.canvas.resize(900, 700)
        self.canvas.show()
        self.canvas.set_work_area(300.0, 200.0)
        self.canvas.resetTransform()
        self.canvas.scale(2.0, 2.0)
        self.app.processEvents()
        self.layer = self.layers.layers[0].id
        self.vp = self.canvas.viewport()

    def at(self, x_mm, y_mm):
        p = self.canvas.mapFromScene(self.canvas.mm_to_scene(x_mm, y_mm))
        return QPoint(p.x(), p.y())

    def click(self, x, y, modifiers=Qt.KeyboardModifier.NoModifier):
        QTest.mousePress(self.vp, L, modifiers, self.at(x, y))
        QTest.mouseRelease(self.vp, L, modifiers, self.at(x, y))

    def move(self, x, y, buttons=Qt.MouseButton.NoButton):
        p = self.at(x, y)
        QApplication.sendEvent(self.vp, QMouseEvent(QEvent.Type.MouseMove, QPointF(p), QPointF(self.vp.mapToGlobal(p)),
                                                    Qt.MouseButton.NoButton, buttons, Qt.KeyboardModifier.NoModifier))

    def drag(self, x1, y1, x2, y2, button=None):
        button = button or L
        QTest.mousePress(self.vp, button, Qt.KeyboardModifier.NoModifier, self.at(x1, y1))
        for i in range(1, 5):
            self.move(x1 + (x2 - x1) * i / 4, y1 + (y2 - y1) * i / 4, button)
        QTest.mouseRelease(self.vp, button, Qt.KeyboardModifier.NoModifier, self.at(x2, y2))

    def type(self, text):
        for ch in text:
            QTest.keyClick(self.canvas, ch)
        QTest.keyClick(self.canvas, Qt.Key.Key_Return)

    def last(self):
        return self.canvas.objects[-1]

    def test_line_by_two_clicks_and_by_length(self):
        self.canvas.set_draw_tool("line", self.layer)
        self.click(60, 60)
        self.move(80, 60)
        self.click(80, 60)
        self.assertEqual(self.last().shape_type, "Ligne")
        self.assertAlmostEqual(self.last().width_mm, 20.0, delta=0.6)
        self.click(10, 150)
        self.type("25")                                         # longueur au clavier
        self.assertAlmostEqual(self.last().width_mm, 25.0)
        self.assertEqual(len(self.canvas.document._undo_stack), 2)

    def test_rectangle_in_three_points_and_by_dimensions(self):
        self.canvas.set_draw_tool("rect", self.layer)
        self.click(60, 120)
        self.click(90, 120)                                     # base de 30 mm
        self.drag(80, 120, 80, 135)                             # profondeur tirée : 15 mm
        rect = self.last()
        self.assertAlmostEqual(rect.width_mm, 30.0, delta=0.6)
        self.assertAlmostEqual(rect.height_mm, 15.0, delta=0.6)
        self.click(150, 150)
        self.type("30x20")
        self.assertEqual((self.last().width_mm, self.last().height_mm), (30.0, 20.0))

    def test_circle_in_one_gesture_and_escape(self):
        self.canvas.set_draw_tool("circle", self.layer)
        self.drag(200, 100, 210, 100)                           # centre, puis rayon de 10 mm
        self.assertAlmostEqual(self.last().width_mm, 20.0, delta=1.0)
        count = len(self.canvas.objects)
        self.click(250, 150)
        QTest.keyClick(self.canvas, Qt.Key.Key_Escape)          # tracé commencé : annulé, outil gardé
        self.assertEqual((len(self.canvas.objects), self.canvas.draw_tool), (count, "circle"))
        QTest.keyClick(self.canvas, Qt.Key.Key_Escape)          # rien en cours : retour à la sélection
        self.assertIsNone(self.canvas.draw_tool)

    def test_drawing_snaps_to_existing_corners(self):
        self.canvas.add_object(ShapeObject("Rectangle", 30, 20, layer_id=self.layer, x_mm=20, y_mm=20))
        self.canvas.set_draw_tool("line", self.layer)
        self.click(50.6, 40.4)                                  # près du coin (50, 40)
        self.click(90, 40)
        line = self.last()
        self.assertEqual((round(line.x_mm, 3), round(line.y_mm, 3)), (50.0, 40.0))

    def test_measure_keeps_its_annotation(self):
        self.canvas.set_draw_tool("measure", self.layer)
        self.click(10, 10)
        self.click(40, 50)
        texts = [it.text() for it in self.canvas.measure.labels if isinstance(it, QGraphicsSimpleTextItem)]
        self.assertEqual([t.split(" mm")[0] for t in texts], ["50.00"])        # 30 × 40 → 50 mm
        self.canvas.set_draw_tool(None)
        self.assertEqual(len(self.canvas.measure.labels), 2)                   # trait + texte, gardés
        self.canvas.measure.clear_labels()
        self.assertEqual(self.canvas.measure.labels, [])

    def test_drag_moves_the_selection_on_the_grid(self):
        self.canvas.add_object(ShapeObject("Rectangle", 30, 20, layer_id=self.layer, x_mm=20, y_mm=20))
        moved = []
        self.canvas.object_moved.connect(moved.append)
        self.canvas.set_snap_enabled(True)
        self.canvas.set_snap_step(5.0)
        self.drag(30, 30, 43.7, 32.1)
        rect = self.last()
        self.assertEqual((rect.x_mm % 5.0, rect.y_mm % 5.0), (0.0, 0.0))
        self.assertEqual(moved, [rect])
        self.assertEqual(len(self.canvas.document._undo_stack), 1)

    def test_middle_button_pans_the_view(self):
        bar = self.canvas.horizontalScrollBar()
        before = bar.value()
        self.drag(150, 100, 140, 100, button=Qt.MouseButton.MiddleButton)
        self.assertGreater(bar.value(), before)

    def test_node_edit_moves_adds_and_removes_points(self):
        path = QPainterPath()
        path.addRect(0, 0, 20, 10)
        self.canvas.add_object(SvgPathObject(local_path_data=path, source_tag="g", layer_id=self.layer,
                                             x_mm=100, y_mm=100))
        item = self.canvas.item_for(self.last())
        item.setSelected(True)
        self.assertTrue(self.canvas.nodes.enter())
        self.assertTrue(self.canvas.nodes.active)

        def handles():
            return sorted((h for h in self.canvas.scene_obj.items() if isinstance(h, QGraphicsEllipseItem)
                           and isinstance(h.data(0), tuple) and h.data(0)[0] == "node"),
                          key=lambda h: h.data(0)[1:])

        def mm(h):
            return self.canvas.scene_to_mm(h.rect().center())

        count = len(handles())
        a, b = mm(handles()[1]), mm(handles()[2])
        QTest.mouseDClick(self.vp, L, Qt.KeyboardModifier.NoModifier, self.at((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        self.assertEqual(len(handles()), count + 1)             # sommet ajouté sur le segment
        x, y = mm(handles()[0])
        self.drag(x, y, x - 4, y - 3)                           # (contour fermé : sommet de départ en double)
        self.assertTrue(any(abs(hx - (x - 4)) < 0.6 and abs(hy - (y - 3)) < 0.6 for hx, hy in map(mm, handles())))
        x, y = mm(handles()[2])
        QTest.mousePress(self.vp, L, Qt.KeyboardModifier.NoModifier, self.at(x, y))
        QTest.keyClick(self.canvas, Qt.Key.Key_Delete)
        QTest.mouseRelease(self.vp, L, Qt.KeyboardModifier.NoModifier, self.at(x, y))
        self.assertEqual(len(handles()), count)                 # sommet retiré
        QTest.keyClick(self.canvas, Qt.Key.Key_Escape)
        self.assertFalse(self.canvas.nodes.active)
        self.assertEqual(handles(), [])


if __name__ == "__main__":
    unittest.main()
