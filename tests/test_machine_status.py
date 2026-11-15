"""État et position de la machine : MachineStateView (cadre Connexion) et
AxisPositionRow (sous le pilotage), qui remplacent l'ancien DRO."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.ui.machine.status import AxisPositionRow, MachineStateView
    from laser_studio.i18n import tr
except ImportError:  # PyQt6 manquant
    MachineStateView = None


@unittest.skipIf(MachineStateView is None, "PyQt6 non importable ici")
class MachineStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, cls):
        widget = cls()
        self.addCleanup(widget.deleteLater)
        return widget

    def test_state_starts_unknown(self):
        view = self.make(MachineStateView)
        self.assertEqual(view.state_label.text(), tr("ui.dro_state").format(value="—"))
        self.assertTrue(view.unlock_button.isHidden())

    def test_state_is_coloured(self):
        view = self.make(MachineStateView)
        view.set_state("Idle")
        self.assertEqual(view.state_label.text(), tr("ui.dro_state").format(value="Idle"))
        self.assertIn("#2ecc71", view.state_label.styleSheet())
        view.set_state(None)
        self.assertIn("#cccccc", view.state_label.styleSheet())   # plus la couleur d'avant

    def test_unlock_button_only_in_alarm(self):
        view = self.make(MachineStateView)
        received = []
        view.unlock_requested.connect(lambda: received.append(True))
        view.set_state("Alarm")
        self.assertFalse(view.unlock_button.isHidden())
        view.unlock_button.click()
        self.assertEqual(received, [True])
        view.set_state("Idle")                          # jamais de déverrouillage automatique
        self.assertTrue(view.unlock_button.isHidden())

    def test_position_with_three_decimals(self):
        row = self.make(AxisPositionRow)
        self.assertEqual(row.x_label.text(), tr("ui.dro_x").format(value="—"))
        row.set_position(12.3456, -7.5, 0.0)
        self.assertEqual((row.x_label.text(), row.y_label.text(), row.z_label.text()),
                         (tr("ui.dro_x").format(value="12.346"), tr("ui.dro_y").format(value="-7.500"),
                          tr("ui.dro_z").format(value="0.000")))
        row.set_position(None)
        self.assertEqual(row.z_label.text(), tr("ui.dro_z").format(value="—"))

    def test_axes_share_the_width_equally(self):
        row = self.make(AxisPositionRow)
        layout = row.layout()
        self.assertEqual([layout.stretch(i) for i in range(layout.count())], [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
