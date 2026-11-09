"""Machine & Profils et Configuration GRBL : fenêtres ouvertes depuis la barre de menus."""
import importlib
import os
import re
import sys
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_source  # noqa: E402


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


class AppMenusTests(unittest.TestCase):
    """Menu et barre d'outils (ui/app/menu/) : structure et signaux."""

    @classmethod
    def setUpClass(cls):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.app.menu import AppActions, AppMenuBar, AppToolBar
            from i18n import tr
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

    def test_menu_bar_order_is_file_settings_tools_help(self):
        tr = self.tr
        self.assertEqual(self.texts(self.menu_bar),
                         [tr("menu.file"), tr("menu.settings"), tr("menu.tools"), tr("menu.help")])

    def test_settings_and_tools_entries_are_in_their_menu(self):
        tr = self.tr
        settings = self.texts(self.menu_bar.settings_menu)
        self.assertEqual(settings, [tr("tab.machine_params"), tr("tab.machine_profiles"), tr("tab.grbl_config"),
                                    tr("menu.language"), tr("menu.theme")])
        self.assertEqual(self.texts(self.menu_bar.tools_menu),
                         [tr("tab.test_matrix"), tr("menu.tools.stencil_studio"), tr("sep.tab_title"),
                          tr("png2svg.tab_title")])

    def test_toolbar_reuses_the_menu_actions(self):
        # Mêmes QAction que le menu : icône, libellé, raccourci et état identiques.
        a = self.actions
        in_toolbar = set(self.toolbar.actions())
        for action in (a.quit, a.save_project, a.open_project, a.machine_params_window, a.machine_window,
                       a.grbl_window, *a.tool_actions):
            self.assertIn(action, in_toolbar, action.text())
        self.assertIn(a.save_project, self.menu_bar.file_menu.actions())

    def test_toolbar_order_undo_image_and_connection(self):
        from PyQt6.QtWidgets import QWidgetAction
        a = self.actions
        entries = [x for x in self.toolbar.actions() if not x.isSeparator()]
        widgets = [x for x in entries if isinstance(x, QWidgetAction)]
        order = [entries.index(x) for x in (a.quit, a.save_project, a.png2svg_tab, a.image_undo, a.image_redo,
                                            a.image_delete, a.mirror_v, a.image_reset, a.estimate)]
        order += [entries.index(widgets[0]), entries.index(a.gcode_import), entries.index(widgets[1]),
                  entries.index(a.refresh_ports), entries.index(a.connection)]
        self.assertEqual(order, sorted(order))
        self.assertEqual(widgets[0].defaultWidget().text(), self.tr("gcode.generate"))
        self.assertIs(widgets[1].defaultWidget(), self.toolbar.ports_combo)

    def test_image_actions_are_disabled_until_an_image_is_shown(self):
        from ui.app.menu import AppActions
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
                (a.machine_window, a.settings_window_requested, ("machine",)),
                (a.test_matrix_window, a.settings_window_requested, ("test_matrix",)),
                (a.separation_tab, a.main_tab_requested, ("tab_separation",)),
                (a.language_actions["en"], a.language_selected, ("en",)),
                (a.theme_actions["light"], a.theme_selected, ("light",)),
                (a.image_rotate_right, a.image_rotate_requested, (True,)),
                (a.connection, a.connection_toggle_requested, ())):
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

    def test_connection_state(self):
        a = self.actions
        a.set_connected(True)
        self.assertEqual(a.connection.text(), self.tr("laser.disconnect"))
        a.set_connected(False)
        self.assertEqual(a.connection.text(), self.tr("laser.connect"))


