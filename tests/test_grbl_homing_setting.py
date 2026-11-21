"""« Inclure $H » décoché à la connexion quand la machine a le homing désactivé ($22=0)
(EngraverController.check_grbl_settings, cases grisées par la fenêtre)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, REPO)                                   # stencil_studio (window_controller)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from laser_studio.i18n import tr
    from laser_studio.controllers.engraver import EngraverController
    from laser_studio.controllers.machine_connection import MachineConnection
    from laser_studio.grbl.commands import parse_grbl_settings
    from laser_studio.models.grbl import GrblConfig
    from laser_studio.ui.app.window_controller import WindowControllerMixin
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6, pyserial... manquants
    EngraverController = None


class _Check:
    def __init__(self, checked):
        self.checked = checked
        self.enabled = True
        self.tooltip = ""

    def setEnabled(self, value):
        self.enabled = value

    def setToolTip(self, text):
        self.tooltip = text

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
    last_port = "/dev/ttyUSB0"

    def __init__(self, response):
        self.response = response

    def send_command(self, cmd):
        return self.response


class _Window:
    """Les deux cases homing de la fenêtre (Configuration GRBL, matrice de test)."""
    _set_homing_available = WindowControllerMixin._set_homing_available if EngraverController else None


@unittest.skipIf(EngraverController is None, "PyQt6 non importable ici")
class GrblHomingSettingTests(unittest.TestCase):
    def connect_with(self, response, f=None):
        if f is None:
            f = _Window()
            f.txt_console = _Console()
            f.chk_homing = _Check(True)
            f.chk_mat_homing = _Check(True)
            f.dialogs = FakeDialogs()
        engraver = EngraverController(MachineConnection(usb=_USB(response)), GrblConfig(), f.dialogs,
                                      set_homing_available=f._set_homing_available)
        engraver.log.connect(f.txt_console.append)         # messages : barre d'état (log_message)
        engraver.check_grbl_settings()
        f.warnings = [title for kind, title, _text in f.dialogs.calls if kind == "warning"]
        return f

    def test_homing_disabled_unchecks_and_disables_both_options(self):
        f = self.connect_with("$22=0 (homing cycle, bool)\n$32=1\nok")
        for check in (f.chk_homing, f.chk_mat_homing):
            self.assertFalse(check.checked)
            self.assertFalse(check.enabled)
            self.assertTrue(check.tooltip)
        self.assertEqual(len(f.txt_console.lines), 2)       # case décochée + mode laser ($32)

    def test_homing_enabled_or_unknown_keeps_the_default(self):
        for response in ("$22=1\n$32=1\nok", "$22=abc\n$32=1\nok", "Pas de réponse"):
            f = self.connect_with(response)
            self.assertTrue(f.chk_homing.checked, response)
            self.assertTrue(f.chk_homing.enabled, response)

    def test_reconnecting_a_machine_with_homing_enables_without_rechecking(self):
        f = self.connect_with("$22=0\n$32=1\nok")
        self.connect_with("$22=1\n$32=1\nok", f)
        for check in (f.chk_homing, f.chk_mat_homing):
            self.assertTrue(check.enabled)
            self.assertFalse(check.checked)
            self.assertEqual(check.tooltip, "")

    def test_unknown_after_homing_off_keeps_it_disabled(self):
        f = self.connect_with("$22=0\n$32=1\nok")
        self.connect_with("Pas de réponse", f)                # pas de réponse : on ne sait rien de plus
        self.assertFalse(f.chk_homing.enabled)

    def test_parse_grbl_settings(self):
        parsed = parse_grbl_settings("Grbl 1.1h\n$22 = 0 (homing)\n$32=1\nerror:9\nok")
        self.assertEqual(parsed, {"$22": "0", "$32": "1"})

    def test_homing_off_shows_the_message_once(self):
        f = self.connect_with("$22=0\n$32=1\nok")
        self.assertEqual(f.warnings, [tr("laser.homing_unsupported_title")])
        self.connect_with("$22=0\n$32=1\nok", f)          # reconnexion : déjà décoché
        self.assertEqual(len(f.warnings), 1)

    def test_missing_22_means_homing_unsupported(self):
        f = self.connect_with("$32=1\nok")
        self.assertEqual(f.warnings, [tr("laser.homing_unsupported_title")])
        for check in (f.chk_homing, f.chk_mat_homing):
            self.assertFalse(check.checked)
            self.assertFalse(check.enabled)
            self.assertEqual(check.tooltip, tr("ui.homing_unsupported_tip"))

    def test_missing_32_warns_about_laser_mode_and_keeps_homing(self):
        f = self.connect_with("$22=1\nok")
        self.assertEqual(len(f.txt_console.lines), 1)       # « $32 introuvable »
        self.assertEqual(f.warnings, [tr("laser.grbl_mode_missing_title")])
        self.assertTrue(f.chk_homing.checked)
        self.assertTrue(f.chk_homing.enabled)

    def test_no_answer_warns_and_keeps_homing(self):
        """Mauvais port (rien ne répond à $$) : on ne désactive pas le homing
        d'un graveur qu'on n'a pas pu interroger."""
        f = self.connect_with("")
        self.assertEqual(f.warnings, [tr("laser.grbl_no_answer_title")])
        self.assertTrue(f.chk_homing.checked)
        self.assertTrue(f.chk_homing.enabled)


if __name__ == "__main__":
    unittest.main()
