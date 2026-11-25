"""Réglages de Stencil Studio tels que la page web les définit (ui/studio.html), lus par la fenêtre Qt.

La page reste la seule source : la liste des réglages (SPEC : clé, type, libellé, valeur par défaut, bornes,
options, groupe), les modes (MODES, avec leur icône), les groupes affichés par mode (MODE_COMMON, MODE_EXTRA,
MODE_NOT, MODE_ROWS) et les bulles d'aide (TIPS). Les deux interfaces ont ainsi les mêmes réglages et les mêmes
valeurs par défaut (qui ne sont pas toujours celles de core.Params : la page envoie toujours tous ses réglages).

    spec = load()
    spec.defaults()["dot_gamma"]          # 1.2, comme la page
    spec.request_params(state)            # ce que la page envoie dans « params »
    spec.groups_for("halftone")           # groupes affichés pour ce mode, dans l'ordre de la page
"""
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from .models.frame import is_full

UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "studio.html")

# Littéraux de la page à lire : nom de la constante -> caractère ouvrant.
CONSTANTS = {"SPEC": "[", "MODES": "[", "MODE_COMMON": "[", "MODE_EXTRA": "{", "MODE_NOT": "{", "MODE_ROWS": "{",
             "TIPS": "{", "PRESETS": "{", "PRESET_MODE": "{", "ADV": "[", "PRESET_SKIP": "[", "NO_RESET": "[",
             "BOXMSG": "{", "DEF_OPEN": "["}
_CLOSING = {"[": "]", "{": "}"}
# Fonction d'affichage d'une valeur (« fmt:mm », « fmt:v => … ») : inutile hors de la page, remplacée par son nom.
_UNIT = re.compile(r'["\']\s*([^"\'\d\s+.]+)["\']\s*$')
_FMT = re.compile(r'fmt:\s*(v\s*=>.*?|\w+)(?=,\s*\w+\s*:|\s*\})')


