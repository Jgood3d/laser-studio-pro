"""Gravure : image tramée à la résolution de la machine et contour de découpe, rendus et exports.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import time
import cv2
import numpy as np
from PIL import Image

from .params import Result
from .framing import fill_outside
from .tones import tone_gray
from .plate import _pad_img, decorate, effective_ring, extract_contours, shape_inside, text_supported
from .render import _sheet_mask


def engrave_result(rgb, p, subject=None, valid=None):
    try:
        from .. import engrave as E
    except ImportError:
        import engrave as E
    t0 = time.time()
    h, w = rgb.shape[:2]
    ppm = max(h, w) / p.size_mm
    if subject is not None and subject.shape != (h, w):
        subject = cv2.resize(subject, (w, h), interpolation=cv2.INTER_NEAREST)
    gray = tone_gray(fill_outside(rgb, valid), p.tone_source)
    if p.contrast:
        gray = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(gray)
    if subject is not None:
        gray = np.where(subject > 0, gray, 255).astype(np.uint8)
    inside = shape_inside(p.shape, h, w)
    ring_mm = effective_ring(p)
    has_text = text_supported(p) and bool((p.text_top or "").strip() or (p.text_bottom or "").strip())
    plate, pad, tab, dinfo = decorate(inside.copy(), inside, p, ppm, ring_mm)
    base = _pad_img(inside, pad)
    sheet = _pad_img(_sheet_mask(p.shape, h, w), pad)
    base_sheet = sheet.copy()      # forme seule, sans la languette de l'œillet (pour le caisson)
    if tab is not None:
        sheet = sheet | tab
    gray = _pad_img(gray, pad, 255)
    rgb = _pad_img(rgb, pad, (255, 255, 255))
    subj = None if subject is None else _pad_img(subject, pad)
    # zone gravée : à l'intérieur de la pièce, à distance du bord (ou de l'anneau si texte)
    border = (ring_mm if has_text else p.eng_border_mm) * ppm
    d = cv2.distanceTransform(cv2.copyMakeBorder(base, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1]
    area = (d >= max(0.0, border)) & (base > 0)
    if valid is not None:
        area &= _pad_img(valid, pad) > 0
    H2, W2 = plate.shape
    w_mm, h_mm = W2 / ppm, H2 / ppm
    tw, th = max(8, int(round(w_mm / 25.4 * p.eng_dpi))), max(8, int(round(h_mm / 25.4 * p.eng_dpi)))
    g = np.where(area, gray, 255).astype(np.float32)
    g = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA if tw < W2 else cv2.INTER_CUBIC)
    md = cv2.resize(area.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST) > 0
    g = E.prepare_gray(g, p.eng_brightness, p.eng_contrast, p.eng_gamma)
    if p.eng_sharpen > 0:
        sg = max(0.8, 0.35 / 25.4 * p.eng_dpi)
        g = np.clip(g + float(p.eng_sharpen) * (g - cv2.GaussianBlur(g, (0, 0), sg)), 0, 255)
    if p.eng_invert:
        g = 255.0 - g
    g[~md] = 255.0
    bits = E.dither(g, p.eng_dither, p.eng_levels)
    bits[~md] = 255
    k = ppm / 12.0
    polys_mm = [q / ppm for q in extract_contours(plate, p.smooth * k, p.simplify * k)]
    length = sum(float(np.sum(np.hypot(*np.diff(np.vstack([q, q[:1]]), axis=0).T))) for q in polys_mm)
    cover = 100.0 * float(1.0 - bits[md].mean() / 255.0) if md.any() else 0.0
    holes = [(x / ppm, y / ppm, r / ppm) for x, y, r in dinfo.pop("hang_holes", [])]
    stats = dict(threshold=0.0, contours=len(polys_mm), length_mm=length, linked=0, dropped=0,
                 w_mm=w_mm, h_mm=h_mm, px=[W2, H2], eng_px=[tw, th], eng_dpi=p.eng_dpi,
                 eng_cover=round(cover, 1), eng_minutes=round(E.estimate_minutes(h_mm, w_mm, p.eng_dpi, p.eng_speed), 1),
                 seconds=round(time.time() - t0, 2), **dinfo)
    gray = _pad_img(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (0, 0, 0, 0))
    return Result(rgb, gray, subj, plate, plate, np.zeros_like(plate), polys_mm, w_mm, h_mm, stats, sheet,
                  engrave=bits, eng_dpi=float(p.eng_dpi), tab=tab, hang_holes=holes, base_sheet=base_sheet)


def engrave_png_bytes(res):
    import io
    buf = io.BytesIO()
    Image.fromarray(res.engrave).save(buf, "PNG", dpi=(res.eng_dpi, res.eng_dpi))
    return buf.getvalue()


def svg_engrave_string(res):
    """SVG à la bonne échelle (mm) : image tramée incrustée + contours de découpe (calque CUT)."""
    import base64
    b64 = base64.b64encode(engrave_png_bytes(res)).decode()
    paths = "\n".join('<path d="M' + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + ' Z"/>' for q in res.polys_mm)
    W, H = res.w_mm, res.h_mm
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">\n'
            f'<image id="ENGRAVE" x="0" y="0" width="{W:.3f}" height="{H:.3f}" preserveAspectRatio="none" '
            f'xlink:href="data:image/png;base64,{b64}" href="data:image/png;base64,{b64}"/>\n'
            f'<g id="CUT" fill="none" stroke="#ff0000" stroke-width="0.1">\n{paths}\n</g>\n</svg>\n')
