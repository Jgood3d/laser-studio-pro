# -*- coding: utf-8 -*-
"""separation_engine.py - Calculs de séparation couleur / verre (numpy + Pillow, sans Qt).

Le calque NOIR (luminosité, contraste, gamma, tramage, spot) n'est plus calculé
ici : c'est le pipeline de l'onglet « Image & Filtres » qui s'en charge. Ce
module fournit seulement ce qui est propre à la séparation : tonalité (canal V)
envoyée à Image & Filtres, calque couleur, simulation, PDF d'impression.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def boite_recadrage(sw, sh, aspect, zoom=1.0, ox=0.5, oy=0.5):
    """Zone (gauche, haut, droite, bas) de l'image source qui sera gravée.
    aspect = largeur/hauteur de la plaque ; zoom >= 1 resserre le cadrage ;
    ox, oy (0..1) déplacent la zone dans l'image (0.5 = centré)."""
    if sw / sh > aspect:
        bh = float(sh)
        bw = bh * aspect
    else:
        bw = float(sw)
        bh = bw / aspect
    zoom = max(1.0, float(zoom))
    bw /= zoom
    bh /= zoom
    left = min(max(ox, 0.0), 1.0) * (sw - bw)
    top = min(max(oy, 0.0), 1.0) * (sh - bh)
    return (left, top, min(left + bw, float(sw)), min(top + bh, float(sh)))


def cadrer(img, px_w, px_h, cadrage=0, zoom=1.0, ox=0.5, oy=0.5):
    """Met l'image à la taille exacte px_w x px_h.
    cadrage : 0 = recadrer (avec zoom / décalage ox, oy), 1 = étirer."""
    size = (max(1, int(px_w)), max(1, int(px_h)))
    if cadrage == 0:
        box = boite_recadrage(img.width, img.height, size[0] / size[1], zoom, ox, oy)
        return img.resize(size, Image.LANCZOS, box=box)
    return img.resize(size, Image.LANCZOS)


def tonalite_v(img_array):
    """Tonalité = canal max (V de HSV), 0..1. C'est elle qui pilote le calque noir."""
    return img_array.astype(np.float32).max(axis=2) / 255.0


def compenser_gain_point(tone, gain=0.0):
    """Compense l'élargissement des points brûlés (gain de point), gain 0..1."""
    if gain <= 0:
        return tone
    x = np.linspace(0.0, 1.0, 1025, dtype=np.float32)
    eff = np.clip(x + gain * 4.0 * x * (1.0 - x), 0.0, 1.0)
    return np.interp(tone, eff, x).astype(np.float32)


def calculer_calque_couleur(img_array, saturation=1.4, clarte=1.0):
    """Calque couleur : teinte + saturation à luminosité maximale (V = 1)."""
    a = img_array.astype(np.float32) / 255.0
    mx = np.maximum(a.max(axis=2, keepdims=True), 0.05)
    mn_n = np.minimum(a.min(axis=2, keepdims=True) / mx, 1.0)
    cn = np.clip(a / mx, 0.0, 1.0)
    s = 1.0 - mn_n
    s2 = np.clip(s * saturation, 0.0, 1.0)
    c = np.clip((cn - mn_n) / np.maximum(s, 1e-4), 0.0, 1.0)
    rgb = (1.0 - s2) + c * s2
    return np.clip(rgb * clarte, 0.0, 1.0)


def simuler_retroeclairage(lumiere, couleur, intensite=1.0):
    """Rétro-éclairage en lumière linéaire (lumiere : fraction de verre dégagé,
    forme (H, W, 1) ; couleur : (H, W, 3) en 0..1). Renvoie du sRGB 0..1."""
    lin = np.where(couleur <= 0.04045, couleur / 12.92, ((couleur + 0.055) / 1.055) ** 2.4)
    e = np.clip(lumiere * lin * intensite, 0.0, 1.0)
    return np.where(e <= 0.0031308, e * 12.92, 1.055 * np.power(e, 1 / 2.4) - 0.055)


def vers_lineaire(couleur):
    """sRGB 0..1 -> lumière linéaire (à calculer une seule fois par calque couleur)."""
    return np.where(couleur <= 0.04045, couleur / 12.92, ((couleur + 0.055) / 1.055) ** 2.4).astype(np.float32)


def _construire_lut_srgb():
    x = np.arange(4096, dtype=np.float32) / 4095.0
    y = np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return (np.clip(y, 0.0, 1.0) * 255 + 0.5).astype(np.uint8)


_LUT_SRGB = _construire_lut_srgb()


def simuler_vers_image(lumiere, lin, intensite=1.0):
    """Version rapide de simuler_retroeclairage : `lin` = vers_lineaire(couleur)
    déjà calculé, encodage sRGB par table de correspondance. Renvoie une image PIL."""
    e = np.clip(lumiere * lin * intensite, 0.0, 1.0)
    return Image.fromarray(_LUT_SRGB[(e * 4095.0 + 0.5).astype(np.uint16)])


def array_vers_image(a):
    return Image.fromarray((np.clip(a, 0.0, 1.0) * 255 + 0.5).astype(np.uint8))


def generer_pdf_impression(img_couleur, dpi, chemin_pdf, w_mm, h_mm):
    """PDF A4 avec le calque couleur à l'échelle 1:1, centré, avec repères de coin.
    Renvoie False si la plaque ne tient pas sur une feuille A4."""
    for pw_mm, ph_mm in ((210, 297), (297, 210)):
        if w_mm <= pw_mm and h_mm <= ph_mm:
            pw, ph = round(pw_mm / 25.4 * dpi), round(ph_mm / 25.4 * dpi)
            page = Image.new("RGB", (pw, ph), "white")
            x, y = (pw - img_couleur.width) // 2, (ph - img_couleur.height) // 2
            page.paste(img_couleur, (x, y))
            marge = min(pw_mm - w_mm, ph_mm - h_mm) / 2
            if marge >= 4:
                d = ImageDraw.Draw(page)
                gap = round(1 / 25.4 * dpi)
                long = round(min(marge - 1, 5) / 25.4 * dpi)
                for cx, sx in ((x, -1), (x + img_couleur.width, 1)):
                    for cy, sy in ((y, -1), (y + img_couleur.height, 1)):
                        d.line([(cx + sx * gap, cy), (cx + sx * (gap + long), cy)], fill=(0, 0, 0))
                        d.line([(cx, cy + sy * gap), (cx, cy + sy * (gap + long))], fill=(0, 0, 0))
            page.save(chemin_pdf, "PDF", resolution=float(dpi))
            return True
    return False
