"""Connexion au graveur : port série, threads de dialogue avec GRBL, état
« référencé » (homing fait depuis la connexion). Sans aucune boîte de
dialogue : la fenêtre s'abonne à ses signaux et affiche ce qu'il faut.

    connection = MachineConnection(parent=window)
    connection.status_updated.connect(window._on_status_updated)
    connection.connection_changed.connect(window.update_connection_widgets)
    if connection.connect("/dev/ttyUSB0"):
        settings = connection.read_settings()      # {"$22": "1", "$32": "1", ...}
        connection.home()

Pendant un job (start_stream), c'est le thread d'envoi qui interroge l'état
du graveur ; le sondage périodique est alors mis en pause par l'appelant
(pause_status_poll / resume_status_poll), comme le fait la file d'attente.
"""

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger
from laser_studio.grbl.connection import LaserUSBController
from laser_studio.workers import (
    CommandThread, GCodeStreamerThread, ReconnectThread, StatusPollThread,
)

log = get_logger()

# Octets temps réel GRBL.
FEED_HOLD = b"!"
CYCLE_START = b"~"
SOFT_RESET = b"\x18"


def parse_grbl_settings(response):
    """Réponse de « $$ » -> {"$32": "1", "$22": "0", ...} (commentaires
    « (...) » ignorés)."""
    grbl_settings = {}
    for line in (response or "").splitlines():
        line = line.strip()
        if line.startswith("$") and "=" in line:
            key, value = line.split("=", 1)
            grbl_settings[key.strip()] = value.split("(", 1)[0].strip()
    return grbl_settings


