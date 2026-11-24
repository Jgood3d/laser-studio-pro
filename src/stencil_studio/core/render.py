"""Aperçus : matériaux et lumières, rendu réaliste, vues de la pile de couches.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np

from .params import Params
from .plate import GENERIC_SHAPES, shape_inside


def _engrave_preview(res):
    """Gravure tramée (noir = brûlé) à l'échelle de l'aperçu + contour de découpe en rouge."""
    H, W = res.mat.shape
    up = cv2.resize(res.engrave, (W, H), interpolation=cv2.INTER_NEAREST)
    g = np.where(res.sheet > 0, up, 255).astype(np.uint8)
    out = np.stack([g, g, g], -1)
    out[(res.mat == 0) & (res.sheet > 0)] = (232, 232, 232)      # parties découpées (œillet, lettres)
    ppm = W / res.w_mm
    cv2.polylines(out, [np.round(q * ppm).astype(np.int32).reshape(-1, 1, 2) for q in res.polys_mm], True, (230, 40, 40), 1)
    return out


def render_engrave(res, material="wood_light"):
    """Aperçu réaliste : pièce découpée dans le matériau, gravure foncée (bois) ou claire (matière sombre)."""
    H, W = res.mat.shape
    base_rgb, kind = MATERIALS.get(material, MATERIALS["wood_light"])
    luma = 0.299 * base_rgb[0] + 0.587 * base_rgb[1] + 0.114 * base_rgb[2]
    mark = np.array((22, 11, 5) if material == "wood_dark" else ((55, 30, 14) if kind == "wood" else
                    ((205, 205, 205) if luma < 130 else (60, 60, 60))), np.float32)
    noise = _grain(H, W, 0.10 if kind == "wood" else 0.015)
    plate = np.array(base_rgb, np.float32)[None, None, :] * (1.0 + noise[..., None])
    a = cv2.resize(255 - res.engrave, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
    a = cv2.GaussianBlur(a, (0, 0), max(0.6, 0.12 * W / res.w_mm))   # léger étalement du point brûlé
    a = np.clip(a * 0.92, 0, 1)[..., None]
    piece = plate * (1 - a) + mark[None, None, :] * a
    solid = (res.mat > 0)
    edge = cv2.GaussianBlur(solid.astype(np.float32), (0, 0), 1.2)[..., None]
    piece = piece * (0.8 + 0.2 * edge)
    out = np.where(solid[..., None], piece, np.array((46, 48, 53), np.float32)[None, None, :])
    return np.clip(out, 0, 255).astype(np.uint8)


def render_layer_stack(res, material="wood_light"):
    """Aperçu des couches empilées (la 1re derrière), éclairées par le haut à gauche : ombre portée sur la plaque
    de derrière (plus longue pour les plaques de devant), arête biseautée claire côté lumière et sombre côté
    opposé. Donne une idée fidèle du relief une fois les plaques collées."""
    mats = res.layers
    n = len(mats)
    H, W = mats[0].shape
    big = max(H, W)
    base = np.array(MATERIALS.get(material, MATERIALS[material if material in MATERIALS else "wood_light"])[0], np.float32)
    out = np.full((H, W, 3), (226, 226, 230), np.float32)
    cols = res.layer_colors
    s0 = max(2, int(0.005 * big))
    bev = max(1.2, 0.0035 * big)                       # largeur du biseau (px)
    lx, ly = -0.7071, -0.7071                           # direction de la lumière (vers le haut à gauche)
    for i, m in enumerate(mats):
        mf = m.astype(np.float32)
        off = int(round(s0 * (1.0 + 0.5 * min(i, 4))))   # plus la plaque est en avant, plus l'ombre s'allonge
        sh = cv2.GaussianBlur(np.roll(np.roll(mf, off, 0), off, 1), (0, 0), max(1.0, 0.004 * big) * (1.0 + 0.25 * min(i, 4)))
        out *= (1.0 - 0.55 * sh)[..., None]
        if cols:
            col = np.array(cols[i], np.float32)
        else:
            col = np.clip(base * (0.6 + 0.4 * (i / max(1, n - 1))), 0, 255)
        solid = m > 0
        out[solid] = col
        # biseau : dégradé du masque lissé ; arête tournée vers la lumière = plus claire, opposée = plus sombre
        g = cv2.GaussianBlur(mf, (0, 0), bev)
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        lit = -(gx * lx + gy * ly)
        lit = np.clip(lit / max(1e-6, float(np.abs(lit).max())) * 2.2, -1.0, 1.0)
        band = solid & (g < 0.97)
        k = (1.0 + 0.42 * lit)[..., None]
        out[band] = np.clip(out[band] * k[band] + (8.0 * np.maximum(lit, 0))[band][:, None], 0, 255)
        if i == n - 1 and res.marks is not None and res.layer_boxes:
            x0, y0, tw, th = res.layer_boxes[-1]
            mk = res.marks[y0:y0 + th, x0:x0 + tw] > 0
            out[mk] = out[mk] * 0.28
    return out.astype(np.uint8)


def _sheet_mask(shape, h, w):
    """1 = la plaque existe. Cercle, ovale, cœur... : la forme ; sinon toute l'image."""
    if shape == "circle" or shape in GENERIC_SHAPES:
        return shape_inside(shape, h, w)
    return np.ones((h, w), np.uint8)


