"""Projet : enregistré puis rouvert dans la vraie fenêtre, sans erreur."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:  # PyQt6 manquant
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt6 non importable ici")
class ProjectRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()               # préférences isolées : rien chez l'utilisateur
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": cls.tmp, "XDG_DATA_HOME": cls.tmp}):
            import main_window
            cls.app = QApplication.instance() or QApplication([])
            cls.win = main_window.FullLaserStudio()

    def test_saved_project_reopens_with_its_layers(self):
        win = self.win
        win.layer_manager.layers[0].name = "Calque du projet"
        win.layer_manager.layers[0].speed = 1234
        path = os.path.join(self.tmp, "projet.lsp")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(win.project.data(encode_image=False), f)

        win.layer_manager.layers[0].name = "Autre nom"
        win.layers_tab.refresh()
        with mock.patch.object(QMessageBox, "critical") as critical, \
                mock.patch.object(QMessageBox, "information") as information:
            win.project.open_path(path)
        critical.assert_not_called()                  # ex. AttributeError sur un widget renommé
        information.assert_called_once()
        self.assertEqual(win.layer_manager.layers[0].name, "Calque du projet")
        self.assertEqual(win.layer_manager.layers[0].speed, 1234)


if __name__ == "__main__":
    unittest.main()
