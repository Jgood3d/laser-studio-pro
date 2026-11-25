"""Stencil Studio en widgets Qt (expérimental, ui/qt/) : parcours principal de la fenêtre et entrée du menu
Outils, à côté de la version web."""
import os
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))


try:
    import cv2  # noqa: F401
    from PyQt6.QtWidgets import QApplication
    from stencil_studio.controllers.service import StudioService
except ImportError:          # OpenCV ou PyQt6 absents
    StudioService = None

IMAGE = os.path.join(REPO, "src", "stencil_studio", "exemple", "girl1.png")


@unittest.skipIf(StudioService is None, "OpenCV ou PyQt6 non importables ici")
class QtDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tempfile.TemporaryDirectory()
        os.environ["XDG_DATA_HOME"] = cls.data.name
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.data.cleanup()

    def wait(self, condition, timeout=120):
        end = time.time() + timeout
        while time.time() < end and not condition():
            self.app.processEvents()
            time.sleep(0.02)
        self.assertTrue(condition())

    def test_main_path_open_preview_mode_export(self):
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        exported = []
        dialog.export_ready.connect(exported.append)
        dialog.open_path(IMAGE)
        self.wait(lambda: dialog.result_view._pixmap is not None)
        self.assertIn("contours", dialog.status.text())
        halftone = next(b for b in dialog.mode_buttons.buttons() if b.property("mode") == "halftone")
        halftone.click()
        self.assertEqual(dialog.state["output"], "halftone")
        self.assertFalse(dialog.form.boxes["Halftone dots"].isHidden())
        self.assertTrue(dialog.form.boxes["Cleanup and bridges"].isHidden())
        dialog.export_svg()
        self.wait(lambda: exported)
        with open(exported[0], encoding="utf-8") as f:
            self.assertIn("<svg", f.read())

    def test_menu_entry_opens_the_qt_version_next_to_the_web_one(self):
        from unittest import mock
        from PyQt6.QtWidgets import QWidget
        from stencil_studio.controllers.studio import StencilStudioController
        window = QWidget()
        self.addCleanup(window.deleteLater)
        controller = StencilStudioController(window, theme=dict, language="fr", dialogs=mock.Mock())
        forwarded = []
        controller.export_ready.connect(forwarded.append)
        controller.open_qt()
        self.addCleanup(controller.qt_dialog.deleteLater)
        controller.qt_dialog.export_ready.emit("/tmp/x.svg")
        self.assertEqual(forwarded, ["/tmp/x.svg"])               # même chemin vers Laser Studio que la page
        self.assertIsNone(controller.dialog)                       # la page web n'a pas été ouverte


if __name__ == "__main__":
    unittest.main()
