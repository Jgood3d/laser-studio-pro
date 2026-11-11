"""Graveur GRBL simulé, pour tester l'application sans machine.

Activé par la variable d'environnement LASER_STUDIO_SIMULATION : un port « SIMULATION » apparaît alors dans la
liste des ports, et s'y connecter ouvre SimulatedGrblSerial au lieu d'un vrai port série. La valeur
de la variable est le facteur de vitesse de la simulation : LASER_STUDIO_SIMULATION=1 (temps réel),
LASER_STUDIO_SIMULATION=20 (vingt fois plus vite).

SimulatedGrblSerial imite la partie de pyserial utilisée par l'application (write, readline,
in_waiting, is_open, reset_input_buffer, flush, close) et le protocole GRBL 1.1 :
- une réponse « ok » / « error:N » par ligne, et un planificateur de 15 mouvements : les « ok »
  n'arrivent que quand il y a de la place, comme sur une vraie carte ;
- des mouvements G0/G1/G2/G3 qui prennent le temps qu'ils prendraient (distance / vitesse) ;
- les commandes temps réel : « ? » (rapport d'état), « ! » (pause), « ~ » (reprise),
  Ctrl+X (reset, ALARM:3 si la machine bougeait), annulation de jog (0x85) ;
- les commandes $ : $$ (réglages, modifiables par $N=valeur), $H (homing), $X (déverrouillage),
  $I (version), $J= (jog).
"""
import os
import re
import threading
import time

SIMULATED_PORT = "SIMULATION"
WELCOME = "Grbl 1.1h ['$' for help]"
PLANNER_SIZE = 15
RAPID_FEED = 6000.0            # mm/min, vitesse des déplacements G0
DEFAULT_FEED = 1000.0          # mm/min, si aucun F n'a été donné
HOMING_SECONDS = 2.0
HOLD_DECEL_SECONDS = 0.1       # Hold:1 (décélération) puis Hold:0 (arrêt complet)

DEFAULT_SETTINGS = {
    "$0": "10", "$1": "25", "$2": "0", "$3": "0", "$4": "0", "$5": "0", "$6": "0",
    "$10": "1", "$11": "0.010", "$12": "0.002", "$13": "0", "$20": "0", "$21": "0",
    "$22": "1", "$23": "0", "$24": "25.000", "$25": "500.000", "$26": "250", "$27": "1.000",
    "$30": "1000", "$31": "0", "$32": "1",
    "$100": "80.000", "$101": "80.000", "$102": "250.000",
    "$110": "6000.000", "$111": "6000.000", "$112": "500.000",
    "$120": "500.000", "$121": "500.000", "$122": "10.000",
    "$130": "400.000", "$131": "400.000", "$132": "0.000",
}

_WORD_RE = re.compile(r"([A-Z])([-+]?(?:\d+\.?\d*|\.\d+))")
_LINE_RE = re.compile(r"(?:[A-Z][-+]?(?:\d+\.?\d*|\.\d+))+")


def simulation_speed():
    """Facteur de vitesse lu dans LASER_STUDIO_SIMULATION, ou None si la simulation est désactivée."""
    value = os.environ.get("LASER_STUDIO_SIMULATION", "").strip().lower()
    if value in ("", "0", "false", "no", "non"):
        return None
    try:
        speed = float(value)
    except ValueError:
        return 1.0                 # LASER_STUDIO_SIMULATION=oui, true... : temps réel
    return speed if speed > 0 else 1.0


def simulation_enabled():
    return simulation_speed() is not None


class _Block:
    """Mouvement (ou pause G4, ou cycle de homing) du planificateur."""

    def __init__(self, target, duration, feed, laser, ack_when_done=False):
        self.target = target
        self.duration = duration
        self.feed = feed
        self.laser = laser
        self.ack_when_done = ack_when_done   # $H : « ok » seulement à la fin du cycle
        self.start_pos = None


