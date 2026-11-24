"""QR code gravé ou découpé : contenu, matrice, masques, vérification de lecture.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import cv2
import numpy as np


def qr_payload(p):
    """Texte encodé dans le QR code (lien / texte libre, ou Wi-Fi au format standard)."""
    if p.qr_kind == "wifi":
        esc = lambda s: "".join("\\" + ch if ch in '\\;,:"' else ch for ch in str(s or ""))
        sec = p.qr_sec if p.qr_sec in ("WPA", "WEP", "nopass") else "WPA"
        pw = "" if sec == "nopass" else f"P:{esc(p.qr_pass)};"
        return f"WIFI:T:{sec};S:{esc(p.qr_ssid)};{pw};"
    return str(p.qr_text or "")


def qr_matrix(text, ec="Q"):
    """Matrice booléenne (True = module sombre) sans marge, via l'encodeur QR d'OpenCV. Lève ValueError."""
    if not text:
        raise ValueError("empty")
    if not hasattr(cv2, "QRCodeEncoder"):
        raise ValueError("OpenCV too old (QRCodeEncoder)")
    lv = {"L": "CORRECT_LEVEL_L", "M": "CORRECT_LEVEL_M", "Q": "CORRECT_LEVEL_Q", "H": "CORRECT_LEVEL_H"}[ec if ec in "LMQH" else "Q"]
    prm = cv2.QRCodeEncoder_Params()
    prm.correction_level = getattr(cv2, "QRCodeEncoder_" + lv)
    try:
        im = cv2.QRCodeEncoder.create(prm).encode(text)
    except cv2.error as e:
        raise ValueError("text too long for a QR code") from e
    if im is None or im.ndim != 2 or im.shape[0] < 25:
        raise ValueError("encoding failed")
    ys, xs = np.nonzero(im == 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return im[y0:y1, x0:x1] == 0


def qr_masks(h, w, p, ppm):
    """Masques d'un QR code centré dans l'image : (raw = matière à découper, marks = zones gravées, info, geo).
    engrave : plaque pleine + modules gravés ; cut : modules ajourés (matière = modules sombres, marge claire ajourée)."""
    info = {}
    M = qr_matrix(qr_payload(p), p.qr_ec)
    n = M.shape[0]
    side = float(p.qr_side_mm) * ppm
    qzm = 2.0                                           # marge ajourée du mode « cut » (en modules)
    need = side * (n + 2 * qzm) / n
    lim = 0.96 * min(h, w)
    if need > lim:
        side *= lim / need
        info["qr_clamped"] = True
    S = max(n, int(round(side)))
    cell = S / n
    x0, y0 = (w - S) // 2, (h - S) // 2
    big = cv2.resize(M.astype(np.uint8), (S, S), interpolation=cv2.INTER_NEAREST)
    Dm = np.zeros((h, w), np.uint8)
    Dm[y0:y0 + S, x0:x0 + S] = big
    R = np.zeros((h, w), np.uint8)
    R[y0:y0 + S, x0:x0 + S] = 1
    q = int(round(qzm * cell))
    Q = np.zeros((h, w), np.uint8)
    Q[max(0, y0 - q):y0 + S + q, max(0, x0 - q):x0 + S + q] = 1
    inv = bool(p.qr_invert)
    if p.qr_mode == "cut":
        holes = Dm if inv else (Q & (1 - Dm))
        raw, marks = (1 - holes).astype(np.uint8), None
    else:
        marks = (R & (1 - Dm)) if inv else Dm
        raw = np.ones((h, w), np.uint8)
    mod_mm = cell / ppm
    info.update(qr_modules=int(n), qr_module_mm=round(mod_mm, 2))
    lo = 1.5 if p.qr_mode == "cut" else 0.8
    if mod_mm < lo:
        info["qr_small"] = True
    return raw, marks, info, dict(x0=x0, y0=y0, S=S, q=q, n=n, text=qr_payload(p))


def qr_scan_check(img_black, geo):
    """Relit le QR rendu (img_black : 1 = noir) comme un téléphone. Retourne 'ok' | 'inverted' | 'fail'."""
    h, w = img_black.shape
    x0, y0, S, n = geo["x0"], geo["y0"], geo["S"], geo["n"]
    cell = S / n
    crop = img_black[y0:y0 + S, x0:x0 + S]           # seulement les modules : les ponts de la marge ne comptent pas
    f = max(1, int(np.ceil(10.0 / max(cell, 1e-6))))
    pic = np.where(crop > 0, 0, 255).astype(np.uint8)
    pic = cv2.copyMakeBorder(pic, int(4 * cell), int(4 * cell), int(4 * cell), int(4 * cell), cv2.BORDER_CONSTANT, value=255)
    if f > 1:
        pic = cv2.resize(pic, None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
    det = cv2.QRCodeDetector()
    try:
        if det.detectAndDecode(pic)[0] == geo["text"]:
            return "ok"
        if det.detectAndDecode(255 - pic)[0] == geo["text"]:
            return "inverted"
    except cv2.error:
        pass
    return "fail"
