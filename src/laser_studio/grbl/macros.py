"""Macros de l'utilisateur : quelques lignes de G-Code envoyées d'un clic depuis le panneau des actions de job.
Lecture et écriture du fichier YAML, contrôle des macros, sans Qt.

Fichier (macros.yaml, dans le dossier des données de l'application) :

    macros:
      - name: Décaler +20 X +10 Y
        tooltip: Déplace la tête, laser éteint
        gcode: |
          G91
          G0 X20 Y10
          G90
      - name: Pointeur 1 %
        confirm: true
        machines: [Atomstack A5]
        gcode: |
          M3 S10

`machines` : profils machine où la macro apparaît (toutes si absent). Une macro qui allume le laser
(fires_laser) est toujours confirmée avant l'envoi, que `confirm` soit coché ou non.
"""
import re
from dataclasses import dataclass, field

import yaml

from laser_studio.grbl.streaming import gcode_lines

FILE_NAME = "macros.yaml"
FILE_HEADER = "# Macros de Laser Studio Pro : voir l'aide (F1), « Les macros ».\n"

_WORD_RE = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")


class MacroError(ValueError):
    """Fichier ou macro invalide. `code` : clé de traduction `macros.err.<code>`, `info` : ses champs."""

    def __init__(self, code, **info):
        super().__init__(code)
        self.code = code
        self.info = info


@dataclass
class Macro:
    name: str
    gcode: tuple = ()
    tooltip: str = ""
    confirm: bool = False
    machines: tuple = field(default_factory=tuple)

    @property
    def fires_laser(self):
        return fires_laser(self.gcode)

    def shown_for(self, profile_name):
        """Vrai si la macro apparaît pour le profil machine `profile_name` (toujours sans liste de machines)."""
        return not self.machines or profile_name in self.machines


def _strip_comments(line):
    return re.sub(r"\([^)]*\)", "", line.split(";", 1)[0]).upper()


def fires_laser(lines):
    """Vrai si ces lignes peuvent allumer le laser : M3 ou M4 actif avec une puissance S > 0 (la puissance
    peut venir d'une ligne précédente, la commande est modale). M5 éteint."""
    on, power = False, 0.0
    for line in lines:
        for letter, value in _WORD_RE.findall(_strip_comments(line)):
            number = float(value)
            if letter == "S":
                power = number
            elif letter == "M" and number in (3.0, 4.0):
                on = True
            elif letter == "M" and number == 5.0:
                on = False
        if on and power > 0:
            return True
    return False


def _text(entry, key, index, required=False):
    value = entry.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise MacroError("bad_field", index=index, field=key)
    value = str(value).strip()
    if required and not value:
        raise MacroError("missing_field", index=index, field=key)
    return value


def macro_from_dict(entry, index=1):
    """Macro décrite par un dictionnaire du fichier (`index` : son rang, pour les messages)."""
    if not isinstance(entry, dict):
        raise MacroError("not_a_macro", index=index)
    name = _text(entry, "name", index, required=True)
    raw = entry.get("gcode")
    if isinstance(raw, list) and all(isinstance(line, (str, int, float)) for line in raw):
        raw = "\n".join(str(line) for line in raw)
    if not isinstance(raw, str):
        raise MacroError("missing_field", index=index, field="gcode")
    # Commentaires de fin de ligne « ; … » retirés : GRBL n'en a pas besoin.
    lines = tuple(line.split(";", 1)[0].strip() for line in gcode_lines(raw))
    if not lines:
        raise MacroError("empty_gcode", index=index, name=name)
    machines = entry.get("machines") or ()
    if isinstance(machines, str):
        machines = (machines,)
    if not isinstance(machines, (list, tuple)) or not all(isinstance(m, str) for m in machines):
        raise MacroError("bad_field", index=index, field="machines")
    return Macro(name=name, gcode=lines, tooltip=_text(entry, "tooltip", index),
                 confirm=bool(entry.get("confirm", False)), machines=tuple(m.strip() for m in machines if m.strip()))


def load_macros(text):
    """Macros du texte YAML `text` (vide : aucune). Lève MacroError si le fichier ou une macro est invalide."""
    try:
        data = yaml.safe_load(text) if text.strip() else None
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        raise MacroError("yaml", line=(mark.line + 1) if mark else 0) from error
    if data is None:
        return []
    entries = data.get("macros") if isinstance(data, dict) else data
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise MacroError("not_a_list")
    return [macro_from_dict(entry, index) for index, entry in enumerate(entries, 1)]


class _Dumper(yaml.SafeDumper):
    """G-Code sur plusieurs lignes écrit en bloc « | », lisible et modifiable à la main."""


def _str_representer(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_representer)


def macro_to_dict(macro):
    entry = {"name": macro.name}
    if macro.tooltip:
        entry["tooltip"] = macro.tooltip
    if macro.confirm:
        entry["confirm"] = True
    if macro.machines:
        entry["machines"] = list(macro.machines)
    entry["gcode"] = "\n".join(macro.gcode) + "\n"
    return entry


def dump_macros(macros):
    """Texte YAML des macros (relu à l'identique par load_macros)."""
    body = yaml.dump({"macros": [macro_to_dict(m) for m in macros]}, Dumper=_Dumper, allow_unicode=True,
                     sort_keys=False, default_flow_style=False, width=120)
    return FILE_HEADER + body
