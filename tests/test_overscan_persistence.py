"""Surbalayage mémorisé dans le profil machine (voir MachineProfilesMixin._capture_overscan_fields)."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from machine_profiles_mixin import MachineProfilesMixin
    from vector_layers import LayerManager
except ImportError:  # PyQt6 manquant
    MachineProfilesMixin = None


class _Check:
    def __init__(self, checked):
        self.checked = checked

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        self.checked = value


class _Combo:
    def __init__(self, index):
        self.index = index

    def currentIndex(self):
        return self.index

    def setCurrentIndex(self, index):
        self.index = index


class _Spin:
    def __init__(self, value):
        self.v = value

    def value(self):
        return self.v

    def setValue(self, value):
        self.v = value


def _make_app(profiles):
    class App(MachineProfilesMixin):
        pass
    a = App()
    a.layer_manager = LayerManager()
    a.combo_machine_profile = _Combo(0)
    a.machine_profiles = profiles
    # Valeurs par défaut de l'interface (ui_setup_mixin) : activé, distance fixe, 2,5 mm, 5 %.
    a.chk_overscan = _Check(True)
    a.combo_overscan_mode = _Combo(0)
    a.spin_overscan_dist = _Spin(2.5)
    a.spin_overscan_pct = _Spin(5.0)
    return a


@unittest.skipIf(MachineProfilesMixin is None, "machine_profiles_mixin non importable ici")
class OverscanPersistenceTests(unittest.TestCase):
    def test_value_survives_a_restart(self):
        a = _make_app([{"name": "Phecda"}])
        a.chk_overscan.checked = False
        a.combo_overscan_mode.index = 1
        a.spin_overscan_dist.v = 6.0
        a.spin_overscan_pct.v = 8.5
        a._store_layers_in_active_profile()                    # appelé à la fermeture (save_machine_settings)
        saved = json.loads(json.dumps(a.machine_profiles))     # aller-retour disque (QSettings en JSON)

        b = _make_app(saved)                                   # nouveau démarrage : valeurs par défaut
        b._apply_overscan_fields(saved[0])
        self.assertEqual((b.chk_overscan.checked, b.combo_overscan_mode.index,
                          b.spin_overscan_dist.v, b.spin_overscan_pct.v), (False, 1, 6.0, 8.5))

    def test_each_machine_keeps_its_own_value(self):
        a = _make_app([{"name": "A"}, {"name": "B"}])
        a.combo_machine_profile.index = 1
        a.spin_overscan_dist.v = 7.0
        a._store_layers_in_active_profile()
        self.assertNotIn("overscan_dist_mm", a.machine_profiles[0])
        self.assertEqual(a.machine_profiles[1]["overscan_dist_mm"], 7.0)

    def test_old_profile_without_overscan_keeps_current_values(self):
        a = _make_app([{"name": "Ancien"}])
        a.spin_overscan_dist.v = 4.0
        a._apply_overscan_fields({"name": "Ancien", "w": 400})
        self.assertEqual((a.chk_overscan.checked, a.combo_overscan_mode.index, a.spin_overscan_dist.v),
                         (True, 0, 4.0))

    def test_unreadable_values_are_ignored(self):
        a = _make_app([{"name": "M"}])
        a._apply_overscan_fields({"overscan_mode": 7, "overscan_dist_mm": "abc"})
        self.assertEqual((a.combo_overscan_mode.index, a.spin_overscan_dist.v), (0, 2.5))

    def test_profile_update_captures_overscan(self):
        a = _make_app([{"name": "M"}])
        a.spin_overscan_dist.v = 3.2
        fields = a._capture_overscan_fields()
        self.assertEqual(fields, {"overscan_enabled": True, "overscan_mode": 0,
                                  "overscan_dist_mm": 3.2, "overscan_pct": 5.0})
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "machine_profiles_mixin.py"), encoding="utf-8").read()
        capture = src[src.index("def _capture_machine_profile_fields"):src.index("def _apply_machine_profile_fields")]
        self.assertIn("**self._capture_overscan_fields()", capture)     # « Mettre à jour le profil »
        widgets = src[src.index("def _apply_machine_profile_widgets"):src.index("def _on_machine_profile_selected")]
        self.assertIn("self._apply_overscan_fields(p)", widgets)          # changement de profil, démarrage


if __name__ == "__main__":
    unittest.main()
