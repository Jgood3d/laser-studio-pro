"""Machine & Profils et Configuration GRBL : fenêtres ouvertes depuis la barre de menus."""
import importlib
import os
import re
import sys
import types
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_files, ui_source  # noqa: E402


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


class AppMenusTests(unittest.TestCase):
    """Menu et barre d'outils (ui/app/menu/) : structure et signaux."""

    @classmethod
    def setUpClass(cls):
        try:
            from PyQt6.QtWidgets import QApplication
            from laser_studio.ui.app.menu import AppActions, AppMenuBar, AppToolBar
            from laser_studio.i18n import tr
        except ImportError:
            raise unittest.SkipTest("PyQt6 non importable ici")
        cls.app = QApplication.instance() or QApplication([])
        cls.tr = staticmethod(tr)
        cls.actions = AppActions()
        cls.menu_bar = AppMenuBar(cls.actions)
        cls.toolbar = AppToolBar(cls.actions)

    @staticmethod
    def texts(widget):
        return [a.text() for a in widget.actions() if not a.isSeparator()]

    def record(self, signal):
        received = []
        signal.connect(lambda *args: received.append(args))
        return received

    def test_kofi_button_is_the_last_widget_of_the_toolbar(self):
        from unittest import mock
        from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeButton
        from laser_studio.ui.buy_me_a_coffee import button as button_module
        last = self.toolbar.widgetForAction(self.toolbar.actions()[-1])
        self.assertIsInstance(last, BuyMeACoffeeButton)
        self.assertEqual(last.toolTip(), self.tr("ui.support_button_tooltip"))
        with mock.patch.object(button_module.QDesktopServices, "openUrl") as open_url:
            last.click()
        self.assertEqual(open_url.call_args[0][0].toString(), button_module.KOFI_URL)

    def test_menu_bar_order_is_file_settings_view_tools_help(self):
        tr = self.tr
        self.assertEqual(self.texts(self.menu_bar),
                         [tr("menu.file"), tr("menu.settings"), tr("menu.view"), tr("menu.tools"),
                          tr("menu.help")])

    def test_view_menu_toggles_the_gcode_console(self):
        from laser_studio.ui.app.menu import AppActions, AppMenuBar
        a = AppActions()                                 # instance neuve : état de départ
        menu_bar = AppMenuBar(a)
        self.assertEqual(menu_bar.view_menu.actions(), [a.gcode_console, a.job_queue])
        self.assertTrue(a.gcode_console.isCheckable())
        self.assertFalse(a.gcode_console.isChecked())    # console masquée au démarrage
        received = self.record(a.gcode_console_toggled)
        a.gcode_console.trigger()
        a.gcode_console.trigger()
        self.assertEqual(received, [(True,), (False,)])

    def test_fullscreen_sits_just_before_kofi(self):
        from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeButton
        entries = self.toolbar.actions()
        index = entries.index(self.actions.fullscreen)
        self.assertIsInstance(self.toolbar.widgetForAction(entries[index + 1]), BuyMeACoffeeButton)
        self.assertEqual(self.actions.fullscreen.shortcut().toString(), "F11")
        received = self.record(self.actions.fullscreen_requested)
        self.actions.fullscreen.trigger()
        self.assertEqual(received, [()])

    def test_tool_icons_come_from_the_bundled_pack(self):
        a = self.actions
        for action in (*a.tool_actions, *a.vector_tool_actions, a.fullscreen):
            self.assertFalse(action.icon().isNull(), action.text())

    def test_file_menu_order(self):
        tr, fm = self.tr, self.menu_bar.file_menu
        self.assertEqual(self.texts(fm), [tr("menu.file.save_project"), tr("menu.file.open_project"),
                                          tr("menu.file.recent_projects"), tr("gcode.import"),
                                          tr("menu.file.save_gcode"), tr("menu.file.quit")])
        received = self.record(self.actions.gcode_import_requested)
        self.actions.gcode_import.trigger()
        self.assertEqual(received, [()])

    def test_job_queue_toggle_in_view_menu_and_toolbar(self):
        a = self.actions
        self.assertIn(a.job_queue, self.toolbar.actions())
        self.assertEqual(a.job_queue.text(), self.tr("menu.view.job_queue"))
        self.assertTrue(a.job_queue.isCheckable())
        received = self.record(a.job_queue_toggled)
        a.job_queue.setChecked(True)
        a.job_queue.setChecked(False)
        self.assertEqual(received, [(True,), (False,)])

    def test_save_gcode_submenu_is_enabled_after_generation(self):
        from laser_studio.ui.app.menu import AppActions, AppMenuBar
        a = AppActions()
        menu_bar = AppMenuBar(a)                         # gardé : sinon ses menus sont détruits
        submenu = menu_bar.file_menu.gcode_export_menu
        self.assertEqual(submenu.title(), self.tr("menu.file.save_gcode"))
        self.assertEqual(self.texts(submenu), [".gcode", ".nc", ".gc"])
        self.assertFalse(submenu.isEnabled())
        self.assertFalse(any(x.isEnabled() for x in submenu.actions()))
        a.set_gcode_export_enabled(True)
        self.assertTrue(submenu.isEnabled())
        received = self.record(a.gcode_export_requested)
        for action in submenu.actions():
            action.trigger()
        self.assertEqual(received, [(".gcode",), (".nc",), (".gc",)])

    def test_settings_and_tools_entries_are_in_their_menu(self):
        tr = self.tr
        settings = self.texts(self.menu_bar.settings_menu)
        self.assertEqual(settings, [tr("tab.machine_params"), tr("tab.grbl_config"),
                                    tr("menu.language"), tr("menu.theme")])
        self.assertEqual(self.texts(self.menu_bar.tools_menu),
                         [tr("tab.test_matrix"), tr("menu.tools.stencil_studio"), tr("sep.tab_title"),
                          tr("png2svg.tab_title"), tr("menu.tools.camera"), tr("menu.tools.library"),
                          tr("menu.tools.import_vector"), tr("menu.tools.box"),
                          tr("menu.tools.puzzle"), tr("menu.tools.ornament"), tr("menu.tools.keychain")])

    def test_toolbar_reuses_the_menu_actions(self):
        # Mêmes QAction que le menu : icône, libellé, raccourci et état identiques.
        a = self.actions
        in_toolbar = set(self.toolbar.actions())
        for action in (a.quit, a.save_project, a.open_project, a.machine_params_window,
                       a.grbl_window, *a.tool_actions, *a.vector_tool_actions):
            self.assertIn(action, in_toolbar, action.text())
        # Le menu Outils, sans séparateur, est repris en entier dans la barre.
        tools = self.menu_bar.tools_menu.actions()
        self.assertFalse(any(x.isSeparator() for x in tools))
        self.assertTrue(set(tools) <= in_toolbar)
        self.assertIn(a.save_project, self.menu_bar.file_menu.actions())

    def test_toolbar_order_image_and_gcode(self):
        from PyQt6.QtWidgets import QWidgetAction
        a = self.actions
        entries = [x for x in self.toolbar.actions() if not x.isSeparator()]
        widgets = [x for x in entries if isinstance(x, QWidgetAction)]
        order = [entries.index(x) for x in (a.quit, a.save_project, a.png2svg_tab, a.estimate)]
        order += [entries.index(widgets[0])]
        self.assertEqual(order, sorted(order))
        # Actions sur l'image : barre flottante des aperçus d'image.
        for action in (a.image_undo, a.image_redo, a.image_rotate_left, a.image_rotate_right,
                       a.mirror_h, a.mirror_v, a.image_reset, a.image_delete):
            self.assertNotIn(action, entries, action.text())
        self.assertNotIn(a.gcode_import, entries)          # passé dans le menu Fichier
        self.assertEqual(widgets[0].defaultWidget().text(), self.tr("gcode.generate"))
        # La connexion au graveur est passée dans le panneau machine.
        self.assertFalse(hasattr(self.toolbar, "ports_combo"))

    def test_image_actions_are_disabled_until_an_image_is_shown(self):
        from laser_studio.ui.app.menu import AppActions
        a = AppActions()                                 # instance neuve : état de départ
        for action in (*a.image_actions, a.mirror_h, a.mirror_v):
            self.assertFalse(action.isEnabled(), action.text())
        a.set_image_actions_enabled(True)
        a.set_mirrors_enabled(True)
        self.assertTrue(all(x.isEnabled() for x in (*a.image_actions, a.mirror_h, a.mirror_v)))

    def test_mirror_changed_gives_both_mirrors(self):
        a = self.actions
        received = self.record(a.mirror_changed)
        a.mirror_h.setChecked(True)
        a.mirror_v.setChecked(True)
        a.mirror_h.setChecked(False)
        a.mirror_v.setChecked(False)
        self.assertEqual(received, [(True, False), (True, True), (False, True), (False, False)])

    def test_actions_emit_their_signal(self):
        a = self.actions
        for action, signal, expected in (
                (a.save_project, a.save_project_requested, ()),
                (a.open_project, a.open_project_requested, ()),
                (a.quit, a.quit_requested, ()),
                (a.grbl_window, a.settings_window_requested, ("grbl",)),
                (a.test_matrix_window, a.settings_window_requested, ("test_matrix",)),
                (a.separation_tab, a.main_tab_requested, ("tab_separation",)),
                (a.language_actions["en"], a.language_selected, ("en",)),
                (a.theme_actions["light"], a.theme_selected, ("light",)),
                (a.image_rotate_right, a.image_rotate_requested, (True,)),
                (a.vector_import, a.vector_import_requested, ()),
                (a.box_generator, a.box_generator_requested, ()),
                (a.puzzle_generator, a.puzzle_generator_requested, ()),
                (a.ornament_generator, a.ornament_generator_requested, ())):
            received = self.record(signal)
            action.setEnabled(True)
            action.trigger()
            self.assertEqual(received, [expected], action.text())

    def test_recent_projects(self):
        a, file_menu = self.actions, self.menu_bar.file_menu
        file_menu.set_recent_projects([])
        empty = file_menu.recent_projects_menu.actions()
        self.assertEqual([(x.text(), x.isEnabled()) for x in empty], [(self.tr("project.no_recent"), False)])
        file_menu.set_recent_projects(["/tmp/projets/plaque.lsp"])
        (entry,) = file_menu.recent_projects_menu.actions()
        self.assertEqual((entry.text(), entry.toolTip()), ("plaque.lsp", "/tmp/projets/plaque.lsp"))
        received = self.record(a.recent_project_requested)
        entry.trigger()
        self.assertEqual(received, [("/tmp/projets/plaque.lsp",)])



