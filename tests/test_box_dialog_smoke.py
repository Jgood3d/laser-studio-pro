"""Fenêtre du générateur de boîte exécutée avec de FAUX widgets Qt : détecte les fautes de frappe,
les attributs manquants et vérifie la logique (paramètres lus, résumé, décor, calques par défaut)."""
import importlib
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class Sig:
    def connect(self, fn):
        pass


class W:
    """Widget factice : toute méthode Qt non définie ici est sans effet."""
    def __init__(self, *a, **k):
        self._text = a[0] if a and isinstance(a[0], str) else ""
        self._enabled = True

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name.endswith(("Changed", "changed", "clicked", "toggled", "accepted", "rejected")):
            return Sig()
        return lambda *a, **k: W()

    def setText(self, t): self._text = t
    def text(self): return self._text
    def setEnabled(self, flag): self._enabled = flag


class Dialog(W):
    def __init__(self, parent=None):
        super().__init__()


class Spin(W):
    def __init__(self, *a, **k):
        super().__init__()
        self._v, self._lo, self._hi = 0.0, -1e9, 1e9

    def setRange(self, lo, hi): self._lo, self._hi = lo, hi
    def setValue(self, v): self._v = min(max(float(v), self._lo), self._hi)
    def value(self): return self._v


class IntSpin(Spin):
    def value(self): return int(self._v)


class Combo(W):
    def __init__(self, *a, **k):
        super().__init__()
        self.items, self._i = [], 0

    def addItem(self, text, data=None): self.items.append((text, data))
    def findData(self, d):
        return next((i for i, it in enumerate(self.items) if it[1] == d), -1)
    def currentIndex(self): return self._i
    def setCurrentIndex(self, i): self._i = max(0, min(i, len(self.items) - 1))
    def currentData(self): return self.items[self._i][1] if self.items else None
    def currentText(self): return self.items[self._i][0] if self.items else ""
    def setSpecialValueText(self, t): pass


class FontCombo(Combo):
    def currentFont(self):
        return types.SimpleNamespace(family=lambda: "DejaVu Sans")


class Check(W):
    def __init__(self, *a, **k):
        super().__init__(*a)
        self._c = False

    def setChecked(self, c): self._c = bool(c)
    def isChecked(self): return self._c


class Line(W):
    pass


class Item(W):
    def __init__(self, text=""):
        super().__init__(text)
        self._data = {}

    def setData(self, role, value): self._data[role] = value
    def data(self, role): return self._data.get(role)


class ListW(W):
    def __init__(self, *a, **k):
        super().__init__()
        self.items, self._row = [], -1

    def addItem(self, item):
        self.items.append(item)
        self._row = len(self.items) - 1

    def count(self): return len(self.items)
    def item(self, i): return self.items[i]
    def currentRow(self): return self._row
    def takeItem(self, i):
        self._row = -1
        return self.items.pop(i)


class ButtonBox(W):
    class StandardButton:
        Ok = 1
        Cancel = 2

    def __init__(self, *a, **k):
        super().__init__()
        self._buttons = {}

    def button(self, kind):
        return self._buttons.setdefault(kind, W())


def fake_widgets_module():
    m = types.ModuleType("PyQt6.QtWidgets")
    for name in ("QFormLayout", "QGroupBox", "QHBoxLayout", "QLabel", "QPushButton", "QScrollArea",
                 "QStackedWidget", "QVBoxLayout", "QWidget"):
        setattr(m, name, type(name, (W,), {}))
    m.QDialog = Dialog
    m.QDoubleSpinBox = Spin
    m.QSpinBox = IntSpin
    m.QComboBox = Combo
    m.QFontComboBox = FontCombo
    m.QCheckBox = Check
    m.QLineEdit = Line
    m.QListWidget = ListW
    m.QListWidgetItem = Item
    m.QDialogButtonBox = ButtonBox
    m.QFileDialog = type("QFileDialog", (W,), {"getOpenFileName": staticmethod(lambda *a, **k: ("/tmp/x.svg", ""))})
    return m


