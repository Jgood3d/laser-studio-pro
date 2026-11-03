"""Fermeture de la fenêtre : sort de la sauvegarde automatique selon la réponse."""
import importlib
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class QuitTests(unittest.TestCase):
    def setUp(self):
        try:
            self.mod = importlib.import_module("ui_setup_mixin")
        except ImportError:
            self.skipTest("ui_setup_mixin non importable ici")
        cls = next(c for c in vars(self.mod).values() if isinstance(c, type) and c.__name__ == "UiSetupMixin")
        self.win = cls.__new__(cls)
        self.calls = []
        for name in ("save_machine_settings", "save_splitter_sizes", "_clear_autosave", "_flush_background_writes"):
            setattr(self.win, name, lambda n=name: self.calls.append(n))
        self.event = mock.Mock()

    def close_with(self, answer, saved=True):
        self.win.save_project = lambda: self.calls.append("save_project") or saved
        button = getattr(self.mod.QMessageBox.StandardButton, answer)
        with mock.patch.object(self.mod.QMessageBox, "question", return_value=button):
            self.win.closeEvent(self.event)

    def test_quit_without_saving_clears_the_autosave(self):
        self.close_with("No")
        self.assertIn("_clear_autosave", self.calls)
        self.event.accept.assert_called_once()

    def test_cancelled_save_keeps_the_window_open(self):
        self.close_with("Yes", saved=False)
        self.event.ignore.assert_called_once()
        self.event.accept.assert_not_called()

    def test_successful_save_quits(self):
        self.close_with("Yes")
        self.assertIn("save_project", self.calls)
        self.event.accept.assert_called_once()

    def test_cancel_keeps_the_window_open_and_the_autosave(self):
        self.close_with("Cancel")
        self.event.ignore.assert_called_once()
        self.assertNotIn("_clear_autosave", self.calls)


if __name__ == "__main__":
    unittest.main()
