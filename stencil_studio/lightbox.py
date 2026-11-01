"""Caisson lumineux (boîte à LED) pour une plaque de façade : fichiers de découpe par couches.

Principe (fonctionne avec n'importe quelle forme : cercle, cœur, étoile...) :
  façade (votre plaque) + diffuseur + N cadres collés (parois) + fond démontable vissé.
Les cadres ont la même silhouette que la façade, évidée à l'intérieur ; la bande LED se colle sur les parois.
"""
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

try:
    from . import core
except ImportError:
    import core


def _center_hole(body, ppm, p):
    """Trou rond au centre du fond (centre de la boîte englobante de la forme), diamètre box_center_mm."""
    d = float(getattr(p, "box_center_mm", 0.0))
    if d <= 0.0 or not body.any():
        return []
    ys, xs = np.nonzero(body)
    return [_circle((xs.min() + xs.max() + 1) / 2.0 / ppm, (ys.min() + ys.max() + 1) / 2.0 / ppm, d / 2.0)]


def _circle(x, y, r, n=48):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([x + r * np.cos(t), y + r * np.sin(t)], 1)


def _polys(mask, ppm, p):
    k = ppm / 12.0
    return [q / ppm for q in core.extract_contours(mask.astype(np.uint8), p.smooth * k, p.simplify * k)]


def _bbox(polys):
    a = np.vstack(polys)
    return a.min(0), a.max(0)


def _screw_points(body, ppm, wall_mm, n):
    """n points régulièrement répartis au milieu de la paroi (jamais en haut au centre, où se trouve l'œillet)."""
    if n <= 0:
        return []
    path = core._ring_path(body, wall_mm * ppm, clockwise=True)
    if path is None:
        return []
    cl = np.vstack([path, path[:1]])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(cl, axis=0).T))])
    L = float(s[-1])
    s0 = float(s[int(np.argmin(path[:, 1]))]) + L / (2.0 * n)
    pts = []
    for i in range(n):
        q = (s0 + i * L / n) % L
        pts.append((float(np.interp(q, s, cl[:, 0])) / ppm, float(np.interp(q, s, cl[:, 1])) / ppm))
    return pts


def _body_mask(res, sheet):
    """Corps du caisson : la forme seule, sans la languette d'accroche (le tracé de la paroi, du diffuseur et
    des fentes reste le même qu'il y ait un œillet ou non)."""
    bs = getattr(res, "base_sheet", None)
    if bs is not None and bs.shape == sheet.shape:
        return (bs > 0).astype(np.uint8)
    tab = (res.tab > 0) if res.tab is not None else np.zeros(sheet.shape, bool)
    return ((sheet > 0) & ~tab).astype(np.uint8)


def _rrect(w, h, r, n=8):
    """Rectangle à coins arrondis centré sur l'origine (polygone fermé, mm)."""
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for a in np.radians(np.linspace(a0, a0 + 90, n)):
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    return np.array(pts, float)


def _keyhole(cx, y_low, head, shank, travel, n=36):
    """Trou de serrure : grand cercle (tête de vis) en bas, fente étroite (tige) qui monte de `travel` mm."""
    r, s = head / 2.0, min(shank / 2.0, head / 2.0 - 0.3)
    th0 = np.arcsin(s / r)
    phi = np.linspace(th0, 2 * np.pi - th0, n)
    circ = [(cx + r * np.sin(f), y_low - r * np.cos(f)) for f in phi]          # y vers le bas : le haut est -y
    y_join = y_low - r * np.cos(th0)
    y_top = y_join - travel
    top = [(cx - s * np.cos(a), y_top - s * np.sin(a)) for a in np.linspace(0, np.pi, 12)]
    top = [(cx - s * np.cos(a), y_top - s * np.sin(a)) for a in np.linspace(0, np.pi, 12)]
    return np.array(circ + [(cx - s, y_join)] + top + [(cx + s, y_join)], float)


