"""Console directe (DirectConsolePanel) : signal émis, historique, verrouillage."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QPushButton
    from laser_control_mixin import LaserControlMixin
    from ui.machine.console import DirectConsolePanel
except ImportError:  # PyQt6, pyserial... manquants
    DirectConsolePanel = None


@unittest.skipIf(DirectConsolePanel is None, "PyQt6 non importable ici")
class DirectConsolePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        panel = DirectConsolePanel()
        self.addCleanup(panel.deleteLater)
        received = []
        panel.command_submitted.connect(received.append)
        return panel, received

    def test_enter_emits_the_trimmed_command_and_clears_the_field(self):
        panel, received = self.make()
        panel.command_edit.setText("  $X  ")
        QTest.keyClick(panel.command_edit, Qt.Key.Key_Return)
        self.assertEqual((received, panel.command_edit.text()), (["$X"], ""))

    def test_send_button_emits_the_command(self):
        panel, received = self.make()
        panel.command_edit.setText("G0 X10")
        panel.findChildren(QPushButton)[0].click()
        self.assertEqual(received, ["G0 X10"])

    def test_empty_input_does_nothing(self):
        panel, received = self.make()
        panel.command_edit.setText("   ")
        QTest.keyClick(panel.command_edit, Qt.Key.Key_Return)
        self.assertEqual((received, panel.command_edit.text()), ([], "   "))

    def test_sent_commands_are_recalled_with_the_arrows(self):
        panel, _ = self.make()
        for command in ("$X", "G0 X10"):
            panel.command_edit.setText(command)
            QTest.keyClick(panel.command_edit, Qt.Key.Key_Return)
        QTest.keyClick(panel.command_edit, Qt.Key.Key_Up)
        self.assertEqual(panel.command_edit.text(), "G0 X10")
        QTest.keyClick(panel.command_edit, Qt.Key.Key_Up)
        self.assertEqual(panel.command_edit.text(), "$X")

    def test_set_connected_locks_the_console(self):
        panel, _ = self.make()
        panel.set_connected(False)
        self.assertFalse(panel.isEnabled())
        panel.set_connected(True)
        self.assertTrue(panel.isEnabled())


@unittest.skipIf(DirectConsolePanel is None, "PyQt6 non importable ici")
class SendManualCommandTests(unittest.TestCase):
    """La logique reçoit la commande et l'envoie, sans lire de widget."""

    def make(self, connected=True):
        class Fake(LaserControlMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = type("U", (), {"is_connected": lambda self: connected})()
        f.sent = []
        f._run_commands_async = f.sent.append
        return f

    def test_command_is_sent(self):
        f = self.make()
        f.send_console_command("$H")
        self.assertEqual(f.sent, ["$H"])

    def test_empty_command_is_ignored(self):
        f = self.make()
        f.send_console_command("")
        self.assertEqual(f.sent, [])


if __name__ == "__main__":
    unittest.main()