class MenuStructureTests(unittest.TestCase):
    def test_image_settings_buttons_left_the_image_tab(self):
        src = ui_source()
        # Plus aucun bouton dans l'onglet Image & Filtres : seul l'aiguillage les appelle.
        for call in ("image.rotate_left", "image.rotate_right", "clear=image.clear,"):
            self.assertEqual(src.count(call), 1, call)
        # (la boîte de saisie d'un texte, dans l'éditeur vectoriel, a ses propres cases miroir)
        image_src = "\n".join(read(name) for name in ui_files() if not name.startswith(os.path.join("ui", "vector_editor")))
        self.assertNotIn("chk_mirror", image_src)
        # Annuler / refaire ont quitté l'onglet Image & Filtres (raccourcis conservés) ; réinitialiser
        # et la connexion restent aussi sur leur page.
        self.assertEqual(src.count('tr("ui.img_undo")'), 1)
        self.assertEqual(src.count('tr("ui.img_redo")'), 1)
        self.assertIn("self._shortcut(QKeySequence.StandardKey.Undo, self.undo_requested)", src)
        self.assertIn("settings.undo_requested.connect(image_history.undo)", src)
        self.assertNotIn('QPushButton(tr("img.reset"))', src)      # seul celui de la barre d'outils reste
        self.assertNotIn("MachineProfilesPage", src)            # fenêtre Matériaux et connexion supprimée
        for key in ("gcode.estimate", "gcode.generate", "gcode.import"):   # plus dans la colonne de gauche
            self.assertEqual(src.count(f'tr("{key}")'), 1, key)

    def test_separation_vectorization_and_console_tabs_are_hidden_at_startup(self):
        src = ui_source()
        self.assertIn("for tab in (self.tab_separation, self.tab_png2svg, self.tab_console_gcode):\n"
                      "            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)", src)

    def test_tab_toolbars_share_one_builder(self):
        src = ui_source()
        builder = read(os.path.join("ui", "widgets", "tab_toolbar.py"))
        order = [builder.index(k) for k in ("left_actions:", "self._spacer()", "right_widgets:")]
        self.assertEqual(order, sorted(order))             # actions à gauche, widgets à droite
        for name in ("fullscreen_action", "fullscreen_requested"):      # plus de plein écran par onglet
            self.assertNotIn(name, builder)
        image_tab = read(os.path.join("ui", "tabs", "image", "tab.py"))
        previews = image_tab[image_tab.index("compare_icon = QIcon.fromTheme"):image_tab.index("return toolbar")]
        self.assertIn('tr("img.compare_algos_tip")', previews)
        self.assertEqual(src.count("compare=controller.show_dither_comparison"), 1)   # plus dans Image & Filtres
        uses = src.count(" = TabToolBar(")             # src : toute l'interface, onglet Séparation compris
        self.assertEqual(uses, 1)                          # seule « Graver une image » garde un bandeau
        self.assertEqual(src.count("._fullscreen_control"), 0)

    def test_one_fullscreen_button_for_every_tab(self):
        # Un seul « Plein écran », dans la barre principale à côté de ko-fi, pour l'onglet affiché.
        src = read(os.path.join("ui", "app", "main_window.py"))
        tabs = read(os.path.join("ui", "app", "tabs.py"))
        body = tabs[tabs.index("def toggle_current_fullscreen"):]
        body = body[:body.index("\n    def ", 10)]
        for call in ("self.open_vector_editor_fullscreen()", 'tr("png2svg.fullscreen_title")',
                     "self.open_fullscreen(", "self._restore_close_button(tab)"):
            self.assertIn(call, body)
        self.assertIn("actions.fullscreen_requested.connect(w.tabs.toggle_current_fullscreen)",
                      read(os.path.join("ui", "app", "window_controller.py")))
        self.assertNotIn("fullscreen_requested.connect", src)          # plus de bouton par onglet

    def test_preview_options_are_in_the_2d_floating_toolbar(self):
        src = ui_source()
        tab = read(os.path.join("ui", "tabs", "preview_2d", "tab.py"))
        bar = tab[tab.index("self.options_toolbar = FloatingToolBar("):]
        bar = bar[:bar.index("self.plot_widget,")]
        for check in ("flip_check", "negative_check", "hide_rapid_check", "optimize_path_check"):
            self.assertIn(f"self.{check}", bar, check)
        # Les options d'affichage sont lues par l'onglet lui-même ; « Optimiser le chemin » par le job.
        self.assertEqual(src.count("self.tab_vector_2d.optimize_path_check.isChecked()"), 1)
        self.assertNotIn("left_bottom_layout.addWidget(self.chk_", src)

    def test_generate_shows_the_2d_tab_as_soon_as_it_starts(self):
        job = read(os.path.join("controllers", "job.py"))
        start = job[:job.index("        self.worker.start()")]
        self.assertTrue(start.rstrip().endswith("self.started.emit()"))
        main = read(os.path.join("ui", "app", "main_window.py"))
        self.assertIn("self.job.started.connect(display.generation_started)", main)
        self.assertIn("show_preview=lambda: self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)", main)
        view = read(os.path.join("ui", "app", "job_display.py"))
        view = view[view.index("def generation_started"):]
        view = view[:view.index("\n    def ")]
        self.assertTrue(view.rstrip().endswith("self._show_preview()"))

    def test_machine_panel_scrolls_instead_of_being_crushed(self):
        src = ui_source()
        self.assertIn("center_bottom_scroll.setWidget(self.machine_panel)", src)
        self.assertIn("self.center_v_splitter.addWidget(center_bottom_scroll)", src)
        self.assertIn("self.center_bottom_widget = center_bottom_scroll", src)

    def test_original_image_is_hidden_in_the_image_tab(self):
        src = ui_source()
        self.assertIn("self._source_box.setVisible(False)", src)
        self.assertIn("left_widgets=[self.show_original_check]", src)      # case « Afficher l'originale »

    def test_sent_gcode_is_followed_in_the_machine_panel(self):
        self.assertNotIn("SentGcodeLog()", read(os.path.join("ui", "tabs", "job_queue", "tab.py")))
        self.assertIn("self.text_edit.setReadOnly(True)",
                      read(os.path.join("ui", "machine", "sent_gcode", "log.py")))
        # Un seul lanceur d'envoi (direct et file) : chaque ligne envoyée s'ajoute au suivi.
        self.assertIn("c.stream_lines_sent.connect(panel.sent_gcode_log.append_lines)",
                      read(os.path.join("ui", "app", "job_display.py")))
        self.assertIn("self.streamer.lines_sent.connect(self.stream_lines_sent)",
                      read(os.path.join("controllers", "machine_connection.py")))
        self.assertIn("sent_log=self.machine_panel.sent_gcode_log", ui_source())
        self.assertIn("start_stream=engraver.start_stream", ui_source())

    def test_load_button_and_keep_ratio_span_the_panel(self):
        src = ui_source()
        self.assertIn("layout.addRow(load_button)", src)
        self.assertIn("layout.addRow(self.keep_ratio_check)", src)

    def test_load_image_button_is_on_two_lines(self):
        from laser_studio.i18n import TRANSLATIONS
        for lang, text in TRANSLATIONS["img.load"].items():
            self.assertEqual(text.count("\n"), 1, lang)

    def test_resolution_stack_does_not_stretch(self):
        src = ui_source()
        self.assertIn("self.stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)",
                      read(os.path.join("ui", "tabs", "image", "resolution_box.py")).replace("(\n            ", "(").replace(",\n            ", ", ").replace("\n        )", ")"))

    def test_pages_are_no_longer_tabs_of_the_left_column(self):
        src = ui_source()
        self.assertNotIn("tabs.addTab(tab_mach,", src)
        self.assertNotIn("tabs.addTab(tab_gcode_cfg,", src)
        self.assertIn("self.tab_grbl_config = build_grbl_config_page(", src)

    def test_machine_params_and_test_matrix_are_no_longer_tabs_either(self):
        src = ui_source()
        self.assertNotIn('tabs.addTab(tab_machine_params', src)
        self.assertNotIn('tabs.addTab(tab_matrix', src)
        self.assertIn("self.tab_machine_params, self.machines = build_machine_params_page(", src)
        self.assertIn("self.tab_matrix, self.matrix_image = build_test_matrix_page(", src)

    def test_other_tabs_are_still_there(self):
        src = ui_source()
        # Image & Filtres, taille et offset de l'image : panneau de gauche de « Graver une image » ;
        # ancrage : cadre « Position du job », dans l'onglet Visualisation 2D ; Calques : onglet central.
        self.assertIn('layout.addRow(tr("dim.width"), self.width_spin)', src)
        self.assertIn("self.tab_previews.settings.size_mm()", src)
        self.assertIn("layout.addWidget(self.job_position_box)", src)
        self.assertIn('layout.addRow(tr("dim.origin"), self.origin_combo)', src)
        self.assertIn('"origin_pos": w.job_position_box.origin()', src)   # code, pas le libellé traduit
        for widget in ("self.offset_x_spin", "self.offset_y_spin"):
            self.assertRegex(src, rf"layout\.addRow\(tr\(\"[a-z_.]+\"\), {re.escape(widget)}\)")
        self.assertNotIn('tr("tab.dimensions")', src)
        self.assertIn("self._settings_scroll = self._side_scroll(self.settings)", src)
        self.assertNotIn('tr("tab.image_filters")', src)
        self.assertIn('tabs.addTab(self.tab_vector_editor, tr("ui.tab_vector_editor"))', src)
        self.assertIn('tabs.addTab(self.tab_vector_2d, tr("ui.tab_2d_preview"))', src)
        order = [src.index(k) for k in ('tabs.addTab(self.tab_vector_editor, tr("ui.tab_vector_editor"))',
                                         'tabs.addTab(self.layers_tab, tr("tab.layers"))',
                                         'tabs.addTab(self.tab_vector_2d, tr("ui.tab_2d_preview"))')]
        self.assertEqual(order, sorted(order))


