#!/usr/bin/env python3
"""Laser Stencil Studio : interface locale dans le navigateur.

    py studio.py            -> ouvre http://127.0.0.1:8765
    py studio.py --port 9000 --no-browser

Rien n'est envoyé sur Internet : le serveur n'écoute que sur 127.0.0.1.
"""
import argparse
import base64
import io
import json
import os
import re
import socket
import sys
import threading
import traceback
import types
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
from PIL import Image

try:
    from . import core
except ImportError:
    import core
if not hasattr(core, "VERSION"):
    core.VERSION = "ancienne version / old version"
try:
    from .i18n import available_languages, detect_language, load_catalog
except ImportError:
    from i18n import available_languages, detect_language, load_catalog

HERE = os.path.dirname(os.path.abspath(__file__))
UI_NAME = "studio.html"  # page de l'interface (à côté de studio.py, ou dans web/)


def find_ui():
    for d in (HERE, os.path.join(HERE, "web")):
        path = os.path.join(d, UI_NAME)
        if os.path.isfile(path):
            return path
    return None


def check_versions():
    """Affiche les versions des fichiers et signale un mélange (ex. core.py ancien)."""
    ui = find_ui()
    ui_ver = "?"
    if ui:
        m = re.search(r'UI_VERSION = "([^"]+)"', open(ui, encoding="utf-8").read())
        ui_ver = m.group(1) if m else "ancienne version / old version"
    print(f"Versions : core.py {core.VERSION} | studio.html {ui_ver}")
    if ui_ver != core.VERSION:
        return [f"Fichiers de versions différentes / mixed versions : core.py={core.VERSION}, studio.html={ui_ver}. "
                "Remplacer TOUS les fichiers / replace ALL the files (core.py, studio.py, studio.html, i18n.py)."]
    return []


def check_files():
    """Messages clairs si des fichiers du programme manquent."""
    problems = []
    if find_ui() is None:
        problems.append(f"Fichier manquant / missing file : {UI_NAME}  (à placer à côté de studio.py)")
    for f in ("core.py", "i18n.py", "engrave.py", "lightbox.py"):
        if not os.path.isfile(os.path.join(HERE, f)):
            problems.append(f"Fichier manquant / missing file : {f}")
    return problems
DISPLAY_MAX = 1600  # taille maxi de l'image affichée / des repères peints

STATE = types.SimpleNamespace(img=None, name="image", disp_jpeg=b"", disp_size=(1, 1), disp_rgb=None,
                              hints=None, hints_ver=0, img_id=0)
CACHE = types.SimpleNamespace(sig=None, result=None, subj_key=None, subject=None, subj_full=False, ai_used=False)
GRAB_SIZE = 700  # résolution interne de GrabCut (px, grand côté)
LOCK = threading.Lock()     # un seul calcul à la fois
META = threading.Lock()
LATEST = [0]                # dernier numéro de requête d'aperçu reçu


def load_image(data, name):
    img = core.to_rgb(Image.open(io.BytesIO(data)))
    img.load()
    disp = img.copy()
    disp.thumbnail((DISPLAY_MAX, DISPLAY_MAX), Image.LANCZOS)
    buf = io.BytesIO()
    disp.save(buf, "JPEG", quality=90)
    STATE.img, STATE.name = img, name
    STATE.disp_jpeg, STATE.disp_size = buf.getvalue(), disp.size
    STATE.disp_rgb = np.array(disp)
    STATE.hints = np.zeros((disp.height, disp.width), np.uint8)
    STATE.hints_ver += 1
    STATE.img_id += 1
    CACHE.sig = CACHE.subj_key = None


def set_hints(png_bytes):
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    dw, dh = STATE.disp_size
    if im.size != (dw, dh):
        im = im.resize((dw, dh), Image.NEAREST)
    arr = np.array(im)
    STATE.hints = core.codes_from_rgb(arr[..., :3], arr[..., 3])
    STATE.hints_ver += 1


