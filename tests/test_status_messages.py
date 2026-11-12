"""Messages d'information dans la barre d'état (show_status_message, log_message), jamais dans la console du G-Code."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from PIL import Image
    from laser_studio import main_window
except ImportError:  # PyQt6, pyqtgraph... manquants
    main_window = None


@unittest.skipIf(main_window is None, "main_window non importable ici")
class StatusMessagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        # Préférences et données de l'application dans un dossier temporaire.
        cls.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": cls.tmp.name, "XDG_DATA_HOME": cls.tmp.name})
        cls.env.start()
        cls.app = QApplication.instance() or QApplication([])
        # Préchauffage de Stencil Studio (QTimer 3 s) : QtWebEngine plante hors écran.
        mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
        cls.win = main_window.FullLaserStudio()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def test_loaded_image_is_announced_in_the_status_bar(self):
        path = os.path.join(self.tmp.name, "medaille.png")
        Image.new("L", (945, 945), 128).save(path, dpi=(300, 300))
        console_before = self.win.txt_console.toPlainText()
        self.win.load_image_from_path(path)
        status_bar = self.win.statusBar()
        label = status_bar.message_label
        self.assertIn("medaille.png", label.text())
        self.assertNotIn(self.tmp.name, label.text())           # nom du fichier seul…
        self.assertIn(path, label.toolTip())                      # … chemin complet dans l'infobulle
        self.assertIn("80.0 x 80.0", label.text())
        self.assertTrue(status_bar.message_timer.isActive())
        self.assertEqual(self.win.txt_console.toPlainText(), console_before)   # console du graveur intacte

        status_bar.message_timer.timeout.emit()             # délai écoulé : message effacé
        self.assertEqual(label.text(), "")

    def test_message_does_not_hide_the_generation_progress(self):
        status_bar = self.win.statusBar()
        status_bar.show_progress(40, "Génération en cours… 40%")
        self.win.show_status_message("Image supprimée.")
        self.assertFalse(status_bar.progress_bar.isHidden())
        status_bar.hide_progress()
        self.assertTrue(status_bar.progress_bar.isHidden())

    def test_action_messages_go_to_the_status_bar_not_the_console(self):
        # La console ne contient que le G-Code généré, relu par l'export et la file d'attente.
        self.win.txt_console.setPlainText("G21\nG1 X10")
        self.win.log_message(">>> Connecté sur COM3")
        self.win.log_message("> $$\n< ok")
        self.assertEqual(self.win.txt_console.toPlainText(), "G21\nG1 X10")
        label = self.win.statusBar().message_label
        self.assertEqual(label.text(), "> $$ — < ok")
        self.assertEqual(label.toolTip(), "> $$\n< ok")

    def test_no_message_is_written_to_the_console_anymore(self):
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "laser_studio")
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                        self.assertNotIn("txt_console.append", f.read(), name)


class StatusTextTests(unittest.TestCase):
    def test_console_markers_are_removed_and_lines_joined(self):
        from laser_studio.ui.statusbar import status_text
        self.assertEqual(status_text(">>> Déverrouillage ($X) envoyé"), "Déverrouillage ($X) envoyé")
        self.assertEqual(status_text("\n; ERREUR DE GÉNÉRATION :\n; division par zéro"),
                         "ERREUR DE GÉNÉRATION : — division par zéro")
        self.assertEqual(status_text("!!! ERREUR GRBL : error:9"), "ERREUR GRBL : error:9")
        self.assertEqual(status_text("--- Importé depuis : job.nc ---"), "Importé depuis : job.nc")
        self.assertEqual(status_text("  \n "), "")


if __name__ == "__main__":
    unittest.main()