def fake_qsettings(stored):
    """Faux QSettings : pas de vrais réglages touchés."""
    fake = mock.Mock()
    fake.return_value.setValue.side_effect = stored.__setitem__
    fake.return_value.value.side_effect = lambda key, default=None: stored.get(key, default)
    return fake


class ShowWindowTests(unittest.TestCase):
    """WindowController : fenêtres de réglages, onglets demandés par le menu."""

    def setUp(self):
        try:
            self.mod = importlib.import_module("laser_studio.ui.app.window_controller")
        except ImportError:
            self.skipTest("window_controller non importable ici")

    def make(self, with_pages=True):
        # Sans __init__ : la fenêtre est un simple espace de noms, pas un QObject.
        controller = self.mod.WindowController.__new__(self.mod.WindowController)
        controller.window = types.SimpleNamespace(tabs=mock.Mock())
        controller._settings_windows = {}
        if with_pages:
            controller.window.tab_machine_params = object()
            controller.window.tab_grbl_config = object()
        return controller

    class Recorder:
        created = []

        def __init__(self, parent, title, page, key, *a, **k):
            self.args = (title, page, key)
            self.fronted = 0
            type(self).created.append(self)

        def bring_to_front(self):
            self.fronted += 1

    def test_window_is_created_once_and_reused(self):
        self.Recorder.created = []
        obj = self.make()
        with mock.patch.object(self.mod, "SettingsWindow", self.Recorder):
            obj.show_settings_window("machine_params")
            obj.show_settings_window("machine_params")
            obj.show_settings_window("grbl")
        self.assertEqual(len(self.Recorder.created), 2)
        machine, grbl = self.Recorder.created
        self.assertEqual(machine.fronted, 2)
        self.assertEqual(grbl.fronted, 1)
        self.assertIs(machine.args[1], obj.window.tab_machine_params)
        self.assertIs(grbl.args[1], obj.window.tab_grbl_config)
        self.assertEqual((machine.args[2], grbl.args[2]), ("machine_params", "grbl"))

    def test_all_three_menu_windows_are_wired_to_their_pages(self):
        self.Recorder.created = []
        obj = self.make()
        obj.window.tab_machine_params, obj.window.tab_matrix = object(), object()
        with mock.patch.object(self.mod, "SettingsWindow", self.Recorder):
            for kind in ("machine_params", "grbl", "test_matrix"):
                obj.show_settings_window(kind)
        pages = {w.args[2]: w.args[1] for w in self.Recorder.created}
        self.assertEqual(sorted(pages), ["grbl", "machine_params", "test_matrix"])
        self.assertIs(pages["machine_params"], obj.window.tab_machine_params)
        self.assertIs(pages["test_matrix"], obj.window.tab_matrix)

    def test_missing_page_is_ignored(self):
        self.Recorder.created = []
        obj = self.make(with_pages=False)
        with mock.patch.object(self.mod, "SettingsWindow", self.Recorder):
            obj.show_settings_window("grbl")
        self.assertEqual(self.Recorder.created, [])

    def test_vector_tools_open_the_vector_editor_first(self):
        obj = self.make()
        obj.window.tab_vector_editor = object()
        calls = []
        obj.window.tabs.show = lambda tab: calls.append(tab)
        obj.run_in_vector_editor(lambda: calls.append("puzzle"))
        self.assertEqual(calls, [obj.window.tab_vector_editor, "puzzle"])

    def test_menu_shows_a_tab_by_its_name(self):
        obj = self.make()
        obj.window.tab_separation = object()
        obj.show_main_tab("tab_separation")
        obj.window.tabs.show.assert_called_once_with(obj.window.tab_separation)
        obj.show_main_tab("tab_inconnu")                       # ignoré
        self.assertEqual(obj.window.tabs.show.call_count, 1)

    def test_dithering_algorithm_is_remembered(self):
        module = importlib.import_module("laser_studio.controllers.image")
        stored = {}
        obj = types.SimpleNamespace(image_settings=mock.Mock())
        controller = module.ImageController
        with mock.patch.object(module, "QSettings", fake_qsettings(stored)):
            controller.restore_remembered_algorithm(obj)
            obj.image_settings.update.assert_not_called()            # rien de mémorisé : défaut
            controller.remember_algorithm(obj, "Atkinson")
            controller.restore_remembered_algorithm(obj)
            obj.image_settings.update.assert_called_once_with(algorithm="Atkinson")
            stored[module.ALGORITHM_SETTING] = "Algorithme disparu"   # plus dans la liste : ignoré
            controller.restore_remembered_algorithm(obj)
            self.assertEqual(obj.image_settings.update.call_count, 1)
            obj.remember_algorithm = lambda name: controller.remember_algorithm(obj, name)
            controller.choose_algorithm(obj, "Stucki")               # choix dans la comparaison : mémorisé
            self.assertEqual(stored[module.ALGORITHM_SETTING], "Stucki")
        src = read(os.path.join("ui", "app", "main_window.py"))
        self.assertIn("settings.algorithm_combo.textActivated.connect(image.remember_algorithm)",
                      read(os.path.join("ui", "tabs", "image", "builder.py")))
        self.assertIn("self.image.restore_remembered_algorithm()", src)
        self.assertIn("dialog.algorithm_chosen.connect(image.choose_algorithm)",
                      read(os.path.join("ui", "app", "window_controller.py")))


