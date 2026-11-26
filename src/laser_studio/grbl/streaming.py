"""Envoi d'un G-Code à GRBL, partie sans Qt ni port série : quelles lignes envoyer, combien GRBL peut en
recevoir d'un coup, et ce que veut dire chacune de ses réponses.

GRBL reçoit les lignes dans un tampon de 127 octets et répond « ok » pour chaque ligne acceptée (ou
« error:N »). Le protocole « character counting » consiste à envoyer des lignes tant que leur total
(octets envoyés et pas encore acquittés) tient dans ce tampon, puis à attendre les « ok ».
controllers/workers.GCodeStreamerThread fait les lectures et écritures sur le port, au rythme voulu ;
ce module lui dit quoi envoyer et comment lire les réponses. Testable sans machine.

    stream = CharacterCountingStream(gcode_lines(texte))
    while (data := stream.next_to_send()) is not None:
        port.write(data)
        stream.mark_sent()
    if classify(port.readline()) == OK:
        stream.acknowledge()
"""
import math
import re
from collections import deque

# Taille du tampon de réception de GRBL (octets).
RX_BUFFER_SIZE = 127

# Début d'une ligne que GRBL sait lire : un mot G-Code (lettre suivie d'une valeur), une commande « $ »,
# un commentaire « ( », « % » ou une commande temps réel.
_GRBL_LINE_RE = re.compile(r'^(?:[A-Z]\s*[-+.\d]|\$|\(|%|[?!~])', re.IGNORECASE)

# Réponses de GRBL (classify).
EMPTY = "empty"      # ligne vide
OK = "ok"            # ligne acceptée
ERROR = "error"      # « error:N », « ALARM:N » (ou « ERROR: » de certains clones) : ligne refusée, machine à arrêter
STATUS = "status"    # rapport d'état « <Idle|MPos:…> », réponse à « ? »
OTHER = "other"      # message d'information (« [MSG:…] », bannière…)


def gcode_lines(gcode_text):
    """Lignes de la console à envoyer à GRBL. La console mélange le G-Code et les messages de
    l'application (« Connecté à … », « >>> Mode laser GRBL … ») : GRBL refuserait ceux-ci (error:1)
    et l'envoi s'arrêterait, ils sont donc écartés comme les commentaires « ; »."""
    lines = (line.strip() for line in gcode_text.split('\n'))
    return [line for line in lines if is_sent_line(line)]


def is_sent_line(line):
    """La ligne (déjà sans espaces autour) part-elle au graveur ? L'aperçu 2D numérote ses traits avec la même
    règle, pour que le suivi de la gravure tombe sur les lignes que GRBL a acquittées."""
    return bool(line) and not line.startswith(';') and _GRBL_LINE_RE.match(line) is not None


def wire_bytes(line):
    """Octets réellement envoyés pour `line` : « G1 X12.5 S300 ; OVERSCAN_END » part en « G1X12.5S300 ».
    GRBL retire lui-même espaces et commentaires ; sur une image, la liaison série est souvent plus lente
    que la gravure, chaque octet compte. Une ligne avec un commentaire entre parenthèses part telle quelle."""
    if "(" not in line:
        line = line.split(";", 1)[0].replace(" ", "").replace("\t", "")
    return (line + "\n").encode("utf-8")


def classify(response):
    """Nature d'une réponse de GRBL (texte déjà décodé et nettoyé) : EMPTY, OK, ERROR, STATUS ou OTHER."""
    if not response:
        return EMPTY
    if response == 'ok':
        return OK
    if response.startswith(('error', 'ALARM', 'ERROR:')):
        return ERROR
    if response.startswith('<'):
        return STATUS
    return OTHER


class CharacterCountingStream:
    """Suivi de l'envoi de `lines` : la prochaine ligne à envoyer si elle tient dans le tampon de GRBL, les
    lignes envoyées en attente de leur « ok », le nombre de « ok » reçus."""

    def __init__(self, lines, buffer_size=RX_BUFFER_SIZE):
        self.lines = list(lines)
        self.buffer_size = buffer_size
        self.next_index = 0               # prochaine ligne à envoyer
        self.acked = 0                    # « ok » reçus
        self._pending = deque()           # (ligne, octets) envoyées, pas encore acquittées
        self._occupancy = 0

    @property
    def total(self):
        return len(self.lines)

    @property
    def all_sent(self):
        return self.next_index >= len(self.lines)

    @property
    def pending(self):
        """Nombre de lignes envoyées en attente d'un « ok »."""
        return len(self._pending)

    @property
    def occupancy(self):
        """Octets envoyés et pas encore acquittés (place prise dans le tampon de GRBL)."""
        return self._occupancy

    @property
    def first_pending(self):
        """Plus ancienne ligne en attente d'un « ok » (celle que vise la prochaine réponse), ou None."""
        return self._pending[0][0] if self._pending else None

    def next_to_send(self):
        """Octets de la prochaine ligne (avec son saut de ligne) si elle tient dans le tampon, sinon None.
        Le tampon est toujours accepté vide : une ligne trop longue part seule."""
        if self.all_sent:
            return None
        data = wire_bytes(self.lines[self.next_index])
        if self._occupancy + len(data) >= self.buffer_size and self._pending:
            return None
        return data

    def mark_sent(self):
        """La ligne rendue par next_to_send vient d'être écrite sur le port."""
        line = self.lines[self.next_index]
        size = len(wire_bytes(line))
        self._pending.append((line, size))
        self._occupancy += size
        self.next_index += 1
        return line

    def acknowledge(self):
        """Un « ok » reçu : libère la plus ancienne ligne en attente. Renvoie False s'il n'y en avait aucune
        (« ok » inattendu, par exemple la réponse à une commande envoyée avant le job)."""
        if not self._pending:
            return False
        _line, size = self._pending.popleft()
        self._occupancy -= size
        self.acked += 1
        return True


