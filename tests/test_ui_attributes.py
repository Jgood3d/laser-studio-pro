"""Aucun widget ni méthode privée ne doit être utilisé sans être construit quelque part
(typiquement : un mixin mis à jour avec un ui_setup_mixin.py resté à l'ancienne version)."""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_ui_attributes as chk


def write(directory, name, text):
    with open(os.path.join(directory, name), "w", encoding="utf-8") as f:
        f.write(text)


class UiAttributesTests(unittest.TestCase):
    def test_project_has_no_missing_widget(self):
        problems = chk.find_problems(chk.project_files(ROOT))
        detail = "\n".join(f"self.{n} <- {sorted(p)[:3]}" for n, p in sorted(problems.items()))
        self.assertEqual(problems, {}, "Attributs utilisés mais jamais construits :\n" + detail)

    def test_checker_detects_a_widget_that_nothing_builds(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "ui.py", "class Ui:\n    def build(self):\n        self.spin_a = 1\n")
            write(d, "logic.py", "class Logic:\n    def go(self):\n        return self.spin_a + self.combo_missing.value()\n")
            problems = chk.find_problems(chk.project_files(d))
        self.assertEqual(set(problems), {"combo_missing"})
        self.assertEqual(problems["combo_missing"], {("logic.py", 3)})

    def test_checker_accepts_hasattr_guard_methods_and_dynamic_definitions(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.py", (
                "class A:\n"
                "    def f(self):\n"
                "        if hasattr(self, 'spin_optional'):\n"
                "            self.spin_optional.setValue(1)\n"
                "        setattr(self, 'btn_dynamic', 1)\n"
                "        return self.btn_dynamic, self._helper(), self.setWindowTitle('x')\n"
                "    def _helper(self):\n"
                "        return 1\n"))
            self.assertEqual(chk.find_problems(chk.project_files(d)), {})

    def test_checker_detects_a_missing_private_method(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "a.py", "class A:\n    def f(self):\n        self._not_defined_anywhere()\n")
            self.assertEqual(set(chk.find_problems(chk.project_files(d))), {"_not_defined_anywhere"})

    def test_reproduces_the_stale_ui_setup_case(self):
        """Mixin récent (lit combo_material_bg) + ui_setup_mixin.py d'avant la matière : doit être signalé."""
        with tempfile.TemporaryDirectory() as d:
            write(d, "image_processing_mixin.py", "class I:\n    def get_material_bg(self):\n        return self.combo_material_bg.currentData()\n")
            write(d, "ui_setup_mixin.py", "class U:\n    def init_ui(self):\n        self.chk_invert = 1\n")
            self.assertEqual(set(chk.find_problems(chk.project_files(d))), {"combo_material_bg"})
            write(d, "ui_setup_mixin.py", "class U:\n    def init_ui(self):\n        self.combo_material_bg = 1\n")
            self.assertEqual(chk.find_problems(chk.project_files(d)), {})


if __name__ == "__main__":
    unittest.main()
