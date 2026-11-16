"""Modèle des calques (models/layers.py) : toute modification passe par
LayersModel, qui émet ses signaux et l'écrit dans le journal de débogage.
Le tableau des calques (LayerManagerWidget) suit le modèle."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.models.layers import LayersModel, LaserLayer
    from laser_studio.vector_layers import LayerManager, LayerManagerWidget
except ImportError:  # PyQt6 manquant
    LayersModel = None

LOGGER = "laser_studio.gravure.modeles"


@unittest.skipIf(LayersModel is None, "PyQt6 non importable ici")
class LayersModelTests(unittest.TestCase):
    def make(self):
        model = LayersModel()
        events = []
        model.layer_changed.connect(lambda i, c: events.append(("changed", i, c)))
        model.layer_added.connect(lambda i: events.append(("added", i)))
        model.layer_removed.connect(lambda i: events.append(("removed", i)))
        model.layers_reordered.connect(lambda: events.append(("reordered",)))
        model.layers_reset.connect(lambda: events.append(("reset",)))
        model.changed.connect(lambda: events.append(("any",)))
        return model, events

    def test_old_name_still_works(self):
        self.assertIs(LayerManager, LayersModel)

    def test_update_emits_only_what_changed(self):
        model, events = self.make()
        engrave = model.engrave_layer()
        changes = model.update(engrave.id, power=80, speed=engrave.speed)
        self.assertEqual(changes, {"power": 80.0})
        self.assertEqual(events, [("changed", engrave.id, {"power": 80.0}), ("any",)])

    def test_update_without_change_emits_nothing(self):
        model, events = self.make()
        engrave = model.engrave_layer()
        self.assertEqual(model.update(engrave.id, power=engrave.power), {})
        self.assertEqual(events, [])

    def test_values_are_converted_and_invalid_ones_ignored(self):
        model, _events = self.make()
        engrave = model.engrave_layer()
        model.update(engrave.id, speed="1200", power="abc", mode="Inconnu")
        self.assertEqual(engrave.speed, 1200)
        self.assertEqual(engrave.power, 35.0)
        self.assertEqual(engrave.mode, "Gravure Remplie")

    def test_unknown_setting_is_a_programming_error(self):
        model, _events = self.make()
        with self.assertRaises(KeyError):
            model.update(model.layers[0].id, puissance=80)

    def test_unknown_layer_is_ignored(self):
        model, events = self.make()
        with self.assertLogs(LOGGER, "WARNING"):
            self.assertEqual(model.update("nope", power=10), {})
        self.assertEqual(events, [])

    def test_every_change_is_logged_with_old_and_new_value(self):
        model, _events = self.make()
        engrave = model.engrave_layer()
        with self.assertLogs(LOGGER, "INFO") as logs:
            model.update(engrave.id, power=80)
        self.assertIn("power 35.0 -> 80.0", logs.output[0])
        self.assertIn(engrave.name, logs.output[0])

    def test_add_remove_move_emit_their_signal(self):
        model, events = self.make()
        layer = model.add_layer()
        self.assertEqual(events[-2:], [("added", layer.id), ("any",)])
        self.assertEqual(model.move_layer(layer.id, -1), len(model.layers) - 2)
        self.assertEqual(events[-2:], [("reordered",), ("any",)])
        model.remove_layer(layer.id)
        self.assertEqual(events[-2:], [("removed", layer.id), ("any",)])
        self.assertIsNone(model.get(layer.id))

    def test_load_list_resets_and_repairs_corrupted_values(self):
        model, events = self.make()
        model.load_list([{"id": "a1", "name": "X", "mode": "Découpe", "power": "abc", "speed": "x"}])
        self.assertEqual(events, [("reset",), ("any",)])
        layer = model.get("a1")
        defaults = LaserLayer()
        self.assertEqual((layer.power, layer.speed), (defaults.power, defaults.speed))
        self.assertEqual({l.role for l in model.layers}, {"engrave", "cut", "mark"})

    def test_engrave_layer_is_the_first_fill_layer(self):
        model, _events = self.make()
        self.assertEqual(model.engrave_layer().mode, "Gravure Remplie")
        model.update(model.engrave_layer().id, mode="Découpe")
        self.assertIs(model.engrave_layer(), model.layers[0])   # plus de remplissage : le premier


@unittest.skipIf(LayersModel is None, "PyQt6 non importable ici")
class LayerTableFollowsModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        model = LayersModel()
        widget = LayerManagerWidget(model, focal_getter=lambda: 0.1)
        self.addCleanup(widget.deleteLater)
        return model, widget

    def test_change_made_elsewhere_is_shown(self):
        """Matériau, profil machine, matrice : le tableau affiche la valeur."""
        model, widget = self.make()
        engrave = model.engrave_layer()
        model.update(engrave.id, power=80, enabled=False)
        editors = widget._editors[engrave.id]
        self.assertEqual(editors["power"].value(), 80.0)
        self.assertFalse(editors["enabled"].isChecked())

    def test_typing_in_the_table_updates_the_model(self):
        model, widget = self.make()
        engrave = model.engrave_layer()
        widget._editors[engrave.id]["power"].setValue(65)
        self.assertEqual(engrave.power, 65.0)

    def test_reload_rebuilds_the_rows(self):
        model, widget = self.make()
        model.load_list(model.to_list() + [{"id": "zz", "name": "Extra", "mode": "Découpe"}])
        self.assertEqual(widget.table.rowCount(), 4)
        self.assertIn("zz", widget._editors)

    def test_widget_relays_model_changes(self):
        model, widget = self.make()
        received = []
        widget.layers_changed.connect(lambda: received.append(True))
        model.update(model.layers[0].id, passes=3)
        self.assertEqual(received, [True])


if __name__ == "__main__":
    unittest.main()
