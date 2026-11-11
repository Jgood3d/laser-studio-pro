"""Onglet « Graver une image » (ImageTab, ImageSettingsPanel) et cadre
« Position du job » (JobPositionBox) : signaux et état."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtGui import QShortcut
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
    from laser_studio.i18n import tr
    from laser_studio.ui.machine.job_position import JobPositionBox
    from laser_studio.ui.tabs.image import ImageSettingsPanel, ImageTab
    from laser_studio.ui.tabs.image.material_combo import MaterialComboBox
    from laser_studio.ui.tabs.image.resolution_box import ResolutionBox
    from laser_studio.ui.widgets import SliderWithButtons
except ImportError:  # PyQt6 manquant
    ImageTab = None


def record(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


class _QtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, cls):
        widget = cls()
        self.addCleanup(widget.deleteLater)
        return widget


@unittest.skipIf(ImageTab is None, "PyQt6 non importable ici")
class ImageSettingsPanelTests(_QtTest):
    def button(self, panel, key):
        return next(
            b for b in panel.findChildren(QPushButton) if b.text() == tr(key)
        )

    def test_processing_settings_ask_for_a_new_rendering(self):
        panel = self.make(ImageSettingsPanel)
        received = record(panel.processing_changed)
        for slider in (
            panel.brightness_slider,
            panel.contrast_slider,
            panel.gamma_slider,
            panel.sharpness_slider,
        ):
            slider.setValue(slider.value() + 10)
        panel.invert_check.toggle()
        panel.algorithm_combo.setCurrentIndex(3)
        panel.lines_per_mm_spin.setValue(12.0)
        self.assertEqual(len(received), 7)

    def test_business_values(self):
        panel = self.make(ImageSettingsPanel)
        size, material = record(panel.size_changed), record(
            panel.material_changed
        )
        lmm, dpi = record(panel.lines_per_mm_changed), record(
            panel.dpi_changed
        )
        panel.width_spin.setValue(80.0)
        panel.height_spin.setValue(40.0)
        panel.material_combo.setCurrentIndex(0)
        panel.lines_per_mm_spin.setValue(12.0)
        panel.dpi_spin.setValue(300.0)
        self.assertEqual(size, [("w", 80.0), ("h", 40.0)])
        self.assertEqual(material, [("dark",)])
        self.assertEqual((lmm, dpi), ([(12.0,)], [(300.0,)]))

    def test_resolution_starts_on_the_laser_focal(self):
        panel = self.make(ImageSettingsPanel)
        self.assertEqual(panel.resolution_mode_combo.currentIndex(), 2)
        self.assertEqual(panel.resolution_stack.currentIndex(), 2)
        received = record(panel.resolution_mode_changed)
        panel.resolution_mode_combo.setCurrentIndex(1)
        self.assertEqual(received, [(1,)])

    def test_buttons_and_shortcuts_emit_their_signal(self):
        panel = self.make(ImageSettingsPanel)
        for key, signal in (
            ("img.load", panel.load_requested),
            ("img.configure_focal", panel.configure_focal_requested),
        ):
            received = record(signal)
            self.button(panel, key).click()
            self.assertEqual(received, [()], key)
        saved = record(panel.save_as_focal_requested)
        for b in panel.findChildren(QPushButton):
            if b.text() == tr("img.save_as_focal"):
                b.click()
        self.assertEqual(len(saved), 2)  # pages lignes/mm et DPI
        undo, redo = record(panel.undo_requested), record(panel.redo_requested)
        for shortcut in panel.findChildren(QShortcut):
            shortcut.activated.emit()
        self.assertEqual((undo, redo), ([()], [()]))


@unittest.skipIf(ImageTab is None, "PyQt6 non importable ici")
class ImageTabTests(_QtTest):
    def test_original_image_is_hidden_until_asked(self):
        tab = self.make(ImageTab)
        tab.show()
        self.assertFalse(tab.source_view.isVisible())
        self.assertTrue(tab.dither_view.isVisible())
        tab.show_original_check.setChecked(True)
        self.assertTrue(tab.source_view.isVisible())

    def test_toolbar_requests(self):
        tab = self.make(ImageTab)
        compare = record(tab.compare_requested)
        fullscreen = record(tab.fullscreen_requested)
        toolbar_actions = [
            a
            for a in tab.findChildren(type(tab._fullscreen_control))
            if a.text() == tr("img.compare_algos")
        ]
        toolbar_actions[0].trigger()
        tab._fullscreen_control.trigger()
        self.assertEqual((compare, fullscreen), ([()], [()]))

    def test_settings_width_follows_longer_texts(self):
        tab = self.make(ImageTab)
        before = tab._settings_scroll.width()
        tab.settings.focal_info_label.setText("x" * 120)
        tab.fit_settings_width()
        self.assertGreater(tab._settings_scroll.width(), before)


@unittest.skipIf(ImageTab is None, "PyQt6 non importable ici")
class JobPositionBoxTests(_QtTest):
    def test_origin_choices(self):
        box = self.make(JobPositionBox)
        self.assertEqual(box.title(), tr("ui.job_position_box"))
        self.assertEqual(
            [box.origin_combo.itemText(i) for i in range(2)],
            [tr("ui.origin_bottom_left"), tr("ui.origin_center")],
        )


@unittest.skipIf(ImageTab is None, "PyQt6 non importable ici")
class ImagePanelPartsTests(_QtTest):
    def test_slider_buttons_move_by_their_step_and_show_the_value(self):
        row = SliderWithButtons(
            0, 300, 100, step=10, formatter=lambda v: f"{v / 100:.2f}"
        )
        self.addCleanup(row.deleteLater)
        received = record(row.value_changed)
        minus, plus = row.findChildren(QPushButton)
        plus.click()
        minus.click()
        minus.click()
        self.assertEqual(received, [(110,), (100,), (90,)])
        labels = [l.text() for l in row.findChildren(QLabel)]
        self.assertIn("0.90", labels)

    def test_material_combo_emits_the_material(self):
        combo = self.make(MaterialComboBox)
        self.assertEqual(combo.material(), "light")
        received = record(combo.material_changed)
        combo.setCurrentIndex(0)
        self.assertEqual((received, combo.material()), ([("dark",)], "dark"))

    def test_resolution_box_signals_and_pages(self):
        box = self.make(ResolutionBox)
        self.assertEqual(box.stack.currentIndex(), 2)  # focale au départ
        mode, dpi = record(box.mode_changed), record(box.dpi_changed)
        box.mode_combo.setCurrentIndex(1)
        box.dpi_spin.setValue(300.0)
        self.assertEqual((mode, dpi), ([(1,)], [(300.0,)]))
        self.assertFalse(box.quality_label.isVisibleTo(box))  # vide : masqué


if __name__ == "__main__":
    unittest.main()