class ImageToolbarActionsTests(unittest.TestCase):
    """Pivoter / supprimer / miroirs : l'image de l'onglet affiché (ImageToolbarActions)."""

    def setUp(self):
        try:
            from laser_studio.ui.app.image_actions import ImageToolbarActions
            from job_fakes import FakeDialogs
        except ImportError:
            self.skipTest("PyQt6 non importable ici")
        self.current = None
        self.dialogs = FakeDialogs()
        self.app_actions = mock.Mock()
        self.actions = ImageToolbarActions(self.app_actions, current_tab=lambda: self.current, dialogs=self.dialogs)
        self.previews, self.png2svg, self.separation = object(), object(), object()
        self.image, self.converter, self.sep = mock.Mock(), mock.Mock(), mock.Mock()
        self.image.has_image.return_value = False
        self.sep.has_image.return_value = False
        self.converter.image_path = None
        # Comme main_window : chaque onglet d'image s'inscrit.
        self.actions.add(self.previews, has_image=self.image.has_image,
                         rotate=lambda cw: (self.image.rotate_right if cw else self.image.rotate_left)(),
                         clear=self.image.clear, confirm_clear=False)
        self.actions.add(self.png2svg, has_image=lambda: bool(self.converter.image_path),
                         rotate=lambda cw: self.converter.rotate_image(90 if cw else -90),
                         clear=self.converter.clear_image, mirrors=False)
        self.actions.add(self.separation, has_image=self.sep.has_image,
                         rotate=lambda cw: self.sep.rotate_image(-90 if cw else 90), clear=self.sep.clear)

    def assert_enabled(self, tab, image_actions, mirrors):
        self.current = tab
        self.actions.update_state()
        self.app_actions.set_image_actions_enabled.assert_called_with(image_actions)
        self.app_actions.set_mirrors_enabled.assert_called_with(mirrors)

    def test_image_actions_need_an_image_on_the_current_tab(self):
        for tab in (self.previews, self.png2svg, self.separation, object()):
            self.assert_enabled(tab, False, False)
        self.image.has_image.return_value = True
        self.assert_enabled(self.previews, True, True)
        self.assert_enabled(self.separation, False, False)   # l'image d'un autre onglet ne compte pas
        self.assert_enabled(object(), False, False)
        self.sep.has_image.return_value = True
        self.assert_enabled(self.separation, True, True)
        self.converter.image_path = "/tmp/a.png"
        self.assert_enabled(self.png2svg, True, False)       # pas de miroir de gravure en PNG ⇒ SVG

    def test_toolbar_rotation_targets_the_current_tab(self):
        self.current = self.previews
        self.actions.rotate(True)
        self.image.rotate_right.assert_called_once()
        self.current = self.png2svg
        self.actions.rotate(True)
        self.converter.rotate_image.assert_called_once_with(90)
        self.current = self.separation
        self.actions.rotate(True)
        self.sep.rotate_image.assert_called_once_with(-90)     # PIL : positif = antihoraire
        self.current = object()
        self.actions.rotate(True)                              # onglet sans image : rien
        self.image.rotate_left.assert_not_called()

    def test_delete_asks_first_except_where_the_tab_asks_itself(self):
        self.current = self.previews
        self.actions.delete()
        self.image.clear.assert_called_once()
        self.assertEqual(self.dialogs.kinds(), [])             # ImageController.clear demande lui-même
        self.current = self.separation
        self.dialogs.answer = False
        self.actions.delete()
        self.sep.clear.assert_not_called()
        self.dialogs.answer = True
        self.actions.delete()
        self.sep.clear.assert_called_once()
        self.assertEqual(self.dialogs.kinds(), ["confirm_yes_no", "confirm_yes_no"])


