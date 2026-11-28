"""Styles SVG selon la spécification (SVG 1.1 / SVG 2 du W3C, couleurs CSS Color 3), sans widget :
couleurs, cascade des propriétés et héritage.

- Couleurs : les 147 noms CSS, #rgb, #rgba, #rrggbb, #rrggbbaa, rgb()/rgba() (entiers ou pourcentages),
  hsl()/hsla(), « currentColor » (propriété `color`), « transparent ».
- Cascade d'un élément : attributs de présentation (fill="…"), puis règles de la feuille <style> (sélecteurs
  simples : élément, .classe, #id, et leurs listes séparées par des virgules), puis attribut style="…" ;
  « !important » de la feuille passe avant l'attribut style.
- Héritage : seules les propriétés héritées par la spécification passent du parent à l'enfant (fill,
  stroke, visibility, polices…) ; display, opacity, transform ne s'héritent pas. « inherit » reprend la
  valeur du parent.

    sheet = StyleSheet.from_root(root)
    style = computed_style(elem, parent_style, sheet)
    rgba = parse_color(style.get("fill"), style.get("color"))
"""
import colorsys
import re

# Propriétés héritées (SVG 1.1, index des propriétés ; SVG 2 pour paint-order).
INHERITED = {
    "clip-rule", "color", "color-interpolation", "color-rendering", "cursor", "direction", "fill",
    "fill-opacity", "fill-rule", "font", "font-family", "font-size", "font-size-adjust", "font-stretch",
    "font-style", "font-variant", "font-weight", "glyph-orientation-horizontal", "glyph-orientation-vertical",
    "image-rendering", "kerning", "letter-spacing", "line-height", "marker", "marker-end", "marker-mid",
    "marker-start", "paint-order", "pointer-events", "shape-rendering", "stroke", "stroke-dasharray",
    "stroke-dashoffset", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-opacity",
    "stroke-width", "text-anchor", "text-rendering", "visibility", "word-spacing", "writing-mode",
}
# Propriétés lues dans les attributs de présentation (fill="…").
PRESENTATION = INHERITED | {"display", "opacity", "stop-color", "stop-opacity", "clip-path", "mask",
                            "filter", "overflow"}
# Valeurs initiales utiles (sans parent).
INITIAL = {"fill": "black", "stroke": "none", "visibility": "visible", "fill-rule": "nonzero",
           "stroke-width": "1", "fill-opacity": "1", "stroke-opacity": "1", "color": "black"}

