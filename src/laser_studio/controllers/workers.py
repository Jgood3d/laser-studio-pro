"""Threads d'arrière-plan (QThread) : traitement d'image, streaming G-Code,
génération du G-Code (job et matrice de test), exécution de commandes.

La génération du G-Code elle-même est dans le paquet gcode/ (sans Qt) :
AdvancedGCodeWorker et TestMatrixWorker ne font que l'appeler dans un thread."""
import time

import numpy as np

from PyQt6.QtCore import QThread, pyqtSignal

from laser_studio.core.debug_log import get_logger

log = get_logger()

from laser_studio.gcode.job import build_job_gcode
from laser_studio.gcode.test_matrix import build_test_matrix_gcode
from laser_studio.grbl.streaming import (
    EMPTY, ERROR, OK, STATUS, CharacterCountingStream, classify, gcode_lines,
)
from laser_studio.i18n import tr
# Calculs sans Qt, réexportés ici pour le code existant (anciens noms).
from laser_studio.image.dithering import process_image


class ImageProcessingWorker(QThread):
    """Traitement et tramage de l'image dans un thread (image.dithering.process_image) :
    l'interface reste fluide pendant les tramages lents (Stucki, Jarvis)."""
    finished = pyqtSignal(np.ndarray, object)

    def __init__(self, raw_image, params):
        super().__init__()
        self.raw_image = raw_image
        self.params = params

    def run(self):
        result = process_image(self.raw_image, self.params)
        if result is not None:
            self.finished.emit(*result)


