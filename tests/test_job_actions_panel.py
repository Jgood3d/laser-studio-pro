"""Panneau des actions de job (JobActionsPanel) : signaux émis, état reçu."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
    from laser_control_mixin import LaserControlMixin
    from ui.machine.job_actions import JobActionsPanel
    from i18n import tr
except ImportError:  # PyQt6, pyserial... manquants
    JobActionsPanel = None


@unittest.skipIf(JobActionsPanel is None, "PyQt6 non importable ici")
class JobActionsPanelTests(unittest.TestCase):
    """Le panneau émet des signaux, sans rien savoir de la machine."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        panel = JobActionsPanel()
        self.addCleanup(panel.deleteLater)
        return panel

    def button(self, panel, key):
        return next(b for b in panel.findChildren(QToolButton) if b.toolTip() == tr(key))

    def test_each_action_emits_its_signal(self):
        panel = self.make()
        panel.set_repeat_enabled(True)
        for key, signal in (("ui.frame", panel.frame_requested),
                            ("ui.zero_work", panel.set_work_zero_requested),
                            ("ui.go_zero", panel.go_to_work_zero_requested),
                            ("ui.repeat_last_job", panel.repeat_job_requested)):
            received = []
            signal.connect(lambda *args, r=received: r.append(args))
            self.button(panel, key).click()
            self.assertEqual(received, [()], key)

    def test_every_action_keeps_its_label_as_a_tooltip(self):
        panel = self.make()
        tooltips = {b.toolTip() for b in panel.findChildren(QToolButton)}
        self.assertEqual(tooltips, {tr(k) for k in ("ui.frame", "ui.zero_work", "ui.go_zero",
                                                    "ui.repeat_last_job")})
        self.assertEqual(panel.findChildren(QPushButton), [])     # boutons à icône seulement

    def test_repeat_is_disabled_until_a_job_was_sent(self):
        panel = self.make()
        button = self.button(panel, "ui.repeat_last_job")
        self.assertFalse(button.isEnabled())
        panel.set_repeat_enabled(True)
        self.assertTrue(button.isEnabled())

    def test_set_connected_locks_the_panel(self):
        panel = self.make()
        panel.set_connected(False)
        self.assertFalse(panel.isEnabled())
        panel.set_connected(True)
        self.assertTrue(panel.isEnabled())


@unittest.skipIf(JobActionsPanel is None, "PyQt6 non importable ici")
class WorkZeroTests(unittest.TestCase):
    """La logique fabrique les commandes de l'origine de travail."""

    def make(self):
        class Fake(LaserControlMixin):
            pass
        f = Fake.__new__(Fake)
        f.sent = []
        f.send_manual_direct_cmd = f.sent.append
        return f

    def test_set_work_zero(self):
        f = self.make()
        f.set_work_zero()
        self.assertEqual(f.sent, ["G92 X0 Y0"])

    def test_go_to_work_zero(self):
        f = self.make()
        f.go_to_work_zero()
        self.assertEqual(f.sent, ["G0 X0 Y0"])


if __name__ == "__main__":
    unittest.main()
