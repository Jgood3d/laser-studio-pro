"""Bibliothèque de modèles : catalogue (library/catalog.py), fiche et import des modèles
(vector/svg_import.py, vector/svg_tree_import.import_library_svg), fenêtres (ui/dialogs/library) et import
dans les calques (controllers/library.py)."""
import json
import os
import xml.etree.ElementTree as ET
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
LIBRARY = os.path.join(REPO, "src", "laser_studio", "resources", "library")
TOTEM = os.path.join(LIBRARY, "trophees", "totem-sportif-modele-1", "totem-sportif-modele-1.svg")
TOTEM2 = os.path.join(LIBRARY, "trophees", "totem-sportif-modele-2", "totem-sportif-modele-2.svg")
MEDAL = os.path.join(LIBRARY, "medailles", "medaille-sportive-modele-1", "medaille-sportive-modele-1.svg")
MEDAL2 = os.path.join(LIBRARY, "medailles", "medaille-sportive-modele-2", "medaille-sportive-modele-2.svg")
ORNAMENT = os.path.join(LIBRARY, "noel", "boule-de-noel-prenom", "boule-de-noel-prenom.svg")
KEYCHAIN = os.path.join(LIBRARY, "porte-clefs", "porte-clef-sportif-modele-1", "porte-clef-sportif-modele-1.svg")
KEYCHAIN2 = os.path.join(LIBRARY, "porte-clefs", "porte-clef-sportif-modele-2", "porte-clef-sportif-modele-2.svg")

from laser_studio.library.catalog import load_catalog, pretty_name  # noqa: E402

try:
    from PyQt6.QtWidgets import QApplication, QDialog
    from laser_studio.controllers.library import LibraryController
    from laser_studio.models.layers import LayersModel
    from laser_studio.ui.dialogs.library import LibraryDialog, LibraryItemDialog
    from laser_studio.ui.dialogs.library.thumbnails import (
        BURN_COLOR, MATERIAL_COLOR, item_image, render_artwork,
    )
    from laser_studio.models.vector_objects import IGNORED_LAYER_ID
    from laser_studio.vector.svg_import import (
        document_size_mm, find_variant_groups, parse_transform, role_of_label,
        TextChange, find_texts, svg_preview,
    )
    from laser_studio.vector.svg_tree_import import import_library_svg as import_svg
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


INK = "http://www.inkscape.org/namespaces/inkscape"


def layer(name, body, hidden=False, extra=""):
    style = ' style="display:none"' if hidden else ""
    return f'<g inkscape:groupmode="layer" inkscape:label="{name}"{style} {extra}>{body}</g>'


def cut(body, extra=""):
    return layer("Cut", body, extra=extra)


def engrave(body, extra=""):
    return layer("Engrave", body, extra=extra)


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
        self.assertIn("trophees/totem-sportif-modele-1", keys)


def leaves(objects):
    for obj in objects:
        children = getattr(obj, "children", None)
        if children:
            yield from leaves(children)
        else:
            yield obj


def read_model(path, variants=None, texts=None):
    """Import d'un modèle comme le fait la bibliothèque, à plat ; le calque de chaque objet est son rôle."""
    return list(leaves(import_svg(path, lambda role: role, 0.0, variants=variants, texts=texts)))


def roles(objects):
    return sorted({o.layer_id for o in objects if o.layer_id in ("cut", "engrave", "mark")})


def box(objects, role):
    """Rectangle englobant des objets du rôle `role` (mm, repère de l'éditeur)."""
    rect = None
    for obj in objects:
        if obj.layer_id == role:
            r = obj.world_path().boundingRect()
            rect = r if rect is None else rect.united(r)
    return rect


