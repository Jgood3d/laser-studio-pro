"""Onglet « Calques » (LayersTab) : relais du signal et accès aux calques."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtWidgets import QApplication, QLineEdit
    from ui.tabs.layers import LayersTab
    from vector_layers import LayerManager
except ImportError:  # PyQt6 manquant
    LayersTab = None


@unittest.skipIf(LayersTab is None, "PyQt6 non importable ici")
class LayersTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self):
        manager = LayerManager()
        tab = LayersTab(manager, focal_getter=lambda: 0.1)
        self.addCleanup(tab.deleteLater)
        return tab, manager

    def test_editing_a_layer_emits_layers_changed(self):
        tab, manager = self.make()
        received = []
        tab.layers_changed.connect(lambda: received.append(manager.layers[0].name))
        edit = tab.layer_widget.findChildren(QLineEdit)[0]
        edit.setText("Mon calque")
        edit.textEdited.emit("Mon calque")
        edit.editingFinished.emit()
        self.assertIn("Mon calque", received)

    def test_focal_getter_is_shared_with_the_layer_list(self):
        tab, _ = self.make()
        self.assertEqual(tab.focal_getter(), 0.1)
        self.assertIs(tab.layer_widget.focal_getter, tab.focal_getter)

    def test_refresh_follows_the_layer_manager(self):
        tab, manager = self.make()
        count = len(tab.layer_widget.findChildren(QLineEdit))
        manager.add_layer()
        tab.refresh()
        self.app.processEvents()
        self.assertGreater(len(tab.layer_widget.findChildren(QLineEdit)), count)


if __name__ == "__main__":
    unittest.main()
