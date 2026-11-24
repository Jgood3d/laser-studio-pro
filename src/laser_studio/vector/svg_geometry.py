"""Géométrie SVG selon la spécification (SVG 1.1 / SVG 2, CSS Values, CSS Transforms), sur des QPainterPath
(QtGui, sans widget) : longueurs avec unité, transformation CSS, tirets d'un trait, découpe d'un tracé par une
zone (clipPath, mask).

    user_length("10mm", "x", viewport=(210, 297))       # 37.8 unités utilisateur (1 mm = 96 / 25,4 px)
    css_transform("rotate(45deg) translate(10px, 0)")    # QTransform
    dashed(path, [5, 2], 0)                              # tirets du tracé
    clip_area(path, zone) / clip_lines(path, zone)       # surface / contour gardés dans la zone
"""
import math
import re

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainterPath, QTransform

# Unités absolues en unités utilisateur (CSS : 1 px = 1 unité, 1 in = 96 px).
CSS_PX = {"": 1.0, "px": 1.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "q": 96 / 101.6, "in": 96.0,
          "pt": 96 / 72, "pc": 16.0}
# Échelle des opérations booléennes (Qt aplatit les courbes à environ une unité près).
BOOLEAN_SCALE = 100.0
_LENGTH_RE = re.compile(r"\s*([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)\s*([a-zA-Z%]*)\s*")


def user_length(value, axis="diag", viewport=(100.0, 100.0), font_size=16.0, default=0.0):
    """Longueur SVG (« 12 », « 10mm », « 2em », « 50% ») en unités utilisateur. Pourcentage : de la largeur
    (`axis` « x »), de la hauteur (« y ») ou de la diagonale normalisée (« diag », SVG 1.1 § 7.10) de la zone
    d'affichage `viewport` ; em / ex : de `font_size`. `default` si la valeur est absente ou illisible."""
    if value is None:
        return default
    match = _LENGTH_RE.fullmatch(str(value))
    if not match:
        return default
    number, unit = float(match.group(1)), match.group(2).lower()
    if unit == "%":
        width, height = viewport
        reference = {"x": width, "y": height}.get(axis, math.hypot(width, height) / math.sqrt(2))
        return number / 100.0 * reference
    if unit == "em":
        return number * font_size
    if unit == "ex":
        return number * font_size / 2.0
    if unit in CSS_PX:
        return number * CSS_PX[unit]
    return default


def length_list(value, viewport=(100.0, 100.0), font_size=16.0):
    """Liste de longueurs (« 5, 2 », « 3mm 1mm ») en unités utilisateur ; [] si absente ou « none »."""
    if value is None or str(value).strip().lower() in ("", "none"):
        return []
    return [user_length(part, "diag", viewport, font_size, default=float("nan"))
            for part in re.split(r"[\s,]+", str(value).strip()) if part]


def dash_pattern(style, viewport=(100.0, 100.0), font_size=16.0):
    """(longueurs, décalage) des tirets d'un trait (stroke-dasharray, stroke-dashoffset), ou None pour un
    trait plein : liste absente, valeur négative ou illisible, ou somme nulle (SVG 1.1 § 11.4). Une liste de
    longueur impaire est répétée."""
    pattern = length_list(style.get("stroke-dasharray"), viewport, font_size)
    if not pattern or any(math.isnan(v) or v < 0 for v in pattern) or sum(pattern) <= 0:
        return None
    if len(pattern) % 2:
        pattern = pattern * 2
    return pattern, user_length(style.get("stroke-dashoffset"), "diag", viewport, font_size)


def _angle(text):
    match = re.fullmatch(r"\s*([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)\s*(deg|rad|grad|turn)?\s*", text)
    if not match:
        return 0.0
    number, unit = float(match.group(1)), match.group(2) or "deg"
    return {"deg": number, "rad": math.degrees(number), "grad": number * 0.9, "turn": number * 360.0}[unit]


def css_transform(text, viewport=(100.0, 100.0), font_size=16.0, origin=None):
    """Propriété CSS `transform` (« rotate(45deg) translate(10px, 5mm) scale(2) »…) en QTransform, comme
    l'attribut transform : la dernière fonction s'applique en premier. `origin` : (x, y) de
    transform-origin, en unités utilisateur. « none » ou une valeur illisible : identité."""
    result = QTransform()
    for name, args in re.findall(r"([a-zA-Z0-9]+)\s*\(([^)]*)\)", text or ""):
        name = name.lower()
        parts = [p for p in re.split(r"[\s,]+", args.strip()) if p]

        def length(index, axis):
            return user_length(parts[index], axis, viewport, font_size) if len(parts) > index else 0.0

        def number(index, default):
            try:
                return float(parts[index]) if len(parts) > index else default
            except ValueError:
                return default

        t = QTransform()
        if name == "matrix" and len(parts) == 6:
            t = QTransform(*(number(i, 0.0) for i in range(6)))
        elif name == "translate":
            t.translate(length(0, "x"), length(1, "y"))
        elif name == "translatex":
            t.translate(length(0, "x"), 0.0)
        elif name == "translatey":
            t.translate(0.0, length(0, "y"))
        elif name == "scale":
            sx = number(0, 1.0)
            t.scale(sx, number(1, sx))
        elif name == "scalex":
            t.scale(number(0, 1.0), 1.0)
        elif name == "scaley":
            t.scale(1.0, number(0, 1.0))
        elif name == "rotate" and parts:
            t.rotate(_angle(parts[0]))
        elif name in ("skew", "skewx") and parts:
            ax = math.tan(math.radians(_angle(parts[0])))
            ay = math.tan(math.radians(_angle(parts[1]))) if name == "skew" and len(parts) > 1 else 0.0
            t = QTransform(1, ay, ax, 1, 0, 0)
        elif name == "skewy" and parts:
            t = QTransform(1, math.tan(math.radians(_angle(parts[0]))), 0, 1, 0, 0)
        result = t * result
    if origin is not None and (origin[0] or origin[1]):
        to_origin, back = QTransform(), QTransform()
        to_origin.translate(-origin[0], -origin[1])
        back.translate(origin[0], origin[1])
        result = to_origin * result * back
    return result