def subpaths(objects, role):
    return sum(len(o.world_path().toSubpathPolygons()) for o in objects if o.layer_id == role)


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

    def test_units_transforms_and_hidden_elements(self):
        # viewBox de 200 unités pour 100 mm : 1 unité = 0,5 mm ; calque décalé de 20 unités.
        path = self.file(
            cut('<rect x="0" y="0" width="40" height="20" fill="none" stroke="red"/>'
                '<rect x="0" y="80" width="10" height="20" stroke="red" display="none"/>',
                'transform="translate(20,0)"')
            + '<g inkscape:label="Cut" style="display:none"><circle cx="5" cy="5" r="50" stroke="red"/></g>',
            w="100mm", h="50mm", vb="0 0 200 100")
        objects = read_model(path)
        self.assertEqual(roles(objects), ["cut"])
        cut_box = box(objects, "cut")
        self.assertAlmostEqual(cut_box.width(), 20.0, delta=0.5)                 # trait compris
        self.assertAlmostEqual(cut_box.height(), 10.0, delta=0.5)

    def test_the_colour_decides_the_layer_and_white_is_ignored(self):
        """Comme le bouton « Importer » : rouge = découpe, noir = gravure, vert = marquage ; le blanc ne creuse
        plus la gravure (il va sur le calque « Ignoré ») : les modèles font de vraies Différences."""
        path = self.file(
            cut('<rect width="10" height="10" fill="none" stroke="red"/>')
            + engrave('<rect x="20" width="10" height="10" fill="#000"/>'
                      '<rect x="22" y="2" width="4" height="4" fill="#fff"/>')
            + '<g inkscape:label="Mark"><rect x="40" width="10" height="10" fill="none" stroke="#00ff00"/></g>')
        objects = read_model(path)
        self.assertEqual(roles(objects), ["cut", "engrave", "mark"])
        self.assertEqual(subpaths(objects, "engrave"), 1)                           # pas de trou creusé
        self.assertIn(IGNORED_LAYER_ID, {o.layer_id for o in objects})
        self.assertEqual((role_of_label(" CUT "), role_of_label("Engrave")), ("cut", "engrave"))
        for name in ("Découpe", "Gravure", "Trou", "Contour", "Cutting"):
            self.assertIsNone(role_of_label(name), name)

    def test_options_are_sublayers_and_the_layer_name_is_the_option(self):
        path = self.file(engrave(
            '<g inkscape:label="Niveau">'
            + layer("Petit", '<rect width="10" height="10"/>', hidden=True)
            + layer("Grand", '<rect width="40" height="40"/>') + '</g>'))
        groups = find_variant_groups(path)
        self.assertEqual([(g.key, [o[0] for o in g.options], g.default) for g in groups],
                         [("Niveau", ["Petit", "Grand"], "Grand")])
        self.assertAlmostEqual(box(read_model(path), "engrave").width(), 40, places=3)
        small = read_model(path, variants={"Niveau": "Petit"})
        self.assertAlmostEqual(box(small, "engrave").width(), 10, places=3)
        self.assertIn(b"display:none", svg_preview(path, {"Niveau": "Grand"}))

    def test_groups_with_the_same_name_form_one_choice(self):
        # « Forme » dans Cut et « Forme » dans Engrave : un seul choix, appliqué aux deux.
        path = self.file(
            cut('<g inkscape:label="Forme">'
                + layer("Ronde", '<circle cx="20" cy="20" r="20" fill="none" stroke="red" stroke-width="0.1"/>')
                + layer("Carrée", '<rect width="60" height="60" fill="none" stroke="red" stroke-width="0.1"/>',
                        hidden=True) + '</g>')
            + engrave('<g inkscape:label="Forme">'
                      + layer("Ronde", '<circle cx="20" cy="20" r="5"/>')
                      + layer("Carrée", '<rect width="30" height="30"/>', hidden=True) + '</g>'))
        groups = find_variant_groups(path)
        self.assertEqual([(g.key, [o[0] for o in g.options], g.default) for g in groups],
                         [("Forme", ["Ronde", "Carrée"], "Ronde")])
        square = read_model(path, variants={"Forme": "Carrée"})
        self.assertAlmostEqual(box(square, "cut").width(), 60, delta=0.2)
        self.assertAlmostEqual(box(square, "engrave").width(), 30, places=2)

    def test_a_group_without_visible_option_is_not_a_choice(self):
        path = self.file(cut('<g inkscape:label="Forme">'
                             + layer("Ronde", '<circle cx="20" cy="20" r="20" fill="none"/>', hidden=True)
                             + layer("Carrée", '<rect width="60" height="60" fill="none"/>', hidden=True)
                             + '</g>'))
        self.assertEqual(find_variant_groups(path), [])

    def test_named_elements_alone_are_not_options(self):
        path = self.file(engrave('<g inkscape:label="Niveau"><rect inkscape:label="A" width="10" height="10"/>'
                                 '<rect inkscape:label="B" width="20" height="10" style="display:none"/></g>'))
        self.assertEqual(find_variant_groups(path), [])

    def test_an_option_can_change_cut_and_engrave(self):
        # Option à la racine : chaque forme a ses propres calques Cut et Engrave.
        red = 'fill="none" stroke="red" stroke-width="0.1"'
        path = self.file('<g inkscape:label="Forme">'
                         + layer("Ronde", cut(f'<circle cx="20" cy="20" r="20" {red}/>')
                                 + engrave('<circle cx="20" cy="20" r="5"/>'))
                         + layer("Carrée", cut(f'<rect width="60" height="60" {red}/>')
                                 + engrave('<rect x="20" y="20" width="5" height="5"/>'), hidden=True)
                         + '</g>')
        self.assertAlmostEqual(box(read_model(path), "cut").width(), 40, delta=0.2)
        square = read_model(path, variants={"Forme": "Carrée"})
        self.assertAlmostEqual(box(square, "cut").width(), 60, delta=0.2)
        self.assertEqual(roles(square), ["cut", "engrave"])

    def test_text_becomes_an_editable_text_object(self):
        path = self.file(engrave('<text x="50" y="30" style="font-size:10px;text-anchor:middle;font-weight:bold">'
                                 '<tspan x="50" y="30">Bonjour</tspan></text>'))
        (obj,) = read_model(path)
        self.assertEqual((obj.layer_id, obj.kind, obj.text, obj.bold), ("engrave", "text", "Bonjour", True))

    def test_text_is_placed_where_the_svg_draws_it(self):
        # Rectangle de 100 x 50 mm, texte centré au milieu : il reste au milieu.
        path = self.file(cut('<rect width="100" height="50" fill="none" stroke="red" stroke-width="0.1"/>')
                         + engrave('<text x="50" y="30" style="font-size:10px;text-anchor:middle">Milieu</text>'))
        objects = read_model(path)
        text = next(o for o in objects if o.kind == "text").world_path().boundingRect()
        self.assertAlmostEqual(text.center().x(), box(objects, "cut").center().x(), delta=0.5)

    def test_parse_transform_order(self):
        t = parse_transform("translate(10,0) scale(2)")
        p = t.map(1.0, 1.0)
        self.assertEqual(p, (12.0, 2.0))

    def test_rounded_rect_and_document_size(self):
        path = self.file(cut('<rect width="30" height="18" ry="4" fill="none" stroke="red"/>'),
                         w="30mm", h="18mm", vb="0 0 30 18")
        self.assertEqual(document_size_mm(path), (30.0, 18.0))
        self.assertEqual(len(read_model(path)), 1)

    def test_strokes_are_engraved_with_their_width(self):
        # Trait noir de 2 mm d'épaisseur sur une ligne de 40 mm (bouts ronds) : 42 x 2 mm gravés.
        path = self.file(engrave('<line x1="10" y1="20" x2="50" y2="20" stroke="#000" stroke-width="2" '
                                 'stroke-linecap="round" fill="none"/>'))
        (obj,) = read_model(path)
        rect = obj.world_path().boundingRect()
        self.assertEqual(obj.layer_id, "engrave")
        self.assertAlmostEqual(rect.width(), 42.0, delta=0.05)
        self.assertAlmostEqual(rect.height(), 2.0, delta=0.05)

    def test_bundled_medal_2_pictograms(self):
        groups = {g.key: g for g in find_variant_groups(MEDAL2)}
        self.assertEqual([o[0] for o in groups["Motif"].options],
                         ["Natation", "Dribble", "Handball", "Water-polo", "Escrime", "Haltérophilie", "Football"])
        for motif, _name in groups["Motif"].options:
            self.assertEqual(roles(read_model(MEDAL2, variants={"Motif": motif})), ["cut", "engrave"], motif)

    def test_a_text_in_a_mask_is_cut_out_and_stays_replaceable(self):
        """Texte qui creuse un bandeau : rangé dans un <mask> du bandeau, il reste un champ de la fiche."""
        path = self.file(engrave(
            '<path d="M 0,0 H 100 V 50 H 0 Z" style="fill:#000" mask="url(#m)"/>'
            '<mask id="m" maskUnits="userSpaceOnUse" x="-100" y="-100" width="300" height="300">'
            '<rect x="-100" y="-100" width="300" height="300" style="fill:#fff"/>'
            '<text id="titre" x="50" y="30" style="font-size:20px;fill:#000;text-anchor:middle">Club</text></mask>'
            '<text id="num" x="50" y="45" style="font-size:8px;fill:#000;text-anchor:middle">1</text>'))
        self.assertEqual([f.key for f in find_texts(path)], ["titre", "num"])
        band = lambda texts: next(o for o in read_model(path, texts=texts) if o.kind == "svg_path")
        self.assertGreater(len(band(None).world_path().toSubpathPolygons()), 1)        # lettres creusées
        self.assertEqual(len(band({"titre": ""}).world_path().toSubpathPolygons()), 1)  # rien à creuser
        self.assertIn("1", [getattr(o, "text", "") for o in read_model(path)])          # texte noir : modifiable

    def test_texts_can_be_replaced(self):
        path = self.file(engrave('<text id="titre" x="10" y="20" style="font-size:8px">Régate de XXXX</text>')
                         + '<text id="hors" x="10" y="40" style="font-size:8px">Hors calque</text>')
        self.assertEqual([(f.key, f.text) for f in find_texts(path)], [("titre", "Régate de XXXX")])
        texts = [o.text for o in read_model(path, texts={"titre": "Régate de Rennes"}) if o.kind == "text"]
        self.assertIn("Régate de Rennes", texts)
        self.assertIn("Régate de Rennes", svg_preview(path, texts={"titre": "Régate de Rennes"}).decode())

    def test_text_fields_give_font_and_size_in_mm(self):
        # viewBox de 200 unités pour 100 mm : une police de 10 unités fait 5 mm.
        path = self.file(engrave('<text id="t" x="10" y="20" style="font-size:10px;font-family:\'DejaVu Sans\';'
                                 'font-weight:bold">Club</text>'), w="100mm", h="50mm", vb="0 0 200 100")
        (field,) = find_texts(path)
        self.assertEqual((field.family, field.size_mm, field.bold), ("DejaVu Sans", 5.0, True))

    def test_font_and_size_can_be_changed(self):
        path = self.file(engrave('<text id="t" x="10" y="20" style="font-size:5px">Club</text>'))
        height = lambda objects: objects[0].world_path().boundingRect().height()
        normal = height(read_model(path))
        double = height(read_model(path, texts={"t": TextChange(size_mm=10.0)}))
        self.assertAlmostEqual(double / normal, 2.0, delta=0.05)
        (obj,) = read_model(path, texts={"t": TextChange(family="DejaVu Serif")})
        self.assertEqual((obj.text, obj.font_family), ("Club", "DejaVu Serif"))
        preview = svg_preview(path, texts={"t": TextChange(family="DejaVu Serif", size_mm=10.0)}).decode()
        self.assertIn("font-family:'DejaVu Serif'", preview)
        self.assertIn("font-size:10.0000px", preview)

    def test_inkscape_line_tspans_are_placed_under_the_text(self):
        # Inkscape enregistre parfois x="0" y="0" sur une ligne : elle s'affiche quand même au x / y du texte.
        path = self.file(cut('<rect width="100" height="50" fill="none" stroke="red" stroke-width="0.1"/>')
                         + engrave('<text id="t" x="50" y="25" style="font-size:10px;text-anchor:middle">'
                                   '<tspan xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
                                   'sodipodi:role="line" x="0" y="0">8</tspan></text>'))
        objects = read_model(path)
        text = next(o for o in objects if o.kind == "text").world_path().boundingRect()
        self.assertAlmostEqual(text.center().x(), box(objects, "cut").center().x(), delta=1.0)
        self.assertIn('x="50"', svg_preview(path).decode())

    def test_bundled_models_follow_the_convention(self):
        """Chaque modèle : calques Cut (rouge) et Engrave, options en sous-calques, et aucun blanc : ce qui est
        en réserve dans la gravure est une vraie Différence (ou un texte dans un masque)."""
        for model in (TOTEM, TOTEM2, MEDAL, MEDAL2, KEYCHAIN, KEYCHAIN2, ORNAMENT):
            root = ET.parse(model).getroot()
            layers = {next((v for k, v in g.attrib.items() if k.endswith("label")), "")
                      for g in root if g.tag.endswith("}g") and "display:none" not in g.attrib.get("style", "")}
            self.assertEqual(layers, {"Cut", "Engrave"}, model)
            cut_layer = next(g for g in root if g.attrib.get(f"{{{INK}}}label") == "Cut")
            for shape in cut_layer.iter():
                if shape.tag.split("}")[-1] in ("path", "rect", "circle"):
                    self.assertIn("stroke:#ff0000", shape.attrib.get("style", ""), model)
            engrave_layer = next(g for g in root if g.attrib.get(f"{{{INK}}}label") == "Engrave")
            masks = {e for m in engrave_layer.iter() if m.tag.endswith("}mask") for e in m.iter()}
            for shape in engrave_layer.iter():
                if shape in masks:
                    continue
                style = shape.attrib.get("style", "").replace(" ", "").lower()
                for white in ("fill:#ffffff", "fill:#fff;", "stroke:#ffffff", "stroke:#fff;"):
                    self.assertNotIn(white, style + ";", (model, shape.attrib.get("id")))

    def test_bundled_totems(self):
        expected = {
            TOTEM: ["Basket-ball (1 contre 1)", "Kayak", "Surf", "Natation", "Course", "Vélo", "Ballon de basket",
                    "Handball", "Volley-ball", "Gymnastique", "Arts martiaux"],
            TOTEM2: ["Natation", "Dribble", "Handball", "Water-polo", "Escrime", "Haltérophilie", "Football"],
        }
        for model, options in expected.items():
            (group,) = find_variant_groups(model)
            self.assertEqual((group.key, [o[0] for o in group.options]), ("Motif", options))
            self.assertEqual([(f.key, f.text) for f in find_texts(model)],
                             [("Titre", "TITRE TOTEM"), ("Sous-titre", "Challenge XXX")])
            for option in options:
                objects = read_model(model, variants={"Motif": option})
                self.assertEqual(roles(objects), ["cut", "engrave"], option)
                outline = box(objects, "cut")
                self.assertAlmostEqual(outline.width(), 30.0, delta=0.3)
                self.assertAlmostEqual(outline.height(), 116.4, delta=0.3)
                for obj in objects:                                         # textes dans la largeur
                    if obj.kind == "text":
                        self.assertLess(obj.world_path().boundingRect().width(), 28.0, obj.text)

    def test_totem_pictogram_is_reserved_in_the_black_circle(self):
        """Le picto est une Différence du rond noir : plus de sous-tracés que le rond seul."""
        for motif in ("Kayak", "Natation"):
            objects = read_model(TOTEM, variants={"Motif": motif})
            self.assertGreater(subpaths([o for o in objects if o.kind == "svg_path"], "engrave"), 4, motif)

    def test_bundled_ornament(self):
        """Boule de Noël : prénom gravé, en police manuscrite (embarquée, ou celle du système dans le
        paquet Fedora), centré sur la boule."""
        from PyQt6.QtGui import QFont, QFontInfo
        from laser_studio.ui.fonts import SCRIPT_FONT, load_bundled_fonts
        load_bundled_fonts()
        self.assertEqual(QFontInfo(QFont(SCRIPT_FONT)).family().split(" [")[0], SCRIPT_FONT)   # « [fabricant] » si en double
        (field,) = find_texts(ORNAMENT)
        self.assertEqual((field.key, field.text, field.family), ("Prénom", "Prénom", SCRIPT_FONT))
        for name in ("Prénom", "Léa", "Joséphine"):
            objects = read_model(ORNAMENT, texts={"Prénom": name})
            text = next(o for o in objects if o.kind == "text")
            self.assertEqual((text.text, text.font_family), (name, SCRIPT_FONT))
            self.assertAlmostEqual(text.world_path().boundingRect().center().x(), box(objects, "cut").center().x(),
                                   delta=0.6)

    def test_bundled_keychains(self):
        expected = {
            KEYCHAIN: (["Aviron (diagonal)", "Aviron (horizontal)", "Basket-ball (1 contre 1)", "Kayak", "Surf",
                        "Natation", "Course", "Vélo", "Ballon de basket", "Handball", "Volley-ball", "Gymnastique",
                        "Arts martiaux"], "Aviron (diagonal)"),
            KEYCHAIN2: (["Natation", "Dribble", "Handball", "Water-polo", "Escrime", "Haltérophilie", "Football"],
                        "Natation"),
        }
        for model, (options, default) in expected.items():
            (group,) = find_variant_groups(model)
            self.assertEqual((group.key, [o[0] for o in group.options], group.default), ("Motif", options, default))
            for option in options:
                objects = read_model(model, variants={"Motif": option})
                self.assertEqual(roles(objects), ["cut", "engrave"], option)
                self.assertEqual(len([o for o in objects if o.layer_id == "cut"]), 2, option)   # contour et trou
                self.assertAlmostEqual(box(objects, "cut").width(), 50.0, delta=0.3)

    def test_bundled_medal(self):
        groups = {g.key: g for g in find_variant_groups(MEDAL)}
        self.assertEqual(list(groups), ["Forme", "Résultat", "Motif"])   # « Forme » de Cut et d'Engrave : un seul choix
        self.assertEqual([o[0] for o in groups["Motif"].options],
                         ["Aviron", "Basket-ball (1 contre 1)", "Kayak", "Surf", "Natation", "Course", "Vélo",
                          "Ballon de basket", "Handball", "Volley-ball", "Gymnastique", "Arts martiaux"])
        self.assertEqual([o[0] for o in groups["Forme"].options], ["Hexagonale", "Ronde"])
        self.assertEqual(groups["Forme"].default, "Hexagonale")
        self.assertEqual([o[0] for o in groups["Résultat"].options], ["Étoile", "1ère place", "2e place", "3e place"])
        self.assertEqual([f.key for f in find_texts(MEDAL)], ["Compétition de XXXX", "1"])
        for shape in ("Hexagonale", "Ronde"):
            objects = read_model(MEDAL, variants={"Forme": shape, "Résultat": "Étoile"},
                                 texts={"Compétition de XXXX": "Régate de Rennes"})
            self.assertEqual(roles(objects), ["cut", "engrave"], shape)
            self.assertEqual(subpaths(objects, "cut"), 2, shape)                  # contour et trou du ruban
        # Motif basket : tient dans la zone du skiffeur, en largeur et en hauteur.
        import xml.etree.ElementTree as ElementTree
        import laser_studio.vector.svg_import as si
        root = ElementTree.parse(MEDAL).getroot()

        def motif_box(motif):
            found = None
            for elem, _d, _role, ctm in si._visible_elements(root, {"Motif": motif}):
                inside = any(e is elem for g in root.iter() if g.attrib.get("id") == f"motif_{motif[:6].lower()}"
                             for e in g.iter())
                geometry = si._shape_path(elem, si._local(elem.tag))
                if inside and geometry is not None:
                    r = (si.parse_transform(elem.attrib.get("transform")) * ctm).map(geometry).boundingRect()
                    found = r if found is None else found.united(r)
            return found
        rower, players = motif_box("Aviron"), motif_box("Basket-ball (1 contre 1)")
        self.assertTrue(rower.contains(players), (rower, players))

    def test_every_medal_motif_fits_the_rower_area(self):
        """Chaque motif (dessin ou pictogramme) tient dans la zone du skiffeur."""
        import xml.etree.ElementTree as ElementTree
        import laser_studio.vector.svg_import as si
        for model in (MEDAL, MEDAL2):
            root = ElementTree.parse(model).getroot()
            motif_group = next(e for e in root.iter() if e.attrib.get("id") == "layer6")
            for option in motif_group:
                name = option.attrib[f"{{{INK}}}label"]
                inside = {id(e) for e in option.iter()}
                found = None
                for elem, _d, _role, ctm in si._visible_elements(root, {"Motif": name}):
                    geometry = si._shape_path(elem, si._local(elem.tag))
                    if id(elem) in inside and geometry is not None:
                        r = (si.parse_transform(elem.attrib.get("transform")) * ctm).map(geometry).boundingRect()
                        found = r if found is None else found.united(r)
                self.assertIsNotNone(found, name)
                # Zone du skiffeur : x 2,98..75,75, y 25,63..44,66 (marge pour les traits épaissis).
                self.assertGreaterEqual(found.left(), 2.5, name)
                self.assertLessEqual(found.right(), 76.3, name)
                self.assertGreaterEqual(found.top(), 25.1, name)
                self.assertLessEqual(found.bottom(), 45.2, name)
                self.assertTrue(read_model(model, variants={"Motif": name}), name)

    def test_round_medal_is_concentric(self):
        """Découpe ronde concentrique à la gravure ronde (même centre)."""
        objects = read_model(MEDAL, variants={"Forme": "Ronde", "Motif": "Basket-ball (1 contre 1)"})
        cut_box = box(objects, "cut")
        engrave_box = max((o.world_path().boundingRect() for o in objects
                           if o.layer_id == "engrave" and o.kind == "svg_path"), key=lambda r: r.width())
        self.assertAlmostEqual(cut_box.width(), cut_box.height(), places=1)           # un cercle
        self.assertAlmostEqual(cut_box.center().x(), engrave_box.center().x(), places=1)


