"""Éléments communs aux générateurs de G-Code : le résultat d'une génération, la puissance (valeur S),
la distance de surbalayage et la durée estimée (en secondes, marge comprise ; sa mise en forme traduite
est dans i18n/durations.py)."""
from typing import NamedTuple

# Mode de surbalayage (params['overscan_mode']) : valeur indépendante de la
# langue, fournie par la fenêtre (voir JobController.overscan_mode_value).
OVERSCAN_PERCENT = "Pourcentage (%)"
OVERSCAN_FIXED = "Distance Fixe (mm)"


class GcodeResult(NamedTuple):
    """Résultat d'une génération : le G-Code, son nombre de lignes, la
    puissance moyenne (%) des tracés gravés et la durée estimée en secondes,
    marge des accélérations comprise (with_time_margin).

    C'est un tuple : il se décompose comme les signaux `finished` des workers
    (gcode, nb_lignes, puissance_moyenne, durée)."""
    gcode: str
    line_count: int
    avg_power: float
    duration: float


def power_value(percent, s_max):
    """Valeur S de GRBL pour une puissance de `percent` % (S-Max = `s_max`), arrondie au plus proche.
    Seul calcul de la puissance du G-Code : une case de la matrice de test et un calque réglé au même
    pourcentage donnent ainsi le même S."""
    return max(0, int(round(float(percent) / 100.0 * float(s_max))))


def overscan_distance(mode, pct, dist, width_mm):
    """Distance de surbalayage (mm) : `pct` % de `width_mm` (largeur gravée) en mode OVERSCAN_PERCENT,
    sinon la distance fixe `dist`. Ne vérifie pas si le surbalayage est activé : c'est à l'appelant."""
    if mode == OVERSCAN_PERCENT:
        return width_mm * (pct / 100.0)
    return dist


def scan_offset_mm(value):
    """Décalage des lignes retour (mm, voir bidir_test_gcode) lu dans un réglage ; 0 si absent ou
    illisible."""
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


# Marge ajoutée à toute durée calculée d'après le G-Code (job, matrice de test, motif aller/retour) : les
# accélérations et décélérations de la machine allongent le temps des trajets à vitesse constante.
# L'estimation rapide (bouton « Estimer ») n'en a pas : elle le dit dans son message.
TIME_MARGIN = 1.15


def with_time_margin(seconds):
    """Durée calculée d'après le G-Code (secondes), plus la marge des accélérations (TIME_MARGIN)."""
    return max(0.0, float(seconds)) * TIME_MARGIN


def duration_parts(seconds):
    """(heures, minutes, secondes) entières d'une durée, arrondie à la seconde."""
    total = max(0, int(round(float(seconds))))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return hours, minutes, secs


def num(value):
    """Nombre du G-Code, au millième, sans zéros inutiles : 12.5, 3, -0.25 (moins d'octets à envoyer)."""
    text = f"{float(value):.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


class LaserMoves:
    """Écrit les déplacements laser dans `lines`, selon les règles de GRBL en mode laser ($32=1) :

    - la puissance S voyage sur la ligne du mouvement. Une ligne qui change S sans bouger (« S0 », « M4 S500 »)
      oblige GRBL à vider son tampon : la tête s'arrête à chaque allumage, d'où une gravure saccadée ;
    - la commande laser (M3, M4) n'est écrite que quand elle change, et M5 qu'à la fin : GRBL vide aussi son
      tampon à chaque changement M3 / M4 / M5 ;
    - G0 coupe le laser de lui-même ; il porte quand même S0 si le laser était allumé (sans effet sur le
      mouvement), pour qu'un graveur hors mode laser ne brûle pas pendant le trajet ;
    - les mots inchangés (G1, F, X, Y, S) ne sont pas répétés : moins d'octets sur la liaison série, que le
      graveur lit plus vite qu'il ne grave.

    Le premier mouvement écrit tous ses mots. Après des lignes écrites par quelqu'un d'autre, forget()."""

    def __init__(self, lines):
        self.lines = lines
        self.cmd = None
        self.forget()

    def forget(self):
        """État de GRBL inconnu (lignes ajoutées sans passer par ici) : tout sera réécrit."""
        self.motion = self.feed = self.power = self.x = self.y = None
        self._x_text = self._y_text = None    # dernier X / Y écrits, déjà mis en forme (num)

    def extend(self, lines):
        """Ajoute des lignes écrites ailleurs (étiquette de la matrice…), qui se terminent laser éteint."""
        self.lines.extend(lines)
        self.cmd = None
        self.forget()

    def laser(self, cmd):
        """Mode laser `cmd` (« M3 » ou « M4 »), puissance nulle, s'il n'est pas déjà actif."""
        if cmd != self.cmd:
            self.lines.append(f"{cmd} S0")
            self.cmd, self.power = cmd, 0

    def off(self):
        """Laser éteint (M5), en fin de job (ou de partie de job)."""
        self.lines.append("M5")
        self.cmd, self.power = None, 0

    def travel(self, x=None, y=None, comment=""):
        """Déplacement rapide (G0), laser éteint."""
        words = self._axes(x, y)
        if not words:
            return
        if self.power:
            words.append("S0")
            self.power = 0
        self.motion = 0
        self.lines.append(" ".join(["G0"] + words) + (f" ; {comment}" if comment else ""))

    def move(self, x=None, y=None, power=0, feed=None, comment=""):
        """Déplacement gravé (G1) à la puissance S `power` (0 : laser éteint, la tête continue) et à la
        vitesse `feed` (mm/min)."""
        words = self._axes(x, y)
        if not words:
            return
        if feed is not None and feed != self.feed:
            words.append(f"F{num(feed)}")
            self.feed = feed
        if power != self.power:
            words.append(f"S{int(power)}")
            self.power = power
        if self.motion != 1:
            words.insert(0, "G1")
            self.motion = 1
        self.lines.append(" ".join(words) + (f" ; {comment}" if comment else ""))

    def _axes(self, x, y):
        # Chaque coordonnée n'est mise en forme qu'une fois : c'était le plus long d'une image à graver.
        words = []
        if x is not None:
            text = num(x)
            if text != self._x_text:
                words.append("X" + text)
                self.x, self._x_text = x, text
        if y is not None:
            text = num(y)
            if text != self._y_text:
                words.append("Y" + text)
                self.y, self._y_text = y, text
        return words


def start_lines(homing, start_gcode):
    """Lignes de début de job : homing ($H) et G-Code de début, s'ils sont
    demandés."""
    lines = []
    if homing:
        lines.append("$H ; Homing initial")
    start = str(start_gcode or '').strip()
    if start:
        lines.append("; --- G-Code de Début ---")
        lines.append(start)
    return lines
