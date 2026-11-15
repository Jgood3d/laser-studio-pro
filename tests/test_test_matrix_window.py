"""Matrice de test : après « Générer », la fenêtre se ferme et l'aperçu 2D s'affiche."""
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton
    from laser_studio.i18n import tr
except ImportError:  # PyQt6 manquant
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt6 non importable ici")
class TestMatrixWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.mkdtemp()                       # préférences isolées : rien chez l'utilisateur
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp, "XDG_DATA_HOME": tmp}):
            from laser_studio import main_window
            from laser_studio import gcode_generation_mixin
            cls.gen = gcode_generation_mixin
            cls.app = QApplication.instance() or QApplication([])
            # Préchauffage de Stencil Studio (QTimer 3 s) : QtWebEngine plante hors écran.
            mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
            cls.win = main_window.FullLaserStudio()
            cls.win.show()

    def open_matrix_window(self):
        win = self.win
        win.main_tabs_view.setCurrentWidget(win.tab_vector_editor)
        win.show_settings_window("test_matrix")
        self.app.processEvents()
        window = win.tab_matrix.window()
        self.assertTrue(window.isVisible())
        return window

    def click_generate(self):
        button = next(b for b in self.win.tab_matrix.findChildren(QPushButton)
                      if b.text() == tr("ui.gen_test_matrix"))
        worker = mock.Mock()
        with mock.patch.object(self.gen, "TestMatrixWorker", return_value=worker), \
                mock.patch.object(QMessageBox, "warning") as warning:
            button.click()
            self.app.processEvents()
        return worker, warning

    def test_generation_closes_the_window_and_shows_the_2d_preview(self):
        window = self.open_matrix_window()
        self.win.tab_matrix.set_image_test_checked(False)
        worker, _ = self.click_generate()
        worker.start.assert_called_once()
        self.assertFalse(window.isVisible())
        self.assertIs(self.win.main_tabs_view.currentWidget(), self.win.tab_vector_2d)

    def test_window_stays_open_when_generation_cannot_start(self):
        window = self.open_matrix_window()
        self.win.raw_image = None
        self.win.tab_matrix.source_image = None
        self.win.tab_matrix.set_image_test_checked(True)    # test à partir d'une image, sans image
        worker, warning = self.click_generate()
        worker.start.assert_not_called()
        warning.assert_called_once()
        self.assertTrue(window.isVisible())
        self.assertIs(self.win.main_tabs_view.currentWidget(), self.win.tab_vector_editor)
        self.win.tab_matrix.set_image_test_checked(False)
        window.close()


if __name__ == "__main__":
    unittest.main()
