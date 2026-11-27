"""Premiers pas : quand la fenêtre s'ouvre, ce que lance chaque étape, et quand elle est faite."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.first_steps import SHOW_KEY, STEPS, FirstStepsController
    from laser_studio.core.preferences import MemoryStore, Preferences
    from laser_studio.i18n import tr
    from laser_studio.ui.dialogs.first_steps import open_first_steps
except ImportError:  # PyQt6 manquant
    FirstStepsController = None

if FirstStepsController is not None:
    class FakeConnection(QObject):
        connection_changed = pyqtSignal(bool)
        state_changed = pyqtSignal(str)

        def __init__(self):
            super().__init__()
            self.connected, self.homed = False, False

        def is_connected(self):
            return self.connected


@unittest.skipIf(FirstStepsController is None, "PyQt6 non importable ici")
class FirstStepsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, values=None):
        connection = FakeConnection()
        actions = {key: mock.Mock() for key in STEPS}
        settings = Preferences(MemoryStore(values))
        return FirstStepsController(connection, actions, settings), connection, actions, settings

    def test_shown_at_first_launch_until_unticked(self):
        steps, _connection, _actions, settings = self.make()
        self.assertTrue(steps.should_show_at_launch())
        steps.set_show_at_launch(False)
        self.assertEqual(settings.store.values, {SHOW_KEY: False})
        self.assertFalse(steps.should_show_at_launch())
        steps, *_ = self.make({SHOW_KEY: "false"})                     # QSettings rend du texte
        self.assertFalse(steps.should_show_at_launch())

    def test_steps_are_done_when_the_engraver_says_so(self):
        steps, connection, actions, _settings = self.make()
        self.assertEqual(steps.done(), dict.fromkeys(STEPS, False))
        steps.run("machine")
        actions["machine"].assert_called_once()
        steps.run("frame")                                            # pas connecté : le cadrage n'a rien fait
        self.assertEqual(steps.done(), {"machine": True, "connect": False, "home": False, "frame": False})
        connection.connected = True
        connection.homed = True
        self.assertEqual(steps.done(), dict.fromkeys(STEPS, True))
        connection.connected = False                                  # déconnecté : homing et cadrage à refaire
        self.assertEqual(steps.done(), {"machine": True, "connect": False, "home": False, "frame": False})

    def test_dialog_runs_the_steps_and_shows_their_state(self):
        steps, connection, actions, _settings = self.make()
        dialog = open_first_steps(None, steps)
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.states["connect"].text(), tr("first_steps.todo"))
        dialog.buttons["connect"].click()
        actions["connect"].assert_called_once()
        connection.connected = True
        connection.connection_changed.emit(True)                      # l'état suit la connexion
        self.assertEqual(dialog.states["connect"].text(), tr("first_steps.done"))
        dialog.show_check.setChecked(False)
        self.assertFalse(steps.should_show_at_launch())


if __name__ == "__main__":
    unittest.main()
