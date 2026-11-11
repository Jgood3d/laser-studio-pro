"""Calques et profils machine : mémoire continue des calques dans le profil
actif, restauration au démarrage, changement de machine, actions sur les
profils (controllers/machine_profiles.py, controllers/layer_memory.py)."""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt6.QtWidgets import QApplication, QComboBox, QInputDialog, QMessageBox
    from controllers import machine_profiles as mp
    from controllers.layer_memory import apply_saved_layers
    from controllers.machine_profiles import MachineProfilesController, ProfileFields
    from vector_layers import LayerManager
except ImportError:  # PyQt6 manquant
    MachineProfilesController = None


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


@unittest.skipIf(MachineProfilesController is None, "PyQt6 non importable ici")
class LayerProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, profiles, index=0):
        self.manager = LayerManager()
        self.captured = {"w": 400.0}
        self.applied, self.linked, self.saved = [], [], []
        combo = QComboBox()
        self.addCleanup(combo.deleteLater)
        controller = MachineProfilesController(
            None,
            combo,
            ProfileFields(
                capture=lambda: dict(self.captured, layers=self.manager.to_list()),
                apply=self.applied.append,
                apply_layers=lambda saved, full: apply_saved_layers(self.manager, saved, full),
                memory=lambda: {"layers": self.manager.to_list()},
                profile_selected=lambda: None,
                link_layers_to_focal=lambda: self.linked.append(True),
            ),
            save_settings=lambda: self.saved.append(True),
        )
        controller.profiles = profiles
        controller.refresh_combo()
        combo.setCurrentIndex(index)
        return controller

    # -- mémoire continue

    def test_store_puts_layers_in_active_profile_only(self):
        c = self.make([{"name": "A"}, {"name": "B"}], index=1)
        self.manager.layers[0].power = 55.0
        c.store_memory()
        self.assertNotIn("layers", c.profiles[0])
        self.assertEqual(c.profiles[1]["layers"], self.manager.to_list())

    def test_startup_restores_layers_completely(self):
        c = self.make([{"name": "M1"}])
        first = self.manager.layers[0]
        first.power, first.speed, first.name = 55.0, 1234, "Mon calque"
        self.manager.add_layer().passes = 4
        c.store_memory()
        saved = json.loads(c.to_json())  # aller-retour disque
        ids = [layer.id for layer in self.manager.layers]

        other = LayerManager()  # nouveau démarrage : calques par défaut
        self.assertTrue(apply_saved_layers(other, saved[0]["layers"], full=True))
        self.assertEqual([layer.id for layer in other.layers], ids)
        self.assertEqual((other.layers[0].name, other.layers[0].power, other.layers[0].speed),
                         ("Mon calque", 55.0, 1234))
        self.assertEqual(len(other.layers), 3)
        self.assertEqual(other.layers[2].passes, 4)

    def test_load_applies_the_last_profile_fully(self):
        c = self.make([])
        layers = LayerManager()
        layers.layers[0].speed = 4321
        raw = json.dumps([{"name": "A"}, {"name": "B", "layers": layers.to_list()}])
        c.load(raw, "B", {"name": "Défaut"})
        self.assertEqual(c.current_name(), "B")
        self.assertEqual(self.applied[-1]["name"], "B")
        self.assertEqual(self.manager.layers[0].speed, 4321)
        c.load("pas du json", None, {"name": "Défaut"})
        self.assertEqual([p["name"] for p in c.profiles], ["Défaut"])

    def test_schedule_persist_waits_until_ready_and_debounces(self):
        c = self.make([{"name": "M1"}])
        _FakeTimer.instances.clear()
        with mock.patch.object(mp, "QTimer", _FakeTimer):
            c.schedule_persist()  # pas encore prêt : ignoré
            self.assertEqual(_FakeTimer.instances, [])
            c.persist_ready = True
            c.schedule_persist()
            c.schedule_persist()
        self.assertEqual(len(_FakeTimer.instances), 1)  # un seul minuteur réutilisé
        self.assertEqual(c.profiles[0]["layers"], self.manager.to_list())  # rangé tout de suite
        timer = _FakeTimer.instances[0]
        self.assertEqual((timer.started, timer.single), (2, True))
        timer.timeout.connect.assert_called_once()

    # -- changement de machine (calques existants)

    def test_switching_machine_only_updates_settings_by_id(self):
        manager = LayerManager()
        ids = [layer.id for layer in manager.layers]
        names = [layer.name for layer in manager.layers]
        other = [dict(layer.to_dict(), power=11.0, speed=999, passes=7, enabled=False)
                 for layer in manager.layers]
        other[0]["name"], other[0]["color"] = "Nom de l'autre machine", "#000000"
        apply_saved_layers(manager, other, full=False)
        self.assertEqual([layer.id for layer in manager.layers], ids)  # identité conservée
        self.assertEqual([layer.name for layer in manager.layers], names)  # nom conservé
        for layer in manager.layers:
            self.assertEqual((layer.power, layer.speed, layer.passes, layer.enabled),
                             (11.0, 999, 7, False))

    def test_switching_machine_falls_back_to_position(self):
        manager = LayerManager()
        apply_saved_layers(manager, [{"id": "zzz1", "power": 20.0, "speed": 3000},
                                     {"id": "zzz2", "power": 70.0, "speed": 400}])
        self.assertEqual((manager.layers[0].power, manager.layers[0].speed), (20.0, 3000))
        self.assertEqual((manager.layers[1].power, manager.layers[1].speed), (70.0, 400))

    def test_switching_never_adds_or_removes_layers(self):
        manager = LayerManager()
        n = len(manager.layers)
        apply_saved_layers(manager, [{"power": 1.0}])  # moins de calques
        apply_saved_layers(manager, [{"power": 2.0}] * (n + 3))  # plus de calques
        self.assertEqual(len(manager.layers), n)

    def test_profile_without_layers_changes_nothing(self):
        manager = LayerManager()
        before = manager.to_list()
        for saved in (None, [], "oups", [None, 3]):
            apply_saved_layers(manager, saved, full=True)
            apply_saved_layers(manager, saved, full=False)
        self.assertEqual(manager.to_list(), before)

    def test_corrupted_values_do_not_crash(self):
        manager = LayerManager()
        apply_saved_layers(manager, [{"id": manager.layers[0].id, "power": "abc",
                                      "speed": None, "passes": 3}])
        layer = manager.layers[0]
        self.assertEqual(layer.passes, 3)  # la valeur valide est reprise
        self.assertIsInstance(layer.power, float)  # la valeur corrompue est ignorée
        self.assertIsInstance(layer.speed, int)
        apply_saved_layers(manager, [{"power": "abc", "speed": "x", "passes": [],
                                      "enabled": 0, "mode": "Inconnu"}], full=True)
        for layer in manager.layers:
            self.assertIsInstance(layer.power, float)
            self.assertIsInstance(layer.speed, int)
            self.assertIsInstance(layer.passes, int)
            self.assertEqual(layer.mode, "Découpe")  # mode inconnu -> valeur par défaut
            self.assertFalse(layer.enabled)  # valeur valide reprise

    # -- actions sur les profils

    def test_new_profile_captures_the_displayed_settings(self):
        c = self.make([{"name": "A"}])
        self.manager.layers[1].speed = 777
        with mock.patch.object(QInputDialog, "getText", return_value=("  B  ", True)):
            c.new_profile()
        self.assertEqual(c.current_name(), "B")
        self.assertEqual(c.profiles[1]["w"], 400.0)
        self.assertEqual(c.profiles[1]["layers"][1]["speed"], 777)

    def test_update_keeps_the_name_and_links_layers(self):
        c = self.make([{"name": "A", "w": 100.0}])
        with mock.patch.object(QMessageBox, "information"):
            c.update_profile()
        self.assertEqual((c.profiles[0]["name"], c.profiles[0]["w"]), ("A", 400.0))
        self.assertEqual(self.linked, [True])

    def test_the_last_profile_cannot_be_deleted(self):
        c = self.make([{"name": "A"}, {"name": "B"}], index=1)
        with mock.patch.object(QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            c.delete_profile()
        self.assertEqual([p["name"] for p in c.profiles], ["A"])
        with mock.patch.object(QMessageBox, "warning") as warning:
            c.delete_profile()
        warning.assert_called_once()
        self.assertEqual(len(c.profiles), 1)


if __name__ == "__main__":
    unittest.main()