class MainTabsTests(unittest.TestCase):
    """Onglets du centre (MainTabs) : affichage, onglets facultatifs, plein écran, séparateurs."""

    def setUp(self):
        try:
            self.mod = importlib.import_module("laser_studio.ui.app.tabs")
        except ImportError:
            self.skipTest("PyQt6 non importable ici")
        self.view = mock.Mock()
        self.view.indexOf.return_value = -1                    # pas de croix à poser pendant les tests
        self.vector_editor, self.png2svg = object(), object()
        self.preview_splitter = mock.Mock()
        self.tabs = self.mod.MainTabs(
            self.view, mock.Mock(), splitter=mock.Mock(), bottom_panel=mock.Mock(isHidden=lambda: False),
            panel_tabs=(), preview_splitter=self.preview_splitter, job_in_progress=lambda: False,
            vector_editor=self.vector_editor, recenter_vector_editor=lambda: None, png2svg=self.png2svg)

    def test_show_selects_or_raises_the_fullscreen_window(self):
        tab = mock.Mock()
        self.view.indexOf.return_value = 3
        self.tabs.show(tab)
        self.view.setTabVisible.assert_called_once_with(3, True)    # masqué au démarrage
        self.view.setCurrentWidget.assert_called_once_with(tab)
        self.view.indexOf.return_value = -1                    # onglet ouvert en plein écran
        self.tabs.show(tab)
        tab.window().raise_.assert_called_once()

    def test_job_queue_visibility_is_remembered_and_shown_by_default(self):
        queue = object()
        self.tabs.add_optional(queue, self.mod.JOB_QUEUE_SETTING, mock.Mock())
        self.view.indexOf.return_value = 3
        stored = {}
        with mock.patch.object(self.mod, "QSettings", fake_qsettings(stored)):
            self.assertTrue(self.mod.optional_tab_was_visible(self.mod.JOB_QUEUE_SETTING))   # affichée au départ
            self.tabs.set_optional_visible(queue, True)
            self.assertEqual(stored, {})                          # inchangé : rien d'écrit
            self.tabs.set_optional_visible(queue, False)
            self.view.setTabVisible.assert_called_with(3, False)
            self.assertEqual(stored, {"show_job_queue": False})
            self.assertFalse(self.mod.optional_tab_was_visible(self.mod.JOB_QUEUE_SETTING))

    def test_gcode_console_visibility_is_remembered(self):
        console, action = object(), mock.Mock()
        self.tabs.add_optional(console, self.mod.GCODE_CONSOLE_SETTING, action)
        stored = {}
        with mock.patch.object(self.mod, "QSettings", fake_qsettings(stored)):
            self.tabs.restore_optional_tabs()
            action.setChecked.assert_called_once_with(False)     # masquée la première fois
            self.view.indexOf.return_value = 7
            self.tabs.set_optional_visible(console, True)
            self.view.setTabVisible.assert_called_with(7, True)
            self.assertTrue(self.mod.optional_tab_was_visible(self.mod.GCODE_CONSOLE_SETTING))
            self.view.indexOf.return_value = -1                  # en plein écran : onglet pas touché
            self.view.setTabVisible.reset_mock()
            self.tabs.set_optional_visible(console, False)
            self.view.setTabVisible.assert_not_called()
            self.assertFalse(self.mod.optional_tab_was_visible(self.mod.GCODE_CONSOLE_SETTING))

    def test_current_tab_fullscreen_dispatch(self):
        calls = []
        self.tabs.open_vector_editor_fullscreen = lambda: calls.append("vectoriel")
        self.tabs.open_fullscreen = lambda tab, title, close, tab_title, on_restored=None: calls.append(title)
        self.view.tabText.return_value = "Visualisation 2D"
        for tab in (self.vector_editor, self.png2svg, object()):
            self.view.currentWidget.return_value = tab
            self.tabs.toggle_current_fullscreen()
        from laser_studio.i18n import tr
        self.assertEqual(calls, ["vectoriel", tr("png2svg.fullscreen_title"), "Visualisation 2D"])

    def test_preview_2d_splitter_position_is_remembered(self):
        stored = {}
        self.preview_splitter.sizes.return_value = [900, 0]  # statistiques repliées : gardé
        self.tabs.splitter.sizes.return_value = [600, 200]
        with mock.patch.object(self.mod, "QSettings", fake_qsettings(stored)):
            self.tabs.save_splitter_sizes()
            self.assertEqual(stored["preview_2d_side_sizes"], [900, 0])
            self.assertEqual(stored["center_v_splitter_sizes"], [600, 200])
            self.tabs.load_splitter_sizes()
        self.preview_splitter.setSizes.assert_called_once_with([900, 0])
        self.tabs.splitter.setSizes.assert_called_once_with([600, 200])