def subject_mask(box, margin, shape_hw, moving, sbox=None, rot=0.0, ai=False):
    """Masque du sujet (0/1) pour le cadre `box`.
    - avec repères peints et/ou rectangle du sujet : calculé UNE fois sur la photo entière
      (le cadre peut bouger sans recalcul) ;
    - sans rien : calculé sur le cadre (rectangle de recherche = cadre moins la marge)."""
    m = max(0.0, min(0.4, margin))
    has_hints = STATE.hints is not None and bool(STATE.hints.any())
    use_full = has_hints or sbox is not None
    rect = sbox if sbox is not None else (m, m, 1 - 2 * m, 1 - 2 * m)
    if use_full:
        key = (STATE.img_id, round(m, 3), STATE.hints_ver if has_hints else 0, sbox)
    else:
        key = (STATE.img_id, round(m, 3), box, rot)
    key = key + (bool(ai) and not use_full,)
    if CACHE.subj_key != key:
        if moving and not use_full:
            return None  # pendant le glissement : pas de calcul lent
        got = None
        if ai and not use_full:          # IA : seulement quand l'utilisateur n'a rien dessiné
            got = core.ai_mask(core.crop_resize(STATE.img, box, 500, rot))
        CACHE.ai_used = got is not None
        if got is not None:
            CACHE.subject = got
        elif use_full:
            CACHE.subject = core.remove_background(STATE.disp_rgb, rect, STATE.hints, size=GRAB_SIZE)
        else:
            small = core.crop_resize(STATE.img, box, 500, rot)
            CACHE.subject = core.remove_background(small, rect, None, size=500)
        CACHE.subj_key, CACHE.subj_full = key, use_full
    mask = CACHE.subject
    if CACHE.subj_full and rot and float(rot) % 360 != 0:      # cadre tourné : on échantillonne le masque de la photo
        W, H = STATE.img.size
        dw, dh = STATE.disp_size
        h, w = shape_hw
        mx, my = core.rot_maps(box, shape_hw, float(rot))
        up = cv2.remap(mask.astype(np.uint8) * 255, mx * dw / W, my * dh / H, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return (up > 127).astype(np.uint8)
    if CACHE.subj_full:
        W, H = STATE.img.size
        dw, dh = STATE.disp_size
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


def compute(req, work):
    p = core.Params.from_dict(req.get("params"))
    fr = req.get("frame", {})
    isolate = bool(req.get("isolate"))
    margin = float(req.get("margin", 0.03))
    moving = bool(req.get("moving"))
    sbox = parse_sbox(req.get("box")) if isolate else None
    W, H = STATE.img.size
    box = core.frame_box(W, H, fr)
    rot = 0.0 if fr.get("full") else float(fr.get("rot", 0) or 0) % 360
    pd = {k: v for k, v in p.to_dict().items()
          if not k.startswith("box_")}   # le caisson ne change pas le résultat
    mbr = parse_manual(req.get("mbr"))
    lpg = parse_guides(req.get("lpg")) if p.output == "lowpoly" else None
    sig = json.dumps([STATE.img_id, box, rot, work, pd, isolate, round(margin, 3),
                      STATE.hints_ver if isolate else 0, moving and isolate, sbox, mbr, lpg], sort_keys=True)
    if CACHE.sig == sig:
        return CACHE.result
    rgb = core.crop_resize(STATE.img, box, work, rot)
    subject = subject_mask(box, margin, rgb.shape[:2], moving, sbox, rot, bool(p.ai_subject)) if isolate else None
    failed = False
    if subject is not None and subject.mean() < 0.01:
        subject, failed = None, True  # détection ratée (sujet quasi vide) : on n'applique pas le masque
    res = core.process(rgb, p, subject, core.valid_mask(box, W, H, rgb.shape[:2], rot), manual=mbr, guides=lpg)
    if isolate:
        res.stats["subject_pct"] = None if subject is None else round(100.0 * float(subject.mean()), 1)
        res.stats["subject_failed"] = failed
        res.stats["ai_used"] = bool(CACHE.ai_used)
        if p.ai_subject and not CACHE.ai_used and sbox is None and not (STATE.hints is not None and STATE.hints.any()):
            try:
                import subject_ai as _sa
            except ImportError:
                from . import subject_ai as _sa
            res.stats["ai_missing"] = (_sa.last_error() or ("onnxruntime" if not _sa.has_runtime() else "")) or None
    CACHE.sig, CACHE.result = sig, res
    return res


def png_data_url(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def version_info(req):
    """Infos de version renvoyées à l'interface (détecte les fichiers de versions mélangées)."""
    return {"version": core.VERSION, "ignored": core.Params.unknown_keys(req.get("params"))}


def api_preview(req):
    seq = int(req.get("seq", 0))
    with META:
        LATEST[0] = max(LATEST[0], seq)
    with LOCK:
        if seq < LATEST[0]:
            return {"stale": True}
        res = compute(req, int(req.get("work", 640)))
        view = req.get("view", "result")
        style = dict(req.get("style") or {})
        stats = dict(res.stats)
        if view in ("box", "assembled"):
            try:
                from . import lightbox
            except ImportError:
                import lightbox
            p = core.Params.from_dict(req.get("params"))
            style["params"] = p
            stats["box"] = lightbox.summary(lightbox.make_box(res, p))
        return {"seq": seq, "image": png_data_url(core.render_view(res, view, style)),
                "stats": stats, **version_info(req)}


def api_face(req):
    with LOCK:
        if STATE.disp_rgb is None:
            return {"error": "no image"}
        f = core.detect_face(STATE.disp_rgb)
        return {"face": list(f) if f else None}


def api_export(req):
    with LOCK:
        res = compute(req, int(req.get("work", 1200)))
        fr = core.polys_bbox(res.polys_mm) if core.Params.from_dict(req.get("params")).export_frame else None
        out = {"svg": core.svg_string(res.polys_mm, res.w_mm, res.h_mm, fr, res.marks_polys),
               "dxf": core.dxf_string(res.polys_mm, res.h_mm, frame=fr, marks=res.marks_polys), "stats": res.stats,
               "name": os.path.splitext(STATE.name)[0]}
        if res.engrave is not None:   # gravure : image tramée à la bonne résolution + SVG avec image
            out["png_b64"] = base64.b64encode(core.engrave_png_bytes(res)).decode()
            out["svg_image"] = core.svg_engrave_string(res)
        if req.get("what") == "flextest":
            try:
                from . import lightbox
            except ImportError:
                import lightbox
            fb = lightbox.make_flex_test(core.Params.from_dict(req.get("params")))
            out["flex_svg"], out["flex_dxf"] = lightbox.flex_test_svg(fb), lightbox.flex_test_dxf(fb)
            out["flex_info"] = [round(fb["sheet"][0], 1), round(fb["sheet"][1], 1), len(fb["layout"])]
        if req.get("what") == "box":
            try:
                from . import lightbox
            except ImportError:
                import lightbox
            box = lightbox.make_box(res, core.Params.from_dict(req.get("params")))
            ef = core.Params.from_dict(req.get("params")).export_frame
            out["box_svg"], out["box_dxf"] = lightbox.box_svg_string(box, ef), lightbox.box_dxf_string(box, ef)
            out["box_summary"] = lightbox.summary(box)
            out["diffuser_svg"] = lightbox.diffuser_svg_string(box)
            pdf = lightbox.diffuser_pdf_bytes(box, req.get("lang") or "fr")
            if pdf:
                out["diffuser_pdf_b64"] = base64.b64encode(pdf).decode()
        return out


PRESETS_FILE = os.path.join(HERE, "presets.json")


def load_presets_file():
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            o = json.load(f)
        return o if isinstance(o, dict) else {}
    except (OSError, ValueError):
        return {}


def save_presets_file(obj):
    tmp = PRESETS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PRESETS_FILE)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # silence
        pass

    # -- helpers
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass  # le navigateur a annulé la requête (aperçu périmé)

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    # -- routes
    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html", "/" + UI_NAME):
                ui = find_ui()
                if ui is None:
                    self._send(404, f"{UI_NAME} introuvable / not found (voir la fenêtre de commande)",
                               "text/plain; charset=utf-8")
                else:
                    with open(ui, "rb") as f:
                        self._send(200, f.read(), "text/html; charset=utf-8")
            elif u.path == "/api/langs":
                self._send(200, {"langs": available_languages() or ["en"], "default": detect_language()})
            elif u.path == "/api/catalog":
                lang = parse_qs(u.query).get("lang", ["en"])[0]
                self._send(200, load_catalog(lang))
            elif u.path == "/api/presets":
                self._send(200, load_presets_file())
            elif u.path == "/api/image":
                if STATE.img is None:
                    self._send(404, {"error": "no image"})
                else:
                    self._send(200, STATE.disp_jpeg, "image/jpeg")
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            data = self._body()
            if u.path == "/api/upload":
                from urllib.parse import unquote
                name = unquote(self.headers.get("X-Filename", "image"))
                with LOCK:
                    load_image(data, name)
                W, H = STATE.img.size
                self._send(200, {"width": W, "height": H, "v": STATE.img_id})
            elif u.path == "/api/hints":
                if STATE.img is None:
                    self._send(400, {"error": "no image"})
                else:
                    with LOCK:
                        set_hints(data)
                    self._send(200, {"ok": True})
            elif u.path == "/api/presets":
                obj = json.loads(data.decode("utf-8"))
                if not isinstance(obj, dict):
                    self._send(400, {"error": "bad presets"})
                else:
                    save_presets_file(obj)
                    self._send(200, {"ok": True})
            elif u.path == "/api/face":
                self._send(200, api_face({}) if STATE.img is not None else {"error": "no image"})
            elif u.path in ("/api/preview", "/api/export"):
                if STATE.img is None:
                    self._send(400, {"error": "no image"})
                else:
                    req = json.loads(data.decode("utf-8"))
                    out = api_preview(req) if u.path == "/api/preview" else api_export(req)
                    self._send(200, out)
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": str(e)})


def free_port(preferred):
    for port in (preferred, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def start_server(port=0):
    """Démarre le serveur dans un thread (sans navigateur). Retourne (serveur, port) : pour l'intégrer dans une
    autre application (fenêtre Qt de Laser Studio Pro). Arrêt : serveur.shutdown(); serveur.server_close()."""
    port = free_port(port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, name="stencil-studio", daemon=True).start()
    return srv, port


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    problems = check_files() + check_versions()
    if problems:
        print("\n".join(["ATTENTION :"] + ["  - " + m for m in problems]))
        if find_ui() is None:
            return 1
    port = free_port(args.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"Laser Stencil Studio : {url}   (Ctrl+C pour quitter / to quit)")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
