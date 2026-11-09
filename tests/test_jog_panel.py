"""Panneau de pilotage (JogControlPanel) : signaux émis, état reçu, et jog_move()."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_source  # noqa: E402

try:
    from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
    from laser_control_mixin import LaserControlMixin
    from ui.machine.controls import JogControlPanel
    from ui_menus import MenusMixin
    from app_constants import JOG_DEFAULT_SPEED, JOG_SPEED_MIN, JOG_STEPS_MM
    from i18n import tr
except ImportError:  # PyQt6, pyserial... manquants
    JogControlPanel = None


class _USB:
    def is_connected(self):
        return True


@unittest.skipIf(JogControlPanel is None, "PyQt6 non importable ici")
class JogMoveTests(unittest.TestCase):
    """La logique reçoit des millimètres et fabrique la commande GRBL."""

    def make(self):
        class Fake(LaserControlMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = _USB()
        f.sent = []
        f._run_commands_async = f.sent.append
        return f

    def test_millimetres_become_a_jog_command(self):
        f = self.make()
        f.jog_move(1.0, 0.0, 6000)
        f.jog_move(-1.0, 1.0, 6000)
        self.assertEqual(f.sent, ["$J=G91 G21 X1.000 Y0.000 F6000", "$J=G91 G21 X-1.000 Y1.000 F6000"])

    def test_small_step(self):
        f = self.make()
        f.jog_move(0.0, -0.1, 300)
        self.assertEqual(f.sent, ["$J=G91 G21 X0.000 Y-0.100 F300"])


@unittest.skipIf(JogControlPanel is None, "PyQt6 non importable ici")
class JogControlPanelTests(unittest.TestCase):
    """Le panneau émet des signaux, sans rien savoir de la machine."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, max_speed=6000):
        panel = JogControlPanel(max_speed)
        self.addCleanup(panel.deleteLater)
        return panel

    def button(self, panel, tooltip):
        return next(b for b in panel.findChildren(QToolButton) if b.toolTip() == tooltip)

    def record(self, signal):
        received = []
        signal.connect(lambda *args: received.append(args))
        return received

    def test_arrows_emit_millimetres_and_speed(self):
        panel = self.make()
        jogs = self.record(panel.jog_requested)
        for tooltip in ("X+", "X-", "Y+", "Y-", "X+ Y+", "X- Y-"):
            self.button(panel, tooltip).click()
        self.assertEqual(jogs, [(10.0, 0.0, 3000), (-10.0, 0.0, 3000), (0.0, 10.0, 3000),
                                (0.0, -10.0, 3000), (10.0, 10.0, 3000), (-10.0, -10.0, 3000)])

    def test_step_slider_sets_the_distance(self):
        panel = self.make()
        jogs = self.record(panel.jog_requested)
        panel.step_slider.setValue(JOG_STEPS_MM.index(0.1))
        self.button(panel, "X+").click()
        self.assertEqual(jogs, [(0.1, 0.0, 3000)])

    def test_commands_emit_their_signal(self):
        panel = self.make()
        for key, signal in (("ui.homing_cmd", panel.home_requested), ("ui.pause", panel.pause_requested),
                            ("ui.resume", panel.resume_requested), ("ui.reset", panel.reset_requested),
                            ("ui.kill", panel.emergency_stop_requested),
                            ("ui.send_to_laser", panel.send_job_requested)):
            received = self.record(signal)
            self.button(panel, tr(key)).click()
            self.assertEqual(received, [()], key)

    def test_every_command_keeps_its_label_as_a_tooltip(self):
        panel = self.make()
        tooltips = {b.toolTip() for b in panel.findChildren(QToolButton)}
        for key in ("ui.homing_cmd", "ui.pause", "ui.resume", "ui.reset", "ui.kill", "ui.send_to_laser"):
            self.assertIn(tr(key), tooltips, key)
        self.assertEqual(panel.findChildren(QPushButton), [])     # boutons à icône seulement

    def test_send_button_can_be_disabled_during_a_job(self):
        panel = self.make()
        button = self.button(panel, tr("ui.send_to_laser"))
        panel.set_send_enabled(False)
        self.assertFalse(button.isEnabled())
        panel.set_send_enabled(True)
        self.assertTrue(button.isEnabled())

    def test_set_connected_locks_the_panel(self):
        panel = self.make()
        panel.set_connected(False)
        self.assertFalse(panel.isEnabled())
        panel.set_connected(True)
        self.assertTrue(panel.isEnabled())

    def test_speed_never_exceeds_the_machine_max_speed(self):
        panel = self.make(max_speed=6000)
        self.assertEqual((panel.speed_slider.maximum(), panel.speed()), (6000, JOG_DEFAULT_SPEED))
        panel.set_max_speed(2000)                       # machine plus lente : valeur ramenée au maximum
        self.assertEqual((panel.speed_slider.maximum(), panel.speed()), (2000, 2000))
        self.assertIn("2000", panel.speed_slider.toolTip())
        panel.set_max_speed(10)                         # jamais sous la vitesse minimale
        self.assertEqual(panel.speed_slider.maximum(), JOG_SPEED_MIN)

    def test_slow_machine_starts_at_its_max_speed(self):
        panel = self.make(max_speed=1500)
        self.assertEqual(panel.speed(), 1500)


