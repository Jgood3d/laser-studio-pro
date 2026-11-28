"""Taille d'origine d'une image (sans Qt) à partir de la résolution (DPI) enregistrée dans le fichier."""

DEFAULT_DPI = 96.0       # sans indication dans le fichier : résolution d'écran courante (celle de Inkscape, Paint...)
MIN_VALID_DPI = 10.0     # en dessous (ex. 1 dpi écrit par certains outils), la valeur n'est pas une vraie résolution
MAX_VALID_DPI = 20000.0
MM_PER_INCH = 25.4


def read_dpi(info):
    """DPI horizontal lu dans le dictionnaire `info` de Pillow ; None si absent ou invalide."""
    value = None
    dpi = info.get("dpi")
    if dpi:
        value = dpi[0] if isinstance(dpi, (tuple, list)) else dpi
    else:
        unit, density = info.get("jfif_unit"), info.get("jfif_density")
        if density and unit in (1, 2):
            value = density[0] * (2.54 if unit == 2 else 1.0)     # unité 2 : points par centimètre
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if MIN_VALID_DPI <= value <= MAX_VALID_DPI else None


def natural_size_mm(width_px, height_px, dpi=None, max_w=None, max_h=None, default_dpi=DEFAULT_DPI):
    """(largeur mm, hauteur mm, dpi utilisés, réduite ?). Les proportions de l'image sont toujours conservées ;
    si max_w / max_h (zone de travail de la machine) sont donnés et que l'image est plus grande, elle est
    réduite pour y tenir."""
    used = dpi if dpi else default_dpi
    w_mm = width_px / used * MM_PER_INCH
    h_mm = height_px / used * MM_PER_INCH
    shrunk = False
    factor = 1.0
    if max_w and max_w > 0:
        factor = min(factor, max_w / w_mm)
    if max_h and max_h > 0:
        factor = min(factor, max_h / h_mm)
    if factor < 1.0:
        w_mm, h_mm, shrunk = w_mm * factor, h_mm * factor, True
    return max(w_mm, 0.1), max(h_mm, 0.1), used, shrunk
