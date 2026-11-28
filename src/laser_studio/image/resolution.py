"""Résolution de gravure d'une image : lignes/mm, DPI, focale du laser, et
qualité de l'écart entre les lignes par rapport à la taille du spot. Sans Qt.

    lmm = dpi_to_lmm(254)                  # 10 lignes/mm
    quality = resolution_quality(0.1, 15)  # écart de 0,067 mm pour un spot de 0,1 mm : trop fin
"""

MM_PER_INCH = 25.4
DEFAULT_FOCAL_MM = 0.1


def dpi_to_lmm(dpi):
    """1 pouce = 25,4 mm : lignes/mm = DPI / 25,4."""
    return dpi / MM_PER_INCH


def lmm_to_dpi(lmm):
    return lmm * MM_PER_INCH


def focal_to_lmm(focal_mm):
    """Lignes/mm calées sur la taille du spot (une ligne par largeur de
    spot) ; un spot nul ou négatif compte pour DEFAULT_FOCAL_MM."""
    if focal_mm <= 0:
        focal_mm = DEFAULT_FOCAL_MM
    return 1.0 / focal_mm


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


# En dessous de ce rapport écart / focale, on prévient (réglage trop fin).
WARN_BELOW_RATIO = 0.9


def resolution_quality(focal_mm, lmm):
    """Classement de l'écart entre lignes, en multiples de la focale (seuils
    calés sur un tableau de référence à 5 zones) :
    (écart en mm, rapport écart / focale, clé du texte, couleur), ou None si
    la focale ou les lignes/mm ne sont pas positives."""
    if focal_mm <= 0 or lmm <= 0:
        return None
    spacing = 1.0 / lmm
    ratio = spacing / focal_mm
    if ratio < 0.6:
        key, color = "image.quality_too_fine", "#e05656"      # forte surgravure, risque de brûlure
    elif ratio < 0.9:
        key, color = "image.quality_fine", "#e0a656"          # surgravure probable
    elif ratio < 1.25:
        key, color = "image.quality_fine_ok", "#999999"       # fin mais correct
    elif ratio <= 2.25:
        key, color = "image.quality_recommended", "#56c271"   # zone recommandée
    else:
        key, color = "image.quality_coarse", "#999999"        # grossier mais correct
    return spacing, ratio, key, color