def _support(body, ppm, p, depth_total, edge_mm, thick):
    """Supports du caisson : trous de serrure dans le fond (fixation murale) et pied (base + couches à rainure).
    body : masque du corps (px) ; retourne (trous du fond en mm, pièces supplémentaires, notes)."""
    mode = getattr(p, "box_support", "none")
    holes, extra, notes = [], [], []
    if mode == "none" or not body.any():
        return holes, extra, notes
    ys, xs = np.nonzero(body)
    x0, x1, y0, y1 = xs.min() / ppm, xs.max() / ppm, ys.min() / ppm, ys.max() / ppm
    bw, bh = x1 - x0, y1 - y0
    if mode in ("wall", "both"):
        head, shank = max(4.0, float(p.box_key_head)), max(2.0, float(p.box_key_shank))
        travel = max(4.0, head * 0.9)
        pad = cv2.copyMakeBorder(body, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        dist = cv2.distanceTransform(pad, cv2.DIST_L2, 5)[1:-1, 1:-1] / ppm

        def ok(x, y):
            xi, yi = int(round(x * ppm)), int(round(y * ppm))
            return 0 <= yi < dist.shape[0] and 0 <= xi < dist.shape[1] and dist[yi, xi] >= edge_mm + head / 2.0
        cx = (x0 + x1) / 2.0
        placed = False
        for fy in np.linspace(0.18, 0.70, 14):
            y_low = y0 + fy * bh + travel
            for sp in (min(max(0.45 * bw, 30.0), 120.0) * f for f in (1.0, 0.85, 0.7, 0.55, 0.4)):
                pos = (cx - sp / 2.0, cx + sp / 2.0)
                if all(ok(x, y_low) and ok(x, y_low - travel - head / 2.0) for x in pos):
                    holes = [_keyhole(x, y_low, head + 0.5, shank + 0.4, travel) for x in pos]
                    placed = True
                    break
            if placed:
                break
        if not placed:
            notes.append("key_no_room")
    if mode in ("foot", "both"):
        n = max(1, int(np.ceil(max(4.0, float(p.box_foot_h)) / thick)))
        pocket = n * thick
        rows = np.nonzero(body.any(axis=1))[0]
        band = body[max(0, int(rows.max() - pocket * ppm)):rows.max() + 1]
        bx = np.nonzero(band.any(axis=0))[0]
        slot_l = (bx.max() - bx.min()) / ppm + 1.0
        slot_w = depth_total + 0.3 + max(0.0, float(p.box_fit_mm))
        arm = 15.0
        fw, fd = max(slot_l + 2 * arm, 60.0), slot_w + 2 * arm
        outline = _rrect(fw, fd, 4.0)
        slot = _rrect(slot_l, slot_w, 1.0)
        extra.append(dict(name="foot_base", qty=1, polys=[outline.copy()]))
        extra.append(dict(name="foot_slot", qty=n, polys=[outline.copy(), slot.copy()]))
        if mode == "foot" and p.shape == "none":
            notes.append("foot_shape")
    return holes, extra, notes


def _make_box_stack(res, p):
    """Caisson par couches collées. Retourne un dict : parts, layout, sheet (mm), notes."""
    H, W = res.mat.shape
    ppm = W / res.w_mm
    sheet = (res.sheet > 0).astype(np.uint8)
    body = _body_mask(res, sheet)
    wall, thick = float(p.box_wall_mm), max(0.5, float(p.box_thickness_mm))
    n_frames = max(1, int(np.ceil(float(p.box_depth_mm) / thick)))
    notes = []
    if p.box_depth_mm < 15:
        notes.append("depth_low")
    scr_d = float(p.box_screw_mm)
    if p.box_screws > 0 and wall < scr_d + 5:
        notes.append("wall_thin")

    outer = _polys(sheet, ppm, p)
    hang = [_circle(x, y, r) for x, y, r in (res.hang_holes or [])]
    pad = cv2.copyMakeBorder(body, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    dist = cv2.distanceTransform(pad, cv2.DIST_L2, 5)[1:-1, 1:-1]
    opening = (dist >= wall * ppm).astype(np.uint8)
    if not opening.any():
        notes.append("wall_too_wide")
        opening_polys = []
    else:
        opening_polys = _polys(opening, ppm, p)
    screws = _screw_points(body, ppm, wall, int(p.box_screws))
    hh = res.hang_holes or []
    screws = [(x, y) for x, y in screws if all(np.hypot(x - hx, y - hy) > hr + 8.0 for hx, hy, hr in hh)]  # loin de l'œillet
    pilot = [_circle(x, y, 0.4 * scr_d) for x, y in screws]       # avant-trou (vis à bois)
    clear = [_circle(x, y, 0.55 * scr_d) for x, y in screws]      # passage dans le fond
    cable = []
    if p.box_cable_mm > 0 and opening.any():
        ys, xs = np.nonzero(opening)
        cx = float(xs.mean())
        col = np.nonzero(opening[:, int(round(cx))])[0]
        yb = float(col.max()) if len(col) else float(ys.max())
        cable = [_circle(cx / ppm, yb / ppm - p.box_cable_mm / 2.0 - 2.0, p.box_cable_mm / 2.0)]

    k_pilot = min(n_frames, int(np.ceil(8.0 / thick))) if screws else 0
    parts = [dict(name="front", qty=1, polys=[q.copy() for q in res.polys_mm])]
    if p.box_diffuser:
        parts.append(dict(name="diffuser", qty=1, polys=_polys(body, ppm, p)))
    if k_pilot:
        parts.append(dict(name="frame_pilot", qty=k_pilot, polys=outer + opening_polys + hang + pilot))
    if n_frames - k_pilot:
        parts.append(dict(name="frame", qty=n_frames - k_pilot, polys=outer + opening_polys + hang))
    depth_total = (1 + (1 if p.box_diffuser else 0) + n_frames + 1) * thick
    key_holes, foot_parts, sup_notes = _support(body, ppm, p, depth_total, wall + 2.0, thick)
    notes += sup_notes
    parts.append(dict(name="back", qty=1, polys=outer + hang + clear + cable + _center_hole(body, ppm, p) + key_holes))
    parts += foot_parts
    for pt in parts:
        lo, hi = _bbox(pt["polys"])
        pt["polys"] = [q - lo for q in pt["polys"]]
        pt["w"], pt["h"] = float(hi[0] - lo[0]), float(hi[1] - lo[1])

    # mise en page en étagères sur une plaque de largeur box_sheet_w
    gap = max(1.0, float(p.box_gap_mm))
    sw = max(60.0, float(p.box_sheet_w))
    inst = [pt for pt in parts for _ in range(pt["qty"])]
    inst.sort(key=lambda a: -a["h"])
    x = y = rowh = 0.0
    maxw = 0.0
    layout = []
    for it in inst:
        if x > 0 and x + it["w"] > sw:
            x, y, rowh = 0.0, y + rowh + gap + 4.0, 0.0
        layout.append(dict(name=it["name"], x=x, y=y + 4.0, w=it["w"], h=it["h"],
                           polys=[q + np.array([x, y + 4.0]) for q in it["polys"]]))
        x += it["w"] + gap
        rowh = max(rowh, it["h"])
        maxw = max(maxw, x - gap)
    total_h = y + rowh + 4.0
    if maxw > sw:
        notes.append("sheet_too_small")
    return dict(parts=parts, layout=layout, sheet=(max(maxw, 1.0), total_h), notes=notes, frames=n_frames,
                pilot=k_pilot, depth_total=depth_total, screws=len(screws))


# --------------------------------------------------------------------------
# Caisson « boîte » : parois à encoches (assemblage à doigts), matériau flexible sur les courbes
# --------------------------------------------------------------------------
SLIT_MARGIN = 2.0     # fentes de flexion : distance au bord haut / bas de la paroi
SLIT_ROW_MIN = 10.0   # longueur mini d'une fente


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def _resample(poly, step=0.5):
    q = np.vstack([poly, poly[:1]])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(q, axis=0).T))])
    n = max(32, int(s[-1] / step))
    u = np.linspace(0, s[-1], n, endpoint=False)
    pts = np.stack([np.interp(u, s, q[:, 0]), np.interp(u, s, q[:, 1])], 1)
    x, y = pts[:, 0], pts[:, 1]
    if 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) < 0:   # sens horaire à l'écran
        pts = pts[::-1].copy()
    return pts, float(s[-1]) / n


