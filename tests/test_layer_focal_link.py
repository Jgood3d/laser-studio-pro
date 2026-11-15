"""Lien du pas de remplissage à la taille du spot : seuls les calques remplis
sont liés ; les calques de contour (Découpe, Marquage) gardent leur pas."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.vector_layers import LayerManager, LayerManagerWidget
except ImportError:  # PyQt6 manquant
    LayerManagerWidget = None


@unittest.skipIf(LayerManagerWidget is None, "PyQt6 non importable ici")
class LayerFocalLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_contour_layers_keep_their_own_interval(self):
        manager = LayerManager()                       # gravure, découpe, marquage
        widget = LayerManagerWidget(manager, focal_getter=lambda: 0.1)
        self.addCleanup(widget.deleteLater)
        manager.layers[1].line_interval_linked = True  # ancien profil : découpe liée
        widget.link_all_to_focal()
        engrave, cut, mark = manager.layers
        self.assertEqual((engrave.line_interval_linked, engrave.line_interval), (True, 0.1))
        self.assertFalse(cut.line_interval_linked)
        self.assertEqual((mark.line_interval_linked, mark.line_interval), (False, 0.06))


if __name__ == "__main__":
    unittest.main()