def transform_origin(value, viewport=(100.0, 100.0), font_size=16.0):
    """(x, y) de transform-origin (« 50% 50% », « center », « 10px 20px », « right bottom ») en unités
    utilisateur, rapporté à la zone d'affichage (transform-box par défaut des éléments SVG : view-box)."""
    keywords = {"left": ("x", "0%"), "right": ("x", "100%"), "top": ("y", "0%"), "bottom": ("y", "100%")}
    x, y = "0", "0"
    parts = [p for p in str(value or "").split() if p]
    positional = []
    for part in parts[:2]:
        key = part.lower()
        if key in keywords:
            axis, percent = keywords[key]
            if axis == "x":
                x = percent
            else:
                y = percent
        elif key == "center":
            positional.append("50%")
        else:
            positional.append(part)
    if positional:
        if len(parts) == 1 or parts[0].lower() not in keywords:
            x = positional[0]
            if len(positional) > 1:
                y = positional[1]
            elif len(parts) == 1:
                y = "50%" if parts[0].lower() == "center" else y
        else:
            y = positional[0]
    return user_length(x, "x", viewport, font_size), user_length(y, "y", viewport, font_size)


def _polylines(path):
    """Polylignes du tracé, courbes aplaties finement quelle que soit l'unité."""
    down = 1.0 / BOOLEAN_SCALE
    scaled = QTransform.fromScale(BOOLEAN_SCALE, BOOLEAN_SCALE).map(path)
    return [[QPointF(p.x() * down, p.y() * down) for p in poly] for poly in scaled.toSubpathPolygons(QTransform())]


def dashed(path, pattern, offset=0.0):
    """Tirets du tracé (tracé ouvert, un sous-tracé par tiret) : `pattern` [tiret, espace, …] et `offset`
    en unités du tracé ; le motif reprend au début de chaque sous-tracé, comme le veut SVG."""
    total = sum(pattern)
    result = QPainterPath()
    for poly in _polylines(path):
        position = offset % total
        index, remaining = 0, pattern[0]
        while position > 0:                   # se place dans le motif d'après le décalage
            step = min(position, remaining)
            position -= step
            remaining -= step
            if remaining <= 1e-12:
                index = (index + 1) % len(pattern)
                remaining = pattern[index]
        drawing = False
        for a, b in zip(poly, poly[1:]):
            segment = math.hypot(b.x() - a.x(), b.y() - a.y())
            done = 0.0
            while done < segment - 1e-12:
                step = min(remaining, segment - done)
                t0, t1 = done / segment, (done + step) / segment
                p0 = a + (b - a) * t0
                p1 = a + (b - a) * t1
                if index % 2 == 0:
                    if not drawing:
                        result.moveTo(p0)
                        drawing = True
                    result.lineTo(p1)
                done += step
                remaining -= step
                if remaining <= 1e-12:
                    index = (index + 1) % len(pattern)
                    remaining = pattern[index]
                    drawing = False
    return result


def _scaled(path, factor):
    mapped = QTransform.fromScale(factor, factor).map(path)
    mapped.setFillRule(path.fillRule())
    return mapped


def clip_area(path, zone):
    """Surface de `path` (règle pair-impair) gardée dans `zone`."""
    area = QPainterPath(path)
    area.setFillRule(Qt.FillRule.OddEvenFill)
    result = _scaled(_scaled(area, BOOLEAN_SCALE).intersected(_scaled(zone, BOOLEAN_SCALE)).simplified(),
                     1 / BOOLEAN_SCALE)
    result.setFillRule(Qt.FillRule.OddEvenFill)
    return result


def outside_area(path, zone):
    """Surface de `path` hors de `zone` (vide si `path` est entièrement dans la zone)."""
    area = QPainterPath(path)
    area.setFillRule(Qt.FillRule.OddEvenFill)
    return _scaled(_scaled(area, BOOLEAN_SCALE).subtracted(_scaled(zone, BOOLEAN_SCALE)), 1 / BOOLEAN_SCALE)


def clip_lines(path, zone, step=0.1):
    """Parties d'un contour (lignes de découpe ou de marquage) qui passent dans `zone` : le tracé reste un
    trait, il n'est pas refermé sur le bord de la zone. Précision : `step` (unités du tracé)."""
    result = QPainterPath()
    for poly in _polylines(path):
        drawing = False
        for a, b in zip(poly, poly[1:]):
            length = math.hypot(b.x() - a.x(), b.y() - a.y())
            pieces = max(1, math.ceil(length / step))
            for i in range(pieces):
                p0 = a + (b - a) * (i / pieces)
                p1 = a + (b - a) * ((i + 1) / pieces)
                if zone.contains((p0 + p1) / 2):
                    if not drawing:
                        result.moveTo(p0)
                        drawing = True
                    result.lineTo(p1)
                else:
                    drawing = False
    return result
