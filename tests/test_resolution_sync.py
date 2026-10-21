"""La résolution de gravure affichée dans l'onglet Séparation doit toujours
correspondre à celle d'Image & Filtres (DPI, lignes/mm ou focale)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from image_processing_mixin import ImageProcessingMixin
    from separation_mixin import SeparationMixin
except ImportError:
    ImageProcessingMixin = None


class Spin:
    def __init__(self, value=0.0, lo=1.0, hi=50.0):
        self._v, self._lo, self._hi = value, lo, hi
        self.blocked = False
        self.signal_count = 0

    def value(self):
        return self._v

    def minimum(self):
        return self._lo

    def maximum(self):
        return self._hi

    def blockSignals(self, flag):
        self.blocked = flag

    def setValue(self, v):
        self._v = float(v)
        if not self.blocked:
            self.signal_count += 1


class Label:
    def __init__(self):
        self.text = ""

    def setText(self, t):
        self.text = t


class Stack:
    def setCurrentIndex(self, i):
        self.index = i


@unittest.skipIf(ImageProcessingMixin is None, "mixins non importables ici")
class ResolutionSyncTests(unittest.TestCase):
    def make(self, with_separation=True, image_loaded=False):
        class Fake(ImageProcessingMixin, SeparationMixin if with_separation else object):
            def update_image_processing(self, *a):
                pass

            def _sep_schedule_push(self):
                self.pushes += 1

        f = Fake.__new__(Fake)
        f.pushes = 0
        f.spin_lmm = Spin(10.0)                    # valeur par défaut, comme au démarrage
        f.spin_dpi = Spin(254.0, 10.0, 2000.0)
        f.spin_machine_focal = Spin(0.13, 0.01, 1.0)
        f.stack_lmm_input = Stack()
        f.lbl_focal_info = Label()
        if with_separation:
            f.sep_lbl_dpi = Label()
            f.sep_src = object() if image_loaded else None
            f._sep_update_dpi_label()              # libellé construit au démarrage : 254 DPI
        return f

    @staticmethod
    def shown_dpi(f):
        return int(f.sep_lbl_dpi.text.split(":")[1].split("DPI")[0])

    def test_label_starts_at_the_default(self):
        self.assertEqual(self.shown_dpi(self.make()), 254)

    def test_dpi_mode_updates_the_separation_label_even_with_signals_blocked(self):
        f = self.make()
        f.on_dpi_value_changed(195)
        self.assertTrue(f.spin_lmm.blocked is False)          # le champ lignes/mm a bien été modifié silencieusement
        self.assertEqual(f.spin_lmm.signal_count, 0)          # ... sans aucun signal
        self.assertEqual(self.shown_dpi(f), 195)

    def test_focal_mode_updates_the_label(self):
        f = self.make()
        f._apply_focal_to_lmm()
        self.assertAlmostEqual(f.spin_lmm.value(), 1 / 0.13, places=6)
        self.assertEqual(self.shown_dpi(f), round(1 / 0.13 * 25.4))      # 195 DPI pour une focale de 0,13 mm
        self.assertEqual(self.shown_dpi(f), int(f.spin_dpi.value()))     # même chiffre que le champ DPI d'Image & Filtres

    def test_lines_per_mm_mode_updates_the_label(self):
        f = self.make()
        f.spin_lmm.setValue(7.68)
        f._sync_dpi_and_quality_from_lmm(7.68)
        self.assertEqual(self.shown_dpi(f), round(7.68 * 25.4))

    def test_startup_restoration_path(self):
        """Au démarrage, la résolution est restaurée (signaux bloqués) puis on_lmm_mode_changed est appelée."""
        for mode, prepare in ((0, lambda f: f.spin_lmm.setValue(7.68)),
                              (1, lambda f: f.spin_dpi.setValue(195.0)),
                              (2, lambda f: None)):
            f = self.make()
            prepare(f)
            f.on_lmm_mode_changed(mode)
            self.assertEqual(self.shown_dpi(f), round(f.spin_lmm.value() * 25.4), f"mode {mode}")
            self.assertEqual(self.shown_dpi(f), int(f.spin_dpi.value()), f"mode {mode}")

    def test_tone_is_resent_only_when_a_separation_image_is_loaded(self):
        f = self.make(image_loaded=False)
        f.on_dpi_value_changed(300)
        self.assertEqual(f.pushes, 0)
        g = self.make(image_loaded=True)
        g.on_dpi_value_changed(300)
        self.assertEqual(g.pushes, 1)

    def test_without_separation_tab_nothing_breaks(self):
        f = self.make(with_separation=False)
        f.on_dpi_value_changed(195)
        f._apply_focal_to_lmm()
        f.on_lmm_mode_changed(0)


@unittest.skipIf(ImageProcessingMixin is None, "mixins non importables ici")
class SeparationHooksStillPresentTests(unittest.TestCase):
    """Garde-fou : les deux liaisons Image & Filtres <-> Séparation ne doivent pas disparaître
    quand image_processing_mixin.py est remplacé par une autre version."""

    def source(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "image_processing_mixin.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_load_image_releases_the_separation_settings(self):
        self.assertIn("self.separation_release_image_settings()", self.source())

    def test_reset_forgets_the_separation_state(self):
        self.assertIn("self._sep_glass_settings_active = False", self.source())
