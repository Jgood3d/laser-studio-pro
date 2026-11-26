"""Panneau des actions de job (JobActionsPanel) : signaux émis, état reçu."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
    from unittest import mock
    from laser_studio.controllers.engraver import EngraverController
    from laser_studio.models.grbl import GrblConfig
    from laser_studio.ui.machine.job_actions import JobActionsPanel
    from laser_studio.i18n import tr
    from laser_studio.models import machine_state as ms
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
                                                    "ui.repeat_last_job", "macros.manage_tip")})
        self.assertEqual(panel.findChildren(QPushButton), [])     # sans macro : boutons à icône seulement

    def test_macro_buttons(self):
        panel = self.make()
        got, managed = [], []
        panel.macro_requested.connect(got.append)
        panel.manage_macros_requested.connect(lambda: managed.append(True))
        panel.set_macros([(3, "Décaler", "Déplace la tête", False), (5, "Pointeur", "", True)])
        buttons = panel.findChildren(QPushButton)
        self.assertEqual([b.text() for b in buttons], ["Décaler", "⚠ Pointeur"])
        self.assertIn(tr("macros.laser_tip"), buttons[1].toolTip())
        buttons[1].click()
        panel.buttons["macros"].click()
        self.assertEqual((got, managed), ([5], [True]))
        panel.set_macros([])
        self.app.processEvents()
        self.assertFalse(panel.macro_area.isVisibleTo(panel))

    def test_repeat_is_disabled_until_a_job_was_sent(self):
        panel = self.make()
        button = self.button(panel, "ui.repeat_last_job")
        self.assertFalse(button.isEnabled())
        panel.set_repeat_enabled(True)
        self.assertTrue(button.isEnabled())

    def test_set_connected_locks_the_actions_but_not_the_macros_editor(self):
        panel = self.make()
        panel.set_macros([(0, "Décaler", "", False)])
        panel.set_repeat_enabled(True)
        panel.set_allowed(lambda action: ms.allowed(ms.DISCONNECTED, action))
        actions = [b for name, b in panel.buttons.items() if name != "macros"]
        self.assertFalse(any(b.isEnabled() for b in actions))
        self.assertFalse(panel.macro_buttons[0].isEnabled())
        self.assertTrue(panel.buttons["macros"].isEnabled())          # macros modifiables sans graveur
        panel.set_allowed(lambda action: ms.allowed(ms.READY, action))
        self.assertTrue(all(b.isEnabled() for b in actions))
        self.assertTrue(panel.macro_buttons[0].isEnabled())
        panel.set_repeat_enabled(False)
        self.assertFalse(panel.buttons["repeat"].isEnabled())


@unittest.skipIf(JobActionsPanel is None, "PyQt6 non importable ici")
class WorkZeroTests(unittest.TestCase):
    """La logique fabrique les commandes de l'origine de travail."""

    def make(self):
        engraver = EngraverController(mock.Mock(), GrblConfig(), mock.Mock())
        engraver.sent = []
        engraver.send_direct = engraver.sent.append
        return engraver

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
