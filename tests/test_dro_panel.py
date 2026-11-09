"""Position de la machine (DroPanel) : affichage de l'état et signal de déverrouillage."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt6.QtWidgets import QApplication
    from ui.machine.dro import DroPanel
    from i18n import tr
except ImportError:  # PyQt6 manquant
    DroPanel = None


@unittest.skipIf(DroPanel is None, "PyQt6 non importable ici")
class DroPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        panel = DroPanel()
        self.addCleanup(panel.deleteLater)
        return panel

    def test_starts_without_position(self):
        panel = self.make()
        self.assertEqual(panel.state_label.text(), tr("ui.dro_state").format(value="—"))
        self.assertEqual(panel.x_label.text(), tr("ui.dro_x").format(value="—"))
        self.assertTrue(panel.unlock_button.isHidden())

    def test_position_is_shown_with_three_decimals(self):
        panel = self.make()
        panel.set_status("Idle", 12.3456, -7.5, 0.0)
        self.assertEqual(panel.state_label.text(), tr("ui.dro_state").format(value="Idle"))
        self.assertEqual((panel.x_label.text(), panel.y_label.text(), panel.z_label.text()),
                         (tr("ui.dro_x").format(value="12.346"), tr("ui.dro_y").format(value="-7.500"),
                          tr("ui.dro_z").format(value="0.000")))
        self.assertIn("#2ecc71", panel.state_label.styleSheet())

    def test_unlock_button_only_in_alarm(self):
        panel = self.make()
        panel.set_status("Alarm", 0, 0, 0)
        self.assertFalse(panel.unlock_button.isHidden())
        panel.set_status("Idle", 0, 0, 0)               # jamais de déverrouillage automatique
        self.assertTrue(panel.unlock_button.isHidden())

    def test_disconnected_hides_the_position(self):
        panel = self.make()
        panel.set_status("Alarm", 1, 2, 3)
        panel.set_status(None)
        self.assertEqual(panel.x_label.text(), tr("ui.dro_x").format(value="—"))
        self.assertTrue(panel.unlock_button.isHidden())
        self.assertIn("#cccccc", panel.state_label.styleSheet())   # plus la couleur de l'alarme

    def test_unlock_button_emits_its_signal(self):
        panel = self.make()
        received = []
        panel.unlock_requested.connect(lambda: received.append(True))
        panel.set_status("Alarm", 0, 0, 0)
        panel.unlock_button.click()
        self.assertEqual(received, [True])


if __name__ == "__main__":
    unittest.main()