class MachineConnection(QObject):
    """Dialogue avec le graveur GRBL.

    Signaux :
    - connection_changed(bool) : port ouvert ou fermé (connexion,
      déconnexion, câble débranché, reconnexion automatique) ;
    - status_updated(état, x, y, z) : état et position du graveur, en
      continu (sondage hors job, thread d'envoi pendant un job) ;
    - log(texte) : échanges et événements à afficher à l'utilisateur ;
    - position_lost() : la position n'est plus fiable (reset en mouvement,
      arrêt sur erreur, reconnexion) : un nouveau homing est nécessaire ;
    - stream_progress(lignes, total), stream_lines_sent(lignes),
      stream_lines_acked(nombre) : avancement du job en cours ;
    - reconnecting() / reconnected(réussi) : coupure USB pendant un job et
      tentative de réouverture du port (le job, lui, n'est jamais relancé).
    """

    connection_changed = pyqtSignal(bool)
    status_updated = pyqtSignal(str, float, float, float)
    log = pyqtSignal(str)
    position_lost = pyqtSignal()
    stream_progress = pyqtSignal(int, int)
    stream_lines_sent = pyqtSignal(list)
    stream_lines_acked = pyqtSignal(int)
    reconnecting = pyqtSignal()
    reconnected = pyqtSignal(bool)

    def __init__(self, usb=None, parent=None):
        super().__init__(parent)
        self.usb = usb if usb is not None else LaserUSBController()
        # Homing fait depuis la connexion : sinon, la fenêtre demande
        # confirmation avant un job (position non référencée).
        self.homed = False
        # Dernier G-Code réellement envoyé (« Répéter le dernier job »).
        self.last_sent_gcode = None
        self.streamer = None
        self._status_poll = None
        self._cmd_thread = None
        self._reconnect_thread = None

    # -- état

    def is_connected(self):
        return self.usb.is_connected()

    @property
    def last_state(self):
        """Dernier état GRBL connu (« Idle », « Run », « Alarm »...)."""
        return getattr(self.usb, "last_state", None)

    @property
    def port(self):
        """Port de la dernière connexion réussie."""
        return getattr(self.usb, "last_port", None)

    def is_streaming(self):
        """Vrai pendant l'envoi d'un job."""
        try:
            return bool(self.streamer is not None and self.streamer.isRunning())
        except RuntimeError:          # thread Qt déjà détruit
            return False

    def _forget_homing(self):
        if self.homed:
            self.homed = False
        self.position_lost.emit()

    # -- connexion

    def connect(self, port):
        """Ouvre `port` et lance le sondage de l'état. Faux si le port ne
        s'ouvre pas."""
        if not self.usb.connect(port):
            return False
        self.homed = False
        self.start_status_poll()
        self.connection_changed.emit(True)
        return True

    def disconnect(self):
        self.stop_status_poll()
        self.usb.disconnect()
        self.homed = False
        self.connection_changed.emit(False)

    # -- commandes

    def send_command(self, cmd):
        """Envoie `cmd` et attend la réponse de GRBL (bloquant, quelques
        secondes au plus). Peut lever une exception (port fermé...)."""
        return self.usb.send_command(cmd)

    def read_settings(self):
        """Réglages du graveur ($$) : {"$22": "1", ...} ; {} si le graveur
        ne répond pas. Peut lever une exception (port fermé...)."""
        response = self.send_command("$$")
        log.info("Connexion : réponse à $$ (%d caractères)", len(response or ""))
        return parse_grbl_settings(response)

    def run_commands(self, commands):
        """Envoie une commande ou une liste de commandes en arrière-plan,
        réponses dans le signal log. Faux (rien n'est envoyé) si un envoi de
        commandes est déjà en cours."""
        if self._cmd_thread is not None and self._cmd_thread.isRunning():
            return False
        self._cmd_thread = CommandThread(self.usb, commands)
        self._cmd_thread.log_signal.connect(self.log)
        self._cmd_thread.start()
        return True

    def home(self):
        """Cycle de homing ($H) : la position devient référencée."""
        self.run_commands("$H")
        self.homed = True

    def jog(self, dx_mm, dy_mm, speed):
        """Déplacement relatif de `dx_mm`, `dy_mm`, à `speed` mm/min."""
        self.run_commands(f"$J=G91 G21 X{dx_mm:.3f} Y{dy_mm:.3f} F{speed}")

    def unlock(self):
        """Déverrouillage après une alarme ($X)."""
        self.run_commands("$X")

    def pause(self):
        self.usb.send_raw_byte(FEED_HOLD)

    def resume(self):
        self.usb.send_raw_byte(CYCLE_START)

    def soft_reset(self):
        """Reset logiciel GRBL (0x18), commun à RESET et KILL : arrête
        l'envoi en cours puis réinitialise le contrôleur.

        Si la machine n'était PAS à l'arrêt complet (job en cours, pause,
        jog, état inconnu), GRBL perd sa position (ALARM:3 « Reset while in
        motion ») : le statut « référencé » est retiré (signal
        position_lost) pour que le prochain job redemande un homing. Un
        reset fait machine à l'arrêt (Idle) ne change rien.

        Renvoie True si la position a été perdue."""
        streaming = self.is_streaming()
        was_idle = (not streaming) and self.last_state == "Idle"
        if streaming:
            self.streamer.stop()
        self.usb.send_raw_byte(SOFT_RESET)
        if not was_idle:
            self._forget_homing()
        return not was_idle

    # -- sondage de l'état (hors job)

    def start_status_poll(self):
        """Interroge l'état du graveur (« ? ») à intervalles réguliers."""
        self.stop_status_poll()
        self._status_poll = StatusPollThread(self.usb)
        self._status_poll.status_updated.connect(self.status_updated)
        # Port perdu hors job (câble débranché...).
        self._status_poll.connection_lost.connect(
            lambda: self.connection_changed.emit(self.is_connected()))
        self._status_poll.start()

    def stop_status_poll(self):
        if self._status_poll is not None:
            self._status_poll.stop()
            self._status_poll.wait(1000)
            self._status_poll = None

    def pause_status_poll(self):
        """Pendant un envoi, c'est le thread d'envoi qui interroge l'état."""
        if self._status_poll is not None:
            self._status_poll.pause()

    def resume_status_poll(self):
        if self._status_poll is not None:
            self._status_poll.resume()

    # -- envoi d'un job

    def start_stream(self, gcode_text, on_finished):
        """Lance l'envoi de `gcode_text` (GCodeStreamerThread).
        `on_finished(fin_propre)` est appelée à la fin. Avancement, état et
        messages passent par les signaux stream_*, status_updated et log."""
        self.last_sent_gcode = gcode_text
        self.streamer = GCodeStreamerThread(self.usb, gcode_text)
        self.streamer.lines_sent.connect(self.stream_lines_sent)
        self.streamer.lines_acked.connect(self.stream_lines_acked)
        self.streamer.progress.connect(self.stream_progress)
        self.streamer.log_signal.connect(self.log)
        self.streamer.status_updated.connect(self.status_updated)
        self.streamer.finished_signal.connect(on_finished)
        self.streamer.connection_lost.connect(self._on_stream_connection_lost)
        self.streamer.start()
        return self.streamer

    def check_position_after_stream(self):
        """Après un job arrêté sur erreur GRBL : si le reset a eu lieu
        machine encore en mouvement, la position n'est plus fiable (signal
        position_lost). Renvoie True dans ce cas."""
        if self.streamer is not None and getattr(self.streamer, "position_lost", False):
            self._forget_homing()
            return True
        return False

    def _on_stream_connection_lost(self):
        """Coupure USB pendant un job : rouvre le même port en arrière-plan.
        Le job reste arrêté : seule la LIAISON est rétablie, jamais l'envoi
        du G-Code (la position réelle n'est plus fiable)."""
        port = self.port
        if not port:
            return
        self.reconnecting.emit()
        self._reconnect_thread = ReconnectThread(
            self.usb, port, getattr(self.usb, "last_baudrate", 115200))
        self._reconnect_thread.reconnected.connect(self._on_reconnect_result)
        self._reconnect_thread.start()

    def _on_reconnect_result(self, success):
        if success:
            self.homed = False
            self.start_status_poll()
        self.connection_changed.emit(self.is_connected())
        self.reconnected.emit(success)

    def shutdown(self):
        """Fermeture de l'application : arrête le sondage."""
        self.stop_status_poll()