# --- SettingsWindow avec de faux widgets Qt ---------------------------------------------------
class FakeQt:
    store = {}

    class QSettings:
        def __init__(self, *a):
            pass

        def value(self, key, default=None):
            return FakeQt.store.get(key, default)

        def setValue(self, key, value):
            FakeQt.store[key] = value

    class QDialog:
        def __init__(self, parent=None):
            self.calls = []
            self._geo = b"geo-initial"
            self.restored = None
            self.parent = parent

        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return lambda *a, **k: self.calls.append(name)

        def saveGeometry(self): return self._geo
        def restoreGeometry(self, value): self.restored = value
        def closeEvent(self, event): self.calls.append("super.closeEvent")
        def done(self, result): self.calls.append("super.done")
        def screen(self): raise AttributeError("pas d'écran dans le test")

    class QScrollArea:
        def __init__(self):
            self.widget = None
            self.resizable = None

        def setWidgetResizable(self, flag): self.resizable = flag
        def setWidget(self, w): self.widget = w

    class QVBoxLayout:
        def __init__(self, parent=None):
            self.widgets = []

        def setContentsMargins(self, *a): pass
        def addWidget(self, w): self.widgets.append(w)


def load_window_module():
    fake_core = types.ModuleType("PyQt6.QtCore")
    fake_core.QSettings = FakeQt.QSettings
    fake_widgets = types.ModuleType("PyQt6.QtWidgets")
    fake_widgets.QDialog, fake_widgets.QScrollArea, fake_widgets.QVBoxLayout = FakeQt.QDialog, FakeQt.QScrollArea, FakeQt.QVBoxLayout
    with mock.patch.dict(sys.modules, {"PyQt6.QtCore": fake_core, "PyQt6.QtWidgets": fake_widgets}):
        sys.modules.pop("laser_studio.ui.settings.window", None)
        module = importlib.import_module("laser_studio.ui.settings.window")
    sys.modules.pop("laser_studio.ui.settings.window", None)
    return module


