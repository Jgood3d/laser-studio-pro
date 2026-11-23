"""Job de gravure : paramètres, contrôles avant génération, génération du
G-Code dans un thread, estimation rapide, export et import du G-Code, matrice
de test et motif aller/retour.

Le G-Code lui-même est calculé par le paquet gcode/ (sans Qt), dans les
threads de controllers/workers.py. Ce contrôleur ne touche pas aux widgets : il lit
l'état de l'interface par des fonctions qu'on lui donne, pose ses questions
par UserDialogs et publie ses résultats par signaux, que la fenêtre affiche.

    job = JobController(layers, grbl, machine, image_settings, UserDialogs(window),
                        geometry=window._job_geometry, image=lambda: window.processed_array, ...)
    job.generated.connect(job_display.show_generated)
    job.generate()
"""
import traceback
import xml.etree.ElementTree as ET

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from svg.path import parse_path

from laser_studio.core.constants import ORIGIN_CENTER
from laser_studio.gcode import MATRIX_CUT, MATRIX_ENGRAVE, bidir_test_gcode, image_origin
from laser_studio.gcode.common import OVERSCAN_FIXED, OVERSCAN_PERCENT
from laser_studio.gcode.test_matrix import matrix_cell_at
from laser_studio.i18n import tr
from laser_studio.models.layer_modes import MODE_FILL, layer_laser_cmd, layer_overscan_enabled
from laser_studio.models.layers import BASE_LAYER_DEFAULTS, layer_label
from laser_studio.vector.layer_data import extract_vector_layer_data
from laser_studio.controllers.workers import AdvancedGCodeWorker, TestMatrixWorker
from laser_studio.image.gain_test import build_gain_test_array
from laser_studio.core.debug_log import get_logger

log = get_logger()

# Bornes de la vitesse (mm/min) et de la puissance (%) de gravure d'une image.
ENGRAVE_SPEED_RANGE = (10, 20000)
ENGRAVE_POWER_RANGE = (0, 100)
# Bornes de la découpe de l'ancien mode SVG.
CUT_SPEED_RANGE = (10, 5000)
CUT_POWER_RANGE = (0, 100)
CUT_PASSES_RANGE = (0, 99)


def _clamp(value, bounds):
    low, high = bounds
    return min(max(int(value), low), high)


