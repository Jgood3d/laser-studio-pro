"""Barre d'outils d'un onglet (TabToolBar) : ordre, bouton « Plein écran »."""

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

    def test_left_items_then_spacer_then_right_items_then_fullscreen(self):
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
        self.assertEqual(len(actions), 5)
        self.assertEqual(actions[0].text(), "Action")
        self.assertEqual(actions[0].toolTip(), "Infobulle")
        self.assertIs(bar.widgetForAction(actions[1]), left)
        self.assertIs(bar.widgetForAction(actions[3]), right)
        self.assertIs(actions[4], bar.fullscreen_action)
        actions[0].trigger()
        self.assertEqual(calls, [1])

    def test_fullscreen_button_emits_fullscreen_requested(self):
        bar = TabToolBar()
        self.addCleanup(bar.deleteLater)
        received = []
        bar.fullscreen_requested.connect(lambda: received.append(True))
        bar.fullscreen_action.trigger()
        self.assertEqual(received, [True])


if __name__ == "__main__":
    unittest.main()
