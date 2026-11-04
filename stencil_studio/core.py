"""Traitement photo -> silhouette de découpe laser (partagé par la CLI et l'interface web).

Aucune dépendance à une interface : tout est en fonctions pures sur des tableaux numpy.
"""
import os
import time
from dataclasses import asdict, dataclass, fields, replace

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

VERSION = "2026.10.84"  # doit être identique dans core.py et studio.html
REF_SIZE = 1200.0  # taille de référence : les réglages en pixels sont exprimés pour 1200 px


# --------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------
@dataclass
class Params:
    size_mm: float = 100.0        # taille finale (plus grand côté)
    output: str = "stencil"        # stencil (formes + ponts) | halftone (trame de points pour les photos)
    dot_pitch_mm: float = 1.6     # halftone : pas de la trame
    min_web_mm: float = 0.5       # halftone : matière minimale entre deux trous
    min_dot_mm: float = 0.35      # halftone : plus petit trou découpé (en dessous : zone pleine)
    dot_angle: float = 45.0       # halftone : angle de la trame (degrés)
    dot_gamma: float = 1.0        # halftone : courbe des tons (>1 = plus de matière)
    dot_contrast: float = 0.8     # halftone : 0 = niveaux étalés ; 1 = histogramme égalisé (contraste maximal)
    dot_detail: float = 1.5       # halftone : renforcement du détail local (0 = aucun)
    shape: str = "circle"         # circle | rect | none
    ring_mm: float = 4.0          # largeur de l'anneau extérieur
    bridge_mm: float = 1.5        # largeur des ponts
    max_bridge_mm: float = 8.0    # îlot plus loin : supprimé
    min_island_mm2: float = 10.0  # îlot plus petit : supprimé
    min_feature_mm: float = 0.8   # plus petit détail découpable
    keep_thin: bool = True        # épaissir les traits fins au lieu de les supprimer
    grow_mm: float = 0.0          # épaisseur des traits : + épaissit, - amincit (variation de largeur totale)
    mode: str = "local"           # local | global
    tone_source: str = "luminance" # luminance | darkest | mix
    auto_threshold: bool = True
    threshold: float = 128.0
    bias: float = 0.0
    texture: float = 1.0          # passes de lissage des textures (0 = aucun)
    outline_mm: float = 1.0       # trait plein le long du contour du sujet (si sujet isolé)
    blur: float = 1.5             # px à 1200 px
    contrast: bool = True
    invert: bool = False
    local_contrast: float = 10.0
    local_size: float = 0.125     # fraction de l'image
    dark_offset: float = 90.0
    smooth: float = 2.0           # px à 1200 px
    simplify: float = 0.8         # px à 1200 px
    hang: str = "none"            # accroche : none | top | top_left | top_right | both
    hang_style: str = "round"     # round | drop
    hang_hole_mm: float = 3.0     # diamètre du trou d'accroche
    hang_tab_mm: float = 2.5      # matière autour du trou
    text_top: str = ""            # texte courbe dans l'anneau (haut)
    text_bottom: str = ""         # texte courbe dans l'anneau (bas)
    text_size_mm: float = 6.0     # hauteur des majuscules
    text_spacing: float = 12.0    # espace entre lettres (% de la hauteur)
    text_bridge_mm: float = 0.7   # largeur des ponts dans les lettres (centres de A, O, B...)
    font: str = ""                # chemin d'une police .ttf (vide = police fournie)
    eng_dpi: float = 195.0        # gravure : résolution de la machine (points par pouce)
    eng_dither: str = "stucki"    # stucki | floyd | atkinson | jarvis | burkes | sierra | bayer | threshold
    eng_levels: int = 2           # 2 = noir / blanc ; 3 et plus = niveaux de gris (puissances différentes)
    eng_brightness: float = 0.0   # -100..100
    eng_contrast: float = 0.0     # -90..90
    eng_gamma: float = 1.0        # > 1 = plus clair
    eng_sharpen: float = 1.0      # netteté (0 = aucune)
    eng_invert: bool = False      # graver les zones claires (matière sombre qui s'éclaircit)
    eng_border_mm: float = 1.0    # marge sans gravure le long du bord de la pièce
    eng_speed: float = 5500.0     # mm/min, pour l'estimation de durée
    box_depth_mm: float = 25.0    # caisson lumineux : profondeur intérieure
    box_thickness_mm: float = 3.0 # épaisseur du matériau des cadres
    box_wall_mm: float = 10.0     # largeur de paroi
    box_screws: int = 4           # vis du fond (0 = collé)
    box_screw_mm: float = 3.0     # diamètre de vis (M3)
    export_frame: bool = False   # ajoute un rectangle de cadrage (calque FRAME / Marquage) aux exports SVG et DXF
    box_support: str = "none"    # none | foot | wall | both : pied et/ou trous de serrure dans le fond
    box_foot_h: float = 9.0       # profondeur de la rainure du pied (mm)
    box_key_head: float = 8.0     # diamètre de la tête de vis pour la fixation murale (mm)
    box_key_shank: float = 4.0    # diamètre de la tige de vis (mm)
    box_center_mm: float = 0.0    # trou rond au centre du fond (diamètre, 0 = aucun)
    box_cable_mm: float = 8.0     # trou de câble dans le fond (0 = aucun)
    box_diffuser: bool = True     # plaque diffusante entre façade et cadres
    box_sheet_w: float = 400.0    # largeur de la plaque à découper (mise en page)
    box_gap_mm: float = 4.0       # espace entre pièces
    box_style: str = "stack"      # stack (cadres collés) | fingers (parois à encoches, flexibles sur les courbes)
    box_rib_mm: float = 2.54  # fingers : écart entre deux lignes de coupe de la paroi flexible (= largeur d'une nervure)
    box_end_mm: float = 2.7    # fingers : distance des fentes centrales aux bords haut / bas
    box_fit_auto: bool = True     # fingers : jeu des languettes ajusté à la courbure
    box_tab_solid: bool = False   # fingers : languettes pleines (non traversées par les fentes de flexion)
    box_mid_mm: float = 6.0  # fingers : pont de matière au milieu entre cellules
    box_wall_parts: int = 1       # fingers : nombre de morceaux de la paroi courbe (1 à 3)
    box_fit_mm: float = 0.1       # fingers : jeu des fentes (colle)
    box_lip_mm: float = 1.5       # fingers : débord de la façade et du fond autour de la paroi
    line_pitch_mm: float = 1.5    # lignes : écart entre deux lignes
    line_angle: float = 30.0      # lignes : angle (degrés)
    lp_points: int = 200          # low poly : nombre approximatif de sommets du maillage
    lp_beam_mm: float = 1.4       # low poly : largeur des arêtes (poutres) en mm
    lp_style: str = "solid"       # low poly : wire (arêtes seules) | solid (facettes sombres pleines) | shade (trou de chaque facette selon le ton)
    lp_geo: bool = False          # low poly : style géométrique (silhouette en polygone, peu de sommets, taches sombres en facettes)
    lp_simplify: float = 1.2      # low poly géométrique : simplification de la silhouette (% de la taille)
    ml_layers: int = 4            # multicouche : nombre de plaques empilées (la 1re = fond plein)
    ml_invert: bool = False       # multicouche : les zones claires sont les plus profondes (au lieu des sombres)
    ml_sep: str = "tone"          # multicouche : tone (par luminosité) | color (une plaque par couleur dominante)
    ml_order: str = ""            # multicouche couleur : ordre des couleurs de l'arrière vers l'avant (indices séparés par des virgules)
    ml_bg: str = "front"          # multicouche : fond de l'image = couleur de la plaque de devant (front) | plaque de fond à part (own)
    ml_bg_color: str = "#e8dcc8"  # multicouche : couleur de la plaque de fond à part (aperçu et export)
    ml_engrave: bool = False      # multicouche : graver les détails (visages...) sur la plaque de devant (calque ENGRAVE)
    ml_eng_level: float = 50.0    # multicouche : sensibilité de la gravure des détails (0 à 100)
    ml_pins: bool = True          # multicouche : 3 trous de repérage identiques dans la bordure de chaque couche
    ml_pin_mm: float = 3.0        # diamètre des trous de repérage (tourillons / vis)
    ml_picks: str = ""            # multicouche couleur : couleurs choisies à la pipette (#rrggbb séparés par des virgules ; ≥ 2 = remplace le k-means)
    ml_color_auto: bool = True    # multicouche couleur : nombre de couleurs détecté automatiquement (ml_layers = maximum)
    ml_pieces: bool = False       # multicouche : plaques de dessus = pièces libres à coller (aucun pont)
    keep_islands: bool = False    # interne : les îlots non reliés sont gardés comme pièces libres (au lieu d'être supprimés)
    loose: bool = False           # interne : pas de ponts (pièces libres)
    ml_gap_mm: float = 6.0        # espace entre couches sur la planche de découpe
    qr_kind: str = "text"         # qr : text (lien, texte...) | wifi
    qr_text: str = "https://exemple.fr"
    qr_ssid: str = ""
    qr_pass: str = ""
    qr_sec: str = "WPA"           # WPA | WEP | nopass
    qr_ec: str = "Q"              # correction d'erreur : L | M | Q | H
    qr_mode: str = "engrave"      # engrave (modules gravés sur la plaque) | cut (modules ajourés, avec ponts)
    qr_side_mm: float = 40.0      # côté du code (sans la marge)
    qr_invert: bool = False       # polarité inversée (graver les modules clairs / ajourer les modules sombres)
    qr_bridge_mm: float = 0.5     # largeur des ponts du mode ajouré
    ai_subject: bool = True       # détecte le sujet par réseau de neurones si onnxruntime est installé (sinon méthode classique)
    lp_auto: bool = True          # low poly : détecte le sujet tout seul si le fond est uni
    lp_level: float = 0.0         # low poly (solid) : décalage du seuil clair/sombre (+ = plus de facettes pleines)
    lp_focus: float = 0.35         # low poly : 0 = sommets uniformes, 1 = très serrés sur les détails
    lp_seed: int = 1              # low poly : variante du semis de sommets
    line_break_mm: float = 30.0   # lignes : longueur max d'une fente avant un pont (0 = fentes continues)

    @classmethod
    def unknown_keys(cls, d):
        """Réglages reçus que cette version de core.py ne connaît pas."""
        names = {f.name for f in fields(cls)}
        return sorted(k for k in (d or {}) if k not in names)

    @classmethod
    def from_dict(cls, d):
        names = {f.name: f.type for f in fields(cls)}
        out = {}
        for k, v in (d or {}).items():
            if k in names:
                out[k] = v
        return cls(**out)

    def to_dict(self):
        return asdict(self)


@dataclass
class Result:
    rgb: np.ndarray
    gray: np.ndarray
    subject: object
    mat0: np.ndarray       # matière après nettoyage (avant forme + ponts)
    mat: np.ndarray        # matière finale
    bridges: np.ndarray
    polys_mm: list
    w_mm: float
    h_mm: float
    stats: dict
    sheet: object = None   # masque 1 = plaque présente (hors plaque : fond)
    engrave: object = None  # gravure : image tramée (uint8, 0 = brûlé) à la résolution de la machine
    eng_dpi: float = 0.0
    tab: object = None      # zone de l'œillet (masque, repère agrandi)
    hang_holes: object = None  # trous d'accroche [(x_mm, y_mm, r_mm)]
    base_sheet: object = None  # masque de la forme sans la languette d'accroche
    marks: object = None       # qr : masque des zones gravées (modules)
    marks_polys: object = None  # qr : contours (mm) des zones gravées, pour le calque ENGRAVE
    layers: object = None       # multicouche : matière (masque) de chaque couche, taille d'une tuile
    layer_colors: object = None  # multicouche couleur : (r, g, b) de chaque plaque
    layer_boxes: object = None   # multicouche : (x0, y0, w, h) de chaque tuile sur la planche
    layer_polys: object = None  # multicouche : [(nom, contours mm)] sur la planche de découpe


# --------------------------------------------------------------------------
# Cadrage / image
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Sujet (GrabCut)
# --------------------------------------------------------------------------
def _grabcut_input(small):
    """GrabCut modélise des couleurs. Sur une image grise (R=G=B) les statistiques sont dégénérées
    et il ne trouve aucun sujet : on lui donne alors 3 canaux utiles (gris, gris flou, texture)."""
    ch = small.astype(np.int16)
    spread = np.abs(ch[..., 0] - ch[..., 1]).mean() + np.abs(ch[..., 1] - ch[..., 2]).mean()
    if spread > 6:
        return small
    g = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(g, (0, 0), 3)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    mag = np.clip(cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 2) * 0.5, 0, 255).astype(np.uint8)
    return np.dstack([g, blur, mag])