def fake_gui_module():
    """QtGui factice : l'aperçu n'est jamais peint dans ces tests (pas de QPainter réel)."""
    m = types.ModuleType("PyQt6.QtGui")
    for name in ("QColor", "QFont", "QPainter", "QPainterPath", "QPen"):
        setattr(m, name, type(name, (W,), {}))
    return m


def load_dialog_module():
    fakes = {"PyQt6.QtWidgets": fake_widgets_module(), "PyQt6.QtGui": fake_gui_module()}
    with mock.patch.dict(sys.modules, fakes):
        # patch.dict remet sys.modules en l'état à la sortie : le module
        # « factice » (et son paquet) ne reste pas en cache.
        for name in ("laser_studio.ui.dialogs.box_generator", "laser_studio.ui.dialogs.box_generator.dialog",
                     "laser_studio.ui.dialogs.box_generator.preview"):
            sys.modules.pop(name, None)
        module = importlib.import_module("laser_studio.ui.dialogs.box_generator.dialog")
        module.preview_module = sys.modules["laser_studio.ui.dialogs.box_generator.preview"]
    return module


class Layer:
    def __init__(self, id_, name, mode):
        self.id, self.name, self.mode = id_, name, mode


LAYERS = [Layer("g", "Gravure", "Gravure Remplie"), Layer("c", "Découpe", "Découpe"), Layer("m", "Marquage", "Marquage (Contour)")]

try:
    bd = load_dialog_module()
except ImportError:
    bd = None


