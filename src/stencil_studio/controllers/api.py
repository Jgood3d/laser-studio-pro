"""API de calcul de Stencil Studio : ce que la page web demande au serveur
(aperçu, détection du visage, export), sur l'image de la session.

    api = StudioApi(StudioSession())
    api.session.load_image(data, "photo.jpg")
    api.preview({"params": {...}, "frame": {...}, "seq": 1, "view": "result"})
    api.export({"params": {...}, "frame": {...}, "what": "box"})

Un seul calcul à la fois (verrou) ; un aperçu dépassé par une demande plus
récente n'est pas calculé (« stale »). Le dernier résultat est gardé en
cache tant que la demande ne change pas.
"""
import base64
import io
import json
import os
import threading
import types

import cv2
import numpy as np
from PIL import Image

from .. import core, lightbox, subject_ai

GRAB_SIZE = 700  # résolution interne de GrabCut (px, grand côté)


def parse_sbox(raw):
    """Rectangle du sujet {x,y,w,h} en fractions de l'image -> tuple valide ou None."""
    try:
        x, y, w, h = (float(raw[k]) for k in ("x", "y", "w", "h"))
    except (TypeError, KeyError, ValueError):
        return None
    x, y = max(0.0, min(1.0, x)), max(0.0, min(1.0, y))
    w, h = min(w, 1.0 - x), min(h, 1.0 - y)
    if w < 0.02 or h < 0.02:
        return None
    return (round(x, 4), round(y, 4), round(w, 4), round(h, 4))


def parse_manual(raw):
    """Ponts manuels [[x1,y1,x2,y2], ...] (fractions 0..1 du résultat) -> liste valide."""
    out = []
    for seg in (raw or [])[:400]:
        try:
            v = [min(1.0, max(0.0, float(t))) for t in seg[:4]]
        except (TypeError, ValueError):
            continue
        if len(v) == 4:
            out.append([round(t, 4) for t in v])
    return out


def parse_guides(raw):
    """Guides low poly {pts:[[x,y]], edges:[[x1,y1,x2,y2]]} (fractions 0..1) -> dict valide ou None."""
    if not isinstance(raw, dict):
        return None

    def clean(lst, n):
        out = []
        for q in (lst or [])[:300]:
            try:
                v = [round(min(1.0, max(0.0, float(t))), 4) for t in q[:n]]
            except (TypeError, ValueError):
                continue
            if len(v) == n:
                out.append(v)
        return out
    pts, edges = clean(raw.get("pts"), 2), clean(raw.get("edges"), 4)
    return {"pts": pts, "edges": edges} if (pts or edges) else None


