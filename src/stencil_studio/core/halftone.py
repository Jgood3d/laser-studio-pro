"""Trame de points : plaque percée de trous dont la taille suit la clarté.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import time
import cv2
import numpy as np

from .params import Result
from .framing import fill_outside
from .tones import tone_gray
from .plate import GENERIC_SHAPES, _pad_img, decorate, effective_ring, extract_contours, shape_inside
from .render import _sheet_mask


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
