"""Import SVG qui garde la structure du fichier (vector/svg_tree_import.py), d'après la spécification SVG :
groupes, styles en cascade et héritage (vector/svg_style.py), visibilité, opacité, règle de remplissage,
<use>, <switch>, <svg> imbriqué, viewBox ; calque d'après la couleur, textes modifiables, éléments cachés
sur le calque « Ignoré », blanc qui efface la gravure ; puis les données de gravure (vector/layer_data.py)
et le bouton Importer de l'éditeur."""
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPainterPath
    from PyQt6.QtWidgets import QApplication
    from laser_studio.controllers.vector_editor import VectorEditorController
    from laser_studio.models.layers import LayersModel
    from laser_studio.models.machine import MachineConfig
    from laser_studio.models.vector_document import VectorDocument
    from laser_studio.models.vector_objects import IGNORED_LAYER_ID, GroupObject, TextObject
    from laser_studio.ui.vector_editor.canvas import VectorCanvasView
    from laser_studio.vector import boolean_ops
    from laser_studio.vector.layer_data import extract_vector_layer_data
    from laser_studio.vector.svg_import import ROLE_CUT, ROLE_ENGRAVE, ROLE_MARK
    from laser_studio.vector.svg_import import _document_transform
    from laser_studio.vector.svg_style import StyleSheet, computed_style, parse_color
    from laser_studio.vector.svg_tree_import import LIGHT, color_role, import_svg_tree, svg_tree_counts
    import xml.etree.ElementTree as ET
    from job_fakes import FakeDialogs
except ImportError:  # PyQt6 manquant
    import_svg_tree = None

# Une plaque noire avec un titre blanc ; un groupe de découpe caché (rouge) ; un groupe de variantes dont une
# seule est visible ; un trait vert de marquage.
MEDAL = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
  width="60mm" height="40mm" viewBox="0 0 60 40">
  <g inkscape:groupmode="layer" id="layer1" inkscape:label="Découpe" style="display:none">
    <rect id="r1" inkscape:label="Contour" x="0" y="0" width="60" height="40" style="fill:#ff0000"/>
  </g>
  <g inkscape:groupmode="layer" id="layer2" inkscape:label="Gravure">
    <rect id="r2" inkscape:label="Bandeau" x="5" y="5" width="50" height="12" style="fill:#000000"/>
    <path id="p1" d="M 5 30 L 55 30" style="fill:none;stroke:#00a000;stroke-width:0.5"/>
  </g>
  <g inkscape:groupmode="layer" id="layer3" inkscape:label="Personnalisation" transform="translate(1,0)">
    <text id="t1" inkscape:label="Titre" x="29" y="14" style="font-size:8px;font-family:Sans;text-anchor:middle;fill:#ffffff">ABC</text>
    <g id="g1" inkscape:label="Résultat">
      <text id="t2" x="29" y="36" style="font-size:6px;font-family:Sans;fill:#000000">1</text>
      <text id="t3" x="29" y="36" style="font-size:6px;font-family:Sans;fill:#000000;display:none">2</text>
    </g>
  </g>
