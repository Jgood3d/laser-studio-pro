"""Cadre de découpe sur la photo, comme la page web le calcule (curAspect, isFull, freeOn, frameDims, clampFrame,
getFrame de ui/studio.html). Le cadre est {"cx", "cy", "w"} : centre et largeur en fractions de la photo.

    f = clamp(state, 1600, 1200, {"cx": 0.5, "cy": 0.5, "w": 1.0})
    request_frame(state, 1600, 1200, f)            # {"cx", "cy", "w", "aspect", "full", "free", "rot"}
    centered_frame(state, 1600, 1200)              # les deux à la fois, cadre de départ
"""
import math


def aspect(state, iw, ih):
    """Rapport largeur / hauteur du cadre (curAspect)."""
    if state.get("shape") == "circle":
        return 1.0
    if state.get("aspect") == "custom":
        w, h = float(state.get("custom_w") or 1), float(state.get("custom_h") or 1)
        return max(0.1, min(10.0, w / h))
    if state.get("aspect") == "full":
        return iw / ih if iw and ih else 1.0
    return float(state.get("aspect") or 1)


def is_full(state):
    """Image complète (format « full », hors cercle) : le cadre prend toute la photo (isFull)."""
    return state.get("shape") != "circle" and state.get("aspect") == "full"


def rotation(state):
    return 0.0 if is_full(state) else float(state.get("rot") or 0)


def free_on(state):
    """Placement libre : demandé, ou cadre tourné ; le cadre peut alors déborder de la photo (freeOn)."""
    return (bool(state.get("free")) or rotation(state) != 0) and not is_full(state)


def dims(state, iw, ih, f):
    """Largeur et hauteur du cadre en pixels de la photo (frameDims)."""
    a = aspect(state, iw, ih)
    fw = f["w"] * iw
    fh = fw / a
    if free_on(state):
        return fw, fh
    if fh > ih:
        fh, fw = ih, ih * a
    if fw > iw:
        fw, fh = iw, iw / a
    return fw, fh


def clamp(state, iw, ih, f):
    """Cadre ramené dans ses limites (clampFrame) : contenu dans la photo, ou largeur de 0,05 à 10 et centre
    dans la photo en placement libre. Renvoie un nouveau cadre."""
    if free_on(state):
        return {"cx": min(max(f["cx"], 0.0), 1.0), "cy": min(max(f["cy"], 0.0), 1.0),
                "w": min(10.0, max(0.05, f["w"]))}
    fw, fh = dims(state, iw, ih, f)
    return {"cx": min(max(f["cx"], fw / 2 / iw), 1 - fw / 2 / iw),
            "cy": min(max(f["cy"], fh / 2 / ih), 1 - fh / 2 / ih),
            "w": fw / iw}


def request_frame(state, iw, ih, f):
    """Cadre tel que la page l'envoie au calcul (getFrame)."""
    return {"cx": f["cx"], "cy": f["cy"], "w": f["w"], "aspect": aspect(state, iw, ih), "full": is_full(state),
            "free": free_on(state), "rot": rotation(state)}


def centered_frame(state, iw, ih, width=1.0):
    """Cadre de départ (chargement d'une image) : centré, de largeur `width`, ramené dans ses limites."""
    return request_frame(state, iw, ih, clamp(state, iw, ih, {"cx": 0.5, "cy": 0.5, "w": width}))


def frame_width_mm(state, iw, ih):
    """Largeur du cadre sur la plaque, en mm (frameWidthMm) : la taille vaut pour le plus grand côté."""
    return float(state.get("size_mm") or 100) * min(1.0, aspect(state, iw, ih))


def image_width_mm(state, iw, ih, f):
    """Largeur de toute la photo une fois placée sur la plaque (syncImgMm), arrondie au dixième de mm."""
    return round(frame_width_mm(state, iw, ih) / f["w"] * 10) / 10


def width_for_image_mm(state, iw, ih, mm):
    """Largeur du cadre (fraction de la photo) qui donne à la photo `mm` de large sur la plaque."""
    return frame_width_mm(state, iw, ih) / max(10.0, float(mm))


def unit_polygon(shape):
    """Contour d'une forme (heart, star, tree) dans le carré unité, mêmes formules que la page (unitPoly) et que
    core : pour dessiner le cadre."""
    if shape == "tree":
        half = [(0.5, 0), (0.70, 0.30), (0.60, 0.30), (0.82, 0.58), (0.70, 0.58), (0.96, 0.86), (0.58, 0.86),
                (0.58, 1.0)]
        return half + [(1 - x, y) for x, y in reversed(half)]
    if shape == "heart":
        pts = []
        for i in range(200):
            t = i / 200 * 2 * math.pi
            pts.append((16 * math.sin(t) ** 3,
                        -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))))
    else:
        pts = [((0.42 if k % 2 else 1) * math.cos(-math.pi / 2 + k * math.pi / 5),
                (0.42 if k % 2 else 1) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return [((x - x0) / (x1 - x0), (y - y0) / (y1 - y0)) for x, y in pts]
