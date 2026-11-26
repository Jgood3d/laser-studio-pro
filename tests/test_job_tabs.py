"""Onglets Aperçu 2D, Console et File d'attente : signaux et état."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtWidgets import QApplication, QGroupBox, QLabel, QPushButton
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

    def make(self, cls, *args):
        tab = cls(*args)
        self.addCleanup(tab.deleteLater)
        return tab


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class Preview2DTabTests(_TabTest):
    def test_display_options_ask_for_a_redraw(self):
        tab = self.make(Preview2DTab, QGroupBox("Position"))
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

    def test_negative_preview_is_off_by_default(self):
        """Aperçu réaliste par défaut : le négatif inversait zones gravées et non gravées."""
        tab = self.make(Preview2DTab, QGroupBox("Position"))
        self.assertFalse(tab.negative_check.isChecked())
        self.assertTrue(tab.hide_rapid_check.isChecked())

    def test_click_is_emitted_in_bed_millimetres(self):
        tab = self.make(Preview2DTab, QGroupBox("Position"))
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

    def test_no_toolbar_above_the_preview(self):
        # Plus de bandeau : une barre verticale (loupes) contre la colonne de droite, le plein écran dans la
        # barre principale ; la colonne de droite ne touche pas la poignée du séparateur.
        from PyQt6.QtWidgets import QToolBar
        from laser_studio.ui.tabs.preview_2d.tab import SIDE_PANEL_LEFT_MARGIN
        tab = self.make(Preview2DTab, QGroupBox("Position"))
        self.assertEqual(tab.findChildren(QToolBar), [tab.options_toolbar])
        self.assertEqual(tab.options_toolbar.orientation(), Qt.Orientation.Vertical)
        self.assertFalse(hasattr(tab, "fullscreen_requested"))
        self.assertGreater(SIDE_PANEL_LEFT_MARGIN, 0)
        self.assertEqual(tab.side_panel.layout().contentsMargins().left(), SIDE_PANEL_LEFT_MARGIN)


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class ConsoleTabTests(_TabTest):
    def test_no_stats_nor_export_buttons_left(self):
        # Statistiques : panneau machine ; export : menu Fichier.
        tab = self.make(ConsoleTab)
        self.assertEqual(tab.findChildren(QPushButton), [])
        self.assertFalse(hasattr(tab, "set_stats"))

    def test_a_big_gcode_fills_the_console_in_the_background(self):
        # 500 000 lignes d'un coup figeaient l'interface près d'une seconde : paquets, lecture seule pendant ce
        # temps, et gcode() déjà complet (envoi, export, file d'attente).
        from laser_studio.ui.tabs.console.tab import FILL_CHUNK_LINES
        tab = self.make(ConsoleTab)
        text = "\n".join(f"G1 X{i} S10" for i in range(FILL_CHUNK_LINES * 2 + 5)) + "\n"
        tab.set_gcode(text)
        self.assertTrue(tab.is_filling() and tab.console_edit.isReadOnly())
        self.assertEqual(tab.gcode(), text)
        while tab.is_filling():
            QApplication.processEvents()
        self.assertEqual((tab.console_edit.toPlainText(), tab.console_edit.isReadOnly()), (text, False))
        tab.set_gcode("G0 X0")                                     # petit G-Code : tout de suite, modifiable
        self.assertEqual((tab.is_filling(), tab.gcode()), (False, "G0 X0"))


@unittest.skipIf(ConsoleTab is None, "PyQt6 non importable ici")
class JobStatsPanelTests(_TabTest):
    def test_job_position_then_stats_on_the_right_of_the_2d_preview(self):
        box = QGroupBox("Position")
        tab = self.make(Preview2DTab, box)
        self.assertEqual(tab.splitter.orientation(), Qt.Orientation.Horizontal)
        self.assertIs(tab.splitter.widget(1), tab.side_panel)
        self.assertTrue(tab.splitter.widget(0).isAncestorOf(tab.plot_widget))
        layout = tab.side_panel.layout()
        # Options d'affichage, puis position du job, génération (« Optimiser le chemin » change le G-Code, pas
        # l'affichage) et statistiques.
        display, generation = layout.itemAt(0).widget(), layout.itemAt(2).widget()
        self.assertTrue(display.isAncestorOf(tab.flip_check) and not display.isAncestorOf(tab.optimize_path_check))
        self.assertTrue(generation.isAncestorOf(tab.optimize_path_check))
        self.assertEqual([layout.itemAt(i).widget() for i in (1, 3)], [box, tab.job_stats_panel])

    def test_simulation_replays_the_burned_strokes(self):
        tab = self.make(Preview2DTab, QGroupBox("Position"))
        tab.show_gcode("M4 S0\nG0 X0 Y0\nG1 X10 Y0 S500 F1000\nG1 X10 Y10\nG1 X0 Y10\nM5\n")
        tab.simulate_action.setChecked(True)
        self.assertEqual(tab.burn.done, 0)
        tab.set_head_position(50, 50)                               # position réelle : ignorée pendant ce temps
        while tab.simulate_action.isChecked():
            QApplication.processEvents()
            tab._simulation_tick()
        self.assertEqual(tab.burn.done, 3)                          # tout le parcours, puis arrêt tout seul
        self.assertEqual(tab.position_marker.getData()[0][0], 0.0)  # tête au bout du dernier trait
        tab.simulate_action.setChecked(True)
        tab.show_gcode("G0 X1 Y1\n")                               # nouveau G-Code : simulation arrêtée
        self.assertFalse(tab.simulate_action.isChecked())

    def test_side_panel_is_as_narrow_as_possible(self):
        tab = self.make(Preview2DTab, QGroupBox("Position"))
        tab.resize(1400, 600)
        tab.show()
        self.app.processEvents()
        plot, side = tab.splitter.sizes()
        self.assertEqual(side, tab.side_panel.minimumSizeHint().width())
        self.assertGreater(plot, side)

    def test_set_stats(self):
        from laser_studio.ui.tabs.preview_2d import JobStatsPanel
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