</svg>
"""

LAYERS = {ROLE_ENGRAVE: "E", ROLE_CUT: "C", ROLE_MARK: "M", None: "D"}


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class ColorTests(unittest.TestCase):
    def test_colors_with_a_tolerance(self):
        for color, role in (("#000000", ROLE_ENGRAVE), ("#333333", ROLE_ENGRAVE), ("#ff0000", ROLE_CUT),
                            ("#e8301c", ROLE_CUT), ("#00ff00", ROLE_MARK), ("#2e9d3a", ROLE_MARK),
                            ("#ffffff", LIGHT), ("#f4f4f4", LIGHT), ("black", ROLE_ENGRAVE), ("red", ROLE_CUT),
                            ("darkred", ROLE_CUT), ("forestgreen", ROLE_MARK), ("rgb(100%, 0%, 0%)", ROLE_CUT),
                            ("hsl(120, 100%, 30%)", ROLE_MARK), ("#000f", ROLE_ENGRAVE)):
            self.assertEqual(color_role(color), role, color)
        for color in ("none", "url(#degrade)", "#ffcc00", "#a020f0", "#0000ff", "transparent", "#ff000000"):
            self.assertIsNone(color_role(color), color)
        self.assertEqual(color_role("currentColor", "red"), ROLE_CUT)

    def test_color_syntaxes(self):
        self.assertEqual(parse_color("#f00"), (255, 0, 0, 1.0))
        self.assertEqual(parse_color("rgba(0, 0, 255, 0.5)"), (0, 0, 255, 0.5))
        self.assertEqual(parse_color("hsl(0, 100%, 50%)"), (255, 0, 0, 1.0))
        self.assertEqual(parse_color("cornflowerblue"), (100, 149, 237, 1.0))
        self.assertAlmostEqual(parse_color("#ff000080")[3], 128 / 255)
        self.assertIsNone(parse_color("pas une couleur"))


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class CascadeTests(unittest.TestCase):
    def test_presentation_sheet_style_and_inheritance(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg"><style>.a { fill: green } #x { stroke: red !important }'
            ' rect.a { stroke-width: 3 }</style>'
            '<g fill="blue" opacity="0.5" display="inline"><rect id="x" class="a" fill="black" '
            'style="stroke: blue; fill: inherit"/></g></svg>')
        sheet = StyleSheet.from_root(root)
        group = root[1]
        rect = group[0]
        group_style = computed_style(group, {}, sheet)
        style = computed_style(rect, group_style, sheet)
        self.assertEqual(style["fill"], "blue")              # inherit : celui du groupe
        self.assertEqual(style["stroke"], "red")             # !important de la feuille l'emporte
        self.assertEqual(style["stroke-width"], "3")
        self.assertNotIn("opacity", style)                   # ne s'hérite pas
        self.assertNotIn("display", style)

    def test_viewbox_keeps_proportions(self):
        root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" '
                             'viewBox="0 0 10 10"/>')
        point = _document_transform(root).map(QPointF(10, 10))
        self.assertAlmostEqual(point.x(), 75.0)              # xMidYMid meet : 5 mm/unité, centré
        self.assertAlmostEqual(point.y(), 50.0)
        root.set("preserveAspectRatio", "none")
        point = _document_transform(root).map(QPointF(10, 10))
        self.assertAlmostEqual(point.x(), 100.0)


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class TreeImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(MEDAL)
        self.addCleanup(os.remove, self.path)
        self.objects = import_svg_tree(self.path, LAYERS.get, bed_h_mm=100.0)

    def test_layers_and_groups_are_kept(self):
        self.assertEqual([o.name for o in self.objects], ["Découpe", "Gravure", "Personnalisation"])
        self.assertTrue(all(isinstance(o, GroupObject) for o in self.objects))
        gravure = self.objects[1]
        self.assertEqual([getattr(c, "name", "") for c in gravure.children], ["Bandeau", ""])
        self.assertEqual([c.layer_id for c in gravure.children], ["E", "M"])     # noir, vert
        result = self.objects[2].children[1]
        self.assertEqual(result.name, "Résultat")

    def test_hidden_elements_are_ignored_but_remember_their_layer(self):
        cut = self.objects[0]
        self.assertTrue(cut.is_ignored())
        self.assertEqual(cut.children[0].saved_layer_id, "C")                  # rouge : découpe
        one, two = self.objects[2].children[1].children
        self.assertFalse(one.is_ignored())
        self.assertTrue(two.is_ignored())
        two.set_ignored(False)
        self.assertEqual(two.layer_id, "E")

    def test_texts_are_editable_and_white_is_ignored(self):
        title = self.objects[2].children[0]
        self.assertIsInstance(title, TextObject)
        self.assertEqual((title.text, title.name), ("ABC", "Titre"))
        # Le blanc n'est pas une couleur de laser : ignoré, il garde le calque par défaut pour le X.
        self.assertTrue(title.is_ignored())
        self.assertEqual(title.saved_layer_id, "D")
        # Titre de 8 px de haut environ, centré sur le bandeau (x 5..55 décalé de 1 mm par le calque).
        box = title.world_path().boundingRect()
        self.assertAlmostEqual(box.center().x(), 30.0, delta=1.0)
        self.assertTrue(4.0 < box.height() < 8.5)

    def test_outlined_text_takes_the_stroke_colour(self):
        handle, path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="50mm" height="20mm" viewBox="0 0 50 20">'
                    '<text x="2" y="15" style="font-size:12px;fill:none;stroke:red">AB</text></svg>')
        self.addCleanup(os.remove, path)
        text = import_svg_tree(path, LAYERS.get, bed_h_mm=100.0)[0]
        self.assertEqual((text.layer_id, text.is_ignored()), ("C", False))       # lettres à découper

    def test_counts(self):
        layers = LayersModel()
        objects = import_svg_tree(self.path, lambda role: layers.layer_for_role(role).id, 100.0)
        counts = svg_tree_counts(objects, layers)
        self.assertEqual((counts["count"], counts["hidden"]), (6, 3))             # 2 cachés + le titre blanc

    def test_engraving_keeps_each_object(self):
        layers = LayersModel()
        engrave = layers.layer_for_role(ROLE_ENGRAVE).id
        objects = import_svg_tree(self.path, lambda role: layers.layer_for_role(role).id, 100.0)
        data = extract_vector_layer_data(objects, layers, optimize_path=False)
        self.assertEqual(len(data[engrave]["polygon_groups"]), 2)                # bandeau et « 1 », sans le titre
        cut = layers.layer_for_role(ROLE_CUT).id
        self.assertEqual(data[cut]["polygon_groups"], [])                          # découpe cachée


SPEC = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="100mm" height="100mm" viewBox="0 0 100 100">
  <defs><symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol>
    <circle id="c" r="2" fill="red"/></defs>
  <g visibility="hidden"><rect x="0" y="0" width="5" height="5"/>
    <rect visibility="visible" x="10" y="0" width="5" height="5"><title>Visible</title></rect></g>
  <g opacity="0.5"><rect opacity="0" x="20" y="0" width="5" height="5"/></g>
  <path fill-rule="nonzero" d="M 0 20 H 30 V 50 H 0 Z M 10 30 H 20 V 40 H 10 Z"/>
  <path fill-rule="evenodd" d="M 40 20 H 70 V 50 H 40 Z M 50 30 H 60 V 40 H 50 Z"/>
  <use xlink:href="#c" x="80" y="80"/>
  <use href="#s" x="60" y="60" width="20" height="20"/>
  <switch><rect x="0" y="90" width="5" height="5"/><rect x="10" y="90" width="5" height="5"/></switch>
  <svg x="40" y="80" width="10" height="10" viewBox="0 0 1 1"><rect width="1" height="1"/></svg>
  <rect x="90" y="0" width="5" height="5" fill="black" fill-opacity="0" stroke="none"/>
</svg>
"""


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class SpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        handle, path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(SPEC)
        self.addCleanup(os.remove, path)
        self.objects = import_svg_tree(path, LAYERS.get, bed_h_mm=100.0)

    @staticmethod
    def box(obj):
        rect = obj.world_path().boundingRect()      # repère éditeur : Y vers le haut, bed_h = 100
        return (round(rect.left(), 2), round(100 - rect.bottom(), 2), round(rect.width(), 2),
                round(rect.height(), 2))

    def test_visibility_is_inherited_but_can_be_restored(self):
        group = self.objects[0]
        self.assertTrue(group.children[0].is_ignored())
        visible = group.children[1]
        self.assertFalse(visible.is_ignored())
        self.assertEqual(visible.name, "Visible")                       # <title>

    def test_cumulated_opacity_hides(self):
        self.assertTrue(self.objects[1].is_ignored())

    def test_fill_rules(self):
        nonzero, evenodd = self.objects[2], self.objects[3]
        self.assertTrue(nonzero.world_path().contains(QPointF(15, 100 - 35)))     # nonzero : centre plein
        self.assertFalse(evenodd.world_path().contains(QPointF(55, 100 - 35)))    # evenodd : centre vide

    def test_use_symbol_switch_and_nested_svg(self):
        circle, symbol, switch, nested = self.objects[4:8]
        self.assertEqual(circle.children[0].layer_id, "C")                        # rouge du <circle> référencé
        self.assertEqual(self.box(circle), (78.0, 78.0, 4.0, 4.0))
        self.assertEqual(self.box(symbol), (60.0, 60.0, 20.0, 20.0))              # viewBox du <symbol>
        self.assertEqual(self.box(switch), (0.0, 90.0, 5.0, 5.0))                 # premier enfant seulement
        self.assertEqual(self.box(nested), (40.0, 80.0, 10.0, 10.0))

    def test_transparent_fill_is_not_imported(self):
        self.assertEqual(len(self.objects), 8)


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class PaintRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_order_of_painting(self):
        big, small, dot = QPainterPath(), QPainterPath(), QPainterPath()
        big.addRect(0, 0, 40, 40)
        small.addRect(10, 10, 20, 20)
        dot.addEllipse(QPointF(20, 20), 3, 3)
        region = boolean_ops.paint_region([(big, False), (small, True), (dot, False)])
        self.assertTrue(region.contains(QPointF(5, 5)))
        self.assertFalse(region.contains(QPointF(12, 12)))     # effacé par le blanc
        self.assertTrue(region.contains(QPointF(20, 20)))      # regravé par-dessus
        self.assertTrue(boolean_ops.paint_region([(small, True)]).isEmpty())


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class ImportButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_import_file_keeps_the_structure(self):
        handle, path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(MEDAL)
        self.addCleanup(os.remove, path)
        layers = LayersModel()
        document = VectorDocument()
        canvas = VectorCanvasView(layers, document=document)
        self.addCleanup(canvas.deleteLater)
        canvas.set_work_area(300.0, 200.0)
        dialogs = FakeDialogs()
        editor = VectorEditorController(document, canvas, layers, MachineConfig(), dialogs)
        editor.import_file(path)
        self.assertEqual([o.name for o in document.objects], ["Découpe", "Gravure", "Personnalisation"])
        self.assertTrue(canvas.item_for(document.objects[0]).inactive)            # calque caché : ignoré
        self.assertFalse(canvas.item_for(document.objects[1]).inactive)
        self.assertNotIn(IGNORED_LAYER_ID, {o.layer_id for o in document.objects[1:]})


