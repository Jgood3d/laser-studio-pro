"""Fenêtre unique des générateurs (ui/dialogs/generators) : un seul couple « Importer » / « Annuler » pour tous."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QVBoxLayout
    from laser_studio.ui.dialogs.generators import GeneratorsDialog
except ImportError:  # PyQt6 manquant
    GeneratorsDialog = None


def fake_generator(parent):
    """Comme les vraies fenêtres : OK / Annuler, OK grisé tant que les réglages sont invalides."""
    dialog = QDialog(parent)
    dialog.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    dialog.buttons.accepted.connect(dialog.accept)
    dialog.buttons.rejected.connect(dialog.reject)
    QVBoxLayout(dialog).addWidget(dialog.buttons)
    return dialog


@unittest.skipIf(GeneratorsDialog is None, "PyQt6 non importable ici")
class GeneratorsWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = GeneratorsDialog(None, [("box", "Boîte", QIcon(), fake_generator),
                                              ("puzzle", "Puzzle", QIcon(), fake_generator)], start="puzzle")
        self.addCleanup(self.window.deleteLater)

    def ok(self, key):
        return self.window.page(key).buttons.button(QDialogButtonBox.StandardButton.Ok)

    def test_the_generator_buttons_give_way_to_the_common_ones(self):
        self.assertTrue(self.window.page("puzzle").buttons.isHidden())
        self.assertEqual(self.window.current_key(), "puzzle")

    def test_import_follows_the_ok_of_the_shown_generator(self):
        self.ok("puzzle").setEnabled(False)                     # réglages invalides
        self.assertFalse(self.window.import_button.isEnabled())
        self.window.list.setCurrentRow(0)                       # la boîte, valide
        self.assertTrue(self.window.import_button.isEnabled())
        self.window.list.setCurrentRow(1)
        self.assertFalse(self.window.import_button.isEnabled())
        self.ok("puzzle").setEnabled(True)
        self.assertTrue(self.window.import_button.isEnabled())

    def test_import_validates_the_shown_generator(self):
        self.window.import_button.click()
        self.assertEqual(self.window.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(self.window.chosen, "puzzle")


if __name__ == "__main__":
    unittest.main()
