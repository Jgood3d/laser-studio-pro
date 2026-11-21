"""Boîtes de dialogue des contrôleurs (ui/user_dialogs.py) : chaque méthode
ouvre la bonne boîte Qt, avec les bons boutons ; et aucun contrôleur n'en
ouvre lui-même."""
import os
import re
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLLERS = os.path.join(REPO, "src", "laser_studio", "controllers")
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
    from laser_studio.ui.user_dialogs import UserDialogs
except ImportError:  # PyQt6 manquant
    UserDialogs = None

YES, NO, CANCEL = (QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No,
                   QMessageBox.StandardButton.Cancel) if UserDialogs else (None, None, None)


class ControllersTests(unittest.TestCase):
    def test_no_controller_opens_a_qt_dialog_itself(self):
        """Les contrôleurs passent par UserDialogs (testables sans fenêtre)."""
        pattern = re.compile(r"\b(QMessageBox|QFileDialog|QInputDialog)\b")
        offenders = []
        for name in sorted(os.listdir(CONTROLLERS)):
            if name.endswith(".py"):
                with open(os.path.join(CONTROLLERS, name), encoding="utf-8") as f:
                    if pattern.search(f.read()):
                        offenders.append(name)
        self.assertEqual(offenders, [])


@unittest.skipIf(UserDialogs is None, "PyQt6 non importable ici")
class UserDialogsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.parent = object()
        self.dialogs = UserDialogs(self.parent)

    def test_messages(self):
        for method, qt_name in (("info", "information"), ("warning", "warning"), ("error", "critical")):
            with mock.patch.object(QMessageBox, qt_name) as box:
                getattr(self.dialogs, method)("Titre", "Texte")
            box.assert_called_once_with(self.parent, "Titre", "Texte")

    def test_questions_and_their_buttons(self):
        cases = (
            ("confirm", "question", (YES | CANCEL, YES), YES),         # Oui par défaut
            ("confirm_default_no", "question", (YES | NO, NO), YES),   # action à risque : Non par défaut
            ("confirm_yes_no", "question", (YES | NO,), YES),          # suppression : défaut de Qt
            ("ask_yes_no", "warning", (YES | NO,), YES),               # avertissement Oui / Non
        )
        for method, qt_name, buttons, yes in cases:
            for answer, expected in ((yes, True), (NO, False), (CANCEL, False)):
                with mock.patch.object(QMessageBox, qt_name, return_value=answer) as box:
                    self.assertEqual(getattr(self.dialogs, method)("T", "Q"), expected, (method, answer))
                self.assertEqual(box.call_args[0], (self.parent, "T", "Q") + buttons, method)

    def test_files(self):
        with mock.patch.object(QFileDialog, "getSaveFileName", return_value=("/tmp/a.json", "JSON")) as save:
            self.assertEqual(self.dialogs.save_file("T", "a.json", "JSON (*.json)"), "/tmp/a.json")
        save.assert_called_once_with(self.parent, "T", "a.json", "JSON (*.json)")
        with mock.patch.object(QFileDialog, "getOpenFileName", return_value=("", "")) as open_:
            self.assertEqual(self.dialogs.open_file("T", "JSON (*.json)"), "")
        open_.assert_called_once_with(self.parent, "T", "", "JSON (*.json)")

    def test_ask_text(self):
        with mock.patch.object(QInputDialog, "getText", return_value=(" Verre ", True)) as ask:
            self.assertEqual(self.dialogs.ask_text("Nouveau", "Nom :"), " Verre ")
        ask.assert_called_once_with(self.parent, "Nouveau", "Nom :")
        with mock.patch.object(QInputDialog, "getText", return_value=("ignoré", False)):
            self.assertIsNone(self.dialogs.ask_text("Nouveau", "Nom :"))


if __name__ == "__main__":
    unittest.main()
