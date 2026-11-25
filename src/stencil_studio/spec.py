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

UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "studio.html")

# Littéraux de la page à lire : nom de la constante -> caractère ouvrant.
CONSTANTS = {"SPEC": "[", "MODES": "[", "MODE_COMMON": "[", "MODE_EXTRA": "{", "MODE_NOT": "{", "MODE_ROWS": "{",
             "TIPS": "{"}
_CLOSING = {"[": "]", "{": "}"}
# Fonction d'affichage d'une valeur (« fmt:mm », « fmt:v => … ») : inutile hors de la page, remplacée par son nom.
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


def js_to_json(text):
    """Littéral JavaScript de la page (clés sans guillemets, chaînes '…', virgules finales, noms nus) -> JSON."""
    text = _FMT.sub(lambda m: 'fmt:"%s"' % ("mm" if m.group(1) == "mm" else "pct" if m.group(1) == "pct"
                                             else "custom"), text)
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


@lru_cache(maxsize=1)
def load(path=UI_FILE):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    parsed = {name: js_to_json(_literal(html, name)) for name in CONSTANTS}
    return Spec(groups=parsed["SPEC"], modes=parsed["MODES"], mode_common=parsed["MODE_COMMON"],
                mode_extra=parsed["MODE_EXTRA"], mode_not=parsed["MODE_NOT"], mode_rows=parsed["MODE_ROWS"],
                tips=parsed["TIPS"])
