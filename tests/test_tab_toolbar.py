"""Barre d'outils d'un onglet (TabToolBar) : ordre des éléments (le plein
écran est dans la barre d'outils principale)."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel
    from laser_studio.ui.widgets import TabToolBar
except ImportError:  # PyQt6 manquant
    TabToolBar = None


@unittest.skipIf(TabToolBar is None, "PyQt6 non importable ici")
class TabToolBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_left_items_then_spacer_then_right_items(self):
        calls = []
        left, right = QCheckBox("gauche"), QLabel("droite")
        bar = TabToolBar(
            left_actions=[
                (QIcon(), "Action", "Infobulle", lambda: calls.append(1))
            ],
            left_widgets=[left],
            right_widgets=[right],
        )
        self.addCleanup(bar.deleteLater)
        actions = bar.actions()
        self.assertEqual(len(actions), 4)
        self.assertEqual(actions[0].text(), "Action")
        self.assertEqual(actions[0].toolTip(), "Infobulle")
        self.assertIs(bar.widgetForAction(actions[1]), left)
        self.assertIs(bar.widgetForAction(actions[3]), right)
        self.assertFalse(hasattr(bar, "fullscreen_action"))
        actions[0].trigger()
        self.assertEqual(calls, [1])



if __name__ == "__main__":
    unittest.main()
