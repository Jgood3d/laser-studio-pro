"""Threads d'arrière-plan (QThread) : traitement d'image, streaming G-Code,
génération du G-Code (job et matrice de test), exécution de commandes.

La génération du G-Code elle-même est dans le paquet gcode/ (sans Qt) :
AdvancedGCodeWorker et TestMatrixWorker ne font que l'appeler dans un thread."""
import re
import time

import numpy as np
from PIL import Image, ImageEnhance, ImageDraw

from PyQt6.QtCore import QThread, pyqtSignal

from laser_studio.core.debug_log import get_logger

log = get_logger()

try:
    from numba import njit
    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False

from laser_studio.gcode.job import build_job_gcode
from laser_studio.gcode.test_matrix import build_test_matrix_gcode
from laser_studio.vector.font import VectorFont
from laser_studio.image import separation as separation_engine
from laser_studio.image.filters import sharpen_image
from laser_studio.i18n import tr

if _HAS_NUMBA:
    @njit(cache=True)
    def _diffuse_numba(arr, out, kdy, kdx, kw):
        h, w = arr.shape
        n_taps = len(kw)
        for y in range(h):
            for x in range(w):
                old_val = arr[y, x]
                new_val = 255.0 if old_val > 128.0 else 0.0
                out[y, x] = new_val
                err = old_val - new_val
                for i in range(n_taps):
                    ny = y + kdy[i]
                    nx = x + kdx[i]
                    if 0 <= ny < h and 0 <= nx < w:
                        arr[ny, nx] += err * kw[i]
        return out


def _diffuse_pure_python(arr_in, kernel):
    """Repli sans numba : la diffusion d'erreur reste intrinsèquement séquentielle
    (chaque pixel dépend du précédent), donc impossible à vectoriser avec numpy.
    On utilise ici des listes Python natives, nettement plus rapides que l'accès
    scalaire à un tableau numpy dans une boucle Python (2 à 4x plus rapide dans
    ce cas précis)."""
    h, w = arr_in.shape
    rows = arr_in.tolist()
    out_rows = [[0] * w for _ in range(h)]
    for y in range(h):
        row = rows[y]
        for x in range(w):
            old_val = row[x]
            new_val = 255 if old_val > 128 else 0
            out_rows[y][x] = new_val
            err = old_val - new_val
            if err != 0:
                for dy, dx, weight in kernel:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        rows[ny][nx] += err * weight
    return np.array(out_rows, dtype=np.uint8)