def _literal(html, name):
    """Texte du littéral `const NAME = …` de la page (jusqu'au crochet ou à l'accolade qui le ferme)."""
    opening = CONSTANTS[name]
    start = html.index(opening, html.index(f"const {name} ="))
    depth, i, quote = 0, start, None
    while i < len(html):
        ch = html[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == opening:
            depth += 1
        elif ch == _CLOSING[opening]:
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
        i += 1
    raise ValueError(f"{name} : littéral non fermé dans studio.html")


def _fmt_name(match):
    """« fmt » de la page -> son nom ; une fonction garde l'unité qu'elle ajoute au nombre (« v + " °" »)."""
    name = match.group(1)
    if name in ("mm", "pct"):
        return f'fmt:"{name}"'
    unit = _UNIT.search(name)
    return 'fmt:"custom"' + (f',unit:"{unit.group(1)}"' if unit else "")


def js_to_json(text):
    """Littéral JavaScript de la page (clés sans guillemets, chaînes '…', virgules finales, noms nus) -> JSON."""
    text = _FMT.sub(_fmt_name, text)
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":                                   # chaîne : recopiée, en guillemets doubles
            j, buf = i + 1, []
            while text[j] != ch:
                if text[j] == "\\":
                    buf.append(text[j:j + 2])
                    j += 2
                    continue
                buf.append('\\"' if text[j] == '"' else text[j])
                j += 1
            out.append('"' + "".join(buf) + '"')
            i = j + 1
        elif ch.isalpha() or ch == "_":                   # nom : clé (suivi de « : ») ou valeur nue
            j = i
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            rest = text[j:].lstrip()
            if rest.startswith(":"):
                out.append(json.dumps(word))
            elif word in ("true", "false", "null"):
                out.append(word)
            else:
                out.append(json.dumps(word))
            i = j
        elif ch == ",":                                   # virgule finale avant ] ou } : retirée
            rest = text[i + 1:].lstrip()
            if not rest.startswith(("]", "}")):
                out.append(ch)
            i += 1
        else:
            out.append(ch)
            i += 1
    return json.loads("".join(out))


@dataclass
class Spec:
    groups: list          # [{"g": nom du groupe, "items": [réglage, ...]}]
    modes: list           # [{"id", "label", "tip", "ic" (tracé SVG 24 px)}]
    mode_common: list
    mode_extra: dict
    mode_not: dict
    mode_rows: dict
    tips: dict
    presets: dict         # styles prédéfinis : nom -> réglages
    preset_mode: dict     # style -> mode où il est proposé
    advanced: list        # réglages avancés, masqués sauf « afficher les réglages avancés » (ADV)
    preset_skip: list     # réglages que « mes réglages enregistrés » ne gardent pas (PRESET_SKIP)
    no_reset: list        # réglages jamais comptés comme modifiés (NO_RESET)
    box_messages: dict    # avertissements du caisson : code -> texte (BOXMSG)
    default_open: list    # groupes ouverts au départ, les autres repliés (DEF_OPEN)

    def items(self):
        return [item for group in self.groups for item in group["items"]]

    def item(self, key):
        return next(item for item in self.items() if item["k"] == key)

    def defaults(self):
        """Valeur de départ de chaque réglage, comme la page (DEFAULTS)."""
        return {item["k"]: item.get("def") for item in self.items()}

    def request_params(self, state):
        """« params » d'une demande, comme la page (getParams) : tous les réglages sauf ceux de l'interface."""
        return {item["k"]: state.get(item["k"], item.get("def")) for item in self.items() if not item.get("ui")}

    def groups_for(self, mode):
        """Groupes affichés pour le mode `mode`, dans l'ordre de la page (groupOK)."""
        mode = mode if any(m["id"] == mode for m in self.modes) else "stencil"
        return [g for g in self.groups
                if g["g"] not in self.mode_not.get(mode, [])
                and (g["g"] in self.mode_common or g["g"] in self.mode_extra.get(mode, []))]

    def row_shown(self, key, mode):
        """Réglage propre à certains modes (MODE_ROWS) : affiché pour `mode` ?"""
        return key not in self.mode_rows or mode in self.mode_rows[key]

    def is_modified(self, key, value):
        """Réglage changé par rapport à sa valeur de départ (isMod de la page)."""
        default = self.item(key).get("def")
        if isinstance(default, (int, float)) and not isinstance(default, bool):
            try:
                return abs(float(value) - default) > 1e-9
            except (TypeError, ValueError):
                return True
        return value != default

    def presets_for(self, mode):
        """Styles proposés dans « Partir d'un style » pour `mode` (PRESET_MODE), dans l'ordre de la liste."""
        return [value for value, _label in self.item("preset")["opts"]
                if value and self.preset_mode.get(value) == mode]

    def row_states(self, state):
        """(grisés, masqués) : réglages qui ne s'appliquent pas avec les autres réglages, comme la page
        (refreshDisabled). Les groupes et lignes propres à un mode sont à part (groups_for, row_shown)."""
        s, o = state, state.get("output")
        disabled, hidden = set(), set()

        def dis(key, on):
            if on:
                disabled.add(key)

        def hid(key, on):
            if on:
                hidden.add(key)
        dis("threshold", s.get("auto_threshold"))
        dis("aspect", s.get("shape") == "circle")
        picks = [t.strip() for t in str(s.get("ml_picks") or "").split(",")
                 if re.fullmatch(r"#[0-9a-fA-F]{6}", t.strip())]
        dis("ml_color_auto", o == "layers" and s.get("ml_sep") == "color" and len(picks) >= 2)
        for key in ("custom_w", "custom_h"):
            dis(key, s.get("shape") == "circle" or s.get("aspect") != "custom")
        dis("margin", not s.get("isolate"))
        for key in ("rot", "zoom", "img_mm"):
            dis(key, is_full(s))
        for key in ("hang_style", "hang_hole_mm", "hang_tab_mm"):
            dis(key, s.get("hang") == "none")
        no_text = not s.get("text_top") and not s.get("text_bottom")
        text_shape = s.get("shape") in ("circle", "oval", "rect", "rrect")
        for key in ("text_top", "text_bottom"):
            dis(key, not text_shape)
        for key in ("text_size_mm", "text_spacing", "text_bridge_mm"):
            dis(key, no_text or not text_shape)
        dis("lightcolor", not s.get("backlight"))
        dis("outline_mm", not s.get("isolate"))
        is_stencil = o == "stencil" or not any(m["id"] == o for m in self.modes)
        for i in self.items():
            k = i["k"]
            if i.get("local"):
                hid(k, not is_stencil or s.get("mode") != "local")
            if i.get("st") and not i.get("local"):
                hid(k, not is_stencil and not (o == "lowpoly" and i.get("sl")))
            if i.get("ml"):
                hid(k, o != "layers" or (i.get("mlcol") and s.get("ml_sep") != "color") or i.get("mlorder")
                    or (i.get("mlpin") and not s.get("ml_pins")) or (i.get("mlbg") and s.get("ml_bg") != "own")
                    or (i.get("mleng") and not s.get("ml_engrave")))
            if i.get("qr"):
                hid(k, o != "qr" or (i.get("qrk") and i["qrk"] != s.get("qr_kind"))
                    or (i.get("qrcut") and s.get("qr_mode") != "cut"))
            if i.get("lp"):
                hid(k, o != "lowpoly" or (i.get("lpsolid") and s.get("lp_style") != "solid"))
            if i.get("ni"):
                hid(k, o == "engrave")
            if i.get("ht"):
                hid(k, o not in ("halftone", "lines"))
            if i.get("dt"):
                hid(k, o != "halftone")
            if i.get("ln"):
                hid(k, o != "lines")
            if i.get("eg"):
                hid(k, o != "engrave")
            if i.get("bs"):
                hid(k, s.get("box_style") == "fingers")
            if i.get("bf"):
                hid(k, s.get("box_style") != "fingers")
            if i.get("sf"):
                hid(k, s.get("box_support") not in ("foot", "both"))
            if i.get("sk"):
                hid(k, s.get("box_support") not in ("wall", "both"))
        return disabled, hidden


@lru_cache(maxsize=1)
def load(path=UI_FILE):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    parsed = {name: js_to_json(_literal(html, name)) for name in CONSTANTS}
    return Spec(groups=parsed["SPEC"], modes=parsed["MODES"], mode_common=parsed["MODE_COMMON"],
                mode_extra=parsed["MODE_EXTRA"], mode_not=parsed["MODE_NOT"], mode_rows=parsed["MODE_ROWS"],
                tips=parsed["TIPS"], presets=parsed["PRESETS"], preset_mode=parsed["PRESET_MODE"],
                advanced=parsed["ADV"], preset_skip=parsed["PRESET_SKIP"], no_reset=parsed["NO_RESET"],
                box_messages=parsed["BOXMSG"], default_open=parsed["DEF_OPEN"])
