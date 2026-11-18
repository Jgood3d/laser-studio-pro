"""Bibliothèque de modèles : catalogue (library/catalog.py), import SVG complet
(vector/svg_import.py), fenêtres (ui/dialogs/library) et import dans les
calques (controllers/library.py)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
LIBRARY = os.path.join(REPO, "src", "laser_studio", "resources", "library")
TOTEM = os.path.join(LIBRARY, "trophees", "totem-brevet-aviron", "totem-brevet-aviron.svg")

from laser_studio.library.catalog import load_catalog, pretty_name  # noqa: E402

try:
    from PyQt6.QtWidgets import QApplication, QDialog
    from laser_studio.controllers.library import LibraryController
    from laser_studio.models.layers import LayersModel
    from laser_studio.ui.dialogs.library import LibraryDialog, LibraryItemDialog
    from laser_studio.vector.svg_import import (
        document_size_mm, find_variant_groups, import_svg, parse_transform, role_of_label,
        svg_with_variants,
    )
except ImportError:  # PyQt6 manquant
    import_svg = None

SVG_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            'width="{w}" height="{h}" viewBox="{vb}">')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def svg(body, w="100mm", h="50mm", vb="0 0 100 50"):
    return SVG_HEAD.format(w=w, h=h, vb=vb) + body + "</svg>"


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def model(self, category, name, files):
        for file_name, content in files.items():
            write(os.path.join(self.root, category, name, file_name), content)

    def test_categories_items_and_metadata(self):
        write(os.path.join(self.root, "medals", "_category.json"),
              json.dumps({"title": {"fr": "Médailles", "en": "Medals"}}))
        self.model("medals", "medaille-or", {
            "medaille.svg": svg(""), "medaille_preview.png": "x", "readme.txt": "Lisez-moi",
            "info.json": json.dumps({"title": {"fr": "Médaille d'or", "en": "Gold medal"},
                                     "author": "Club", "tags": ["or", "sport"]})})
        self.model("medals", "sans-svg", {"readme.txt": "rien"})          # pas de SVG : ignoré
        self.model("signs", "porte_nom", {"plaque.svg": svg("")})
        os.makedirs(os.path.join(self.root, "vide"))                      # catégorie vide : omise
        categories = load_catalog([self.root], "fr")
        self.assertEqual([c.title for c in categories], ["Médailles", "Signs"])
        item = categories[0].items[0]
        self.assertEqual((item.key, item.title, item.author, item.readme),
                         ("medals/medaille-or", "Médaille d'or", "Club", "Lisez-moi"))
        self.assertTrue(item.preview_path.endswith("medaille_preview.png"))
        self.assertEqual(categories[1].items[0].title, "Porte nom")
        self.assertIsNone(categories[1].items[0].preview_path)
        self.assertEqual(load_catalog([self.root], "en")[0].items[0].title, "Gold medal")

    def test_search(self):
        self.model("signs", "porte-nom", {"a.svg": svg(""), "info.json": json.dumps(
            {"description": "Plaque de bureau", "tags": ["étiquette"]})})
        item = load_catalog([self.root])[0].items[0]
        for text in ("PORTE", "bureau", "etiquette"):
            self.assertTrue(item.matches(text), text)
        self.assertFalse(item.matches("médaille"))

    def test_several_roots_are_merged_first_one_wins(self):
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        self.model("signs", "plaque", {"a.svg": svg("")})
        write(os.path.join(other.name, "signs", "plaque", "b.svg"), svg(""))
        write(os.path.join(other.name, "signs", "autre", "c.svg"), svg(""))
        items = load_catalog([self.root, other.name])[0].items
        self.assertEqual([i.key for i in items], ["signs/autre", "signs/plaque"])
        self.assertTrue(items[1].svg_path.endswith("a.svg"))

    def test_pretty_name(self):
        self.assertEqual(pretty_name("totem-brevet_aviron"), "Totem brevet aviron")

    def test_bundled_library_is_found(self):
        keys = [i.key for c in load_catalog([LIBRARY]) for i in c.items]
        self.assertIn("trophees/totem-brevet-aviron", keys)


@unittest.skipIf(import_svg is None, "PyQt6 non importable ici")
class SvgImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def file(self, body, **kwargs):
        path = os.path.join(self.tmp.name, "m.svg")
        write(path, svg(body, **kwargs))
        return path

    @staticmethod
    def boxes(artwork):
        return {role: obj.world_path().boundingRect() for role, obj in artwork.items}

    def test_units_transforms_and_hidden_elements(self):
        # viewBox de 200 unités pour 100 mm : 1 unité = 0,5 mm ; groupe décalé de 20 unités.
        path = self.file(
            '<g inkscape:label="Découpes" transform="translate(20,0)">'
            '<rect x="0" y="0" width="40" height="20" fill="none" stroke="blue"/></g>'
            '<g inkscape:label="sources" style="display:none"><circle cx="5" cy="5" r="50"/></g>'
            '<rect x="0" y="80" width="10" height="20" display="none"/>',
            w="100mm", h="50mm", vb="0 0 200 100")
        art = import_svg(path, offset_x_mm=0, offset_y_mm=0)
        self.assertEqual([role for role, _o in art.items], ["cut"])
        box = self.boxes(art)["cut"]
        self.assertAlmostEqual(box.width(), 20.0, places=3)
        self.assertAlmostEqual(box.height(), 10.0, places=3)

    def test_roles_from_labels_and_fill(self):
        path = self.file(
            '<g inkscape:label="Gravure"><rect width="10" height="10" fill="none"/></g>'
            '<g inkscape:label="Marquage"><rect x="20" width="10" height="10"/></g>'
            '<g id="divers"><rect x="40" width="10" height="10" fill="#000"/>'
            '<rect x="60" width="10" height="10" fill="none" stroke="red"/></g>')
        roles = [role for role, _o in import_svg(path).items]
        self.assertEqual(sorted(roles), ["cut", "engrave", "mark"])     # un objet groupé par rôle
        self.assertEqual(role_of_label("Découpes"), "cut")
        self.assertIsNone(role_of_label("Niveau du brevet"))

    def test_variants_are_detected_and_chosen(self):
        path = self.file(
            '<g inkscape:label="Niveau">'
            '<rect inkscape:label="Petit" width="10" height="10" style="display:none"/>'
            '<rect inkscape:label="Grand" width="40" height="40"/></g>')
        groups = find_variant_groups(path)
        self.assertEqual([(g.key, [o[0] for o in g.options], g.default) for g in groups],
                         [("Niveau", ["Petit", "Grand"], "Grand")])
        self.assertAlmostEqual(self.boxes(import_svg(path))["engrave"].width(), 40, places=3)
        small = import_svg(path, variants={"Niveau": "Petit"})
        self.assertAlmostEqual(self.boxes(small)["engrave"].width(), 10, places=3)
        self.assertIn(b"display:none", svg_with_variants(path, {"Niveau": "Grand"}))

    def test_text_becomes_an_editable_text_object(self):
        path = self.file('<text x="50" y="30" style="font-size:10px;text-anchor:middle;font-weight:bold">'
                         '<tspan x="50" y="30">Bonjour</tspan></text>')
        art = import_svg(path, offset_x_mm=0, offset_y_mm=0)
        (role, obj), = art.items
        self.assertEqual((role, obj.kind, obj.text, obj.bold), ("engrave", "text", "Bonjour", True))

    def test_text_is_placed_where_the_svg_draws_it(self):
        # Rectangle de 100 x 50 mm, texte centré au milieu : il reste au milieu.
        path = self.file('<g inkscape:label="Découpe"><rect width="100" height="50" fill="none"/></g>'
                         '<text x="50" y="30" style="font-size:10px;text-anchor:middle">Milieu</text>')
        art = import_svg(path, offset_x_mm=0, offset_y_mm=0)
        text = next(o for _r, o in art.items if o.kind == "text").world_path().boundingRect()
        self.assertAlmostEqual(text.center().x(), 50.0, delta=0.5)

    def test_parse_transform_order(self):
        t = parse_transform("translate(10,0) scale(2)")
        p = t.map(1.0, 1.0)
        self.assertEqual(p, (12.0, 2.0))

    def test_rounded_rect_and_document_size(self):
        path = self.file('<rect width="30" height="18" ry="4" fill="none"/>', w="30mm", h="18mm", vb="0 0 30 18")
        self.assertEqual(document_size_mm(path), (30.0, 18.0))
        self.assertEqual(len(import_svg(path).items), 1)

    def test_bundled_totem(self):
        groups = find_variant_groups(TOTEM)
        self.assertEqual([o[0] for o in groups[0].options],
                         ["Niveau 2", "Niveau 1", "Bronze", "Argent", "Or", "Niveau 3"])
        art = import_svg(TOTEM, variants={groups[0].key: "Or"})
        texts = sorted(o.text for _r, o in art.items if o.kind == "text")
        self.assertEqual(texts, ["Brevet d'aviron", "Or"])               # calque caché « sources » ignoré
        self.assertEqual(sorted({r for r, _o in art.items}), ["cut", "engrave"])
        self.assertAlmostEqual(art.width_mm, 30.0, places=1)
        self.assertAlmostEqual(art.height_mm, 116.4, places=1)


@unittest.skipIf(import_svg is None, "PyQt6 non importable ici")
class LibraryDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        body = '<g inkscape:label="Niveau"><rect inkscape:label="A" width="10" height="10"/>' \
               '<rect inkscape:label="B" width="20" height="10" style="display:none"/></g>'
        write(os.path.join(self.tmp.name, "medals", "medaille", "m.svg"), svg(body))
        write(os.path.join(self.tmp.name, "signs", "plaque", "p.svg"), svg('<rect width="5" height="5"/>'))
        self.categories = load_catalog([self.tmp.name])

    def dialog(self):
        d = LibraryDialog(None, self.categories, icon_size=120)
        self.addCleanup(d.deleteLater)
        return d

    def test_category_and_search_filters(self):
        d = self.dialog()
        self.assertEqual(d.grid.count(), 2)
        d.category_list.setCurrentRow(2)                  # « Signs »
        self.assertEqual([d.grid.item(i).text() for i in range(d.grid.count())], ["Plaque"])
        d.category_list.setCurrentRow(0)
        d.search_edit.setText("méd")
        self.assertEqual(d.grid.count(), 1)

    def test_icon_size_slider_resizes_the_grid(self):
        d = self.dialog()
        sizes = []
        d.icon_size_changed.connect(sizes.append)
        d.size_slider.setValue(300)
        self.assertEqual((d.grid.iconSize().width(), sizes), (300, [300]))
        self.assertGreater(d.grid.gridSize().width(), 300)

    def test_import_gives_the_item_and_its_default_variants(self):
        d = self.dialog()
        d.grid.setCurrentRow(0)
        d.import_button.click()
        item, variants = d.chosen()
        self.assertEqual((item.key, variants), ("medals/medaille", {"Niveau": "A"}))
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)

    def test_details_offer_the_variants(self):
        item = self.categories[0].items[0]
        details = LibraryItemDialog(None, item)
        self.addCleanup(details.deleteLater)
        self.assertEqual(details.variants(), {"Niveau": "A"})
        details._combos["Niveau"].setCurrentIndex(1)
        self.assertEqual(details.variants(), {"Niveau": "B"})


@unittest.skipIf(import_svg is None, "PyQt6 non importable ici")
class LibraryControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_import_puts_each_role_on_its_layer(self):
        layers = LayersModel()
        layers.load_list([])                     # les trois calques de base : gravure, découpe, marquage
        added = []
        controller = LibraryController(None, layers, bed_height=lambda: 300.0,
                                       add_to_vector_editor=added.extend, roots=lambda: [LIBRARY])
        item = next(i for c in controller.catalog() for i in c.items if i.key == "trophees/totem-brevet-aviron")
        objects = controller.import_item(item)
        self.assertEqual(objects, added)
        by_role = {layer.role: layer.id for layer in layers.layers if getattr(layer, "role", None)}
        layer_ids = {o.layer_id for o in objects}
        self.assertEqual(layer_ids, {by_role["cut"], by_role["engrave"]})

    def test_open_with_an_empty_library_says_so(self):
        layers = LayersModel()
        layers.load_list([])
        with tempfile.TemporaryDirectory() as empty, \
                mock.patch("laser_studio.controllers.library.QMessageBox.information") as info:
            LibraryController(None, layers, bed_height=lambda: 300.0, add_to_vector_editor=list,
                              roots=lambda: [empty]).open()
        info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
