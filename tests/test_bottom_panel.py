"""Panneau du bas (ui/app/bottom_panel.py) : onglets, repli et dépliage, hauteur rendue, état mémorisé."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QLabel, QSplitter
    from job_fakes import memory_preferences
    from laser_studio.ui.app.bottom_panel import BottomPanel
except ImportError:  # PyQt6 manquant
    BottomPanel = None


@unittest.skipIf(BottomPanel is None, "PyQt6 non importable ici")
class BottomPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.stored = memory_preferences(self)["UIConfig"].values
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.addCleanup(self.splitter.deleteLater)
        self.splitter.addWidget(QLabel("onglets"))
        self.panel = BottomPanel([("machine", "Graveur", QLabel("m")), ("gcode", "G-code", QLabel("g"))],
                                 self.splitter)
        self.splitter.addWidget(self.panel)
        self.splitter.resize(400, 600)
        self.splitter.show()

    def test_collapsed_at_first_start_and_tabs_open_their_page(self):
        self.assertTrue(self.panel.is_collapsed())
        self.assertTrue(self.panel.stack.isHidden())
        self.assertEqual(self.stored, {})                                 # rien d'écrit au départ
        self.panel.show_page("gcode")
        self.assertFalse(self.panel.is_collapsed())
        self.assertEqual(self.panel.stack.currentIndex(), 1)
        self.assertIs(self.stored["bottom_panel_collapsed"], False)

    def test_expanding_gives_back_the_height_it_had(self):
        self.panel.set_collapsed(False)
        self.splitter.setSizes([350, 250])
        self.app.processEvents()
        expanded = self.splitter.sizes()
        self.panel.toggle()                                               # replié : sa barre d'onglets seule
        self.assertLessEqual(self.panel.maximumHeight(), self.panel.header.sizeHint().height())
        self.assertEqual(self.panel.expanded_sizes, expanded)
        self.app.processEvents()
        self.assertEqual(self.splitter.sizes()[1], self.panel.header.sizeHint().height())   # place rendue
        self.panel.toggle()
        self.app.processEvents()
        self.assertEqual(self.splitter.sizes(), expanded)


if __name__ == "__main__":
    unittest.main()
