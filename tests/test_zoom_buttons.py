"""Loupes « + » et « − » des onglets « Graver une image » et « Visualisation 2D G-Code » (boutons et
Ctrl++ / Ctrl+-)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtGui import QImage
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.machine.job_position import JobPositionBox
    from laser_studio.ui.tabs.image.tab import ImageTab
    from laser_studio.ui.tabs.preview_2d import Preview2DTab
except ImportError:  # PyQt6 / pyqtgraph manquants
    ImageTab = None


@unittest.skipIf(ImageTab is None, "PyQt6 non importable ici")
class ZoomButtonsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_image_tab_zooms_both_previews(self):
        tab = ImageTab()
        self.addCleanup(tab.deleteLater)
        image = QImage(200, 100, QImage.Format.Format_Grayscale8)
        image.fill(128)
        tab.source_view.set_image(image)
        tab.dither_view.set_image(image)
        before = [v.transform().m11() for v in (tab.source_view, tab.dither_view)]
        self.assertNotIn(tab.zoom_in_action, tab.view_toolbar.actions())   # dans la barre du haut, posée par la fenêtre
        tab.zoom_in_action.trigger()
        after = [v.transform().m11() for v in (tab.source_view, tab.dither_view)]
        self.assertTrue(all(abs(a / b - 1.25) < 1e-6 for a, b in zip(after, before)))
        tab.zoom_out_action.trigger()
        back = [v.transform().m11() for v in (tab.source_view, tab.dither_view)]
        self.assertTrue(all(abs(a - b) < 1e-6 for a, b in zip(back, before)))

    def test_preview_zooms_the_plot(self):
        tab = Preview2DTab(JobPositionBox())
        self.addCleanup(tab.deleteLater)
        box = tab.plot_widget.getViewBox()
        box.setRange(xRange=(0, 100), yRange=(0, 100), padding=0)
        width = box.viewRange()[0][1] - box.viewRange()[0][0]
        # Loupes au bout à droite, comme dans les autres barres flottantes.
        self.assertEqual(tab.options_toolbar.actions()[-2:], [tab.zoom_in_action, tab.zoom_out_action])
        tab.zoom_in_action.trigger()
        self.assertLess(box.viewRange()[0][1] - box.viewRange()[0][0], width)
        tab.zoom_out_action.trigger()
        self.assertAlmostEqual(box.viewRange()[0][1] - box.viewRange()[0][0], width, places=3)


@unittest.skipIf(ImageTab is None, "PyQt6 non importable ici")
class FloatingToolbarsLookAlikeTests(unittest.TestCase):
    """Barres flottantes : annuler / refaire puis loupes au bout à droite, mêmes icônes que l'éditeur
    vectoriel (Breeze dans la couleur du thème)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _pixels(icon):
        return icon.pixmap(22, 22).toImage()

    def test_image_toolbar_ends_like_the_vector_one(self):
        from laser_studio.ui.app.menu.actions import AppActions
        from laser_studio.ui.utils import palette_icon
        from laser_studio.ui.widgets import FloatingToolBar
        tab = ImageTab()
        self.addCleanup(tab.deleteLater)
        actions = AppActions()
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "laser_studio", "ui",
                                "app", "main_window.py"), encoding="utf-8").read()
        bar = src[src.index("self.image_floating_toolbar = FloatingToolBar("):]
        bar = bar[:bar.index("self.tab_previews.preview_area)")]
        self.assertTrue(bar.rstrip().rstrip(",").endswith(
            "None, a.image_undo, a.image_redo,\n             None, self.tab_previews.zoom_in_action, "
            "self.tab_previews.zoom_out_action]"))
        for action, name in ((actions.image_undo, "edit-undo"), (actions.image_redo, "edit-redo"),
                             (actions.image_delete, "edit-delete"), (actions.image_rotate_right, "object-rotate-right")):
            self.assertEqual(self._pixels(action.icon()), self._pixels(palette_icon(name, QApplication.palette())),
                             name)
        self.assertIsInstance(tab.view_toolbar, FloatingToolBar)


if __name__ == "__main__":
    unittest.main()
