"""Sujet de la photo : détourage GrabCut, réseau de neurones (subject_ai), visage, choix automatique.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np

from .params import REF_SIZE
from .tones import otsu_value


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


def ai_mask(rgb, valid=None):
    """Masque du sujet par IA (subject_ai), ou None si indisponible."""
    try:
        try:
            from .. import subject_ai
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
