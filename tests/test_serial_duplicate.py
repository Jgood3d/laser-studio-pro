"""Duplication en série : noms, clones, grille, centrage du texte, dépassement du contour (sans Qt)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))
from laser_studio.vector import serial_duplicate as sd


class Fake:
    """Objet minimal : rectangle w x h ancré par son coin bas-gauche (x_mm, y_mm), comme les vrais objets."""

    def __init__(self, x, y, w, h, text=None):
        self.x_mm, self.y_mm, self.w, self.h, self.text = x, y, w, h, text


class FakeText(Fake):
    """Texte dont la largeur dépend du nombre de caractères (2 mm par lettre)."""

    def __init__(self, x, y, text="PRENOM", h=5.0):
        super().__init__(x, y, 0, h, text)

    @property
    def width(self):
        return 2.0 * len(self.text)


def bounds(o):
    w = o.width if isinstance(o, FakeText) else o.w
    return (o.x_mm, o.y_mm, o.x_mm + w, o.y_mm + o.h)


def clone(o):
    if isinstance(o, FakeText):
        return FakeText(o.x_mm, o.y_mm, o.text, o.h)
    return Fake(o.x_mm, o.y_mm, o.w, o.h, o.text)


def keyring():
    """Un porte-clés : contour 40 x 20 et un prénom au milieu."""
    return [Fake(10, 10, 40, 20), FakeText(20, 15, "PRENOM")]


class NamesTests(unittest.TestCase):
    def test_parse_names_ignores_blank_lines_and_spaces(self):
        self.assertEqual(sd.parse_names("  Léa \n\n Tom\r\n   \nAnna"), ["Léa", "Tom", "Anna"])
        self.assertEqual(sd.parse_names(""), [])
        self.assertEqual(sd.parse_names(None), [])

    def test_copy_count_follows_names_then_count(self):
        self.assertEqual(sd.copy_count(["a", "b", "c"], 10), 3)
        self.assertEqual(sd.copy_count([], 7), 7)
        self.assertEqual(sd.copy_count([], 0), 1)
        self.assertEqual(sd.copy_count([], 10 ** 6), sd.MAX_COPIES)

    def test_default_columns(self):
        self.assertEqual([sd.default_columns(n) for n in (1, 2, 4, 5, 9, 10)], [1, 2, 2, 3, 3, 4])


class BuildCopiesTests(unittest.TestCase):
    def test_copies_are_independent_clones(self):
        objs = keyring()
        copies = sd.build_copies(objs, 3, clone=clone, bounds=bounds)
        self.assertEqual(len(copies), 3)
        self.assertIs(copies[0][0], objs[0])                     # l'exemplaire 0 est l'original
        self.assertIsNot(copies[1][0], objs[0])
        self.assertIsNot(copies[1][0], copies[2][0])
        self.assertEqual([o.text for o in copies[2]], [None, "PRENOM"])

    def test_names_set_one_text_per_copy_including_original(self):
        copies = sd.build_copies(keyring(), 1, clone=clone, bounds=bounds, text_index=1,
                                 names=["Léa", "Tom", "Anna"], keep_center=False)
        self.assertEqual([c[1].text for c in copies], ["Léa", "Tom", "Anna"])

    def test_without_text_index_names_are_ignored(self):
        copies = sd.build_copies(keyring(), 2, clone=clone, bounds=bounds, names=["a", "b", "c"])
        self.assertEqual(len(copies), 2)
        self.assertEqual(copies[1][1].text, "PRENOM")

    def test_keep_center_keeps_text_centered(self):
        copies = sd.build_copies(keyring(), 1, clone=clone, bounds=bounds, text_index=1, names=["Al", "Bartholomew"])
        centers = []
        for c in copies:
            x0, _, x1, _ = bounds(c[1])
            centers.append((x0 + x1) / 2.0)
        self.assertAlmostEqual(centers[0], centers[1])
        self.assertAlmostEqual(centers[0], 20 + 6.0)             # centre de « PRENOM » (12 mm de large) d'origine

    def test_set_text_without_keep_center_keeps_left_anchor(self):
        t = FakeText(20, 15, "PRENOM")
        sd.set_text(t, "Bartholomew", bounds, keep_center=False)
        self.assertEqual(t.x_mm, 20)

    def test_set_text_with_empty_outline_does_not_crash(self):
        t = FakeText(20, 15, "PRENOM")
        sd.set_text(t, "X", lambda o: None, keep_center=True)
        self.assertEqual(t.text, "X")


class GridTests(unittest.TestCase):
    def test_grid_positions_upward(self):
        copies = sd.build_copies(keyring(), 4, clone=clone, bounds=bounds)
        extent = sd.layout_grid(copies, bounds, cols=2, gap_x=5, gap_y=3, upward=True)
        origins = [sd.copy_bounds(c, bounds)[:2] for c in copies]
        self.assertEqual(origins[0], (10, 10))                   # le premier ne bouge pas
        self.assertEqual(origins[1], (10 + 45, 10))
        self.assertEqual(origins[2], (10, 10 + 23))
        self.assertEqual(origins[3], (10 + 45, 10 + 23))
        self.assertEqual(extent, (85, 43))

    def test_grid_downward(self):
        copies = sd.build_copies(keyring(), 3, clone=clone, bounds=bounds)
        sd.layout_grid(copies, bounds, cols=1, gap_x=0, gap_y=2, upward=False)
        ys = [sd.copy_bounds(c, bounds)[1] for c in copies]
        self.assertEqual(ys, [10, 10 - 22, 10 - 44])

    def test_cells_fit_the_largest_copy_so_nothing_overlaps(self):
        copies = sd.build_copies(keyring(), 1, clone=clone, bounds=bounds, text_index=1,
                                 names=["A", "Un nom vraiment très très long", "B"], keep_center=True)
        sd.layout_grid(copies, bounds, cols=3, gap_x=2, gap_y=2)
        boxes = [sd.copy_bounds(c, bounds) for c in copies]
        for a, b in zip(boxes, boxes[1:]):
            self.assertGreaterEqual(b[0] - a[2], 2 - 1e-9)       # au moins l'espacement entre deux voisins

    def test_columns_are_clamped(self):
        copies = sd.build_copies(keyring(), 2, clone=clone, bounds=bounds)
        extent = sd.layout_grid(copies, bounds, cols=10, gap_x=1, gap_y=1)
        self.assertEqual(extent, (81, 20))
        sd.layout_grid(copies, bounds, cols=0, gap_x=1, gap_y=1)  # 0 colonne : ramené à 1

    def test_grid_extent(self):
        self.assertEqual(sd.grid_extent(5, 2, 10, 4, 1, 1), (21, 14))


class OverflowTests(unittest.TestCase):
    def test_overflowing_lists_names_wider_than_the_outline(self):
        copies = sd.build_copies(keyring(), 1, clone=clone, bounds=bounds, text_index=1,
                                 names=["Léa", "Un nom vraiment beaucoup trop long pour le porte-clés"])
        self.assertEqual(sd.overflowing(copies, 1, bounds), [1])

    def test_no_other_object_means_nothing_to_compare(self):
        copies = sd.build_copies([FakeText(0, 0)], 2, clone=clone, bounds=bounds, text_index=0, names=["a", "b"])
        self.assertEqual(sd.overflowing(copies, 0, bounds), [])


if __name__ == "__main__":
    unittest.main()
