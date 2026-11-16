"""Liste des ports : ports « n/a » masqués, USB en tête, dernier port resélectionné."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication, QComboBox
    from laser_studio.grbl import ports
    from laser_studio.laser_control_mixin import LaserControlMixin
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


class _Settings:
    """Remplace QSettings : rien n'est écrit dans la vraie configuration."""

    def __init__(self):
        self.values = {}

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


@unittest.skipIf(ports is None, "PyQt6 / pyserial non importables ici")
class SerialPortsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings = _Settings()
        patcher = mock.patch.object(ports, "_settings", lambda: self.settings)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_na_ports_hidden_and_usb_first(self):
        self.assertEqual(ports.port_labels(SYSTEM_PORTS), [
            "/dev/ttyACM0 - GRBL",
            "/dev/ttyUSB2 - USB Serial",
            "/dev/ttyUSB10 - USB Serial",
            "/dev/ttyS4 - 16550A UART",
        ])

    def window(self):
        class Fake(LaserControlMixin):
            pass
        f = Fake.__new__(Fake)
        f.combo_ports = QComboBox()
        self.addCleanup(f.combo_ports.deleteLater)
        return f

    def refresh(self, f, system_ports):
        with mock.patch("serial.tools.list_ports.comports", return_value=system_ports), \
                mock.patch("laser_studio.laser_control_mixin.simulation_enabled", return_value=False):
            f.refresh_com_ports()

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
        f = self.window()
        self.refresh(f, SYSTEM_PORTS)
        f.combo_ports.setCurrentText("/dev/ttyUSB2 - USB Serial")
        f.usb = mock.Mock()
        f.usb.is_connected.return_value = False
        f.usb.connect.return_value = True
        for name in ("update_connection_widgets", "log_message",
                     "_check_grbl_laser_mode", "_start_status_poll"):
            setattr(f, name, mock.Mock())
        f.toggle_connection()
        f.usb.connect.assert_called_once_with("/dev/ttyUSB2")
        self.assertEqual(ports.load_last_port(), "/dev/ttyUSB2")


if __name__ == "__main__":
    unittest.main()
