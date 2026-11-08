"""Panneau de pilotage compact : jog avec les curseurs de pas et de vitesse."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_source  # noqa: E402

try:
    from laser_control_mixin import LaserControlMixin
    from ui_jog import JogMixin
    from ui_menus import MenusMixin
    from ui_setup_mixin import UiSetupMixin
except ImportError:  # PyQt6, pyserial... manquants
    LaserControlMixin = None


class _Slider:
    def __init__(self, value):
        self.v = value

    def value(self):
        return self.v


class _USB:
    def is_connected(self):
        return True


@unittest.skipIf(LaserControlMixin is None, "laser_control_mixin non importable ici")
class JogPanelTests(unittest.TestCase):
    def make(self, step_index, speed):
        class Fake(LaserControlMixin):
            JOG_STEPS_MM = JogMixin.JOG_STEPS_MM
        f = Fake.__new__(Fake)
        f.usb = _USB()
        f.slider_jog_step = _Slider(step_index)
        f.slider_jog_speed = _Slider(speed)
        f.sent = []
        f._run_commands_async = f.sent.append
        return f

    def test_sliders_set_the_step_and_the_speed(self):
        f = self.make(JogMixin.JOG_STEPS_MM.index(1.0), 6000)
        f.jog_move(1, 0)
        f.jog_move(-1, 1)
        self.assertEqual(f.sent, ["$J=G91 G21 X1.000 Y0.000 F6000", "$J=G91 G21 X-1.000 Y1.000 F6000"])

    def test_small_step(self):
        f = self.make(0, 300)
        f.jog_move(0, -1)
        self.assertEqual(f.sent, ["$J=G91 G21 X0.000 Y-0.100 F300"])

    def test_every_command_keeps_its_label_as_a_tooltip(self):
        with open(os.path.join(ROOT, "ui_jog.py"), encoding="utf-8") as fh:
            src = fh.read()
        panel = src[src.index('jog_box = QGroupBox(tr("ui.jog_box"))'):src.index("return jog_box")]
        for key in ("ui.pause", "ui.resume", "ui.reset", "ui.kill", "ui.frame", "ui.zero_work",
                    "ui.go_zero", "ui.send_to_laser", "ui.repeat_last_job", "ui.homing_cmd"):
            self.assertRegex(panel, rf'_jog_tool_button\((?:.|\n)*?tr\("{re.escape(key)}"\)', key)
        self.assertNotIn("QPushButton(", panel)                 # plus de boutons à texte


class _Box:
    def __init__(self):
        self.enabled = None

    def setEnabled(self, value):
        self.enabled = value


@unittest.skipIf(LaserControlMixin is None, "ui_setup_mixin non importable ici")
class CommandsLockTests(unittest.TestCase):
    def make(self, connected):
        class Fake(MenusMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = type("U", (), {"is_connected": lambda self: connected})()
        f.jog_box, f.direct_console_box = _Box(), _Box()
        return f

    def test_commands_follow_the_connection(self):
        for connected in (False, True):
            f = self.make(connected)
            f.update_connection_widgets()
            self.assertEqual((f.jog_box.enabled, f.direct_console_box.enabled), (connected, connected))

    def test_layout_position_left_jog_center_dro_right(self):
        src = ui_source()
        row = src[src.index("machine_row = QHBoxLayout()"):src.index("center_bottom_layout.addLayout(machine_row)")]
        # Le facteur d'étirement (place partagée) peut suivre chaque widget.
        order = [row.index(k) for k in ("addWidget(self.job_position_box", "addWidget(jog_box",
                                        "addWidget(dro_box")]
        self.assertEqual(order, sorted(order))
        self.assertRegex(src, r"# Commandes verrouillées tant que non connecté\s+self\.update_connection_widgets\(\)")


@unittest.skipIf(LaserControlMixin is None, "PyQt6 non importable ici")
class JogSpeedLimitTests(unittest.TestCase):
    def test_speed_slider_never_exceeds_the_machine_max_speed(self):
        import tempfile
        from unittest import mock
        tmp = tempfile.mkdtemp()                       # préférences isolées : rien chez l'utilisateur
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp, "XDG_DATA_HOME": tmp}):
            from PyQt6.QtWidgets import QApplication
            import main_window
            app = QApplication.instance() or QApplication([])
            win = main_window.FullLaserStudio()
        slider = win.slider_jog_speed
        self.assertEqual(slider.maximum(), int(win.spin_machine_max_speed.value()))
        win.spin_machine_max_speed.setValue(2000)      # machine plus lente : valeur ramenée au maximum
        self.assertEqual((slider.maximum(), slider.value()), (2000, 2000))
        win.spin_machine_max_speed.setValue(8000)
        slider.setValue(10000)
        self.assertEqual(slider.value(), 8000)


if __name__ == "__main__":
    unittest.main()