class MenuStructureTests(unittest.TestCase):
    def test_image_settings_buttons_left_the_image_tab(self):
        src = ui_source()
        # Plus aucun bouton dans l'onglet Image & Filtres : seul l'aiguillage les appelle.
        for call in ("self.rotate_image_left", "self.rotate_image_right", "self.clear_image()"):
            self.assertEqual(src.count(call), 1, call)
        self.assertNotIn("chk_mirror", src)
        # Annuler / refaire ont quitté l'onglet Image & Filtres (raccourcis conservés) ; réinitialiser
        # et la connexion restent aussi sur leur page.
        self.assertEqual(src.count('tr("ui.img_undo")'), 1)
        self.assertEqual(src.count('tr("ui.img_redo")'), 1)
        self.assertIn("shortcut_undo_img.activated.connect(self.undo_image_settings)", src)
        self.assertNotIn('QPushButton(tr("img.reset"))', src)      # seul celui de la barre d'outils reste
        self.assertIn("self.combo_ports.setModel(self.main_toolbar.ports_combo.model())", src)
        for key in ("gcode.estimate", "gcode.generate", "gcode.import"):   # plus dans la colonne de gauche
            self.assertEqual(src.count(f'tr("{key}")'), 1, key)

    def test_separation_and_vectorization_tabs_are_hidden_at_startup(self):
        src = ui_source()
        self.assertIn("for tab in (self.tab_separation, self.tab_png2svg):\n"
                      "            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)", src)

    def test_tab_toolbars_share_one_builder(self):
        src = ui_source()
        builder = src[src.index("def _build_tab_toolbar"):src.index("def _fullscreen_icon")]
        order = [builder.index(k) for k in ("left_actions:", "QSizePolicy.Policy.Expanding",
                                            "right_widgets:", 'tr("ui.vector_fullscreen")')]
        self.assertEqual(order, sorted(order))             # actions à gauche, plein écran à droite
        previews = src[src.index("compare_icon = QIcon.fromTheme"):src.index("outer_layout_previews.addWidget(toolbar_previews)")]
        self.assertIn('tr("img.compare_algos_tip")', previews)
        self.assertEqual(src.count("self.compare_dither_algorithms"), 1)   # plus dans Image & Filtres
        uses = src.count("self._build_tab_toolbar(") + read("separation_mixin.py").count("self._build_tab_toolbar(") \
            + read("png2svg_mixin.py").count("self._build_tab_toolbar(")
        self.assertEqual(uses, 5)                          # Images, PNG→SVG, Séparation, 2D, Console

    def test_every_fullscreen_mode_hides_then_restores_its_button(self):
        for name, func in (("ui_setup_mixin.py", "def _toggle_fullscreen_tab"),
                           ("png2svg_mixin.py", "def toggle_fullscreen_png2svg"),
                           ("vector_editing_mixin.py", "def toggle_fullscreen_vector_editor")):
            src = read(name)
            body = src[src.index(func):]
            body = body[:body.index("dialog.finished.connect(restore)")]
            hide = body.index("_show_fullscreen_control(")
            self.assertIn(", False)", body[hide:hide + 80], func)
            restore = body[body.index("def restore"):]
            self.assertIn("_show_fullscreen_control(", restore, func)
            self.assertIn(", True)", restore, func)

    def test_preview_options_are_in_the_2d_tab_toolbar(self):
        src = ui_source()
        bar = src[src.index("toolbar_vector_2d = self._build_tab_toolbar("):]
        bar = bar[:bar.index("right_widgets=")]
        for name in ("chk_flip_raster_preview", "chk_negative_raster_preview",
                     "chk_hide_rapid_moves", "chk_optimize_path"):
            self.assertIn(f"self.{name}", bar, name)
            self.assertEqual(src.count(f"self.{name} = QCheckBox("), 1, name)
        self.assertNotIn("left_bottom_layout.addWidget(self.chk_", src)

    def test_generate_shows_the_2d_tab_as_soon_as_it_starts(self):
        src = read("gcode_generation_mixin.py")
        start = src[:src.index("        self.worker.start()")]
        self.assertTrue(start.rstrip().endswith("self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)"))

    def test_machine_panel_scrolls_instead_of_being_crushed(self):
        src = ui_source()
        self.assertIn("center_bottom_scroll.setWidget(self.machine_panel)", src)
        self.assertIn("self.center_v_splitter.addWidget(center_bottom_scroll)", src)
        self.assertIn("self.center_bottom_widget = center_bottom_scroll", src)

    def test_original_image_is_hidden_in_the_image_tab(self):
        src = ui_source()
        self.assertIn("box_src.setVisible(False)", src)
        self.assertIn("left_widgets=[self.chk_show_original]", src)      # case « Afficher l'originale »

    def test_queue_tab_is_split_with_the_sent_gcode_on_the_right(self):
        src = ui_source()
        block = src[src.index("queue_splitter = QSplitter("):src.index('self.main_tabs_view.addTab(tab_job_queue')]
        self.assertLess(block.index("queue_splitter.addWidget(queue_left)"),
                        block.index("queue_splitter.addWidget(sent_box)"))
        self.assertIn("self.txt_sent_gcode.setReadOnly(True)", block)
        for name in ("job_queue_mixin.py", "laser_control_mixin.py"):
            self.assertIn("self.streamer.lines_sent.connect(self._append_sent_gcode)", read(name), name)

    def test_load_button_and_keep_ratio_span_the_panel(self):
        src = ui_source()
        self.assertIn("layout_img.addRow(btn_img)", src)
        self.assertIn("layout_img.insertRow(3, self.chk_keep_ratio)", src)

    def test_load_image_button_is_on_two_lines(self):
        from i18n import TRANSLATIONS
        for lang, text in TRANSLATIONS["img.load"].items():
            self.assertEqual(text.count("\n"), 1, lang)

    def test_resolution_stack_does_not_stretch(self):
        src = ui_source()
        self.assertIn("self.stack_lmm_input.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)", src)

    def test_pages_are_no_longer_tabs_of_the_left_column(self):
        src = ui_source()
        self.assertNotIn("tabs.addTab(tab_mach,", src)
        self.assertNotIn("tabs.addTab(tab_gcode_cfg,", src)
        self.assertIn("self.tab_machine_profiles = tab_mach", src)
        self.assertIn("self.tab_grbl_config = tab_gcode_cfg", src)

    def test_machine_params_and_test_matrix_are_no_longer_tabs_either(self):
        src = ui_source()
        self.assertNotIn('tabs.addTab(tab_machine_params', src)
        self.assertNotIn('tabs.addTab(tab_matrix', src)
        self.assertIn("self.tab_machine_params = tab_machine_params", src)
        self.assertIn("self.tab_matrix = tab_matrix", src)

    def test_other_tabs_are_still_there(self):
        src = ui_source()
        # Image & Filtres, taille et offset de l'image : panneau de gauche de « Graver une image » ;
        # ancrage : cadre « Position du job » du panneau machine ; Calques : onglet central.
        self.assertIn('layout_img.insertRow(1, tr("dim.width"), self.spin_w)', src)
        self.assertIn("machine_row.addWidget(self.job_position_box", src)
        self.assertRegex(src, r"job_position_layout\.addRow\(tr\(\"[a-z_.]+\"\), self\.combo_origin\)")
        for widget in ("self.spin_off_x", "self.spin_off_y"):
            self.assertRegex(src, rf"layout_img\.insertRow\(\d, tr\(\"[a-z_.]+\"\), {re.escape(widget)}\)")
        self.assertNotIn('tr("tab.dimensions")', src)
        self.assertIn("img_settings_scroll = self._side_settings_panel(self.tab_img)", src)
        self.assertNotIn('tr("tab.image_filters")', src)
        self.assertIn("self.main_tabs_view.addTab(tab_vector_editor", src)
        self.assertIn("self.main_tabs_view.addTab(tab_vector_2d", src)
        order = [src.index(k) for k in ("self._build_vector_editor_tab()",
                                         'self.main_tabs_view.addTab(self.tab_layers, tr("tab.layers"))',
                                         "self._build_2d_preview_tab()")]
        self.assertEqual(order, sorted(order))


