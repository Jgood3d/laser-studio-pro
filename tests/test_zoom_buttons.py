"""Loupes « + » et « − » des onglets « Graver une image » et « Visualisation 2D G-Code » (boutons et
Ctrl++ / Ctrl+-)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtGui import QImage
    from PyQt6.QtWidgets import QApplication
    from laser_studio.i18n import tr
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
        actions = {a.text(): a for a in tab.toolbar.actions()}
        actions[tr("ui.zoom_in")].trigger()
        after = [v.transform().m11() for v in (tab.source_view, tab.dither_view)]
        self.assertTrue(all(abs(a / b - 1.25) < 1e-6 for a, b in zip(after, before)))
        actions[tr("ui.zoom_out")].trigger()
        back = [v.transform().m11() for v in (tab.source_view, tab.dither_view)]
        self.assertTrue(all(abs(a - b) < 1e-6 for a, b in zip(back, before)))

    def test_preview_zooms_the_plot(self):
        tab = Preview2DTab(JobPositionBox())
        self.addCleanup(tab.deleteLater)
        box = tab.plot_widget.getViewBox()
        box.setRange(xRange=(0, 100), yRange=(0, 100), padding=0)
        width = box.viewRange()[0][1] - box.viewRange()[0][0]
        self.assertIn(tab.zoom_in_action, tab.options_toolbar.actions())
        tab.zoom_in_action.trigger()
        self.assertLess(box.viewRange()[0][1] - box.viewRange()[0][0], width)
        tab.zoom_out_action.trigger()
        self.assertAlmostEqual(box.viewRange()[0][1] - box.viewRange()[0][0], width, places=3)


if __name__ == "__main__":
    unittest.main()
