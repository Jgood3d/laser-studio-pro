"""Filtres d'image purs (Pillow, numpy, scipy ; sans Qt) utilisés par le traitement photo."""
import numpy as np
from PIL import ImageFilter

SHARPNESS_MAX = 100


def sharpen_radius(lines_per_mm=None):
    """Rayon du filtre en pixels : proportionnel à la résolution de gravure (~0,2 mm de détail), borné.
    Sans résolution connue (vignettes de comparaison) : 1 pixel."""
    if not lines_per_mm or lines_per_mm <= 0:
        return 1.0
    return min(max(0.2 * float(lines_per_mm), 0.8), 4.0)


def sharpen_image(img, amount, lines_per_mm=None):
    """Accentuation (masque flou) d'une image en niveaux de gris.

    amount : 0 (aucun effet, l'image est renvoyée telle quelle) à 100 (très marqué).
    Se règle AVANT le tramage : un contour net donne des points mieux répartis, donc une gravure plus
    lisible, surtout sur les petits détails (visages, texte)."""
    amount = max(0.0, min(float(amount), float(SHARPNESS_MAX)))
    if amount <= 0:
        return img
    return img.filter(ImageFilter.UnsharpMask(radius=sharpen_radius(lines_per_mm),
                                              percent=int(round(amount * 3)), threshold=0))


# -- Effet bande dessinée (à la manière du filtre « Bande dessinée » de GIMP / gegl:cartoon) ---------------

CARTOON_RADIUS_MAX_MM = 5.0      # rayon du masque, en mm sur la pièce gravée
CARTOON_BLACK_DEFAULT = 20       # pourcentage de noir par défaut
# Rayon du flou « détail » (mm) : la valeur du pixel, débarrassée du grain.
_CARTOON_DETAIL_MM = 0.1


def cartoon_filter(arr, radius_px, black_percent, detail_px=1.0):
    """Effet bande dessinée sur une image en niveaux de gris (tableau float 0–255) : les pixels nettement
    plus sombres que leur voisinage (le bord des traits) sont noircis, le reste est gardé.

    Chaque pixel (légèrement adouci, `detail_px`) est comparé à la moyenne de son voisinage (flou de rayon
    `radius_px`, le « rayon du masque ») : écart relatif = 1 − pixel / voisinage. Le seuil est choisi pour
    que `black_percent` % de l'image soit au-delà : ces pixels deviennent noirs, les écarts plus petits
    assombrissent en proportion. Renvoie un nouveau tableau float ; l'image d'entrée n'est pas modifiée."""
    from scipy.ndimage import gaussian_filter     # importé ici : scipy n'est chargé qu'à la première utilisation

    arr = np.asarray(arr, dtype=np.float32)
    black = max(0.0, min(float(black_percent), 100.0)) / 100.0
    if radius_px <= 0 or black <= 0 or arr.size == 0:
        return arr.copy()
    detail = gaussian_filter(arr, sigma=max(float(detail_px), 0.5) / 2.0)
    local = gaussian_filter(arr, sigma=max(float(radius_px), float(detail_px)) / 2.0)
    darker = np.zeros_like(arr)
    np.divide(local - detail, local, out=darker, where=local > 1e-6)       # 1 − pixel / voisinage
    darker = np.clip(darker, 0.0, 1.0)
    ramp = float(np.quantile(darker, 1.0 - black))
    if ramp <= 0.0:
        # Moins de `black_percent` % de pixels plus sombres que leur voisinage : seuls ceux-là noircissent.
        return np.where(darker > 0, 0.0, arr).astype(np.float32)
    factor = 1.0 - np.minimum(darker, ramp) / ramp
    return (arr * factor).astype(np.float32)


def cartoon_radius_px(radius_mm, lines_per_mm):
    """Rayon du masque en pixels de l'image gravée (`lines_per_mm` pixels par mm)."""
    return max(0.0, float(radius_mm)) * float(lines_per_mm or 0)


def cartoon_detail_px(lines_per_mm):
    return max(_CARTOON_DETAIL_MM * float(lines_per_mm or 0), 0.5)
