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
    return [line for line in lines if line and not line.startswith(';') and _GRBL_LINE_RE.match(line)]


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
        data = (self.lines[self.next_index] + '\n').encode('utf-8')
        if self._occupancy + len(data) >= self.buffer_size and self._pending:
            return None
        return data

    def mark_sent(self):
        """La ligne rendue par next_to_send vient d'être écrite sur le port."""
        line = self.lines[self.next_index]
        size = len((line + '\n').encode('utf-8'))
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