# Mots-clés de couleur CSS Color 3 (147 noms, dont grey / gray).
_NAMED = """aliceblue f0f8ff antiquewhite faebd7 aqua 00ffff aquamarine 7fffd4 azure f0ffff beige f5f5dc
bisque ffe4c4 black 000000 blanchedalmond ffebcd blue 0000ff blueviolet 8a2be2 brown a52a2a burlywood deb887
cadetblue 5f9ea0 chartreuse 7fff00 chocolate d2691e coral ff7f50 cornflowerblue 6495ed cornsilk fff8dc
crimson dc143c cyan 00ffff darkblue 00008b darkcyan 008b8b darkgoldenrod b8860b darkgray a9a9a9
darkgreen 006400 darkgrey a9a9a9 darkkhaki bdb76b darkmagenta 8b008b darkolivegreen 556b2f darkorange ff8c00
darkorchid 9932cc darkred 8b0000 darksalmon e9967a darkseagreen 8fbc8f darkslateblue 483d8b
darkslategray 2f4f4f darkslategrey 2f4f4f darkturquoise 00ced1 darkviolet 9400d3 deeppink ff1493
deepskyblue 00bfff dimgray 696969 dimgrey 696969 dodgerblue 1e90ff firebrick b22222 floralwhite fffaf0
forestgreen 228b22 fuchsia ff00ff gainsboro dcdcdc ghostwhite f8f8ff gold ffd700 goldenrod daa520
gray 808080 grey 808080 green 008000 greenyellow adff2f honeydew f0fff0 hotpink ff69b4 indianred cd5c5c
indigo 4b0082 ivory fffff0 khaki f0e68c lavender e6e6fa lavenderblush fff0f5 lawngreen 7cfc00
lemonchiffon fffacd lightblue add8e6 lightcoral f08080 lightcyan e0ffff lightgoldenrodyellow fafad2
lightgray d3d3d3 lightgreen 90ee90 lightgrey d3d3d3 lightpink ffb6c1 lightsalmon ffa07a lightseagreen 20b2aa
lightskyblue 87cefa lightslategray 778899 lightslategrey 778899 lightsteelblue b0c4de lightyellow ffffe0
lime 00ff00 limegreen 32cd32 linen faf0e6 magenta ff00ff maroon 800000 mediumaquamarine 66cdaa
mediumblue 0000cd mediumorchid ba55d3 mediumpurple 9370db mediumseagreen 3cb371 mediumslateblue 7b68ee
mediumspringgreen 00fa9a mediumturquoise 48d1cc mediumvioletred c71585 midnightblue 191970 mintcream f5fffa
mistyrose ffe4e1 moccasin ffe4b5 navajowhite ffdead navy 000080 oldlace fdf5e6 olive 808000 olivedrab 6b8e23
orange ffa500 orangered ff4500 orchid da70d6 palegoldenrod eee8aa palegreen 98fb98 paleturquoise afeeee
palevioletred db7093 papayawhip ffefd5 peachpuff ffdab9 peru cd853f pink ffc0cb plum dda0dd
powderblue b0e0e6 purple 800080 red ff0000 rosybrown bc8f8f royalblue 4169e1 saddlebrown 8b4513
salmon fa8072 sandybrown f4a460 seagreen 2e8b57 seashell fff5ee sienna a0522d silver c0c0c0 skyblue 87ceeb
slateblue 6a5acd slategray 708090 slategrey 708090 snow fffafa springgreen 00ff7f steelblue 4682b4 tan d2b48c
teal 008080 thistle d8bfd8 tomato ff6347 turquoise 40e0d0 violet ee82ee wheat f5deb3 white ffffff
whitesmoke f5f5f5 yellow ffff00 yellowgreen 9acd32"""
NAMED_COLORS = {name: tuple(int(code[i:i + 2], 16) for i in (0, 2, 4))
                for name, code in zip(_NAMED.split()[::2], _NAMED.split()[1::2])}

_NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def _channel(text, scale=255.0):
    text = text.strip()
    if text.endswith("%"):
        return max(0.0, min(1.0, float(text[:-1]) / 100.0)) * scale
    return max(0.0, min(scale, float(text)))


def _alpha(text):
    if text is None:
        return 1.0
    text = text.strip()
    return max(0.0, min(1.0, float(text[:-1]) / 100.0 if text.endswith("%") else float(text)))


