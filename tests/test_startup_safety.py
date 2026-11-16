"""Avertissement de sécurité du démarrage : quand l'afficher, case
« Ne plus afficher », rappel tous les 30 démarrages, variable NOWARNING."""
import os
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.controllers.startup_safety import (  # noqa: E402
    COUNT_KEY, HIDDEN_KEY, REMINDER_EVERY, StartupSafetyPolicy,
)


class FakeSettings(dict):
    """Faux QSettings : rien n'est écrit dans les réglages de l'utilisateur."""

    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


class StartupSafetyPolicyTests(unittest.TestCase):
    def policy(self, settings=None, environ=None):
        return StartupSafetyPolicy(settings if settings is not None else FakeSettings(), environ or {})

    def test_shown_at_every_launch_by_default(self):
        policy = self.policy()
        self.assertEqual([policy.should_show_at_launch() for _ in range(5)], [True] * 5)

    def test_hidden_comes_back_every_thirty_launches(self):
        settings = FakeSettings()
        policy = self.policy(settings)
        policy.record(hide=True)
        shown = [policy.should_show_at_launch() for _ in range(2 * REMINDER_EVERY)]
        self.assertEqual(REMINDER_EVERY, 30)
        self.assertEqual([i + 1 for i, s in enumerate(shown) if s], [30, 60])

    def test_unticking_the_box_shows_it_again_at_every_launch(self):
        settings = FakeSettings({HIDDEN_KEY: "true", COUNT_KEY: 12})   # texte : comme QSettings
        policy = self.policy(settings)
        self.assertTrue(policy.hidden())
        policy.record(hide=False)
        self.assertEqual(settings, {HIDDEN_KEY: False, COUNT_KEY: 0})
        self.assertTrue(policy.should_show_at_launch())

    def test_nowarning_disables_it_completely(self):
        for value in ("1", "yes", "true"):
            policy = self.policy(environ={"NOWARNING": value})
            self.assertFalse(policy.should_show_at_launch(), value)
        for value in ("", "0"):
            self.assertTrue(self.policy(environ={"NOWARNING": value}).should_show_at_launch(), value)

    def test_nowarning_does_not_touch_the_settings(self):
        settings = FakeSettings({HIDDEN_KEY: True, COUNT_KEY: 5})
        self.policy(settings, {"NOWARNING": "1"}).should_show_at_launch()
        self.assertEqual(settings[COUNT_KEY], 5)

    def test_corrupt_counter_is_restarted(self):
        settings = FakeSettings({HIDDEN_KEY: True, COUNT_KEY: "abc"})
        self.assertFalse(self.policy(settings).should_show_at_launch())
        self.assertEqual(settings[COUNT_KEY], 1)


try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from laser_studio.ui.dialogs.startup_safety import dialog as dialog_module
    from laser_studio.i18n import tr
except ImportError:  # PyQt6 manquant
    dialog_module = None


@unittest.skipIf(dialog_module is None, "PyQt6 non importable ici")
class StartupSafetyDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def run_dialog(self, answer, tick=None, hide_checked=False):
        seen = {}

        def fake_exec(box):
            check = box.checkBox()
            seen["text"], seen["checked"] = check.text(), check.isChecked()
            if tick is not None:
                check.setChecked(tick)
            return answer

        with mock.patch.object(dialog_module.QMessageBox, "exec", fake_exec):
            result = dialog_module.confirm_startup_safety(None, hide_checked)
        return result, seen

    def test_checkbox_and_answers(self):
        (accepted, hide), seen = self.run_dialog(QMessageBox.StandardButton.Ok, tick=True)
        self.assertEqual((accepted, hide), (True, True))
        self.assertEqual(seen["text"], tr("startup.safety.dont_show").format(n=30))
        self.assertFalse(seen["checked"])
        (accepted, _hide), seen = self.run_dialog(QMessageBox.StandardButton.Cancel, hide_checked=True)
        self.assertFalse(accepted)
        self.assertTrue(seen["checked"])          # rappel : la case reste cochée


class MainWiringTests(unittest.TestCase):
    def test_main_asks_the_policy_before_showing_the_dialog(self):
        with open(os.path.join(REPO, "src", "laser_studio", "main.py"), encoding="utf-8") as f:
            src = f.read()
        block = src[src.index("safety = StartupSafetyPolicy("):src.index("from laser_studio.main_window import")]
        self.assertLess(block.index("if safety.should_show_at_launch():"), block.index("confirm_startup_safety("))
        self.assertLess(block.index("sys.exit(0)"), block.index("safety.record(hide)"))   # Annuler : rien d'enregistré


class LaunchConfirmationTests(unittest.TestCase):
    def test_launch_confirmation_starts_with_the_safety_warning(self):
        try:
            from laser_studio.laser_control_mixin import LaserControlMixin
            from laser_studio.i18n import tr
        except ImportError:
            self.skipTest("laser_control_mixin non importable ici")
        text = LaserControlMixin._launch_confirmation_text()
        self.assertTrue(text.startswith(tr("startup.safety.body") + "\n" + tr("startup.safety.detail")))
        self.assertTrue(text.endswith(tr("laser.confirm_body")))    # vérifications et question à la fin
        with open(os.path.join(REPO, "src", "laser_studio", "laser_control_mixin.py"), encoding="utf-8") as f:
            self.assertIn('tr("laser.confirm_title"),\n    self._launch_confirmation_text(),', f.read())


if __name__ == "__main__":
    unittest.main()
