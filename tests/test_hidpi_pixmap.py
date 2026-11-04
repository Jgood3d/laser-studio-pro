"""Images réduites nettes sur écran haute résolution
(widgets_extra.scaled_to_width_hidpi) : bannière du splash et « À propos »."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap
    from widgets_extra import scaled_to_width_hidpi
except ImportError:  # PyQt6 manquant
    scaled_to_width_hidpi = None


@unittest.skipIf(scaled_to_width_hidpi is None, "PyQt6 non importable ici")
class HiDpiPixmapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.banner = QPixmap(1408, 768)

    def check(self, ratio, physical_width, logical_width):
        pm = scaled_to_width_hidpi(self.banner, 600, ratio)
        self.assertEqual(pm.width(), physical_width)
        self.assertAlmostEqual(pm.devicePixelRatio(), max(1.0, ratio))
        self.assertAlmostEqual(pm.deviceIndependentSize().width(),
                               logical_width)

    def test_normal_screen(self):
        self.check(1.0, 600, 600)

    def test_high_resolution_screen_keeps_the_same_apparent_size(self):
        self.check(2.0, 1200, 600)    # 1200 px réels, 600 px à l'écran
        self.check(1.5, 900, 600)

    def test_ratio_below_one_is_ignored(self):
        self.check(0.5, 600, 600)


if __name__ == "__main__":
    unittest.main()
