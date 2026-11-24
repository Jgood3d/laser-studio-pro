"""Pochoir multicouche : une plaque par couleur, picots de calage, gravure de chaque couche.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np

from .framing import fill_outside
from .subject import ai_mask, auto_subject
from .tones import tone_gray
from .colors import color_classes


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
    """'#rrggbb,#rrggbb' -> liste de tuples RGB (0 à 8 couleurs), sans doublons proches en Lab."""
    out = []
    for t in str(txt or "").split(","):
        t = t.strip().lstrip("#")
        if len(t) == 6:
            try:
                out.append(tuple(int(t[i:i + 2], 16) for i in (0, 2, 4)))
            except ValueError:
                pass
    if len(out) <= 1:
        return out[:8]
    # dédoublonne les pipettes trop proches (même aplat cliqué deux fois / AA)
    lab = cv2.cvtColor(np.array([out], np.uint8), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    keep = []
    for i, c in enumerate(out):
        if any(float(np.linalg.norm(lab[i] - lab[j])) < 10.0 for j in keep):
            continue
        keep.append(i)
    return [out[i] for i in keep][:8]


def layers_masks_color(rgb, p, subject, valid, dom=None, meta=None):
    h, w = rgb.shape[:2]
    dom = _layer_domain(rgb, p, subject, valid) if dom is None else dom
    n = int(min(8, max(2, p.ml_layers)))
    labels, cols = color_classes(fill_outside(rgb, valid), dom, n, auto=p.ml_color_auto, picks=parse_picks(p.ml_picks), meta=meta)
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