class SimulatedGrblSerial:
    """Faux port série qui se comporte comme une carte GRBL 1.1 (voir le docstring du module)."""

    def __init__(self, port=SIMULATED_PORT, baudrate=115200, timeout=1, speed=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.speed = speed
        self.is_open = True
        self.settings = dict(DEFAULT_SETTINGS)
        self._lock = threading.RLock()
        self._out = bytearray()
        self._rx = ""
        self._pending = []             # lignes reçues, pas encore acceptées (planificateur plein)
        self._planner = []
        self._block_start = None       # instant (simulé) du début du mouvement en tête
        self._event_time = None        # instant simulé où le planificateur s'est libéré (_advance)
        self._clock = 0.0              # temps simulé
        self._last_real = time.monotonic()
        self._pos = [0.0, 0.0, 0.0]
        self._absolute = True
        self._inches = False
        self._motion = 0
        self._feed = 0.0
        self._spindle = 0.0
        self._laser_on = False
        self._alarm = False
        self._hold = False
        self._hold_since = None
        self._emit(WELCOME)

    # --- interface pyserial -------------------------------------------------------------
    @property
    def in_waiting(self):
        with self._lock:
            self._advance()
            return len(self._out)

    def write(self, data):
        if not self.is_open:
            raise OSError("port simulé fermé")
        with self._lock:
            self._advance()
            for byte in bytes(data):
                char = chr(byte)
                if char == "?":
                    self._emit(self._status_report())
                elif char == "!":
                    self._feed_hold()
                elif char == "~":
                    self._cycle_start()
                elif byte == 0x18:
                    self._soft_reset()
                elif byte == 0x85:
                    self._jog_cancel()
                elif byte >= 0x80:
                    pass                   # autres commandes temps réel (surcharges) : ignorées
                elif char == "\n":
                    self._pending.append(self._rx.strip())
                    self._rx = ""
                elif char != "\r":
                    self._rx += char
            self._process_pending()
        return len(data)

    def readline(self):
        deadline = time.monotonic() + (self.timeout if self.timeout is not None else 1e9)
        while True:
            with self._lock:
                self._advance()
                newline = self._out.find(b"\n")
                if newline != -1:
                    line = bytes(self._out[:newline + 1])
                    del self._out[:newline + 1]
                    return line
            if not self.is_open or time.monotonic() >= deadline:
                return b""
            time.sleep(0.005)

    def read(self, size=1):
        with self._lock:
            self._advance()
            data = bytes(self._out[:size])
            del self._out[:size]
            return data

    def reset_input_buffer(self):
        with self._lock:
            self._advance()
            self._out.clear()

    def flush(self):
        pass

    def close(self):
        self.is_open = False

    # --- état et rapports ---------------------------------------------------------------
    def _emit(self, line):
        self._out += (line + "\r\n").encode("utf-8")

    def _state(self):
        if self._alarm:
            return "Alarm"
        if self._hold:
            decel_done = self._hold_since is not None and \
                self._clock - self._hold_since >= HOLD_DECEL_SECONDS
            return "Hold:0" if decel_done or not self._planner else "Hold:1"
        if self._planner:
            return "Home" if self._planner[0].ack_when_done else "Run"
        return "Idle"

    def _status_report(self):
        x, y, z = self._pos
        moving = bool(self._planner) and not self._hold
        feed = self._planner[0].feed if moving else 0
        spindle = self._planner[0].laser if moving else 0
        return f"<{self._state()}|MPos:{x:.3f},{y:.3f},{z:.3f}|FS:{feed:.0f},{spindle:.0f}>"

    # --- temps simulé ---------------------------------------------------------------------
    def _advance(self):
        """Fait avancer le temps simulé jusqu'à maintenant : mouvements terminés, « ok » différés,
        lignes en attente acceptées au moment simulé exact où le planificateur se libère."""
        now = time.monotonic()
        self._clock += (now - self._last_real) * self.speed
        self._last_real = now
        while True:
            self._process_pending()
            if not self._planner or self._hold:
                break
            block = self._planner[0]
            if self._block_start is None:
                self._block_start = self._clock
            if block.start_pos is None:
                block.start_pos = list(self._pos)
            elapsed = self._clock - self._block_start
            if elapsed < block.duration:
                ratio = elapsed / block.duration
                self._pos = [s + (t - s) * ratio for s, t in zip(block.start_pos, block.target)]
                break
            self._pos = list(block.target)
            self._planner.pop(0)
            if block.ack_when_done:
                self._emit("ok")
            # Le mouvement suivant (déjà planifié ou accepté juste après) part de cet instant-là.
            self._block_start += block.duration
            self._event_time = self._block_start
        self._event_time = None

    def _process_pending(self):
        while self._pending:
            line = self._pending[0]
            if line.startswith("$") and not line.upper().startswith("$J="):
                # Commandes système : exécutées machine à l'arrêt, comme sur GRBL.
                if self._planner:
                    return
                self._pending.pop(0)
                self._system_command(line)
                continue
            if len(self._planner) >= PLANNER_SIZE:
                return
            self._pending.pop(0)
            self._emit(self._gcode_line(line))

    # --- commandes ------------------------------------------------------------------------
    def _system_command(self, line):
        command = line.upper().replace(" ", "")
        if command == "$$":
            for key in sorted(self.settings, key=lambda k: int(k[1:])):
                self._emit(f"{key}={self.settings[key]}")
            self._emit("ok")
        elif command == "$I":
            self._emit("[VER:1.1h.20190825:SIMULATION]")
            self._emit("ok")
        elif command == "$X":
            self._alarm = False
            self._emit("[MSG:Caution: Unlocked]")
            self._emit("ok")
        elif command.startswith("$H"):
            if self.settings.get("$22") != "1":
                self._emit("error:5")
                return
            self._alarm = False
            self._hold = False
            self._append_block(_Block([0.0, 0.0, 0.0], HOMING_SECONDS, 0.0, 0.0, ack_when_done=True))
        elif re.fullmatch(r"\$\d+=[-+]?[\d.]+", command):
            key, value = command.split("=", 1)
            self.settings[key] = value
            self._emit("ok")
        elif command in ("$G", "$#", "$N", "$C"):
            self._emit("ok")
        else:
            self._emit("error:3")

    def _gcode_line(self, line):
        """Exécute une ligne de G-Code (ou de jog $J=) ; renvoie la réponse « ok » / « error:N »."""
        text = re.sub(r"\(.*?\)", "", line.split(";", 1)[0]).upper().replace(" ", "")
        jog = text.startswith("$J=")
        if jog:
            text = text[3:]
        if not text:
            return "ok"
        if not _LINE_RE.fullmatch(text):
            return "error:1"                         # « Expected command letter »
        if self._alarm:
            return "error:9"                         # G-Code verrouillé en état d'alarme
        words = _WORD_RE.findall(text)
        absolute, inches = self._absolute, self._inches
        motion = self._motion
        for letter, value in words:
            number = float(value)
            if letter == "G":
                if number in (0, 1, 2, 3):
                    motion = int(number)
                elif number == 90:
                    absolute = True
                elif number == 91:
                    absolute = False
                elif number == 20:
                    inches = True
                elif number == 21:
                    inches = False
                elif number == 4:
                    dwell = next((float(v) for l, v in words if l == "P"), 0.0)
                    self._append_block(_Block(list(self._pos), dwell, 0.0, 0.0))
            elif letter == "M":
                if number in (3, 4):
                    self._laser_on = True
                elif number == 5:
                    self._laser_on = False
            elif letter == "S":
                self._spindle = number
            elif letter == "F":
                self._feed = number * (25.4 if inches else 1.0)
        if not jog:
            self._absolute, self._inches, self._motion = absolute, inches, motion
        axes = {l: float(v) * (25.4 if inches else 1.0) for l, v in words if l in "XYZ"}
        if axes:
            target = list(self._pos_after_planner())
            for i, axis in enumerate("XYZ"):
                if axis in axes:
                    target[i] = axes[axis] if absolute else target[i] + axes[axis]
            start = self._pos_after_planner()
            distance = sum((t - s) ** 2 for s, t in zip(start, target)) ** 0.5
            feed = RAPID_FEED if motion == 0 and not jog else (self._feed or DEFAULT_FEED)
            laser = self._spindle if self._laser_on and motion != 0 else 0.0
            self._append_block(_Block(target, distance / (feed / 60.0), feed, laser))
        return "ok"

    def _append_block(self, block):
        """Ajoute un mouvement au planificateur ; s'il est seul, il démarre tout de suite."""
        if not self._planner and not self._hold:
            self._block_start = self._event_time if self._event_time is not None else self._clock
            block.start_pos = list(self._pos)
        self._planner.append(block)

    def _pos_after_planner(self):
        return list(self._planner[-1].target) if self._planner else list(self._pos)

    # --- temps réel -----------------------------------------------------------------------
    def _feed_hold(self):
        if self._planner and not self._hold and not self._planner[0].ack_when_done:
            self._split_current_block()
            self._hold = True
            self._hold_since = self._clock

    def _cycle_start(self):
        if self._hold:
            self._hold = False
            self._hold_since = None
            self._block_start = self._clock
            if self._planner:
                self._planner[0].start_pos = list(self._pos)   # repart d'où il s'est arrêté

    def _split_current_block(self):
        """Le mouvement en cours repart de la position actuelle avec le temps qu'il lui reste."""
        block = self._planner[0]
        if self._block_start is not None:
            elapsed = self._clock - self._block_start
            block.duration = max(block.duration - elapsed, 0.0)
        self._block_start = None

    def _jog_cancel(self):
        if self._planner and not self._planner[0].ack_when_done:
            self._planner.clear()
            self._block_start = None

    def _soft_reset(self):
        was_moving = bool(self._planner) and self._state() not in ("Hold:0",)
        self._planner.clear()
        self._pending.clear()
        self._rx = ""
        self._block_start = None
        self._hold = False
        self._hold_since = None
        self._laser_on = False
        self._absolute, self._inches, self._motion = True, False, 0
        if was_moving:
            self._alarm = True
            self._emit("ALARM:3")
        self._emit(WELCOME)
        if self._alarm:
            self._emit("[MSG:'$H'|'$X' to unlock]")
