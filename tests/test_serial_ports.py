"""Liste des ports : ports « n/a » masqués, USB en tête, dernier port resélectionné."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtGui import QStandardItemModel
    from PyQt6.QtWidgets import QApplication
    from laser_studio.grbl import ports
    from job_fakes import memory_preferences
    from laser_studio.controllers.engraver import EngraverController
    from laser_studio.models.grbl import GrblConfig
    from laser_studio.ui.machine.connection import ConnectionPanel
except ImportError:  # PyQt6, pyserial... manquants
    ports = None


def _port(device, description, vid=None):
    return SimpleNamespace(device=device, description=description, vid=vid)


SYSTEM_PORTS = [
    _port("/dev/ttyS31", "n/a"),
    _port("/dev/ttyS0", "n/a"),
    _port("/dev/ttyS4", "16550A UART"),
    _port("/dev/ttyUSB10", "USB Serial", vid=0x1A86),
    _port("/dev/ttyACM0", "GRBL"),
    _port("/dev/ttyUSB2", "USB Serial", vid=0x1A86),
]


@unittest.skipIf(ports is None, "PyQt6 / pyserial non importables ici")
class SerialPortsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Préférences en mémoire : rien n'est écrit dans la vraie configuration.
        self.settings = memory_preferences(self)["UIConfig"]

    def test_na_ports_hidden_and_usb_first(self):
        self.assertEqual(ports.port_labels(SYSTEM_PORTS), [
            "/dev/ttyACM0 - GRBL",
            "/dev/ttyUSB2 - USB Serial",
            "/dev/ttyUSB10 - USB Serial",
            "/dev/ttyS4 - 16550A UART",
        ])

    def window(self, connection=None):
        """Panneau Connexion et contrôleur du graveur, branchés comme dans la fenêtre."""
        f = SimpleNamespace()
        f.panel = ConnectionPanel(QStandardItemModel())
        self.addCleanup(f.panel.deleteLater)
        f.combo_ports = f.panel.ports_combo
        f.engraver = EngraverController(connection or mock.Mock(), GrblConfig(), mock.Mock(),
                                        selected_port=f.panel.selected_port)
        f.engraver.ports_changed.connect(f.panel.set_ports)
        return f

    def refresh(self, f, system_ports):
        with mock.patch("serial.tools.list_ports.comports", return_value=system_ports), \
                mock.patch("laser_studio.controllers.engraver.simulation_enabled", return_value=False):
            f.engraver.refresh_ports()

    def test_last_port_is_selected_at_startup(self):
        ports.save_last_port("/dev/ttyUSB10")
        f = self.window()
        self.refresh(f, SYSTEM_PORTS)
        self.assertEqual(f.combo_ports.currentText(), "/dev/ttyUSB10 - USB Serial")

    def test_unknown_last_port_falls_back_to_first_usb(self):
        ports.save_last_port("/dev/ttyUSB7")              # graveur débranché
        f = self.window()
        self.refresh(f, SYSTEM_PORTS)
        self.assertEqual(f.combo_ports.currentText(), "/dev/ttyACM0 - GRBL")

    def test_refresh_keeps_the_displayed_port(self):
        f = self.window()
        self.refresh(f, SYSTEM_PORTS)
        f.combo_ports.setCurrentText("/dev/ttyUSB2 - USB Serial")
        self.refresh(f, SYSTEM_PORTS)
        self.assertEqual(f.combo_ports.currentText(), "/dev/ttyUSB2 - USB Serial")

    def test_successful_connection_remembers_the_port(self):
        connection = mock.Mock()
        connection.is_connected.return_value = False
        connection.connect.return_value = True
        f = self.window(connection)
        self.refresh(f, SYSTEM_PORTS)
        f.combo_ports.setCurrentText("/dev/ttyUSB2 - USB Serial")
        f.engraver.check_grbl_settings = mock.Mock()
        f.engraver.toggle_connection()
        connection.connect.assert_called_once_with("/dev/ttyUSB2")
        f.engraver.check_grbl_settings.assert_called_once()
        self.assertEqual(ports.load_last_port(), "/dev/ttyUSB2")


if __name__ == "__main__":
    unittest.main()