def png_data_url(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def version_info(req):
    """Infos de version renvoyées à l'interface (détecte les fichiers de versions mélangées)."""
    return {"version": core.VERSION, "ignored": core.Params.unknown_keys(req.get("params"))}


class StudioApi:
    def __init__(self, session):
        self.session = session
        self.cache = types.SimpleNamespace(sig=None, result=None, subj_key=None, subject=None, subj_full=False,
                                           ai_used=False)
        self.lock = threading.Lock()      # un seul calcul à la fois
        self._meta = threading.Lock()
        self._latest = 0                  # dernier numéro de requête d'aperçu reçu

    # -- image et repères (appelés sous self.lock par le serveur)

    def load_image(self, data, name):
        self.session.load_image(data, name)
        self.cache.sig = self.cache.subj_key = None

    def set_hints(self, png_bytes):
        self.session.set_hints(png_bytes)

    # -- calcul

    def subject_mask(self, box, margin, shape_hw, moving, sbox=None, rot=0.0, ai=False):
        """Masque du sujet (0/1) pour le cadre `box`.
        - avec repères peints et/ou rectangle du sujet : calculé UNE fois sur la photo entière
          (le cadre peut bouger sans recalcul) ;
        - sans rien : calculé sur le cadre (rectangle de recherche = cadre moins la marge)."""
        s, cache = self.session, self.cache
        m = max(0.0, min(0.4, margin))
        has_hints = s.has_hints()
        use_full = has_hints or sbox is not None
        rect = sbox if sbox is not None else (m, m, 1 - 2 * m, 1 - 2 * m)
        if use_full:
            key = (s.img_id, round(m, 3), s.hints_ver if has_hints else 0, sbox)
        else:
            key = (s.img_id, round(m, 3), box, rot)
        key = key + (bool(ai) and not use_full,)
        if cache.subj_key != key:
            if moving and not use_full:
                return None  # pendant le glissement : pas de calcul lent
            got = None
            if ai and not use_full:          # IA : seulement quand l'utilisateur n'a rien dessiné
                got = core.ai_mask(core.crop_resize(s.img, box, 500, rot))
            cache.ai_used = got is not None
            if got is not None:
                cache.subject = got
            elif use_full:
                cache.subject = core.remove_background(s.disp_rgb, rect, s.hints, size=GRAB_SIZE)
            else:
                small = core.crop_resize(s.img, box, 500, rot)
                cache.subject = core.remove_background(small, rect, None, size=500)
            cache.subj_key, cache.subj_full = key, use_full
        mask = cache.subject
        if cache.subj_full and rot and float(rot) % 360 != 0:      # cadre tourné : on échantillonne le masque de la photo
            W, H = s.img.size
            dw, dh = s.disp_size
            mx, my = core.rot_maps(box, shape_hw, float(rot))
            up = cv2.remap(mask.astype(np.uint8) * 255, mx * dw / W, my * dh / H, cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            return (up > 127).astype(np.uint8)
        if cache.subj_full:
            W, H = s.img.size
            dw, dh = s.disp_size
            l, t, r, b = box
            h, w = shape_hw
            if l < 0 or t < 0 or r > W or b > H:   # cadre qui déborde de la photo : hors photo = pas de sujet
                M = np.array([[(r - l) / w * dw / W, 0, l * dw / W], [0, (b - t) / h * dh / H, t * dh / H]], np.float64)
                up = cv2.warpAffine(mask.astype(np.uint8) * 255, M, (w, h),
                                    flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=0)
                return (up > 127).astype(np.uint8)
            dl, dt = int(l * dw / W), int(t * dh / H)
            dr, db = max(dl + 1, int(round(r * dw / W))), max(dt + 1, int(round(b * dh / H)))
            mask = mask[dt:db, dl:dr]
        h, w = shape_hw
        up = cv2.resize(mask.astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_LINEAR)
        return (up > 127).astype(np.uint8)

    def compute(self, req, work):
        """Résultat (core.Result) de la demande `req` à la résolution `work`, depuis le cache si inchangée."""
        s, cache = self.session, self.cache
        p = core.Params.from_dict(req.get("params"))
        fr = req.get("frame", {})
        isolate = bool(req.get("isolate"))
        margin = float(req.get("margin", 0.03))
        moving = bool(req.get("moving"))
        sbox = parse_sbox(req.get("box")) if isolate else None
        W, H = s.img.size
        box = core.frame_box(W, H, fr)
        rot = 0.0 if fr.get("full") else float(fr.get("rot", 0) or 0) % 360
        pd = {k: v for k, v in p.to_dict().items()
              if not k.startswith("box_")}   # le caisson ne change pas le résultat
        mbr = parse_manual(req.get("mbr"))
        lpg = parse_guides(req.get("lpg")) if p.output == "lowpoly" else None
        sig = json.dumps([s.img_id, box, rot, work, pd, isolate, round(margin, 3),
                          s.hints_ver if isolate else 0, moving and isolate, sbox, mbr, lpg], sort_keys=True)
        if cache.sig == sig:
            return cache.result
        rgb = core.crop_resize(s.img, box, work, rot)
        subject = self.subject_mask(box, margin, rgb.shape[:2], moving, sbox, rot, bool(p.ai_subject)) if isolate else None
        failed = False
        if subject is not None and subject.mean() < 0.01:
            subject, failed = None, True  # détection ratée (sujet quasi vide) : on n'applique pas le masque
        res = core.process(rgb, p, subject, core.valid_mask(box, W, H, rgb.shape[:2], rot), manual=mbr, guides=lpg)
        if isolate:
            res.stats["subject_pct"] = None if subject is None else round(100.0 * float(subject.mean()), 1)
            res.stats["subject_failed"] = failed
            res.stats["ai_used"] = bool(cache.ai_used)
            if p.ai_subject and not cache.ai_used and sbox is None and not s.has_hints():
                res.stats["ai_missing"] = (subject_ai.last_error()
                                           or ("onnxruntime" if not subject_ai.has_runtime() else "")) or None
                res.stats["ai_install"] = subject_ai.install_command()
        cache.sig, cache.result = sig, res
        return res

    # -- requêtes de la page

    def preview(self, req):
        seq = int(req.get("seq", 0))
        with self._meta:
            self._latest = max(self._latest, seq)
        with self.lock:
            if seq < self._latest:
                return {"stale": True}
            res = self.compute(req, int(req.get("work", 640)))
            view = req.get("view", "result")
            style = dict(req.get("style") or {})
            stats = dict(res.stats)
            if view in ("box", "assembled") and res.layers is None:
                p = core.Params.from_dict(req.get("params"))
                style["params"] = p
                stats["box"] = lightbox.summary(lightbox.make_box(res, p))
            return {"seq": seq, "image": png_data_url(core.render_view(res, view, style)),
                    "stats": stats, **version_info(req)}

    def face(self):
        with self.lock:
            if self.session.disp_rgb is None:
                return {"error": "no image"}
            f = core.detect_face(self.session.disp_rgb)
            return {"face": list(f) if f else None}

    def export(self, req):
        with self.lock:
            res = self.compute(req, int(req.get("work", 1200)))
            params = core.Params.from_dict(req.get("params"))
            fr = core.polys_bbox(res.polys_mm) if params.export_frame else None
            out = {"svg": core.svg_string(res.polys_mm, res.w_mm, res.h_mm, fr, res.marks_polys, res.layer_polys,
                                          res.layer_colors),
                   "dxf": core.dxf_string(res.polys_mm, res.h_mm, frame=fr, marks=res.marks_polys, layers=res.layer_polys),
                   "stats": res.stats,
                   "name": os.path.splitext(self.session.name)[0]}
            if res.engrave is not None:   # gravure : image tramée à la bonne résolution + SVG avec image
                out["png_b64"] = base64.b64encode(core.engrave_png_bytes(res)).decode()
                out["svg_image"] = core.svg_engrave_string(res)
            if req.get("what") == "flextest":
                fb = lightbox.make_flex_test(params)
                out["flex_svg"], out["flex_dxf"] = lightbox.flex_test_svg(fb), lightbox.flex_test_dxf(fb)
                out["flex_info"] = [round(fb["sheet"][0], 1), round(fb["sheet"][1], 1), len(fb["layout"])]
            if req.get("what") == "box":
                box = lightbox.make_box(res, params)
                ef = params.export_frame
                out["box_svg"], out["box_dxf"] = lightbox.box_svg_string(box, ef), lightbox.box_dxf_string(box, ef)
                out["box_summary"] = lightbox.summary(box)
                out["diffuser_svg"] = lightbox.diffuser_svg_string(box)
                pdf = lightbox.diffuser_pdf_bytes(box, req.get("lang") or "fr")
                if pdf:
                    out["diffuser_pdf_b64"] = base64.b64encode(pdf).decode()
            return out
