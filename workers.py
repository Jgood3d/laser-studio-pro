"""Threads d'arrière-plan (QThread) : traitement d'image, streaming G-Code,
génération avancée de G-Code, exécution de commandes, matrice de test."""
import time
import math
import re
from io import BytesIO
from xml.dom import minidom

import numpy as np
from PIL import Image, ImageEnhance, ImageDraw
from svg.path import parse_path

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from numba import njit
    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False

from vector_font import VectorFont
from vector_layers import build_vector_layers_gcode


def _round_half_up(value):
    """Arrondi arithmétique standard (.5 arrondit toujours vers le haut),
    contrairement à round() de Python qui arrondit .5 vers le nombre pair
    le plus proche (ex: round(62.5) donne 62, pas 63). Utilisé pour les
    étiquettes % puissance / vitesse de la matrice de test, afin qu'une
    valeur S625 s'affiche bien comme 63% (et S275 comme 28%)."""
    return math.floor(value + 0.5)


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

    def __init__(self, usb_controller, gcode_text):
        super().__init__()
        self.usb = usb_controller
        self.lines = [line.strip() for line in gcode_text.split('\n') if line.strip() and not line.startswith(';')]
        self.is_running = True
        self._status_poll_interval = 0.4  # secondes entre deux requêtes '?' pendant le job

    def stop(self):
        self.is_running = False

    def run(self):
        total = len(self.lines)
        clean_finish = True
        
        with self.usb._lock:
            if not (self.usb.ser and self.usb.ser.is_open):
                self.finished_signal.emit(False)
                return
            ser = self.usb.ser
            try:
                ser.reset_input_buffer()
            except Exception:
                pass

        ring_buffer = []
        MAX_BUF_SIZE = 127
        
        line_idx = 0
        last_status_poll = time.time()
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
                    
                    ring_buffer.append((line, line_len))
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
                        
                        if resp == 'ok':
                            if ring_buffer:
                                ring_buffer.pop(0)
                        elif resp.startswith('error') or resp.startswith('ALARM') or resp.startswith('ERROR:'):
                            self.log_signal.emit(f"!!! ERREUR GRBL : {resp}")
                            clean_finish = False
                            self.is_running = False
                            break
                        elif resp.startswith('<'):
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                        else:
                            pass

                if not self.is_running:
                    break

                self.progress.emit(line_idx, total)
                time.sleep(0.001)

            while ring_buffer and self.is_running:
                with self.usb._lock:
                    if not (ser and ser.is_open):
                        break
                    if ser.in_waiting > 0:
                        resp = ser.readline().decode('utf-8', errors='ignore').strip()
                        if resp == 'ok':
                            ring_buffer.pop(0)
                        elif resp.startswith('error') or resp.startswith('ALARM'):
                            clean_finish = False
                            break
                        elif resp.startswith('<'):
                            parsed = self.usb.update_last_status(resp)
                            if parsed:
                                self.status_updated.emit(*parsed)
                    else:
                        time.sleep(0.01)

        except Exception as e:
            self.log_signal.emit(f"!!! ERREUR STREAMING : {e}")
            clean_finish = False

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

    def __init__(self, usb_controller, interval_sec=0.4):
        super().__init__()
        self.usb = usb_controller
        self.interval_sec = interval_sec
        self.is_running = True
        self._paused = False

    def stop(self):
        self.is_running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        while self.is_running:
            if not self._paused:
                if not self.usb.is_connected():
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
        gcode = ["; --- G-CODE HYBRIDE GRBL PRO ---"]
        
        if self.params['homing']:
            gcode.append("$H ; Homing initial")
        
        start_gcode = self.params['start_gcode'].strip()
        if start_gcode:
            gcode.append("; --- G-Code de Début ---")
            gcode.append(start_gcode)

        total_power_samples = []
        total_time_seconds = 0.0
        laser_cmd = self.params['laser_cmd']
        s_max = self.params['s_max']

        # En mode M4 (laser dynamique), pas besoin de renvoyer M4 à chaque
        # ligne : on l'active une seule fois ici pour tout le job, et on ne
        # pilote plus ensuite que la puissance (S...) — ce qui allège
        # nettement le G-code sur une image de plusieurs centaines de lignes.
        # M3 reste inchangé (renvoyé à chaque ligne comme avant) : certains
        # firmwares/pilotes laser en dépendent en mode spindle classique.
        if laser_cmd == "M4":
            gcode.append(f"{laser_cmd} S0 ; Mode laser dynamique activé pour tout le job")
        
        w_mm, h_mm = self.params['width_mm'], self.params['height_mm']
        if self.params['origin_pos'] == "Centre":
            base_offset_x = self.params['offset_x'] - (w_mm / 2.0)
            base_offset_y = self.params['offset_y'] - (h_mm / 2.0)
        else:
            base_offset_x = self.params['offset_x']
            base_offset_y = self.params['offset_y']

        curr_x, curr_y = 0.0, 0.0

        if self.processed_array is not None:
            gcode.append("; --- PHASE 1 : GRAVURE IMAGE (SURBALAYAGE ACTIF) ---")
            speed_engrave = self.params['speed_engrave']
            gcode.append(f"F{speed_engrave}")

            arr = self.processed_array
            h, w = arr.shape
            step_x, step_y = w_mm / w, h_mm / h
            power_engrave = self.params['power_engrave']
            algo = self.params.get('algo', '')

            enable_overscan = self.params['enable_overscan']
            if enable_overscan:
                if self.params.get('overscan_mode') == "Pourcentage (%)":
                    pct = self.params.get('overscan_pct', 5.0)
                    overscan_dist = w_mm * (pct / 100.0)
                else:
                    overscan_dist = self.params['overscan_dist']
            else:
                overscan_dist = 0.0

            def pixel_power_percent(val):
                if algo == "Niveaux de Gris":
                    return power_engrave * (255.0 - float(val)) / 255.0
                return power_engrave if val == 0 else 0.0

            for y in range(h):
                if h > 0 and y % max(1, h // 50) == 0:
                    # Phase 1 (gravure image) occupe ~0-70% de la barre : c'est
                    # de très loin la phase la plus longue (une ligne de gcode
                    # par transition de puissance, sur potentiellement des
                    # centaines de milliers de pixels).
                    self.progress.emit(int((y / h) * 70))
                actual_y = base_offset_y + (h - 1 - y) * step_y
                is_ltr = (y % 2 == 0)

                margin_start_x = base_offset_x - overscan_dist if is_ltr else base_offset_x + w_mm + overscan_dist
                margin_end_x = base_offset_x + w_mm + overscan_dist if is_ltr else base_offset_x - overscan_dist
                image_edge_x = base_offset_x + w_mm if is_ltr else base_offset_x

                if overscan_dist > 0:
                    gcode.append(f"G0 X{margin_start_x:.3f} Y{actual_y:.3f} ; OVERSCAN_START")
                else:
                    gcode.append(f"G0 X{margin_start_x:.3f} Y{actual_y:.3f}")

                if laser_cmd == "M3":
                    gcode.append(f"{laser_cmd} S0")
                else:
                    # Mode M4 déjà activé une fois en tête de job (voir plus
                    # haut) : ici on ne fait plus que remettre la puissance à
                    # 0 avant d'attaquer la ligne, sans renvoyer M4.
                    gcode.append("S0")

                image_start_x = base_offset_x if is_ltr else base_offset_x + w_mm

                if overscan_dist > 0:
                    # Traverse la zone de surbalayage à puissance nulle avant
                    # d'atteindre le premier pixel de l'image : sans cette
                    # ligne, la première commande G1 du tramage (ci-dessous)
                    # parcourait toute la distance (surbalayage + image)
                    # directement à la puissance du premier pixel gravé.
                    gcode.append(f"G1 X{image_start_x:.3f} F{speed_engrave} S0")
                    total_time_seconds += (abs(image_start_x - margin_start_x) / max(speed_engrave, 1)) * 60.0

                row = arr[y, :] if is_ltr else arr[y, ::-1]

                cx = image_start_x
                last_p_val = 0

                for x_idx, val in enumerate(row):
                    x_pixel = x_idx if is_ltr else (w - 1 - x_idx)
                    actual_x = base_offset_x + x_pixel * step_x

                    p_percent = pixel_power_percent(val)
                    p_val = int(round((p_percent / 100.0) * s_max))

                    if p_val != last_p_val:
                        gcode.append(f"G1 X{actual_x:.3f} F{speed_engrave} S{p_val}")
                        total_time_seconds += (abs(actual_x - cx) / max(speed_engrave, 1)) * 60.0
                        cx = actual_x
                        last_p_val = p_val
                        if p_val > 0:
                            total_power_samples.append(p_percent)

                if cx != image_edge_x:
                    gcode.append(f"G1 X{image_edge_x:.3f} F{speed_engrave} S{last_p_val}")
                    total_time_seconds += (abs(image_edge_x - cx) / max(speed_engrave, 1)) * 60.0
                    cx = image_edge_x

                if overscan_dist > 0:
                    gcode.append(f"G1 X{margin_end_x:.3f} F{speed_engrave} S0 ; OVERSCAN_END")
                    total_time_seconds += (abs(margin_end_x - cx) / max(speed_engrave, 1)) * 60.0

                if laser_cmd == "M3":
                    gcode.append("M5")
                elif overscan_dist == 0 and last_p_val != 0:
                    # Sécurité : sans surbalayage pour s'en charger, on
                    # s'assure que la puissance est bien à 0 avant le
                    # déplacement rapide (G0) vers la ligne suivante.
                    gcode.append("S0")

        self.progress.emit(70)

        if self.params['enable_cut'] and self.svg_path:
            gcode.append("; --- PHASE 2 : DÉCOUPE VECTORIELLE SVG ---")
            speed_cut = self.params['speed_cut']
            gcode.append(f"F{speed_cut}")
            p_cut_percent = self.params['power_cut']
            p_cut_val = int((p_cut_percent / 100.0) * s_max)

            doc = minidom.parse(self.svg_path)
            path_strings = [path.getAttribute('d') for path in doc.getElementsByTagName('path')]
            doc.unlink()

            for pass_num in range(self.params['passes_cut']):
                gcode.append(f"; --- Passe Découpe {pass_num + 1}/{self.params['passes_cut']} ---")
                for path_str in path_strings:
                    if not path_str: continue
                    parsed = parse_path(path_str)
                    
                    start_pt = parsed.point(0)
                    sx = base_offset_x + start_pt.real
                    sy = base_offset_y + (h_mm - start_pt.imag)
                    
                    gcode.append(f"G0 X{sx:.3f} Y{sy:.3f}")
                    gcode.append(f"{laser_cmd} S{p_cut_val}")

                    curr_x, curr_y = sx, sy
                    
                    try:
                        path_len = parsed.length()
                        num_samples = max(10, int(path_len / 0.2))
                    except Exception:
                        num_samples = 50

                    for i in range(1, num_samples + 1):
                        pt = parsed.point(i / num_samples)
                        nx = base_offset_x + pt.real
                        ny = base_offset_y + (h_mm - pt.imag)
                        
                        dist = math.hypot(nx - curr_x, ny - curr_y)
                        total_time_seconds += (dist / max(speed_cut, 1)) * 60.0
                        total_power_samples.append(p_cut_percent)
                        curr_x, curr_y = nx, ny
                        
                        gcode.append(f"G1 X{nx:.3f} Y{ny:.3f}")
                    gcode.append("M5")

        self.progress.emit(85)

        if self.vector_layers_data:
            gcode.append("; --- PHASE 3 : CALQUES VECTORIELS (TEXTE & FORMES) ---")
            if self.params.get('enable_overscan', False):
                if self.params.get('overscan_mode') == "Pourcentage (%)":
                    vector_overscan_dist = w_mm * (self.params.get('overscan_pct', 5.0) / 100.0)
                else:
                    vector_overscan_dist = self.params.get('overscan_dist', 2.5)
            else:
                vector_overscan_dist = 0.0
            layer_gcode, layer_time, layer_power_samples = build_vector_layers_gcode(
                self.vector_layers_data, base_offset_x, base_offset_y, h_mm,
                laser_cmd, s_max, overscan_dist=vector_overscan_dist
            )
            gcode.extend(layer_gcode)
            total_time_seconds += layer_time
            total_power_samples.extend(layer_power_samples)

        end_gcode = self.params['end_gcode'].strip()
        if end_gcode:
            gcode.append("; --- G-Code de Fin ---")
            gcode.append(end_gcode)
        else:
            gcode.append("M5\nG0 X0 Y0\n; FIN DU TRAVAIL")

        avg_power = float(np.mean(total_power_samples)) if total_power_samples else 0.0
        time_minutes = (total_time_seconds / 60.0) * 1.15
        
        mins = int(time_minutes)
        secs = int((time_minutes - mins) * 60)
        time_str = f"{mins} min {secs} sec" if mins > 0 else f"{secs} sec"

        self.progress.emit(100)
        self.finished.emit("\n".join(gcode), len(gcode), avg_power, time_str)


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
        mode = self.params.get('mode', 'Gravure')
        gcode = [f"; --- MATRICE DE TEST LASER ({mode.upper()}) ---"]
        
        if self.params.get('homing', False):
            gcode.append("$H ; Homing initial")

        gcode.append("G21 ; Unités en mm")
        gcode.append("G90 ; Positionnement absolu")
        
        s_max = self.params['s_max']
        laser_cmd = self.params['laser_cmd']
        
        min_s, max_s, steps_s = self.params['min_speed'], self.params['max_speed'], self.params['steps_speed']
        sq_size = self.params['size_square']
        gap = self.params['gap']
        
        enable_overscan = self.params.get('enable_overscan', False)
        if enable_overscan and mode == "Gravure":
            if self.params.get('overscan_mode') == "Pourcentage (%)":
                pct = self.params.get('overscan_pct', 5.0)
                overscan_dist = sq_size * (pct / 100.0)
            else:
                overscan_dist = self.params.get('overscan_dist', 2.5)
        else:
            overscan_dist = 0.0

        speeds = np.linspace(min_s, max_s, steps_s)

        total_time_sec = 0.0
        power_samples = []

        offset_labels_x = 22.0
        offset_labels_y = 14.0
        
        mat_off_x = self.params.get('matrix_offset_x', 0.0)
        mat_off_y = self.params.get('matrix_offset_y', 0.0)

        start_x = mat_off_x + offset_labels_x
        start_y = mat_off_y + offset_labels_y

        text_p_val = int((40.0 / 100.0) * s_max)

        if mode == "Gravure":
            min_p, max_p, steps_p = self.params['min_power'], self.params['max_power'], self.params['steps_power']
            lmm = self.params.get('lines_mm', 5.0)
            powers = np.linspace(min_p, max_p, steps_p)

            for j, p in enumerate(powers):
                lbl_x = start_x + j * (sq_size + gap) + (sq_size / 2.0) - 4.0
                lbl_y = start_y - 8.0
                p_text = f"{_round_half_up(p)}%"
                gcode.extend(VectorFont.generate_text_gcode(
                    text=p_text, start_x=lbl_x, start_y=lbl_y, 
                    char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
                ))

            matrix_total_w = (steps_p * sq_size) + ((steps_p - 1) * gap)
            title_pow_x = start_x + (matrix_total_w / 2.0) - 25.0
            title_pow_y = start_y - offset_labels_y
            gcode.extend(VectorFont.generate_text_gcode(
                text="PUISSANCE (%)", start_x=title_pow_x, start_y=title_pow_y, 
                char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

            for i, s in enumerate(speeds):
                # La zone d'étiquettes ne descend jamais sous X=0, même avec
                # un décalage matrice négatif — et laisse la place au titre
                # "VITESSE" (tracé verticalement, ~2.3 mm de large) à sa gauche.
                label_zone_x = max(0.0, mat_off_x)
                lbl_x = label_zone_x + 5.0
                lbl_y = start_y + i * (sq_size + gap) + (sq_size / 3.0)
                s_text = f"{_round_half_up(s)}"
                gcode.extend(VectorFont.generate_text_gcode(
                    text=s_text, start_x=lbl_x, start_y=lbl_y, 
                    char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
                ))

            matrix_total_h = (steps_s * sq_size) + ((steps_s - 1) * gap)
            title_spd_x = max(0.0, mat_off_x)
            title_spd_y = start_y + (matrix_total_h / 2.0) + 18.0
            gcode.extend(VectorFont.generate_text_gcode(
                text="VITESSE", start_x=title_spd_x, start_y=title_spd_y, 
                char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3", vertical=True
            ))

            for i, s in enumerate(speeds):
                for j, p in enumerate(powers):
                    x0 = start_x + j * (sq_size + gap)
                    y0 = start_y + i * (sq_size + gap)
                    
                    p_val = int((p / 100.0) * s_max)
                    power_samples.append(p)
                    
                    gcode.append(f"\n; --- Carré Speed={int(s)} mm/min | Power={p:.1f}% (Gravure) ---")
                    
                    lines = max(1, int(sq_size * lmm))
                    step_y = sq_size / lines
                    
                    for l in range(lines):
                        ly = y0 + l * step_y
                        
                        if l % 2 == 0:
                            margin_start_x = x0 - overscan_dist
                            margin_end_x = x0 + sq_size + overscan_dist
                            
                            if overscan_dist > 0:
                                gcode.append(f"G0 X{margin_start_x:.3f} Y{ly:.3f} ; OVERSCAN_START")
                                gcode.append(f"{laser_cmd} S0")
                                gcode.append(f"G1 X{x0:.3f} F{int(s)} S0")
                            else:
                                gcode.append(f"G0 X{x0:.3f} Y{ly:.3f}")
                                gcode.append(f"{laser_cmd} S0")
                                
                            gcode.append(f"G1 X{x0 + sq_size:.3f} F{int(s)} S{p_val}")
                            
                            if overscan_dist > 0:
                                gcode.append(f"G1 X{margin_end_x:.3f} F{int(s)} S0 ; OVERSCAN_END")
                        else:
                            margin_start_x = x0 + sq_size + overscan_dist
                            margin_end_x = x0 - overscan_dist
                            
                            if overscan_dist > 0:
                                gcode.append(f"G0 X{margin_start_x:.3f} Y{ly:.3f} ; OVERSCAN_START")
                                gcode.append(f"{laser_cmd} S0")
                                gcode.append(f"G1 X{x0 + sq_size:.3f} F{int(s)} S0")
                            else:
                                gcode.append(f"G0 X{x0 + sq_size:.3f} Y{ly:.3f}")
                                gcode.append(f"{laser_cmd} S0")
                                
                            gcode.append(f"G1 X{x0:.3f} F{int(s)} S{p_val}")
                            
                            if overscan_dist > 0:
                                gcode.append(f"G1 X{margin_end_x:.3f} F{int(s)} S0 ; OVERSCAN_END")
                                
                        gcode.append("M5")
                        total_time_sec += ((sq_size + (2 * overscan_dist)) / max(s, 1)) * 60.0
        else:
            single_p = self.params['single_power']
            min_passes = self.params['min_passes']
            max_passes = self.params['max_passes']
            steps_passes = self.params['steps_passes']
            
            passes_arr = np.unique(np.round(np.linspace(min_passes, max_passes, steps_passes))).astype(int)
            num_cols = len(passes_arr)
            num_rows = len(speeds)

            p_val = int((single_p / 100.0) * s_max)
            power_samples.append(single_p)

            for j, pass_val in enumerate(passes_arr):
                lbl_x = start_x + j * (sq_size + gap) + (sq_size / 2.0) - 4.0
                lbl_y = start_y - 8.0
                pass_text = f"{pass_val}p"
                gcode.extend(VectorFont.generate_text_gcode(
                    text=pass_text, start_x=lbl_x, start_y=lbl_y, 
                    char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
                ))

            matrix_total_w = (num_cols * sq_size) + ((num_cols - 1) * gap)
            title_pass_x = start_x + (matrix_total_w / 2.0) - 30.0
            title_pass_y = start_y - offset_labels_y
            gcode.extend(VectorFont.generate_text_gcode(
                text="NOMBRE DE PASSES", start_x=title_pass_x, start_y=title_pass_y, 
                char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
            ))

            for i, s in enumerate(speeds):
                label_zone_x = max(0.0, mat_off_x)
                lbl_x = label_zone_x + 5.0
                lbl_y = start_y + i * (sq_size + gap) + (sq_size / 3.0)
                s_text = f"{_round_half_up(s)}"
                gcode.extend(VectorFont.generate_text_gcode(
                    text=s_text, start_x=lbl_x, start_y=lbl_y, 
                    char_height=3.0, feed_rate=2000, power_val=text_p_val, laser_cmd="M3"
                ))

            matrix_total_h = (num_rows * sq_size) + ((num_rows - 1) * gap)
            title_spd_x = max(0.0, mat_off_x)
            title_spd_y = start_y + (matrix_total_h / 2.0) + 18.0
            gcode.extend(VectorFont.generate_text_gcode(
                text="VITESSE", start_x=title_spd_x, start_y=title_spd_y, 
                char_height=3.2, feed_rate=2000, power_val=text_p_val, laser_cmd="M3", vertical=True
            ))

            for i, s in enumerate(speeds):
                for j, pass_val in enumerate(passes_arr):
                    x0 = start_x + j * (sq_size + gap)
                    y0 = start_y + i * (sq_size + gap)
                    
                    gcode.append(f"\n; --- Carré Speed={int(s)} mm/min | Passes={pass_val} | Power={single_p}% (Découpe) ---")
                    for pass_num in range(pass_val):
                        gcode.append(f"; Passe {pass_num + 1}/{pass_val}")
                        gcode.append(f"G0 X{x0:.3f} Y{y0:.3f}")
                        gcode.append(f"F{int(s)}")
                        gcode.append(f"{laser_cmd} S{p_val}")
                        gcode.append(f"G1 X{x0 + sq_size:.3f}")
                        gcode.append(f"G1 Y{y0 + sq_size:.3f}")
                        gcode.append(f"G1 X{x0:.3f}")
                        gcode.append(f"G1 Y{y0:.3f}")
                        gcode.append("M5")
                        total_time_sec += ((sq_size * 4) / max(s, 1)) * 60.0

        gcode.append("\nM5\nG0 X0 Y0\n; FIN MATRICE DE TEST")

        avg_p = float(np.mean(power_samples)) if power_samples else 0.0
        mins = int(total_time_sec / 60)
        secs = int(total_time_sec % 60)
        time_str = f"{mins} min {secs} sec"

        self.finished.emit("\n".join(gcode), len(gcode), avg_p, time_str)