# Blocs que GRBL garde dans son planificateur après les avoir acquittés (15 sur un ATmega328p, l'Arduino des
# graveurs courants) : ils sont perdus à l'arrêt, la reprise repart donc autant de lignes avant la dernière
# acquittée. Quelques traits sont regravés plutôt qu'un trou laissé dans la gravure.
PLANNER_BLOCKS = 15
_WORD_RE = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)", re.IGNORECASE)


# Distance (mm) en dessous de laquelle la position d'arrêt de la tête est « sur » un trait (resume_gcode).
ON_SEGMENT_MM = 0.05


class _GcodeState:
    """État du G-Code au fil des lignes : unités, mode absolu, déplacement, laser, vitesse, puissance, position."""

    def __init__(self):
        self.units, self.absolute, self.motion, self.laser = "G21", True, 0, "M5"
        self.x = self.y = 0.0
        self.feed = self.power = None

    def copy(self):
        state = _GcodeState()
        state.__dict__.update(self.__dict__)
        return state

    def apply(self, line):
        """Avance l'état d'une ligne envoyée ; True si elle déplace la tête en X ou Y."""
        if line.startswith("$"):
            return False
        words = [(letter.upper(), float(value)) for letter, value in _WORD_RE.findall(re.sub(r"\(.*?\)", "", line))]
        moved = False
        for letter, value in words:
            if letter == "G" and value in (0, 1, 2, 3):
                self.motion = int(value)
            elif letter == "G" and value in (20, 21):
                self.units = f"G{int(value)}"
            elif letter == "G" and value in (90, 91):
                self.absolute = value == 90
            elif letter == "M" and value in (3, 4, 5):
                self.laser = f"M{int(value)}"
            elif letter == "F":
                self.feed = value
            elif letter == "S":
                self.power = value
        for letter, value in words:
            if letter == "X":
                self.x, moved = (value if self.absolute else self.x + value), True
            elif letter == "Y":
                self.y, moved = (value if self.absolute else self.y + value), True
        return moved


def _on_segment(point, a, b, tolerance=ON_SEGMENT_MM):
    (px, py), (ax, ay), (bx, by) = point, a, b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) <= tolerance


def resume_gcode(gcode_text, acked, planner_blocks=PLANNER_BLOCKS, head=None):
    """Reprise d'un job arrêté (alarme, arrêt, coupure) après `acked` lignes acquittées : (texte à envoyer,
    numéro de la ligne de reprise à partir de 1, nombre de lignes du job), ou None s'il ne reste rien.

    `head` : position (x, y) de la tête à l'arrêt, telle que GRBL l'a rapportée. Parmi les lignes que GRBL
    pouvait avoir en mémoire, la reprise part de celle dont le trait passe par ce point (la première, s'il y
    en a plusieurs) et la tête y revient : seul le reste du trait est gravé. Sans position, ou si elle n'est
    sur aucun de ces traits (décalage d'origine G92, mode relatif), la reprise repart `planner_blocks` lignes
    avant la dernière acquittée : quelques traits sont regravés plutôt qu'un trou laissé.

    Le texte commence par l'état du G-Code au point de reprise : unités, mode absolu ou relatif, laser éteint
    pendant le retour en G0, puis commande laser, puissance, mode de déplacement et vitesse ; suivent les
    lignes restantes.

    shortcut: G92 (décalage d'origine) et arcs G2 / G3 modaux (sans mot G sur la ligne reprise) ne sont pas
    restitués ; le G-Code généré ici n'en contient pas, à traiter si un fichier importé en a besoin."""
    lines = gcode_lines(gcode_text)
    start = max(0, acked - planner_blocks)
    if start >= len(lines):
        return None
    state = _GcodeState()
    for line in lines[:start]:
        state.apply(line)
    x, y = state.x, state.y
    if head is not None:
        probe = state.copy()
        for index in range(start, min(acked, len(lines))):
            before, (ax, ay) = probe.copy(), (probe.x, probe.y)
            if probe.apply(lines[index]) and before.absolute and _on_segment(head, (ax, ay), (probe.x, probe.y)):
                start, state, (x, y) = index, before, head
                break
    prologue = [state.units, "M5", "G90", f"G0 X{x:.3f} Y{y:.3f}"]
    if not state.absolute:
        prologue.append("G91")
    if state.laser != "M5":
        prologue.append(f"{state.laser} S{state.power:g}" if state.power is not None else state.laser)
    if state.motion in (0, 1):
        prologue.append(f"G{state.motion} F{state.feed:g}" if state.feed is not None else f"G{state.motion}")
    elif state.feed is not None:
        prologue.append(f"F{state.feed:g}")
    return "\n".join(prologue + lines[start:]), start + 1, len(lines)
