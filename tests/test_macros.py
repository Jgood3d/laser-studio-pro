"""Macros de l'utilisateur : fichier YAML et détection du laser (grbl/macros.py), modèle (models/macros.py),
envoi et confirmations (controllers/macros.py)."""
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import yaml  # noqa: F401
    from laser_studio.grbl.macros import Macro, MacroError, dump_macros, fires_laser, load_macros
except ImportError:  # PyYAML manquant
    load_macros = None

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.macros import MacroController, macro_error_text
    from laser_studio.models.macros import MacrosModel
    from job_fakes import FakeDialogs
except ImportError:
    MacroController = None

EXAMPLE = """# exemple
macros:
  - name: Décaler +20 X +10 Y
    tooltip: Déplace la tête
    gcode: |
      G91
      G0 X20 Y10 ; relatif
      G90
  - name: Pointeur
    confirm: true
    machines: Atomstack A5
    gcode: [S10, M3]
"""


@unittest.skipIf(load_macros is None, "PyYAML non installé")
class MacroFileTests(unittest.TestCase):
    def test_load(self):
        offset, pointer = load_macros(EXAMPLE)
        self.assertEqual(offset, Macro("Décaler +20 X +10 Y", ("G91", "G0 X20 Y10", "G90"), "Déplace la tête"))
        self.assertEqual((pointer.confirm, pointer.machines, pointer.gcode), (True, ("Atomstack A5",), ("S10", "M3")))
        self.assertTrue(offset.shown_for("autre") and pointer.shown_for("Atomstack A5"))
        self.assertFalse(pointer.shown_for("autre"))

    def test_round_trip_keeps_a_readable_block(self):
        macros = load_macros(EXAMPLE)
        text = dump_macros(macros)
        self.assertIn("gcode: |", text)
        self.assertEqual(load_macros(text), macros)

    def test_empty_files(self):
        for text in ("", "   \n", "macros:\n", "# rien\n"):
            self.assertEqual(load_macros(text), [], repr(text))

    def test_errors_have_a_code(self):
        cases = {"macros: 3": "not_a_list", "macros:\n  - gcode: G0\n": "missing_field",
                 "macros:\n  - name: a\n    gcode: '; rien'\n": "empty_gcode", "macros: [": "yaml",
                 "macros:\n  - 12\n": "not_a_macro", "macros:\n  - name: a\n    machines: 3\n    gcode: G0\n": "bad_field"}
        for text, code in cases.items():
            with self.assertRaises(MacroError) as raised:
                load_macros(text)
            self.assertEqual(raised.exception.code, code, text)

    def test_fires_laser(self):
        self.assertFalse(fires_laser(["G91", "G0 X10", "G90"]))
        self.assertFalse(fires_laser(["M3 S0", "G1 X10"]))
        self.assertTrue(fires_laser(["M3 S10"]))
        self.assertTrue(fires_laser(["m4 s5 ; dynamique"]))
        self.assertTrue(fires_laser(["S200", "M3"]))                  # puissance modale
        self.assertFalse(fires_laser(["S200", "M5", "G0 X1"]))
        self.assertFalse(fires_laser(["; M3 S100"]))                  # commentaire
        self.assertFalse(fires_laser(["(M3 S100) G0 X1"]))


class FakeEngraver:
    def __init__(self, connected=True):
        self.connected, self.streaming = connected, False
        self.sent, self.asked = [], []

    def allowed(self, action, _key=None):
        """Comme EngraverController.allowed (le message de refus est testé avec lui)."""
        self.asked.append(action)
        return self.connected and not self.streaming

    def send_direct(self, commands):
        self.sent.append(commands)


