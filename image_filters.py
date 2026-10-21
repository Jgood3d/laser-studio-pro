"""Filtres d'image purs (Pillow uniquement, sans Qt) utilisés par le traitement photo."""
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
