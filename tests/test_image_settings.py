"""Réglages de tramage (models/image_settings.py), leur annulation, leur liaison
aux champs de l'onglet, et les calculs de résolution (image/resolution.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from laser_studio.image.resolution import (  # noqa: E402
    dpi_to_lmm, focal_to_lmm, lmm_to_dpi, resolution_quality,
)

try:
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QSlider
    from laser_studio.models.image_settings import ImageSettings, ImageSettingsHistory
    from laser_studio.ui.binding import bind
except ImportError:  # PyQt6 manquant
    ImageSettings = None


class ResolutionTests(unittest.TestCase):
    def test_conversions(self):
        self.assertAlmostEqual(dpi_to_lmm(254), 10.0)
        self.assertAlmostEqual(lmm_to_dpi(10), 254.0)
        self.assertAlmostEqual(focal_to_lmm(0.08), 12.5)
        self.assertAlmostEqual(focal_to_lmm(0), 10.0)            # spot non réglé : 0,1 mm

    def test_quality_levels(self):
        cases = {50: "image.quality_too_fine", 12: "image.quality_fine", 10: "image.quality_fine_ok",
                 5: "image.quality_recommended", 1 / 0.225: "image.quality_recommended",
                 2: "image.quality_coarse"}
        for lmm, key in cases.items():
            self.assertEqual(resolution_quality(0.1, lmm)[2], key, lmm)
        self.assertIsNone(resolution_quality(0, 10))


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@unittest.skipIf(ImageSettings is None, "PyQt6 non importable ici")
class ImageSettingsTests(unittest.TestCase):
    def test_choosing_a_material_sets_the_negative(self):
        s = ImageSettings()
        s.choose_material("dark")
        self.assertEqual((s.material_bg, s.invert), ("dark", True))
        s.update(invert=False)                    # la case reste modifiable à part
        s.choose_material("light")
        self.assertEqual((s.material_bg, s.invert), ("light", False))
        s.update(material_bg="bois")              # valeur inconnue : ignorée
        self.assertEqual(s.material_bg, "light")

    def test_project_round_trip_and_old_projects(self):
        s = ImageSettings()
        s.update(brightness=10, gamma=150, mirror_h=True, algorithm="Atkinson", material_bg="dark")
        data = s.to_project()
        self.assertEqual((data["bright"], data["gamma"], data["algo"]), (10, 150, "Atkinson"))
        other = ImageSettings()
        other.load_project(data)
        self.assertEqual(other.to_dict(), s.to_dict())
        other.load_project({"invert": True})      # ancien projet : matière déduite du négatif
        self.assertEqual((other.material_bg, other.brightness, other.algorithm),
                         ("dark", 0, "Floyd-Steinberg"))

    def test_reset_keeps_the_algorithm(self):
        s = ImageSettings()
        s.update(contrast=30, invert=True, algorithm="Stucki")
        s.reset()
        self.assertEqual((s.contrast, s.invert, s.algorithm), (0, False, "Stucki"))


@unittest.skipIf(ImageSettings is None, "PyQt6 non importable ici")
class HistoryTests(unittest.TestCase):
    def make(self):
        self.clock = _Clock()
        s = ImageSettings()
        return s, ImageSettingsHistory(s, clock=self.clock)

    def test_undo_and_redo(self):
        s, h = self.make()
        s.update(brightness=20)
        self.clock.now = 1.0
        s.update(contrast=-10)
        self.assertTrue(h.undo())
        self.assertEqual((s.brightness, s.contrast), (20, 0))
        self.assertTrue(h.undo())
        self.assertEqual(s.brightness, 0)
        self.assertFalse(h.undo())
        self.assertTrue(h.redo())
        self.assertEqual(s.brightness, 20)

    def test_close_changes_form_a_single_step(self):
        s, h = self.make()
        for i, value in enumerate(range(5, 50, 5)):    # glissement d'un curseur
            self.clock.now = i * 0.1
            s.update(brightness=value)
        h.undo()
        self.assertEqual(s.brightness, 0)
        self.assertFalse(h.can_undo())

    def test_a_new_change_clears_redo(self):
        s, h = self.make()
        s.update(brightness=20)
        h.undo()
        self.clock.now = 5.0
        s.update(gamma=120)
        self.assertFalse(h.can_redo())

    def test_history_is_limited(self):
        s, h = self.make()
        for i in range(40):
            self.clock.now = float(i)
            s.update(brightness=i + 1)
        steps = 0
        while h.undo():
            steps += 1
        self.assertEqual(steps, ImageSettingsHistory.MAX_STEPS)


@unittest.skipIf(ImageSettings is None, "PyQt6 non importable ici")
class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_slider_checkbox_action_and_combo_follow_the_model(self):
        s = ImageSettings()
        slider = QSlider()
        slider.setRange(-100, 100)
        check, action, combo = QCheckBox(), QAction(None), QComboBox()
        action.setCheckable(True)
        combo.addItems(["Floyd-Steinberg", "Atkinson"])
        bind(slider, s, "brightness")
        bind(check, s, "invert")
        bind(action, s, "mirror_h")
        bind(combo, s, "algorithm", to_widget=combo.findText, from_widget=combo.itemText)
        s.update(brightness=-30, invert=True, mirror_h=True, algorithm="Atkinson")
        self.assertEqual((slider.value(), check.isChecked(), action.isChecked(), combo.currentText()),
                         (-30, True, True, "Atkinson"))
        slider.setValue(15)
        action.setChecked(False)
        combo.setCurrentIndex(0)
        self.assertEqual((s.brightness, s.mirror_h, s.algorithm), (15, False, "Floyd-Steinberg"))


if __name__ == "__main__":
    unittest.main()
