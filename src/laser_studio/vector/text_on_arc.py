"""Texte sur un arc de cercle : position et rotation de chaque lettre (sans Qt).

Repère : mathématique, Y vers le haut, centre du cercle en (0, 0). Les angles sont en degrés, mesurés
depuis l'axe X dans le sens inverse des aiguilles d'une montre (90 = en haut, 270 = en bas).

Deux dispositions :
- extérieur : le texte est posé sur le dessus du cercle, le haut des lettres vers l'extérieur,
  lu dans le sens des aiguilles d'une montre (légende du haut d'une médaille) ;
- intérieur : le haut des lettres est tourné vers le centre, lu de gauche à droite en bas du cercle
  (légende du bas d'une médaille).
Dans les deux cas, la ligne de base du texte suit le cercle de rayon `radius_mm`.
"""
import math

DEFAULT_CENTER_OUTSIDE = 90.0
DEFAULT_CENTER_INSIDE = 270.0


def _wrap_deg(angle):
    """Ramène un angle dans ]-180, 180] (une lettre à 352° est à -8°)."""
    wrapped = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def default_center_deg(inside):
    """Angle où le texte est centré par défaut : en haut (extérieur) ou en bas (intérieur)."""
    return DEFAULT_CENTER_INSIDE if inside else DEFAULT_CENTER_OUTSIDE


def text_length(advances_mm, spacing_mm=0.0):
    """Longueur du texte sur la ligne de base : largeurs des lettres plus l'espacement entre elles."""
    if not advances_mm:
        return 0.0
    return float(sum(advances_mm)) + spacing_mm * (len(advances_mm) - 1)


def arc_span_deg(advances_mm, radius_mm, spacing_mm=0.0):
    """Angle couvert par le texte (peut dépasser 360° : les lettres se chevauchent alors)."""
    if radius_mm <= 0:
        raise ValueError("radius")
    return math.degrees(text_length(advances_mm, spacing_mm) / radius_mm)


def arc_placements(advances_mm, radius_mm, center_deg=None, inside=False, spacing_mm=0.0):
    """Pour chaque lettre : (x, y, rotation_deg).

    (x, y) est le milieu de sa ligne de base, posé sur le cercle ; rotation_deg est la rotation à
    appliquer à la lettre (dessinée de gauche à droite, ligne de base sur l'axe X, centrée sur son
    origine). Le texte entier est centré sur `center_deg`.
    """
    if radius_mm <= 0:
        raise ValueError("radius")
    if center_deg is None:
        center_deg = default_center_deg(inside)
    total = text_length(advances_mm, spacing_mm)
    sign = 1.0 if inside else -1.0
    placements = []
    cursor = 0.0
    for adv in advances_mm:
        s = cursor + adv / 2.0 - total / 2.0
        theta = center_deg + sign * math.degrees(s / radius_mm)
        rad = math.radians(theta)
        rotation = _wrap_deg(theta + 90.0 if inside else theta - 90.0)
        placements.append((radius_mm * math.cos(rad), radius_mm * math.sin(rad), rotation))
        cursor += adv + spacing_mm
    return placements