def remove_background(rgb, rect, codes=None, iters=5, size=500):
    """Isole le sujet. rect=(x,y,w,h) fractions 0-1 ; codes = repères (0/1/2) même cadrage.
    Retourne un masque 0/1 (tout à 1 si GrabCut échoue)."""
    h, w = rgb.shape[:2]
    scale = float(size) / max(h, w)
    sw, sh = max(16, round(w * scale)), max(16, round(h * scale))
    small = cv2.resize(rgb, (sw, sh), interpolation=cv2.INTER_AREA)
    x, y, rw, rh = rect
    x0, y0 = int(x * sw), int(y * sh)
    x1, y1 = min(sw, x0 + max(2, int(rw * sw))), min(sh, y0 + max(2, int(rh * sh)))
    mask = np.full((sh, sw), cv2.GC_BGD, np.uint8)
    mask[y0:y1, x0:x1] = cv2.GC_PR_FGD
    if codes is not None and codes.any():
        cs = cv2.resize(codes, (sw, sh), interpolation=cv2.INTER_NEAREST)
        mask[cs == 1] = cv2.GC_FGD
        mask[cs == 2] = cv2.GC_BGD
    if not ((mask == cv2.GC_BGD) | (mask == cv2.GC_PR_BGD)).any():
        mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = cv2.GC_BGD
    if not ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).any():
        return np.ones((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(cv2.cvtColor(_grabcut_input(small), cv2.COLOR_RGB2BGR), mask, None, bgd, fgd, iters,
                    cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return np.ones((h, w), np.uint8)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    fg = cv2.resize(fg, (w, h), interpolation=cv2.INTER_LINEAR)
    fg = cv2.GaussianBlur(fg, (0, 0), 3 * max(h, w) / REF_SIZE)
    return (fg > 127).astype(np.uint8)


# --------------------------------------------------------------------------
# Tons -> matière
# --------------------------------------------------------------------------
def otsu_value(values):
    hist = np.bincount(values.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    if total == 0:
        return 127.0
    sum_all = np.dot(np.arange(256), hist)
    w0 = sum0 = 0.0
    best, thr = -1.0, 127
    for t in range(256):
        w0 += hist[t]
        if w0 == 0 or w0 == total:
            continue
        sum0 += t * hist[t]
        m0, m1 = sum0 / w0, (sum_all - sum0) / (total - w0)
        var = w0 * (total - w0) * (m0 - m1) ** 2
        if var > best:
            best, thr = var, t
    return float(thr)


def tone_gray(rgb, source):
    """Image de tons (0 = noir). 'darkest' : le canal le plus sombre -> les couleurs saturées
    (rouge, bleu...) deviennent sombres, donc pleines ; 'mix' : moyenne des deux."""
    lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if source == "luminance":
        return lum
    dark = rgb.min(axis=2)
    if source == "darkest":
        return dark
    return ((lum.astype(np.uint16) + dark) // 2).astype(np.uint8)


def tone_mask(gray, p, subject=None):
    ref = max(gray.shape) / REF_SIZE
    g = gray
    for _ in range(int(round(p.texture))):  # lisse les textures, garde les contours
        g = cv2.bilateralFilter(g, 0, 40, max(2.0, 6.0 * ref))
    if p.contrast:
        g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
    if p.blur > 0:
        g = cv2.GaussianBlur(g, (0, 0), p.blur * ref)
    if p.auto_threshold:
        sample = g[subject > 0] if subject is not None and subject.any() else g
        thr = otsu_value(sample)
    else:
        thr = float(p.threshold)
    thr = float(np.clip(thr + p.bias, 0, 255))
    if p.mode == "local":
        block = max(3, int(p.local_size * max(g.shape))) | 1
        local = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, block, float(p.local_contrast)) > 0
        t_dark = thr - p.dark_offset
        if t_dark < 26:   # image globalement sombre : « seuil moins décalage » serait négatif et ne remplirait rien
            ref = g[subject > 0] if subject is not None and subject.any() else g
            t_dark = min(max(t_dark, float(np.percentile(ref, 22))), thr - 10)   # les 22 % les plus sombres deviennent pleins
        mat = local | (g < t_dark)
        if p.invert:
            mat = ~mat
    else:
        mat = (g >= thr) if p.invert else (g < thr)
    return mat.astype(np.uint8), thr


def _remove_small(mask, min_area):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
    keep = np.zeros(n, dtype=np.uint8)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
    return keep[lab]


def clean_mask(mat, px_per_mm, min_feature_mm, keep_thin=True):
    """Rend la matière découpable : comble les trous trop fins et traite la matière trop étroite.
    keep_thin=True : les traits plus fins que le détail minimal sont épaissis (dessins au trait) ;
    sinon ils sont supprimés."""
    d = max(3, int(round(min_feature_mm * px_per_mm)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    closed = cv2.morphologyEx(mat, cv2.MORPH_CLOSE, k)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, k)
    if keep_thin:
        thin = closed & (1 - opened)                  # matière plus étroite que d
        thin = _remove_small(thin, max(4, 2 * d * d))  # on garde les traits, pas les petits bords
        r = max(1, d // 3)
        thick = cv2.dilate(thin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        mat = opened | thick
    else:
        mat = opened
    area = max(4, int(0.5 * d * d))
    mat = _remove_small(mat, area)
    return 1 - _remove_small(1 - mat, area)


# --------------------------------------------------------------------------
# Formes de plaque
# --------------------------------------------------------------------------
GENERIC_SHAPES = ("oval", "rrect", "heart", "star", "tree")


def _poly_unit(shape):
    """Contour normalisé (0..1 dans les deux axes) d'une forme décorative."""
    if shape == "tree":   # sapin : trois étages et un tronc, pointe en haut
        half = [(0.5, 0.0), (0.70, 0.30), (0.60, 0.30), (0.82, 0.58), (0.70, 0.58), (0.96, 0.86), (0.58, 0.86), (0.58, 1.0)]
        pts = np.array(half + [(1.0 - x, y) for x, y in half[::-1]], float)
        return pts
    if shape == "heart":
        t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
        x = 16 * np.sin(t) ** 3
        y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    else:  # star : 5 branches, pointe en haut
        k = np.arange(10)
        a = -np.pi / 2 + k * np.pi / 5
        r = np.where(k % 2 == 0, 1.0, 0.42)
        x, y = r * np.cos(a), r * np.sin(a)
    pts = np.stack([x, y], 1)
    mn, mx = pts.min(0), pts.max(0)
    return (pts - mn) / (mx - mn)


def shape_inside(shape, h, w):
    """Masque uint8 de la plaque (1 = matière possible) pour la forme choisie, dans un cadre h x w."""
    if shape == "circle":
        yy, xx = np.mgrid[0:h, 0:w]
        R = min(h, w) / 2 - 1
        return (np.hypot(xx - (w - 1) / 2, yy - (h - 1) / 2) <= R).astype(np.uint8)
    out = np.zeros((h, w), np.uint8)
    if shape == "oval":
        cv2.ellipse(out, (w // 2, h // 2), (max(1, w // 2 - 1), max(1, h // 2 - 1)), 0, 0, 360, 1, -1)
    elif shape == "rrect":
        r = max(2, int(0.18 * min(h, w)))
        cv2.rectangle(out, (r, 1), (w - 2 - r, h - 2), 1, -1)
        cv2.rectangle(out, (1, r), (w - 2, h - 2 - r), 1, -1)
        for cx, cy in ((r, r), (w - 2 - r, r), (r, h - 2 - r), (w - 2 - r, h - 2 - r)):
            cv2.circle(out, (cx, cy), r, 1, -1)
    elif shape in ("heart", "star", "tree"):
        pts = _poly_unit(shape) * np.array([w - 3, h - 3], float) + 1.5
        cv2.fillPoly(out, [np.round(pts * 16).astype(np.int32)], 1, shift=4)
    else:
        out[:] = 1
    return out


def apply_shape(mat, shape, ring_mm, px_per_mm):
    h, w = mat.shape
    ring = max(2, int(round(ring_mm * px_per_mm)))
    if shape == "circle":
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot(xx - (w - 1) / 2, yy - (h - 1) / 2)
        R = min(h, w) / 2 - 1
        inside = r <= R
        ring_mask = inside & (r > R - ring)
        out = ((mat.astype(bool) & inside) | ring_mask).astype(np.uint8)
        return out, (w // 2, int(round((h - 1) / 2 - R + ring / 2)))
    if shape == "rect":
        out = mat.copy()
        out[:ring, :] = out[-ring:, :] = 1
        out[:, :ring] = out[:, -ring:] = 1
        return out, (w // 2, ring // 2)
    if shape in GENERIC_SHAPES:
        inside = shape_inside(shape, h, w)
        d = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
        ring_mask = (inside > 0) & (d <= ring)
        out = ((mat.astype(bool) & (inside > 0)) | ring_mask).astype(np.uint8)
        col = np.nonzero(inside[:, w // 2])[0]
        y0 = int(col[0]) if len(col) else 0
        return out, (w // 2, min(h - 1, y0 + max(1, ring // 2)))
    return mat.copy(), None


# --------------------------------------------------------------------------
# Texte dans l'anneau + œillet d'accroche
# --------------------------------------------------------------------------
def text_supported(p):
    """Le texte suit l'anneau : formes régulières seulement (pas d'angles rentrants)."""
    return p.shape in ("circle", "oval", "rrect", "rect")


def effective_ring(p):
    """Largeur d'anneau réelle : s'élargit automatiquement pour contenir le texte."""
    r = p.ring_mm
    if text_supported(p) and ((p.text_top or "").strip() or (p.text_bottom or "").strip()):
        r = max(r, p.text_size_mm + 3.0)
    return r


def _load_font(px, path=""):
    from PIL import ImageFont
    base = os.path.dirname(os.path.abspath(__file__))
    cands = ([path] if path else []) + [
        os.path.join(base, "fonts", "DejaVuSans-Bold.ttf"),
        "C:/Windows/Fonts/arialbd.ttf", "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for c in cands:
        try:
            return ImageFont.truetype(c, int(px))
        except Exception:
            continue
    return ImageFont.load_default(int(px))


def _ring_path(inside, ring_px, clockwise):
    """Ligne médiane de l'anneau (polyligne fermée lissée), sens horaire ou antihoraire à l'écran."""
    d = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
    reg = (d >= ring_px / 2.0).astype(np.uint8)
    cnts, _ = cv2.findContours(reg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    if len(c) < 20:
        return None
    sig = max(2.0, ring_px * 0.5)
    c = np.stack([ndi.gaussian_filter1d(c[:, i], sig, mode="wrap") for i in (0, 1)], 1)
    x, y = c[:, 0], c[:, 1]
    area = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))   # > 0 : sens horaire à l'écran
    if (area > 0) != bool(clockwise):
        c = c[::-1]
    return c


def _text_mask(inside, txt, where, p, ppm, ring_px):
    """Masque (1 = trou) du texte posé sur la ligne médiane de l'anneau. where : top | bottom.
    Retourne (masque, texte réduit ?)."""
    from PIL import ImageDraw
    h, w = inside.shape
    path = _ring_path(inside, ring_px, clockwise=(where == "top"))
    if path is None:
        return None, False
    cl = np.vstack([path, path[:1]])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(cl, axis=0).T))])
    L = float(s[-1])

    def pos(q):
        q = np.mod(q, L)
        return np.array([np.interp(q, s, cl[:, 0]), np.interp(q, s, cl[:, 1])])

    idx = int(np.argmin(path[:, 1])) if where == "top" else int(np.argmax(path[:, 1]))
    s0 = float(s[idx])
    SS = 2
    H_px = max(4.0, p.text_size_mm * ppm)
    probe = _load_font(100, p.font)
    cap = max(1.0, -float(probe.getbbox("H", anchor="ls")[1]))
    em = 100.0 * H_px * SS / cap
    chars = list(txt)

    def layout(em, H_px):
        font = _load_font(max(6, round(em)), p.font)
        adv = np.array([font.getlength(c) / SS for c in chars])
        gap = p.text_spacing / 100.0 * H_px
        return font, adv, gap, float(adv.sum() + gap * (len(chars) - 1))

    font, adv, gap, total = layout(em, H_px)
    scaled = False
    if total > 0.8 * L:
        f = 0.8 * L / total
        em, H_px, scaled = em * f, H_px * f, True
        font, adv, gap, total = layout(em, H_px)
    out = np.zeros((h, w), np.uint8)
    cur = -total / 2.0
    for ch, a in zip(chars, adv):
        mid = cur + a / 2.0
        cur += a + gap
        if ch.isspace():
            continue
        q = s0 + mid
        hh = max(a, 2.0) / 2.0
        tv = pos(q + hh) - pos(q - hh)
        nr = float(np.hypot(*tv))
        if nr < 1e-6:
            continue
        tv = tv / nr
        uv = np.array([tv[1], -tv[0]])           # « haut » de la lettre
        P = pos(q)
        bb = font.getbbox(ch, anchor="ls")
        pad = 2 * SS
        gw, gh = int(bb[2] - bb[0] + 2 * pad + 1), int(bb[3] - bb[1] + 2 * pad + 1)
        im = Image.new("L", (gw, gh), 0)
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), ch, font=font, fill=255, anchor="ls")
        xc, yb, sc = pad - bb[0] + a * SS / 2.0, pad - bb[1], 1.0 / SS
        M = np.array([[sc * tv[0], -sc * uv[0], P[0] - sc * xc * tv[0] + (sc * yb - H_px / 2) * uv[0]],
                      [sc * tv[1], -sc * uv[1], P[1] - sc * xc * tv[1] + (sc * yb - H_px / 2) * uv[1]]], np.float64)
        wr = cv2.warpAffine(np.array(im), M, (w, h), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out = np.maximum(out, wr)
    return (out > 127).astype(np.uint8), scaled


def _bridge_counters(plate, T, ppm, bw_mm):
    """Retire le texte (T = trou) de la plaque et relie par un petit pont les centres de lettres
    (A, O, B, D, P, R...) qui sinon tomberaient à la découpe."""
    m = ((plate > 0) & (T == 0)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    if n <= 2:
        return m
    main = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    near = cv2.dilate(T, np.ones((3, 3), np.uint8)) > 0
    cand = [int(i) for i in np.unique(lab[near]) if i not in (0, main)]
    if not cand:
        return m
    dist, (iy, ix) = ndi.distance_transform_edt(lab != main, return_indices=True)
    bw = max(2, int(round(bw_mm * ppm)))
    for i in cand:
        ys, xs = np.nonzero(lab == i)
        j = int(np.argmin(dist[ys, xs]))
        y, x = int(ys[j]), int(xs[j])
        cv2.line(m, (x, y), (int(ix[y, x]), int(iy[y, x])), 1, bw)
    return m


def _eyelet_dirs(p, w, h):
    """Directions (vecteurs unitaires, repère écran) des œillets demandés."""
    cornerish = p.shape in ("rect", "none", "rrect")

    def corner(sx, sy):
        v = np.array([sx * w / 2.0, sy * h / 2.0])
        return v / np.hypot(*v)

    def ang(a):
        return np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])

    return {"top": [ang(-90)],
            "top_left": [corner(-1, -1) if cornerish else ang(-135)],
            "top_right": [corner(1, -1) if cornerish else ang(-45)],
            "both": [ang(180), ang(0)]}.get(p.hang, [])


def decorate(plate, inside, p, ppm, ring_mm):
    """Texte courbe dans l'anneau et œillet(s) d'accroche. plate : matière (1) dans le repère de l'image.
    Retourne (plaque agrandie, (gauche, haut, droite, bas) en px, zone de l'œillet ou None, infos)."""
    h, w = plate.shape
    info = {}
    plate = plate.copy()
    ring_px = ring_mm * ppm
    if (p.text_top or "").strip() or (p.text_bottom or "").strip():
        if not text_supported(p):
            info["text_ignored"] = True
    if text_supported(p) and ring_px >= 4:
        for txt, where in ((p.text_top, "top"), (p.text_bottom, "bottom")):
            txt = (txt or "").strip()
            if not txt:
                continue
            T, scaled = _text_mask(inside, txt, where, p, ppm, ring_px)
            if T is None:
                continue
            plate = _bridge_counters(plate, T, ppm, p.text_bridge_mm)
            info["text"] = info.get("text", 0) + 1
            info["text_scaled"] = bool(info.get("text_scaled")) or scaled
    dirs = _eyelet_dirs(p, w, h)
    if not dirs or (p.shape == "none" and p.output in ("halftone", "lines")):
        return plate, (0, 0, 0, 0), None, info
    hole_r = max(1.0, p.hang_hole_mm * ppm / 2.0)
    Ro = hole_r + max(0.8, p.hang_tab_mm) * ppm
    d = hole_r + max(1.0, p.min_feature_mm) * ppm
    pen = min(1.2 * ppm, 0.5 * ring_px) if ring_px > 2 else 1.2 * ppm
    bw = Ro * (1.4 if p.hang_style == "drop" else 0.55)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    spots = []
    for n in dirs:
        r = 0.0
        while r < np.hypot(w, h):
            x, y = int(round(cx + n[0] * r)), int(round(cy + n[1] * r))
            if x < 0 or y < 0 or x >= w or y >= h or not inside[y, x]:
                break
            r += 0.5
        B = np.array([cx, cy]) + n * r
        C = B + n * d
        tv = np.array([-n[1], n[0]])
        a = np.linspace(0, 2 * np.pi, 64, endpoint=False)
        pts = np.vstack([C + Ro * np.stack([np.cos(a), np.sin(a)], 1),
                         B - n * pen + tv * bw, B - n * pen - tv * bw])
        spots.append((C, cv2.convexHull(pts.astype(np.float32))[:, 0, :]))
    allp = np.vstack([hp for _, hp in spots])
    l = max(0, int(np.ceil(-allp[:, 0].min())) + 2)
    t = max(0, int(np.ceil(-allp[:, 1].min())) + 2)
    rr = max(0, int(np.ceil(allp[:, 0].max() - (w - 1))) + 2)
    b = max(0, int(np.ceil(allp[:, 1].max() - (h - 1))) + 2)
    plate = cv2.copyMakeBorder(plate, t, b, l, rr, cv2.BORDER_CONSTANT, value=0)
    tab = np.zeros_like(plate)
    sh = np.array([l, t], np.float32)
    for C, hp in spots:
        cv2.fillPoly(tab, [np.round((hp + sh) * 16).astype(np.int32)], 1, shift=4)
    if p.shape == "none":  # pas d'anneau : on relie l'œillet à la matière la plus proche
        base = plate > 0
        if base.any() and (tab > 0).any():
            dist, (iy, ix) = ndi.distance_transform_edt(~base, return_indices=True)
            ys, xs = np.nonzero(tab)
            j = int(np.argmin(dist[ys, xs]))
            y, x = int(ys[j]), int(xs[j])
            th = max(2, int(round(max(1.5, 0.8 * p.hang_hole_mm) * ppm)))
            cv2.line(plate, (x, y), (int(ix[y, x]), int(iy[y, x])), 1, th)
    plate = plate | tab
    for C, _ in spots:
        c = C + sh
        cv2.circle(plate, (int(round(c[0])), int(round(c[1]))), int(round(hole_r)), 0, -1)
    info["hang"] = len(spots)
    info["hang_holes"] = [(float(C[0] + l), float(C[1] + t), float(hole_r)) for C, _ in spots]
    return plate, (l, t, rr, b), tab, info


def _pad_img(a, pad, value=0):
    l, t, r, b = pad
    if not (l or t or r or b):
        return a
    return cv2.copyMakeBorder(a, t, b, l, r, cv2.BORDER_CONSTANT, value=value)


def add_bridges(mat, anchor, bridge_mm, px_per_mm, min_island_mm2=3.0, max_bridge_mm=8.0, max_iter=250):
    """Relie chaque îlot de matière au corps principal, du plus proche au plus lointain.
    La pièce principale grandit au fil des ponts : un îlot loin du corps peut être relié via
    un îlot plus proche. Ne sont supprimés que : les îlots trop petits, et ceux qu'aucun pont
    de longueur <= max_bridge_mm ne peut atteindre à la fin.
    Retourne (matière, ponts, nb reliés, nb supprimés)."""
    thick = max(2, int(round(bridge_mm * px_per_mm)))
    max_dist = max_bridge_mm * px_per_mm
    min_area = min_island_mm2 * px_per_mm ** 2
    bridges = np.zeros_like(mat)
    linked = dropped = 0

    def main_label(lab, stats):
        if anchor is not None and lab[anchor[1], anchor[0]] > 0:
            return int(lab[anchor[1], anchor[0]])
        return 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))

    for _ in range(max_iter):
        n, lab, stats, _ = cv2.connectedComponentsWithStats(mat, connectivity=4)
        if n <= 2:
            break
        main = main_label(lab, stats)
        idx = [i for i in range(1, n) if i != main]
        small = [i for i in idx if stats[i, cv2.CC_STAT_AREA] < min_area]
        if small:
            mat[np.isin(lab, small)] = 0
            dropped += len(small)
            continue
        dist, (iy, ix) = ndi.distance_transform_edt(lab != main, return_indices=True)
        mins = np.atleast_1d(np.asarray(ndi.minimum(dist, lab, index=idx)))
        reach = [(float(m), i) for i, m in zip(idx, mins) if m <= max_dist]
        if not reach:  # plus rien d'atteignable : on supprime le reste
            mat[np.isin(lab, idx)] = 0
            dropped += len(idx)
            break
        reach.sort()
        for _, i in reach[: max(1, len(reach) // 2)]:
            ys, xs = np.nonzero(lab == i)
            j = int(np.argmin(dist[ys, xs]))
            y, x = int(ys[j]), int(xs[j])
            tx, ty = int(ix[y, x]), int(iy[y, x])
            cv2.line(mat, (x, y), (tx, ty), 1, thick)
            cv2.line(bridges, (x, y), (tx, ty), 1, thick)
            linked += 1
    return mat, (bridges & mat), linked, dropped


def extract_contours(mat, smooth, simplify):
    cnts, _ = cv2.findContours(mat, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    for c in cnts:
        pts = c[:, 0, :].astype(np.float64) + 0.5
        if len(pts) < 8:
            continue
        if smooth > 0:
            pts = np.stack([ndi.gaussian_filter1d(pts[:, i], smooth, mode="wrap") for i in (0, 1)], 1)
        if simplify > 0:
            pts = cv2.approxPolyDP(pts.astype(np.float32).reshape(-1, 1, 2), simplify, True)[:, 0, :]
        if len(pts) >= 3:
            polys.append(pts)
    return polys


# --------------------------------------------------------------------------
# Trame de points (halftone) : plaque percée de trous, taille selon la clarté
# --------------------------------------------------------------------------
def detect_face(rgb):
    """Cherche le visage principal. Retourne (x, y, w, h) en fraction de l'image, ou None.
    1) détecteur en cascade d'OpenCV s'il est installé avec ses données ; 2) sinon, zone de teinte chair (photos en couleur)."""
    h, w = rgb.shape[:2]
    sc = 640.0 / max(h, w)
    small = cv2.resize(rgb, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_AREA) if sc < 1 else rgb
    sh, sw = small.shape[:2]
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    try:
        import os
        path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if hasattr(cv2, "CascadeClassifier") and os.path.exists(path):
            det = cv2.CascadeClassifier(path)
            faces = det.detectMultiScale(cv2.equalizeHist(gray), 1.1, 5, minSize=(max(24, sw // 14), max(24, sh // 14)))
            if len(faces):
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                return (x / sw, y / sh, fw / sw, fh / sh)
    except Exception:
        pass
    ycc = cv2.cvtColor(small, cv2.COLOR_RGB2YCrCb)
    skin = ((ycc[..., 1] >= 135) & (ycc[..., 1] <= 175) & (ycc[..., 2] >= 80) & (ycc[..., 2] <= 125)).astype(np.uint8)
    if skin.mean() < 0.01:      # image en niveaux de gris ou sans teinte chair
        return None
    k = max(3, sw // 80) | 1
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    skin = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, np.ones((k * 3, k * 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(skin, connectivity=8)
    best, score = None, 0.0
    for i in range(1, n):
        x, y, bw, bh, a = st[i]
        if a < 0.004 * sw * sh:
            continue
        d = np.hypot(cen[i][0] / sw - 0.5, cen[i][1] / sh - 0.45)
        sco = a * (1.0 - min(0.8, d))
        if sco > score:
            best, score = (x, y, bw, bh), sco
    if best is None:
        return None
    x, y, bw, bh = best
    bh = min(bh, int(bw * 1.3))        # le cou et les épaules sont aussi de la peau : on garde un rectangle de visage
    return (x / sw, y / sh, bw / sw, bh / sh)


def _tone_light(rgb, p, subject, valid, ppm, pitch_mm):
    """Carte de clarté 0..1 (1 = clair = gros trou / fente large) pour la trame de points et le mode lignes."""
    h, w = rgb.shape[:2]
    if subject is not None and subject.any():
        n, lab, st, _ = cv2.connectedComponentsWithStats(subject.astype(np.uint8), connectivity=8)
        areas = st[1:, cv2.CC_STAT_AREA]
        if len(areas) > 1:
            keep_lab = [i + 1 for i, a in enumerate(areas) if a >= 0.1 * areas.max()]
            subject = np.isin(lab, keep_lab).astype(np.uint8)
    g = tone_gray(fill_outside(rgb, valid), p.tone_source)
    # étalement des niveaux : la trame a besoin de toute la plage de tons (noirs vraiment noirs, blancs blancs)
    roi = valid if subject is None else (subject if valid is None else (subject & valid))
    if roi is not None and not roi.any():
        roi = None
    sample = g[roi > 0] if roi is not None else g
    lo, hi = np.percentile(sample, [2, 98])
    g = np.clip((g.astype(np.float32) - lo) / max(1.0, hi - lo) * 255.0, 0, 255).astype(np.uint8)
    if p.dot_contrast > 0:  # égalisation d'histogramme sur le sujet : utilise tous les diamètres de trous
        ref = g[roi > 0] if roi is not None else g.ravel()
        cdf = np.cumsum(np.bincount(ref.astype(np.uint8).ravel(), minlength=256)).astype(np.float64)
        cdf = (cdf - cdf[0]) / max(1.0, cdf[-1] - cdf[0])
        eq = (cdf[g] * 255.0).astype(np.float32)
        c = float(np.clip(p.dot_contrast, 0, 1))
        g = np.clip((1 - c) * g.astype(np.float32) + c * eq, 0, 255).astype(np.uint8)
    if p.contrast:
        g = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(g)
    pitch_px = pitch_mm * ppm
    if p.dot_detail > 0:  # masque flou : accentue ce qui varie à l'échelle de quelques points
        base = cv2.GaussianBlur(g, (0, 0), pitch_px * 1.8).astype(np.float32)
        g = np.clip(g.astype(np.float32) + float(p.dot_detail) * (g.astype(np.float32) - base), 0, 255).astype(np.uint8)
    gf = cv2.GaussianBlur(g, (0, 0), max(0.7, pitch_px * 0.4)).astype(np.float32) / 255.0
    light = np.clip(gf, 0, 1) ** max(0.2, p.dot_gamma)
    if p.invert:
        light = 1.0 - light

    return light, subject


def _fits(p, h, w, ppm, ring, xm, ym, r_mm, X, Y):
    """Vrai si un trou (centre xm, ym en mm, rayon r_mm) tient dans la plaque : à distance de l'anneau."""
    web = p.min_web_mm
    W_mm, H_mm = w / ppm, h / ppm
    if p.shape == "none":  # pas de plaque ni d'anneau : seulement les trous, partout dans l'image
        return ((xm - r_mm) >= 0) & ((xm + r_mm) <= W_mm) & ((ym - r_mm) >= 0) & ((ym + r_mm) <= H_mm)
    if p.shape == "circle":
        R = min(W_mm, H_mm) / 2
        return (np.hypot(xm - W_mm / 2, ym - H_mm / 2) + r_mm) <= (R - ring - web)
    if p.shape in GENERIC_SHAPES:  # ovale, cœur, étoile... : distance au bord de la forme
        din = cv2.distanceTransform(shape_inside(p.shape, h, w), cv2.DIST_L2, 5)
        return (din[Y.astype(int), X.astype(int)] / ppm) >= (ring + web + r_mm)
    m_ = ring + web
    return ((xm - r_mm) >= m_) & ((xm + r_mm) <= W_mm - m_) & ((ym - r_mm) >= m_) & ((ym + r_mm) <= H_mm - m_)


def _line_holes(p, light, subject, valid, h, w, ppm, ring):
    """Fentes de largeur variable (plus claires = plus larges) le long de lignes parallèles. Retourne des polygones (mm)."""
    from scipy import ndimage as _ndi
    pitch_px = p.line_pitch_mm * ppm
    ang = np.radians(p.line_angle)
    d = np.array([np.cos(ang), np.sin(ang)])
    nrm = np.array([-d[1], d[0]])
    dmax = max(0.0, p.line_pitch_mm - p.min_web_mm)
    dmin = min(p.min_dot_mm, dmax)
    if dmax <= 0 or dmax < dmin:
        return []
    step_px = max(1.0, min(0.4, p.line_pitch_mm / 4.0) * ppm)
    R = np.hypot(w, h) / 2.0
    K = int(R / pitch_px) + 1
    u = np.arange(-R, R + step_px, step_px)
    v = np.arange(-K, K + 1) * pitch_px
    X = w / 2.0 + u[None, :] * d[0] + v[:, None] * nrm[0]
    Y = h / 2.0 + u[None, :] * d[1] + v[:, None] * nrm[1]
    inb = (X >= 0) & (X < w - 1) & (Y >= 0) & (Y < h - 1)
    Xc, Yc = np.clip(X, 0, w - 2).astype(int), np.clip(Y, 0, h - 2).astype(int)
    Le = np.sqrt(light[Yc, Xc])
    t = np.clip((Le - 0.28) / 0.72, 0, 1)
    wd = dmin + (dmax - dmin) * t                         # largeur de la fente (mm)
    keep = inb & (Le >= 0.28)
    if subject is not None:
        keep &= subject[Yc, Xc] > 0
    if valid is not None:
        keep &= valid[Yc, Xc] > 0
    keep &= _fits(p, h, w, ppm, ring, X / ppm, Y / ppm, wd / 2.0, Xc, Yc)
    step_mm = step_px / ppm
    piece = int(p.line_break_mm / step_mm) if p.line_break_mm > 0 else 10 ** 9
    gap = int(max(0.8, 1.5 * p.min_web_mm) / step_mm) + 1
    polys = []
    for i in range(len(v)):
        row = keep[i]
        if not row.any():
            continue
        idx = np.nonzero(row)[0]
        if piece < 10 ** 8:   # coupures (ponts) à des positions décalées d'une ligne à l'autre : pas de « trait » aligné
            per = piece + gap
            sh = int(((np.sin(i * 12.9898) * 43758.5453) % 1.0) * per)  # décalage pseudo-aléatoire par ligne
            idx = idx[((idx - sh) % per) < piece]
        cuts = np.nonzero(np.diff(idx) > 1)[0] + 1
        for run in np.split(idx, cuts):
            if len(run) < 3:
                continue
            for seg in (run,):
                wsm = _ndi.gaussian_filter1d(wd[i, seg], 1.5, mode="nearest") * ppm / 2.0   # demi-largeur en px
                P = np.stack([X[i, seg], Y[i, seg]], 1)
                poly = np.vstack([P + nrm * wsm[:, None], (P - nrm * wsm[:, None])[::-1]])
                polys.append(poly / ppm)
    return polys


def halftone(rgb, p, subject=None, valid=None):
    """Photo -> plaque pleine percée de trous ronds. Zones claires = gros trous, zones sombres =
    petits trous ou rien. Aucun pont nécessaire : la matière entre les trous relie tout."""
    t0 = time.time()
    h, w = rgb.shape[:2]
    ppm = max(h, w) / p.size_mm
    light, subject = _tone_light(rgb, p, subject, valid, ppm, p.line_pitch_mm if p.output == "lines" else p.dot_pitch_mm)
    ring = effective_ring(p)
    lines = p.output == "lines"
    frameless = p.shape == "none"

    W_mm, H_mm = w / ppm, h / ppm
    hole_polys = []
    if lines:  # fentes de largeur variable
        hole_polys = _line_holes(p, light, subject, valid, h, w, ppm, ring)
        xm = ym = r_mm = np.zeros(0)
    else:      # réseau de points tourné
        pitch_px = p.dot_pitch_mm * ppm
        ang = np.radians(p.dot_angle)
        ca, sa = np.cos(ang), np.sin(ang)
        n = int(np.hypot(w, h) / pitch_px) + 2
        ii, jj = np.meshgrid(np.arange(-n, n + 1), np.arange(-n, n + 1))
        u, v = ii * pitch_px, jj * pitch_px
        X = w / 2 + u * ca - v * sa
        Y = h / 2 + u * sa + v * ca
        ok = (X >= 0) & (X < w - 1) & (Y >= 0) & (Y < h - 1)
        X, Y = X[ok], Y[ok]
        L = light[Y.astype(int), X.astype(int)]
        dmax = max(0.0, p.dot_pitch_mm - p.min_web_mm)          # plus gros trou possible (mm)
        dmin = min(p.min_dot_mm, dmax)                           # plus petit trou découpable
        # tons -> diamètre : en dessous de 8 % de clarté, pas de trou ; sinon de dmin à dmax
        Le = np.sqrt(L)                                          # surface du trou ~ clarté
        t = np.clip((Le - 0.28) / 0.72, 0, 1)
        d_mm = dmin + (dmax - dmin) * t
        r_mm = d_mm / 2.0
        keep = (Le >= 0.28) & (dmax >= dmin) & (dmax > 0)
        if subject is not None:
            keep &= subject[Y.astype(int), X.astype(int)] > 0   # hors sujet : plaque pleine
        if valid is not None:
            keep &= valid[Y.astype(int), X.astype(int)] > 0     # hors photo (marges) : plaque pleine
        xm, ym = X / ppm, Y / ppm
        keep &= _fits(p, h, w, ppm, ring, xm, ym, r_mm, X, Y)
        xm, ym, r_mm = xm[keep], ym[keep], r_mm[keep]

    # plaque : forme + texte dans l'anneau + œillet (le tout peut agrandir le cadre)
    if frameless:
        plate = np.zeros((h, w), np.uint8)
    elif p.shape == "circle":
        plate = np.zeros((h, w), np.uint8)
        cv2.circle(plate, (int(round(w / 2)), int(round(h / 2))), int(round(min(W_mm, H_mm) / 2 * ppm)) - 1, 1, -1)
    else:
        plate = shape_inside(p.shape, h, w)
    pad, tab, dinfo = (0, 0, 0, 0), None, {}
    if not frameless:
        plate, pad, tab, dinfo = decorate(plate, shape_inside(p.shape, h, w), p, ppm, ring)
    decorated = bool(dinfo.get("hang") or dinfo.get("text"))
    xm, ym = xm + pad[0] / ppm, ym + pad[1] / ppm
    hole_polys = [q + np.array([pad[0], pad[1]]) / ppm for q in hole_polys]
    rgb, subject = _pad_img(rgb, pad, (255, 255, 255)), (None if subject is None else _pad_img(subject, pad))
    h2, w2 = plate.shape
    Wp_mm, Hp_mm = w2 / ppm, h2 / ppm

    # polygones : contour extérieur + un cercle par trou
    polys_mm = []
    if frameless:
        pass
    elif p.shape == "circle" and not decorated:
        t = np.linspace(0, 2 * np.pi, 361)[:-1]
        R = min(W_mm, H_mm) / 2
        polys_mm.append(np.stack([W_mm / 2 + R * np.cos(t), H_mm / 2 + R * np.sin(t)], 1))
    elif p.shape == "rect" and not decorated:
        polys_mm.append(np.array([[0, 0], [W_mm, 0], [W_mm, H_mm], [0, H_mm]], float))
    else:
        k = ppm / 12.0
        polys_mm += [q / ppm for q in extract_contours(plate, p.smooth * k, p.simplify * k)]
    for x, y, r in zip(xm, ym, r_mm):
        k = int(min(24, max(8, 2 * np.pi * r / 0.2)))
        t = np.linspace(0, 2 * np.pi, k + 1)[:-1]
        polys_mm.append(np.stack([x + r * np.cos(t), y + r * np.sin(t)], 1))
    polys_mm += hole_polys

    # aperçu : noir = matière, blanc = trou
    mat = plate.copy() if not frameless else np.zeros((h2, w2), np.uint8)
    if frameless:
        mat[:] = 1
    for x, y, r in zip(xm * ppm, ym * ppm, r_mm * ppm):
        cv2.circle(mat, (int(round(x)), int(round(y))), max(1, int(round(r))), 0, -1)
    for q in hole_polys:
        cv2.fillPoly(mat, [np.round(q * ppm * 16).astype(np.int32)], 0, shift=4)
    length = float(sum(np.sum(np.hypot(*np.diff(np.vstack([q, q[:1]]), axis=0).T)) for q in polys_mm))
    holes = [(x / ppm, y / ppm, r / ppm) for x, y, r in dinfo.pop("hang_holes", [])]
    stats = dict(threshold=0.0, contours=len(polys_mm), length_mm=length, linked=0, dropped=0, holes=int(len(r_mm)) + len(hole_polys),
                 **({"lines_across": int(round(W_mm / max(0.1, p.line_pitch_mm)))} if lines else
                    {"dots_across": int(round(W_mm / max(0.1, p.dot_pitch_mm)))}),
                 w_mm=Wp_mm, h_mm=Hp_mm, px=[w2, h2], seconds=round(time.time() - t0, 2), **dinfo)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    sheet = _pad_img(_sheet_mask(p.shape, h, w), pad)
    base_sheet = sheet.copy()      # forme seule, sans la languette de l'œillet (pour le caisson)
    if tab is not None:
        sheet = sheet | tab
    return Result(rgb, gray, subject, mat, mat, np.zeros_like(mat), polys_mm, Wp_mm, Hp_mm, stats, sheet,
                  tab=tab, hang_holes=holes, base_sheet=base_sheet)


# --------------------------------------------------------------------------
# Gravure : image tramée à la résolution de la machine + contour de découpe
# --------------------------------------------------------------------------
def engrave_result(rgb, p, subject=None, valid=None):
    try:
        from . import engrave as E
    except ImportError:
        import engrave as E
    t0 = time.time()
    h, w = rgb.shape[:2]
    ppm = max(h, w) / p.size_mm
    if subject is not None and subject.shape != (h, w):
        subject = cv2.resize(subject, (w, h), interpolation=cv2.INTER_NEAREST)
    gray = tone_gray(fill_outside(rgb, valid), p.tone_source)
    if p.contrast:
        gray = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(gray)
    if subject is not None:
        gray = np.where(subject > 0, gray, 255).astype(np.uint8)
    inside = shape_inside(p.shape, h, w)
    ring_mm = effective_ring(p)
    has_text = text_supported(p) and bool((p.text_top or "").strip() or (p.text_bottom or "").strip())
    plate, pad, tab, dinfo = decorate(inside.copy(), inside, p, ppm, ring_mm)
    base = _pad_img(inside, pad)
    sheet = _pad_img(_sheet_mask(p.shape, h, w), pad)
    base_sheet = sheet.copy()      # forme seule, sans la languette de l'œillet (pour le caisson)
    if tab is not None:
        sheet = sheet | tab
    gray = _pad_img(gray, pad, 255)
    rgb = _pad_img(rgb, pad, (255, 255, 255))
    subj = None if subject is None else _pad_img(subject, pad)
    # zone gravée : à l'intérieur de la pièce, à distance du bord (ou de l'anneau si texte)
    border = (ring_mm if has_text else p.eng_border_mm) * ppm
    d = cv2.distanceTransform(cv2.copyMakeBorder(base, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1]
    area = (d >= max(0.0, border)) & (base > 0)
    if valid is not None:
        area &= _pad_img(valid, pad) > 0
    H2, W2 = plate.shape
    w_mm, h_mm = W2 / ppm, H2 / ppm
    tw, th = max(8, int(round(w_mm / 25.4 * p.eng_dpi))), max(8, int(round(h_mm / 25.4 * p.eng_dpi)))
    g = np.where(area, gray, 255).astype(np.float32)
    g = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA if tw < W2 else cv2.INTER_CUBIC)
    md = cv2.resize(area.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST) > 0
    g = E.prepare_gray(g, p.eng_brightness, p.eng_contrast, p.eng_gamma)
    if p.eng_sharpen > 0:
        sg = max(0.8, 0.35 / 25.4 * p.eng_dpi)
        g = np.clip(g + float(p.eng_sharpen) * (g - cv2.GaussianBlur(g, (0, 0), sg)), 0, 255)
    if p.eng_invert:
        g = 255.0 - g
    g[~md] = 255.0
    bits = E.dither(g, p.eng_dither, p.eng_levels)
    bits[~md] = 255
    k = ppm / 12.0
    polys_mm = [q / ppm for q in extract_contours(plate, p.smooth * k, p.simplify * k)]
    length = sum(float(np.sum(np.hypot(*np.diff(np.vstack([q, q[:1]]), axis=0).T))) for q in polys_mm)
    cover = 100.0 * float(1.0 - bits[md].mean() / 255.0) if md.any() else 0.0
    holes = [(x / ppm, y / ppm, r / ppm) for x, y, r in dinfo.pop("hang_holes", [])]
    stats = dict(threshold=0.0, contours=len(polys_mm), length_mm=length, linked=0, dropped=0,
                 w_mm=w_mm, h_mm=h_mm, px=[W2, H2], eng_px=[tw, th], eng_dpi=p.eng_dpi,
                 eng_cover=round(cover, 1), eng_minutes=round(E.estimate_minutes(h_mm, w_mm, p.eng_dpi, p.eng_speed), 1),
                 seconds=round(time.time() - t0, 2), **dinfo)
    gray = _pad_img(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (0, 0, 0, 0))
    return Result(rgb, gray, subj, plate, plate, np.zeros_like(plate), polys_mm, w_mm, h_mm, stats, sheet,
                  engrave=bits, eng_dpi=float(p.eng_dpi), tab=tab, hang_holes=holes, base_sheet=base_sheet)


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


def engrave_png_bytes(res):
    import io
    buf = io.BytesIO()
    Image.fromarray(res.engrave).save(buf, "PNG", dpi=(res.eng_dpi, res.eng_dpi))
    return buf.getvalue()


def svg_engrave_string(res):
    """SVG à la bonne échelle (mm) : image tramée incrustée + contours de découpe (calque CUT)."""
    import base64
    b64 = base64.b64encode(engrave_png_bytes(res)).decode()
    paths = "\n".join('<path d="M' + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + ' Z"/>' for q in res.polys_mm)
    W, H = res.w_mm, res.h_mm
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">\n'
            f'<image id="ENGRAVE" x="0" y="0" width="{W:.3f}" height="{H:.3f}" preserveAspectRatio="none" '
            f'xlink:href="data:image/png;base64,{b64}" href="data:image/png;base64,{b64}"/>\n'
            f'<g id="CUT" fill="none" stroke="#ff0000" stroke-width="0.1">\n{paths}\n</g>\n</svg>\n')


# --------------------------------------------------------------------------
# Pipeline complet
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Low poly : photo -> maillage de triangles (poutres + facettes pleines)
# --------------------------------------------------------------------------
def _poisson_points(dom_xy, rad, k, seeds, rng, max_cand):
    """Semis de Poisson à rayon variable (dart throwing) ; `seeds` = points imposés (contour)."""
    cs = max(2.0, float(k * rad.max()))
    grid = {}

    def put(x, y, r):
        grid.setdefault((int(x // cs), int(y // cs)), []).append((x, y, r))
    for x, y in seeds:
        put(x, y, k * rad[min(rad.shape[0] - 1, int(y)), min(rad.shape[1] - 1, int(x))])
    out = []
    idx = rng.permutation(len(dom_xy))[:max_cand]
    for i in idx:
        x, y = dom_xy[i]
        r = k * rad[y, x]
        cx, cy = int(x // cs), int(y // cs)
        ok = True
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for qx, qy, qr in grid.get((gx, gy), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < (0.5 * (r + qr)) ** 2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            put(x, y, r)
            out.append((float(x), float(y)))
    return out


def _contour_points(dom, step):
    """Sommets le long du contour du domaine : angles (approxPolyDP) + points intermédiaires tous les ~step px."""
    cnts, _ = cv2.findContours(dom.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    pts = []
    for c in cnts:
        if len(c) < 8:
            continue
        ap = cv2.approxPolyDP(c, max(1.0, 0.3 * step), True).reshape(-1, 2).astype(float)
        n = len(ap)
        for i in range(n):
            a, b = ap[i], ap[(i + 1) % n]
            pts.append(tuple(a))
            L = float(np.hypot(*(b - a)))
            m = int(L // step)
            for j in range(1, m + 1):
                if L - j * step > 0.5 * step:
                    pts.append(tuple(a + (b - a) * (j * step / L)))
    return pts


def _geo_seeds(dom, gray, p, area):
    """Sommets 'géométriques' : silhouette simplifiée en polygone + polygones des taches sombres (yeux, nez, oreilles)."""
    eps = max(1.0, float(p.lp_simplify) * 0.01 * np.sqrt(area))
    pts = []
    cnts, _ = cv2.findContours(dom.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cnts:
        if len(c) >= 8 and cv2.contourArea(c) > 0.002 * area:
            pts += [tuple(q) for q in cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(float)]
    gd = gray[dom]
    if float(gd.std()) >= 14.0:
        g = cv2.GaussianBlur(gray, (0, 0), max(1.0, 0.004 * np.sqrt(area)))
        thr = otsu_value(gd.astype(np.uint8).ravel()) + float(p.lp_level) * 2.55
        dark = ((g > thr) if p.invert else (g < thr)) & dom
        dark = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        er = cv2.erode(dom.astype(np.uint8), np.ones((5, 5), np.uint8))
        cs, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            a = cv2.contourArea(c)
            if a < 0.003 * area or a > 0.5 * area:
                continue
            for q in cv2.approxPolyDP(c, eps * 0.8, True).reshape(-1, 2):
                if er[q[1], q[0]]:                     # déjà sur la silhouette : pas de doublon
                    pts.append((float(q[0]), float(q[1])))
    return pts


def ai_mask(rgb, valid=None):
    """Masque du sujet par IA (subject_ai), ou None si indisponible."""
    try:
        try:
            from . import subject_ai
        except ImportError:
            import subject_ai
        return subject_ai.mask(rgb, valid)
    except Exception:
        return None


def auto_subject(rgb, valid=None):
    """Sujet sur fond uni : pixels éloignés de la couleur du bord de l'image, silhouette pleine (trous comblés).
    Retourne un masque uint8 (1 = sujet) ou None si le fond n'est pas uni / le résultat n'est pas plausible."""
    h, w = rgb.shape[:2]
    k = 640.0 / max(h, w)
    small = cv2.resize(rgb, (max(8, int(w * k)), max(8, int(h * k))), interpolation=cv2.INTER_AREA) if k < 1 else rgb
    sh, sw = small.shape[:2]
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    b = max(2, int(0.03 * min(sh, sw)))
    bm = np.zeros((sh, sw), bool)
    bm[:b, :] = bm[-b:, :] = True
    bm[:, :b] = bm[:, -b:] = True
    bg = np.median(lab[bm], axis=0)
    dist = np.linalg.norm(lab - bg, axis=2)
    if np.percentile(dist[bm], 90) > 18:
        return None                                        # fond non uni
    d8 = np.clip(dist * 2.5, 0, 255).astype(np.uint8)
    thr = max(30.0, otsu_value(d8.ravel()) * 0.8)
    m = (d8 > thr).astype(np.uint8)
    kk = max(3, int(0.015 * min(sh, sw)) | 1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
    inv = (1 - m).astype(np.uint8)
    ff = np.zeros((sh + 2, sw + 2), np.uint8)
    seed = None
    for y, x in ((0, 0), (0, sw - 1), (sh - 1, 0), (sh - 1, sw - 1)):
        if inv[y, x]:
            seed = (x, y)
            break
    if seed is not None:
        cv2.floodFill(inv, ff, seed, 2)                     # fond relié au bord
        m = (inv != 2).astype(np.uint8)                     # tout le reste = sujet (trous comblés)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return None
    big = st[1:, cv2.CC_STAT_AREA].max()
    keep = [i + 1 for i in range(n - 1) if st[i + 1, cv2.CC_STAT_AREA] >= max(0.03 * big, 0.002 * sh * sw)]
    m = np.isin(lbl, keep).astype(np.uint8)
    cov = m.mean()
    if cov < 0.03 or cov > 0.92:
        return None
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR if k < 1 else cv2.INTER_NEAREST)
    m = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5) > 0.5).astype(np.uint8)
    if valid is not None:
        m = m & valid
    return m


def _dark_threshold(gd, invert=False):
    """Seuil des facettes pleines : Otsu à deux niveaux (la classe la plus sombre, ou la plus claire si invert),
    pour ne remplir que les vraies zones sombres (yeux, cheveux, ombres) et pas tous les tons moyens."""
    g8 = gd.astype(np.uint8).ravel()
    t1 = otsu_value(g8)
    part = g8[g8 > t1] if invert else g8[g8 < t1]
    if len(part) < 0.03 * len(g8):
        return float(t1)
    return float(otsu_value(part))


def lowpoly_mask(rgb, p, domain, ppm, guides=None):
    """Matière (1) d'un décor low poly : arêtes du maillage de Delaunay (poutres de lp_beam_mm) + une part
    lp_fill_pct des triangles pleins (les plus sombres). Les sommets suivent les contours de l'image.
    Retourne (masque, nb_sommets, nb_triangles)."""
    from scipy.spatial import Delaunay
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    dom = (domain > 0) if domain is not None else np.ones((h, w), bool)
    if dom.sum() < 50:
        dom = np.ones((h, w), bool)
    g = cv2.GaussianBlur(gray, (0, 0), max(1.0, 0.5 * ppm))
    mag = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    ref = float(np.percentile(mag[dom], 95)) + 1e-6
    dens = np.clip(mag / ref, 0, 1) ** 0.8
    foc = float(np.clip(p.lp_focus, 0, 1))
    rad = 1.0 - 0.7 * foc * dens                       # rayon relatif : petit près des détails
    rad = cv2.GaussianBlur(rad.astype(np.float32), (0, 0), max(1.0, 0.8 * ppm))
    ys, xs = np.nonzero(dom)
    area = float(len(xs))
    n = max(12, int(p.lp_points))
    s = np.sqrt(area / n)
    k = float(np.sqrt(0.696 * np.mean(1.0 / rad[dom] ** 2) * area / n))   # rayon moyen du semis
    if p.lp_geo:
        seeds = _geo_seeds(dom, gray, p, area)
    else:
        seeds = _contour_points(dom, 0.9 * k)
    g_edges = []
    if guides:         # sommets et arêtes posés à la main (fractions de l'image)
        for q in (guides.get("pts") or [])[:300]:
            seeds.append((float(q[0]) * (w - 1), float(q[1]) * (h - 1)))
        for s4 in (guides.get("edges") or [])[:300]:
            a = np.array([float(s4[0]) * (w - 1), float(s4[1]) * (h - 1)])
            b = np.array([float(s4[2]) * (w - 1), float(s4[3]) * (h - 1)])
            g_edges.append((a, b))
            L = float(np.hypot(*(b - a)))
            for j in range(0, max(1, int(L // (0.9 * k))) + 1):    # sommets le long de l'arête : le maillage la suit
                seeds.append(tuple(a + (b - a) * min(1.0, j * 0.9 * k / max(L, 1e-6))))
            seeds.append(tuple(b))
    rng = np.random.default_rng(int(p.lp_seed) * 7919 + 13)
    dom_xy = np.stack([xs, ys], 1)
    inner = _poisson_points(dom_xy, rad, k, seeds, rng, min(30000, 30 * n))
    pts = np.array(seeds + inner, float)
    # points hors du domaine (contour) ramenés dans l'image
    pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)
    pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)
    if len(pts) < 4:
        return np.zeros((h, w), np.uint8), len(pts), 0
    tri = Delaunay(pts).simplices
    domd = cv2.dilate(dom.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    P = pts[tri]                                       # (T, 3, 2)
    cen = P.mean(1)
    ci = np.clip(np.round(cen).astype(int), 0, [w - 1, h - 1])
    keep = dom[ci[:, 1], ci[:, 0]]
    mids = [(P[:, a] + P[:, b]) / 2 for a, b in ((0, 1), (1, 2), (2, 0))]
    cnt = np.zeros(len(tri), int)
    for m in mids:
        mi = np.clip(np.round(m).astype(int), 0, [w - 1, h - 1])
        cnt += domd[mi[:, 1], mi[:, 0]]
    keep &= cnt >= 2
    tri, P, cen = tri[keep], P[keep], cen[keep]
    mask = np.zeros((h, w), np.uint8)
    if len(tri) == 0:
        return mask, len(pts), 0
    # ton moyen de chaque facette (étiquettes raster + moyenne)
    lab = np.zeros((h, w), np.int32)
    for i in range(len(tri)):
        cv2.fillConvexPoly(lab, np.round(P[i] * 16).astype(np.int32), i + 1, cv2.LINE_8, 4)
    cnt = np.bincount(lab.ravel(), minlength=len(tri) + 1)[1:]
    sm = np.bincount(lab.ravel(), weights=gray.ravel(), minlength=len(tri) + 1)[1:]
    tone = np.where(cnt > 0, sm / np.maximum(cnt, 1), 255.0)
    style = p.lp_style if p.lp_style in ("wire", "solid", "shade") else "shade"
    th = max(1, int(round(max(p.lp_beam_mm, p.min_feature_mm + 0.2) * ppm)))
    th = max(max(1, int(round((p.min_feature_mm + 0.2) * ppm))), min(th, int(round(0.3 * s))))   # poutres jamais plus larges que 30 % d'une facette : le maillage reste ajouré
    if style == "solid":
        gd = gray[dom]
        if float(gd.std()) < 14.0:                  # sujet d'un seul ton (silhouette) : maillage seul
            sel = np.zeros(len(tri), bool)
        else:
            thr = _dark_threshold(gd, p.invert) + float(p.lp_level) * 2.55
            sel = (tone > thr) if p.invert else (tone < thr)
        for i in np.nonzero(sel)[0]:
            cv2.fillPoly(mask, [np.round(P[i] * 16).astype(np.int32)], 1, shift=4)
    elif style == "shade":
        lo, hi = np.percentile(tone, [3, 97])
        L = np.clip((tone - lo) / max(1e-6, hi - lo), 0, 1)
        if not p.invert:
            L = L                                 # clair -> grand trou ; sombre -> facette pleine
        else:
            L = 1 - L
        a = np.hypot(*(P[:, 1] - P[:, 0]).T)
        b = np.hypot(*(P[:, 2] - P[:, 1]).T)
        c3 = np.hypot(*(P[:, 0] - P[:, 2]).T)
        sp = (a + b + c3) / 2
        ar = np.sqrt(np.maximum(sp * (sp - a) * (sp - b) * (sp - c3), 1e-9))
        r_in = ar / np.maximum(sp, 1e-6)           # rayon du cercle inscrit
        fmax = np.clip(1 - (th / 2.0) / np.maximum(r_in, 1e-6), 0, 1)
        sc = fmax * L
        min_hole = max(1.0, 0.6 * ppm)              # trou plus petit que ~0,6 mm : facette pleine
        for i in range(len(tri)):
            cv2.fillPoly(mask, [np.round(P[i] * 16).astype(np.int32)], 1, shift=4)
            if sc[i] * r_in[i] >= min_hole / 2:
                hp = cen[i] + (P[i] - cen[i]) * sc[i]
                cv2.fillPoly(mask, [np.round(hp * 16).astype(np.int32)], 0, shift=4)
    # arêtes uniques en poutres arrondies
    edges = set()
    for a, b, c2 in tri:
        for e in ((a, b), (b, c2), (c2, a)):
            edges.add((min(e), max(e)))
    for a, b in edges:
        cv2.line(mask, tuple(np.round(pts[a] * 16).astype(int)), tuple(np.round(pts[b] * 16).astype(int)),
                 1, th, cv2.LINE_8, 4)
    for a, b in g_edges:       # arêtes guidées : toujours dessinées en poutre pleine, même si le maillage les coupe
        cv2.line(mask, tuple(np.round(a * 16).astype(int)), tuple(np.round(b * 16).astype(int)), 1, th, cv2.LINE_8, 4)
    for x, y in pts[np.unique(tri)]:
        cv2.circle(mask, (int(round(x * 16)), int(round(y * 16))), int(round(th * 16 / 2)), 1, -1, cv2.LINE_8, 4)
    return mask, len(pts), len(tri)


def qr_payload(p):
    """Texte encodé dans le QR code (lien / texte libre, ou Wi-Fi au format standard)."""
    if p.qr_kind == "wifi":
        esc = lambda s: "".join("\\" + ch if ch in '\\;,:"' else ch for ch in str(s or ""))
        sec = p.qr_sec if p.qr_sec in ("WPA", "WEP", "nopass") else "WPA"
        pw = "" if sec == "nopass" else f"P:{esc(p.qr_pass)};"
        return f"WIFI:T:{sec};S:{esc(p.qr_ssid)};{pw};"
    return str(p.qr_text or "")


def qr_matrix(text, ec="Q"):
    """Matrice booléenne (True = module sombre) sans marge, via l'encodeur QR d'OpenCV. Lève ValueError."""
    if not text:
        raise ValueError("empty")
    if not hasattr(cv2, "QRCodeEncoder"):
        raise ValueError("OpenCV too old (QRCodeEncoder)")
    lv = {"L": "CORRECT_LEVEL_L", "M": "CORRECT_LEVEL_M", "Q": "CORRECT_LEVEL_Q", "H": "CORRECT_LEVEL_H"}[ec if ec in "LMQH" else "Q"]
    prm = cv2.QRCodeEncoder_Params()
    prm.correction_level = getattr(cv2, "QRCodeEncoder_" + lv)
    try:
        im = cv2.QRCodeEncoder.create(prm).encode(text)
    except cv2.error as e:
        raise ValueError("text too long for a QR code") from e
    if im is None or im.ndim != 2 or im.shape[0] < 25:
        raise ValueError("encoding failed")
    ys, xs = np.nonzero(im == 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return im[y0:y1, x0:x1] == 0


def qr_masks(h, w, p, ppm):
    """Masques d'un QR code centré dans l'image : (raw = matière à découper, marks = zones gravées, info, geo).
    engrave : plaque pleine + modules gravés ; cut : modules ajourés (matière = modules sombres, marge claire ajourée)."""
    info = {}
    M = qr_matrix(qr_payload(p), p.qr_ec)
    n = M.shape[0]
    side = float(p.qr_side_mm) * ppm
    qzm = 2.0                                           # marge ajourée du mode « cut » (en modules)
    need = side * (n + 2 * qzm) / n
    lim = 0.96 * min(h, w)
    if need > lim:
        side *= lim / need
        info["qr_clamped"] = True
    S = max(n, int(round(side)))
    cell = S / n
    x0, y0 = (w - S) // 2, (h - S) // 2
    big = cv2.resize(M.astype(np.uint8), (S, S), interpolation=cv2.INTER_NEAREST)
    Dm = np.zeros((h, w), np.uint8)
    Dm[y0:y0 + S, x0:x0 + S] = big
    R = np.zeros((h, w), np.uint8)
    R[y0:y0 + S, x0:x0 + S] = 1
    q = int(round(qzm * cell))
    Q = np.zeros((h, w), np.uint8)
    Q[max(0, y0 - q):y0 + S + q, max(0, x0 - q):x0 + S + q] = 1
    inv = bool(p.qr_invert)
    if p.qr_mode == "cut":
        holes = Dm if inv else (Q & (1 - Dm))
        raw, marks = (1 - holes).astype(np.uint8), None
    else:
        marks = (R & (1 - Dm)) if inv else Dm
        raw = np.ones((h, w), np.uint8)
    mod_mm = cell / ppm
    info.update(qr_modules=int(n), qr_module_mm=round(mod_mm, 2))
    lo = 1.5 if p.qr_mode == "cut" else 0.8
    if mod_mm < lo:
        info["qr_small"] = True
    return raw, marks, info, dict(x0=x0, y0=y0, S=S, q=q, n=n, text=qr_payload(p))


def qr_scan_check(img_black, geo):
    """Relit le QR rendu (img_black : 1 = noir) comme un téléphone. Retourne 'ok' | 'inverted' | 'fail'."""
    h, w = img_black.shape
    x0, y0, S, n = geo["x0"], geo["y0"], geo["S"], geo["n"]
    cell = S / n
    crop = img_black[y0:y0 + S, x0:x0 + S]           # seulement les modules : les ponts de la marge ne comptent pas
    f = max(1, int(np.ceil(10.0 / max(cell, 1e-6))))
    pic = np.where(crop > 0, 0, 255).astype(np.uint8)
    pic = cv2.copyMakeBorder(pic, int(4 * cell), int(4 * cell), int(4 * cell), int(4 * cell), cv2.BORDER_CONSTANT, value=255)
    if f > 1:
        pic = cv2.resize(pic, None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
    det = cv2.QRCodeDetector()
    try:
        if det.detectAndDecode(pic)[0] == geo["text"]:
            return "ok"
        if det.detectAndDecode(255 - pic)[0] == geo["text"]:
            return "inverted"
    except cv2.error:
        pass
    return "fail"


LAYER_COLORS = ["#ff3b30", "#34c759", "#0a84ff", "#ff9f0a", "#bf5af2", "#64d2ff", "#ffd60a", "#ff375f"]   # couleurs des calques de LSP


def _layer_domain(rgb, p, subject, valid):
    """Zone du sujet pour le multicouche : celle donnée, sinon IA / fond uni, sinon tout le cadre."""
    if subject is not None:
        return subject.astype(np.uint8)
    filled = fill_outside(rgb, valid)
    dom = ai_mask(filled, valid) if p.ai_subject else None
    if dom is None:
        dom = auto_subject(filled, valid)
    if dom is None:
        dom = np.ones(rgb.shape[:2], np.uint8) if valid is None else valid.astype(np.uint8)
    return dom


def parse_picks(txt):
    """'#rrggbb,#rrggbb' -> liste de tuples RGB (2 à 8 couleurs), sinon []."""
    out = []
    for t in str(txt or "").split(","):
        t = t.strip().lstrip("#")
        if len(t) == 6:
            try:
                out.append(tuple(int(t[i:i + 2], 16) for i in (0, 2, 4)))
            except ValueError:
                pass
    return out[:8] if len(out) >= 2 else []


def is_flat_image(rgb, valid=None, top=6, share=0.85):
    """Vrai pour un logo / aplat : quelques couleurs seulement couvrent presque toute l'image."""
    small = cv2.resize(rgb, None, fx=min(1.0, 300.0 / max(rgb.shape[:2])), fy=min(1.0, 300.0 / max(rgb.shape[:2])),
                       interpolation=cv2.INTER_AREA)
    q = (small >> 4).astype(np.int32)
    code = (q[:, :, 0] << 8) | (q[:, :, 1] << 4) | q[:, :, 2]
    if valid is not None:
        vm = cv2.resize(valid.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        if vm.any():
            code = code[vm]
    cnt = np.sort(np.bincount(code.ravel()))[::-1]
    return float(cnt[:top].sum()) / max(1, code.size) >= share


def color_classes(rgb, dom, n, valid=None, auto=True, picks=None):
    """Classe chaque pixel du sujet parmi au plus n couleurs dominantes (k-means en Lab).
    Avec auto : les couleurs proches (ΔE < 14) sont fusionnées et les classes négligeables (< 1,5 %) supprimées ;
    une image « plate » (logo) est classée au plus proche, bords nets. Retourne (labels triés du plus sombre au plus
    clair, centres RGB triés)."""
    h, w = rgb.shape[:2]
    lab = cv2.cvtColor(cv2.GaussianBlur(rgb, (0, 0), max(1.0, 0.003 * max(h, w))), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab0 = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)        # non floutée : les aplats gardent leur vraie couleur
    if picks:       # couleurs choisies à la pipette : pas de k-means
        order_p = sorted(picks, key=lambda c: cv2.cvtColor(np.array([[c]], np.uint8), cv2.COLOR_RGB2LAB)[0, 0, 0])
        n = len(order_p)
        cen = cv2.cvtColor(np.array([order_p], np.uint8), cv2.COLOR_RGB2LAB).reshape(n, 3).astype(np.float32)
        d = ((lab[:, :, None, :] - cen[None, None, :, :]) ** 2).sum(-1)
        if is_flat_image(rgb):
            labels = np.argmin(d, -1).astype(np.uint8)
            labels = cv2.medianBlur(labels, 5 if max(h, w) > 600 else 3).astype(np.int32)
        else:
            prob = np.exp(-d / 400.0)
            sig = max(1.0, 0.004 * max(h, w))
            sm = np.stack([cv2.GaussianBlur(prob[:, :, k].astype(np.float32), (0, 0), sig) for k in range(n)], -1)
            labels = np.argmax(sm, -1).astype(np.int32)
        return labels, [tuple(int(v) for v in c) for c in order_p]
    src = lab0 if auto else lab
    pts = src[dom > 0]
    if len(pts) < n * 10:
        pts = src.reshape(-1, 3)
    if len(pts) > 40000:
        pts = pts[np.random.default_rng(3).choice(len(pts), 40000, replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, _, cen = cv2.kmeans(pts, n, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    cen = cen[np.argsort(cen[:, 0])]
    flat = False
    if auto:
        for _ in range(n):
            k = len(cen)
            d = np.sqrt(((pts[:, None, :] - cen[None, :, :]) ** 2).sum(-1))
            frac = np.bincount(d.argmin(1), minlength=k) / max(1, len(pts))
            changed = False
            small = [i for i in range(k) if frac[i] < 0.015]
            mix = []
            for c in range(k):
                for a in range(k):
                    for b in range(a + 1, k):
                        if c in (a, b):
                            continue
                        dab = float(np.linalg.norm(cen[a] - cen[b]))
                        if dab > 20 and float(np.linalg.norm(cen[a] - cen[c]) + np.linalg.norm(cen[c] - cen[b])) < 1.06 * dab \
                                and frac[c] < 0.12:
                            mix.append(c)
            if mix and k > 2:
                cen = np.delete(cen, min(mix, key=lambda i: frac[i]), 0)
                changed = True
            elif small and k > 2:
                cen = np.delete(cen, min(small, key=lambda i: frac[i]), 0)
                changed = True
            elif k > 2:
                best, bd = None, 14.0
                for i in range(k):
                    for j in range(i + 1, k):
                        dd = float(np.linalg.norm(cen[i] - cen[j]))
                        if dd < bd:
                            best, bd = (i, j), dd
                if best:
                    i, j = best
                    cen[i] = (cen[i] * frac[i] + cen[j] * frac[j]) / max(1e-6, frac[i] + frac[j])
                    cen = np.delete(cen, j, 0)
                    changed = True
            if not changed:
                break
        n = len(cen)
        pl = lab0[dom > 0]
        if len(pl) > 40000:
            pl = pl[np.random.default_rng(5).choice(len(pl), 40000, replace=False)]
        dmin = np.sqrt(((pl[:, None, :] - cen[None, :, :]) ** 2).sum(-1)).min(1)
        flat = float((dmin < 12.0).mean()) >= 0.85
    d = ((lab[:, :, None, :] - cen[None, None, :, :]) ** 2).sum(-1)
    if flat:
        labels = np.argmin(d, -1).astype(np.uint8)
        labels = cv2.medianBlur(labels, 5 if max(h, w) > 600 else 3).astype(np.int32)
    else:
        prob = np.exp(-d / 400.0)
        sig = max(1.0, 0.006 * max(h, w))
        sm = np.stack([cv2.GaussianBlur(prob[:, :, k].astype(np.float32), (0, 0), sig) for k in range(n)], -1)
        labels = np.argmax(sm, -1).astype(np.int32)
    rgb_c = cv2.cvtColor(np.clip(cen, 0, 255).reshape(1, n, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(n, 3)
    return labels, [tuple(int(v) for v in q) for q in rgb_c]


def layers_masks_color(rgb, p, subject, valid, dom=None):
    h, w = rgb.shape[:2]
    dom = _layer_domain(rgb, p, subject, valid) if dom is None else dom
    n = int(min(8, max(2, p.ml_layers)))
    labels, cols = color_classes(fill_outside(rgb, valid), dom, n, auto=p.ml_color_auto, picks=parse_picks(p.ml_picks))
    n = len(cols)
    try:
        order = [int(t) for t in str(p.ml_order).split(",") if t.strip() != ""]
    except ValueError:
        order = []
    if sorted(order) != list(range(n)):
        order = list(range(n))                              # du plus sombre (fond) au plus clair (devant)
        if p.ml_invert:
            order = order[::-1]
    rank = np.zeros(n, np.int32)
    for pos, cid in enumerate(order):
        rank[cid] = pos
    pr = rank[labels]
    masks = []
    for i in range(n):                                     # plaque i : pleine là où la couleur est au même niveau ou devant
        solid = (pr >= i) | (dom == 0)
        masks.append(solid.astype(np.uint8))
    colors = [cols[cid] for cid in order]
    return masks, colors, order


def layers_masks(rgb, p, subject, valid, dom=None):
    """Une plaque par couche (1 = matière), de l'arrière vers l'avant. La couche 1 est pleine ; chaque couche suivante est
    percée là où l'image est assez sombre (ou claire si ml_invert) : plus on avance vers l'avant, plus les ouvertures
    sont grandes, donc les zones sombres sont les plus profondes (effet de relief avec ombres)."""
    h, w = rgb.shape[:2]
    gray = tone_gray(fill_outside(rgb, valid), p.tone_source)
    g = cv2.GaussianBlur(gray, (0, 0), max(1.0, 0.004 * max(h, w))).astype(np.float32)
    dom = _layer_domain(rgb, p, subject, valid) if dom is None else dom
    sample = g[dom > 0] if dom.any() else g.ravel()
    n = int(min(8, max(2, p.ml_layers)))
    masks = [np.ones((h, w), np.uint8)]
    for i in range(2, n + 1):
        q = 100.0 * (i - 1) / n
        reg = (g >= np.percentile(sample, 100.0 - q)) if p.ml_invert else (g <= np.percentile(sample, q))
        masks.append((1 - (reg & (dom > 0))).astype(np.uint8))
    return masks


def _pin_points(base_sheet, ring_px, ppm, pin_mm):
    """3 points bien écartés au milieu de la bordure (présente et pleine dans toutes les couches)."""
    sh = (base_sheet > 0).astype(np.uint8)
    pad = cv2.copyMakeBorder(sh, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    dist = cv2.distanceTransform(pad, cv2.DIST_L2, 5)[1:-1, 1:-1]
    band = np.abs(dist - ring_px / 2.0) <= 1.5
    ys, xs = np.nonzero(band & (sh > 0))
    if len(xs) < 20:
        return []
    pts = np.stack([xs, ys], 1).astype(np.float32)
    p1 = pts[np.lexsort((pts[:, 0], pts[:, 1]))[0]]
    d1 = np.hypot(*(pts - p1).T)
    p2 = pts[int(np.argmax(d1))]
    d2 = np.hypot(*(pts - p2).T)
    p3 = pts[int(np.argmax(np.minimum(d1, d2)))]
    return [tuple(map(float, q)) for q in (p1, p2, p3)]


def _layer_engraving(gray, region, p, ppm):
    """Détails sombres à graver (traits du visage, yeux...) : contraste local, limités à la zone pleine de la plaque de devant."""
    h, w = gray.shape
    g = cv2.GaussianBlur(gray, (0, 0), max(1.0, 0.0015 * max(h, w)))
    block = (int(0.04 * max(h, w)) | 1)
    Cv = max(2.0, 16.0 - 0.14 * float(p.ml_eng_level))
    det = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, max(5, block), Cv) > 0
    inner = cv2.erode((region > 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    det = (det & inner).astype(np.uint8)
    det = cv2.morphologyEx(det, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(det, 8)
    keep = np.zeros(n, np.uint8)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= max(6, int((0.6 * ppm) ** 2))     # on ignore les points de moins de ~0,6 mm
    return keep[lbl]


def layers_result(rgb, p, subject=None, valid=None):
    t0 = time.time()
    h, w = rgb.shape[:2]
    colors, corder = None, None
    dom = _layer_domain(rgb, p, subject, valid)
    if (p.ml_sep == "color" and subject is None and p.ml_bg == "front"
            and (parse_picks(p.ml_picks) or is_flat_image(fill_outside(rgb, valid), valid))):
        dom = np.ones((h, w), np.uint8) if valid is None else valid.astype(np.uint8)   # logo : pas de fond à retirer
    if p.ml_sep == "color":
        masks, colors, corder = layers_masks_color(rgb, p, subject, valid, dom)
    else:
        masks = layers_masks(rgb, p, subject, valid, dom)
    front = masks[-1].copy()
    own_bg = p.ml_bg in ("own", "image")
    if own_bg:       # plaque de fond à part, pleine ; toutes les autres sont percées hors du sujet
        masks = [np.ones((h, w), np.uint8)] + [(m & (dom > 0)).astype(np.uint8) for m in masks]
        try:
            bgc = tuple(int(str(p.ml_bg_color).lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            bgc = (232, 220, 200)
        if p.ml_bg == "image":      # couleur réelle du fond de l'image (médiane hors sujet)
            out = fill_outside(rgb, valid)[dom == 0]
            if len(out) > 50:
                bgc = tuple(int(v) for v in np.median(out, axis=0))
        if colors is not None:
            colors = [bgc] + list(colors)
        else:
            colors = None
    pl = replace(p, output="stencil", keep_islands=(p.ml_sep == "color"))
    outs = [process(rgb, pl if (i == 0 or not p.ml_pieces) else replace(pl, loose=True), None, valid, raw_override=m)
            for i, m in enumerate(masks)]
    n = len(outs)
    H2, W2 = outs[0].mat.shape
    gray_eng = tone_gray(fill_outside(rgb, valid), p.tone_source) if p.ml_engrave else None
    ppm = W2 / max(outs[0].w_mm, 1e-6)
    info = {}
    if p.ml_pins:
        ring_px = effective_ring(p) * ppm
        if p.shape != "none" and ring_px >= (p.ml_pin_mm + 2.0) * ppm:
            pins = _pin_points(outs[0].base_sheet, ring_px, ppm, p.ml_pin_mm)
            rr = max(2, int(round(p.ml_pin_mm * ppm / 2)))
            k = ppm / 12.0
            for r in outs:
                for x, y in pins:
                    cv2.circle(r.mat, (int(round(x)), int(round(y))), rr, 0, -1)
                r.polys_mm = [q / ppm for q in extract_contours(r.mat, p.smooth * k, p.simplify * k)]
            info["ml_pins"] = len(pins)
        else:
            info["ml_pin_skip"] = True
    nl = sum(int(r.stats.get("loose_pieces", 0)) for r in outs)
    if nl:
        info["ml_loose"] = nl
    if colors is not None:
        info["ml_palette"] = ["#%02x%02x%02x" % q for q in (colors[1:] if own_bg else colors)]
        info["ml_order_ids"] = [int(v) for v in corder]
    cols = 1 if n == 1 else (2 if n <= 4 else 3)
    rows = int(np.ceil(n / cols))
    gap = max(2, int(round(p.ml_gap_mm * ppm)))
    TW, TH = cols * W2 + (cols - 1) * gap, rows * H2 + (rows - 1) * gap
    def mosaic(get, dtype=np.uint8, ch=None, fill=0):
        shp = (TH, TW) if ch is None else (TH, TW, ch)
        out = np.full(shp, fill, dtype)
        for i, r in enumerate(outs):
            a = get(r)
            y0, x0 = (i // cols) * (H2 + gap), (i % cols) * (W2 + gap)
            out[y0:y0 + H2, x0:x0 + W2] = a
        return out
    mat = mosaic(lambda r: r.mat)
    boxes = [((i % cols) * (W2 + gap), (i // cols) * (H2 + gap), W2, H2) for i in range(n)]
    layer_polys, allp = [], []
    for i, r in enumerate(outs):
        ox, oy = (i % cols) * (W2 + gap) / ppm, (i // cols) * (H2 + gap) / ppm
        pp = [q + np.array([ox, oy]) for q in r.polys_mm]
        layer_polys.append((f"LAYER_{i + 1}", pp))
        allp += pp
    length = sum(float(np.sum(np.hypot(*np.diff(np.vstack([q, q[:1]]), axis=0).T))) for q in allp)
    stats = dict(threshold=0.0, contours=len(allp), length_mm=length, linked=sum(r.stats.get("linked", 0) for r in outs),
                 dropped=sum(r.stats.get("dropped", 0) for r in outs), w_mm=TW / ppm, h_mm=TH / ppm, px=[TW, TH],
                 seconds=round(time.time() - t0, 2), ml_layers=n, ml_cols=cols, **info)
    for key in ("holes", "hang", "text_scaled", "text_ignored"):
        if key in outs[0].stats:
            stats[key] = outs[0].stats[key]
    marks = marks_polys = None
    if p.ml_engrave:
        em = _layer_engraving(gray_eng, front & (dom > 0), p, ppm)
        if em is not None and em.any():
            fb = boxes[-1]
            emp = np.zeros((H2, W2), np.uint8)
            hh_, ww_ = em.shape
            pad_l, pad_t = (W2 - ww_) // 2 if W2 > ww_ else 0, (H2 - hh_) // 2 if H2 > hh_ else 0
            emp[:hh_, :ww_] = em[:H2, :W2]
            if outs[-1].mat.shape != em.shape:      # languette d'œillet : tout est décalé de la marge ajoutée
                dy, dx = H2 - hh_, W2 - ww_
                emp = np.zeros((H2, W2), np.uint8)
                emp[dy:, dx:] = em if (dy >= 0 and dx >= 0) else emp[dy:, dx:]
            emp &= (outs[-1].mat > 0).astype(np.uint8)       # seulement sur la matière réellement présente de la plaque de devant
            marks = np.zeros((TH, TW), np.uint8)
            marks[fb[1]:fb[1] + H2, fb[0]:fb[0] + W2] = emp
            kk = ppm / 12.0
            marks_polys = [q / ppm for q in extract_contours(marks, 0.0, 0.3 * kk)]
            info["ml_engraved"] = len(marks_polys)
    res = Result(mosaic(lambda r: r.rgb, np.uint8, 3, 255), mosaic(lambda r: r.gray, np.uint8, None, 255), None,
                 mosaic(lambda r: r.mat0), mat, mosaic(lambda r: r.bridges), allp, TW / ppm, TH / ppm, stats,
                 mosaic(lambda r: r.sheet), base_sheet=mosaic(lambda r: r.base_sheet),
                 layers=[r.mat for r in outs], layer_polys=layer_polys, layer_colors=colors, layer_boxes=boxes,
                 marks=marks, marks_polys=marks_polys)
    res.stats.update({k: v for k, v in info.items() if k == "ml_engraved"})
    return res


def render_layer_stack(res, material="wood_light"):
    """Aperçu des couches empilées (la 1re derrière) avec ombres portées : donne une idée du relief."""
    mats = res.layers
    n = len(mats)
    H, W = mats[0].shape
    base = np.array(MATERIALS.get(material, MATERIALS["wood_light"])[0], np.float32)
    out = np.full((H, W, 3), (226, 226, 230), np.float32)
    cols = res.layer_colors
    s = max(2, int(0.006 * max(H, W)))
    for i, m in enumerate(mats):
        mf = m.astype(np.float32)
        sh = cv2.GaussianBlur(np.roll(np.roll(mf, s, 0), s, 1), (0, 0), max(1.0, 0.004 * max(H, W)))
        out *= (1.0 - 0.5 * sh)[..., None]
        if cols:
            col = np.array(cols[i], np.float32)
        else:
            col = np.clip(base * (0.6 + 0.4 * (i / max(1, n - 1))), 0, 255)
        out[m > 0] = col
        edge = (m > 0) & (cv2.erode(m, np.ones((3, 3), np.uint8)) == 0)
        out[edge] = np.clip(col * 1.25 + 8, 0, 255)
        if i == n - 1 and res.marks is not None and res.layer_boxes:
            x0, y0, tw, th = res.layer_boxes[-1]
            mk = res.marks[y0:y0 + th, x0:x0 + tw] > 0
            out[mk] = out[mk] * 0.28
    return out.astype(np.uint8)


def process(rgb, p, subject=None, valid=None, manual=None, guides=None, raw_override=None):
    if p.output == "layers" and raw_override is None:
        return layers_result(rgb, p, subject, valid)
    if p.output in ("halftone", "lines"):
        return halftone(rgb, p, subject, valid)
    if p.output == "engrave":
        return engrave_result(rgb, p, subject, valid)
    t0 = time.time()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    ppm = max(h, w) / p.size_mm
    if subject is not None and subject.shape != gray.shape:
        subject = cv2.resize(subject, (w, h), interpolation=cv2.INTER_NEAREST)
    roi = valid if subject is None else (subject if valid is None else (subject & valid))
    if roi is not None and not roi.any():
        roi = None
    lp_info = {}
    marks = None
    qr_geo = None
    if p.output == "qr":
        p = replace(p, min_feature_mm=min(p.min_feature_mm, 0.3), min_island_mm2=0.0, keep_thin=True, outline_mm=0.0,
                    grow_mm=0.0, smooth=0.0, simplify=min(p.simplify, 0.3), bridge_mm=p.qr_bridge_mm,
                    max_bridge_mm=max(p.max_bridge_mm, 20.0))
        subject = roi = None
        try:
            raw, marks, lp_info, qr_geo = qr_masks(h, w, p, ppm)
        except ValueError as e:
            raw, marks, qr_geo = np.ones((h, w), np.uint8), None, None
            lp_info = {"qr_error": str(e)}
        thr = 0.0
    elif raw_override is not None:
        raw, thr = raw_override.astype(np.uint8), 0.0
    elif p.output == "lowpoly":
        if subject is None and p.lp_auto:
            filled = fill_outside(rgb, valid)
            auto = ai_mask(filled, valid) if p.ai_subject else None
            if auto is None:
                auto = auto_subject(filled, valid)
            if auto is not None:
                subject = auto
                roi = auto if valid is None else (auto & valid)
        dom = np.ones((h, w), np.uint8) if roi is None else roi.astype(np.uint8)
        if p.shape != "none":
            dom = dom & shape_inside(p.shape, h, w)
        raw, npt, ntri = lowpoly_mask(fill_outside(rgb, valid), p, dom, ppm, guides)
        thr = 0.0
        lp_info = {"lp_vertices": npt, "lp_triangles": ntri}
    else:
        raw, thr = tone_mask(tone_gray(fill_outside(rgb, valid), p.tone_source), p, roi)
    if valid is not None:
        raw = raw & valid
    if subject is not None:
        raw = raw & subject
        if p.outline_mm > 0 and p.output != "lowpoly":  # contour plein : la silhouette reste lisible même si le sujet est clair
            k = max(1, int(round(p.outline_mm * ppm)))
            inner = cv2.erode(subject, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
            raw = raw | (subject & (1 - inner))
    if abs(p.grow_mm) >= 0.05:  # épaissit / amincit tous les traits
        r = max(1, int(round(abs(p.grow_mm) * ppm / 2)))
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        raw = cv2.dilate(raw, ker) if p.grow_mm > 0 else cv2.erode(raw, ker)
    mat0 = clean_mask(raw, ppm, p.min_feature_mm, p.keep_thin)
    ring_mm = effective_ring(p)
    mat1, anchor = apply_shape(mat0, p.shape, ring_mm, ppm)
    mat1, pad, tab, dinfo = decorate(mat1, shape_inside(p.shape, h, w), p, ppm, ring_mm)
    sheet = _sheet_mask(p.shape, h, w)
    if any(pad):  # l'œillet dépasse du cadre : tout est agrandi de la même marge
        rgb, gray = _pad_img(rgb, pad, (255, 255, 255)), _pad_img(gray, pad, 255)
        mat0, sheet = _pad_img(mat0, pad), _pad_img(sheet, pad)
        if marks is not None:
            marks = _pad_img(marks, pad)
        if qr_geo is not None:
            qr_geo = dict(qr_geo, x0=qr_geo["x0"] + pad[0], y0=qr_geo["y0"] + pad[1])
        if subject is not None:
            subject = _pad_img(subject, pad)
        if anchor is not None:
            anchor = (anchor[0] + pad[0], anchor[1] + pad[1])
    base_sheet = sheet.copy()      # forme seule, sans la languette de l'œillet (pour le caisson)
    if tab is not None:
        sheet = sheet | tab
    if p.loose:
        mat, bridges, linked, dropped = mat1.copy(), np.zeros_like(mat1), 0, 0
    else:
        mat, bridges, linked, dropped = add_bridges(mat1.copy(), anchor, p.bridge_mm, ppm,
                                                    p.min_island_mm2, p.max_bridge_mm)
        if p.keep_islands:
            ncomp, lab_i, st_i, _ = cv2.connectedComponentsWithStats((mat1 > 0).astype(np.uint8), connectivity=8)
            miss = np.zeros(mat.shape, np.uint8)
            nloose = 0
            for ci in range(1, ncomp):
                if st_i[ci, cv2.CC_STAT_AREA] >= 0.5 * ppm * ppm:
                    comp = lab_i == ci
                    if not (mat[comp] > 0).any():
                        miss[comp] = 1
                        nloose += 1
            mat = mat | miss
            lp_info["loose_pieces"] = nloose
            dropped = 0
    if manual:      # ponts posés à la main : segments (x1, y1, x2, y2) en fractions du résultat
        mh, mw = mat.shape
        th = max(2, int(round(p.bridge_mm * ppm)))
        extra = np.zeros_like(mat)
        for seg in manual[:400]:
            try:
                x1, y1, x2, y2 = (float(v) for v in seg)
            except (TypeError, ValueError):
                continue
            cv2.line(extra, (int(round(x1 * (mw - 1))), int(round(y1 * (mh - 1)))),
                     (int(round(x2 * (mw - 1))), int(round(y2 * (mh - 1)))), 1, th)
        mat = mat | extra
        bridges = bridges | extra
    k = ppm / 12.0
    polys = extract_contours(mat, p.smooth * k, p.simplify * k)
    polys_mm = [q / ppm for q in polys]
    length = sum(float(np.sum(np.hypot(*np.diff(np.vstack([q, q[:1]]), axis=0).T))) for q in polys_mm)
    H2, W2 = mat.shape
    marks_polys = None
    if marks is not None:
        marks_polys = [q / ppm for q in extract_contours(marks, 0.0, 0.3 * k)]
    if qr_geo is not None:
        try:
            if p.qr_mode == "cut":      # noir = ce qui paraît sombre : matière (ou trous si polarité inversée)
                dark = (1 - mat) if p.qr_invert else mat
            else:                       # gravure : zones gravées sombres (ou la plaque non gravée si inversé)
                dark = (1 - marks) if p.qr_invert else marks
            lp_info["qr_scan"] = qr_scan_check(dark, qr_geo)
        except Exception:
            lp_info["qr_scan"] = "fail"
    holes = [(x / ppm, y / ppm, r / ppm) for x, y, r in dinfo.pop("hang_holes", [])]
    stats = dict(threshold=thr, contours=len(polys_mm), length_mm=length, linked=linked,
                 dropped=dropped, w_mm=W2 / ppm, h_mm=H2 / ppm, px=[W2, H2],
                 seconds=round(time.time() - t0, 2), **dinfo, **lp_info)
    return Result(rgb, gray, subject, mat0, mat, bridges, polys_mm, W2 / ppm, H2 / ppm, stats, sheet,
                  tab=tab, hang_holes=holes, base_sheet=base_sheet, marks=marks, marks_polys=marks_polys)


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
            from . import lightbox
        except ImportError:
            import lightbox
        st = style or {}
        return lightbox.render_box(res, st.get("params") or Params(), lang=st.get("lang"))
    if view == "assembled":
        try:
            from . import lightbox
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


# --------------------------------------------------------------------------
# Exports (texte)
# --------------------------------------------------------------------------
def polys_bbox(polys):
    """Rectangle englobant (x0, y0, x1, y1) d'une liste de polylignes, ou None."""
    pts = [np.asarray(q, float).reshape(-1, 2) for q in polys if len(q)]
    if not pts:
        return None
    a = np.vstack(pts)
    return (float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max()))


def svg_string(polys_mm, w_mm, h_mm, frame=None, marks=None, layers=None, colors=None):
    if layers:       # multicouche : une couleur par couche (LSP crée un calque par couleur)
        return _layers_svg(layers, w_mm, h_mm, frame, colors, marks)
    parts = []
    for q in polys_mm:
        d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + " Z"
        parts.append(f'<path d="{d}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_mm:.3f}mm" height="{h_mm:.3f}mm" '
            f'viewBox="0 0 {w_mm:.3f} {h_mm:.3f}">\n'
            f'<g id="CUT" fill="none" stroke="#ff0000" stroke-width="0.1">\n'
            + "\n".join(parts) + "\n</g>\n"
            + _marks_svg(marks)
            + (frame_svg(frame) if frame else "") + "</svg>\n")


def _layers_svg(layers, w_mm, h_mm, frame=None, colors=None, marks=None):
    gs = []
    for i, (name, polys) in enumerate(layers):
        d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + " Z" for q in polys)
        gs.append(f'<g id="{name}" fill="none" stroke="{("#%02x%02x%02x" % tuple(colors[i])) if colors else LAYER_COLORS[i % len(LAYER_COLORS)]}" stroke-width="0.1"><path d="{d}"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_mm:.3f}mm" height="{h_mm:.3f}mm" '
            f'viewBox="0 0 {w_mm:.3f} {h_mm:.3f}">\n' + "\n".join(gs) + "\n" + _marks_svg(marks) + (frame_svg(frame) if frame else "") + "</svg>\n")


def _marks_svg(marks):
    """Calque ENGRAVE (zones gravées pleines) : QR code gravé."""
    if not marks:
        return ""
    d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + " Z" for q in marks)
    return f'<g id="ENGRAVE" fill="#000000" stroke="none" fill-rule="evenodd"><path d="{d}"/></g>\n'


def frame_svg(frame):
    x0, y0, x1, y1 = frame
    return (f'<g id="FRAME" fill="none" stroke="#00aa00" stroke-width="0.1">'
            f'<path d="M{x0:.3f},{y0:.3f} L{x1:.3f},{y0:.3f} L{x1:.3f},{y1:.3f} L{x0:.3f},{y1:.3f} Z"/></g>\n')


def frame_dxf_lines(frame, h_mm):
    """Entités DXF du rectangle de cadrage (calque FRAME), axe Y vers le haut."""
    x0, y0, x1, y1 = frame
    L = ["0", "POLYLINE", "8", "FRAME", "66", "1", "70", "1"]
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        L += ["0", "VERTEX", "8", "FRAME", "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
    return L + ["0", "SEQEND", "8", "FRAME"]


def dxf_string(polys_mm, h_mm, layer="CUT", frame=None, marks=None, layers=None):
    """DXF R12 minimal (POLYLINE fermées), axe Y vers le haut, en mm. layers : [(nom, contours)] pour le multicouche."""
    L = ["0", "SECTION", "2", "ENTITIES"]
    if layers:
        for name, polys in layers:
            for q in polys:
                L += ["0", "POLYLINE", "8", name, "66", "1", "70", "1"]
                for x, y in q:
                    L += ["0", "VERTEX", "8", name, "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
                L += ["0", "SEQEND", "8", name]
        polys_mm = []
    for q in polys_mm:
        L += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
        for x, y in q:
            L += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
        L += ["0", "SEQEND", "8", layer]
    for q in (marks or []):
        L += ["0", "POLYLINE", "8", "ENGRAVE", "66", "1", "70", "1"]
        for x, y in q:
            L += ["0", "VERTEX", "8", "ENGRAVE", "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
        L += ["0", "SEQEND", "8", "ENGRAVE"]
    if frame:
        L += frame_dxf_lines(frame, h_mm)
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"
