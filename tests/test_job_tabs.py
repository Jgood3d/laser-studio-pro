"""Onglets Aperçu 2D, Console et File d'attente : signaux et état."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtCore import QPointF
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
    from laser_studio.i18n import tr
    from laser_studio.ui.tabs.console import ConsoleTab
    from laser_studio.ui.tabs.job_queue import JobQueueTab
    from laser_studio.ui.tabs.preview_2d import Preview2DTab
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
    def test_no_stats_nor_export_buttons_left(self):
        # Statistiques : panneau machine ; export : menu Fichier.
        tab = self.make(ConsoleTab)
        self.assertEqual(tab.findChildren(QPushButton), [])
        self.assertFalse(hasattr(tab, "set_stats"))


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class JobStatsPanelTests(_TabTest):
    def test_set_stats(self):
        from laser_studio.ui.machine.job_stats import JobStatsPanel
        panel = self.make(JobStatsPanel)
        self.assertEqual(panel.title(), tr("ui.job_stats_box"))
        panel.set_stats("Lignes : 4", "Puissance : 12 %", "Temps : 1 min")
        texts = [label.text() for label in panel.findChildren(QLabel)]
        self.assertEqual(texts, ["Lignes : 4", "Puissance : 12 %", "Temps : 1 min"])


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class ConnectionPanelTests(_TabTest):
    def make_panel(self):
        from PyQt6.QtGui import QStandardItemModel
        from laser_studio.ui.machine.connection import ConnectionPanel
        model = QStandardItemModel()
        panel = ConnectionPanel(model)
        self.addCleanup(panel.deleteLater)
        return panel, model

    def test_ports_share_the_model(self):
        from PyQt6.QtWidgets import QComboBox
        panel, model = self.make_panel()
        other = QComboBox()
        other.setModel(model)
        other.addItems(["COM1", "COM2"])
        self.assertEqual(panel.ports_combo.count(), 2)

    def test_buttons_emit_their_signal(self):
        panel, _model = self.make_panel()
        refresh, connect = record(panel.refresh_requested), record(panel.connect_requested)
        panel.refresh_button.click()
        panel.connect_button.click()
        self.assertEqual((refresh, connect), ([()], [()]))
        self.assertEqual(panel.refresh_button.toolTip(), tr("usb.refresh_ports"))

    def test_connect_button_follows_the_state(self):
        panel, _model = self.make_panel()
        self.assertEqual(panel.title(), tr("ui.connection_box"))
        self.assertEqual(panel.connect_button.text(), tr("laser.connect"))
        panel.set_connected(True)
        self.assertEqual(panel.connect_button.text(), tr("laser.disconnect"))


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