def _analyse(pts, step):
    """Direction, courbure et angles vifs le long de la ligne médiane."""
    n = len(pts)
    sg = max(1.0, 1.2 / step)
    ps = np.stack([ndi.gaussian_filter1d(pts[:, i], sg, mode="wrap") for i in (0, 1)], 1)
    t = np.roll(ps, -1, axis=0) - np.roll(ps, 1, axis=0)
    th = np.arctan2(t[:, 1], t[:, 0])
    w2, w5 = max(1, int(round(2.0 / step))), max(2, int(round(5.0 / step)))
    kappa = np.abs(_wrap(np.roll(th, -w2) - np.roll(th, w2))) / (2 * w2 * step)
    turn5 = np.abs(_wrap(np.roll(th, -w5) - np.roll(th, w5)))
    corners = []
    for i in np.argsort(-turn5):
        if turn5[i] < np.radians(60):
            break
        if all(min(abs(i - c), n - abs(i - c)) * step > 8.0 for c, _ in corners):
            corners.append((int(i), float(np.degrees(turn5[i]))))
    return th, kappa, sorted(corners)


def _offset_poly(pts, step, i0, i1, half):
    """Bande (polygone fermé) de demi-largeur `half` autour de la ligne médiane entre les indices i0 et i1."""
    n = len(pts)
    idx = [(i0 + k) % n for k in range(0, (i1 - i0) % n + 1)] if i1 >= i0 else [(i0 + k) % n for k in range((i1 - i0) % n + 1)]
    P = pts[idx]
    T = np.roll(pts, -1, axis=0)[idx] - np.roll(pts, 1, axis=0)[idx]
    T = T / np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-9)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    return np.vstack([P + N * half, (P - N * half)[::-1]])


def _flex_slits(flex_ivs, Lp, H, m, pitch, slit, bridge, ext_fn=None):
    """Lignes de coupe de la paroi flexible à boucles (voir _wall_piece). m : marge à chaque bout sans fentes ;
    ext_fn(x) : prolongement de la fente de bord au-delà du bord haut / bas (languette)."""
    out = []
    slit = min(slit, H * 0.3)                       # garde-fous : valeurs enregistrées avec une ancienne signification
    bridge = min(bridge, H * 0.5)
    e_len = max(1.0, (H - bridge) / 2.0)
    for xa, xb in flex_ivs:
        k = 0
        x = xa + pitch
        while x < xb:
            if m < x < Lp - m:
                if k % 2 == 0:
                    ext = ext_fn(x) if ext_fn else 0.0
                    out.append(np.array([[x, -ext], [x, e_len]], float))
                    out.append(np.array([[x, H - e_len], [x, H + ext]], float))
                elif H - 2 * slit > 3.0:
                    out.append(np.array([[x, slit], [x, H - slit]], float))
            x += pitch
            k += 1
    return out


def _wall_piece(name, Lp, H, t, n_rows, ends, tabs, flex_ivs, pitch, pt, slit=2.7, bridge=6.0, solid_tabs=False, ext=None):
    """Polygone d'une paroi à plat (x le long de la ligne médiane, y de 0 = haut à H = bas) + fentes de flexion.
    ends : ('corner' | 'seam') pour le début et la fin ; tabs : [(xc, longueur)]."""
    h = H / n_rows
    e0, e1 = ext if ext else (t / 2, t / 2)       # saillie des doigts d'angle (t/2 à 90°, plus grande aux angles aigus)
    left, right = [], []
    for i in range(n_rows):
        if ends[0] == "corner":
            left.append(-e0 if i % 2 == 0 else e0)
        else:
            left.append(-t if i % 2 == 0 else t)
        if ends[1] == "corner":
            right.append(Lp + e1 if i % 2 == 1 else Lp - e1)
        else:
            right.append(Lp - t if i % 2 == 0 else Lp + t)

    def edge(y, x0, x1, up):
        pts = [(x0, y)]
        for xc, lt in tabs:
            if x0 + 0.1 < xc - lt / 2 and xc + lt / 2 < x1 - 0.1:
                dy = -pt if up else pt
                pts += [(xc - lt / 2, y), (xc - lt / 2, y + dy), (xc + lt / 2, y + dy), (xc + lt / 2, y)]
        pts.append((x1, y))
        return pts

    poly = edge(0.0, left[0], right[0], True)
    for i in range(n_rows):
        poly.append((right[i], i * h)); poly.append((right[i], (i + 1) * h))
        if i + 1 < n_rows:
            poly.append((right[i + 1], (i + 1) * h))
    bot = edge(H, left[-1], right[-1], False)[::-1]
    poly += bot
    for i in range(n_rows - 1, -1, -1):
        poly.append((left[i], (i + 1) * h)); poly.append((left[i], i * h))
        if i > 0:
            poly.append((left[i - 1], i * h))
    polys = [np.array(poly, float)]
    # paroi flexible « à boucles » (modèle validé à la découpe) : lignes de coupe espacées de `pitch`, alternativement
    #   E : fente de bord, du bord jusqu'au voisinage du milieu (un pont de matière de longueur `bridge` au milieu relie
    #       les cellules voisines) ;
    #   C : fente centrale, fermée aux deux bouts (`slit` = distance au bord haut / bas).
    # Chaque cellule est une boucle de deux nervures ; la bande s'étire comme un ressort au lieu de casser.
    ext_fn = (lambda x: pt if (not solid_tabs) and any(xc - lt / 2 < x < xc + lt / 2 for xc, lt in tabs) else 0.0)
    polys += _flex_slits(flex_ivs, Lp, H, t + 2.0, pitch, slit, bridge, ext_fn)
    return dict(name=name, qty=1, polys=polys)