MORE = """<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">
  <defs>
    <clipPath id="disc"><circle cx="20" cy="20" r="10"/></clipPath>
    <clipPath id="box" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>
    <mask id="m"><rect x="60" y="0" width="40" height="40" fill="white"/>
      <rect x="70" y="10" width="20" height="20" fill="black"/></mask>
  </defs>
  <rect id="clipped" x="0" y="0" width="40" height="40" clip-path="url(#disc)"/>
  <path id="line" d="M 0 20 H 40" stroke="red" fill="none" clip-path="url(#disc)"/>
  <rect id="half" x="0" y="50" width="20" height="10" clip-path="url(#box)"/>
  <rect id="masked" x="60" y="0" width="40" height="40" mask="url(#m)"/>
  <path id="dash" d="M 0 80 H 30" stroke="red" fill="none" stroke-dasharray="5 5"/>
  <rect id="units" x="5mm" y="0" width="10mm" height="50%" fill="black" transform="translate(0,0)"/>
  <rect id="css" x="0" y="0" width="10" height="10" style="transform: translate(50px, 50px) rotate(90deg)"/>
</svg>
"""


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class SpecTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        handle, path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write(MORE)
        self.addCleanup(os.remove, path)
        self.objects = import_svg_tree(path, LAYERS.get, bed_h_mm=100.0)

    @staticmethod
    def at(obj, x, y):
        return obj.world_path().contains(QPointF(x, 100 - y))       # coordonnées SVG (Y vers le bas)

    @staticmethod
    def box(obj):
        rect = obj.world_path().boundingRect()
        return [round(v, 1) for v in (rect.left(), 100 - rect.bottom(), rect.width(), rect.height())]

    def test_clip_path(self):
        clipped, line = self.objects[0], self.objects[1]
        self.assertTrue(self.at(clipped, 20, 20))
        self.assertFalse(self.at(clipped, 3, 3))                              # coin hors du disque
        self.assertEqual(self.box(clipped), [10.0, 10.0, 20.0, 20.0])
        self.assertEqual(line.layer_id, "C")
        self.assertAlmostEqual(self.box(line)[2], 20.0, delta=0.2)          # découpe gardée dans le disque

    def test_clip_path_in_bounding_box_units(self):
        self.assertEqual(self.box(self.objects[2]), [0.0, 50.0, 10.0, 10.0])

    def test_mask(self):
        masked = self.objects[3]
        self.assertTrue(self.at(masked, 62, 2))
        self.assertFalse(self.at(masked, 80, 20))                             # noir du masque : caché

    def test_dashes(self):
        dash = self.objects[4]
        polygons = dash.world_path().toSubpathPolygons()
        self.assertEqual(len(polygons), 3)                                   # 30 mm en 5 plein / 5 vide

    def test_units_and_percentages(self):
        # 1 mm = 96 / 25,4 unités ; le viewBox fait 1 unité = 1 mm : 5mm -> 18,9 unités = 18,9 mm.
        self.assertEqual(self.box(self.objects[5]), [18.9, 0.0, 37.8, 50.0])

    def test_css_transform(self):
        self.assertEqual(self.box(self.objects[6]), [40.0, 50.0, 10.0, 10.0])


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_lengths(self):
        from laser_studio.vector.svg_geometry import dash_pattern, transform_origin, user_length
        self.assertAlmostEqual(user_length("1in"), 96.0)
        self.assertAlmostEqual(user_length("50%", "x", (200, 100)), 100.0)
        self.assertAlmostEqual(user_length("2em", font_size=10), 20.0)
        self.assertEqual(dash_pattern({"stroke-dasharray": "4"}), ([4.0, 4.0], 0.0))
        self.assertIsNone(dash_pattern({"stroke-dasharray": "4 -1"}))
        self.assertEqual(transform_origin("center", (100, 50)), (50.0, 25.0))
        self.assertEqual(transform_origin("right bottom", (100, 50)), (100.0, 50.0))

    def test_px_resolution(self):
        from laser_studio.vector.svg_tree_import import document_px_mm
        for head, expected in (('<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" inkscape:version="0.91 r13725"/>', 90),
                               ('<!-- Generator: Adobe Illustrator 27.0 --><svg xmlns="http://www.w3.org/2000/svg"/>', 72),
                               ('<svg xmlns="http://www.w3.org/2000/svg"/>', 96)):
            handle, path = tempfile.mkstemp(suffix=".svg")
            with os.fdopen(handle, "w", encoding="utf-8") as f:
                f.write(head)
            self.addCleanup(os.remove, path)
            self.assertAlmostEqual(document_px_mm(path, ET.parse(path).getroot()), 25.4 / expected)

    def test_tiny_arcs_stay_round(self):
        import math
        from PyQt6.QtGui import QTransform
        from laser_studio.vector.svg_extract import _svg_path_element_to_single
        circle = _svg_path_element_to_single("M0 0 a0.05 0.05 0 1 0 0.1 0 a0.05 0.05 0 1 0 -0.1 0")
        big = QTransform.fromScale(1000, 1000).map(circle)
        points = [p for poly in big.toSubpathPolygons(QTransform()) for p in poly]
        self.assertLess(max(abs(math.hypot(p.x() - 50, p.y()) - 50) for p in points), 0.1)


