"""Tons -> matière : seuil d'Otsu, gris de travail, masque des tons, nettoyage des petits détails.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np

from .params import REF_SIZE


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


def _keep_strokes(thin, opened, d):
    """Parmi les morceaux de matière plus étroits que d (px), garde ceux qui sont de vrais traits :
    - assez grands (surface >= 2 d²), ou
    - longs (plus de 2,5 d), ou
    - qui relient au moins deux zones épaisses (le jambage fin entre deux boucles d'une écriture).
    Les petites bosses qui bordent une forme épaisse (touchent une seule zone, courtes) sont supprimées.
    Avant : seule la surface comptait, donc un trait fin et sinueux était coupé en points."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(thin, connectivity=8)
    if n <= 1:
        return thin
    on, olab = cv2.connectedComponents(opened, connectivity=8)
    H, W = thin.shape
    keep = np.zeros(n, np.uint8)
    big = max(4, 2 * d * d)
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in st[i])
        if area >= big or max(w, h) >= 2.5 * d:
            keep[i] = 1
            continue
        x0, y0, x1, y1 = max(0, x - 2), max(0, y - 2), min(W, x + w + 2), min(H, y + h + 2)
        comp = (lab[y0:y1, x0:x1] == i).astype(np.uint8)
        ring = cv2.dilate(comp, np.ones((3, 3), np.uint8)) > 0
        touched = np.unique(olab[y0:y1, x0:x1][ring & (opened[y0:y1, x0:x1] > 0)])
        if len(touched[touched > 0]) >= 2:
            keep[i] = 1
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
        thin = _keep_strokes(thin, opened, d)         # on garde les traits (même fins et longs), pas les petits bords
        r = max(1, d // 3)
        thick = cv2.dilate(thin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        mat = opened | thick
    else:
        mat = opened
    area = max(4, int(0.5 * d * d))
    mat = _remove_small(mat, area)
    return 1 - _remove_small(1 - mat, area)
