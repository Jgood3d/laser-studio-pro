"""Tests de image/matrix.py (recadrage et G-Code d'une zone d'image) — sans Qt."""
import re
import unittest

import numpy as np
from PIL import Image

from image import matrix as mi


def _moves(lines):
    """(commande, x) des lignes G0/G1 ; x en float."""
    out = []
    for line in lines:
        m = re.match(r"(G[01]) X(-?[\d.]+)", line)
        if m:
            out.append((m.group(1), float(m.group(2))))
    return out


class CropBoxTests(unittest.TestCase):
    def test_zone_centree_a_l_echelle_reelle(self):
        # Image de 200 x 100 px représentant 100 mm de large : 2 px/mm ; zone 15 x 15 mm = 30 px.
        box, w_mm, h_mm = mi.crop_box_px(200, 100, 100.0, 15.0, 15.0, 0.5, 0.5)
        self.assertEqual(box, (85, 35, 115, 65))
        self.assertEqual((w_mm, h_mm), (15.0, 15.0))

    def test_la_zone_reste_dans_l_image(self):
        box, _, _ = mi.crop_box_px(200, 100, 100.0, 15.0, 15.0, 0.0, 1.0)
        self.assertEqual(box, (0, 70, 30, 100))
        box, _, _ = mi.crop_box_px(200, 100, 100.0, 15.0, 15.0, 5.0, -3.0)
        self.assertEqual(box, (170, 0, 200, 30))

    def test_zone_plus_grande_que_l_image_est_reduite(self):
        box, w_mm, h_mm = mi.crop_box_px(200, 100, 100.0, 150.0, 80.0, 0.5, 0.5)
        self.assertEqual(box, (0, 0, 200, 100))
        self.assertEqual(w_mm, 100.0)
        self.assertEqual(h_mm, 50.0)      # l'image fait 100 x 50 mm

    def test_rectangle_non_carre(self):
        box, w_mm, h_mm = mi.crop_box_px(200, 100, 100.0, 20.0, 10.0, 0.5, 0.5)
        self.assertEqual((box[2] - box[0], box[3] - box[1]), (40, 20))
        self.assertEqual((w_mm, h_mm), (20.0, 10.0))

    def test_frame_fraction(self):
        fw, fh = mi.frame_fraction(200, 100, 100.0, 15.0, 15.0)
        self.assertAlmostEqual(fw, 0.15)
        self.assertAlmostEqual(fh, 0.30)

    def test_valeurs_invalides(self):
        with self.assertRaises(ValueError):
            mi.crop_box_px(200, 100, 0.0, 15.0, 15.0, 0.5, 0.5)
        with self.assertRaises(ValueError):
            mi.crop_box_px(0, 100, 100.0, 15.0, 15.0, 0.5, 0.5)


class ToGrayTests(unittest.TestCase):
    def test_transparent_devient_blanc(self):
        img = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        img.putpixel((1, 0), (0, 0, 0, 255))
        gray = np.array(mi.to_gray(img))
        self.assertEqual(gray[0, 0], 255)
        self.assertEqual(gray[0, 1], 0)

    def test_couleur_en_gris(self):
        self.assertEqual(mi.to_gray(Image.new("RGB", (2, 2), (255, 255, 255))).mode, "L")


class TileGcodeTests(unittest.TestCase):
    def test_ligne_vide_sautee_et_alternance_aller_retour(self):
        arr = np.array([[0, 0, 255, 255],      # ligne du haut : 2 pixels brûlés à gauche
                        [255, 255, 255, 255],  # vide : sautée
                        [255, 255, 0, 0]],     # ligne du bas : 2 pixels brûlés à droite
                       dtype=np.uint8)
        lines, seconds, samples = mi.tile_raster_gcode(
            arr, x0=10.0, y0=20.0, w_mm=4.0, h_mm=3.0, speed=1000, power_pct=50.0,
            s_max=1000, laser_cmd="M3")
        self.assertEqual(lines.count("M5"), 2)             # deux lignes balayées
        text = "\n".join(lines)
        # Ligne du haut (y=2) : Y = 20 + 2 = 22, aller : 10 -> 12 à S500 (50 % de 1000).
        self.assertIn("G0 X10.000 Y22.000", text)
        self.assertIn("G1 X12.000 F1000 S500", text)
        # Ligne du bas (y=0) : Y = 20, retour : démarre à droite (14) et va jusqu'à 12.
        self.assertIn("G0 X14.000 Y20.000", text)
        self.assertIn("G1 X12.000 F1000 S500", text)
        self.assertEqual(samples, [50.0, 50.0])
        self.assertGreater(seconds, 0)

    def test_surbalayage(self):
        arr = np.array([[0, 0]], dtype=np.uint8)
        lines, _, _ = mi.tile_raster_gcode(
            arr, 5.0, 5.0, 2.0, 1.0, 600, 100.0, 1000, "M4", overscan_dist=2.5)
        self.assertIn("G0 X2.500 Y5.000 ; OVERSCAN_START", lines)
        self.assertIn("G1 X5.000 F600 S0", lines)
        self.assertIn("G1 X7.000 F600 S1000", lines)
        self.assertIn("G1 X9.500 F600 S0 ; OVERSCAN_END", lines)

    def test_decalage_ligne_retour(self):
        arr = np.array([[0, 255], [0, 255]], dtype=np.uint8)
        lines, _, _ = mi.tile_raster_gcode(
            arr, 0.0, 0.0, 2.0, 2.0, 600, 100.0, 1000, "M3", scan_offset=0.1)
        starts = [x for cmd, x in _moves(lines) if cmd == "G0"]
        # Aller : le pixel brûlé commence à X=0 ; retour : décalé de 0,1 mm, il part du bord droit.
        self.assertEqual(starts, [0.0, 1.1])

    def test_niveaux_de_gris_puissance_proportionnelle(self):
        arr = np.array([[0, 128, 255]], dtype=np.uint8)
        lines, _, samples = mi.tile_raster_gcode(
            arr, 0.0, 0.0, 3.0, 1.0, 600, 100.0, 1000, "M3", grayscale=True)
        text = "\n".join(lines)
        self.assertIn("S1000", text)                  # noir : pleine puissance
        self.assertIn("S498", text)                   # gris moyen : ~50 %
        self.assertEqual(len(samples), 2)             # le blanc (255) ne grave pas
        self.assertNotIn("X3.000 F600 S0", text)      # la ligne s'arrête au dernier pixel gravé

    def test_image_vide(self):
        self.assertEqual(mi.tile_raster_gcode(np.zeros((0, 0)), 0, 0, 1, 1, 600, 50, 1000, "M3"),
                         ([], 0.0, []))
        lines, seconds, samples = mi.tile_raster_gcode(
            np.full((4, 4), 255, np.uint8), 0, 0, 4, 4, 600, 50, 1000, "M3")
        self.assertEqual((lines, seconds, samples), ([], 0.0, []))


if __name__ == "__main__":
    unittest.main()
