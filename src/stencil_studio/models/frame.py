"""Cadre de découpe sur la photo, comme la page web le calcule (curAspect, frameDims, clampFrame, getFrame de
ui/studio.html) : rapport largeur / hauteur d'après la forme et le format, cadre centré et contenu dans la photo.

    frame = centered_frame(state, 1600, 1200)       # {"cx", "cy", "w", "aspect", "full", "free", "rot"}

shortcut: placement libre et rotation du cadre (réglages « free » et « rot ») pas encore repris : cadre centré,
non tourné ; à reprendre quand la fenêtre Qt saura déplacer le cadre.
"""


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
    """Image complète (format « full », hors cercle) : le cadre prend toute la photo."""
    return state.get("shape") != "circle" and state.get("aspect") == "full"


def centered_frame(state, iw, ih, width=1.0):
    """Cadre centré sur la photo de `iw` × `ih` px, de largeur `width` (fraction de la photo) ramenée dans la
    photo (frameDims puis clampFrame, placement non libre), au format de la demande (getFrame)."""
    a = aspect(state, iw, ih)
    fw = width * iw
    fh = fw / a
    if fh > ih:
        fh, fw = ih, ih * a
    if fw > iw:
        fw, fh = iw, iw / a
    w = fw / iw
    cx = min(max(0.5, fw / 2 / iw), 1 - fw / 2 / iw)
    cy = min(max(0.5, fh / 2 / ih), 1 - fh / 2 / ih)
    return {"cx": cx, "cy": cy, "w": w, "aspect": a, "full": is_full(state), "free": False, "rot": 0}
