"""Barre d'outils flottante des aperçus d'image (FloatingToolBar)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QApplication, QHBoxLayout, QSplitter, QWidget
    from laser_studio.ui.widgets import FloatingToolBar
except ImportError:  # PyQt6 manquant
    FloatingToolBar = None


@unittest.skipIf(FloatingToolBar is None, "PyQt6 non importable ici")
class FloatingToolBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        page = QWidget()
        self.addCleanup(page.deleteLater)
        splitter = QSplitter()
        splitter.addWidget(QWidget())
        layout = QHBoxLayout(page)
        layout.setContentsMargins(100, 0, 0, 0)            # zone décalée dans la page
        layout.addWidget(splitter)
        actions = [QAction("Annuler", page), None, QAction("Miroir", page)]
        actions[2].setCheckable(True)
        bar = FloatingToolBar(actions, splitter, top_margin=10)
        page.resize(800, 400)
        page.show()
        self.app.processEvents()
        return page, splitter, bar, actions

    def test_floats_over_the_splitter_without_becoming_a_pane(self):
        _page, splitter, bar, _actions = self.make()
        self.assertEqual(splitter.count(), 1)              # pas adoptée par le séparateur
        self.assertIs(bar.parentWidget(), splitter.parentWidget())

    def test_centred_at_the_top_of_its_area_and_follows_resizes(self):
        page, splitter, bar, _actions = self.make()
        area = splitter.geometry()
        self.assertEqual(bar.y(), area.y() + 10)
        self.assertAlmostEqual(bar.geometry().center().x(), area.center().x(), delta=2)
        page.resize(1200, 400)
        self.app.processEvents()
        self.assertAlmostEqual(bar.geometry().center().x(), splitter.geometry().center().x(), delta=2)

    def test_reuses_the_given_actions(self):
        _page, _splitter, bar, actions = self.make()
        self.assertEqual([a for a in bar.actions() if not a.isSeparator()], [actions[0], actions[2]])

    def test_right_anchor_is_vertical_against_the_right_edge(self):
        from PyQt6.QtCore import Qt
        page = QWidget()
        self.addCleanup(page.deleteLater)
        layout = QHBoxLayout(page)
        area = QWidget()
        layout.addWidget(area)
        bar = FloatingToolBar([QAction("Gauche", page), QAction("Droite", page)], area, anchor="right", margin=8)
        page.resize(800, 400)
        page.show()
        self.app.processEvents()
        self.assertEqual(bar.orientation(), Qt.Orientation.Vertical)
        self.assertEqual(bar.geometry().right() + 1, area.geometry().right() + 1 - 8)
        self.assertAlmostEqual(bar.geometry().center().y(), area.geometry().center().y(), delta=2)

    def test_bottom_anchor_and_host_inside_a_splitter(self):
        # Hôte DANS un séparateur (graphique de l'aperçu 2D) : la barre va au parent du séparateur.
        from PyQt6.QtWidgets import QCheckBox
        page = QWidget()
        self.addCleanup(page.deleteLater)
        splitter = QSplitter()
        plot, side = QWidget(), QWidget()
        splitter.addWidget(plot)
        splitter.addWidget(side)
        QHBoxLayout(page).addWidget(splitter)
        check = QCheckBox("Option")
        bar = FloatingToolBar([check], plot, anchor="bottom", margin=8)
        page.resize(800, 400)
        page.show()
        self.app.processEvents()
        self.assertIs(bar.parentWidget(), page)
        self.assertEqual(splitter.count(), 2)
        bottom = plot.mapTo(page, plot.rect().bottomLeft()).y()
        self.assertEqual(bar.geometry().bottom(), bottom - 8)
        self.assertIs(check.parentWidget(), bar)

    def test_unknown_anchor_is_refused(self):
        with self.assertRaises(ValueError):
            FloatingToolBar([], QWidget(), anchor="left")


if __name__ == "__main__":
    unittest.main()
