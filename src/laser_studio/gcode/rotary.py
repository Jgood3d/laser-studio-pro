"""Axe rotatif : conversion du G-Code « à plat » vers les commandes de la machine, sans Qt.

Le G-Code du job, l'aperçu, les contrôles et la durée estimée parlent en millimètres SUR LA SURFACE de
l'objet : X le long de l'objet, Y autour. Seul ce qui part vers la machine (envoi, fichier enregistré,
cadrage) est converti : chaque déplacement en Y devient un déplacement de l'axe rotatif.

Deux familles de machines :
  * rotatif branché sur Y (axe « Y ») : le rotatif remplace le moteur de Y. Pour tourner l'objet de
    1 mm de surface, il faut commander `facteur` mm de Y, avec
        facteur = mm_par_tour / (π × diamètre)
    où `mm_par_tour` est la course de Y qui fait faire un tour complet au rotatif (réglée dans le
    firmware, $101), et `diamètre` celui de l'objet (mandrin) ou du rouleau (rouleaux : l'objet est
    entraîné par la surface des rouleaux, son diamètre n'intervient pas) ;
  * axe dédié (« A » : degrés) : le mot Y devient un mot A, et
        facteur = 360 / (π × diamètre)   (degrés par mm de surface).

La vitesse est corrigée : GRBL règle F sur le déplacement de la machine, dont la composante rotative est
étirée du `facteur`. Pour que la surface avance à la vitesse demandée, F est recalculé à chaque
déplacement : F_machine = F × √(dx² + (facteur·dy)²) / √(dx² + dy²).

Pas pris en charge (RotaryError) : les arcs G2/G3 avec X, Y, I ou J, et les pouces (G20).
"""
import math
import re
from dataclasses import dataclass

AXIS_Y, AXIS_A = "Y", "A"
AXES = (AXIS_Y, AXIS_A)
DRIVE_CHUCK, DRIVE_ROLLER = "chuck", "roller"
DRIVES = (DRIVE_CHUCK, DRIVE_ROLLER)

# Déplacements de moins d'un micromètre : ni pente ni correction de vitesse.
_MIN_MOVE_MM = 1e-6
# Écart de vitesse (mm/min) en dessous duquel F n'est pas réécrit.
_FEED_TOLERANCE = 0.05

