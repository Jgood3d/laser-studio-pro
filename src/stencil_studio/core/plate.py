"""Plaque : formes, texte dans l'anneau, œillet, ponts qui retiennent les îlots, contours vectoriels.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import os
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


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
        os.path.join(base, "resources", "fonts", "DejaVuSans-Bold.ttf"),
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
