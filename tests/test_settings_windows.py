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


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


class MenuStructureTests(unittest.TestCase):
    def test_menu_bar_order_is_file_settings_tools(self):
        src = read("ui_setup_mixin.py")
        body = src[src.index("def _build_menu_bar"):src.index("menu_aide = menu_bar.addMenu")]
        order = [body.index(k) for k in ('tr("menu.file")', 'tr("menu.settings")', 'tr("tab.machine_params")',
                                         'tr("tab.machine_profiles")', 'tr("tab.grbl_config")', 'tr("menu.language")',
                                         'tr("menu.tools")', 'tr("tab.test_matrix")', 'tr("menu.tools.stencil_studio")')]
        self.assertEqual(order, sorted(order))

    def test_settings_and_tools_entries_are_in_their_menu_not_the_bar(self):
        src = read("ui_setup_mixin.py")
        body = src[src.index("def _build_menu_bar"):src.index("menu_aide = menu_bar.addMenu")]
        def added_to(menu, method, key):
            # Appel menu.method(...) dont le dernier argument est tr(key), icône éventuelle avant.
            call = rf'{re.escape(menu)}\.{method}\((?:[^()]|\([^()]*(?:\([^()]*\))?[^()]*\))*tr\("{re.escape(key)}"\)\)'
            self.assertRegex(body, call)

        added_to("menu_parametres", "addAction", "tab.machine_params")
        added_to("menu_parametres", "addAction", "tab.machine_profiles")
        added_to("menu_parametres", "addAction", "tab.grbl_config")
        added_to("menu_parametres", "addMenu", "menu.language")
        added_to("self.tools_menu", "addAction", "tab.test_matrix")
        added_to("self.tools_menu", "addAction", "menu.tools.stencil_studio")
        self.assertNotIn("menu_bar.addAction(", body)

    def test_pages_are_no_longer_tabs_of_the_left_column(self):
        src = read("ui_setup_mixin.py")
        self.assertNotIn("tabs.addTab(tab_mach,", src)
        self.assertNotIn("tabs.addTab(tab_gcode_cfg,", src)
        self.assertIn("self.tab_machine_profiles = tab_mach", src)
        self.assertIn("self.tab_grbl_config = tab_gcode_cfg", src)

    def test_machine_params_and_test_matrix_are_no_longer_tabs_either(self):
        src = read("ui_setup_mixin.py")
        self.assertNotIn('tabs.addTab(tab_machine_params', src)
        self.assertNotIn('tabs.addTab(tab_matrix', src)
        self.assertIn("self.tab_machine_params = tab_machine_params", src)
        self.assertIn("self.tab_matrix = tab_matrix", src)

    def test_other_tabs_are_still_there(self):
        src = read("ui_setup_mixin.py")
        for key in ("tab.image_filters", "tab.dimensions", "tab.layers"):
            self.assertIn(f'tabs.addTab(', src)
            self.assertRegex(src, rf'tabs\.addTab\(\w+, tr\("{re.escape(key)}"\)\)')


class ShowWindowTests(unittest.TestCase):
    def setUp(self):
        try:
            self.mod = importlib.import_module("ui_setup_mixin")
        except ImportError:
            self.skipTest("ui_setup_mixin non importable ici")

    def make(self, with_pages=True):
        cls = next(c for c in vars(self.mod).values() if isinstance(c, type) and c.__name__ == "UiSetupMixin")
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