# Matériaux (couleur de base, type) et couleurs de lumière pour l'aperçu réaliste
MATERIALS = {
    "wood_light": ((222, 184, 135), "wood"),   # bois clair (bouleau, pin)
    "wood_dark": ((92, 58, 38), "wood"),       # bois foncé (noyer)
    "black": ((24, 24, 27), "flat"),
    "gray": ((118, 121, 126), "flat"),
    "slate": ((58, 64, 72), "flat"),           # ardoise
    "white": ((235, 235, 232), "flat"),
}


LIGHTS = {
    "warm": (255, 214, 150), "cool": (205, 225, 255), "white": (255, 255, 245),
    "red": (255, 70, 60), "green": (80, 255, 120), "blue": (80, 130, 255), "amber": (255, 170, 40),
}


def _grain(h, w, strength, seed=7):
    """Bruit étiré horizontalement : veines du bois (ou grain très fin pour un matériau uni)."""
    rng = np.random.default_rng(seed)
    a = cv2.resize(rng.random((max(2, h // 3), max(2, w // 60))).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    b = cv2.resize(rng.random((max(2, h // 12), max(2, w // 15))).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    return ((0.65 * a + 0.35 * b) - 0.5) * 2.0 * strength


def render_realistic(res, material="wood_light", backlight=False, light="warm"):
    """Aperçu réaliste : plaque dans le matériau choisi, trous = lumière diffusée (rétroéclairage) ou
    papier/diffuseur éteint. Les couleurs sont indicatives."""
    mat = res.mat > 0
    h, w = mat.shape
    sheet = (res.sheet > 0) if res.sheet is not None else np.ones((h, w), bool)
    holes = sheet & ~mat
    ppm = max(h, w) / max(res.w_mm, res.h_mm, 1e-6)
    base_rgb, kind = MATERIALS.get(material, MATERIALS["wood_light"])
    noise = _grain(h, w, 0.10 if kind == "wood" else 0.015)
    base = np.array(base_rgb, np.float32)[None, None, :] * (1.0 + noise[..., None])
    hf = holes.astype(np.float32)
    rim = cv2.GaussianBlur(hf, (0, 0), max(1.0, 0.25 * ppm))
    plate = base * (1.0 - 0.28 * rim[..., None])                 # léger creux autour des trous
    if backlight:
        lc = np.array(LIGHTS.get(light, LIGHTS["warm"]), np.float32)[None, None, :]
        glow = cv2.GaussianBlur(hf, (0, 0), max(2.0, 0.9 * ppm))
        plate = plate * 0.55 + lc * glow[..., None] * 0.35        # pièce plus sombre, lumière qui déborde
        soft = cv2.GaussianBlur(hf, (0, 0), max(1.0, 0.4 * ppm))
        hole_col = lc * (0.90 + 0.10 * soft[..., None])
        bg = (22, 24, 28)
    else:
        hole_col = np.array((226, 222, 214), np.float32)[None, None, :] * 0.80   # papier diffuseur éteint
        bg = (46, 48, 53)
    out = np.where(holes[..., None], hole_col, plate)
    out = np.where(sheet[..., None], out, np.array(bg, np.float32)[None, None, :])
    return np.clip(out, 0, 255).astype(np.uint8)


def render_view(res, view, style=None):
    """Image RGB (uint8) à afficher : result | material | original | overlay | render (aperçu réaliste)."""
    if res.layers is not None and view == "assembled":
        return render_layer_stack(res, (style or {}).get("material", "wood_light"))
    if res.layers is not None and view == "box":
        view = "result"
    if res.layers is not None and view == "result" and not res.layer_colors:
        out = np.full(res.mat.shape + (3,), 255, np.uint8)
        out[res.mat > 0] = 0
        out[res.bridges > 0] = (230, 40, 40)
        if res.marks is not None:
            out[res.marks > 0] = (255, 255, 255)
        return out
    if res.layers is not None and res.layer_colors and view == "result":
        out = np.full(res.mat.shape + (3,), 255, np.uint8)
        for (x0, y0, tw, th), col, m in zip(res.layer_boxes, res.layer_colors, res.layers):
            t = out[y0:y0 + th, x0:x0 + tw]
            t[m > 0] = col
        out[res.bridges > 0] = (230, 40, 40)
        if res.marks is not None:
            out[res.marks > 0] = (45, 30, 25)
        return out
    if view == "box":
        try:
            from .. import lightbox
        except ImportError:
            import lightbox
        st = style or {}
        return lightbox.render_box(res, st.get("params") or Params(), lang=st.get("lang"))
    if view == "assembled":
        try:
            from .. import lightbox
        except ImportError:
            import lightbox
        st = style or {}
        return lightbox.render_assembled(res, st.get("params") or Params(), st)
    if res.marks is not None and res.layers is None and view in ("result", "material", "overlay", "render"):   # QR gravé : plaque + modules gravés
        st = style or {}
        if view == "render":
            out = render_realistic(res, st.get("material", "wood_light"), bool(st.get("backlight")), st.get("light", "warm"))
            if out.shape[:2] == res.marks.shape:
                out[res.marks > 0] = (out[res.marks > 0] * 0.22).astype(np.uint8)
            return out
        out = np.full(res.mat.shape + (3,), 255, np.uint8)
        out[res.mat > 0] = (205, 205, 205)
        out[res.marks > 0] = 0
        if view == "overlay":
            out = (0.45 * res.rgb + 0.55 * out).astype(np.uint8)
        return out
    if res.engrave is not None and view in ("result", "material", "overlay", "render"):
        st = style or {}
        if view == "render":
            return render_engrave(res, st.get("material", "wood_light"))
        out = _engrave_preview(res)
        if view == "overlay":
            out = (0.45 * res.rgb + 0.55 * out).astype(np.uint8)
        return out
    if view == "render":
        st = style or {}
        return render_realistic(res, st.get("material", "wood_light"), bool(st.get("backlight")), st.get("light", "warm"))
    if view == "original":
        out = res.rgb.copy()
        if res.subject is not None:
            out[res.subject == 0] = (out[res.subject == 0] * 0.3).astype(np.uint8)
        return out
    if view == "material":
        out = np.full(res.mat0.shape + (3,), 255, np.uint8)
        out[res.mat0 > 0] = 0
        return out
    out = np.full(res.mat.shape + (3,), 255, np.uint8)
    out[res.mat > 0] = 0
    out[res.bridges > 0] = (230, 40, 40)
    if view == "overlay":
        out = (0.45 * res.rgb + 0.55 * out).astype(np.uint8)
    return out