class ShowWindowTests(unittest.TestCase):
    def setUp(self):
        try:
            self.mod = importlib.import_module("ui_setup_mixin")
        except ImportError:
            self.skipTest("ui_setup_mixin non importable ici")

    def make(self, with_pages=True):
        cls = next(c for c in vars(self.mod).values() if isinstance(c, type) and c.__name__ == "UiSetupMixin")
        cls = type("Window", (cls, importlib.import_module("ui_window_controller").WindowControllerMixin), {})
        obj = cls.__new__(cls)
        if with_pages:
            obj.tab_machine_profiles = object()
            obj.tab_grbl_config = object()
        return obj

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
            obj.show_settings_window("machine")
            obj.show_settings_window("machine")
            obj.show_settings_window("grbl")
        self.assertEqual(len(self.Recorder.created), 2)
        machine, grbl = self.Recorder.created
        self.assertEqual(machine.fronted, 2)
        self.assertEqual(grbl.fronted, 1)
        self.assertIs(machine.args[1], obj.tab_machine_profiles)
        self.assertIs(grbl.args[1], obj.tab_grbl_config)
        self.assertEqual((machine.args[2], grbl.args[2]), ("machine", "grbl"))

    def test_all_four_menu_windows_are_wired_to_their_pages(self):
        self.Recorder.created = []
        obj = self.make()
        obj.tab_machine_params, obj.tab_matrix = object(), object()
        with mock.patch.object(self.mod, "SettingsWindow", self.Recorder):
            for kind in ("machine_params", "machine", "grbl", "test_matrix"):
                obj.show_settings_window(kind)
        pages = {w.args[2]: w.args[1] for w in self.Recorder.created}
        self.assertEqual(sorted(pages), ["grbl", "machine", "machine_params", "test_matrix"])
        self.assertIs(pages["machine_params"], obj.tab_machine_params)
        self.assertIs(pages["test_matrix"], obj.tab_matrix)

    def image_tabs(self):
        obj = self.make()
        obj.app_actions = mock.Mock()
        obj.tab_previews, obj.tab_png2svg, obj.tab_separation = object(), object(), object()
        obj.main_tabs_view = mock.Mock()
        obj.raw_image = obj.sep_src = None
        obj.png2svg_widget = mock.Mock(image_path=None)
        return obj

    def assert_enabled(self, obj, tab, image_actions, mirrors):
        obj.main_tabs_view.currentWidget.return_value = tab
        obj.update_image_actions_state()
        obj.app_actions.set_image_actions_enabled.assert_called_with(image_actions)
        obj.app_actions.set_mirrors_enabled.assert_called_with(mirrors)

    def test_image_actions_need_an_image_on_the_current_tab(self):
        obj = self.image_tabs()
        for tab in (obj.tab_previews, obj.tab_png2svg, obj.tab_separation, object()):
            self.assert_enabled(obj, tab, False, False)
        obj.raw_image = "img"
        self.assert_enabled(obj, obj.tab_previews, True, True)
        self.assert_enabled(obj, obj.tab_separation, False, False)   # l'image d'un autre onglet ne compte pas
        self.assert_enabled(obj, object(), False, False)
        obj.sep_src = "img"
        self.assert_enabled(obj, obj.tab_separation, True, True)
        obj.png2svg_widget.image_path = "/tmp/a.png"
        self.assert_enabled(obj, obj.tab_png2svg, True, False)       # pas de miroir de gravure en PNG ⇒ SVG

    def test_toolbar_rotation_targets_the_current_tab(self):
        obj = self.image_tabs()
        obj.rotate_image_left, obj.rotate_image_right = mock.Mock(), mock.Mock()
        obj.separation_rotate_image = mock.Mock()
        obj.main_tabs_view.currentWidget.return_value = obj.tab_previews
        obj._on_toolbar_rotate_image(clockwise=True)
        obj.rotate_image_right.assert_called_once()
        obj.main_tabs_view.currentWidget.return_value = obj.tab_png2svg
        obj._on_toolbar_rotate_image(clockwise=True)
        obj.png2svg_widget.rotate_image.assert_called_once_with(90)
        obj.main_tabs_view.currentWidget.return_value = obj.tab_separation
        obj._on_toolbar_rotate_image(clockwise=True)
        obj.separation_rotate_image.assert_called_once_with(-90)     # PIL : positif = antihoraire
        obj.rotate_image_left.assert_not_called()

    def test_connection_widgets_follow_the_port_state(self):
        obj = self.make()
        obj.btn_connect, obj.app_actions = mock.Mock(), mock.Mock()
        for connected, label in ((False, "laser.connect"), (True, "laser.disconnect")):
            obj.usb = mock.Mock(is_connected=lambda c=connected: c)
            obj.update_connection_widgets()
            obj.btn_connect.setText.assert_called_with(self.mod.tr(label))
            obj.app_actions.set_connected.assert_called_with(connected)

    def test_show_fullscreen_control(self):
        tab, control = mock.Mock(), mock.Mock()
        tab._fullscreen_control = control
        self.mod.UiSetupMixin._show_fullscreen_control(tab, False)
        control.setVisible.assert_called_with(False)
        self.mod.UiSetupMixin._show_fullscreen_control(object(), True)   # onglet sans bouton : ignoré

    def test_show_main_tab_selects_or_raises_the_fullscreen_window(self):
        obj = self.make()
        obj.tab_separation = mock.Mock()
        obj.main_tabs_view = mock.Mock()
        obj.main_tabs_view.indexOf.return_value = 3
        obj.show_main_tab("tab_separation")
        obj.main_tabs_view.setTabVisible.assert_called_once_with(3, True)    # masqué au démarrage
        obj.main_tabs_view.setCurrentWidget.assert_called_once_with(obj.tab_separation)
        obj.main_tabs_view.indexOf.return_value = -1            # onglet ouvert en plein écran
        obj.show_main_tab("tab_separation")
        obj.tab_separation.window().raise_.assert_called_once()
        obj.show_main_tab("tab_inconnu")                       # ignoré

    def test_missing_page_is_ignored(self):
        self.Recorder.created = []
        obj = self.make(with_pages=False)
        with mock.patch.object(self.mod, "SettingsWindow", self.Recorder):
            obj.show_settings_window("machine")
        self.assertEqual(self.Recorder.created, [])


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
        sys.modules.pop("settings_window", None)
        module = importlib.import_module("settings_window")
    sys.modules.pop("settings_window", None)
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