def parse_color(value, current_color=None):
    """(r, g, b, alpha) d'une couleur CSS / SVG (r, g, b de 0 à 255, alpha de 0 à 1), ou None pour « none »,
    une référence (url(#dégradé)) ou une valeur illisible. `current_color` : valeur de la propriété
    `color`, pour « currentColor »."""
    color = (value or "").strip().lower()
    if not color or color == "none" or color.startswith("url("):
        return None
    if color == "transparent":
        return (0, 0, 0, 0.0)
    if color == "currentcolor":
        return parse_color(current_color or "black") if current_color != value else None
    if color in NAMED_COLORS:
        return (*NAMED_COLORS[color], 1.0)
    match = re.fullmatch(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", color)
    if match:
        h = match.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        alpha = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
    match = re.fullmatch(r"rgba?\(\s*([^,\s]+)\s*[,\s]\s*([^,\s]+)\s*[,\s]\s*([^,\s/)]+)\s*(?:[,/]\s*([^)\s]+)\s*)?\)",
                         color)
    if match:
        try:
            r, g, b = (round(_channel(v)) for v in match.groups()[:3])
            return (r, g, b, _alpha(match.group(4)))
        except ValueError:
            return None
    match = re.fullmatch(r"hsla?\(\s*([^,\s]+?)(?:deg)?\s*[,\s]\s*([^,\s]+)\s*[,\s]\s*([^,\s/)]+)\s*"
                         r"(?:[,/]\s*([^)\s]+)\s*)?\)", color)
    if match:
        try:
            hue = (float(match.group(1)) % 360) / 360
            sat, light = _channel(match.group(2), 1.0), _channel(match.group(3), 1.0)
        except ValueError:
            return None
        r, g, b = colorsys.hls_to_rgb(hue, light, sat)
        return (round(r * 255), round(g * 255), round(b * 255), _alpha(match.group(4)))
    return None


def _declarations(text):
    """{propriété: (valeur, important)} d'un bloc « a: b; c: d !important »."""
    result = {}
    for part in (text or "").split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        value = value.strip()
        important = value.lower().endswith("!important")
        if important:
            value = value[: -len("!important")].strip()
        result[key.strip().lower()] = (value, important)
    return result


class StyleSheet:
    """Règles des éléments <style> du document, limitées aux sélecteurs simples (élément, .classe, #id,
    élément.classe), dans l'ordre de la feuille."""

    def __init__(self, rules=()):
        self.rules = list(rules)          # [(spécificité, ordre, élément, classes, id, déclarations)]

    @classmethod
    def from_root(cls, root):
        rules = []
        for elem in root.iter():
            if elem.tag.split("}")[-1] != "style" or not elem.text:
                continue
            text = re.sub(r"/\*.*?\*/", "", elem.text, flags=re.S)
            for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
                declarations = _declarations(body)
                for selector in selectors.split(","):
                    parsed = cls._simple(selector.strip())
                    if parsed is not None:
                        tag, classes, ident = parsed
                        specificity = (1 if ident else 0, len(classes), 1 if tag else 0)
                        rules.append((specificity, len(rules), tag, classes, ident, declarations))
        return cls(rules)

    @staticmethod
    def _simple(selector):
        """(élément, {classes}, id) d'un sélecteur simple, ou None (combinateurs, attributs, pseudo-classes)."""
        match = re.fullmatch(r"([a-zA-Z][\w-]*|\*)?((?:[.#][\w-]+)*)", selector)
        if not match or not selector:
            return None
        tag = match.group(1) if match.group(1) not in (None, "*") else None
        parts = re.findall(r"([.#])([\w-]+)", match.group(2))
        ids = [name for kind, name in parts if kind == "#"]
        if len(ids) > 1:
            return None
        return tag, {name for kind, name in parts if kind == "."}, ids[0] if ids else None

    def declarations_for(self, elem):
        """[(propriété, valeur, important)] des règles qui s'appliquent à `elem`, de la moins à la plus
        prioritaire (spécificité, puis ordre)."""
        tag = elem.tag.split("}")[-1]
        classes = set((elem.attrib.get("class") or "").split())
        ident = elem.attrib.get("id")
        matched = [rule for rule in self.rules
                   if (rule[2] is None or rule[2] == tag) and rule[3] <= classes
                   and (rule[4] is None or rule[4] == ident) and (rule[2] or rule[3] or rule[4])]
        matched.sort(key=lambda rule: (rule[0], rule[1]))
        return [(key, value, important) for rule in matched for key, (value, important) in rule[5].items()]


def computed_style(elem, parent_style=None, sheet=None):
    """Style calculé de `elem` : propriétés héritées du parent (`parent_style`, déjà calculé), puis
    attributs de présentation, feuille de style et attribut style ; « inherit » reprend la valeur du
    parent."""
    parent_style = parent_style or {}
    style = {k: v for k, v in parent_style.items() if k in INHERITED}
    own = {}
    for name in PRESENTATION:
        value = elem.attrib.get(name)
        if value is not None:
            own[name] = value.strip()
    important = {}
    for key, value, is_important in (sheet.declarations_for(elem) if sheet is not None else []):
        (important if is_important else own)[key] = value
    for key, (value, _imp) in _declarations(elem.attrib.get("style")).items():
        own[key] = value
    own.update(important)
    for key, value in own.items():
        if value.lower() == "inherit":
            if key in parent_style:
                style[key] = parent_style[key]
            else:
                style.pop(key, None)
        else:
            style[key] = value
    return style


def paint_alpha(style, which):
    """Opacité d'un remplissage (`which` = « fill ») ou d'un trait (« stroke ») : alpha de la couleur ×
    fill-opacity / stroke-opacity. 0 si la peinture est « none »."""
    color = parse_color(style.get(which, INITIAL[which]), style.get("color"))
    if color is None:
        return 0.0
    try:
        opacity = _alpha(style.get(f"{which}-opacity", "1"))
    except ValueError:
        opacity = 1.0
    return color[3] * opacity
