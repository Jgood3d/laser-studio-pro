"""« Inclure $H » décoché à la connexion quand la machine a le homing désactivé ($22=0)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from laser_control_mixin import LaserControlMixin
except ImportError:  # PyQt6, pyserial... manquants
    LaserControlMixin = None


class _Check:
    def __init__(self, checked):
        self.checked = checked

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        self.checked = value


class _Console:
    def __init__(self):
        self.lines = []

    def append(self, text):
        self.lines.append(text)


class _USB:
    def __init__(self, response):
        self.response = response

    def send_command(self, cmd):
        return self.response


@unittest.skipIf(LaserControlMixin is None, "laser_control_mixin non importable ici")
class GrblHomingSettingTests(unittest.TestCase):
    def connect_with(self, response):
        class Fake(LaserControlMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = _USB(response)
        f.txt_console = _Console()
        f.chk_homing = _Check(True)
        f.chk_mat_homing = _Check(True)
        f._check_grbl_laser_mode()
        return f

    def test_homing_disabled_unchecks_both_options(self):
        f = self.connect_with("$22=0 (homing cycle, bool)\n$32=1\nok")
        self.assertFalse(f.chk_homing.checked)
        self.assertFalse(f.chk_mat_homing.checked)
        self.assertEqual(len(f.txt_console.lines), 2)       # case décochée + mode laser ($32)

    def test_homing_enabled_or_unknown_keeps_the_default(self):
        for response in ("$22=1\n$32=1\nok", "$32=1\nok", "Pas de réponse"):
            f = self.connect_with(response)
            self.assertTrue(f.chk_homing.checked, response)
            self.assertTrue(f.chk_mat_homing.checked, response)

    def test_parse_grbl_settings(self):
        parsed = LaserControlMixin._parse_grbl_settings("Grbl 1.1h\n$22 = 0 (homing)\n$32=1\nerror:9\nok")
        self.assertEqual(parsed, {"$22": "0", "$32": "1"})

    def test_laser_mode_check_still_reports_missing_32(self):
        f = self.connect_with("$22=1\nok")
        self.assertEqual(len(f.txt_console.lines), 1)       # « $32 introuvable »


if __name__ == "__main__":
    unittest.main()
