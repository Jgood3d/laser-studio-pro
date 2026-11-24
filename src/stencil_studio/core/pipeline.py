"""Calcul complet d'un pochoir (process) : enchaîne cadrage, sujet, tons, plaque et sortie demandée.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import time
from dataclasses import replace
import cv2
import numpy as np

from .params import Result
from .framing import fill_outside
from .subject import ai_mask, auto_subject
from .tones import clean_mask, tone_gray, tone_mask
from .plate import _pad_img, add_bridges, apply_shape, decorate, effective_ring, extract_contours, shape_inside
from .halftone import halftone
from .engraving import engrave_result
from .lowpoly import lowpoly_mask
from .qr import qr_masks, qr_scan_check
from .colors import is_flat_image, is_shaded_image
from .layers import _layer_domain, _layer_engraving, _pin_points, layers_masks, layers_masks_color, parse_picks
from .render import _sheet_mask


def layers_result(rgb, p, subject=None, valid=None):
    t0 = time.time()
    h, w = rgb.shape[:2]
    colors, corder = None, None
    color_meta = {}
    dom = _layer_domain(rgb, p, subject, valid)
    # Logo / aplat : analyser TOUTE l'image (y compris bandes rouges en bordure),
    # quel que soit ml_bg (front ou plaque à part).
    if (p.ml_sep == "color" and subject is None
            and (parse_picks(p.ml_picks) or is_flat_image(fill_outside(rgb, valid), valid))):
        dom = np.ones((h, w), np.uint8) if valid is None else valid.astype(np.uint8)
    use_color = (p.ml_sep == "color")
    picks = parse_picks(p.ml_picks)
    # Image ombrée / photo sans pipette : bascule vers les tons (meilleur relief)
    if use_color and not picks and is_shaded_image(fill_outside(rgb, valid), valid):
        use_color = False
        color_meta["ml_sep_fallback"] = "tone"
        color_meta["ml_sep_reason"] = "shaded"
    if use_color:
        masks, colors, corder = layers_masks_color(rgb, p, subject, valid, dom, meta=color_meta)
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
    pl = replace(p, output="stencil", keep_islands=(colors is not None))
    nm = len(masks)

    def _plate_params(i):
        # Une plaque posée sur une plaque pleine n'a pas besoin de ponts : ses îlots se collent derrière.
        # Plaque de devant : ponts conservés (sauf « pièces libres »). Plaques intermédiaires : libres,
        # sinon le pont d'une couleur de milieu (ex. rouge) se voit comme un trait entre les formes de devant.
        if i == 0:
            return pl
        if p.ml_pieces or (p.ml_mid_loose and i < nm - 1):
            return replace(pl, loose=True)
        return pl
    outs = [process(rgb, _plate_params(i), None, valid, raw_override=m) for i, m in enumerate(masks)]
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
        if color_meta.get("ml_ignored"):
            info["ml_ignored"] = color_meta["ml_ignored"]
    if color_meta.get("ml_sep_fallback"):
        info["ml_sep_fallback"] = color_meta["ml_sep_fallback"]
        info["ml_sep_reason"] = color_meta.get("ml_sep_reason", "")
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