@unittest.skipIf(import_svg is None, "PyQt6 non importable ici")
class PreviewTests(unittest.TestCase):
    """Aperçu calculé : matière dans la découpe, trous transparents, gravure brûlée."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_material_holes_and_engraving(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.svg")
            # Plaque de 100 x 50 mm, trou de 10 mm à gauche, carré gravé de 10 mm à droite.
            write(path, svg(cut('<rect width="100" height="50" fill="none" stroke="red" stroke-width="0.01"/>'
                                '<circle cx="20" cy="25" r="5" fill="none" stroke="red" stroke-width="0.01"/>')
                            + engrave('<rect x="70" y="20" width="10" height="10"/>')))
            image = render_artwork(import_svg(path, lambda role: role, 0.0), 104, margin_px=2)     # 1 px par mm
        pixel = lambda x, y: image.pixelColor(x + 2, y + 2)
        self.assertEqual(pixel(20, 25).alpha(), 0)                        # trou : transparent
        self.assertEqual(pixel(45, 10).rgb(), MATERIAL_COLOR.rgb())       # matière
        self.assertEqual(pixel(75, 25).rgb(), BURN_COLOR.rgb())           # gravure

    def test_preview_follows_options_and_texts(self):
        item = next(i for c in load_catalog([LIBRARY]) for i in c.items if i.key.endswith("medaille-sportive-modele-1"))
        hexagonal = item_image(item, 200)
        round_ = item_image(item, 200, {"Forme": "Ronde"})
        self.assertFalse(hexagonal.isNull())
        self.assertNotEqual(hexagonal, round_)
        self.assertNotEqual(item_image(item, 200, texts={"Compétition de XXXX": "Rennes"}), hexagonal)


@unittest.skipIf(import_svg is None, "PyQt6 non importable ici")
class LibraryDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        body = engrave('<g inkscape:label="Niveau">' + layer("A", '<rect width="10" height="10"/>')
                       + layer("B", '<rect width="20" height="10"/>', hidden=True) + '</g>')
        write(os.path.join(self.tmp.name, "medals", "medaille", "m.svg"), svg(body))
        write(os.path.join(self.tmp.name, "signs", "plaque", "p.svg"), svg(engrave('<rect width="5" height="5"/>')))
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
        item, variants, texts = d.chosen()
        self.assertEqual((item.key, variants, texts), ("medals/medaille", {"Niveau": "A"}, {}))
        self.assertEqual(d.result(), QDialog.DialogCode.Accepted)

    def test_details_open_only_once(self):
        """Un double-clic émet itemDoubleClicked puis itemActivated : une seule fiche, et rien
        ne se rouvre après l'import (avant, une seconde fiche vierge s'ouvrait)."""
        d = self.dialog()
        d.grid.setCurrentRow(0)
        opened = []

        def fake_exec(details):
            opened.append(details)
            d.grid.itemActivated.emit(d.grid.currentItem())     # pendant que la fiche est ouverte
            return QDialog.DialogCode.Accepted

        with mock.patch.object(LibraryItemDialog, "exec", fake_exec):
            d.grid.itemDoubleClicked.emit(d.grid.currentItem())
            d.grid.itemActivated.emit(d.grid.currentItem())
        self.assertEqual(len(opened), 1)
        self.assertEqual(d.chosen()[0].key, "medals/medaille")

    def test_details_offer_the_texts(self):
        write(os.path.join(self.tmp.name, "signs", "nom", "n.svg"),
              svg(engrave('<text id="nom" x="10" y="20" style="font-size:8px">Prénom</text>')))
        item = next(i for c in load_catalog([self.tmp.name]) for i in c.items if i.key == "signs/nom")
        details = LibraryItemDialog(None, item)
        self.addCleanup(details.deleteLater)
        self.assertEqual(details.texts(), {})                      # rien de modifié
        edit, font, size, field, _start_family, _start_size = details._text_edits["nom"]
        self.assertEqual(size.value(), field.size_mm)
        edit.setText("Léa")
        self.assertEqual(details.texts(), {"nom": TextChange(text="Léa")})
        size.setValue(12.0)
        self.assertEqual(details.texts(), {"nom": TextChange(text="Léa", size_mm=12.0)})

    def test_untouched_text_with_a_missing_font_is_not_a_change(self):
        """Police absente (remplacée dans la liste) et taille arrondie : pas une modification."""
        write(os.path.join(self.tmp.name, "signs", "num", "n.svg"),
              svg(engrave('<text id="num" x="10" y="20" style="font-size:16.3363px;'
                          'font-family:\'Police Introuvable\'">1</text>')))
        item = next(i for c in load_catalog([self.tmp.name]) for i in c.items if i.key == "signs/num")
        details = LibraryItemDialog(None, item)
        self.addCleanup(details.deleteLater)
        self.assertEqual(details.texts(), {})

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
        controller = LibraryController(layers, bed_height=lambda: 300.0, add_to_vector_editor=added.extend,
                                       dialogs=mock.Mock(), roots=lambda: [LIBRARY])
        item = next(i for c in controller.catalog() for i in c.items if i.key == "trophees/totem-sportif-modele-1")
        objects = controller.import_item(item)
        self.assertEqual(objects, added)
        by_role = {layer.role: layer.id for layer in layers.layers if getattr(layer, "role", None)}
        layer_ids = {o.layer_id for o in leaves(objects)}
        self.assertEqual(layer_ids, {by_role["cut"], by_role["engrave"]})

    def test_empty_library_has_no_page_in_the_generators_window(self):
        layers = LayersModel()
        layers.load_list([])
        with tempfile.TemporaryDirectory() as empty:
            controller = LibraryController(layers, bed_height=lambda: 300.0, add_to_vector_editor=list,
                                           roots=lambda: [empty], dialogs=mock.Mock())
            self.assertIsNone(controller.generator_request())

    def test_chosen_model_is_imported(self):
        layers = LayersModel()
        layers.load_list([])
        added = []
        controller = LibraryController(layers, bed_height=lambda: 300.0, add_to_vector_editor=added.extend,
                                       dialogs=mock.Mock(), roots=lambda: [LIBRARY])
        categories, icon_size, _remember = controller.generator_request()
        self.assertEqual(len(categories), len(controller.catalog()))
        self.assertGreater(icon_size, 0)
        item = next(i for c in categories for i in c.items if i.key == "trophees/totem-sportif-modele-1")
        controller.import_choice((item, None, None))
        self.assertTrue(added)


if __name__ == "__main__":
    unittest.main()
