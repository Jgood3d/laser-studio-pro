"""Gestionnaire de connexion USB / GRBL."""
import time
import threading
import re
import serial

# Rapport de statut GRBL temps réel, ex : "<Idle|MPos:0.000,0.000,0.000|FS:0,0>"
# ou avec WPos (coordonnées travail) selon le firmware/réglage $10.
_STATUS_RE = re.compile(r'<([A-Za-z]+)[^|>]*\|(?:MPos|WPos):(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)')


class LaserUSBController:
    """Gestionnaire de connexion USB / GRBL"""
    def __init__(self):
        self.ser = None
        self._lock = threading.Lock()
        # Dernier statut connu (mis à jour par CommandThread/GCodeStreamerThread/
        # StatusPollThread dès qu'une ligne "<...>" est reçue) — lu par l'UI
        # pour l'affichage DRO (position/état machine en direct).
        self.last_state = None
        self.last_x = None
        self.last_y = None
        self.last_z = None

    @staticmethod
    def parse_status_line(line):
        """Parse une ligne de rapport de statut GRBL temps réel. Renvoie
        (état, x, y, z) ou None si la ligne ne correspond pas au format
        attendu."""
        m = _STATUS_RE.match(line.strip())
        if not m:
            return None
        state = m.group(1)
        try:
            x, y, z = float(m.group(2)), float(m.group(3)), float(m.group(4))
        except ValueError:
            return None
        return state, x, y, z

    def update_last_status(self, line):
        """Parse une ligne de statut et met à jour last_state/x/y/z si elle
        est valide. Renvoie le tuple parsé (ou None)."""
        parsed = self.parse_status_line(line)
        if parsed:
            self.last_state, self.last_x, self.last_y, self.last_z = parsed
        return parsed

    def query_status(self, timeout=0.5):
        """Envoie une requête de statut temps réel ('?', un seul caractère —
        GRBL y répond immédiatement sans consommer le buffer RX du G-Code en
        cours, contrairement à une commande classique terminée par '\\n') et
        lit la réponse. Réservé à l'utilisation hors streaming actif (voir
        StatusPollThread) : pendant un job, c'est GCodeStreamerThread qui
        interroge lui-même périodiquement, pour éviter toute concurrence
        d'accès au port série entre deux threads."""
        with self._lock:
            if not (self.ser and self.ser.is_open):
                return None
            try:
                self.ser.write(b'?')
                start = time.time()
                while time.time() - start < timeout:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('<'):
                        return self.update_last_status(line)
                return None
            except Exception:
                return None

    def is_connected(self):
        return bool(self.ser and self.ser.is_open)

    def connect(self, port, baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)
            self.ser.write(b"\r\n\r\n")
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            return True
        except Exception as e:
            print(f"Erreur connexion : {e}")
            self.ser = None
            return False

    def disconnect(self):
        with self._lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = None
        self.last_state = None
        self.last_x = None
        self.last_y = None
        self.last_z = None

    def send_command(self, cmd):
        with self._lock:
            if not (self.ser and self.ser.is_open):
                return "Non connecté"
            try:
                self.ser.write(f"{cmd.strip()}\n".encode('utf-8'))
                response_lines = []
                start_time = time.time()
                while True:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        if line == 'ok' or line.startswith('error') or line.startswith('ALARM'):
                            break
                    if time.time() - start_time > 2.0:
                        break
                return "\n".join(response_lines) if response_lines else "Pas de réponse"
            except Exception as e:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                return f"ERROR: Connexion perdue ({e})"

    def send_raw_byte(self, raw_bytes):
        with self._lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(raw_bytes)
                    self.ser.flush()
                except Exception as e:
                    print(f"Erreur envoi commande temps réel : {e}")
