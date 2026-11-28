"""Matrice de test à partir d'une image : recadrage et gravure d'une zone — sans Qt.

La matrice de test grave d'habitude des carrés pleins. Ici chaque case grave à la place une
même zone (largeur x hauteur en mm) découpée dans une image, à l'échelle réelle. Ce module
contient la partie « pure » (testable sans interface) :

* `to_gray` : image PIL -> niveaux de gris (transparence sur fond blanc) ;
* `crop_box_px` / `frame_fraction` : où et quelle taille a la zone dans l'image ;
* `tile_raster_gcode` : G-Code d'une zone déjà tramée (même balayage aller/retour, même
  surbalayage et même calcul de puissance que controllers/workers.AdvancedGCodeWorker).
"""

import numpy as np
from PIL import Image


def to_gray(img):
    """Image PIL en niveaux de gris ('L'). Les pixels transparents deviennent blancs
    (matière intacte), comme une image sans fond."""
    if img.mode in ("RGBA", "LA") or "transparency" in getattr(img, "info", {}):
        rgba = img.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        return background.convert("L")
    return img.convert("L")


def _check(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm):
    if img_w_px < 1 or img_h_px < 1:
        raise ValueError("image vide")
    if img_width_mm <= 0 or tile_w_mm <= 0 or tile_h_mm <= 0:
        raise ValueError("dimensions en mm invalides")


def effective_tile_mm(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm):
    """Dimensions (mm) réellement gravées : celles demandées, réduites à celles de l'image
    si la zone dépasse. `img_width_mm` est la largeur réelle de l'image entière."""
    _check(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm)
    img_height_mm = img_width_mm * img_h_px / img_w_px
    return min(tile_w_mm, img_width_mm), min(tile_h_mm, img_height_mm)


def frame_fraction(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm):
    """Taille du cadre de la zone, en fraction de la largeur et de la hauteur de l'image."""
    eff_w, eff_h = effective_tile_mm(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm)
    img_height_mm = img_width_mm * img_h_px / img_w_px
    return eff_w / img_width_mm, eff_h / img_height_mm


def crop_box_px(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm, center_fx, center_fy):
    """Rectangle (gauche, haut, droite, bas) en pixels de la zone à graver.

    `center_fx` / `center_fy` : centre souhaité de la zone, en fraction de l'image (0 à 1,
    l'origine est le coin haut-gauche). La zone est décalée au besoin pour rester dans l'image.
    Renvoie (rectangle, largeur_mm, hauteur_mm) ; les dimensions en mm sont celles demandées,
    sauf si la zone est plus grande que l'image.
    """
    eff_w, eff_h = effective_tile_mm(img_w_px, img_h_px, img_width_mm, tile_w_mm, tile_h_mm)
    px_per_mm = img_w_px / img_width_mm
    crop_w = min(img_w_px, max(1, int(round(eff_w * px_per_mm))))
    crop_h = min(img_h_px, max(1, int(round(eff_h * px_per_mm))))
    left = int(round(min(max(center_fx, 0.0), 1.0) * img_w_px - crop_w / 2.0))
    top = int(round(min(max(center_fy, 0.0), 1.0) * img_h_px - crop_h / 2.0))
    left = max(0, min(img_w_px - crop_w, left))
    top = max(0, min(img_h_px - crop_h, top))
    return (left, top, left + crop_w, top + crop_h), eff_w, eff_h


def tile_raster_gcode(arr, x0, y0, w_mm, h_mm, speed, power_pct, s_max, laser_cmd,
                      overscan_dist=0.0, grayscale=False, scan_offset=0.0):
    """G-Code de gravure d'une zone d'image déjà tramée.

    `arr` : tableau 2D uint8 (0 = pixel brûlé, 255 = intact ; en niveaux de gris, la
    puissance est proportionnelle au noir). Le coin bas-gauche de la zone est en (x0, y0) et
    elle fait w_mm x h_mm. Même balayage que la gravure d'image : lignes vides sautées,
    sens aller/retour alterné, surbalayage, ligne retour décalée de `scan_offset`.
    Laser allumé une fois au début de la zone, éteint (M5) à la fin ; entre les deux, la puissance voyage sur
    chaque mouvement (gcode.common.LaserMoves).

    Renvoie (lignes de G-Code, durée en secondes, puissances en % des segments gravés).
    """
    arr = np.asarray(arr)
    if arr.ndim != 2 or arr.size == 0:
        return [], 0.0, []
    h, w = arr.shape
    step_x, step_y = w_mm / w, h_mm / h
    speed = max(float(speed), 1.0)
    from laser_studio.gcode.common import LaserMoves   # import local : le paquet gcode importe ce module
    f = int(speed)
    lines = []
    moves = LaserMoves(lines)
    seconds = 0.0
    samples = []
    scanned = 0

    for y in range(h):
        row = arr[y, :].astype(np.float64)
        if grayscale:
            pct = power_pct * (255.0 - row) / 255.0
        else:
            pct = np.where(row == 0, power_pct, 0.0)
        s_vals = np.rint((pct / 100.0) * s_max).astype(np.int64)
        burned = np.flatnonzero(s_vals > 0)
        if burned.size == 0:
            continue
        first, last = int(burned[0]), int(burned[-1])

        ly = y0 + (h - 1 - y) * step_y
        ltr = (scanned % 2 == 0)
        scanned += 1
        row_x0 = x0 if ltr else x0 + scan_offset
        seg_left = row_x0 + first * step_x
        seg_right = row_x0 + (last + 1) * step_x
        edge_in = seg_left if ltr else seg_right
        edge_out = seg_right if ltr else seg_left
        margin_in = edge_in - overscan_dist if ltr else edge_in + overscan_dist
        margin_out = edge_out + overscan_dist if ltr else edge_out - overscan_dist

        moves.laser(laser_cmd)                 # à la première ligne gravée : rien pour une zone blanche
        if overscan_dist > 0:
            moves.travel(margin_in, ly, "OVERSCAN_START")
            moves.move(edge_in, power=0, feed=f)
            seconds += abs(edge_in - margin_in) / speed * 60.0
        else:
            moves.travel(edge_in, ly)

        # Plages de pixels de même puissance, dans le sens du balayage.
        seg = s_vals[first:last + 1]
        pcts = pct[first:last + 1]
        if not ltr:
            seg = seg[::-1]
            pcts = pcts[::-1]
        cuts = np.flatnonzero(np.diff(seg)) + 1
        starts = np.concatenate(([0], cuts))
        ends = np.concatenate((cuts, [seg.size]))
        cursor = edge_in
        for a, b in zip(starts, ends):
            nx = edge_in + b * step_x if ltr else edge_in - b * step_x
            s_run = int(seg[a])
            moves.move(nx, power=s_run, feed=f)
            seconds += abs(nx - cursor) / speed * 60.0
            if s_run > 0:
                samples.append(float(pcts[a]))
            cursor = nx

        if overscan_dist > 0:
            moves.move(margin_out, power=0, feed=f, comment="OVERSCAN_END")
            seconds += abs(margin_out - cursor) / speed * 60.0

    if lines:
        moves.off()
    return lines, seconds, samples
