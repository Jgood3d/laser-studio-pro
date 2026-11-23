"""Image de calibrage du gain de point pour le verre peint (onglet Séparation),
sans Qt : JobController.generate_gain_test la grave."""
import numpy as np
from PIL import Image, ImageDraw

from laser_studio.image import separation as separation_engine
from laser_studio.vector.font import VectorFont

GAIN_TEST_GAINS = (0, 5, 10, 15, 20)              # valeurs du curseur « gain de point » (en %)
GAIN_TEST_TONES = tuple(i / 10.0 for i in range(11))   # 0 % (verre intact) ... 100 % (verre dégagé)


def build_gain_test_array(lines_per_mm, mirror=False, patch_mm=8.0, gap_mm=1.5, label_mm=7.0,
                          gains=GAIN_TEST_GAINS, tones=GAIN_TEST_TONES):
    """Image de calibrage du gain de point pour le verre peint.

    Grille : une LIGNE par valeur de gain (celles du curseur de l'onglet
    Séparation), une COLONNE par ton, de 0 % (peinture intacte) à 100 % (verre
    entièrement dégagé). Chaque case est tramée (Floyd-Steinberg) avec la
    couverture compensée compenser_gain_point(ton, gain) ; les valeurs du
    gain sont gravées à gauche de chaque ligne.
    Renvoie (tableau uint8 : 0 = brûlé, 255 = intact ; largeur_mm ; hauteur_mm).
    mirror=True retourne tout à l'horizontale, pour une gravure vue à travers
    le verre (le texte se lit alors à l'endroit de l'autre côté)."""
    lpm = float(lines_per_mm)

    def px(mm):
        return max(1, int(round(mm * lpm)))

    cell = px(patch_mm)
    gap = px(gap_mm)
    label_w = px(label_mm)
    n_t, n_g = len(tones), len(gains)
    width = label_w + n_t * cell + (n_t - 1) * gap
    height = n_g * cell + (n_g - 1) * gap
    arr = np.full((height, width), 255, np.uint8)

    for gi, g in enumerate(gains):
        y0 = gi * (cell + gap)
        for ti, tone in enumerate(tones):
            x0 = label_w + ti * (cell + gap)
            coverage = float(separation_engine.compenser_gain_point(np.float32(tone), g / 100.0))
            coverage = min(max(coverage, 0.0), 1.0)
            gray = np.full((cell, cell), int(round(255 * (1.0 - coverage))), np.uint8)
            bits = np.array(Image.fromarray(gray, "L").convert("1"))      # tramage Floyd-Steinberg
            arr[y0:y0 + cell, x0:x0 + cell] = np.where(bits, 255, 0).astype(np.uint8)

    # Valeurs du gain, à gauche de chaque ligne (police vectorielle 5x7, tracée avec PIL)
    canvas = Image.fromarray(arr, "L")
    draw = ImageDraw.Draw(canvas)
    text_h_px = min(cell, px(3.0))
    stroke = max(1, int(round(text_h_px / 7.0)))
    for gi, g in enumerate(gains):
        label = str(g)
        scale = text_h_px / 7.0
        y_mid = gi * (cell + gap) + cell / 2.0
        x_left = px(0.8)
        for i, char in enumerate(label):
            for x1, y1, x2, y2 in VectorFont.FONT_5X7.get(char, []):
                ox = x_left + i * (5 + 2) * scale
                draw.line([(ox + x1 * scale, y_mid + (3.5 - y1) * scale),
                           (ox + x2 * scale, y_mid + (3.5 - y2) * scale)], fill=0, width=stroke)
    arr = np.array(canvas)
    if mirror:
        arr = np.ascontiguousarray(arr[:, ::-1])
    return arr, width / lpm, height / lpm

