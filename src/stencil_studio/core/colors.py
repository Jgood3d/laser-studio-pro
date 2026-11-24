"""Analyse des couleurs : image en aplats ou ombrée, palette, regroupement des teintes, classes.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np


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


def is_shaded_image(rgb, valid=None):
    """Vrai pour une photo / figurine ombrée : beaucoup de micro-variations, peu d'aplats francs.
    Dans ce cas la séparation par tons est en général plus pertinente que par couleurs dominantes."""
    if is_flat_image(rgb, valid, top=8, share=0.78):
        return False
    small = cv2.resize(rgb, None, fx=min(1.0, 280.0 / max(rgb.shape[:2])), fy=min(1.0, 280.0 / max(rgb.shape[:2])),
                       interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB)
    L = lab[:, :, 0].astype(np.float32)
    if valid is not None:
        vm = cv2.resize(valid.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        if not vm.any():
            return False
    else:
        vm = np.ones(L.shape, bool)
    # gradient local moyen élevé + beaucoup de niveaux de L distincts → ombrage / photo
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    gmag = np.hypot(gx, gy)[vm]
    levels = len(np.unique((L[vm] / 4.0).astype(np.int32)))
    return float(np.median(gmag)) > 6.5 and levels >= 28


def _chroma_boost(cen_lab, counts, total):
    """Score d'importance : surface + vivacité + bonus contours sombres.
    Les aplats vifs même petits (bandes rouges) restent prioritaires."""
    frac = counts / max(1.0, float(total))
    surf = np.clip((frac - 0.0010) / 0.04, 0.05, 1.0)
    a = cen_lab[:, 1].astype(np.float32) - 128.0
    b = cen_lab[:, 2].astype(np.float32) - 128.0
    chroma = np.hypot(a, b)
    # bonus fort pour les couleurs saturées (rouge logo, etc.)
    vivid = 1.0 + 1.35 * np.clip(chroma / 45.0, 0.0, 1.8)
    L = cen_lab[:, 0].astype(np.float32)
    dark = 1.0 + 0.55 * np.clip((55.0 - L) / 55.0, 0.0, 1.0)
    return surf * vivid * dark


def _merge_near_colors(cen, cnt, max_dist=12.0, white_dist=18.0):
    """Fusionne les centres très proches en Lab. Les quasi-blancs se regroupent plus facilement ;
    les teintes sombres (traits) ne sont fusionnées que si vraiment identiques."""
    cen = np.asarray(cen, np.float32).copy()
    cnt = np.asarray(cnt, np.float64).copy()
    merged = True
    while merged and len(cen) > 2:
        merged = False
        best, bd = None, 1e9
        for i in range(len(cen)):
            for j in range(i + 1, len(cen)):
                dd = float(np.linalg.norm(cen[i] - cen[j]))
                ch_i = float(np.hypot(cen[i, 1] - 128.0, cen[i, 2] - 128.0))
                ch_j = float(np.hypot(cen[j, 1] - 128.0, cen[j, 2] - 128.0))
                # blancs / pâles : seuil large
                if cen[i, 0] > 180 and cen[j, 0] > 180 and ch_i < 18 and ch_j < 18:
                    lim = white_dist
                # deux teintes sombres (contours) : seuil strict pour ne pas perdre le trait
                elif cen[i, 0] < 60 and cen[j, 0] < 60:
                    lim = min(max_dist, 9.0)
                # couleur vive (rouge, etc.) : ne fusionner que si quasi identique
                elif ch_i >= 28.0 or ch_j >= 28.0:
                    lim = min(max_dist, 8.0)
                else:
                    lim = max_dist
                if dd < lim and dd < bd:
                    best, bd = (i, j), dd
        if best is not None and bd < 1e8:
            i, j = best
            cen[i] = (cen[i] * cnt[i] + cen[j] * cnt[j]) / max(1e-6, cnt[i] + cnt[j])
            cnt[i] += cnt[j]
            cen, cnt = np.delete(cen, j, 0), np.delete(cnt, j)
            merged = True
    return cen, cnt


def _select_mmr(cen_lab, counts, total, k, min_dist=11.0, lam=0.45):
    """Sélectionne jusqu'à k centres en favorisant l'importance et la diversité perceptuelle (Lab).
    Retourne (indices_choisis, liste_(idx, raison_rejet))."""
    m = len(cen_lab)
    if m <= k:
        return list(range(m)), []
    imp = _chroma_boost(cen_lab, counts, total)
    imp_n = imp / max(1e-6, float(imp.max()))
    first = int(np.argmax(imp))
    chosen = [first]

    while len(chosen) < k:
        best_idx = None
        best_val = -1e9
        for i in range(m):
            if i in chosen:
                continue
            dmin = min(float(np.linalg.norm(cen_lab[i] - cen_lab[j])) for j in chosen)
            # pénalité plus forte sous min_dist ; les accents vifs restent favorisés via imp_n
            pen = 3.2 if dmin < min_dist else lam * np.exp(-dmin / 28.0)
            val = imp_n[i] - pen
            if val > best_val:
                best_val = val
                best_idx = i
        if best_idx is None:
            break
        # Arrêt anticipé seulement si le candidat est quasi nul (évite de couper noir / détails)
        if best_val < 0.02 and len(chosen) >= 2:
            break
        chosen.append(best_idx)

    rejected = []
    for i in range(m):
        if i not in chosen:
            dmin = min(float(np.linalg.norm(cen_lab[i] - cen_lab[j])) for j in chosen)
            reason = "merged" if dmin < min_dist else "cap"
            rejected.append((i, reason))
    return chosen, rejected


def _lab_to_hex(lab_vec):
    rgb = cv2.cvtColor(np.clip(lab_vec, 0, 255).reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB)[0, 0]
    return "#%02x%02x%02x" % (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _collect_ignored_vivid(cen_lab, counts, total, rejected, min_chroma=22.0):
    """Liste compacte des couleurs vives non retenues dans la palette finale."""
    out = []
    for idx, reason in rejected:
        c = cen_lab[idx]
        chroma = float(np.hypot(float(c[1]) - 128.0, float(c[2]) - 128.0))
        frac = float(counts[idx]) / max(1.0, float(total))
        if chroma >= min_chroma and frac >= 0.0025:
            out.append({
                "hex": _lab_to_hex(c),
                "reason": reason,
                "share": round(frac * 100.0, 2),
                "chroma": round(chroma, 1),
            })
    out.sort(key=lambda item: (-item["chroma"], -item["share"]))
    return out[:6]


def _saturated_peaks_lab(rgb, dom, max_peaks=4, min_frac=0.0015):
    """Centres Lab des aplats saturés (rouge, etc.) via histogramme HSV — même s'ils sont fins."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    m = (dom > 0) & (hsv[:, :, 1] >= 80) & (hsv[:, :, 2] >= 40)
    if int(m.sum()) < 50:
        return np.zeros((0, 3), np.float32), np.zeros(0, np.float64)
    # quantifie la teinte (H) en 18 seaux
    h = hsv[:, :, 0][m].astype(np.int32)
    bins = np.bincount(h // 10, minlength=18)
    total = float(m.sum())
    peaks = []
    counts = []
    lab0 = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    for bi in np.argsort(-bins):
        if bins[bi] < min_frac * total:
            break
        sel = m & (hsv[:, :, 0] // 10 == bi)
        if not sel.any():
            continue
        peaks.append(lab0[sel].mean(0))
        counts.append(float(sel.sum()))
        if len(peaks) >= max_peaks:
            break
    if not peaks:
        return np.zeros((0, 3), np.float32), np.zeros(0, np.float64)
    return np.array(peaks, np.float32), np.array(counts, np.float64)


def _flat_palette(lab0, dom, n, min_frac=0.0025, radius=13.0, meta=None, rgb=None):
    """Palette d'un logo / d'une illustration à aplats : couleurs dominantes cherchées sur les pixels « plats »
    (sans les bords anti-crénelés, qui ne sont que des mélanges de deux couleurs), par recherche de modes.
    Garde les petites zones vraiment distinctes (bandes, nez, yeux, langue) grâce à la diversité MMR et au bonus
    de vivacité chromatique. Retourne les centres (Lab OpenCV) ou None si l'image n'est pas à aplats."""
    m = dom > 0
    k3 = np.ones((3, 3), np.uint8)
    rng = np.zeros(m.shape, np.float32)
    for c in range(3):
        ch = lab0[:, :, c]
        rng = np.maximum(rng, cv2.dilate(ch, k3) - cv2.erode(ch, k3))
    flat = m & (rng < 7.0)
    pts = lab0[flat]
    if len(pts) < 300:
        return None
    if len(pts) > 120000:
        pts = pts[np.random.default_rng(11).choice(len(pts), 120000, replace=False)]
    total = len(pts)
    rem, cens, cnts = pts, [], []
    for _ in range(18):
        if len(rem) < 0.0008 * total:
            break
        q = np.floor(rem / 6.0).astype(np.int64)
        key = (q[:, 0] * 64 + q[:, 1]) * 64 + q[:, 2]
        uniq, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        c = rem[inv == int(np.argmax(cnt))].mean(0)
        for _ in range(4):
            sel = np.linalg.norm(rem - c, axis=1) < radius * 0.8
            if sel.any():
                c = rem[sel].mean(0)
        sel = np.linalg.norm(rem - c, axis=1) < radius
        n_sel = int(sel.sum())
        chroma = float(np.hypot(c[1] - 128.0, c[2] - 128.0))
        # aplats vifs (bandes rouges) acceptés plus petits que les gris neutres
        need = (min_frac * 0.45 * total) if chroma >= 28.0 else (min_frac * total)
        if n_sel >= need:
            cens.append(c)
            cnts.append(n_sel)
        rem = rem[~sel]
    if len(cens) < 2:
        return None
    cen = np.array(cens, np.float32)
    cnt = np.array(cnts, np.float64)
    # injecte les aplats saturés (bandes rouges fines) s'ils manquent
    if rgb is not None:
        sp, sc = _saturated_peaks_lab(rgb, dom.astype(np.uint8), max_peaks=4, min_frac=0.0012)
        for i in range(len(sp)):
            if len(cen) and min(float(np.linalg.norm(sp[i] - c)) for c in cen) < 14.0:
                continue
            cen = np.vstack([cen, sp[i][None, :]])
            cnt = np.append(cnt, sc[i])
    # fusion des centres presque identiques (dégradés doux / quasi-blancs anti-crénelés)
    cen, cnt = _merge_near_colors(cen, cnt, max_dist=12.0, white_dist=20.0)
    # l'image est-elle bien à aplats ? (la plupart des pixels du sujet sont proches d'une couleur trouvée ;
    # mesuré sur la palette complète, avant de la réduire au nombre de plaques demandé)
    pl = lab0[m]
    if len(pl) > 60000:
        pl = pl[np.random.default_rng(5).choice(len(pl), 60000, replace=False)]
    dmin = np.sqrt(((pl[:, None, :] - cen[None, :, :]) ** 2).sum(-1)).min(1)
    if float((dmin < 16.0).mean()) < 0.80:
        return None
    # nombre naturel de couleurs (auto) : n reste un plafond
    n_use = min(n, len(cen))  # lié au nombre de plaques manuel (plafond = n)
    # sélection MMR avec bonus de vivacité chromatique si plus de candidats que n plaques
    if len(cen) > n_use:
        chosen, rejected = _select_mmr(cen, cnt, total, n_use, min_dist=11.0, lam=0.45)
        if meta is not None:
            ign = _collect_ignored_vivid(cen, cnt, total, rejected)
            if ign:
                meta["ml_ignored"] = ign
        # rattache les centres écartés les plus proches sans altérer les teintes vives retenues
        kept_cen = cen[chosen].copy()
        for idx, reason in rejected:
            if reason == "merged":
                j = int(np.argmin([np.linalg.norm(cen[idx] - kept_cen[r]) for r in range(len(kept_cen))]))
                w_keep = cnt[chosen[j]]
                w_drop = cnt[idx]
                kept_cen[j] = (kept_cen[j] * w_keep + cen[idx] * w_drop) / max(1e-6, w_keep + w_drop)
        cen = kept_cen
    return cen[np.argsort(cen[:, 0])]


def _assign_flat(lab, cen, tol=16.0):
    """Étiquette chaque pixel par la couleur la plus proche ; un pixel de bord (loin de toutes les couleurs, car mélange
    de deux d'entre elles) va à la plus proche des deux couleurs qu'il mélange, pas à une troisième couleur
    intermédiaire (évite les liserés parasites entre le noir et le bleu). Aucun flou des étiquettes : les contours
    fins sont conservés."""
    h, w = lab.shape[:2]
    n = len(cen)
    flat_lab = lab.reshape(-1, 3)
    labels = np.empty(len(flat_lab), np.int64)
    dm = np.empty(len(flat_lab), np.float32)
    for s0 in range(0, len(flat_lab), 400000):      # par blocs : pas de tableau géant sur les grandes images
        blk = flat_lab[s0:s0 + 400000]
        d = np.sqrt(((blk[:, None, :] - cen[None, :, :]) ** 2).sum(-1))
        labels[s0:s0 + 400000] = d.argmin(1)
        dm[s0:s0 + 400000] = d.min(1)
    mix = np.nonzero(dm > tol)[0]
    if len(mix) and n >= 3:
        P = flat_lab[mix]
        best_d = np.full(len(mix), 1e9, np.float32)
        best_l = labels[mix].copy()
        for a in range(n):
            for b in range(a + 1, n):
                ab = cen[b] - cen[a]
                den = float((ab ** 2).sum())
                if den < 1e-6:
                    continue
                t = np.clip(((P - cen[a]) @ ab) / den, 0.0, 1.0)
                dist = np.linalg.norm(P - (cen[a] + t[:, None] * ab), axis=1)
                better = dist < best_d
                best_d = np.where(better, dist, best_d)
                best_l = np.where(better, np.where(t < 0.5, a, b), best_l)
        labels[mix] = best_l
    return labels.reshape(h, w).astype(np.int32)


def color_classes(rgb, dom, n, valid=None, auto=True, picks=None, meta=None):
    """Classe chaque pixel du sujet parmi au plus n couleurs dominantes (k-means / modes en Lab).

    - picks : couleurs choisies à la pipette (listes de RGB). Elles servent de centres
      préférés. Le nombre de plaques demandé (n) est TOUJOURS respecté.
        • len(picks) == n  → centres exacts
        • len(picks) <  n  → picks en graines + k-means pour le reste
        • len(picks) >  n  → on garde les n picks les mieux réparties en luminosité
    - auto : fusion des couleurs proches / sélection MMR avec bonus de vivacité chromatique
      (uniquement quand il n'y a pas de picks).
    Retourne (labels, centres RGB triés du plus sombre au plus clair).
    """
    h, w = rgb.shape[:2]
    lab = cv2.cvtColor(cv2.GaussianBlur(rgb, (0, 0), max(1.0, 0.003 * max(h, w))),
                       cv2.COLOR_RGB2LAB).astype(np.float32)
    lab0 = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)

    picks = picks or []
    n = int(max(2, min(8, n)))

    # ---------- Cas pipette ----------
    if picks:
        order_p = sorted(picks, key=lambda c: cv2.cvtColor(
            np.array([[c]], np.uint8), cv2.COLOR_RGB2LAB)[0, 0, 0])

        if len(order_p) >= n:
            if len(order_p) > n:
                idx = [int(round(i * (len(order_p) - 1) / (n - 1))) for i in range(n)]
                order_p = [order_p[i] for i in idx]
            cen = cv2.cvtColor(np.array([order_p], np.uint8),
                               cv2.COLOR_RGB2LAB).reshape(n, 3).astype(np.float32)
        else:
            # Les picks sont des centres FIXES ; on complète jusqu'à n avec des modes distants
            fixed = cv2.cvtColor(np.array([order_p], np.uint8),
                                 cv2.COLOR_RGB2LAB).reshape(len(order_p), 3).astype(np.float32)
            src = lab0 if auto else lab
            pts = src[dom > 0]
            if len(pts) < n * 10:
                pts = src.reshape(-1, 3)
            if len(pts) > 40000:
                pts = pts[np.random.default_rng(3).choice(len(pts), 40000, replace=False)]

            crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
            k_extra = min(max(n + 2, n * 2), 12)
            _, _, cand = cv2.kmeans(pts, k_extra, None, crit, 3, cv2.KMEANS_PP_CENTERS)
            # part des picks, ajoute les candidats les plus éloignés des centres déjà choisis
            cen_list = [fixed[i] for i in range(len(fixed))]
            while len(cen_list) < n and len(cand):
                dmin = np.array([min(float(np.linalg.norm(c - f)) for f in cen_list) for c in cand])
                j = int(np.argmax(dmin))
                if dmin[j] < 8.0:   # plus rien de distinct
                    break
                cen_list.append(cand[j])
                cand = np.delete(cand, j, 0)
            # si encore trop peu : comble avec k-means à n puis impose les picks
            if len(cen_list) < n:
                _, _, cen = cv2.kmeans(pts, n, None, crit, 3, cv2.KMEANS_PP_CENTERS)
                for f in fixed:
                    j = int(np.argmin(np.linalg.norm(cen - f, axis=1)))
                    cen[j] = f
            else:
                cen = np.array(cen_list[:n], np.float32)
            cen = cen[np.argsort(cen[:, 0])]

        d = ((lab[:, :, None, :] - cen[None, None, :, :]) ** 2).sum(-1)
        if is_flat_image(rgb):
            labels = np.argmin(d, -1).astype(np.uint8)
            labels = cv2.medianBlur(labels, 5 if max(h, w) > 600 else 3).astype(np.int32)
        else:
            prob = np.exp(-d / 400.0)
            sig = max(1.0, 0.004 * max(h, w))
            sm = np.stack([cv2.GaussianBlur(prob[:, :, k].astype(np.float32), (0, 0), sig)
                           for k in range(n)], -1)
            labels = np.argmax(sm, -1).astype(np.int32)

        rgb_c = cv2.cvtColor(np.clip(cen, 0, 255).reshape(1, n, 3).astype(np.uint8),
                             cv2.COLOR_LAB2RGB).reshape(n, 3)
        return labels, [tuple(int(v) for v in q) for q in rgb_c]

    # ---------- Cas classique (sans pipette) ----------
    if auto:
        pal = _flat_palette(lab0, dom, n, meta=meta, rgb=rgb)
        if pal is not None:     # logo / illustration à aplats : palette par modes, étiquettes sans flou
            lab_f = cv2.cvtColor(cv2.GaussianBlur(rgb, (0, 0), 0.6), cv2.COLOR_RGB2LAB).astype(np.float32)
            labels = _assign_flat(lab_f, pal)
            rgb_c = cv2.cvtColor(np.clip(pal, 0, 255).reshape(1, len(pal), 3).astype(np.uint8),
                                 cv2.COLOR_LAB2RGB).reshape(len(pal), 3)
            return labels, [tuple(int(v) for v in q) for q in rgb_c]
    src = lab0 if auto else lab
    pts = src[dom > 0]
    if len(pts) < n * 10:
        pts = src.reshape(-1, 3)
    if len(pts) > 40000:
        pts = pts[np.random.default_rng(3).choice(len(pts), 40000, replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    k_cand = min(max(n + 3, n * 2), 12) if auto else n
    _, _, cen = cv2.kmeans(pts, k_cand, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    cen = cen[np.argsort(cen[:, 0])]
    flat = False
    if auto:
        d = np.sqrt(((pts[:, None, :] - cen[None, :, :]) ** 2).sum(-1))
        cnt = np.bincount(d.argmin(1), minlength=len(cen)).astype(np.float64)
        total_pts = float(len(pts))
        # filtre le bruit micro-pixel (< 0.25 %)
        valid_c = [i for i in range(len(cen)) if cnt[i] >= 0.0025 * total_pts]
        if len(valid_c) >= 2:
            cen = cen[valid_c]
            cnt = cnt[valid_c]
        # regroupe les quasi-blancs et teintes presque identiques avant la sélection
        cen, cnt = _merge_near_colors(cen, cnt, max_dist=12.0, white_dist=19.0)
        n_use = min(n, len(cen))  # lié au nombre de plaques manuel (plafond = n)
        # sélection MMR avec bonus chromatique pour préserver les accents vifs (ex. bandes rouges)
        chosen, rejected = _select_mmr(cen, cnt, total_pts, n_use, min_dist=11.0, lam=0.45)
        if meta is not None:
            ign = _collect_ignored_vivid(cen, cnt, total_pts, rejected)
            if ign:
                meta["ml_ignored"] = ign
        cen = cen[chosen]
        cnt = cnt[chosen]
        # élagage des clusters redondants ou de mélange intermédiaire sans supprimer les couleurs vives distinctes
        for _ in range(len(cen)):
            k = len(cen)
            if k <= 2:
                break
            d = np.sqrt(((pts[:, None, :] - cen[None, :, :]) ** 2).sum(-1))
            frac = np.bincount(d.argmin(1), minlength=k) / max(1, len(pts))
            chroma = np.hypot(cen[:, 1] - 128.0, cen[:, 2] - 128.0)
            changed = False
            small = [i for i in range(k) if frac[i] < 0.003 or (frac[i] < 0.012 and chroma[i] < 22.0)]
            mix = []
            for c in range(k):
                if chroma[c] >= 28.0:
                    continue
                for a in range(k):
                    for b in range(a + 1, k):
                        if c in (a, b):
                            continue
                        dab = float(np.linalg.norm(cen[a] - cen[b]))
                        if dab > 20 and float(np.linalg.norm(cen[a] - cen[c]) +
                                              np.linalg.norm(cen[c] - cen[b])) < 1.06 * dab                                 and frac[c] < 0.12:
                            mix.append(c)
            if mix and k > 2:
                cen = np.delete(cen, min(mix, key=lambda i: frac[i]), 0)
                changed = True
            elif small and k > 2:
                cen = np.delete(cen, min(small, key=lambda i: frac[i]), 0)
                changed = True
            elif k > 2:
                best, bd = None, 12.0
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
        cen = cen[np.argsort(cen[:, 0])]
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
        sm = np.stack([cv2.GaussianBlur(prob[:, :, k].astype(np.float32), (0, 0), sig)
                       for k in range(n)], -1)
        labels = np.argmax(sm, -1).astype(np.int32)

    rgb_c = cv2.cvtColor(np.clip(cen, 0, 255).reshape(1, n, 3).astype(np.uint8),
                         cv2.COLOR_LAB2RGB).reshape(n, 3)
    return labels, [tuple(int(v) for v in q) for q in rgb_c]
