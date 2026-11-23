"""La vraie fenêtre (ui/app/main_window.py), hors écran : onglets, plein écran, panneau du bas,
outils de dessin, barre d'outils de l'image, génération et affichage du G-Code, résolution et
focale, thème et langue, fermeture, projet, export de Stencil Studio.

Les préférences sont en mémoire pendant toute la classe : rien n'est écrit chez l'utilisateur."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

try:
    from PIL import Image
    from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
    from laser_studio.core import preferences
    from laser_studio.i18n import language, tr
    from laser_studio.models.layers import ENGRAVE_MODE
    from laser_studio.ui.app import main_window
except ImportError:  # PyQt6, Pillow manquants
    main_window = None

YES = "Yes"


@unittest.skipIf(main_window is None, "PyQt6 / Pillow non importables ici")
class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._memory = preferences.in_memory()
        cls.stores = cls._memory.__enter__()
        cls._language = language._current_lang
        # Préchauffage de Stencil Studio (QTimer 3 s) : QtWebEngine plante hors écran.
        cls._preload = mock.patch("stencil_studio.controllers.studio.StencilStudioController.preload")
        cls._preload.start()
        cls.win = main_window.FullLaserStudio()
        cls.win.show()
        cls.app.processEvents()
        cls.folder = tempfile.mkdtemp()
        cls.image_path = os.path.join(cls.folder, "image.png")
        Image.new("L", (200, 100), 90).save(cls.image_path)

    @classmethod
    def tearDownClass(cls):
        cls._preload.stop()
        cls.win.hide()                     # pas de close() : il demanderait d'enregistrer le projet
        language._current_lang = cls._language
        cls._memory.__exit__(None, None, None)

    def pump(self, seconds=0.05):
        end = time.time() + seconds
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)

    @property
    def tabs(self):
        return self.win.main_tabs_view

    def visible(self, tab):
        return self.tabs.isTabVisible(self.tabs.indexOf(tab))

    def close_button(self, tab):
        return self.tabs.tabBar().tabButton(self.tabs.indexOf(tab), self.tabs.tabBar().ButtonPosition.RightSide)

    @staticmethod
    def answer(name):
        return getattr(QMessageBox.StandardButton, name)

    def load_image(self):
        self.win.image.load_path(self.image_path)
        self.pump(0.5)

    def test_window_title_is_translated(self):
        self.assertEqual(self.win.windowTitle(), tr("ui.window_title"))

    # -- onglets

    def test_optional_tabs_menu_and_close_button(self):
        w, actions = self.win, self.win.app_actions
        self.assertTrue(self.visible(w.tab_job_queue) and actions.job_queue.isChecked())   # affichée au départ
        self.assertIsNotNone(self.close_button(w.tab_job_queue))
        actions.gcode_console.setChecked(True)
        self.assertTrue(self.visible(w.tab_console_gcode))
        self.close_button(w.tab_console_gcode).click()
        self.assertFalse(self.visible(w.tab_console_gcode) or actions.gcode_console.isChecked())
        self.assertIs(self.stores[preferences.UI_CONFIG].values["show_gcode_console"], False)   # choix mémorisé

    def test_tools_menu_opens_a_hidden_tab(self):
        self.win.app_actions.main_tab_requested.emit("tab_separation")
        self.assertTrue(self.visible(self.win.tab_separation))
        self.assertIs(self.tabs.currentWidget(), self.win.tab_separation)

    def test_bottom_panel_only_on_job_tabs(self):
        self.tabs.setCurrentWidget(self.win.tab_previews)
        self.pump()
        self.assertTrue(self.win.center_bottom_widget.isHidden())
        self.tabs.setCurrentWidget(self.win.tab_vector_2d)
        self.pump()
        self.assertFalse(self.win.center_bottom_widget.isHidden())

    def test_fullscreen_of_a_tab_and_of_the_vector_editor(self):
        w = self.win
        self.tabs.setCurrentWidget(w.tab_job_queue)
        w.app_actions.fullscreen.trigger()
        self.pump(0.1)
        self.assertEqual(self.tabs.indexOf(w.tab_job_queue), -1)
        w.tab_job_queue.window().close()
        self.pump(0.2)
        self.assertNotEqual(self.tabs.indexOf(w.tab_job_queue), -1)
        self.assertIsNotNone(self.close_button(w.tab_job_queue))       # croix remise au retour
        self.tabs.setCurrentWidget(w.tab_vector_editor)
        w.app_actions.fullscreen.trigger()
        self.pump(0.1)
        self.assertEqual(self.tabs.indexOf(w.tab_vector_editor), -1)
        w.tab_vector_editor.window().close()
        self.pump(0.2)
        self.assertIs(self.tabs.currentWidget(), w.tab_vector_editor)

    # -- éditeur vectoriel

    def test_draw_tools_snap_and_work_area(self):
        w, tab = self.win, self.win.tab_vector_editor
        tab.draw_buttons["rect"].trigger()
        self.assertEqual(w.vector_canvas._draw_tool, "rect")
        self.assertEqual([k for k, b in tab.draw_buttons.items() if b.isChecked()], ["rect"])
        tab.draw_buttons[None].trigger()
        tab.snap_check.setChecked(True)
        tab.snap_step_spin.setValue(2.5)
        self.assertEqual((w.vector_canvas.snap_enabled, w.vector_canvas.snap_step_mm), (True, 2.5))
        tab.snap_check.setChecked(False)
        bed = w.machine.bed_w
        w.machine.update(bed_w=321.0)
        self.assertEqual(w.vector_canvas.work_w_mm, 321.0)               # suit le modèle de la machine
        w.machine.update(bed_w=bed)

    # -- barre d'outils de l'image

    def test_image_toolbar_on_the_image_tab(self):
        w, actions = self.win, self.win.app_actions
        self.tabs.setCurrentWidget(w.tab_previews)
        self.pump()
        w.image.processed_array = None
        w.image.raw_image = None
        w.image_actions.update_state()
        self.assertFalse(actions.image_rotate_left.isEnabled())
        self.load_image()
        self.assertTrue(actions.image_rotate_left.isEnabled() and actions.mirror_h.isEnabled())
        actions.image_rotate_right.trigger()
        self.assertEqual(w.image.raw_image.size, (100, 200))
        with mock.patch.object(QMessageBox, "question", return_value=self.answer(YES)) as question:
            actions.image_delete.trigger()
        self.assertFalse(w.image.has_image())
        self.assertEqual(question.call_count, 1)                        # une seule question
        self.assertFalse(actions.image_rotate_left.isEnabled())

    def test_image_toolbar_on_the_separation_tab(self):
        w, actions = self.win, self.win.app_actions
        w.tabs.show(w.tab_separation)
        self.pump()
        w.separation.load_path(self.image_path)
        self.pump(0.3)
        self.assertTrue(actions.image_rotate_left.isEnabled())
        with mock.patch.object(QMessageBox, "question", return_value=self.answer("No")):
            actions.image_delete.trigger()
        self.assertTrue(w.separation.has_image())
        with mock.patch.object(QMessageBox, "question", return_value=self.answer(YES)):
            actions.image_delete.trigger()
        self.assertFalse(w.separation.has_image())

    # -- G-Code

    def test_generated_and_imported_gcode_are_shown(self):
        w = self.win
        self.load_image()
        w.job_display.last_gcode_text = None
        with mock.patch.object(QMessageBox, "question", return_value=self.answer(YES)), \
                mock.patch.object(QMessageBox, "warning", return_value=self.answer(YES)), \
                mock.patch.object(QMessageBox, "information"):
            w.job.generate()
        end = time.time() + 20
        while w.job_display.last_gcode_text is None and time.time() < end:
            self.pump(0.1)
        self.assertTrue(w.tab_console_gcode.gcode().strip())
        self.assertIs(self.tabs.currentWidget(), w.tab_vector_2d)
        self.assertTrue(all(a.isEnabled() for a in w.app_actions.gcode_export_actions.values()))
        w.job_display.status_updated("Run", 5.0, 6.0, 0.0)
        self.assertEqual(list(w.tab_vector_2d.position_marker.getData()[0]), [5.0])
        w.job.imported.emit("G21\nG1 X1 Y1 S10\n", "/tmp/x.gcode")
        self.assertTrue(w.tab_console_gcode.gcode().startswith("G21"))

    # -- résolution, focale, comparaison

    def test_resolution_reaches_the_matrix_and_focal_drives_it(self):
        w = self.win
        w.resolution_box.mode_combo.setCurrentIndex(0)                  # lignes/mm saisies
        w.resolution_box.set_lines_per_mm(8.0)
        self.assertAlmostEqual(w.tab_matrix.lines_mm_spin.value(), 8.0)
        w.resolution_box.mode_combo.setCurrentIndex(2)                  # d'après la focale
        focal = w.machine.focal
        w.tab_machine_params.focal_spin.setValue(0.2)
        self.pump()
        self.assertAlmostEqual(w.resolution_box.lines_per_mm(), 5.0, places=2)
        w.tab_machine_params.focal_spin.setValue(focal)
        w.resolution_box.configure_focal_requested.emit()
        self.pump(0.1)
        self.assertTrue(w.tab_machine_params.window().isVisible())      # bouton de la focale
        w.tab_machine_params.window().close()

    def test_dither_comparison_and_engrave_layer_list(self):
        w = self.win
        self.load_image()
        with mock.patch.object(QDialog, "exec", return_value=0) as dialog:
            w.tab_previews.compare_requested.emit()
        self.assertEqual(dialog.call_count, 1)
        combo = w.tab_previews.settings.engrave_layer_combo
        count = combo.count()
        layer = w.layer_manager.add_layer()
        w.layer_manager.update(layer.id, mode=ENGRAVE_MODE)
        self.assertEqual(combo.count(), count + 1)                      # la liste suit les calques
        w.layer_manager.remove_layer(layer.id)

    # -- thème, langue, aide

    def test_theme_language_and_help(self):
        w = self.win
        w.app_actions.theme_selected.emit("light")
        self.assertEqual(self.stores[preferences.UI_CONFIG].values["app_theme"], "light")
        w.app_actions.theme_selected.emit("dark")
        with mock.patch.object(QMessageBox, "information") as info:
            w.app_actions.language_selected.emit("en")
        self.assertEqual(info.call_count, 1)                            # appliquée au prochain démarrage
        self.assertEqual(self.stores[preferences.UI_CONFIG].values["language"], "en")
        language.set_language("fr")
        w.app_actions.documentation_requested.emit()
        self.pump(0.1)
        self.assertIsNotNone(w.window_controller._help_dialog)
        w.window_controller._help_dialog.close()

    # -- fermeture, projet

    def test_cancelled_close_keeps_the_window_and_saves_the_settings(self):
        w = self.win
        with mock.patch.object(QMessageBox, "question", return_value=self.answer("Cancel")):
            w.close()
        self.assertTrue(w.isVisible())
        self.assertIn("preview_2d_side_sizes", self.stores[preferences.UI_CONFIG].values)
        self.assertEqual(self.stores[preferences.MACHINE_CONFIG].values["machine_bed_w_mm"], w.machine.bed_w)

    def test_project_round_trip(self):
        w = self.win
        self.load_image()
        width = w.tab_previews.settings.width_spin
        width.setValue(42.0)
        data, image = w.state.capture_project()
        width.setValue(77.0)
        w.state.restore_project(data, image)
        self.pump(0.3)
        self.assertAlmostEqual(w.tab_previews.settings.size_mm()[0], 42.0)
        self.assertTrue(w.image.has_image())
        self.assertEqual(w.state._material_autosave_pause, 0)

    # -- Stencil Studio

    def test_stencil_studio_export_lands_in_the_vector_editor(self):
        """L'export téléchargé par la page du Studio est rangé dans les calques, sans moteur web."""
        w = self.win
        studio = w.window_controller.stencil()
        dialog = studio.dialog or studio._new_dialog()
        svg = os.path.join(tempfile.mkdtemp(prefix="stencil_studio_"), "export.svg")
        with open(svg, "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="20mm" height="20mm" viewBox="0 0 20 20">'
                    '<g id="CUT"><path d="M1 1 L10 1 L10 10 Z"/></g></svg>')
        count = len(w.vector_document.objects)
        dialog.downloaded(svg)
        self.pump()
        self.assertGreater(len(w.vector_document.objects), count)
        self.assertFalse(os.path.exists(svg))                           # fichier temporaire supprimé
        self.assertIn("export.svg", w.statusBar().message_label.text())


if __name__ == "__main__":
    unittest.main()
