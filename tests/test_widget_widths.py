"""Garde-fou : une liste déroulante à textes longs ne doit pas imposer sa largeur à la colonne de gauche.

Par défaut, QComboBox prend la largeur de son élément le plus long comme largeur MINIMALE : un libellé
de 60 caractères empêche de rétrécir la colonne avec le séparateur. Toute liste dont un élément traduit
dépasse LONG caractères doit donc fixer une politique de taille (ou une largeur minimale)."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import i18n
except ImportError:
    i18n = None

LONG = 40
UI_FILES = ("ui_setup_mixin.py", "separation_mixin.py", "png2svg_widget.py", "vector_layers.py", "image_processing_mixin.py")


def long_combos():
    """[(fichier, nom du combo, clé)] pour les combos dont un élément traduit est trop long."""
    found = []
    for name in UI_FILES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            src = f.read().replace("\r\n", "\n")
        for m in re.finditer(r'((?:self\.)?\w+)\.addItem\(\s*tr\("([^"]+)"\)', src):
            key = m.group(2)
            entry = i18n.TRANSLATIONS.get(key)
            if entry and max(len(v) for v in entry.values()) > LONG:
                found.append((name, m.group(1), key, src))
    return found


@unittest.skipIf(i18n is None, "i18n non importable ici")
class WidgetWidthTests(unittest.TestCase):
    def test_long_combo_items_do_not_force_the_column_width(self):
        problems = []
        for name, combo, key, src in long_combos():
            guarded = (re.search(rf"{re.escape(combo)}\.setSizeAdjustPolicy\(", src)
                       or re.search(rf"{re.escape(combo)}\.setMinimumContentsLength\(", src)
                       or re.search(rf"{re.escape(combo)}\.setMinimumWidth\(\s*[1-9]", src))
            if not guarded:
                longest = max(len(v) for v in i18n.TRANSLATIONS[key].values())
                problems.append(f"{name}: {combo} ({key}, {longest} caractères)")
        self.assertEqual(problems, [], "Liste déroulante à texte long sans politique de taille :\n" + "\n".join(problems))

    def test_the_material_selector_is_covered(self):
        names = {(f, c) for f, c, _, _ in long_combos()}
        self.assertIn(("ui_setup_mixin.py", "self.combo_material_bg"), names)

    def test_material_selector_uses_a_short_minimum_width(self):
        with open(os.path.join(ROOT, "ui_setup_mixin.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("self.combo_material_bg.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)", src)
        self.assertRegex(src, r"self\.combo_material_bg\.setMinimumContentsLength\(\d{1,2}\)")


class SplitterTests(unittest.TestCase):
    """Le séparateur principal doit pouvoir élargir la colonne de gauche."""

    def source(self):
        with open(os.path.join(ROOT, "ui_setup_mixin.py"), encoding="utf-8") as f:
            return f.read()

    def test_center_has_an_explicit_small_minimum_width(self):
        m = re.search(r"center_widget\.setMinimumWidth\((\d+)\)", self.source())
        self.assertIsNotNone(m, "le centre doit avoir une largeur minimale explicite")
        self.assertLessEqual(int(m.group(1)), 600)
        self.assertGreaterEqual(int(m.group(1)), 200)

    def test_left_column_has_no_maximum_width(self):
        src = self.source()
        body = src[src.index("left_widget = "):src.index("splitter.addWidget(left_widget)")]
        self.assertNotIn("setMaximumWidth", body)
        self.assertNotIn("setFixedWidth", body)

    def test_generate_button_padding(self):
        self.assertIn('btn_generate.setStyleSheet("background-color: #2b5c8f; color: white; font-weight: bold; padding: 3px;")', self.source())


@unittest.skipIf(i18n is None, "i18n non importable ici")
class VectorToolbarTests(unittest.TestCase):
    """Barre d'outils de l'éditeur vectoriel : deux lignes, libellés entièrement visibles."""

    def rows(self):
        with open(os.path.join(ROOT, "ui_setup_mixin.py"), encoding="utf-8") as f:
            src = f.read().replace("\r\n", "\n")
        block = src[src.index("toolbar_vector = QHBoxLayout()"):src.index("layout_vector_editor.addLayout(toolbar_vector_edit)")]
        keys = dict(re.findall(r'(btn_\w+) = QPushButton\(tr\("([^"]+)"\)\)', block))
        rows = {}
        for layout, button in re.findall(r"(toolbar_vector\w*)\.addWidget\((btn_\w+)\)", block):
            rows.setdefault(layout, []).append(keys[button])
        return rows

    def estimated_width(self, keys):
        """~7 px par caractère de la traduction la plus longue + 28 px de marges de bouton."""
        return sum(max(len(v) for v in i18n.TRANSLATIONS[k].values()) * 7 + 28 for k in keys)

    def test_two_rows_with_all_twelve_buttons(self):
        rows = self.rows()
        self.assertEqual(sorted(rows), ["toolbar_vector", "toolbar_vector_edit"])
        self.assertEqual(sum(len(v) for v in rows.values()), 12)
        self.assertEqual(len(set(k for v in rows.values() for k in v)), 12)

    def test_each_row_is_narrow_enough_in_every_language(self):
        for layout, keys in self.rows().items():
            self.assertLessEqual(self.estimated_width(keys), 1000, f"{layout} : {self.estimated_width(keys)} px")

    def test_import_and_box_generator_buttons_are_on_the_first_row(self):
        first = self.rows()["toolbar_vector"]
        self.assertIn("ui.vector_import_svg", first)
        self.assertIn("ui.vector_box_generator", first)
        self.assertIn("ui.vector_nesting", first)


if __name__ == "__main__":
    unittest.main()