class SettingsWindowTests(unittest.TestCase):
    def setUp(self):
        FakeQt.store = {}
        self.sw = load_window_module()

    def test_page_is_hosted_in_a_scroll_area_and_window_is_not_modal(self):
        page = object()
        w = self.sw.SettingsWindow(None, "Machine & Profils", page, "machine")
        self.assertIs(w.scroll.widget, page)
        self.assertTrue(w.scroll.resizable)
        self.assertIn("setModal", w.calls)
        self.assertIn("setWindowTitle", w.calls)
        self.assertIn("resize", w.calls)            # repli sans écran : taille par défaut

    def test_an_already_scrollable_page_is_not_wrapped_twice(self):
        page = FakeQt.QScrollArea()
        w = self.sw.SettingsWindow(None, "t", page, "machine_params")
        self.assertIs(w.scroll, page)

    def test_geometry_is_saved_on_close_and_restored_next_time(self):
        w = self.sw.SettingsWindow(None, "t", object(), "grbl")
        self.assertIsNone(w.restored)               # rien de mémorisé la première fois
        w._geo = b"geo-utilisateur"
        w.closeEvent(object())
        self.assertEqual(FakeQt.store["settings_window/grbl/geometry"], b"geo-utilisateur")
        w2 = self.sw.SettingsWindow(None, "t", object(), "grbl")
        self.assertEqual(w2.restored, b"geo-utilisateur")
        other = self.sw.SettingsWindow(None, "t", object(), "machine")
        self.assertIsNone(other.restored)           # clé propre à chaque fenêtre

    def test_done_also_saves_the_geometry(self):
        w = self.sw.SettingsWindow(None, "t", object(), "machine")
        w._geo = b"x"
        w.done(0)
        self.assertEqual(FakeQt.store["settings_window/machine/geometry"], b"x")

    def test_bring_to_front(self):
        w = self.sw.SettingsWindow(None, "t", object(), "machine")
        w.calls.clear()
        w.bring_to_front()
        self.assertEqual(w.calls, ["show", "raise_", "activateWindow"])


if __name__ == "__main__":
    unittest.main()