class _Box:
    def __init__(self):
        self.enabled = None

    def setEnabled(self, value):
        self.enabled = value

    def set_connected(self, value):
        self.enabled = value


@unittest.skipIf(JogControlPanel is None, "ui_menus non importable ici")
class CommandsLockTests(unittest.TestCase):
    def make(self, connected):
        class Fake(MenusMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = type("U", (), {"is_connected": lambda self: connected})()
        f.jog_panel, f.job_actions_box, f.direct_console_box = _Box(), _Box(), _Box()
        return f

    def test_commands_follow_the_connection(self):
        for connected in (False, True):
            f = self.make(connected)
            f.update_connection_widgets()
            self.assertEqual((f.jog_panel.enabled, f.job_actions_box.enabled, f.direct_console_box.enabled),
                             (connected, connected, connected))

    def test_layout_position_jog_job_actions_dro(self):
        src = ui_source()
        row = src[src.index("machine_row = QHBoxLayout()"):src.index("center_bottom_layout.addLayout(machine_row)")]
        # Le facteur d'étirement (place partagée) peut suivre chaque widget.
        order = [row.index(k) for k in ("addWidget(self.job_position_box", "addWidget(self.jog_panel",
                                        "addWidget(self.job_actions_box", "addWidget(dro_box")]
        self.assertEqual(order, sorted(order))
        self.assertRegex(src, r"# Commandes verrouillées tant que non connecté\s+self\.update_connection_widgets\(\)")


@unittest.skipIf(JogControlPanel is None, "PyQt6 non importable ici")
class WindowWiringTests(unittest.TestCase):
    """Dans la fenêtre : le panneau suit la vitesse max du graveur."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        from unittest import mock
        tmp = tempfile.mkdtemp()                       # préférences isolées : rien chez l'utilisateur
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": tmp, "XDG_DATA_HOME": tmp}):
            import main_window
            cls.app = QApplication.instance() or QApplication([])
            cls.win = main_window.FullLaserStudio()

    def test_speed_slider_follows_the_machine_max_speed(self):
        win = self.win
        slider = win.jog_panel.speed_slider
        self.assertEqual(slider.maximum(), int(win.spin_machine_max_speed.value()))
        win.spin_machine_max_speed.setValue(2000)
        self.assertEqual((slider.maximum(), slider.value()), (2000, 2000))
        win.spin_machine_max_speed.setValue(8000)
        slider.setValue(10000)
        self.assertEqual(slider.value(), 8000)

    def test_job_actions_keep_their_label_as_a_tooltip(self):
        tooltips = {b.toolTip() for b in self.win.job_actions_box.findChildren(QToolButton)}
        for key in ("ui.frame", "ui.zero_work", "ui.go_zero", "ui.repeat_last_job"):
            self.assertIn(tr(key), tooltips, key)


if __name__ == "__main__":
    unittest.main()