_TOKEN = re.compile(r"\([^)]*\)|([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


class RotaryError(ValueError):
    """G-Code que la conversion ne sait pas traiter (arc, pouces) : l'envoi doit être refusé."""


@dataclass(frozen=True)
class RotaryConfig:
    """Réglages de l'axe rotatif (GrblConfig : rotary_*)."""

    enabled: bool = False
    axis: str = AXIS_Y
    drive: str = DRIVE_CHUCK
    object_mm: float = 60.0        # diamètre de l'objet
    roller_mm: float = 20.0        # diamètre des rouleaux (entraînement par rouleaux)
    mm_per_turn: float = 360.0     # course de Y pour un tour du rotatif (axe Y seulement)

    @classmethod
    def from_settings(cls, settings):
        """Depuis un objet qui porte les réglages `rotary_*` (GrblConfig)."""
        return cls(enabled=bool(settings.rotary_enabled), axis=settings.rotary_axis,
                   drive=settings.rotary_drive, object_mm=float(settings.rotary_object_mm),
                   roller_mm=float(settings.rotary_roller_mm),
                   mm_per_turn=float(settings.rotary_mm_per_turn))

    @property
    def driven_diameter(self):
        """Diamètre dont dépend le facteur : l'objet (mandrin) ou le rouleau."""
        return self.object_mm if self.drive == DRIVE_CHUCK else self.roller_mm

    @property
    def active(self):
        """Activé et réglé de façon utilisable (diamètres et course positifs)."""
        if not self.enabled or self.driven_diameter <= 0 or self.object_mm <= 0:
            return False
        return self.axis == AXIS_A or self.mm_per_turn > 0

    @property
    def factor(self):
        """Unités de l'axe (mm de Y, ou degrés de A) par mm de surface."""
        turn = 360.0 if self.axis == AXIS_A else self.mm_per_turn
        return turn / (math.pi * self.driven_diameter)

    @property
    def circumference_mm(self):
        """Tour de l'objet : la hauteur maximale d'un motif qui ne se recouvre pas."""
        return math.pi * self.object_mm

    def describe(self):
        """Ligne de commentaire du G-Code converti."""
        drive = "mandrin" if self.drive == DRIVE_CHUCK else "rouleaux"
        unit = "°/mm" if self.axis == AXIS_A else "mm/mm"
        return (f"; Axe rotatif : axe {self.axis}, {drive}, objet Ø {self.object_mm:g} mm"
                f"{'' if self.drive == DRIVE_CHUCK else f', rouleau Ø {self.roller_mm:g} mm'}"
                f", facteur {self.factor:.4f} {unit}")


def surface_y(machine_y, config):
    """Position en Y sur la surface, d'après la position Y rapportée par la machine (axe Y seulement :
    un axe A n'est pas rapporté dans Y, la valeur est rendue telle quelle)."""
    if config is None or not config.active or config.axis != AXIS_Y or config.factor == 0:
        return machine_y
    return machine_y / config.factor


def _fmt(value, decimals=4):
    text = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def machine_gcode(text, config, header=True):
    """G-Code du job (mm de surface) -> G-Code de la machine. Sans effet (texte rendu tel quel) si
    `config` est None ou inactif. Lève RotaryError pour un arc ou des pouces.

    `header` : ajoute en tête une ligne de commentaire qui décrit la conversion (fichier enregistré). Pour
    l'envoi il est omis : le texte envoyé garde exactement les lignes du G-Code à plat, ce qui permet à la
    reprise d'un job interrompu (grbl.streaming.resume_gcode) de s'y repérer par numéro de ligne."""
    if config is None or not config.active:
        return text
    factor = config.factor
    out = [config.describe()] if header else []
    relative = False
    motion = None
    x = y = 0.0
    wanted_feed = None          # vitesse demandée, sur la surface
    emitted_feed = None         # dernière vitesse envoyée à la machine

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped[0] in ";$%":
            out.append(raw)
            continue
        code, sep, comment = raw.partition(";")
        words = [(m.group(1).upper(), float(m.group(2))) for m in _TOKEN.finditer(code) if m.group(1)]
        letters = {w for w, _ in words}
        value_of = {}
        for letter, value in words:
            value_of.setdefault(letter, value)

        for letter, value in words:
            if letter == "G":
                if value == 20:
                    raise RotaryError("G20 (pouces)")
                if value == 90:
                    relative = False
                elif value == 91:
                    relative = True
                elif value in (0, 1, 2, 3):
                    motion = int(value)
        has_xy = "X" in letters or "Y" in letters
        if motion in (2, 3) and (has_xy or "I" in letters or "J" in letters):
            raise RotaryError("arc G2/G3")

        is_move = motion in (0, 1) and has_xy
        desired_feed = None
        if is_move:
            new_x = (x + value_of["X"]) if relative and "X" in value_of else value_of.get("X", x)
            new_y = (y + value_of["Y"]) if relative and "Y" in value_of else value_of.get("Y", y)
            if relative:
                dx, dy = value_of.get("X", 0.0), value_of.get("Y", 0.0)
            else:
                dx, dy = new_x - x, new_y - y
            x, y = new_x, new_y
            if "F" in value_of:
                wanted_feed = value_of["F"]
            if motion == 1 and wanted_feed is not None:
                length = math.hypot(dx, dy)
                ratio = math.hypot(dx, factor * dy) / length if length > _MIN_MOVE_MM else 1.0
                desired_feed = wanted_feed * ratio
        elif "F" in value_of:
            wanted_feed = value_of["F"]
            emitted_feed = value_of["F"]          # cette ligne règle F telle quelle sur la machine

        feed_done = False

        def replace(match):
            nonlocal feed_done
            if not match.group(1):
                return match.group(0)             # commentaire entre parenthèses
            letter, value = match.group(1).upper(), float(match.group(2))
            if letter == "Y":
                return f"{config.axis}{_fmt(value * factor)}"
            if letter == "F" and desired_feed is not None:
                feed_done = True
                return f"F{_fmt(desired_feed, 1)}"
            return match.group(0)

        new_code = _TOKEN.sub(replace, code)
        if desired_feed is not None:
            if feed_done:
                emitted_feed = desired_feed
            elif emitted_feed is None or abs(desired_feed - emitted_feed) > _FEED_TOLERANCE:
                new_code = f"{new_code.rstrip()} F{_fmt(desired_feed, 1)}" + (" " if sep else "")
                emitted_feed = desired_feed
        out.append(new_code + (sep + comment if sep else ""))
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def machine_lines(lines, config):
    """Même conversion pour une liste de commandes (cadrage)."""
    if config is None or not config.active:
        return list(lines)
    return machine_gcode("\n".join(lines), config, header=False).splitlines()