class GCodeStreamerThread(QThread):
    """Thread d'envoi séquentiel du G-Code à GRBL : lectures et écritures sur le port, au bon rythme. Ce qu'il
    faut envoyer et ce que veulent dire les réponses est dans grbl/streaming.py (CharacterCountingStream,
    classify), sans Qt."""
    progress = pyqtSignal(int, int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    # DRO pendant le streaming : (état, x, y, z), à partir des rapports de
    # statut GRBL ("<...>") obtenus par requêtes '?' périodiques envoyées
    # par ce même thread (voir _status_poll_interval) — pas de thread séparé
    # pendant un job actif, pour ne jamais se disputer l'accès au port série.
    status_updated = pyqtSignal(str, float, float, float)
    connection_lost = pyqtSignal()
    # Lignes envoyées à GRBL, par paquets (au plus ~10 émissions par seconde, voir
    # _flush_sent_lines) : un signal par ligne saturerait l'interface sur un long job.
    lines_sent = pyqtSignal(list)
    # Nombre de lignes acceptées par GRBL (« ok » reçus), au même rythme : sert à suivre la
    # gravure en temps réel sur l'aperçu 2D (voir Preview2DTab.update_burn).
    lines_acked = pyqtSignal(int)
    SENT_LINES_INTERVAL = 0.1

    def __init__(self, usb_controller, gcode_text):
        super().__init__()
        self.usb = usb_controller
        self.stream = CharacterCountingStream(gcode_lines(gcode_text))
        self.lines = self.stream.lines
        self.is_running = True
        self._stopped_by_user = False
        # Secondes entre deux requêtes '?' pendant le job : 5 par seconde (limite conseillée par GRBL),
        # pour que le point rouge de l'aperçu 2D suive la tête sans à-coups.
        self._status_poll_interval = 0.2
        # Fin de job : GRBL répond « ok » dès qu'il a ACCEPTÉ une ligne, pas
        # quand le mouvement est terminé. Après le dernier « ok », on attend
        # donc que la machine repasse à l'état Idle avant d'annoncer la fin.
        self._idle_poll_interval = 0.2    # secondes entre deux requêtes '?' pendant l'attente
        self._idle_reply_timeout = 8.0    # aucun rapport de statut pendant ce délai : liaison considérée perdue
        # Arrêt de la machine sur erreur GRBL (voir _stop_machine_after_error).
        self._hold_timeout = 3.0          # délai maxi pour que le feed hold soit complet (Hold:0)
        self.stopped_on_error = False     # True si la machine a été arrêtée suite à une erreur GRBL
        self.position_lost = False        # True si ce reset a eu lieu machine encore en mouvement
        self._sent_batch = []
        self._last_sent_emit = 0.0
        self._acked_emitted = 0

    @property
    def acked(self):
        """« ok » reçus depuis le début du job."""
        return self.stream.acked

    @property
    def stopped_by_user(self):
        """Vrai si l'envoi a été arrêté par l'utilisateur (Reset, arrêt d'urgence)."""
        return self._stopped_by_user

    def _flush_sent_lines(self, force=False):
        """Émet les lignes envoyées et le nombre de « ok » reçus depuis la dernière émission
        (toutes les SENT_LINES_INTERVAL s, ou tout de suite si `force`)."""
        now = time.time()
        if not force and now - self._last_sent_emit < self.SENT_LINES_INTERVAL:
            return
        if self._sent_batch:
            self.lines_sent.emit(self._sent_batch)
            self._sent_batch = []
        if self.acked != self._acked_emitted:
            self.lines_acked.emit(self.acked)
            self._acked_emitted = self.acked
        self._last_sent_emit = now

    def stop(self):
        log.info("Streamer : arrêt demandé par l'utilisateur")
        self.is_running = False
        self._stopped_by_user = True

    def _stop_machine_after_error(self, ser):
        """GRBL vient de refuser une ligne (error:N) : il continue pourtant d'exécuter les lignes
        déjà acceptées dans son buffer (jusqu'à 127 caractères : déplacements, laser allumé...).
        On arrête donc la machine :
        1. feed hold (« ! ») : décélération sans perte de pas, laser coupé en mode laser ($32=1) ;
        2. attente de l'arrêt complet (Hold:0, ou Idle s'il n'y avait plus rien à exécuter) ;
        3. reset logiciel (0x18) : vide le buffer de GRBL et coupe le laser.
        Si l'arrêt complet n'est pas confirmé à temps (ou en cas d'ALARM), le reset a lieu quand
        même et la position est considérée perdue (position_lost) : un homing sera reproposé.
        Doit être appelée HORS du verrou du port série (elle le prend elle-même)."""
        self.stopped_on_error = True
        stopped = False
        try:
            with self.usb._lock:
                ser.write(b'!')
            deadline = time.time() + self._hold_timeout
            last_poll = 0.0
            while not stopped and time.time() < deadline:
                with self.usb._lock:
                    now = time.time()
                    if now - last_poll >= self._idle_poll_interval:
                        ser.write(b'?')
                        last_poll = now
                    while ser.in_waiting > 0:
                        resp = ser.readline().decode('utf-8', errors='ignore').strip()
                        if resp.startswith('<'):
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                            if resp.startswith('<Hold:0') or resp.startswith('<Idle'):
                                stopped = True
                        if resp.startswith('ALARM') or resp.startswith('<Alarm'):
                            deadline = 0      # GRBL s'est déjà arrêté seul, position non garantie
                time.sleep(0.02)
            with self.usb._lock:
                ser.write(b'\x18')
        except Exception:
            log.warning("Arrêt du job : séquence d'arrêt interrompue", exc_info=True)
            stopped = False
        self.position_lost = not stopped
        self.log_signal.emit(tr("laser.error_stop_log"))

    def _wait_until_idle(self, ser):
        """Attend que GRBL passe à l'état Idle (planificateur vide, plus aucun
        mouvement). Tant que la machine est en mouvement (Run, Hold, Jog...)
        on attend sans limite de durée : un dernier trajet lent peut être long,
        et l'utilisateur garde la main (Reset/Stop). Renvoie True si Idle est
        atteint ; False en cas d'alarme, d'arrêt demandé ou si GRBL cesse de
        répondre. Lève une exception si le port se ferme."""
        last_poll = 0.0
        last_reply = time.time()
        last_logged_state = None
        log.info("Streamer : tous les « ok » reçus, attente de l'état Idle")
        while self.is_running:
            state = None
            with self.usb._lock:
                if not (ser and ser.is_open):
                    raise Exception("Connexion perdue")
                now = time.time()
                if now - last_poll >= self._idle_poll_interval:
                    try:
                        ser.write(b'?')
                    except Exception:   # plusieurs fois par seconde : la coupure est vue au tour suivant
                        pass
                    last_poll = now
                while ser.in_waiting > 0:
                    resp = ser.readline().decode('utf-8', errors='ignore').strip()
                    log.debug("RX (attente Idle) %r", resp)
                    if resp.startswith('<'):
                        parsed = self.usb.update_last_status(resp)
                        if parsed:
                            last_reply = time.time()
                            state = parsed[0]
                            self.status_updated.emit(*parsed)
                    elif resp.startswith('ALARM') or resp.startswith('error'):
                        log.error("Streamer : %s pendant l'attente de Idle", resp)
                        self.log_signal.emit(f"!!! ERREUR GRBL : {resp}")
                        return False
            if state is not None and state != last_logged_state:
                log.info("Streamer : état GRBL %s", state)
                last_logged_state = state
            if state == 'Idle':
                return True
            if state == 'Alarm':
                self.log_signal.emit("!!! GRBL en état ALARM à la fin du job")
                return False
            if time.time() - last_reply > self._idle_reply_timeout:
                log.error("Streamer : aucun rapport de statut depuis %.1f s (attente de Idle)",
                          self._idle_reply_timeout)
                self.log_signal.emit("!!! GRBL ne répond plus (attente de la fin du mouvement)")
                return False
            time.sleep(0.02)
        return False

    def run(self):
        total = len(self.lines)
        clean_finish = True
        t_start = time.time()
        log.info("Streamer : démarrage, %d lignes à envoyer", total)
        if total == 0:
            log.warning("Streamer : aucune ligne à envoyer (G-Code vide ou uniquement des commentaires)")

        with self.usb._lock:
            if not (self.usb.ser and self.usb.ser.is_open):
                log.error("Streamer : port série fermé au démarrage (ser=%r), fin immédiate", self.usb.ser)
                self.finished_signal.emit(False)
                return
            ser = self.usb.ser
            log.info("Streamer : port %s, %d baud, %d octet(s) en attente avant purge",
                     getattr(ser, "port", "?"), getattr(ser, "baudrate", 0), ser.in_waiting)
            try:
                ser.reset_input_buffer()
            except Exception:
                log.exception("Streamer : échec de reset_input_buffer")

        stream = self.stream
        last_status_poll = time.time()
        # Diagnostic : compteurs et détection d'un envoi bloqué (plus aucune réponse de GRBL).
        ok_count = 0
        last_rx = time.time()
        last_stall_log = 0.0
        STALL_WARNING_S = 5.0
        grbl_error = False
        try:
            while not stream.all_sent and self.is_running:
                # Autant de lignes que le tampon de GRBL peut en recevoir (character counting).
                while self.is_running:
                    data = stream.next_to_send()
                    if data is None:
                        break
                    with self.usb._lock:
                        if not (ser and ser.is_open):
                            raise Exception("Connexion perdue")
                        ser.write(data)
                    line = stream.mark_sent()
                    log.debug("TX #%d %r (buffer %d/%d)", stream.next_index, line, stream.occupancy,
                              stream.buffer_size)
                    self._sent_batch.append(line)

                with self.usb._lock:
                    if not (ser and ser.is_open):
                        raise Exception("Connexion perdue")

                    # Requête de statut temps réel ('?', un seul caractère non
                    # bufferisé par GRBL) à intervalle régulier, pour le DRO
                    # (position/état machine) pendant le job — sans perturber
                    # le streaming : GRBL y répond immédiatement, sans jamais
                    # consommer le buffer RX du G-Code en cours d'envoi.
                    now = time.time()
                    if now - last_status_poll >= self._status_poll_interval:
                        try:
                            ser.write(b'?')
                        except Exception:   # plusieurs fois par seconde : la coupure est vue au tour suivant
                            pass
                        last_status_poll = now

                    while ser.in_waiting > 0:
                        resp = ser.readline().decode('utf-8', errors='ignore').strip()
                        kind = classify(resp)
                        if kind == EMPTY:
                            continue
                        last_rx = time.time()
                        log.debug("RX %r", resp)

                        if kind == OK:
                            ok_count += 1
                            if not stream.acknowledge():
                                log.warning("Streamer : « ok » reçu alors qu'aucune ligne n'est en attente")
                        elif kind == ERROR:
                            log.error("Streamer : %s en réponse à la ligne %r (ligne n° %d, %d « ok » reçus)",
                                      resp, stream.first_pending, ok_count + 1, ok_count)
                            self.log_signal.emit(f"!!! ERREUR GRBL : {resp}")
                            clean_finish = False
                            grbl_error = True
                            self.is_running = False
                            break
                        elif kind == STATUS:
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                        else:
                            log.info("Streamer : message GRBL non traité %r", resp)

                    now = time.time()
                    if stream.pending and now - last_rx > STALL_WARNING_S and now - last_stall_log > STALL_WARNING_S:
                        log.warning("Streamer : aucune réponse de GRBL depuis %.1f s ; %d ligne(s) en attente "
                                    "d'un « ok » (%r…), dernier état %s",
                                    now - last_rx, stream.pending, stream.first_pending, self.usb.last_state)
                        last_stall_log = now

                if not self.is_running:
                    break

                self.progress.emit(stream.next_index, total)
                self._flush_sent_lines()
                time.sleep(0.001)

            log.info("Streamer : %d/%d lignes envoyées, %d en attente d'un « ok »",
                     stream.next_index, total, stream.pending)
            while stream.pending and self.is_running:
                with self.usb._lock:
                    if not (ser and ser.is_open):
                        # Port fermé avant d'avoir reçu tous les « ok » : ce n'est
                        # pas une fin propre.
                        clean_finish = False
                        break
                    if ser.in_waiting > 0:
                        resp = ser.readline().decode('utf-8', errors='ignore').strip()
                        kind = classify(resp)
                        log.debug("RX (fin) %r", resp)
                        if kind != EMPTY:
                            last_rx = time.time()
                        if kind == OK:
                            ok_count += 1
                            stream.acknowledge()
                        elif kind == ERROR:
                            log.error("Streamer : %s en réponse à la ligne %r", resp, stream.first_pending)
                            self.log_signal.emit(f"!!! ERREUR GRBL : {resp}")
                            clean_finish = False
                            grbl_error = True
                            break
                        elif kind == STATUS:
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                    else:
                        now = time.time()
                        if now - last_rx > STALL_WARNING_S and now - last_stall_log > STALL_WARNING_S:
                            log.warning("Streamer : aucune réponse de GRBL depuis %.1f s en fin de job ; "
                                        "%d ligne(s) en attente d'un « ok » (%r…)",
                                        now - last_rx, stream.pending, stream.first_pending)
                            last_stall_log = now
                        time.sleep(0.01)
                self._flush_sent_lines()

            # Erreur GRBL : arrêter la machine, qui exécuterait sinon la fin de son buffer.
            if grbl_error:
                self._stop_machine_after_error(ser)

            # Tous les « ok » sont reçus : la machine peut encore bouger.
            # On n'annonce la fin qu'une fois GRBL revenu à l'état Idle.
            if clean_finish and self.is_running and not stream.pending:
                if not self._wait_until_idle(ser):
                    clean_finish = False

        except Exception as e:
            log.exception("Streamer : exception pendant l'envoi")
            self.log_signal.emit(f"!!! ERREUR STREAMING : {e}")
            clean_finish = False
            # Signale une coupure probable (USB débranché, driver qui
            # décroche...) pour que l'UI propose une reconnexion automatique
            # — voir ReconnectThread plus bas et MachineConnection._on_stream_connection_lost
            # (controllers/machine_connection.py). Le job lui-même reste arrêté :
            # jamais de reprise automatique de l'envoi (position potentiellement
            # plus fiable après une coupure).
            self.connection_lost.emit()

        # Arrêt demandé par l'utilisateur (Reset / Arrêt d'urgence) : ce n'est
        # pas une fin propre — sinon l'interface annonçait « Terminé » et la
        # file d'attente enchaînait sur le job suivant.
        if self._stopped_by_user:
            clean_finish = False

        self._flush_sent_lines(force=True)
        log.info("Streamer : fin en %.1f s, %d/%d lignes envoyées, %d « ok » reçus, fin propre=%s, "
                 "arrêt utilisateur=%s", time.time() - t_start, stream.next_index, total, ok_count,
                 clean_finish, self._stopped_by_user)
        self.finished_signal.emit(clean_finish)


class StatusPollThread(QThread):
    """Interroge périodiquement GRBL (requête temps réel '?') pour afficher
    la position machine et l'état courant en direct (DRO) quand aucun
    streaming n'est actif (idle, jog, homing...). Pendant un streaming,
    c'est GCodeStreamerThread qui s'en charge lui-même (voir plus haut) :
    ce thread doit alors être mis en pause via pause()/resume() pour éviter
    toute concurrence d'accès au port série entre deux threads."""
    status_updated = pyqtSignal(str, float, float, float)  # état, x, y, z
    connection_lost = pyqtSignal()

    def __init__(self, usb_controller, interval_sec=0.2):
        super().__init__()
        self.usb = usb_controller
        self.interval_sec = interval_sec
        self.is_running = True
        self._paused = False

    def stop(self):
        self.is_running = False

    def pause(self):
        log.debug("StatusPoll : pause")
        self._paused = True

    def resume(self):
        log.debug("StatusPoll : reprise")
        self._paused = False

    def run(self):
        while self.is_running:
            if not self._paused:
                if not self.usb.is_connected():
                    log.warning("StatusPoll : port déconnecté, arrêt du polling")
                    self.connection_lost.emit()
                    break
                result = self.usb.query_status()
                if result:
                    self.status_updated.emit(*result)
            time.sleep(self.interval_sec)


class AdvancedGCodeWorker(QThread):
    """Thread de génération G-Code optimisé (RLE & Surbalayage)"""
    finished = pyqtSignal(str, int, float, float)    # G-Code, lignes, puissance moyenne, durée (s)
    progress = pyqtSignal(int)  # 0-100 : avancement de la génération
    error = pyqtSignal(str)     # émis si la génération échoue (au lieu de mourir silencieusement)

    def __init__(self, processed_array, svg_path, params, vector_layers_data=None):
        super().__init__()
        self.processed_array = processed_array
        self.svg_path = svg_path
        self.params = params
        # Données géométriques déjà extraites (thread-safe, pas d'objets Qt) pour
        # les calques de texte/formes créés dans l'éditeur vectoriel.
        self.vector_layers_data = vector_layers_data or {}

    def run(self):
        try:
            self._run_impl()
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

    def _run_impl(self):
        result = build_job_gcode(self.processed_array, self.svg_path, self.params,
                                 self.vector_layers_data, progress=self.progress.emit)
        self.finished.emit(*result)


class CommandThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, usb_controller, commands):
        super().__init__()
        self.usb = usb_controller
        self.commands = commands if isinstance(commands, list) else [commands]

    def run(self):
        for cmd in self.commands:
            res = self.usb.send_command(cmd)
            self.log_signal.emit(f"> {cmd}\n< {res}")
        self.finished_signal.emit()