def estimate_duration_text(seconds):
    """Durée de l'estimation rapide, par exemple « 3min 07s » ou « 1h 05min »."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m:02d}min"
    return f"{m}min {s:02d}s"


class JobController(QObject):
    """Préparation et génération du job.

    Modèles : `layers` (LayersModel), `grbl` (GrblConfig), `machine`
    (MachineConfig), `image_settings` (ImageSettings). `dialogs` : UserDialogs.

    État de l'interface, lu à chaque usage :
    - geometry() : dict width_mm, height_mm, origin_pos, offset_x, offset_y ;
    - image() : image tramée à graver (tableau numpy) ou None ;
    - svg_path() : SVG de l'ancien mode découpe, ou None ;
    - vector_objects() : objets de l'éditeur vectoriel ;
    - optimize_path() : True pour réordonner les tracés (moins de G0) ;
    - lines_mm() : résolution de gravure (lignes/mm) ;
    - material_summary() : rappel de la matière, pour la confirmation.

    Signaux :
    - started() : génération lancée (le thread démarre) ;
    - progress(pct) ;
    - generated(gcode, nb_lignes, puissance_moyenne, durée) : G-Code prêt
      (job, matrice de test ou motif aller/retour) ;
    - failed(texte) : la génération a échoué dans le thread ;
    - imported(gcode, chemin) : fichier G-Code importé ;
    - log(texte) : ligne pour la console ;
    - status(texte) : message pour la barre d'état.
    """

    started = pyqtSignal()
    progress = pyqtSignal(int)
    generated = pyqtSignal(str, int, float, str)
    failed = pyqtSignal(str)
    imported = pyqtSignal(str, str)
    log = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, layers, grbl, machine, image_settings, dialogs, *, geometry, image,
                 svg_path=lambda: None, vector_objects=lambda: [], optimize_path=lambda: True,
                 lines_mm=lambda: 10.0, material_summary=lambda: "", parent=None):
        super().__init__(parent)
        self.layers = layers
        self.grbl = grbl
        self.machine = machine
        self.image_settings = image_settings
        self.dialogs = dialogs
        self._geometry = geometry
        self._image = image
        self._svg_path = svg_path
        self._vector_objects = vector_objects
        self._optimize_path = optimize_path
        self._lines_mm = lines_mm
        self._material_summary = material_summary
        # Ancien mode SVG : découpe d'un SVG entier (svg_path), avec un seul
        # réglage. Plus accessible depuis l'interface, mais encore lu dans les
        # anciens projets et les profils matériaux (voir set_cut_settings).
        self.cut_enabled = False
        self.cut_speed = 300
        self.cut_power = 90
        self.cut_passes = 2
        # Dernière matrice de test générée : un clic sur une de ses cases dans
        # l'aperçu 2D en applique les réglages (voir apply_matrix_cell).
        self.last_test_matrix_params = None
        self.worker = None
        self.matrix_worker = None
        self.gain_test_worker = None

    # -- réglages de la gravure d'une image et de l'ancienne découpe SVG

    # La gravure d'une image (tramage, séparation couleur) utilise la vitesse
    # et la puissance du calque de gravure (LayersModel.engrave_layer). Elles
    # sont LUES dans le calque à chaque usage : il n'en existe pas de copie
    # qui pourrait diverger du calque affiché.

    @property
    def engrave_speed(self):
        """Vitesse (mm/min) de la gravure d'une image, entière, ramenée dans
        ENGRAVE_SPEED_RANGE."""
        layer = self.layers.engrave_layer()
        speed = layer.speed if layer else BASE_LAYER_DEFAULTS["engrave"][4]
        return _clamp(speed, ENGRAVE_SPEED_RANGE)

    @property
    def engrave_power(self):
        """Puissance (%) de la gravure d'une image, entière, ramenée dans
        ENGRAVE_POWER_RANGE."""
        layer = self.layers.engrave_layer()
        power = layer.power if layer else BASE_LAYER_DEFAULTS["engrave"][3]
        return _clamp(power, ENGRAVE_POWER_RANGE)

    @property
    def image_overscan_enabled(self):
        """True si le surbalayage s'applique à la gravure d'une image : activé
        dans Configuration GRBL ET pour le calque de gravure."""
        return layer_overscan_enabled(self.layers.engrave_layer(), self.grbl.overscan_enabled)

    @property
    def image_laser_cmd(self):
        """Commande laser ("M4" ou "M3") de la gravure d'une image : celle du
        calque de gravure, sinon celle de Configuration GRBL."""
        return layer_laser_cmd(self.layers.engrave_layer(), self.grbl.laser_cmd)

    def set_engrave_settings(self, speed, power):
        """Écrit la vitesse (mm/min) et la puissance (%) de la gravure d'une
        image dans le calque de gravure (ex. case de la matrice de test,
        ancien projet sans calques). Valeurs entières, ramenées dans
        ENGRAVE_SPEED_RANGE et ENGRAVE_POWER_RANGE."""
        layer = self.layers.engrave_layer()
        if layer is not None:
            self.layers.update(layer.id, speed=_clamp(speed, ENGRAVE_SPEED_RANGE),
                               power=_clamp(power, ENGRAVE_POWER_RANGE))

    def set_cut_settings(self, speed, power, passes):
        """Vitesse (mm/min), puissance (%) et passes de la découpe de l'ancien
        mode SVG. Valeurs entières, ramenées dans CUT_SPEED_RANGE,
        CUT_POWER_RANGE et CUT_PASSES_RANGE."""
        self.cut_speed = _clamp(speed, CUT_SPEED_RANGE)
        self.cut_power = _clamp(power, CUT_POWER_RANGE)
        self.cut_passes = _clamp(passes, CUT_PASSES_RANGE)

    def engrave_layer_label(self):
        """Nom et mode du calque de la gravure image, ex. « Gravure  [Gravure Remplie] »."""
        layer = self.layers.engrave_layer()
        return layer_label(layer) if layer else ""

    def check_engrave_layer(self):
        """Avant de graver une image : s'il n'y a aucun calque en mode Gravure
        Remplie, le premier calque sert, et un message le signale."""
        layer = self.layers.engrave_layer()
        if layer is None or layer.mode != MODE_FILL:
            self.status.emit(tr("vector.no_engrave_layer"))

    # -- paramètres

    def overscan_mode_value(self):
        """Mode de surbalayage sous une forme indépendante de la langue : les
        libellés du menu sont traduits, le générateur compare à
        OVERSCAN_PERCENT."""
        return OVERSCAN_PERCENT if self.grbl.overscan_mode == 1 else OVERSCAN_FIXED

    def _overscan_values(self):
        return {
            'enable_overscan': self.grbl.overscan_enabled,
            'overscan_mode': self.overscan_mode_value(),
            'overscan_dist': self.grbl.overscan_dist_mm,
            'overscan_pct': self.grbl.overscan_pct,
            # Décalage des lignes retour (mm), propre à la machine.
            'scan_offset_mm': self.grbl.scan_offset_mm,
        }

    def build_params(self):
        """Paramètres de génération du G-Code (voir gcode.job.build_job_gcode)."""
        params = dict(self._geometry())
        params.update({
            'speed_engrave': self.engrave_speed,
            'power_engrave': self.engrave_power,
            'enable_cut': self.cut_enabled,
            'speed_cut': self.cut_speed,
            'power_cut': self.cut_power,
            'passes_cut': self.cut_passes,
            'laser_cmd': self.grbl.laser_cmd,
            # Gravure d'image : commande et surbalayage de son calque de gravure.
            'image_laser_cmd': self.image_laser_cmd,
            'image_overscan': self.image_overscan_enabled,
            'algo': self.image_settings.algorithm,
            's_max': self.grbl.smax,
            'homing': self.grbl.homing_enabled,
            'start_gcode': self.grbl.start_gcode,
            'end_gcode': self.grbl.end_gcode,
            # Graver avant de découper ; intérieurs avant extérieurs (voir vector/order.py).
            'safe_cut_order': self.grbl.safe_cut_order,
        })
        params.update(self._overscan_values())
        return params

    def _overscan_check_distance(self, params):
        if params['overscan_mode'] == OVERSCAN_PERCENT:
            return params['width_mm'] * (params['overscan_pct'] / 100.0)
        return params['overscan_dist']

    # -- génération du job

    def generate(self):
        """Contrôle le job (taille, vitesses, surbalayage, confirmations), puis
        lance la génération dans un thread. Renvoie True si elle a démarré."""
        try:
            return self._generate()
        except Exception as e:
            error_text = f"{e}\n\n{traceback.format_exc()}"
            self.log.emit(f"\n; ERREUR AVANT GÉNÉRATION :\n; {error_text}")
            self.dialogs.error(tr("laser.error"), tr("gen.start_failed").format(error=error_text))
            return False

    def _generate(self):
        processed_array = self._image()
        # Image (tramage / séparation couleur) : toujours en mode gravure par
        # défaut, avant la lecture des vitesses/puissances ci-dessous.
        if processed_array is not None:
            self.check_engrave_layer()
        geometry = self._geometry()
        job_w, job_h = geometry['width_mm'], geometry['height_mm']
        bed_w, bed_h = self.machine.bed_w, self.machine.bed_h
        if job_w > bed_w or job_h > bed_h:
            self.dialogs.warning(
                tr("gen.too_big_title"),
                tr("gen.too_big_body").format(
                    job_w=job_w, job_h=job_h, bed_w=bed_w, bed_h=bed_h,
                    tab_machine=tr("tab.machine_params"), tab_dims=tr("ui.tab_image_tracing"),
                ),
            )
            return False

        max_speed_limit = self.machine.max_speed
        speeds_to_check = [(tr("gen.speed_row_engrave"), self.engrave_speed)]
        if self.cut_enabled:
            speeds_to_check.append((tr("gen.speed_row_cut_old"), self.cut_speed))
        for layer in self.layers.layers:
            if layer.enabled:
                speeds_to_check.append((tr("gen.speed_row_layer").format(name=layer.name), layer.speed))
        over_limit = [(name, spd) for name, spd in speeds_to_check if spd > max_speed_limit]
        if over_limit:
            details = "\n".join(f"  • {name} : {spd:.0f} mm/min" for name, spd in over_limit)
            if not self.dialogs.ask_yes_no(
                    tr("gen.speed_limit_title"),
                    tr("gen.speed_limit_body").format(
                        limit=max_speed_limit, details=details, tab_machine=tr("tab.machine_params"),
                    )):
                return False

        objects = list(self._vector_objects())
        if processed_array is not None and objects:
            layer_names = sorted(set(
                self.layers.get(o.layer_id).name for o in objects if self.layers.get(o.layer_id)
            ))
            summary = (
                tr("gen.confirm_image") + "\n"
                + tr("gen.confirm_vectors").format(
                    count=len(objects), layers=len(layer_names),
                    names=', '.join(layer_names) if layer_names else '—',
                )
            )
            if not self.dialogs.confirm(tr("gen.confirm_title"), tr("gen.confirm_body").format(summary=summary)):
                return False

        params = self.build_params()

        if params['image_overscan'] and processed_array is not None:
            overscan_check = self._overscan_check_distance(params)
            base_x_check = image_origin(params)[0]
            if base_x_check - overscan_check < 0:
                self.dialogs.error(
                    tr("gen.overscan_title"),
                    tr("gen.overscan_body").format(
                        overscan=overscan_check, offset=params['offset_x'],
                        start=base_x_check - overscan_check,
                        tab_dims=tr("ui.tab_image_tracing"), tab_grbl=tr("tab.grbl_config"),
                    ),
                )
                return False

        # Extraction géométrique des calques vectoriels (texte/formes) : se fait
        # ici dans le thread principal (Qt requis), le résultat est du texte/nombres
        # purs, sans risque pour le thread qui va s'en servir.
        vector_layers_data = extract_vector_layer_data(objects, self.layers, optimize_path=self._optimize_path())

        if params['enable_overscan']:
            vec_overscan_check = self._overscan_check_distance(params)
            base_x = (params['offset_x'] - (params['width_mm'] / 2.0)
                      if params['origin_pos'] == ORIGIN_CENTER else params['offset_x'])
            for data in vector_layers_data.values():
                layer = data["layer"]
                if layer["mode"] != MODE_FILL or not data["polygons"] or not layer_overscan_enabled(layer, True):
                    continue
                min_x = min(p[0] for poly in data["polygons"] for p in poly)
                if base_x + min_x - vec_overscan_check < 0:
                    self.dialogs.error(
                        tr("gen.overscan_vec_title"),
                        tr("gen.overscan_vec_body").format(
                            name=layer['name'], overscan=vec_overscan_check,
                            start=base_x + min_x - vec_overscan_check, tab_grbl=tr("tab.grbl_config"),
                        ),
                    )
                    return False

        # Dernier garde-fou avant de générer une gravure image : rappel de la
        # puissance et de la vitesse, comme l'alerte de surbalayage ci-dessus.
        if processed_array is not None:
            if not self.dialogs.confirm(
                    tr("gen.engrave_confirm_title"),
                    tr("gen.engrave_confirm_body").format(
                        layer=self.engrave_layer_label() or "—",
                        power=params['power_engrave'], speed=params['speed_engrave'],
                        width=params['width_mm'], height=params['height_mm'],
                        material=self._material_summary(),
                    )):
                return False

        self.worker = AdvancedGCodeWorker(processed_array, self._svg_path(), params, vector_layers_data)
        self.worker.finished.connect(self.generated)
        self.worker.progress.connect(self.progress)
        self.worker.error.connect(self.failed)
        # La fenêtre affiche l'aperçu dès le lancement (il se remplit à la fin).
        self.started.emit()
        self.worker.start()
        return True

    # -- estimation rapide

    def estimate(self):
        """Estimation RAPIDE du temps de gravure/découpe, sans générer le
        G-Code complet : utile pour ajuster vitesse/résolution avant de
        lancer un calcul complet (qui peut prendre du temps sur une grande
        image). Approximatif par nature (ignore accélérations/G0)."""
        total_seconds = 0.0
        details = []

        processed_array = self._image()
        if processed_array is not None:
            w_mm = self._geometry()['width_mm']
            speed = self.engrave_speed
            # Surbalayage de chaque côté d'une ligne, comme à la génération :
            # désactivé, distance fixe ou pourcentage de la largeur de l'image.
            if self.image_overscan_enabled:
                if self.overscan_mode_value() == OVERSCAN_PERCENT:
                    overscan = w_mm * self.grbl.overscan_pct / 100.0
                else:
                    overscan = self.grbl.overscan_dist_mm
            else:
                overscan = 0.0
            # Comme la génération : lignes vides sautées, chaque ligne balayée de son premier à son
            # dernier pixel gravé, plus le surbalayage.
            burned = np.asarray(processed_array) < 255
            swept = burned.any(axis=1)
            first = burned.argmax(axis=1)
            last = burned.shape[1] - 1 - burned[:, ::-1].argmax(axis=1)
            step_x = w_mm / max(burned.shape[1], 1)
            distance = float(((last + 1 - first) * step_x + 2 * overscan)[swept].sum())
            t = (distance / max(speed, 1)) * 60.0
            total_seconds += t
            details.append(tr("gcode.image_details").format(duration=estimate_duration_text(t)))

        svg_path = self._svg_path()
        if svg_path:
            try:
                tree = ET.parse(svg_path)
                total_len_svg = 0.0
                for elem in tree.iter():
                    d = elem.attrib.get('d')
                    if d:
                        try:
                            total_len_svg += parse_path(d).length(error=1e-3)
                        except Exception:       # tracé illisible : ignoré dans l'estimation
                            log.debug("Estimation : tracé SVG illisible ignoré", exc_info=True)
                t = (total_len_svg / max(self.cut_speed, 1)) * 60.0 * self.cut_passes
                total_seconds += t
                details.append(tr("gcode.svg_details").format(duration=estimate_duration_text(t)))
            except Exception:
                log.warning("Estimation : découpe SVG non estimée (%s)", svg_path, exc_info=True)

        objects = list(self._vector_objects())
        for layer in self.layers.layers:
            if not layer.enabled:
                continue
            objs = [o for o in objects if o.layer_id == layer.id]
            if not objs:
                continue
            if layer.mode == MODE_FILL:
                total_area = sum(o.world_path().boundingRect().width() *
                                 o.world_path().boundingRect().height() for o in objs)
                length_est = total_area / max(layer.line_interval, 0.02)
                t = (length_est / max(layer.speed, 1)) * 60.0
            else:
                total_len = sum(o.world_path().length() for o in objs)
                t = (total_len / max(layer.speed, 1)) * 60.0 * max(layer.passes, 1)
            total_seconds += t
            details.append(tr("gcode.layer_details").format(name=layer.name, duration=estimate_duration_text(t)))

        if total_seconds == 0.0:
            self.dialogs.info(tr("gcode.estimate_title"), tr("gcode.nothing_to_estimate"))
            return
        self.dialogs.info(
            tr("gcode.estimate_title_full"),
            tr("gcode.estimate_details").format(
                details="\n".join(details), total=estimate_duration_text(total_seconds)),
        )

    # -- export et import

    def export_gcode(self, extension, gcode_text):
        """Enregistre `gcode_text` dans un fichier choisi par l'utilisateur
        (extension « .gcode », « .nc »…). Renvoie le chemin, ou "" si rien n'a
        été enregistré."""
        if not gcode_text.strip():
            self.dialogs.warning(tr("gcode.empty_title"), tr("gcode.empty_export"))
            return ""
        path = self.dialogs.save_file(
            tr("gcode.export_title").format(extension=extension),
            f"job_laser{extension}",
            tr("gcode.file_filter").format(extension=extension),
        )
        if not path:
            return ""
        if not path.lower().endswith(extension):
            path += extension
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(gcode_text)
        except Exception as e:
            self.dialogs.error(tr("gcode.export_error_title"), tr("gcode.export_error").format(error=e))
            return ""
        self.dialogs.info(tr("gcode.export_success_title"), tr("gcode.export_success").format(path=path))
        return path

    def import_gcode(self):
        """Importe un fichier G-Code existant (généré par un autre outil :
        LaserGRBL, le multi-générateur kpc29laser/MGL, un export G-Code de
        LightBurn, etc.) pour l'afficher et le visualiser, sans passer par la
        génération interne. Émet imported(gcode, chemin)."""
        path = self.dialogs.open_file(tr("gcode.import_title"), tr("gcode.import_filter"))
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                gcode_text = f.read()
        except Exception as e:
            self.dialogs.error(tr("gcode.export_error_title"), tr("gcode.import_error").format(error=e))
            return
        self.imported.emit(gcode_text, path)

    # -- motifs de test

    def generate_bidir_test(self):
        """Génère le motif de calibrage du décalage aller/retour (voir
        gcode.calibration.bidir_test_gcode) avec la vitesse, la puissance et
        la résolution actuelles."""
        if self.grbl.overscan_enabled:
            overscan = self.grbl.overscan_dist_mm if self.grbl.overscan_mode == 0 else 2.5
        else:
            overscan = 0.0
        geometry = self._geometry()
        params = {
            'origin_pos': geometry['origin_pos'],
            'offset_x': geometry['offset_x'],
            'offset_y': geometry['offset_y'],
            'speed_engrave': self.engrave_speed,
            'power_engrave': self.engrave_power,
            's_max': self.grbl.smax,
            'laser_cmd': self.grbl.laser_cmd,
            'homing': self.grbl.homing_enabled,
            'start_gcode': self.grbl.start_gcode,
            'end_gcode': self.grbl.end_gcode,
            'overscan_dist': overscan,
            'line_pitch_mm': 1.0 / max(self._lines_mm(), 0.1),
        }
        result = bidir_test_gcode(params)
        # La matrice de test mémorisée ne correspond plus au G-Code affiché.
        self.last_test_matrix_params = None
        self.generated.emit(*result)
        self.dialogs.info(tr("gen.bidir_test_title"), tr("gen.bidir_test_body"))

    def generate_gain_test(self):
        """Génère la grille de test du gain de point (verre peint, onglet
        Séparation) : une ligne par valeur du curseur « Gain de point » (0 à
        20), une colonne par ton (0 à 100 %), avec la résolution, la vitesse,
        la puissance et la machine actuelles. Une fois gravée, on repère la
        ligne dont les cases passent régulièrement du noir au clair, et on
        règle le curseur sur la valeur écrite à gauche. Renvoie True si la
        génération a démarré (False : grille plus grande que le plateau)."""
        arr, w_mm, h_mm = build_gain_test_array(self._lines_mm(), mirror=self.image_settings.mirror_h)
        bed_w, bed_h = self.machine.bed_w, self.machine.bed_h
        if w_mm > bed_w or h_mm > bed_h:
            self.dialogs.warning(
                tr("sep.gain_test_title"),
                tr("sep.gain_test_too_big").format(w=w_mm, h=h_mm, bed_w=bed_w, bed_h=bed_h))
            return False
        params = self.build_params()
        params.update(width_mm=w_mm, height_mm=h_mm, algo="Floyd-Steinberg", enable_cut=False)
        self.gain_test_worker = AdvancedGCodeWorker(arr, None, params, None)
        self.gain_test_worker.finished.connect(self._on_gain_test_ready)
        self.gain_test_worker.error.connect(self.failed)
        self.gain_test_worker.start()
        return True

    def _on_gain_test_ready(self, gcode, n_lines, avg_power, time_str):
        header = (
            "; --- TEST DU GAIN DE POINT ---\n"
            "; Lignes de haut en bas : gain 0, 5, 10, 15, 20. Colonnes : 0 % (peinture intacte) a 100 % (verre degage).\n"
            "; Repere la ligne dont les cases passent regulierement du noir au clair,\n"
            "; puis regle le curseur Gain de point sur la valeur ecrite a gauche de cette ligne.\n"
        )
        self.generated.emit(header + gcode, n_lines + header.count("\n"), avg_power, time_str)
        self.dialogs.info(tr("sep.gain_test_title"), tr("sep.gain_test_done"))

    def generate_test_matrix(self, page_params, engraving, image_test=False, build_tile=None):
        """Lance la génération de la matrice de test.

        page_params : réglages de la page Matrice de test (TestMatrixPage.matrix_params).
        engraving : True pour vitesse x puissance, False pour vitesse x passes.
        image_test, build_tile : test à partir d'une image, chaque case gravant
        la zone build_tile(lignes_mm) (None si impossible, message affiché).
        Renvoie True si la génération a démarré."""
        params = dict(page_params)
        # Mode indépendant de la langue : le générateur et apply_matrix_cell comparent un code.
        params.update({'mode': MATRIX_ENGRAVE if engraving else MATRIX_CUT, 's_max': self.grbl.smax})
        params.update(self._overscan_values())
        # Test à partir d'une image : chaque case grave la zone choisie au lieu d'un carré plein.
        if engraving and image_test:
            tile = build_tile(params['lines_mm'])
            if tile is None:
                return False
            params['image_tile'] = tile
            params['cell_w'] = tile['w_mm']
            params['cell_h'] = tile['h_mm']
        self.last_test_matrix_params = dict(params)

        self.matrix_worker = TestMatrixWorker(params)
        self.matrix_worker.finished.connect(self.generated)
        self.matrix_worker.start()
        return True

    def apply_matrix_cell(self, x_mm, y_mm):
        """Clic sur l'aperçu 2D : si le G-Code affiché est la dernière matrice
        de test générée, applique la puissance et la vitesse (ou le nombre de
        passes) de la case cliquée aux réglages de gravure ou de découpe."""
        params = self.last_test_matrix_params
        if not params:
            return
        try:
            cell = matrix_cell_at(params, x_mm, y_mm)
            if cell is None:
                return
            speed, value = cell
            if params.get('mode', MATRIX_ENGRAVE) == MATRIX_ENGRAVE:
                self.set_engrave_settings(speed, value)
                self.log.emit(f">>> Case matrice appliquée : {speed} mm/min, {value}% (gravure)")
            else:
                self.set_cut_settings(speed, round(params.get('single_power', self.cut_power)), value)
                self.log.emit(f">>> Case matrice appliquée : {speed} mm/min, {value} passe(s) (découpe)")
        except Exception:  # un clic hors matrice ou une erreur de calcul ne doit jamais planter l'appli
            log.warning("Clic sur la matrice de test : case non appliquée", exc_info=True)