@unittest.skipIf(import_svg_tree is None, "PyQt6 non importable ici")
class BoxDecorTests(unittest.TestCase):
    """Décor SVG d'une face de boîte (vector/importers.py) : lu par l'importeur conforme à la spécification."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_transforms_hidden_parts_and_defs(self):
        from types import SimpleNamespace
        from laser_studio.vector.importers import BoxDecor, decor_to_objects
        handle, path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20">'
                    '<defs><rect id="pas_dessine" width="100" height="100"/></defs>'
                    '<g transform="translate(20,0)"><rect width="10" height="10"/></g>'
                    '<rect width="10" height="10"/>'
                    '<rect x="30" width="5" height="5" style="display:none"/></svg>')
        self.addCleanup(os.remove, path)
        panel = SimpleNamespace(face_center=lambda: (50.0, 50.0))
        objects = decor_to_objects(BoxDecor(face="front", kind="svg", svg_path=path), panel, "E", 100.0, 0, 0)
        self.assertEqual(len(objects), 1)
        box = objects[0].world_path().boundingRect()
        # Les deux carrés, le second décalé de 20 mm par son groupe ; ni <defs>, ni le carré caché.
        self.assertEqual((round(box.width(), 2), round(box.height(), 2)), (30.0, 10.0))
        self.assertAlmostEqual(box.center().x(), 50.0, places=2)
        self.assertEqual(objects[0].layer_id, "E")


if __name__ == "__main__":
    unittest.main()