class TestMatrixWorker(QThread):
    """Thread de génération de matrice de test Vitesse vs Puissance (Gravure) ou Vitesse vs Passes (Découpe)"""
    finished = pyqtSignal(str, int, float, float)    # G-Code, lignes, puissance moyenne, durée (s)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        self.finished.emit(*build_test_matrix_gcode(self.params))


class ReconnectThread(QThread):
    """Tente de rouvrir automatiquement le port série après une coupure USB
    survenue en cours de job (câble qui bouge, driver Windows capricieux...).
    Reconnecte uniquement la LIAISON série — ne relance JAMAIS le job
    lui-même : après une coupure, la position réelle de la machine n'est
    plus fiable, reprendre l'envoi à l'aveugle serait dangereux (risque de
    collision ou de gravure décalée). C'est à l'utilisateur de décider de la
    suite (re-homing, relance manuelle...) une fois la liaison rétablie."""
    reconnected = pyqtSignal(bool)

    def __init__(self, usb_controller, port, baudrate=115200, max_attempts=5, delay_sec=2.0):
        super().__init__()
        self.usb = usb_controller
        self.port = port
        self.baudrate = baudrate
        self.max_attempts = max_attempts
        self.delay_sec = delay_sec

    def run(self):
        for _ in range(self.max_attempts):
            if self.usb.connect(self.port, self.baudrate):
                self.reconnected.emit(True)
                return
            time.sleep(self.delay_sec)
        self.reconnected.emit(False)
