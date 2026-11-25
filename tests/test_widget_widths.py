"""Garde-fou : une liste déroulante à textes longs ne doit pas imposer sa largeur à la colonne de gauche.

Par défaut, QComboBox prend la largeur de son élément le plus long comme largeur MINIMALE : un libellé
de 60 caractères empêche de rétrécir la colonne avec le séparateur. Toute liste dont un élément traduit
dépasse LONG caractères doit donc fixer une politique de taille (ou une largeur minimale)."""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_source import ui_files, ui_source  # noqa: E402

try:
    from laser_studio import i18n
except ImportError:
    i18n = None
try:
    from laser_studio.ui.vector_editor import tab as vector_tab
except ImportError:  # PyQt6 manquant
    vector_tab = None

LONG = 40
# Le paquet ui/ comprend l'éditeur vectoriel (ui/vector_editor/) et le tableau des calques.
UI_FILES = tuple(ui_files())


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
        self.assertIn((os.path.join("ui", "tabs", "image", "material_combo.py"), "self"), names)

    def test_material_selector_uses_a_short_minimum_width(self):
        with open(os.path.join(ROOT, "ui", "tabs", "image", "material_combo.py"), encoding="utf-8") as f:
            combo = f.read()
        self.assertIn("self.setSizeAdjustPolicy(\n            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon", combo)
        self.assertRegex(combo, r"self\.setMinimumContentsLength\(\d{1,2}\)")


class SplitterTests(unittest.TestCase):
    """Le séparateur principal doit pouvoir élargir la colonne de gauche."""

    def source(self):
        return ui_source()

    def test_center_has_an_explicit_small_minimum_width(self):
        m = re.search(r"center_widget\.setMinimumWidth\((\d+)\)", self.source())
        self.assertIsNotNone(m, "le centre doit avoir une largeur minimale explicite")
        self.assertLessEqual(int(m.group(1)), 600)
        self.assertGreaterEqual(int(m.group(1)), 200)

    def test_there_is_no_left_column_any_more(self):
        # La colonne de gauche a été supprimée : réglages de l'image dans « Graver une image »,
        # position du job dans le panneau machine. Le centre occupe toute la largeur.
        src = self.source()
        # Le widget de conversion PNG → SVG a son propre panneau de gauche
        # (left_widget) : seule la fenêtre principale est concernée ici.
        with open(os.path.join(ROOT, "ui", "app", "main_window.py"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"\bleft_widget\b")
        self.assertNotIn("self.left_v_splitter", src)
        self.assertIn("main_layout.addWidget(center_widget)", src)

    def test_generate_button_takes_the_theme_colors(self):
        # Bouton principal : ses couleurs viennent du thème (QPushButton[role="primary"] dans theme.py).
        with open(os.path.join(ROOT, "ui", "app", "menu", "toolbar.py"), encoding="utf-8") as f:
            toolbar = f.read()
        self.assertIn('button.setProperty("role", "primary")', toolbar)
        self.assertNotIn("setStyleSheet", toolbar)


@unittest.skipIf(i18n is None or vector_tab is None, "i18n / PyQt6 non importables ici")
class VectorToolbarTests(unittest.TestCase):
    """Barre d'outils de l'éditeur vectoriel (ui/vector_editor/tab.py) : Importer en haut, l'édition (générateurs
    compris) contre la liste des objets, créer / dessiner dans la barre flottante du canevas, l'alignement dans
    les propriétés."""

    def rows(self):
        return {"top": ["ui.vector_import_drop"]}

    def estimated_width(self, keys):
        """~7 px par caractère de la traduction la plus longue + 28 px de marges de bouton."""
        return sum(max(len(v) for v in i18n.TRANSLATIONS[k].values()) * 7 + 28 for k in keys)

    def test_one_row_with_import_and_tools(self):
        self.assertEqual(list(vector_tab.COMMANDS[:1]), ["import"])
        # Les générateurs : une icône en tête de la barre d'édition, qui ouvre leur fenêtre unique.
        self.assertEqual(vector_tab.EDIT_ACTIONS[0], ("generators", "ui.vector_generators", "draw-cuboid"))
        self.assertIn(("nesting", "ui.vector_nesting", "object-group"), vector_tab.EDIT_ACTIONS)

    def test_create_and_draw_tools_float_on_the_left_with_icons(self):
        pairs = {(key, icon) for _name, key, icon in vector_tab.CREATE_ACTIONS + vector_tab.DRAW_TOOLS}
        for pair in (("ui.vector_add_text", "insert-text"), ("ui.vector_add_shape", "shape-choose"),
                     ("ui.vector_tool_select", "tool-pointer"), ("ui.vector_tool_line", "draw-line"),
                     ("ui.vector_tool_rect", "draw-rectangle"), ("ui.vector_tool_circle", "draw-circle"),
                     ("ui.vector_tool_ellipse", "draw-ellipse"), ("ui.vector_tool_measure", "measure")):
            self.assertIn(pair, pairs)
        with open(os.path.join(ROOT, "ui", "vector_editor", "tab.py"), encoding="utf-8") as f:
            src = f.read()
        # Une seule barre flottante sur le canevas : l'édition est dans la rangée du haut, l'alignement dans
        # les propriétés.
        self.assertEqual(src.count("FloatingToolBar("), 1)
        self.assertIn('self.canvas, anchor="left")', src)
        # Alignement : pictogramme seul sur le bouton, action complète en infobulle (4 langues).
        self.assertIn('tr(key).split(" ", 1)[0], tr(f"{key}_tip")', src)

    def test_edit_and_align_actions(self):
        edit = [entry[1] for entry in vector_tab.EDIT_ACTIONS if entry]
        for key in ("ui.vector_edit_selection", "ui.vector_rotate_90", "ui.vector_duplicate", "ui.vector_delete",
                    "vector.explode_path", "vector.edit_nodes", "vector.text_follow", "ui.vector_undo", "ui.vector_redo"):
            self.assertIn(key, edit)
        align = [entry[1] for entry in vector_tab.ALIGN_ACTIONS if entry]
        for key in ("ui.vector_align_left", "ui.vector_align_center_h", "ui.vector_align_right",
                    "ui.vector_align_top", "ui.vector_align_middle_v", "ui.vector_align_bottom",
                    "ui.vector_distribute_h", "ui.vector_distribute_v"):
            self.assertIn(key, align)
            self.assertEqual(sorted(i18n.TRANSLATIONS[f"{key}_tip"]), ["de", "en", "es", "fr"])

    def test_each_row_is_narrow_enough_in_every_language(self):
        for layout, keys in self.rows().items():
            self.assertLessEqual(self.estimated_width(keys), 1000, f"{layout} : {self.estimated_width(keys)} px")



if __name__ == "__main__":
    unittest.main()
