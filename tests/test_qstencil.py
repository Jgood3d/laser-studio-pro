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

    def test_frame_wheel_drag_rotation_preset_and_exports(self):
        from unittest import mock
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent, QWheelEvent
        from PyQt6.QtWidgets import QFileDialog
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.resize(1400, 900)
        dialog.show()
        dialog.open_path(IMAGE)
        view = dialog.source_view

        def wheel(dy, modifiers=Qt.KeyboardModifier.NoModifier):
            view.wheelEvent(QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, dy),
                                        Qt.MouseButton.NoButton, modifiers, Qt.ScrollPhase.NoScrollPhase, False))
        wheel(600)                                                     # molette : cadre plus petit
        self.assertLess(view.frame()["w"], 1.0)
        self.assertEqual(dialog.state["zoom"], round(view.frame()["w"], 2))
        start, centre = view.frame()["cx"], view.rect().center()
        for handler, point in ((view.mousePressEvent, centre), (view.mouseMoveEvent, centre + QPoint(40, 0)),
                               (view.mouseReleaseEvent, centre + QPoint(40, 0))):
            handler(QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(point), QPointF(point), Qt.MouseButton.LeftButton,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.assertGreater(view.frame()["cx"], start)                  # glissé vers la droite
        wheel(-120, Qt.KeyboardModifier.AltModifier)                   # Alt + molette : rotation
        self.assertEqual((dialog.state["rot"], dialog.form.value("rot")), (1.0, 1.0))
        preset = dialog.form.widgets["preset"]
        preset.setCurrentIndex(preset.findData("silhouette"))           # style prédéfini
        self.assertEqual(dialog.state["preset"], "")
        for key, value in dialog.spec.presets["silhouette"].items():
            self.assertEqual(dialog.state[key], value, key)
        exported = []
        dialog.export_ready.connect(exported.append)
        dialog.export("dxf")                                            # DXF : vers Laser Studio
        self.wait(lambda: exported)
        self.assertTrue(exported[0].endswith("_cut.dxf"))
        saved = os.path.join(tempfile.mkdtemp(), "box.svg")
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(saved, "")):
            dialog.export("boxsvg")                                     # caisson : enregistré sur le disque
            self.wait(lambda: os.path.exists(saved))
        self.assertEqual(len(exported), 1)
        self.assertFalse(dialog.export_actions["png"].isEnabled())      # gravure PNG : mode Gravure seulement

    def test_subject_box_and_painted_hints(self):
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from stencil_studio.ui.qt import QStencilDialog
        dialog = QStencilDialog(language="fr")
        self.addCleanup(dialog.deleteLater)
        dialog.resize(1400, 900)
        dialog.show()
        dialog.open_path(IMAGE)
        view = dialog.source_view
        scale, ox, oy = view._view()

        def drag(a, b):
            for handler, (fx, fy) in ((view.mousePressEvent, a), (view.mouseMoveEvent, b), (view.mouseReleaseEvent, b)):
                point = QPointF(ox + fx * view.iw * scale, oy + fy * view.ih * scale)
                handler(QMouseEvent(QMouseEvent.Type.MouseMove, point, point, Qt.MouseButton.LeftButton,
                                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        paint = [b for b in dialog.tool_buttons.buttons() if b.property("tool") in ("fg", "bg", "erase")]
        self.assertTrue(all(b.isHidden() for b in paint))              # repères : seulement en isolant le sujet
        next(b for b in dialog.tool_buttons.buttons() if b.property("tool") == "box").click()
        drag((0.30, 0.15), (0.70, 0.60))
        self.assertTrue(dialog.state["isolate"])                       # le rectangle isole le sujet
        self.assertEqual(round(view.frame()["cx"], 3), 0.5)            # cadre réglé sur le rectangle
        self.assertEqual(dialog.request(300)["box"], view.subject_box)
        self.assertFalse(any(b.isHidden() for b in paint))
        next(b for b in dialog.tool_buttons.buttons() if b.property("tool") == "fg").click()
        drag((0.48, 0.30), (0.52, 0.45))                                # trait vert sur le sujet
        self.wait(lambda: dialog.service.session.has_hints())

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
