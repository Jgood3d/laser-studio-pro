"""Onglet « Séparation Couleur / Verre » (SeparationTab) : comportement de
la vue et signaux."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PyQt6.QtGui import QDropEvent
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.tabs.separation import SeparationTab
except ImportError:  # PyQt6 manquant
    SeparationTab = None


def record(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


@unittest.skipIf(SeparationTab is None, "PyQt6 non importable ici")
class SeparationTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        tab = SeparationTab()
        self.addCleanup(tab.deleteLater)
        return tab

    def test_plate_follows_the_image_proportions(self):
        tab = self.make()
        tab.set_image_ratio(2.0)
        tab.fit_plate_to_image()
        self.assertEqual(tab.plate_height_spin.value(), 75.0)  # 150 / 2
        tab.plate_height_spin.setValue(50.0)
        self.assertEqual(tab.plate_width_spin.value(), 100.0)
        tab.swap_plate_size()
        self.assertEqual(
            (tab.plate_width_spin.value(), tab.plate_height_spin.value()),
            (50.0, 100.0),
        )

    def test_crop_is_only_active_with_free_proportions_and_crop_framing(self):
        tab = self.make()
        self.assertFalse(tab.crop_box.isEnabled())
        self.assertEqual(tab.frame_args(), (0, 1.0, 0.5, 0.5))
        tab.keep_ratio_check.setChecked(False)
        self.assertTrue(tab.crop_box.isEnabled())
        tab.crop_zoom_slider.setValue(150)
        self.assertEqual(tab.frame_args(), (0, 1.5, 0.5, 0.5))
        tab.framing_combo.setCurrentIndex(1)  # étirer
        self.assertFalse(tab.crop_box.isEnabled())
        self.assertEqual(tab.frame_args(), (1, 1.0, 0.5, 0.5))
        tab.reset_crop()
        self.assertEqual(tab.crop_zoom_slider.value(), 100)

    def test_signals(self):
        tab = self.make()
        tone, preview = record(tab.tone_changed), record(tab.preview_changed)
        tab.gain_slider.setValue(3)
        self.assertEqual((len(tone), len(preview)), (1, 0))
        tab.saturation_slider.setValue(200)
        self.assertEqual((len(tone), len(preview)), (1, 1))
        tab.plate_width_spin.setValue(120)
        self.assertEqual((len(tone), len(preview)), (2, 2))

    def test_support_presets(self):
        tab = self.make()
        tab.support_combo.activated.emit(1)
        self.assertEqual(
            (
                tab.saturation_slider.value(),
                tab.lightness_slider.value(),
                tab.diffusion_slider.value(),
            ),
            (170, 90, 60),
        )

    def test_dropping_an_image_emits_its_path(self):
        tab = self.make()
        dropped = record(tab.image_dropped)
        mime = QMimeData()
        mime.setUrls(
            [
                QUrl.fromLocalFile("/tmp/photo.JPG"),
                QUrl.fromLocalFile("/tmp/notes.txt"),
            ]
        )
        event = QDropEvent(
            QPointF(1, 1),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        tab.dropEvent(event)
        self.assertEqual(dropped, [("/tmp/photo.JPG",)])


if __name__ == "__main__":
    unittest.main()