@unittest.skipIf(MacroController is None or load_macros is None, "PyQt6 ou PyYAML non importable ici")
class MacroControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "macros.yaml")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(EXAMPLE + "  - name: Laser sans case\n    gcode: M4 S50\n")
        self.model = MacrosModel(self.path)
        self.engraver, self.dialogs = FakeEngraver(), FakeDialogs()
        self.edited = None
        self.ctrl = MacroController(self.model, self.engraver, self.dialogs,
                                    profile_name=lambda: "Atomstack A5", profiles=lambda: ["Atomstack A5"])

    def test_plain_macro_is_sent_without_question(self):
        self.assertTrue(self.ctrl.run(0))
        self.assertEqual(self.engraver.sent, [["G91", "G0 X20 Y10", "G90"]])
        self.assertEqual(self.dialogs.calls, [])

    def test_laser_macro_is_always_confirmed_with_no_as_default(self):
        self.dialogs.answer = False
        self.assertFalse(self.ctrl.run(2))
        self.assertEqual(self.dialogs.kinds(), ["confirm_default_no"])
        self.assertEqual(self.engraver.sent, [])
        self.dialogs.answer = True
        self.assertTrue(self.ctrl.run(1))                               # laser ET case cochée : une seule question
        self.assertEqual(self.dialogs.kinds(), ["confirm_default_no", "confirm_default_no"])
        self.assertEqual(self.engraver.sent, [["S10", "M3"]])

    def test_checked_macro_asks_a_simple_confirmation(self):
        self.model.macros[0].confirm = True
        self.dialogs.answer = False
        self.assertFalse(self.ctrl.run(0))
        self.assertEqual(self.dialogs.kinds(), ["confirm"])

    def test_never_during_a_job_nor_disconnected(self):
        self.engraver.streaming = True
        self.assertFalse(self.ctrl.run(0))
        self.assertEqual(self.engraver.asked, ["macro"])               # la table de l'état du graveur décide
        self.engraver.streaming = False
        self.engraver.connected = False
        self.assertFalse(self.ctrl.run(0))
        self.assertFalse(self.ctrl.run(99))
        self.assertEqual(self.engraver.sent, [])

    def test_profile_filter(self):
        self.assertEqual([i for i, _m in self.ctrl.visible()], [0, 1, 2])
        self.ctrl._profile_name = lambda: "Autre"
        self.assertEqual([i for i, _m in self.ctrl.visible()], [0, 2])

    def test_manage_saves_the_new_list(self):
        changed = []
        self.model.changed.connect(lambda: changed.append(True))
        macros, profiles, _read, _write = self.ctrl.editor_args()          # remplit l'éditeur
        self.assertEqual((len(macros), profiles), (3, ["Atomstack A5"]))
        self.assertTrue(self.ctrl.save([Macro("Seule", ("G0 X0 Y0",))]))   # « Enregistrer » de la page
        self.assertEqual((changed, [m.name for m in MacrosModel(self.path).macros]), ([True], ["Seule"]))

    def test_unreadable_file_is_kept_until_new_macros_are_saved(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("macros: [")
        model = MacrosModel(self.path)
        self.assertEqual((model.macros, model.load_error.code), ([], "yaml"))
        self.assertIn("YAML", macro_error_text(model.load_error))
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "macros: [")                     # pas écrasé à la lecture

    def test_import_export(self):
        out = os.path.join(self.dir.name, "export.yaml")
        self.ctrl.write_file(out, self.model.macros)
        self.assertEqual(self.ctrl.read_file(out), self.model.macros)



@unittest.skipIf(MacroController is None or load_macros is None, "PyQt6 ou PyYAML non importable ici")
class MacroEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, macros=()):
        from laser_studio.ui.dialogs.macros import MacroEditorDialog
        dialog = MacroEditorDialog(list(macros), ["Atomstack A5", "Ortur"], None, None)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_add_edit_and_validate(self):
        dialog = self.make(load_macros(EXAMPLE))
        dialog.list_buttons["add"].click()
        dialog.name.setText("Origine")
        dialog.gcode.setPlainText("$H\nG92 X0 Y0")
        dialog.machines.item(1).setCheckState(dialog.machines.item(1).checkState().Checked)
        self.assertFalse(dialog.laser_warning.isVisibleTo(dialog))
        dialog.gcode.setPlainText("$H\nM3 S5")
        self.assertTrue(dialog.laser_warning.isVisibleTo(dialog))
        dialog.gcode.setPlainText("$H\nG92 X0 Y0")
        dialog._accept()
        names = [m.name for m in dialog.result_macros]
        self.assertEqual(names, ["Décaler +20 X +10 Y", "Pointeur", "Origine"])
        self.assertEqual(dialog.result_macros[2].machines, ("Ortur",))

    def test_invalid_macro_is_refused_and_selected(self):
        from unittest import mock
        from PyQt6.QtWidgets import QMessageBox
        dialog = self.make(load_macros(EXAMPLE))
        dialog.list.setCurrentRow(0)
        dialog.gcode.setPlainText("; rien")
        dialog.list.setCurrentRow(1)
        with mock.patch.object(QMessageBox, "warning") as warning:
            dialog._accept()
        warning.assert_called_once()
        self.assertIsNone(getattr(dialog, "result_macros", None))
        self.assertEqual(dialog.list.currentRow(), 0)

    def test_move_and_delete(self):
        dialog = self.make(load_macros(EXAMPLE))
        dialog.list.setCurrentRow(1)
        dialog.list_buttons["up"].click()
        dialog.list_buttons["delete"].click()
        dialog._accept()
        self.assertEqual([m.name for m in dialog.result_macros], ["Décaler +20 X +10 Y"])
        self.assertTrue(dialog.result_macros[0].machines == ())


if __name__ == "__main__":
    unittest.main()
