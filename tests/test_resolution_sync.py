"""La résolution de gravure (lignes/mm, DPI ou focale) reste cohérente entre les
champs de « Graver une image » (ResolutionBox), et l'onglet Séparation affiche
toujours la même."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.separation import SeparationController
    from laser_studio.models.image_settings import ImageSettings
    from laser_studio.models.separation import SeparationSettings
    from laser_studio.ui.tabs.image.resolution_box import (
        RESOLUTION_DPI, RESOLUTION_FOCAL, RESOLUTION_LMM, ResolutionBox,
    )
    from job_fakes import FakeDialogs
except ImportError:
    ResolutionBox = None


def record(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


@unittest.skipIf(ResolutionBox is None, "PyQt6 non importable ici")
class ResolutionBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, focal=0.13, mode=RESOLUTION_LMM):
        box = ResolutionBox()
        self.addCleanup(box.deleteLater)
        box.set_focal(focal)
        box.mode_combo.blockSignals(True)
        box.mode_combo.setCurrentIndex(mode)
        box.mode_combo.blockSignals(False)
        self.lmm_signals = record(box.lines_per_mm_spin.valueChanged)
        self.changes = record(box.resolution_changed)
        return box

    def test_dpi_mode_sets_the_lines_per_mm_silently(self):
        box = self.make(mode=RESOLUTION_DPI)
        box.dpi_spin.setValue(195)
        self.assertAlmostEqual(box.lines_per_mm(), 195 / 25.4, places=2)
        self.assertEqual(self.lmm_signals, [])                 # champ lignes/mm modifié sans signal…
        self.assertEqual(len(self.changes), 1)                 # … mais la résolution est annoncée

    def test_focal_mode_follows_the_spot(self):
        box = self.make()
        box.apply_focal()
        self.assertAlmostEqual(box.lines_per_mm(), 1 / 0.13, places=2)
        self.assertEqual(int(box.dpi_spin.value()), round(1 / 0.13 * 25.4))   # 195 DPI pour 0,13 mm
        self.assertIn("0.13", box.focal_info_label.text())
        self.assertEqual(self.changes, [(box.lines_per_mm(),)])

    def test_lines_per_mm_mode_updates_the_dpi(self):
        box = self.make()
        box.lines_per_mm_spin.setValue(7.68)
        self.assertEqual(int(box.dpi_spin.value()), round(7.68 * 25.4))
        self.assertEqual(self.changes, [(7.68,)])

    def test_startup_restoration_path(self):
        """Au démarrage, la résolution est restaurée (signaux bloqués) puis refresh() recalcule tout."""
        for mode, prepare in ((RESOLUTION_LMM, lambda b: b.lines_per_mm_spin.setValue(7.68)),
                              (RESOLUTION_DPI, lambda b: b.dpi_spin.setValue(195.0)),
                              (RESOLUTION_FOCAL, lambda b: None)):
            box = self.make(mode=mode)
            for spin in (box.lines_per_mm_spin, box.dpi_spin):
                spin.blockSignals(True)
            prepare(box)
            for spin in (box.lines_per_mm_spin, box.dpi_spin):
                spin.blockSignals(False)
            box.refresh()
            self.assertEqual(box.stack.currentIndex(), mode)
            self.assertEqual(int(box.dpi_spin.value()), round(box.lines_per_mm() * 25.4), f"mode {mode}")
            self.assertEqual(self.changes[-1], (box.lines_per_mm(),), f"mode {mode}")

    def test_too_fine_lines_are_reported(self):
        box = self.make(focal=0.2)
        box.lines_per_mm_spin.setValue(20.0)                   # 0,05 mm entre les lignes pour un spot de 0,2 mm
        self.assertNotEqual(box.quality_label.text(), "")
        box.lines_per_mm_spin.setValue(3.0)                    # écart confortable : rien à signaler
        self.assertEqual(box.quality_label.text(), "")

    def test_without_focal_nothing_is_reported(self):
        box = self.make(focal=None)
        box.lines_per_mm_spin.setValue(40.0)
        self.assertEqual(box.quality_label.text(), "")
        box.apply_focal()                                      # focale inconnue : 0,1 mm
        self.assertAlmostEqual(box.lines_per_mm(), 10.0)


@unittest.skipIf(ResolutionBox is None, "PyQt6 non importable ici")
class SeparationFollowsTheResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, image_loaded):
        self.lmm = 10.0
        c = SeparationController(SeparationSettings(), ImageSettings(), frame_args=lambda: (0, 1.0, 0.5, 0.5),
                                 engrave_lmm=lambda: self.lmm, dialogs=FakeDialogs())
        c.source = object() if image_loaded else None
        self.pushes = 0
        # Tonalité renvoyée : compte les démarrages du minuteur d'envoi.
        c._push_timer = type("T", (), {"start": lambda _t: setattr(self, "pushes", self.pushes + 1),
                                       "stop": lambda _t: None})()
        self.dpi = record(c.engrave_dpi_changed)
        return c

    def test_label_follows_the_engraving_resolution(self):
        c = self.make(image_loaded=False)
        self.lmm = 195 / 25.4
        c.resolution_changed()
        self.assertEqual(self.dpi, [(195,)])

    def test_tone_is_resent_only_when_a_separation_image_is_loaded(self):
        self.make(image_loaded=False).resolution_changed()
        self.assertEqual(self.pushes, 0)
        self.make(image_loaded=True).resolution_changed()
        self.assertEqual(self.pushes, 1)


class SeparationHooksStillPresentTests(unittest.TestCase):
    """Garde-fou : les liaisons « Graver une image » <-> Séparation ne doivent pas disparaître
    quand ui/app/main_window.py ou window_controller.py est remplacé par une autre version."""

    def source(self, *parts):
        with open(os.path.join(REPO, "src", "laser_studio", *parts), encoding="utf-8") as f:
            return f.read()

    def test_load_image_releases_the_separation_settings(self):
        self.assertIn("image.loading_file.connect(separation.release_glass_settings)",
                      self.source("ui", "tabs", "separation", "builder.py"))

    def test_reset_forgets_the_separation_state(self):
        self.assertIn("image.resetting.connect(separation.forget_glass_settings)",
                      self.source("ui", "tabs", "separation", "builder.py"))

    def test_resolution_reaches_the_separation(self):
        self.assertIn("separation.resolution_changed()", self.source("ui", "app", "window_controller.py"))
