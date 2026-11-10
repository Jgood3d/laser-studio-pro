"""Onglets Aperçu 2D, Console et File d'attente : signaux et état."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtCore import QPointF
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
    from i18n import tr
    from ui.tabs.console import ConsoleTab
    from ui.tabs.job_queue import JobQueueTab
    from ui.tabs.preview_2d import Preview2DTab
except ImportError:  # PyQt6, pyqtgraph... manquants
    ConsoleTab = None


def record(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


class _TabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, cls):
        tab = cls()
        self.addCleanup(tab.deleteLater)
        return tab


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class Preview2DTabTests(_TabTest):
    def test_display_options_ask_for_a_redraw(self):
        tab = self.make(Preview2DTab)
        received = record(tab.display_options_changed)
        for check in (
            tab.flip_check,
            tab.negative_check,
            tab.hide_rapid_check,
        ):
            check.toggle()
        self.assertEqual(len(received), 3)
        tab.optimize_path_check.toggle()  # prochaine génération seulement
        self.assertEqual(len(received), 3)

    def test_click_is_emitted_in_bed_millimetres(self):
        tab = self.make(Preview2DTab)
        tab.resize(400, 300)
        tab.show()
        view_box = tab.plot_widget.getPlotItem().vb
        view_box.setRange(xRange=(0, 100), yRange=(0, 100), padding=0)
        scene_pos = view_box.mapViewToScene(QPointF(40.0, 25.0))

        class Click:
            def scenePos(self):
                return scene_pos

        received = record(tab.plot_clicked)
        tab.plot_widget.scene().sigMouseClicked.emit(Click())
        ((x, y),) = received
        self.assertAlmostEqual(x, 40.0, places=3)
        self.assertAlmostEqual(y, 25.0, places=3)

    def test_fullscreen_is_relayed(self):
        tab = self.make(Preview2DTab)
        received = record(tab.fullscreen_requested)
        tab._fullscreen_control.trigger()
        self.assertEqual(received, [()])


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class ConsoleTabTests(_TabTest):
    def test_each_export_button_emits_its_extension(self):
        tab = self.make(ConsoleTab)
        received = record(tab.export_requested)
        for button in tab.findChildren(QPushButton):
            button.click()
        self.assertEqual(received, [(".gcode",), (".nc",), (".gc",)])

    def test_set_stats(self):
        tab = self.make(ConsoleTab)
        tab.set_stats("Lignes : 4", "Puissance : 12 %", "Temps : 1 min")
        texts = [label.text() for label in tab.findChildren(QLabel)]
        self.assertEqual(
            texts[:3], ["Lignes : 4", "Puissance : 12 %", "Temps : 1 min"]
        )


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class JobQueueTabTests(_TabTest):
    def test_buttons_emit_their_signal(self):
        tab = self.make(JobQueueTab)
        for key, signal in (
            ("ui.queue_add_current", tab.add_current_requested),
            ("ui.queue_remove_selected", tab.remove_selected_requested),
            ("ui.queue_clear", tab.clear_requested),
            ("ui.queue_run", tab.run_requested),
        ):
            received = record(signal)
            button = next(
                b for b in tab.findChildren(QPushButton) if b.text() == tr(key)
            )
            button.click()
            self.assertEqual(received, [()], key)

    def test_moving_a_job_emits_reordered(self):
        tab = self.make(JobQueueTab)
        tab.queue_list.addItems(["a", "b"])
        received = record(tab.reordered)
        model = tab.queue_list.model()
        root = model.index(0, 0).parent()
        model.moveRow(root, 0, root, 2)
        self.assertEqual(received, [()])
        self.assertEqual(
            [tab.queue_list.item(i).text() for i in range(2)], ["b", "a"]
        )


if __name__ == "__main__":
    unittest.main()
