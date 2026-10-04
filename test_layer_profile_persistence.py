"""Tests de la mémorisation des réglages des calques (vitesse, puissance,
passes...) dans le profil de la machine active.

Lancer depuis le dossier du projet :  python -m unittest discover tests -v
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import machine_profiles_mixin as mpm
    from machine_profiles_mixin import MachineProfilesMixin
    from vector_layers import LayerManager
except ImportError:  # PyQt6... manquant
    MachineProfilesMixin = None


class _Combo:
    def __init__(self, index=0):
        self.index = index

    def currentIndex(self):
        return self.index

    def currentText(self):
        return "Bas-Gauche (0,0)"


class _Val:
    def __init__(self, v):
        self.v = v

    def value(self):
        return self.v


class _Widget:
    """Faux LayerManagerWidget : compte les appels."""
    def __init__(self):
        self.refreshed = 0
        self.linked = 0

    def refresh(self):
        self.refreshed += 1

    def link_all_to_focal(self):
        self.linked += 1


class _FakeTimer:
    instances = []

    def __init__(self):
        self.started = 0
        self.interval = None
        self.single = False
        self.timeout = mock.MagicMock()
        _FakeTimer.instances.append(self)

    def setSingleShot(self, v):
        self.single = v

    def setInterval(self, v):
        self.interval = v

    def start(self):
        self.started += 1


def _make_app(profile_index=0, profiles=None):
    class App(MachineProfilesMixin):
        pass
    a = App()
    a.layer_manager = LayerManager()
    a.layer_widget = _Widget()
    a.combo_machine_profile = _Combo(profile_index)
    a.machine_profiles = profiles if profiles is not None else [{"name": "M1", "w": 400, "h": 400}]
    return a


@unittest.skipIf(MachineProfilesMixin is None, "machine_profiles_mixin non importable ici")
class LayerProfileTests(unittest.TestCase):
    def test_store_puts_layers_in_active_profile_only(self):
        a = _make_app(profile_index=1, profiles=[{"name": "A"}, {"name": "B"}])
        a.layer_manager.layers[0].power = 55.0
        a._store_layers_in_active_profile()
        self.assertNotIn("layers", a.machine_profiles[0])
        self.assertEqual(a.machine_profiles[1]["layers"], a.layer_manager.to_list())

    def test_startup_restores_layers_completely(self):
        a = _make_app()
        a.layer_manager.layers[0].power = 55.0
        a.layer_manager.layers[0].speed = 1234
        a.layer_manager.layers[0].name = "Mon calque"
        extra = a.layer_manager.add_layer()
        extra.passes = 4
        a._store_layers_in_active_profile()
        saved = json.loads(json.dumps(a.machine_profiles))   # aller-retour disque (QSettings en JSON)

        b = _make_app(profiles=saved)                          # nouveau démarrage : calques par défaut
        b._apply_profile_layers(saved[0]["layers"], full=True)
        self.assertEqual([l.id for l in b.layer_manager.layers], [l.id for l in a.layer_manager.layers])
        self.assertEqual(b.layer_manager.layers[0].name, "Mon calque")
        self.assertEqual(b.layer_manager.layers[0].power, 55.0)
        self.assertEqual(b.layer_manager.layers[0].speed, 1234)
        self.assertEqual(len(b.layer_manager.layers), 3)
        self.assertEqual(b.layer_manager.layers[2].passes, 4)
        self.assertGreaterEqual(b.layer_widget.refreshed, 1)
        self.assertGreaterEqual(b.layer_widget.linked, 1)

    def test_switching_machine_only_updates_settings_by_id(self):
        a = _make_app()
        ids = [l.id for l in a.layer_manager.layers]
        names = [l.name for l in a.layer_manager.layers]
        other = [dict(l.to_dict(), power=11.0, speed=999, passes=7, enabled=False) for l in a.layer_manager.layers]
        other[0]["name"] = "Nom de l'autre machine"
        other[0]["color"] = "#000000"
        a._apply_profile_layers(other, full=False)
        self.assertEqual([l.id for l in a.layer_manager.layers], ids)          # identité conservée
        self.assertEqual([l.name for l in a.layer_manager.layers], names)      # nom conservé
        for l in a.layer_manager.layers:
            self.assertEqual((l.power, l.speed, l.passes, l.enabled), (11.0, 999, 7, False))

    def test_switching_machine_falls_back_to_position(self):
        a = _make_app()
        other = [{"id": "zzz1", "power": 20.0, "speed": 3000}, {"id": "zzz2", "power": 70.0, "speed": 400}]
        a._apply_profile_layers(other, full=False)
        self.assertEqual((a.layer_manager.layers[0].power, a.layer_manager.layers[0].speed), (20.0, 3000))
        self.assertEqual((a.layer_manager.layers[1].power, a.layer_manager.layers[1].speed), (70.0, 400))

    def test_switching_never_adds_or_removes_layers(self):
        a = _make_app()
        n = len(a.layer_manager.layers)
        a._apply_profile_layers([{"power": 1.0}], full=False)                      # moins de calques
        self.assertEqual(len(a.layer_manager.layers), n)
        a._apply_profile_layers([{"power": 2.0}] * (n + 3), full=False)            # plus de calques
        self.assertEqual(len(a.layer_manager.layers), n)

    def test_profile_without_layers_changes_nothing(self):
        a = _make_app()
        before = a.layer_manager.to_list()
        for saved in (None, [], "oups", [None, 3]):
            a._apply_profile_layers(saved, full=True)
            a._apply_profile_layers(saved, full=False)
        self.assertEqual(a.layer_manager.to_list(), before)

    def test_corrupted_values_do_not_crash(self):
        a = _make_app()
        a._apply_profile_layers([{"id": a.layer_manager.layers[0].id, "power": "abc", "speed": None, "passes": 3}], full=False)
        l = a.layer_manager.layers[0]
        self.assertEqual(l.passes, 3)                       # la valeur valide est reprise
        self.assertIsInstance(l.power, float)               # la valeur corrompue est ignorée
        self.assertIsInstance(l.speed, int)
        a._apply_profile_layers([{"power": "abc", "speed": "x", "passes": [], "enabled": 0, "mode": "Inconnu"}], full=True)
        for l in a.layer_manager.layers:
            self.assertIsInstance(l.power, float)
            self.assertIsInstance(l.speed, int)
            self.assertIsInstance(l.passes, int)
            self.assertEqual(l.mode, "Découpe")             # mode inconnu -> valeur par défaut
            self.assertFalse(l.enabled)                      # valeur valide reprise

    def test_capture_includes_layers(self):
        a = _make_app()
        a.spin_machine_w, a.spin_machine_h = _Val(400.0), _Val(400.0)
        a.spin_machine_max_speed, a.spin_machine_accel = _Val(6000.0), _Val(500.0)
        a.layer_manager.layers[1].speed = 777
        fields = a._capture_machine_profile_fields()
        self.assertEqual(fields["layers"], a.layer_manager.to_list())
        self.assertEqual(fields["layers"][1]["speed"], 777)

    def test_schedule_persist_waits_until_ready_and_debounces(self):
        a = _make_app()
        _FakeTimer.instances.clear()
        with mock.patch.object(mpm, "QTimer", _FakeTimer):
            a._schedule_layer_persist()                       # pas encore prêt : ignoré
            self.assertEqual(_FakeTimer.instances, [])
            a._layers_persist_ready = True
            a._schedule_layer_persist()
            a._schedule_layer_persist()
        self.assertEqual(len(_FakeTimer.instances), 1)        # un seul minuteur réutilisé
        self.assertEqual(a.machine_profiles[0]["layers"], a.layer_manager.to_list())  # rangé tout de suite
        t = _FakeTimer.instances[0]
        self.assertEqual(t.started, 2)
        self.assertTrue(t.single)
        t.timeout.connect.assert_called_once_with(a.save_machine_settings)


if __name__ == "__main__":
    unittest.main()
