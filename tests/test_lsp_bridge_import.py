"""Pont Stencil Studio -> Laser Studio : si l'import avec routage des calques
échoue, le fichier passe par l'import standard de l'éditeur vectoriel."""
import os
import sys
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from stencil_studio import lsp_bridge
except ImportError:  # dépendances de LSP manquantes
    lsp_bridge = None


@unittest.skipIf(lsp_bridge is None, "stencil_studio.lsp_bridge non importable ici")
class FallbackImportTests(unittest.TestCase):
    def make_window(self):
        window = mock.Mock()
        window.layer_manager.layers = []            # import routé impossible : aucun calque
        return window

    def test_failed_routed_import_falls_back_to_the_vector_editor(self):
        window = self.make_window()
        with mock.patch.object(lsp_bridge, "_cleanup_temp"):
            self.assertIsNone(lsp_bridge.import_exported_file(window, "/ailleurs/motif.svg"))
        window.vector_editor.import_file.assert_called_once_with(os.path.abspath("/ailleurs/motif.svg"))

    def test_other_formats_go_straight_to_the_vector_editor(self):
        window = self.make_window()
        with mock.patch.object(lsp_bridge, "_cleanup_temp"):
            lsp_bridge.import_exported_file(window, "/ailleurs/motif.eps")
        window.vector_editor.import_file.assert_called_once_with(os.path.abspath("/ailleurs/motif.eps"))


if __name__ == "__main__":
    unittest.main()
