"""Fenêtre de comparaison des algorithmes de tramage (DitherComparisonDialog)."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import numpy as np
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
    from ui.dialogs.dither_comparison import DitherComparisonDialog
except ImportError:  # PyQt6, numpy manquants
    DitherComparisonDialog = None


@unittest.skipIf(DitherComparisonDialog is None, "PyQt6 non importable ici")
class DitherComparisonDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, names):
        thumb = np.zeros((20, 30), dtype=np.uint8)
        dialog = DitherComparisonDialog(None, [(n, thumb) for n in names])
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_one_thumbnail_and_button_per_algorithm(self):
        dialog = self.make(["Stucki", "Atkinson", "Burkes"])
        buttons = [b.text() for b in dialog.findChildren(QPushButton)]
        self.assertEqual(buttons, ["Stucki", "Atkinson", "Burkes"])
        pixmaps = [l.pixmap() for l in dialog.findChildren(QLabel)]
        self.assertEqual(
            [(p.width(), p.height()) for p in pixmaps], [(30, 20)] * 3
        )

    def test_choosing_emits_the_algorithm_and_closes(self):
        dialog = self.make(["Stucki", "Atkinson"])
        chosen = []
        dialog.algorithm_chosen.connect(chosen.append)
        dialog.show()
        dialog.findChildren(QPushButton)[1].click()
        self.assertEqual(chosen, ["Atkinson"])
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