class ImageProcessingWorker(QThread):
    """Thread d'arrière-plan pour le traitement d'image et le tramage (fluidité garantie)"""
    finished = pyqtSignal(np.ndarray, object)

    def __init__(self, raw_image, params):
        super().__init__()
        self.raw_image = raw_image
        self.params = params

    def run(self):
        if not self.raw_image:
            return

        w_mm = self.params['w_mm']
        h_mm = self.params['h_mm']
        lmm = self.params['lmm']

        px_w = int(w_mm * lmm)
        px_h = int(h_mm * lmm)
        if px_w < 1 or px_h < 1:
            return

        img = self.raw_image.resize((px_w, px_h), Image.Resampling.LANCZOS)

        if self.params['mirror_h']:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if self.params['mirror_v']:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        bright = self.params['bright']
        contrast = self.params['contrast']
        gamma = self.params['gamma'] / 100.0

        if bright != 0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.0 + bright / 100.0)

        if contrast != 0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.0 + contrast / 100.0)

        arr = np.array(img, dtype=np.float32)

        if gamma != 1.0:
            arr = 255.0 * ((arr / 255.0) ** (1.0 / gamma))
            arr = np.clip(arr, 0, 255)

        # Netteté : après les réglages de tons, juste avant l'inversion et le tramage.
        sharp = float(self.params.get('sharp', 0) or 0)
        if sharp > 0:
            sharpened = sharpen_image(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), sharp, lmm)
            arr = np.array(sharpened, dtype=np.float32)

        if self.params['invert']:
            arr = 255.0 - arr

        algo = self.params['algo']
        if algo == "Niveaux de Gris":
            out_arr = arr.astype(np.uint8)
        elif algo == "Seuil Simple (Binaire)":
            out_arr = np.where(arr > 128, 255, 0).astype(np.uint8)
        else:
            out_arr = self.apply_error_diffusion(arr, algo)

        dither_img = Image.fromarray(out_arr)
        self.finished.emit(out_arr, dither_img)

    def apply_error_diffusion(self, arr_in, algo):
        if algo == "Floyd-Steinberg":
            pil_img = Image.fromarray(np.clip(arr_in, 0, 255).astype(np.uint8))
            dithered = pil_img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            return np.where(np.array(dithered), 255, 0).astype(np.uint8)

        if algo.startswith("Bayer"):
            return self.apply_bayer_dither(arr_in, algo)

        h, w = arr_in.shape
        arr = arr_in.copy()
        out = np.zeros((h, w), dtype=np.uint8)

        kernels = {
            "Jarvis, Judice & Ninke": [
                (0, 1, 7/48), (0, 2, 5/48),
                (1, -2, 3/48), (1, -1, 5/48), (1, 0, 7/48), (1, 1, 5/48), (1, 2, 3/48),
                (2, -2, 1/48), (2, -1, 3/48), (2, 0, 5/48), (2, 1, 3/48), (2, 2, 1/48)
            ],
            "Stucki": [
                (0, 1, 8/42), (0, 2, 4/42),
                (1, -2, 2/42), (1, -1, 4/42), (1, 0, 8/42), (1, 1, 4/42), (1, 2, 2/42),
                (2, -2, 1/42), (2, -1, 2/42), (2, 0, 4/42), (2, 1, 2/42), (2, 2, 1/42)
            ],
            "Atkinson": [
                (0, 1, 1/8), (0, 2, 1/8),
                (1, -1, 1/8), (1, 0, 1/8), (1, 1, 1/8),
                (2, 0, 1/8)
            ],
            "Sierra": [
                (0, 1, 5/32), (0, 2, 3/32),
                (1, -2, 2/32), (1, -1, 4/32), (1, 0, 5/32), (1, 1, 4/32), (1, 2, 2/32),
                (2, -1, 2/32), (2, 0, 3/32), (2, 1, 2/32)
            ],
            "Sierra Lite (rapide)": [
                (0, 1, 2/4),
                (1, -1, 1/4), (1, 0, 1/4)
            ],
            "Burkes": [
                (0, 1, 8/32), (0, 2, 4/32),
                (1, -2, 2/32), (1, -1, 4/32), (1, 0, 8/32), (1, 1, 4/32), (1, 2, 2/32)
            ]
        }
        kernel = kernels.get(algo, kernels.get("Jarvis, Judice & Ninke"))

        if _HAS_NUMBA:
            kdy = np.array([k[0] for k in kernel], dtype=np.int64)
            kdx = np.array([k[1] for k in kernel], dtype=np.int64)
            kw = np.array([k[2] for k in kernel], dtype=np.float64)
            out = _diffuse_numba(arr, out, kdy, kdx, kw)
            return out
        else:
            return _diffuse_pure_python(arr, kernel)

    def apply_bayer_dither(self, arr_in, algo):
        """Tramage ordonné (matrice de Bayer) : contrairement à la diffusion
        d'erreur, chaque pixel est comparé à un seuil fixe qui se répète en
        motif régulier. Résultat plus régulier/répétitif (trame en points),
        souvent apprécié sur le bois pour sa texture homogène et sans
        'traînées' contrairement à Floyd-Steinberg. Aussi bien plus rapide
        (aucune dépendance séquentielle entre pixels)."""
        bayer_2x2 = np.array([[0, 2], [3, 1]], dtype=np.float64)
        bayer_4x4 = np.array([
            [0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]
        ], dtype=np.float64)
        bayer_8x8 = np.array([
            [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
            [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
            [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
            [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]
        ], dtype=np.float64)
        matrix = bayer_8x8 if "8x8" in algo else (bayer_2x2 if "2x2" in algo else bayer_4x4)
        n = matrix.shape[0]
        threshold_map = (matrix + 0.5) / (n * n) * 255.0

        h, w = arr_in.shape
        tiled = np.tile(threshold_map, (h // n + 1, w // n + 1))[:h, :w]
        return np.where(arr_in > tiled, 255, 0).astype(np.uint8)


# Début d'une ligne que GRBL sait lire : un mot G-Code (lettre suivie d'une valeur), une commande « $ »,
# un commentaire « ( », « % » ou une commande temps réel.
_GRBL_LINE_RE = re.compile(r'^(?:[A-Z]\s*[-+.\d]|\$|\(|%|[?!~])', re.IGNORECASE)


def gcode_lines(gcode_text):
    """Lignes de la console à envoyer à GRBL. La console mélange le G-Code et les messages de
    l'application (« Connecté à … », « >>> Mode laser GRBL … ») : GRBL refuserait ceux-ci (error:1)
    et l'envoi s'arrêterait, ils sont donc écartés comme les commentaires « ; »."""
    lines = (line.strip() for line in gcode_text.split('\n'))
    return [line for line in lines if line and not line.startswith(';') and _GRBL_LINE_RE.match(line)]


class GCodeStreamerThread(QThread):
    """Thread d'envoi séquentiel du G-Code à GRBL (Streaming avec gestion du buffer RX)"""
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
        self.lines = gcode_lines(gcode_text)
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
        self.acked = 0                    # « ok » reçus depuis le début du job
        self._acked_emitted = 0

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
                    except Exception:
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

        ring_buffer = []
        MAX_BUF_SIZE = 127
        
        line_idx = 0
        last_status_poll = time.time()
        # Diagnostic : compteurs et détection d'un envoi bloqué (plus aucune réponse de GRBL).
        ok_count = 0
        last_rx = time.time()
        last_stall_log = 0.0
        STALL_WARNING_S = 5.0
        grbl_error = False
        try:
            while line_idx < total and self.is_running:
                while line_idx < total and self.is_running:
                    line = self.lines[line_idx]
                    encoded_line = (line + '\n').encode('utf-8')
                    line_len = len(encoded_line)
                    
                    current_buf_occupancy = sum(item[1] for item in ring_buffer)
                    if current_buf_occupancy + line_len >= MAX_BUF_SIZE and ring_buffer:
                        break
                    
                    with self.usb._lock:
                        if not (ser and ser.is_open):
                            raise Exception("Connexion perdue")
                        ser.write(encoded_line)
                    log.debug("TX #%d %r (buffer %d/%d)", line_idx + 1, line,
                              current_buf_occupancy + line_len, MAX_BUF_SIZE)
                    
                    ring_buffer.append((line, line_len))
                    self._sent_batch.append(line)
                    line_idx += 1

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
                        except Exception:
                            pass
                        last_status_poll = now
                    
                    while ser.in_waiting > 0:
                        resp = ser.readline().decode('utf-8', errors='ignore').strip()
                        if not resp:
                            continue
                        last_rx = time.time()
                        log.debug("RX %r", resp)
                        
                        if resp == 'ok':
                            ok_count += 1
                            if ring_buffer:
                                ring_buffer.pop(0)
                                self.acked += 1
                            else:
                                log.warning("Streamer : « ok » reçu alors qu'aucune ligne n'est en attente")
                        elif resp.startswith('error') or resp.startswith('ALARM') or resp.startswith('ERROR:'):
                            log.error("Streamer : %s en réponse à la ligne %r (ligne n° %d, %d « ok » reçus)",
                                      resp, ring_buffer[0][0] if ring_buffer else None,
                                      ok_count + 1, ok_count)
                            self.log_signal.emit(f"!!! ERREUR GRBL : {resp}")
                            clean_finish = False
                            grbl_error = True
                            self.is_running = False
                            break
                        elif resp.startswith('<'):
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                        else:
                            log.info("Streamer : message GRBL non traité %r", resp)

                    now = time.time()
                    if ring_buffer and now - last_rx > STALL_WARNING_S and now - last_stall_log > STALL_WARNING_S:
                        log.warning("Streamer : aucune réponse de GRBL depuis %.1f s ; %d ligne(s) en attente "
                                    "d'un « ok » (%r…), dernier état %s",
                                    now - last_rx, len(ring_buffer), ring_buffer[0][0],
                                    self.usb.last_state)
                        last_stall_log = now

                if not self.is_running:
                    break

                self.progress.emit(line_idx, total)
                self._flush_sent_lines()
                time.sleep(0.001)

            log.info("Streamer : %d/%d lignes envoyées, %d en attente d'un « ok »",
                     line_idx, total, len(ring_buffer))
            while ring_buffer and self.is_running:
                with self.usb._lock:
                    if not (ser and ser.is_open):
                        # Port fermé avant d'avoir reçu tous les « ok » : ce n'est
                        # pas une fin propre.
                        clean_finish = False
                        break
                    if ser.in_waiting > 0:
                        resp = ser.readline().decode('utf-8', errors='ignore').strip()
                        log.debug("RX (fin) %r", resp)
                        if resp:
                            last_rx = time.time()
                        if resp == 'ok':
                            ok_count += 1
                            ring_buffer.pop(0)
                            self.acked += 1
                        elif resp.startswith('error') or resp.startswith('ALARM'):
                            log.error("Streamer : %s en réponse à la ligne %r", resp, ring_buffer[0][0])
                            self.log_signal.emit(f"!!! ERREUR GRBL : {resp}")
                            clean_finish = False
                            grbl_error = True
                            break
                        elif resp.startswith('<'):
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                    else:
                        now = time.time()
                        if now - last_rx > STALL_WARNING_S and now - last_stall_log > STALL_WARNING_S:
                            log.warning("Streamer : aucune réponse de GRBL depuis %.1f s en fin de job ; "
                                        "%d ligne(s) en attente d'un « ok » (%r…)",
                                        now - last_rx, len(ring_buffer), ring_buffer[0][0])
                            last_stall_log = now
                        time.sleep(0.01)
                self._flush_sent_lines()

            # Erreur GRBL : arrêter la machine, qui exécuterait sinon la fin de son buffer.
            if grbl_error:
                self._stop_machine_after_error(ser)

            # Tous les « ok » sont reçus : la machine peut encore bouger.
            # On n'annonce la fin qu'une fois GRBL revenu à l'état Idle.
            if clean_finish and self.is_running and not ring_buffer:
                if not self._wait_until_idle(ser):
                    clean_finish = False

        except Exception as e:
            log.exception("Streamer : exception pendant l'envoi")
            self.log_signal.emit(f"!!! ERREUR STREAMING : {e}")
            clean_finish = False
            # Signale une coupure probable (USB débranché, driver qui
            # décroche...) pour que l'UI propose une reconnexion automatique
            # — voir ReconnectThread plus bas et MachineConnection._on_stream_connection_lost
            # dans laser_control_mixin.py. Le job lui-même reste arrêté :
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
                 "arrêt utilisateur=%s", time.time() - t_start, line_idx, total, ok_count,
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
    finished = pyqtSignal(str, int, float, str)
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
    finished = pyqtSignal(str, int, float, str)

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


# ----------------------------------------------------------------------
# Image de calibrage du gain de point (fonction pure : testable sans Qt)
# ----------------------------------------------------------------------
GAIN_TEST_GAINS = (0, 5, 10, 15, 20)              # valeurs du curseur « gain de point » (en %)
GAIN_TEST_TONES = tuple(i / 10.0 for i in range(11))   # 0 % (verre intact) ... 100 % (verre dégagé)


def build_gain_test_array(lines_per_mm, mirror=False, patch_mm=8.0, gap_mm=1.5, label_mm=7.0,
                          gains=GAIN_TEST_GAINS, tones=GAIN_TEST_TONES):
    """Image de calibrage du gain de point pour le verre peint.

    Grille : une LIGNE par valeur de gain (celles du curseur de l'onglet
    Séparation), une COLONNE par ton, de 0 % (peinture intacte) à 100 % (verre
    entièrement dégagé). Chaque case est tramée (Floyd-Steinberg) avec la
    couverture compensée compenser_gain_point(ton, gain) ; les valeurs du
    gain sont gravées à gauche de chaque ligne.
    Renvoie (tableau uint8 : 0 = brûlé, 255 = intact ; largeur_mm ; hauteur_mm).
    mirror=True retourne tout à l'horizontale, pour une gravure vue à travers
    le verre (le texte se lit alors à l'endroit de l'autre côté)."""
    lpm = float(lines_per_mm)

    def px(mm):
        return max(1, int(round(mm * lpm)))

    cell = px(patch_mm)
    gap = px(gap_mm)
    label_w = px(label_mm)
    n_t, n_g = len(tones), len(gains)
    width = label_w + n_t * cell + (n_t - 1) * gap
    height = n_g * cell + (n_g - 1) * gap
    arr = np.full((height, width), 255, np.uint8)

    for gi, g in enumerate(gains):
        y0 = gi * (cell + gap)
        for ti, tone in enumerate(tones):
            x0 = label_w + ti * (cell + gap)
            coverage = float(separation_engine.compenser_gain_point(np.float32(tone), g / 100.0))
            coverage = min(max(coverage, 0.0), 1.0)
            gray = np.full((cell, cell), int(round(255 * (1.0 - coverage))), np.uint8)
            bits = np.array(Image.fromarray(gray, "L").convert("1"))      # tramage Floyd-Steinberg
            arr[y0:y0 + cell, x0:x0 + cell] = np.where(bits, 255, 0).astype(np.uint8)

    # Valeurs du gain, à gauche de chaque ligne (police vectorielle 5x7, tracée avec PIL)
    canvas = Image.fromarray(arr, "L")
    draw = ImageDraw.Draw(canvas)
    text_h_px = min(cell, px(3.0))
    stroke = max(1, int(round(text_h_px / 7.0)))
    for gi, g in enumerate(gains):
        label = str(g)
        scale = text_h_px / 7.0
        y_mid = gi * (cell + gap) + cell / 2.0
        x_left = px(0.8)
        for i, char in enumerate(label):
            for x1, y1, x2, y2 in VectorFont.FONT_5X7.get(char, []):
                ox = x_left + i * (5 + 2) * scale
                draw.line([(ox + x1 * scale, y_mid + (3.5 - y1) * scale),
                           (ox + x2 * scale, y_mid + (3.5 - y2) * scale)], fill=0, width=stroke)
    arr = np.array(canvas)
    if mirror:
        arr = np.ascontiguousarray(arr[:, ::-1])
    return arr, width / lpm, height / lpm

