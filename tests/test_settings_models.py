"""Modèles des réglages machine (MachineConfig), de la configuration GRBL
(GrblConfig) et des matériaux (MaterialsModel), et liaison des champs de
l'interface à un modèle (ui/binding.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QTextEdit
    from laser_studio.controllers.materials import complete_material
    from laser_studio.models.grbl import GrblConfig
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.materials import MaterialsModel
    from laser_studio.ui.binding import bind
except ImportError:  # PyQt6 manquant
    MachineConfig = None

LOGGER = "laser_studio.gravure.modeles"


@unittest.skipIf(MachineConfig is None, "PyQt6 non importable ici")
class SettingsModelTests(unittest.TestCase):
    def test_values_read_as_attributes_and_change_only_through_update(self):
        machine = MachineConfig()
        received = []
        machine.changed.connect(received.append)
        self.assertEqual(machine.bed_w, 300.0)
        self.assertEqual(machine.update(bed_w="400", bed_h=200.0), {"bed_w": 400.0})
        self.assertEqual(received, [{"bed_w": 400.0}])
        self.assertEqual(machine.update(bed_w=400), {})          # rien de nouveau : pas de signal
        self.assertEqual(len(received), 1)

    def test_invalid_value_is_ignored_and_unknown_name_refused(self):
        machine = MachineConfig()
        with self.assertLogs(LOGGER, "WARNING"):
            machine.update(focal="abc")
        self.assertEqual(machine.focal, 0.10)
        with self.assertRaises(KeyError):
            machine.update(largeur=10)
        with self.assertRaises(AttributeError):
            machine.largeur

    def test_changes_are_logged(self):
        grbl = GrblConfig()
        with self.assertLogs(LOGGER, "INFO") as logs:
            grbl.update(smax=255)
        self.assertIn("GRBL : smax 1000 -> 255", logs.output[0])

    def test_choices_are_enforced(self):
        grbl = GrblConfig()
        with self.assertLogs(LOGGER, "WARNING"):
            grbl.update(laser_cmd="M7")
        self.assertEqual(grbl.laser_cmd, "M4")
        grbl.update(laser_cmd="M3")
        self.assertEqual(grbl.laser_cmd, "M3")

    def test_machine_profile_round_trip(self):
        machine = MachineConfig()
        machine.update(bed_w=410, focal=0.08, max_speed=9000)
        profile = machine.to_profile()
        self.assertEqual(profile["w"], 410.0)
        other = MachineConfig()
        other.apply_profile(profile)
        self.assertEqual(other.to_dict(), machine.to_dict())

    def test_old_profile_without_limits_gets_the_defaults(self):
        machine = MachineConfig()
        machine.update(max_speed=9000, bed_w=500)
        machine.apply_profile({"h": 250})                   # ni largeur, ni vitesse
        self.assertEqual((machine.bed_w, machine.bed_h, machine.max_speed), (500.0, 250.0, 6000.0))


@unittest.skipIf(MachineConfig is None, "PyQt6 non importable ici")
class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_spin_box_follows_the_model_and_feeds_it(self):
        machine = MachineConfig()
        spin = QDoubleSpinBox()
        spin.setRange(1, 5000)
        self.addCleanup(spin.deleteLater)
        bind(spin, machine, "bed_w")
        self.assertEqual(spin.value(), 300.0)               # le champ prend la valeur du modèle
        machine.update(bed_w=420)
        self.assertEqual(spin.value(), 420.0)
        spin.setValue(250)
        self.assertEqual(machine.bed_w, 250.0)

    def test_widget_signals_still_fire_for_their_listeners(self):
        machine = MachineConfig()
        spin = QDoubleSpinBox()
        spin.setRange(0.01, 2)
        spin.setDecimals(3)
        self.addCleanup(spin.deleteLater)
        bind(spin, machine, "focal")
        heard = []
        spin.valueChanged.connect(heard.append)
        machine.update(focal=0.2)                            # ex. profil machine choisi
        self.assertEqual(heard, [0.2])

    def test_checkbox_combo_and_text(self):
        grbl = GrblConfig()
        check, combo, text = QCheckBox(), QComboBox(), QTextEdit()
        combo.addItems(["M4 (Dynamic Power)", "M3 (Constant Power)"])
        for w in (check, combo, text):
            self.addCleanup(w.deleteLater)
        bind(check, grbl, "overscan_enabled")
        bind(combo, grbl, "laser_cmd", to_widget=("M4", "M3").index,
             from_widget=lambda i: ("M4", "M3")[i])
        bind(text, grbl, "start_gcode")
        self.assertTrue(check.isChecked())
        combo.setCurrentIndex(1)
        self.assertEqual(grbl.laser_cmd, "M3")
        grbl.update(start_gcode="G21")
        self.assertEqual(text.toPlainText(), "G21")
        check.setChecked(False)
        self.assertFalse(grbl.overscan_enabled)


@unittest.skipIf(MachineConfig is None, "PyQt6 non importable ici")
class MaterialsModelTests(unittest.TestCase):
    def make(self):
        model = MaterialsModel({"Personnalisé": {"sp_e": 9}, "Bois": {"sp_e": 8}},
                               complete=complete_material)
        events = []
        for name in ("material_added", "material_removed", "material_changed", "current_changed"):
            getattr(model, name).connect(lambda n, s=name: events.append((s, n)))
        model.materials_reset.connect(lambda: events.append(("reset",)))
        return model, events

    def test_materials_are_completed_and_first_one_is_chosen(self):
        model, _events = self.make()
        self.assertEqual(model.current, "Personnalisé")
        roles = sorted(d["role"] for d in model.get("Bois")["layers"])
        self.assertEqual(roles, ["cut", "engrave", "mark"])

    def test_store_replaces_or_adds_and_says_if_something_changed(self):
        model, events = self.make()
        material = model.get("Bois")
        self.assertFalse(model.store("Bois", material))      # identique : rien
        changed = dict(material, sp_e=1234)
        with self.assertLogs(LOGGER, "INFO"):
            self.assertTrue(model.store("Bois", changed))
        self.assertTrue(model.store("Verre", changed))
        self.assertEqual(events, [("material_changed", "Bois"), ("material_added", "Verre")])

    def test_select_and_remove(self):
        model, events = self.make()
        self.assertTrue(model.select("Bois"))
        self.assertFalse(model.select("Bois"))
        self.assertFalse(model.select("Inconnu"))
        model.remove("Bois")
        self.assertEqual(model.current, "Personnalisé")
        self.assertEqual(events, [("current_changed", "Bois"), ("material_removed", "Bois")])

    def test_reload_keeps_the_wanted_material(self):
        model, events = self.make()
        model.set_materials({"A": {}, "B": {}}, current="B")
        self.assertEqual(model.current, "B")
        self.assertEqual(events, [("reset",)])


if __name__ == "__main__":
    unittest.main()
