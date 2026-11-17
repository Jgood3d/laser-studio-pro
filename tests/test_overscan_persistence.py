"""Surbalayage, décalage et homing mémorisés dans le profil machine
(GrblConfig.mechanical_values / profile_values / apply_profile)."""

import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtWidgets import QApplication, QComboBox
    from laser_studio.controllers.machine_profiles import MachineProfilesController, ProfileFields
    from laser_studio.models.grbl import GrblConfig
    from laser_studio.ui.settings.grbl_config import GrblConfigPage
except ImportError:  # PyQt6 manquant
    GrblConfig = None


@unittest.skipIf(GrblConfig is None, "PyQt6 non importable ici")
class OverscanPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def controller(self, grbl, profiles, index=0):
        combo = QComboBox()
        self.addCleanup(combo.deleteLater)
        noop = lambda *a: None  # noqa: E731
        c = MachineProfilesController(
            None, combo,
            ProfileFields(capture=dict, apply=noop, apply_layers=noop,
                          memory=grbl.mechanical_values, profile_selected=noop,
                          link_layers_to_focal=noop),
            save_settings=noop)
        c.profiles = profiles
        c.refresh_combo()
        combo.setCurrentIndex(index)
        return c

    def test_value_survives_a_restart(self):
        a = GrblConfig()        # valeurs par défaut : activé, distance fixe, 2,5 mm, 5 %
        a.update(overscan_enabled=False, overscan_mode=1, overscan_dist_mm=6.0, overscan_pct=8.5)
        c = self.controller(a, [{"name": "Phecda"}])
        c.store_memory()  # appelé à la fermeture (save_machine_settings)
        saved = json.loads(c.to_json())  # aller-retour disque

        b = GrblConfig()  # nouveau démarrage : valeurs par défaut
        b.apply_profile(saved[0])
        self.assertEqual((b.overscan_enabled, b.overscan_mode, b.overscan_dist_mm, b.overscan_pct),
                         (False, 1, 6.0, 8.5))

    def test_each_machine_keeps_its_own_value(self):
        grbl = GrblConfig()
        c = self.controller(grbl, [{"name": "A"}, {"name": "B"}], index=1)
        grbl.update(overscan_dist_mm=7.0)
        c.store_memory()
        self.assertNotIn("overscan_dist_mm", c.profiles[0])
        self.assertEqual(c.profiles[1]["overscan_dist_mm"], 7.0)

    def test_old_profile_without_overscan_keeps_current_values(self):
        grbl = GrblConfig()
        grbl.update(overscan_dist_mm=4.0, scan_offset_mm=0.3)
        grbl.apply_profile({"name": "Ancien", "w": 400})
        self.assertEqual((grbl.overscan_enabled, grbl.overscan_mode, grbl.overscan_dist_mm),
                         (True, 0, 4.0))
        self.assertEqual(grbl.scan_offset_mm, 0.0)      # décalage absent : revient à 0

    def test_unreadable_values_are_ignored(self):
        grbl = GrblConfig()
        grbl.apply_profile({"overscan_mode": 7, "overscan_dist_mm": "abc", "scan_offset_mm": "x"})
        self.assertEqual((grbl.overscan_mode, grbl.overscan_dist_mm, grbl.scan_offset_mm), (0, 2.5, 0.0))

    def test_profile_update_captures_overscan(self):
        grbl = GrblConfig()
        grbl.update(overscan_dist_mm=3.2)
        values = grbl.profile_values()
        for key, value in {"overscan_enabled": True, "overscan_mode": 0,
                           "overscan_dist_mm": 3.2, "overscan_pct": 5.0}.items():
            self.assertEqual(values[key], value, key)
        self.assertNotIn("smax", values)                 # pas un réglage du profil
        with open(os.path.join(ROOT, "main_window.py"), encoding="utf-8") as f:
            src = f.read()
        capture = src[src.index("def _capture_machine_profile"):src.index("def _apply_machine_profile")]
        self.assertIn("**self.grbl.profile_values()", capture)  # « Mettre à jour le profil »
        apply = src[src.index("def _apply_machine_profile"):src.index("def _machine_memory")]
        self.assertIn("self.grbl.apply_profile(profile)", apply)  # changement, démarrage

    def test_homing_choice_survives_a_restart(self):
        """« Inclure $H » décoché (graveur sans homing) : décoché au prochain
        démarrage, et le décochage déclenche la mémorisation du profil."""
        page = GrblConfigPage()
        self.addCleanup(page.deleteLater)
        changes = []
        page.homing_changed.connect(changes.append)
        page.homing_check.setChecked(False)
        self.assertEqual(changes, [False])
        a = GrblConfig()
        a.update(homing_enabled=False)
        c = self.controller(a, [{"name": "Phecda"}])
        c.store_memory()
        saved = json.loads(c.to_json())
        b = GrblConfig()                                # case cochée par défaut
        b.apply_profile(saved[0])
        self.assertFalse(b.homing_enabled)
        b.apply_profile({"name": "Ancien"})             # profil sans la clé : inchangé
        self.assertFalse(b.homing_enabled)
        with open(os.path.join(ROOT, "main_window.py"), encoding="utf-8") as f:
            self.assertIn("page.homing_changed.connect(self.machines.schedule_persist)", f.read())


if __name__ == "__main__":
    unittest.main()
