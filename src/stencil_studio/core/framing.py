"""Cadrage de la photo : conversion en RGB, cadre, rotation, recadrage, masque de la zone valide.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def to_rgb(img):
    """Image PIL -> RGB (transparence sur fond blanc, orientation EXIF appliquée)."""
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.getchannel("A"))
        return bg
    return img.convert("RGB")


def frame_box(W, H, fr):
    """Cadre {cx, cy, w, aspect} (fractions) -> boîte entière (l, t, r, b) dans l'image."""
    if fr.get("full"):  # image complète : ratio exact de l'original, cadre = toute l'image
        return 0, 0, W, H
    if fr.get("free") or float(fr.get("rot", 0) or 0) % 360 != 0:  # placement libre (ou cadre tourné) : le cadre peut déborder de la photo (marges vides)
        aspect = max(0.1, min(10.0, float(fr.get("aspect", 1.0))))
        fw = max(8.0, min(10.0, float(fr.get("w", 1.0))) * W)
        fh = fw / aspect
        cx = min(max(float(fr.get("cx", 0.5)), 0.0), 1.0) * W
        cy = min(max(float(fr.get("cy", 0.5)), 0.0), 1.0) * H
        l, t = int(round(cx - fw / 2)), int(round(cy - fh / 2))
        return l, t, l + max(8, int(round(fw))), t + max(8, int(round(fh)))
    aspect = max(0.1, min(10.0, float(fr.get("aspect", 1.0))))
    fw = float(fr.get("w", 1.0)) * W
    fh = fw / aspect
    if fh > H:
        fh = H
        fw = fh * aspect
    if fw > W:
        fw = W
        fh = fw / aspect
    cx = min(max(float(fr.get("cx", 0.5)) * W, fw / 2), W - fw / 2)
    cy = min(max(float(fr.get("cy", 0.5)) * H, fh / 2), H - fh / 2)
    l, t = int(round(cx - fw / 2)), int(round(cy - fh / 2))
    r, b = int(round(cx + fw / 2)), int(round(cy + fh / 2))
    return max(0, l), max(0, t), min(W, max(r, l + 8)), min(H, max(b, t + 8))


def rot_maps(box, shape_hw, rot):
    """Cartes (x, y) en pixels de la photo, pour chaque pixel d'un cadre `box` tourné de `rot` degrés (sens horaire)."""
    l, t, r, b = box
    h, w = shape_hw
    a = np.radians(rot)
    ca, sa = np.cos(a), np.sin(a)
    cx, cy = (l + r) / 2.0, (t + b) / 2.0
    s = w / float(r - l)
    u = (np.arange(w, dtype=np.float32) + 0.5 - w / 2.0) / s
    v = (np.arange(h, dtype=np.float32) + 0.5 - h / 2.0) / (h / float(b - t))
    U, V = np.meshgrid(u, v)
    return (cx + ca * U - sa * V).astype(np.float32), (cy + sa * U + ca * V).astype(np.float32)


def crop_resize_rot(img, box, work, rot):
    """Comme crop_resize pour un cadre tourné : le contenu du cadre est remis droit ; hors photo = blanc."""
    l, t, r, b = box
    W, H = img.size
    s = work / float(max(r - l, b - t))
    ow, oh = max(8, round((r - l) * s)), max(8, round((b - t) * s))
    mx, my = rot_maps(box, (oh, ow), rot)
    x0, x1 = int(max(0, np.floor(mx.min()) - 2)), int(min(W, np.ceil(mx.max()) + 3))
    y0, y1 = int(max(0, np.floor(my.min()) - 2)), int(min(H, np.ceil(my.max()) + 3))
    if x1 <= x0 or y1 <= y0:
        return np.full((oh, ow, 3), 255, np.uint8)
    part = img.convert("RGB").crop((x0, y0, x1, y1))
    k = min(1.0, s)                                   # réduction préalable (évite le crénelage) puis échantillonnage
    if k < 1.0:
        part = part.resize((max(1, round(part.width * k)), max(1, round(part.height * k))), Image.LANCZOS)
    src = np.array(part)
    out = cv2.remap(src, (mx - x0) * k, (my - y0) * k, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(255, 255, 255))
    ok = (mx >= 0) & (mx <= W) & (my >= 0) & (my <= H)
    out[~ok] = 255
    return out


def crop_resize(img, box, work, rot=0.0):
    """Découpe `box` dans l'image PIL puis réduit pour que le grand côté = `work` px."""
    if rot and float(rot) % 360 != 0:
        return crop_resize_rot(img, box, work, float(rot))
    l, t, r, b = box
    W, H = img.size
    il, it, ir, ib = max(l, 0), max(t, 0), min(r, W), min(b, H)
    if (il, it, ir, ib) != (l, t, r, b):  # le cadre déborde : marges blanches (calculées à la taille finale)
        s = work / max(r - l, b - t)
        out = Image.new("RGB", (max(8, round((r - l) * s)), max(8, round((b - t) * s))), (255, 255, 255))
        if ir > il and ib > it:
            part = img.convert("RGB").crop((il, it, ir, ib))
            part = part.resize((max(1, round((ir - il) * s)), max(1, round((ib - it) * s))), Image.LANCZOS)
            out.paste(part, (round((il - l) * s), round((it - t) * s)))
        return np.array(out)
    c = img.crop(box)
    s = work / max(c.size)
    c = c.resize((max(8, round(c.width * s)), max(8, round(c.height * s))), Image.LANCZOS)
    return np.array(c)


def fill_outside(rgb, valid):
    """Prolonge les bords de la photo dans les marges (évite de faux contours à la limite de la photo)."""
    if valid is None or not valid.any():
        return rgb
    _, (iy, ix) = ndi.distance_transform_edt(valid == 0, return_indices=True)
    return rgb[iy, ix]


def valid_mask(box, W, H, shape_hw, rot=0.0):
    """1 = pixel qui vient de la photo ; None si le cadre est entièrement dans la photo."""
    l, t, r, b = box
    if rot and float(rot) % 360 != 0:
        mx, my = rot_maps(box, shape_hw, float(rot))
        ok = ((mx >= 0) & (mx <= W) & (my >= 0) & (my <= H)).astype(np.uint8)
        return None if ok.all() else ok
    if l >= 0 and t >= 0 and r <= W and b <= H:
        return None
    h, w = shape_hw
    sx, sy = w / float(r - l), h / float(b - t)
    out = np.zeros((h, w), np.uint8)
    x0, x1 = int(round((max(l, 0) - l) * sx)), int(round((min(r, W) - l) * sx))
    y0, y1 = int(round((max(t, 0) - t) * sy)), int(round((min(b, H) - t) * sy))
    out[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1
    return out


def codes_from_rgb(arr, alpha=None):
    """Repères peints : vert = sujet (1), rouge = fond (2), sinon 0."""
    r, g, b = (arr[..., i].astype(int) for i in range(3))
    ok = np.ones(r.shape, bool) if alpha is None else alpha > 100
    codes = np.zeros(r.shape, np.uint8)
    codes[ok & (g > 150) & (r < 110) & (b < 110)] = 1
    codes[ok & (r > 150) & (g < 110) & (b < 110)] = 2
    return codes
