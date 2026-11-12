"""Point rouge de position de la tête sur l'aperçu 2D G-Code (gcode_position_marker)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio import main_window
except ImportError:  # PyQt6, pyqtgraph... manquants
    main_window = None


@unittest.skipIf(main_window is None, "main_window non importable ici")
class PositionMarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Préchauffage de Stencil Studio (QTimer 3 s) : QtWebEngine plante hors écran.
        mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
        cls.win = main_window.FullLaserStudio()

    def marker_shown(self):
        return self.win.gcode_position_marker in self.win.plot_widget.getPlotItem().items

    def test_marker_survives_a_new_preview(self):
        self.win.plot_gcode_preview("G21\nG90\nG0 X0 Y0\nG1 X50 Y20 F1000 S500\nM5\n")
        self.assertTrue(self.marker_shown())
        self.win._on_status_updated("Run", 12.5, 7.0, 0.0)          # rapport d'état GRBL pendant le job
        xs, ys = self.win.gcode_position_marker.getData()
        self.assertEqual((list(xs), list(ys)), ([12.5], [7.0]))
        self.win.plot_gcode_preview("G21\nG1 X5 Y5 F1000 S100\n")    # nouvel aperçu : toujours là
        self.assertTrue(self.marker_shown())

    def test_disconnect_hides_the_marker(self):
        self.win._on_status_updated("Idle", 3.0, 4.0, 0.0)
        self.win._update_dro_display(None, None, None, None)
        self.assertEqual(len(self.win.gcode_position_marker.getData()[0]), 0)


if __name__ == "__main__":
    unittest.main()