def _make_box_fingers(res, p):
    H_, W_ = res.mat.shape
    ppm = W_ / res.w_mm
    sheet = (res.sheet > 0).astype(np.uint8)
    body = _body_mask(res, sheet)
    t = max(0.5, float(p.box_thickness_mm))
    H = max(6.0, float(p.box_depth_mm))
    fit = max(0.0, float(p.box_fit_mm))
    lip = max(0.3, float(p.box_lip_mm))
    notes = []
    if p.shape == "none" or core.effective_ring(p) < float(p.box_lip_mm) + t + 0.5:
        notes.append("ring_thin")
    outer = _polys(sheet, ppm, p)
    hang = [_circle(x, y, r) for x, y, r in (res.hang_holes or [])]
    padm = cv2.copyMakeBorder(body, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    dist = cv2.distanceTransform(padm, cv2.DIST_L2, 5)[1:-1, 1:-1]
    mid_mask = (dist >= (t / 2 + lip) * ppm).astype(np.uint8)
    diff_mask = (dist >= (lip + t + fit + 0.3) * ppm).astype(np.uint8)
    mids = [q for q in _polys(mid_mask, ppm, p)]
    if not mids:
        notes.append("too_small")
        return None, notes
    mid = max(mids, key=lambda q: len(q))
    pts, step = _resample(mid, 0.5)
    n = len(pts)
    L = n * step
    th, kappa, corners = _analyse(pts, step)
    # angles : on sépare la paroi à chaque angle de 35 à 150 degrés (étoile : un morceau par côté de branche),
    # les morceaux s'assemblent par des doigts d'angle dont la saillie dépend de l'angle entre les deux parois
    right_c = [c for c, ang in corners if 35 <= ang <= 178]
    sharp = [c for c, ang in corners if not (35 <= ang <= 178)]
    if sharp:
        notes.append("sharp_corners")
    ext_of = {c: float(np.clip((t / 2.0) / max(0.35, np.sin(np.pi - np.radians(ang))), t / 2.0, 1.6 * t))
              for c, ang in corners if 35 <= ang <= 178}
    flex_k = kappa > 1.0 / 300.0
    if len(right_c) >= 2:                               # pièces séparées aux angles, assemblées à doigts
        cuts = sorted(right_c)
        spans = [(cuts[k], cuts[(k + 1) % len(cuts)]) for k in range(len(cuts))]
        ends = ("corner", "corner")
    else:                                               # une seule bande refermée (joint en peigne)
        straight = np.nonzero(~flex_k)[0]
        i0 = int(np.median(straight)) if len(straight) > n * 0.2 else int(np.argmin(pts[:, 1]))
        nparts = int(min(3, max(1, p.box_wall_parts)))
        cutsB = []
        for k in range(nparts):                       # coupes réparties ; on préfère un endroit droit à proximité
            c = (i0 + int(round(k * n / nparts))) % n
            near = [(abs(((j - c + n // 2) % n) - n // 2), j) for j in range(c - int(15 / step), c + int(15 / step) + 1)
                    if not flex_k[j % n]]
            cutsB.append((min(near)[1] % n) if near and k > 0 else c)
        cutsB = sorted(set(cutsB))
        if len(cutsB) == 1:
            spans = [(cutsB[0], cutsB[0] + n)]
        else:
            spans = [(cutsB[k], cutsB[(k + 1) % len(cutsB)] if k + 1 < len(cutsB) else cutsB[0]) for k in range(len(cutsB))]
        ends = ("seam", "seam")
    n_rows = max(3, int(round(H / 8.0)) | 1)
    pitch = max(1.5, float(p.box_rib_mm))
    slit_len = max(1.0, float(p.box_end_mm))
    bridge_len = max(1.0, float(p.box_mid_mm))
    tab_slots, walls = [], []
    hang_zone = None
    if res.tab is not None and (res.tab > 0).any():
        k = max(1, int(round(2.0 * ppm)))
        hang_zone = cv2.dilate((res.tab > 0).astype(np.uint8), np.ones((2 * k + 1, 2 * k + 1), np.uint8)) > 0
    rmin = 1e9
    for (a, b) in spans:
        cnt = (b - a) % n if b != a + n else n
        if cnt == 0:
            cnt = n
        Lp = cnt * step
        idx = [(a + k) % n for k in range(cnt + 1)]
        fl = flex_k[idx]
        ivs, k = [], 0
        while k < len(fl):
            if fl[k]:
                k2 = k
                while k2 + 1 < len(fl) and fl[k2 + 1]:
                    k2 += 1
                lo, hi = max(k * step, t + 2.0), min(k2 * step, Lp - t - 2.0)    # hors des doigts d'extrémité
                if hi - lo >= 6.0:
                    ivs.append((lo, hi))
                    rmin = min(rmin, 1.0 / max(float(np.median(kappa[idx[k:k2 + 1]])), 1e-6))
                k = k2 + 1
            else:
                k += 1
        m = t + 3.0
        span = Lp - 2 * m
        if span < 6.0:
            continue
        nt = max(1, int(round(span / 16.0)))
        tabs = []
        for j in range(nt):
            xc = m + (j + 0.5) * span / nt
            ic = idx[min(len(idx) - 1, int(round(xc / step)))]
            kk = float(kappa[ic])
            solid = bool(p.box_tab_solid)
            # languette pleine : cordon rigide dans une fente courbe, flèche tolérée 0,25 mm ; languette découpée en
            # nervures : elle épouse la courbe, on tolère 1 mm de flèche (et donc des languettes plus longues)
            sag_ok = 0.25 if solid else 1.0
            lt = 10.0 if kk < 1.0 / 300.0 else float(np.clip(np.sqrt(8.0 * (1.0 / kk) * sag_ok), 3.0, 10.0))
            # jeu automatique : la fente s'élargit de la flèche de la languette sur la courbure locale
            sag = (lt * lt * kk / 8.0) if (kk >= 1.0 / 300.0 and solid) else 0.0
            extra = sag if p.box_fit_auto else 0.0
            i0 = (a + int(round((xc - lt / 2 - fit / 2) / step))) % n
            i1 = (a + int(round((xc + lt / 2 + fit / 2) / step))) % n
            slot_poly = _offset_poly(pts, step, i0, i1, (t + fit + extra) / 2.0)
            if hang_zone is not None:        # pas de languette là où l'œillet d'accroche passe (fente + trou se toucheraient)
                px = np.clip(np.round(slot_poly * ppm).astype(int), 0, [hang_zone.shape[1] - 1, hang_zone.shape[0] - 1])
                if hang_zone[px[:, 1], px[:, 0]].any():
                    continue
            tabs.append((xc, lt))
            tab_slots.append(slot_poly)
        walls.append(_wall_piece("wall", Lp, H, t, n_rows, ends, tabs, ivs, pitch, t, slit_len, bridge_len, bool(p.box_tab_solid),
                                 (ext_of.get(a, t / 2.0), ext_of.get(b % n, t / 2.0)) if ends[0] == "corner" else None))
    if rmin < 15.0:
        notes.append("radius_small")
    cable = []
    if p.box_cable_mm > 0 and diff_mask.any():
        ys, xs = np.nonzero(diff_mask)
        cx = float(xs.mean())
        col = np.nonzero(diff_mask[:, int(round(cx))])[0]
        yb = float(col.max()) if len(col) else float(ys.max())
        cable = [_circle(cx / ppm, yb / ppm - p.box_cable_mm / 2.0 - 2.0, p.box_cable_mm / 2.0)]
    parts = [dict(name="front", qty=1, polys=[q.copy() for q in res.polys_mm] + [q.copy() for q in tab_slots])]
    if p.box_diffuser and diff_mask.any():
        parts.append(dict(name="diffuser", qty=1, polys=_polys(diff_mask, ppm, p)))
    parts += walls
    key_holes, foot_parts, sup_notes = _support(body, ppm, p, float(p.box_depth_mm) + 2 * t, lip + t + 3.0, t)
    notes += sup_notes
    parts.append(dict(name="back", qty=1, polys=outer + hang + [q.copy() for q in tab_slots] + cable + _center_hole(body, ppm, p) + key_holes))
    parts += foot_parts
    return parts, notes


def _layout(parts, p, notes, **extra):
    for pt in parts:
        a = np.vstack(pt["polys"])
        lo, hi = a.min(0), a.max(0)
        pt["polys"] = [q - lo for q in pt["polys"]]
        pt["w"], pt["h"] = float(hi[0] - lo[0]), float(hi[1] - lo[1])
    gap = max(1.0, float(p.box_gap_mm))
    sw = max(60.0, float(p.box_sheet_w))
    inst = sorted([pt for pt in parts for _ in range(pt["qty"])], key=lambda a: -a["h"])
    x = y = rowh = maxw = 0.0
    layout = []
    for it in inst:
        if x > 0 and x + it["w"] > sw:
            x, y, rowh = 0.0, y + rowh + gap + 4.0, 0.0
        layout.append(dict(name=it["name"], x=x, y=y + 4.0, w=it["w"], h=it["h"],
                           polys=[q + np.array([x, y + 4.0]) for q in it["polys"]]))
        x += it["w"] + gap
        rowh = max(rowh, it["h"])
        maxw = max(maxw, x - gap)
    if maxw > sw:
        notes.append("sheet_too_small")
    return dict(parts=parts, layout=layout, sheet=(max(maxw, 1.0), y + rowh + 4.0), notes=notes, **extra)


def make_box(res, p):
    """Pièces du caisson selon le style : 'stack' (cadres collés) ou 'fingers' (parois à encoches)."""
    if getattr(p, "box_style", "stack") != "fingers":
        b = _make_box_stack(res, p)
        b["style"] = "stack"
        return b
    parts, notes = _make_box_fingers(res, p)
    if parts is None:
        return dict(parts=[], layout=[], sheet=(1.0, 1.0), notes=notes, frames=0, pilot=0,
                    depth_total=0.0, screws=0, style="fingers")
    t = float(p.box_thickness_mm)
    return _layout(parts, p, notes, frames=0, pilot=0, screws=0, style="fingers",
                   depth_total=float(p.box_depth_mm) + 2 * t)


def summary(box):
    """Version courte (JSON) pour l'interface."""
    cnt = {}
    for pt in box["parts"]:
        cnt[pt["name"]] = cnt.get(pt["name"], 0) + pt["qty"]
    return dict(counts=cnt, style=box.get("style", "stack"), sheet=[round(box["sheet"][0], 1), round(box["sheet"][1], 1)], frames=box["frames"],
                depth_total=round(box["depth_total"], 1), notes=box["notes"], screws=box["screws"])


def _path_d(q):
    d = "M" + " L".join(f"{a:.3f},{b:.3f}" for a, b in q)
    return d if len(q) == 2 else d + " Z"       # 2 points = trait ouvert (fente de flexion)


def _layout_bbox(box):
    return core.polys_bbox([q for it in box["layout"] for q in it["polys"]])


def box_svg_string(box, frame=False):
    W, H = box["sheet"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">']
    for i, it in enumerate(box["layout"]):
        d = " ".join(_path_d(q) for q in it["polys"])
        out.append(f'<g id="{it["name"]}_{i + 1}" fill="none" stroke="#ff0000" stroke-width="0.1"><path d="{d}"/></g>')
        out.append(f'<text x="{it["x"]:.2f}" y="{it["y"] - 1.0:.2f}" font-size="3" fill="#0000ff">{it["name"]}</text>')
    fb = _layout_bbox(box) if frame else None
    if fb:
        out.append(core.frame_svg(fb).rstrip("\n"))
    out.append("</svg>\n")
    return "\n".join(out)


def diffuser_svg_string(box):
    it = next((i for i in box["layout"] if i["name"] == "diffuser"), None)
    if it is None:
        return None
    allp = np.vstack(it["polys"])
    lo, hi = allp.min(0), allp.max(0)
    w, h = hi - lo
    d = " ".join(_path_d(q - lo) for q in it["polys"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
            f'<path d="{d}" fill="none" stroke="#ff0000" stroke-width="0.2"/></svg>')


def box_dxf_string(box, frame=False):
    h = box["sheet"][1]
    L = ["0", "SECTION", "2", "ENTITIES"]
    for it in box["layout"]:
        for q in it["polys"]:
            L += ["0", "POLYLINE", "8", "CUT", "66", "1", "70", "0" if len(q) == 2 else "1"]
            for x, y in q:
                L += ["0", "VERTEX", "8", "CUT", "10", f"{x:.4f}", "20", f"{h - y:.4f}"]
            L += ["0", "SEQEND", "8", "CUT"]
    fb = _layout_bbox(box) if frame else None
    if fb:
        L += core.frame_dxf_lines(fb, h)
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"


def diffuser_pdf_bytes(box, lang="fr"):
    """PDF vectoriel du diffuseur en taille réelle (1 unité = 1 point, 1 mm = 72/25,4 pt), page A4/A3 ou sur mesure.
    À imprimer à 100 % (« taille réelle », sans ajuster à la page) pour reporter le contour sur la feuille."""
    it = next((i for i in box["layout"] if i["name"] == "diffuser"), None)
    if it is None:
        return None
    allp = np.vstack(it["polys"])
    x0, y0 = allp.min(0)
    w, h = allp.max(0) - allp.min(0)
    mg = 10.0
    page = None
    for nm, (pw, ph) in (("A4", (210, 297)), ("A3", (297, 420))):
        for (a, b) in ((pw, ph), (ph, pw)):
            if page is None and w + 2 * mg <= a and h + 2 * mg + 8 <= b:
                page = (nm, a, b)
    if page is None:
        page = ("", w + 2 * mg, h + 2 * mg + 8)
    _, pw, ph = page
    k = 72.0 / 25.4
    ox, oy = (pw - w) / 2.0, mg + 8                      # origine du contour (mm, depuis le haut de la page)
    cmds = ["0.5 w 0 0 0 RG"]
    for q in it["polys"]:
        pts = [((x - x0 + ox) * k, (ph - (y - y0 + oy)) * k) for x, y in q]
        cmds.append(f"{pts[0][0]:.2f} {pts[0][1]:.2f} m " + " ".join(f"{a:.2f} {b:.2f} l" for a, b in pts[1:]) + " S")
    ttl = (f"Diffuseur {w:.1f} x {h:.1f} mm - imprimer a 100 % (taille reelle)" if lang == "fr"
           else f"Diffuser {w:.1f} x {h:.1f} mm - print at 100 % (actual size)")
    cmds.append(f"BT /F1 9 Tf {mg * k:.1f} {(ph - 10) * k:.1f} Td ({ttl}) Tj ET")
    # règle de 50 mm pour vérifier l'échelle à l'impression
    ry = (ph - (ph - mg / 2)) * k
    cmds.append(f"{mg * k:.2f} {ry:.2f} m {(mg + 50) * k:.2f} {ry:.2f} l S "
                f"{mg * k:.2f} {ry - 3:.2f} m {mg * k:.2f} {ry + 3:.2f} l S {(mg + 50) * k:.2f} {ry - 3:.2f} m {(mg + 50) * k:.2f} {ry + 3:.2f} l S")
    cmds.append(f"BT /F1 7 Tf {(mg + 52) * k:.1f} {ry - 2:.1f} Td (50 mm) Tj ET")
    content = "\n".join(cmds).encode("latin-1", "replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw * k:.2f} {ph * k:.2f}] /Contents 4 0 R "
            f"/Resources << /Font << /F1 5 0 R >> >> >>".encode(),
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xr = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xr}\n%%EOF\n".encode()
    return bytes(out)


LABELS_FR = {"front": "Façade", "diffuser": "Diffuseur", "frame": "Cadre", "frame_pilot": "Cadre (avant-trous)", "back": "Fond", "wall": "Paroi", "foot_base": "Pied (base)", "foot_slot": "Pied (rainure)"}
LABELS_EN = {"front": "Front", "diffuser": "Diffuser", "frame": "Frame", "frame_pilot": "Frame (pilot holes)", "back": "Back", "wall": "Wall", "foot_base": "Stand (base)", "foot_slot": "Stand (slot layer)"}


def render_box(res, p, width=1200, lang=None):
    """Image de la mise en page des pièces + liste."""
    try:
        from .i18n import get_language, set_language
    except ImportError:
        from i18n import get_language, set_language
    if lang:
        set_language(lang)
    box = make_box(res, p)
    labels = LABELS_FR if get_language() == "fr" else LABELS_EN
    Wm, Hm = box["sheet"]
    s = (width - 40) / max(Wm, 1.0)
    foot = 130
    canvas = Image.new("RGB", (width, int(Hm * s) + 40 + foot), (250, 250, 250))
    arr = np.array(canvas)
    for it in box["layout"]:
        x0, y0 = int(it["x"] * s) + 20, int(it["y"] * s) + 20
        w, h = int(it["w"] * s) + 2, int(it["h"] * s) + 2
        m = np.zeros((h + 4, w + 4), np.uint8)
        for q in it["polys"]:
            if len(q) == 2:
                continue
            one = np.zeros_like(m)
            pts = np.round((q - [it["x"], it["y"]]) * s).astype(np.int32) + 2
            cv2.fillPoly(one, [pts.reshape(-1, 1, 2)], 1)
            m ^= one                      # remplissage pair/impair : les trous restent vides
        reg = arr[y0 - 2:y0 - 2 + m.shape[0], x0 - 2:x0 - 2 + m.shape[1]]
        mm = m[:reg.shape[0], :reg.shape[1]] > 0
        reg[mm] = (222, 190, 140) if it["name"] in ("front",) else ((205, 225, 240) if it["name"] == "diffuser" else (214, 196, 160))
        for q in it["polys"]:
            cv2.polylines(arr, [(np.round(q * s).astype(np.int32) + [20, 20]).reshape(-1, 1, 2)], len(q) > 2,
                          (40, 40, 40) if len(q) > 2 else (150, 70, 40), 1)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    f = core._load_font(14)
    for it in box["layout"]:
        d.text((int(it["x"] * s) + 22, int(it["y"] * s) + 4), labels.get(it["name"], it["name"]), fill=(20, 60, 160), font=f)
    tot = {}
    for pt in box["parts"]:
        tot[pt["name"]] = tot.get(pt["name"], 0) + pt["qty"]
    cnt = ", ".join(f"{labels[k]} x{v}" for k, v in tot.items())
    y = int(Hm * s) + 30
    try:
        from .i18n import tr
    except ImportError:
        from i18n import tr
    lines = [cnt,
             tr("Stack thickness: {d} mm  |  cutting sheet needed: {w} x {h} mm", d=round(box["depth_total"], 1),
                w=round(Wm), h=round(Hm))]
    msgs = {"depth_low": "Depth under 15 mm: the LEDs may show as bright spots through the front.",
            "wall_thin": "The wall is too narrow for the screws: widen it or reduce the screw diameter.",
            "wall_too_wide": "The wall is wider than the piece: reduce the wall width.",
            "sheet_too_small": "A part is wider than the cutting sheet width.",
            "sharp_corners": "Sharp corners (not 90 degrees): the flexible wall may break there. Prefer the stacked box for this shape.",
            "radius_small": "Some curves are tighter than 15 mm radius: use thin flexible plywood or a larger pitch of slits.",
            "ring_thin": "The outer ring is too narrow for the wall slots: widen it (at least wall thickness + 2 mm).",
            "too_small": "The piece is too small for a box.",
            "key_no_room": "No room for the wall keyholes in the back: reduce the screw head size or widen the shape.",
            "foot_shape": "A stand needs a frame shape to hold the box."}
    lines += [tr(msgs[n]) for n in box["notes"] if n in msgs]
    for ln in lines:
        d.text((20, y), ln, fill=(160, 40, 30) if ln in [tr(m) for m in msgs.values()] else (30, 30, 30), font=f)
        y += 22
    return np.array(img)


# --------------------------------------------------------------------------
# Vue du caisson assemblé (perspective oblique) : pour contrôler les proportions avant de découper
# --------------------------------------------------------------------------
def render_assembled(res, p, style=None, width=1100):
    try:
        from . import core as _core
    except ImportError:
        import core as _core
    style = style or {}
    box = make_box(res, p)
    H, W = res.mat.shape
    ppm = W / res.w_mm
    sheet = (res.sheet > 0)
    body = _body_mask(res, sheet)
    t = max(0.5, float(p.box_thickness_mm))
    D = float(box["depth_total"]) or (float(p.box_depth_mm) + 2 * t)
    lip = float(p.box_lip_mm) if getattr(p, "box_style", "stack") == "fingers" else 0.0
    wall_mask = body
    if lip > 0:
        k = max(1, int(round(lip * ppm)))
        wall_mask = cv2.erode(body, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    kx, ky = 0.46, -0.30                                  # décalage par mm de profondeur (vers le fond : droite et haut)
    zs = ppm
    front_img = _core.render_view(res, "render", style)
    if front_img.shape[:2] != (H, W):
        front_img = cv2.resize(front_img, (W, H))
    # étendue : pied éventuel
    foot = [q for q in box["parts"] if q["name"] in ("foot_base", "foot_slot")]
    mg = int(0.08 * max(H, W)) + 10
    extra_x = int(0.6 * W) if foot else 0
    cw = int(W + D * kx * zs + 2 * mg + extra_x)
    ch = int(H + D * abs(ky) * zs + 2 * mg + (0.5 * H if foot else 0) + (D * abs(ky) * zs if foot else 0))
    canvas = np.full((ch, cw, 3), 248, np.uint8)
    ox, oy = mg + extra_x // 2, mg + int(D * abs(ky) * zs)

    def shift(z):
        return ox + int(round(z * kx * zs)), oy + int(round(z * ky * zs))

    def put(mask, color, z):
        dx, dy = shift(z)
        reg = canvas[dy:dy + H, dx:dx + W]
        m = mask[:reg.shape[0], :reg.shape[1]] > 0
        if isinstance(color, np.ndarray) and color.ndim == 3:
            reg[m] = color[:reg.shape[0], :reg.shape[1]][m]
        else:
            reg[m] = color

    def outline(mask, z, col=(70, 55, 35)):
        cs, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dx, dy = shift(z)
        cv2.drawContours(canvas, [c + np.array([dx, dy]) for c in cs], -1, col, 1, cv2.LINE_AA)

    wood = np.array((214, 190, 150), np.uint8)
    wall_col = np.array((186, 160, 120), np.uint8)
    # fond, paroi (couche par couche : de l'arrière vers l'avant), façade
    steps = max(2, int(D / 0.6))
    put(sheet, wood * 0.82, D)
    outline(sheet, D)
    for i in range(steps, 0, -1):
        z = D * i / steps
        if t < z < D - t:
            shade = 0.88 + 0.12 * (i / steps)
            put(wall_mask, (wall_col * shade).astype(np.uint8), z)
        elif z >= D - t:
            put(sheet, (wood * 0.85).astype(np.uint8), z)
    outline(wall_mask, D - t, (110, 90, 60))
    outline(wall_mask, t, (110, 90, 60))
    put(sheet, front_img, 0.0)
    outline(sheet, 0.0)
    # pied : bloc (base + couches à rainure) sous le caisson, rainure autour du bas du corps
    if foot:
        ys, xs = np.nonzero(body)
        cxm, yb = (xs.min() + xs.max()) / 2.0 / ppm, ys.max() / ppm
        base = next(q for q in foot if q["name"] == "foot_base")
        slot = next(q for q in foot if q["name"] == "foot_slot")
        fw, fd = float(base["w"]), float(base["h"])
        n = slot["qty"]
        hb = (n + 1) * t
        z0, z1 = D / 2 - fd / 2, D / 2 + fd / 2
        xa, xb = cxm - fw / 2, cxm + fw / 2
        ytop, ybot = yb - n * t, yb + t
        sl = np.vstack(slot["polys"][1:2]) if len(slot["polys"]) > 1 else None
        sl_w = (sl[:, 0].max() - sl[:, 0].min()) if sl is not None else 0
        sl_d = (sl[:, 1].max() - sl[:, 1].min()) if sl is not None else 0

        def P(x, y, z):
            dx, dy = shift(z)
            return [dx + x * ppm, dy + y * ppm]

        def poly(pts, col, line=(90, 70, 45)):
            a = np.round(np.array(pts)).astype(np.int32)
            cv2.fillPoly(canvas, [a], col, cv2.LINE_AA)
            cv2.polylines(canvas, [a], True, line, 1, cv2.LINE_AA)
        top = [P(xa, ytop, z0), P(xb, ytop, z0), P(xb, ytop, z1), P(xa, ytop, z1)]
        # face du dessus avec la rainure en creux : on la dessine puis on repeint la rainure avec le caisson derrière
        snap = canvas.copy()
        poly(top, (230, 208, 168))
        ring = canvas.copy()
        canvas[:] = snap
        if sl is not None:
            zc = D / 2
            hole = np.round(np.array([P(cxm - sl_w / 2, ytop, zc - sl_d / 2), P(cxm + sl_w / 2, ytop, zc - sl_d / 2),
                                      P(cxm + sl_w / 2, ytop, zc + sl_d / 2), P(cxm - sl_w / 2, ytop, zc + sl_d / 2)])).astype(np.int32)
            hm = np.zeros(canvas.shape[:2], np.uint8)
            cv2.fillPoly(hm, [hole], 1)
            canvas[:] = np.where(hm[..., None] > 0, snap, ring)
            cv2.polylines(canvas, [hole], True, (90, 70, 45), 1, cv2.LINE_AA)
        else:
            canvas[:] = ring
        poly([P(xb, ytop, z0), P(xb, ytop, z1), P(xb, ybot, z1), P(xb, ybot, z0)], (176, 152, 112))     # côté droit
        poly([P(xa, ytop, z0), P(xb, ytop, z0), P(xb, ybot, z0), P(xa, ybot, z0)], (200, 176, 136))     # face avant
    ys2, xs2 = np.nonzero(np.any(canvas != 248, axis=2))
    out = canvas[max(0, ys2.min() - 12):ys2.max() + 12, max(0, xs2.min() - 12):xs2.max() + 12]
    sc = width / out.shape[1]
    if sc < 1.0:
        out = cv2.resize(out, (width, int(out.shape[0] * sc)), interpolation=cv2.INTER_AREA)
    return out


# --------------------------------------------------------------------------
# Plaque de test de flexibilité : plusieurs bandes avec des réglages différents, à couper dans le vrai matériau
# --------------------------------------------------------------------------
FLEX_RIBS = (2.0, 2.54, 3.0, 3.5)
FLEX_BRIDGES = (4.0, 6.0, 8.0)


def make_flex_test(p, length=70.0):
    """Bandes de test : lignes = largeur de nervure, colonnes = pont du milieu ; hauteur = profondeur du caisson."""
    H = max(6.0, float(p.box_depth_mm))
    end = max(1.0, float(p.box_end_mm))
    gap = max(6.0, float(p.box_gap_mm))
    layout, labels = [], []
    x = y = rowh = maxw = 0.0
    k = 0
    for rib in FLEX_RIBS:
        for br in FLEX_BRIDGES:
            k += 1
            if x > 0 and br == FLEX_BRIDGES[0]:          # une ligne par largeur de nervure, une colonne par pont
                x, y = 0.0, y + rowh + gap + 6.0
                rowh = 0.0
            rect = np.array([[0, 0], [length, 0], [length, H], [0, H]], float)
            polys = [rect] + _flex_slits([(0.0, length)], length, H, 3.0, rib, end, br)
            pl = [q + np.array([x, y + 6.0]) for q in polys]
            layout.append(dict(name="test", x=x, y=y + 6.0, w=length, h=H, polys=pl))
            labels.append((x, y + 4.0, f"{k}: nervure {rib:g} / pont {br:g}"))
            x += length + gap
            rowh = max(rowh, H + 6.0)
            maxw = max(maxw, x - gap)
    box = dict(parts=[], layout=layout, sheet=(max(maxw, 1.0), y + rowh + 4.0), notes=[], labels=labels,
               frames=0, pilot=0, screws=0, style="flextest", depth_total=0.0)
    return box


def flex_test_svg(box):
    W, H = box["sheet"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">']
    for i, it in enumerate(box["layout"]):
        d = " ".join(_path_d(q) for q in it["polys"])
        out.append(f'<g id="test_{i + 1}" fill="none" stroke="#ff0000" stroke-width="0.1"><path d="{d}"/></g>')
    for x, y, txt in box["labels"]:
        out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="3" fill="#0000ff">{txt}</text>')
    out.append("</svg>\n")
    return "\n".join(out)


def flex_test_dxf(box):
    s = box_dxf_string(box).replace("0\nENDSEC\n0\nEOF\n", "")
    h = box["sheet"][1]
    L = []
    for x, y, txt in box["labels"]:
        L += ["0", "TEXT", "8", "LABEL", "10", f"{x:.3f}", "20", f"{h - y:.3f}", "40", "3", "1", txt]
    return s + "\n".join(L) + ("\n" if L else "") + "0\nENDSEC\n0\nEOF\n"