@unittest.skipIf(bd is None, "ui.dialogs.box_generator non importable ici")
class DialogSmokeTests(unittest.TestCase):
    def make(self, **kw):
        return bd.BoxGeneratorDialog(None, LAYERS, 400.0, 300.0, kw.get("initial"))

    def ok_enabled(self, d):
        return d.buttons.button(bd.QDialogButtonBox.StandardButton.Ok)._enabled

    def test_defaults_build_a_valid_box(self):
        d = self.make()
        p = d.params()
        self.assertEqual((p.width, p.depth, p.height, p.thickness, p.lid), (100.0, 70.0, 50.0, 3.0, True))
        self.assertEqual(p.dimensions, "outer")
        self.assertEqual(p.max_width, 380.0)
        self.assertTrue(self.ok_enabled(d))
        self.assertIn("6", d.lbl_summary.text())
        self.assertIn("100.0 x 70.0 x 50.0", d.lbl_summary.text())

    def test_content_scrolls_and_buttons_stay_outside_the_scroll_area(self):
        """Écran peu haut : valider doit rester accessible (boutons et résumé hors de la zone qui défile)."""
        d = self.make()
        self.assertIsInstance(d.scroll, bd.QScrollArea)
        src = open(bd.__file__, encoding="utf-8").read()
        self.assertIn("outer.addWidget(self.lbl_summary)", src)
        self.assertIn("outer.addWidget(self.buttons)", src)
        self.assertIn("self.scroll.setWidgetResizable(True)", src)
        self.assertNotIn("main.addWidget(self.buttons)", src)

    def test_default_layers_are_chosen_by_mode(self):
        d = self.make()
        self.assertEqual(d.cut_layer_id(), "c")
        self.assertEqual(d.engrave_layer_id(), "g")

    def test_changing_values_is_reflected_in_params_and_summary(self):
        d = self.make()
        d.spin_x.setValue(120)
        d.spin_thickness.setValue(4)
        d.combo_lid.setCurrentIndex(d.combo_lid.findData("none"))
        d.combo_mode.setCurrentIndex(d.combo_mode.findData("inner"))
        d._refresh_summary()
        p = d.params()
        self.assertEqual((p.width, p.thickness, p.lid, p.dimensions), (120.0, 4.0, False, "inner"))
        self.assertIn("5", d.lbl_summary.text().split("panneau")[0] if "panneau" in d.lbl_summary.text() else d.lbl_summary.text())
        self.assertIn("128.0 x 78.0 x 58.0", d.lbl_summary.text())          # intérieur + 2 x 4

    def test_invalid_values_disable_ok_and_show_a_message(self):
        d = self.make()
        d.spin_z.setValue(10)
        d.spin_thickness.setValue(5)                                           # 3 x 5 = 15 mm minimum : 10 mm est trop petit
        d._refresh_summary()
        self.assertFalse(self.ok_enabled(d))
        self.assertIn("Z", d.lbl_summary.text())
        d.spin_z.setValue(50)
        d._refresh_summary()
        self.assertTrue(self.ok_enabled(d))

    def test_too_big_for_the_bed_shows_a_warning_but_stays_valid(self):
        d = self.make()
        d.spin_x.setValue(700)
        d._refresh_summary()
        self.assertTrue(self.ok_enabled(d))
        self.assertIn("400 x 300", d.lbl_summary.text())

    def test_text_decor_add_and_remove(self):
        d = self.make()
        d.edit_decor_text.setText("Bonjour")
        d.combo_face.setCurrentIndex(d.combo_face.findData("back"))
        d.spin_decor_size.setValue(12)
        d.chk_decor_bold.setChecked(True)
        d.spin_decor_dy.setValue(-3)
        d._add_decor()
        (decor,) = d.decors()
        self.assertEqual((decor.face, decor.kind, decor.text, decor.size_mm, decor.bold, decor.dy),
                         ("back", "text", "Bonjour", 12.0, True, -3.0))
        self.assertEqual(decor.font_family, "DejaVu Sans")
        d._remove_decor()
        self.assertEqual(d.decors(), [])

    def test_empty_text_or_missing_svg_adds_nothing(self):
        d = self.make()
        d.edit_decor_text.setText("   ")
        d._add_decor()
        d.combo_decor_kind.setCurrentIndex(1)
        d._add_decor()                                                         # aucun fichier SVG choisi
        self.assertEqual(d.decors(), [])

    def test_svg_decor(self):
        d = self.make()
        d.combo_decor_kind.setCurrentIndex(1)
        d._browse_svg()
        d.spin_decor_width.setValue(25)
        d._add_decor()
        (decor,) = d.decors()
        self.assertEqual((decor.kind, decor.svg_path, decor.width_mm), ("svg", "/tmp/x.svg", 25.0))

    def test_settings_round_trip(self):
        d = self.make()
        d.spin_x.setValue(88)
        d.spin_kerf.setValue(0.15)
        d.combo_lid.setCurrentIndex(d.combo_lid.findData("none"))
        d.edit_decor_text.setText("Salut")
        d._add_decor()
        saved = d.settings()
        d2 = self.make(initial=saved)
        p = d2.params()
        self.assertEqual((p.width, p.kerf, p.lid), (88.0, 0.15, False))
        self.assertEqual([x.text for x in d2.decors()], ["Salut"])
        self.assertEqual((d2.cut_layer_id(), d2.engrave_layer_id()), ("c", "g"))

    def test_new_option_defaults(self):
        p = self.make().params()
        self.assertEqual((p.lid_type, p.clearance, p.dividers_x, p.dividers_y), ("finger", 0.1, 0, 0))

    def test_lid_choices_and_open_box(self):
        d = self.make()
        kinds = [data for _text, data in d.combo_lid.items]
        self.assertEqual(sorted(kinds), sorted(["finger", "lip", "sliding", "none"]))
        for kind in ("lip", "sliding"):
            d.combo_lid.setCurrentIndex(d.combo_lid.findData(kind))
            p = d.params()
            self.assertEqual((p.lid, p.lid_type), (True, kind))
        d.combo_lid.setCurrentIndex(d.combo_lid.findData("none"))
        p = d.params()
        self.assertFalse(p.lid)
        self.assertEqual(len(bd.bg.build_box(p).panels), 5)

    def test_dividers_are_passed_and_summarised(self):
        d = self.make()
        d.spin_div_x.setValue(2)
        d.spin_div_y.setValue(1)
        d._refresh_summary()
        p = d.params()
        self.assertEqual((p.dividers_x, p.dividers_y), (2, 1))
        self.assertTrue(self.ok_enabled(d))
        self.assertIn("6", d.lbl_summary.text())                            # 3 x 2 compartiments
        self.assertEqual(d.preview._result.dividers, (2, 1))

    def test_too_many_dividers_disable_ok(self):
        d = self.make()
        d.spin_div_x.setValue(10)
        d._refresh_summary()
        self.assertFalse(self.ok_enabled(d))
        self.assertEqual(d.preview._result, None)
        self.assertTrue(d.preview._error)
        d.spin_div_x.setValue(1)
        d._refresh_summary()
        self.assertTrue(self.ok_enabled(d))
        self.assertEqual(d.preview._error, "")

    def test_preview_follows_the_parameters(self):
        d = self.make()
        self.assertEqual(len(d.preview._result.panels), 6)
        d.combo_lid.setCurrentIndex(d.combo_lid.findData("lip"))
        d._refresh_summary()
        self.assertEqual(len(d.preview._result.panels), 7)                  # + rebord
        d.spin_x.setValue(700)
        d._refresh_summary()
        self.assertTrue(d.preview._too_big)

    def test_preview_receives_the_decors(self):
        d = self.make()
        d.edit_decor_text.setText("Hello")
        d._add_decor()
        self.assertEqual([x.text for x in d.preview._decors], ["Hello"])
        d._remove_decor()
        self.assertEqual(d.preview._decors, [])

    def test_new_settings_round_trip(self):
        d = self.make()
        d.combo_lid.setCurrentIndex(d.combo_lid.findData("sliding"))
        d.spin_clearance.setValue(0.25)
        d.spin_div_x.setValue(3)
        d.spin_div_y.setValue(2)
        saved = d.settings()
        p = self.make(initial=saved).params()
        self.assertEqual((p.lid_type, p.clearance, p.dividers_x, p.dividers_y), ("sliding", 0.25, 3, 2))

    def test_legacy_settings_without_lid_type(self):
        legacy = {"width": 90.0, "lid": False}
        self.assertFalse(self.make(initial=legacy).params().lid)
        self.assertTrue(self.make(initial={"width": 90.0, "lid": True}).params().lid)
        self.assertEqual(self.make(initial={"width": 90.0}).params().lid_type, "finger")

    def test_fit_transform_centres_and_scales(self):
        fit = bd.preview_module.fit_transform
        scale, ox, oy = fit(200, 100, 428, 328, margin=14)                  # zone utile 400 x 300 : 2 px/mm
        self.assertAlmostEqual(scale, 2.0)
        self.assertAlmostEqual(ox, 14.0)
        self.assertAlmostEqual(oy, (328 - 200) / 2)
        self.assertEqual(fit(0, 0, 100, 100, margin=10), (1.0, 10, 10))

    def test_panel_labels(self):
        label = bd.preview_module.panel_label
        self.assertNotIn("box.", label("front"))
        self.assertIn("2", label("divider_x2"))
        self.assertIn("3", label("divider_y3"))
        self.assertNotIn("box.", label("lip"))
        self.assertEqual(label("unknown"), "unknown")

    def test_error_messages_exist_for_each_error_code(self):
        from laser_studio.vector import box_generator as bg
        for code, info in (("thickness", {"value": 0}), ("kerf", {"value": 5}), ("too_small", {"axis": "X", "value": 5.0, "minimum": 9.0}),
                           ("finger_too_small", {"value": 1.0, "minimum": 3.0}), ("pinched_panel", {"point": (0, 0)}),
                           ("lid_type", {"value": "x"}), ("clearance", {"value": 5.0}),
                           ("dividers", {"value": 99, "maximum": 20}),
                           ("compartment_too_small", {"axis": "X", "value": 5.0, "minimum": 9.0}),
                           ("dividers_too_low", {"value": 5.0, "minimum": 9.0}),
                           ("unknown_code", {})):
            text = bd.error_message(bg.BoxError(code, **info))
            self.assertTrue(text and not text.startswith("box.err."), code)


if __name__ == "__main__":
    unittest.main()
