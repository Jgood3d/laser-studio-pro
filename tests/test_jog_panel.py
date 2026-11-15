"""Panneau de pilotage (JogControlPanel) : signaux émis, état reçu, et jog_move()."""
import os
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_source  # noqa: E402

try:
    from PyQt6.QtGui import QStandardItemModel
    from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
    from laser_studio.laser_control_mixin import LaserControlMixin
    from laser_studio.ui.machine.controls import JogControlPanel
    from laser_studio.ui.machine import MachinePanel
    from laser_studio.ui.app.window_controller import WindowControllerMixin
    from laser_studio.core.constants import JOG_DEFAULT_SPEED, JOG_SPEED_MIN, JOG_STEPS_MM
    from laser_studio.i18n import tr
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

    def test_steps_include_5_20_and_50_mm(self):
        self.assertEqual(JOG_STEPS_MM, (0.1, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0))
        panel = self.make()
        self.assertEqual(panel.step_mm(), 10.0)               # pas de départ inchangé
        jogs = self.record(panel.jog_requested)
        for step in (5.0, 20.0, 50.0):
            panel.step_slider.setValue(JOG_STEPS_MM.index(step))
            self.assertEqual(panel._step_text(panel.step_slider.value()), f"{step:g} mm")
            self.button(panel, "Y+").click()
        self.assertEqual(jogs, [(0.0, 5.0, 3000), (0.0, 20.0, 3000), (0.0, 50.0, 3000)])

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


@unittest.skipIf(JogControlPanel is None, "window_controller non importable ici")
class CommandsLockTests(unittest.TestCase):
    def make(self, connected):
        class Fake(WindowControllerMixin):
            pass
        f = Fake.__new__(Fake)
        f.usb = type("U", (), {"is_connected": lambda self: connected})()
        f.machine_panel = _Box()
        return f

    def test_commands_follow_the_connection(self):
        for connected in (False, True):
            f = self.make(connected)
            f.update_connection_widgets()
            self.assertEqual(f.machine_panel.enabled, connected)

    def test_machine_panel_locks_commands_but_not_the_state(self):
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from PyQt6.QtWidgets import QGroupBox
        panel = MachinePanel(QStandardItemModel(), 6000)
        self.addCleanup(panel.deleteLater)
        for connected in (False, True):
            panel.set_connected(connected)
            connection = panel.connection_panel
            self.assertEqual((panel.jog_panel.isEnabled(), panel.job_actions_panel.isEnabled(),
                              connection.console.isEnabled()), (connected, connected, connected))
            self.assertEqual(connection.connect_button.text(),
                             tr("laser.disconnect") if connected else tr("laser.connect"))
            self.assertTrue(connection.isEnabled() and connection.state_view.isEnabled())
            self.assertTrue(panel.sent_gcode_log.isEnabled())   # suivi d'envoi toujours lisible

    def test_status_goes_to_connection_and_jog_panels(self):
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from PyQt6.QtWidgets import QGroupBox
        panel = MachinePanel(QStandardItemModel(), 6000)
        self.addCleanup(panel.deleteLater)
        panel.set_status("Idle", 1.0, 2.0, 3.0)
        self.assertEqual(panel.connection_panel.state_view.state_label.text(),
                         tr("ui.dro_state").format(value="Idle"))
        self.assertEqual(panel.jog_panel.position_row.y_label.text(), tr("ui.dro_y").format(value="2.000"))
        panel.set_status(None)                           # déconnecté : plus de position connue
        self.assertEqual(panel.jog_panel.position_row.x_label.text(), tr("ui.dro_x").format(value="—"))

    def test_connection_panel_order_and_signals(self):
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from laser_studio.ui.machine.connection import ConnectionPanel
        panel = ConnectionPanel(QStandardItemModel())
        self.addCleanup(panel.deleteLater)
        layout = panel.layout()
        widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
        # Bouton de connexion, puis l'état, puis la console directe, en dessous.
        self.assertEqual([w for w in widgets if w is not None],
                         [panel.connect_button, panel.state_view, panel.console])
        commands, unlocks = [], []
        panel.command_submitted.connect(commands.append)
        panel.unlock_requested.connect(lambda: unlocks.append(True))
        panel.console.command_edit.setText("$X")
        panel.console.command_edit.returnPressed.emit()
        panel.set_state("Alarm")
        panel.state_view.unlock_button.click()
        self.assertEqual((commands, unlocks), (["$X"], [True]))

    def test_progress_bar_shows_the_engraving_percentage(self):
        app = QApplication.instance() or QApplication([])  # noqa: F841
        from PyQt6.QtWidgets import QGroupBox
        panel = MachinePanel(QStandardItemModel(), 6000)
        self.addCleanup(panel.deleteLater)
        panel.progress_bar.setValue(42)
        self.assertEqual(panel.progress_bar.text(), tr("ui.burn_progress").format(pct=42))

    def test_layout_position_connection_jog_job_actions(self):
        src = ui_source()
        row = src[src.index("machine_row = QHBoxLayout()"):src.index("return machine_row")]
        # Le facteur d'étirement (place partagée) peut suivre chaque widget.
        order = [row.index(k) for k in ("addWidget(self.sent_gcode_log", "addWidget(self.connection_panel",
                                        "addWidget(self.jog_panel", "addWidget(self.job_actions_panel")]
        self.assertNotIn("dro_panel", src)
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
            from laser_studio import main_window
            cls.app = QApplication.instance() or QApplication([])
            # Préchauffage de Stencil Studio (QTimer 3 s) : QtWebEngine plante hors écran.
            mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
            cls.win = main_window.FullLaserStudio()

    def test_speed_slider_follows_the_machine_max_speed(self):
        win = self.win
        slider = win.machine_panel.jog_panel.speed_slider
        self.assertEqual(slider.maximum(), int(win.spin_machine_max_speed.value()))
        win.spin_machine_max_speed.setValue(2000)
        self.assertEqual((slider.maximum(), slider.value()), (2000, 2000))
        win.spin_machine_max_speed.setValue(8000)
        slider.setValue(10000)
        self.assertEqual(slider.value(), 8000)

if __name__ == "__main__":
    unittest.main()
