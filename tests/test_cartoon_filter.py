"""Effet bande dessinée (image/filters.cartoon_filter), dans le traitement de l'image et ses réglages."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PIL import Image
    from laser_studio.image.dithering import comparison_thumbnails, process_image
    from laser_studio.image.filters import cartoon_filter, cartoon_radius_px
except ImportError:  # numpy, scipy ou Pillow manquant
    cartoon_filter = None


def line_image():
    arr = np.full((120, 120), 200, np.float32)
    arr[55:65, :] = 70                               # un trait sombre horizontal
    return arr


@unittest.skipIf(cartoon_filter is None, "scipy / Pillow non importables ici")
class CartoonFilterTests(unittest.TestCase):
    def test_no_effect_without_radius_or_black(self):
        arr = line_image()
        for radius, black in ((0, 20), (8, 0)):
            np.testing.assert_array_equal(cartoon_filter(arr, radius, black), arr)

    def test_flat_areas_are_kept_and_the_line_turns_black(self):
        out = cartoon_filter(line_image(), 8, 20)
        self.assertEqual(out[10, 60], 200)                                   # fond loin du trait
        self.assertLess(out[56, 60], 10)                                     # trait noirci
        self.assertEqual(line_image()[56, 60], 70)                           # entrée intacte

    def test_more_black_with_a_higher_percentage(self):
        photo = np.random.default_rng(1).uniform(0, 255, (150, 150)).astype(np.float32)
        dark = [float((cartoon_filter(photo, 6, k) < 5).mean()) for k in (5, 20, 50)]
        self.assertEqual(dark, sorted(dark))
        self.assertLess(dark[0], dark[2])

    def test_radius_follows_the_engraving_resolution(self):
        self.assertEqual(cartoon_radius_px(1.5, 10), 15.0)
        self.assertEqual(cartoon_radius_px(-1, 10), 0.0)


@unittest.skipIf(cartoon_filter is None, "scipy / Pillow non importables ici")
class CartoonInProcessingTests(unittest.TestCase):
    PARAMS = dict(w_mm=20, h_mm=20, lmm=6, mirror_h=False, mirror_v=False, bright=0, contrast=0, gamma=100,
                  sharp=0, invert=False, algo="Niveaux de Gris")

    def image(self):
        return Image.fromarray(np.clip(line_image(), 0, 255).astype(np.uint8))

    def test_off_by_default_and_applied_when_set(self):
        plain, _ = process_image(self.image(), self.PARAMS)
        same, _ = process_image(self.image(), dict(self.PARAMS, cartoon_r=0, cartoon_k=50))
        np.testing.assert_array_equal(plain, same)
        comic, _ = process_image(self.image(), dict(self.PARAMS, cartoon_r=20, cartoon_k=20))
        self.assertLess(int(comic.min()), int(plain.min()))

    def test_thumbnails_apply_it_too(self):
        plain = dict(comparison_thumbnails(self.image(), 0, 0, 100, 0, False))
        comic = dict(comparison_thumbnails(self.image(), 0, 0, 100, 0, False, cartoon=(20, 20, 20.0)))
        self.assertTrue(any((plain[k] != comic[k]).any() for k in plain))


class CartoonSettingsTests(unittest.TestCase):
    def test_saved_in_projects_and_old_projects_get_the_defaults(self):
        try:
            from laser_studio.models.image_settings import ImageSettings
        except ImportError:
            self.skipTest("PyQt6 non importable ici")
        settings = ImageSettings()
        settings.update(cartoon_radius=15, cartoon_black=35)
        data = settings.to_project()
        self.assertEqual((data["cartoon_r"], data["cartoon_k"]), (15, 35))
        self.assertEqual(settings.processing_params()["cartoon_r"], 15)
        settings.load_project({"bright": 0})
        self.assertEqual((settings.cartoon_radius, settings.cartoon_black), (0, 20))



class CartoonDialogTests(unittest.TestCase):
    """Liste « Appliquer un filtre » et fenêtre « Effet BD » : aperçu en direct, Annuler remet l'image."""

    @classmethod
    def setUpClass(cls):
        try:
            from PyQt6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PyQt6 non importable ici")
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from laser_studio.models.image_settings import ImageSettings
        self.settings = ImageSettings()
        self.changes = []
        self.settings.changed.connect(self.changes.append)

    def dialog(self):
        from laser_studio.ui.tabs.image.cartoon_dialog import DEFAULT_RADIUS, CartoonFilterDialog
        from PyQt6 import sip
        dialog = CartoonFilterDialog(self.settings)
        # Supprimée à la fermeture (WA_DeleteOnClose) : nettoyage seulement si elle existe encore.
        self.addCleanup(lambda: None if sip.isdeleted(dialog) else dialog.deleteLater())
        return dialog, DEFAULT_RADIUS

    def test_window_is_independent(self):
        from PyQt6.QtCore import Qt
        dialog, _default = self.dialog()
        self.assertFalse(dialog.isModal())            # une fenêtre modale serait accrochée à la principale (GNOME)
        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose))

    def test_opening_applies_the_effect_and_sliders_follow_live(self):
        dialog, default = self.dialog()
        self.assertEqual(self.settings.cartoon_radius, default)            # aperçu dès l'ouverture
        dialog.radius.slider.setValue(30)
        dialog.black.slider.setValue(45)
        self.assertEqual((self.settings.cartoon_radius, self.settings.cartoon_black), (30, 45))
        dialog.accept()
        self.assertEqual((self.settings.cartoon_radius, self.settings.cartoon_black), (30, 45))

    def test_cancel_restores_the_previous_settings(self):
        self.settings.update(cartoon_radius=12, cartoon_black=25)
        dialog, _default = self.dialog()
        dialog.radius.slider.setValue(40)
        dialog.reject()
        self.assertEqual((self.settings.cartoon_radius, self.settings.cartoon_black), (12, 25))

    def test_filter_list_follows_the_model_and_asks_on_user_choice(self):
        from laser_studio.ui.tabs.image.settings_panel import FILTER_CARTOON, FILTER_NONE, ImageSettingsPanel
        panel = ImageSettingsPanel()
        self.addCleanup(panel.deleteLater)
        panel.bind_settings(self.settings)
        asked = []
        panel.filter_requested.connect(asked.append)
        self.assertEqual(panel.filter_combo.currentData(), FILTER_NONE)
        self.settings.update(cartoon_radius=10)                            # projet ouvert, Ctrl+Z…
        self.assertEqual(panel.filter_combo.currentData(), FILTER_CARTOON)
        self.assertEqual(asked, [])                                        # pas une demande de l'utilisateur
        panel.filter_combo.activated.emit(panel.filter_combo.findData(FILTER_CARTOON))
        self.assertEqual(asked, [FILTER_CARTOON])


if __name__ == "__main__":
    unittest.main()
