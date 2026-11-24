"""Low poly : maillage de triangles (poutres et facettes pleines) à partir de la photo.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np

from .tones import otsu_value


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
