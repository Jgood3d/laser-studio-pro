"""Conversion d'une image en niveaux de gris pour la gravure laser (tramage à la résolution de la machine).

Fonctions pures numpy/OpenCV. Le tramage par diffusion d'erreur est calculé « par fronts d'onde »
(les pixels indépendants d'une même diagonale sont traités ensemble) : rapide sans compilateur.
"""
import numpy as np

# (dy, dx, poids), diviseur
KERNELS = {
    "floyd":    ([(0, 1, 7), (1, -1, 3), (1, 0, 5), (1, 1, 1)], 16),
    "jarvis":   ([(0, 1, 7), (0, 2, 5), (1, -2, 3), (1, -1, 5), (1, 0, 7), (1, 1, 5), (1, 2, 3),
                  (2, -2, 1), (2, -1, 3), (2, 0, 5), (2, 1, 3), (2, 2, 1)], 48),
    "stucki":   ([(0, 1, 8), (0, 2, 4), (1, -2, 2), (1, -1, 4), (1, 0, 8), (1, 1, 4), (1, 2, 2),
                  (2, -2, 1), (2, -1, 2), (2, 0, 4), (2, 1, 2), (2, 2, 1)], 42),
    "burkes":   ([(0, 1, 8), (0, 2, 4), (1, -2, 2), (1, -1, 4), (1, 0, 8), (1, 1, 4), (1, 2, 2)], 32),
    "sierra":   ([(0, 1, 5), (0, 2, 3), (1, -2, 2), (1, -1, 4), (1, 0, 5), (1, 1, 4), (1, 2, 2),
                  (2, -1, 2), (2, 0, 3), (2, 1, 2)], 32),
    "atkinson": ([(0, 1, 1), (0, 2, 1), (1, -1, 1), (1, 0, 1), (1, 1, 1), (2, 0, 1)], 8),
}
DITHERS = ["stucki", "floyd", "atkinson", "jarvis", "burkes", "sierra", "bayer", "threshold"]

_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32)


def _quant(v, levels):
    """Valeur 0..255 -> niveau le plus proche parmi `levels` niveaux (2 = noir / blanc)."""
    step = 255.0 / (levels - 1)
    return np.clip(np.round(v / step), 0, levels - 1) * step


def diffuse(gray, kernel, levels=2):
    """Diffusion d'erreur par fronts d'onde. gray : float 0..255. Retourne uint8 (valeurs quantifiées)."""
    taps, div = KERNELS[kernel]
    H, W = gray.shape
    m = 1
    for dy, dx, _ in taps:                 # pente du front : toute erreur part vers un front ultérieur
        if dy > 0 and dx < 0:
            m = max(m, -(-(-dx + 1) // dy))
    PX = 2
    buf = np.zeros((H + 3, W + 2 * PX), np.float32)
    buf[:H, PX:PX + W] = gray
    out = np.zeros((H, W), np.uint8)
    wts = [(dy, dx, w / float(div)) for dy, dx, w in taps]
    for t in range(0, (W - 1) + m * (H - 1) + 1):
        y0 = max(0, -(-(t - (W - 1)) // m))
        y1 = min(H - 1, t // m)
        if y1 < y0:
            continue
        ys = np.arange(y0, y1 + 1)
        xs = t - m * ys
        v = buf[ys, xs + PX]
        q = _quant(v, levels)
        out[ys, xs] = q
        e = v - q
        for dy, dx, w in wts:
            buf[ys + dy, xs + dx + PX] += e * w
    return out


def dither(gray, method="stucki", levels=2):
    """gray : array 2D 0..255 (0 = noir = brûlé). Retourne uint8 : valeurs parmi `levels` niveaux."""
    g = np.clip(gray.astype(np.float32), 0, 255)
    levels = int(max(2, min(16, levels)))
    if method == "threshold":
        return _quant(g, levels).astype(np.uint8)
    if method == "bayer":
        H, W = g.shape
        th = (_BAYER4[np.arange(H)[:, None] % 4, np.arange(W)[None, :] % 4] + 0.5) / 16.0 - 0.5
        step = 255.0 / (levels - 1)
        return _quant(g + th * step, levels).astype(np.uint8)
    return diffuse(g, method if method in KERNELS else "stucki", levels)


def prepare_gray(g, brightness=0.0, contrast=0.0, gamma=1.0):
    """Réglages de ton : luminosité (-100..100), contraste (-90..90), gamma (>1 = plus clair)."""
    x = g.astype(np.float32)
    c = float(np.clip(contrast, -90, 90))
    f = (100.0 + c) / (100.0 - c)
    x = (x - 128.0) * f + 128.0 + float(brightness) * 2.55
    x = np.clip(x, 0, 255) / 255.0
    x = x ** (1.0 / max(0.1, float(gamma)))
    return np.clip(x * 255.0, 0, 255)


def estimate_minutes(h_mm, w_mm, dpi, speed_mm_min):
    """Durée approximative de gravure ligne à ligne (sans accélérations ni zones blanches sautées)."""
    rows = h_mm / 25.4 * dpi
    return rows * (w_mm + 6.0) / max(100.0, float(speed_mm_min))
