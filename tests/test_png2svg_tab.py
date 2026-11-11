"""Onglet « Vectorisation d'image » (Png2SvgTab) : relais des signaux."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.tabs.png2svg import Png2SvgTab
except ImportError:  # PyQt6, potrace... manquants
    Png2SvgTab = None


def record(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


@unittest.skipIf(Png2SvgTab is None, "Png2SvgTab non importable ici")
class Png2SvgTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        tab = Png2SvgTab()
        self.addCleanup(tab.deleteLater)
        return tab

    def test_converter_requests_are_relayed(self):
        tab = self.make()
        sent, changed = record(tab.send_to_vector_requested), record(
            tab.image_changed
        )
        tab.converter.sendToVectorEditor.emit("<svg/>")
        tab.converter.imageChanged.emit()
        self.assertEqual(sent, [("<svg/>",)])
        self.assertEqual(changed, [()])

    def test_fullscreen_is_relayed(self):
        tab = self.make()
        received = record(tab.fullscreen_requested)
        tab._fullscreen_control.trigger()
        self.assertEqual(received, [()])


if __name__ == "__main__":
    unittest.main()
