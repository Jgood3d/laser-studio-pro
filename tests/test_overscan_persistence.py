"""Surbalayage et décalage mémorisés dans le profil machine
(GrblConfigPage.mechanical_values / apply_profile_values)."""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtWidgets import QApplication, QComboBox
    from controllers.machine_profiles import MachineProfilesController, ProfileFields
    from ui.settings.grbl_config import GrblConfigPage
except ImportError:  # PyQt6 manquant
    GrblConfigPage = None


@unittest.skipIf(GrblConfigPage is None, "PyQt6 non importable ici")
class OverscanPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def page(self):
        page = GrblConfigPage()  # valeurs par défaut : activé, distance fixe, 2,5 mm, 5 %
        self.addCleanup(page.deleteLater)
        return page

    def controller(self, page, profiles, index=0):
        combo = QComboBox()
        self.addCleanup(combo.deleteLater)
        noop = lambda *a: None  # noqa: E731
        c = MachineProfilesController(
            None, combo,
            ProfileFields(capture=dict, apply=noop, apply_layers=noop,
                          memory=page.mechanical_values, profile_selected=noop,
                          link_layers_to_focal=noop),
            save_settings=noop)
        c.profiles = profiles
        c.refresh_combo()
        combo.setCurrentIndex(index)
        return c

    def test_value_survives_a_restart(self):
        a = self.page()
        a.overscan_check.setChecked(False)
        a.overscan_mode_combo.setCurrentIndex(1)
        a.overscan_dist_spin.setValue(6.0)
        a.overscan_pct_spin.setValue(8.5)
        c = self.controller(a, [{"name": "Phecda"}])
        c.store_memory()  # appelé à la fermeture (save_machine_settings)
        saved = json.loads(c.to_json())  # aller-retour disque

        b = self.page()  # nouveau démarrage : valeurs par défaut
        b.apply_profile_values(saved[0])
        self.assertEqual((b.overscan_check.isChecked(), b.overscan_mode_combo.currentIndex(),
                          b.overscan_dist_spin.value(), b.overscan_pct_spin.value()),
                         (False, 1, 6.0, 8.5))

    def test_each_machine_keeps_its_own_value(self):
        page = self.page()
        c = self.controller(page, [{"name": "A"}, {"name": "B"}], index=1)
        page.overscan_dist_spin.setValue(7.0)
        c.store_memory()
        self.assertNotIn("overscan_dist_mm", c.profiles[0])
        self.assertEqual(c.profiles[1]["overscan_dist_mm"], 7.0)

    def test_old_profile_without_overscan_keeps_current_values(self):
        page = self.page()
        page.overscan_dist_spin.setValue(4.0)
        page.apply_profile_values({"name": "Ancien", "w": 400})
        self.assertEqual((page.overscan_check.isChecked(), page.overscan_mode_combo.currentIndex(),
                          page.overscan_dist_spin.value()), (True, 0, 4.0))

    def test_unreadable_values_are_ignored(self):
        page = self.page()
        page.apply_profile_values({"overscan_mode": 7, "overscan_dist_mm": "abc"})
        self.assertEqual((page.overscan_mode_combo.currentIndex(), page.overscan_dist_spin.value()),
                         (0, 2.5))

    def test_profile_update_captures_overscan(self):
        page = self.page()
        page.overscan_dist_spin.setValue(3.2)
        values = page.profile_values()
        for key, value in {"overscan_enabled": True, "overscan_mode": 0,
                           "overscan_dist_mm": 3.2, "overscan_pct": 5.0}.items():
            self.assertEqual(values[key], value, key)
        with open(os.path.join(ROOT, "main_window.py"), encoding="utf-8") as f:
            src = f.read()
        capture = src[src.index("def _capture_machine_profile"):src.index("def _apply_machine_profile")]
        self.assertIn("**self.tab_grbl_config.profile_values()", capture)  # « Mettre à jour le profil »
        apply = src[src.index("def _apply_machine_profile"):src.index("def _machine_memory")]
        self.assertIn("self.tab_grbl_config.apply_profile_values(profile)", apply)  # changement, démarrage


if __name__ == "__main__":
    unittest.main()
