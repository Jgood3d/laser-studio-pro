"""Graveur, côté logique : choix du port, connexion et vérification des
réglages GRBL, pilotage (jog, homing, zéro, cadrage, pause, reset, console),
envoi d'un job et sa fin, configuration GRBL ($$).

Le dialogue avec GRBL (port série, threads) est dans MachineConnection ; les
commandes sont construites par grbl/commands.py. Ce contrôleur ne touche pas
aux widgets : il lit l'état de l'interface par des fonctions, pose ses
questions par UserDialogs et prévient la fenêtre par signaux.

    engraver = EngraverController(connection, grbl, UserDialogs(window),
                                  selected_port=panel.selected_port, ...)
    panel.connect_requested.connect(engraver.toggle_connection)
    engraver.ports_changed.connect(panel.set_ports)
"""
import serial.tools.list_ports
from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger, log_gcode_summary
from laser_studio.gcode import framing
from laser_studio.gcode.preview import parse_preview_cached
from laser_studio.gcode.raster import image_origin
from laser_studio.gcode.rotary import RotaryConfig, RotaryError, machine_gcode, machine_lines, surface_y
from laser_studio.grbl import commands
from laser_studio.grbl.ports import load_last_port, port_labels, port_of, preferred_index, save_last_port
from laser_studio.grbl.simulator import SIMULATED_PORT, simulation_enabled
from laser_studio.grbl.streaming import gcode_lines, resume_gcode
from laser_studio.i18n import tr
from laser_studio.models import machine_state as ms

log = get_logger()

GRBL_SETTINGS_FILE_FILTER = "Texte (*.txt);;Tous (*.*)"


def launch_confirmation_text(warnings=(), question=None):
    """Texte de la seule fenêtre avant un envoi : l'avertissement de sécurité du démarrage (mêmes traductions),
    puis, s'il y en a, les points à vérifier (`warnings`, un par ligne : G-Code périmé, pas de homing, lignes à
    risque), puis la liste des vérifications et la question (`question`, sinon celle du lancement)."""
    parts = [tr("startup.safety.body"), tr("startup.safety.detail"), ""]
    if warnings:
        parts += [tr("laser.check_title")] + [f"• {warning}" for warning in warnings] + [""]
    parts.append(question or tr("laser.confirm_body"))
    return "\n".join(parts)


class EngraverController(QObject):
    """Pilotage du graveur.

    `connection` : MachineConnection. `grbl` : GrblConfig (configuration
    GRBL affichée, lue et envoyée par read_settings / send_settings).
    `dialogs` : UserDialogs.

    État de l'interface, lu à chaque usage :
    - selected_port() : libellé du port choisi (« /dev/ttyUSB0 - USB Serial ») ;
    - current_gcode() : G-Code affiché, envoyé par send_job ;
    - job_geometry() : dict width_mm, height_mm, origin_pos, offset_x,
      offset_y (cadrage) ;
    - set_homing_available(disponible, infobulle) : grise ou non les cases
      « homing » ; renvoie True si une case cochée a dû être décochée.

    Signaux :
    - ports_changed(libellés, indice) : liste des ports à afficher ;
    - disconnected() : port fermé par l'utilisateur (plus de position connue) ;
    - log(texte) : message pour la console ;
    - direct_job_started() / direct_job_finished() : « Envoyer au laser »
      (bouton d'envoi, suivi du G-Code envoyé) ;
    - stream_starting(gcode) : un envoi commence (direct ou file d'attente) :
      barre de progression, aperçu 2D ;
    - stream_ended(fin_propre) : un envoi se termine : suivi, aperçu 2D ;
    - gcode_restored(gcode) : « Répéter le dernier job » remet le G-Code
      envoyé dans la console ;
    - job_done() : fin d'un job ou de la file (signal sonore) ;
    - resume_available(bool) : un job s'est arrêté avant la fin et peut être repris (resume_job) ;
    - resume_starting(gcode, décalage) : juste avant le stream_starting d'une reprise : `gcode` est le job
      entier, et la ligne envoyée n de la reprise est sa ligne n + décalage (l'aperçu 2D garde le job entier
      et continue le tracé déjà gravé).
    """

    ports_changed = pyqtSignal(list, int)
    disconnected = pyqtSignal()
    log = pyqtSignal(str)
    direct_job_started = pyqtSignal()
    direct_job_finished = pyqtSignal()
    stream_starting = pyqtSignal(str)
    stream_ended = pyqtSignal(bool)
    gcode_restored = pyqtSignal(str)
    job_done = pyqtSignal()
    resume_available = pyqtSignal(bool)
    resume_starting = pyqtSignal(str, int)

    def __init__(self, connection, grbl, dialogs, *, selected_port=lambda: "", current_gcode=lambda: "",
                 job_geometry=None, set_homing_available=lambda available, tip: False,
                 gcode_stale=lambda gcode_text: False, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.grbl = grbl
        self.dialogs = dialogs
        self._selected_port = selected_port
        self._current_gcode = current_gcode
        self._job_geometry = job_geometry
        self._set_homing_available = set_homing_available
        # G-Code généré avant un changement de réglage ? (JobController.is_stale)
        self._gcode_stale = gcode_stale
        connection.reconnected.connect(self._on_reconnect_result)
        # Envoi en cours (G-Code, lignes acquittées, dernière position de la tête) et job arrêté avant la fin,
        # à reprendre (resume_job) : (G-Code, lignes acquittées, position de la tête à l'arrêt ou None).
        self._streaming = None
        self._acked = 0
        self._head = None
        self._await_stop_position = False
        self.resume_point = None
        connection.stream_lines_acked.connect(self._lines_acked)
        connection.status_updated.connect(self._status_updated)

    # -- port et connexion

    def allowed(self, action, message_key="laser.connect_first"):
        """Vrai si `action` (models/machine_state.py : ms.JOG, ms.SEND_JOB…) est permise dans l'état du
        graveur ; sinon, dit pourquoi (pas connecté : `message_key`, occupé, en alarme) et renvoie Faux. Les
        boutons sont déjà grisés d'après la même table : ce message couvre les raccourcis et la file."""
        if self.connection.can(action):
            return True
        state = self.connection.state
        if state == ms.DISCONNECTED:
            self.dialogs.warning(tr("laser.usb_not_connected_title"), tr(message_key))
        elif state == ms.ALARM:
            self.dialogs.warning(tr("laser.alarm_title"), tr("laser.alarm_blocked"))
        else:
            self.dialogs.warning(tr("laser.busy_title"), tr("laser.busy"))
        return False

    def refresh_ports(self):
        """Liste les ports utilisables (sans les ports « n/a » sans matériel),
        les ports USB en tête, et resélectionne le port affiché avant
        l'actualisation, sinon le dernier port auquel on s'est connecté."""
        wanted = port_of(self._selected_port()) or load_last_port()
        labels = []
        if simulation_enabled():
            labels.append(f"{SIMULATED_PORT} - {tr('usb.simulated_port')}")
        labels += port_labels(serial.tools.list_ports.comports())
        self.ports_changed.emit(labels, preferred_index(labels, wanted))

    def ensure_connected(self):
        """Connecte au port choisi (liste des ports relue d'abord) ; sans effet si déjà connecté, au contraire
        de toggle_connection (Premiers pas)."""
        if self.connection.is_connected():
            return
        self.refresh_ports()
        self.toggle_connection()

    def toggle_connection(self):
        """Connecte au port choisi, ou déconnecte."""
        if self.connection.is_connected():
            self.connection.disconnect()
            self.log.emit(tr("laser.disconnected"))
            self.disconnected.emit()
            return
        selected = self._selected_port()
        if not selected:
            self.dialogs.warning(tr("laser.no_port_title"), tr("laser.no_port"))
            return
        port = port_of(selected)
        if not self.connection.connect(port):
            self.dialogs.error(tr("laser.no_port_title"), tr("laser.connection_error").format(port=port))
            return
        save_last_port(port)
        self.log.emit(tr("laser.connected").format(port=port))
        self.check_grbl_settings()

    def check_grbl_settings(self):
        """Lit les réglages du graveur ($$) juste après la connexion.

        - Aucune réponse : le graveur ne répond pas sur ce port (mauvais
          port choisi ?) ; on prévient, sans rien changer aux réglages.
        - $22 (homing) : voir _apply_homing_support.
        - $32 (mode laser) absent : impossible de vérifier le mode laser,
          on prévient. Différent de 1 : le mode laser dynamique est coupé.
          Les optimisations du G-Code généré en mode M4 (pas de coupure
          laser renvoyée à chaque ligne, en comptant sur la coupure
          automatique de GRBL pendant les déplacements rapides G0)
          supposent ce réglage.
        """
        try:
            grbl_settings = self.connection.read_settings()
        except Exception:
            log.warning("Lecture de $$ impossible : $22 et $32 non vérifiés", exc_info=True)
            return
        if not grbl_settings:
            log.info("Connexion : aucune réponse à $$")
            self.dialogs.warning(
                tr("laser.grbl_no_answer_title"),
                tr("laser.grbl_no_answer").format(port=self.connection.port or "?"),
            )
            return
        self._apply_homing_support(grbl_settings)
        value = grbl_settings.get(commands.LASER_MODE_SETTING)
        if value is None:
            self.log.emit(tr("laser.grbl_mode_unknown"))
            self.dialogs.warning(tr("laser.grbl_mode_missing_title"), tr("laser.grbl_mode_missing"))
            return
        self.log.emit(tr("laser.grbl_mode_status").format(value=value))
        if value != "1":
            self.dialogs.warning(tr("laser.grbl_dynamic_off_title"),
                                 tr("laser.grbl_dynamic_off").format(value=value))

    def _apply_homing_support(self, grbl_settings):
        """Homing ($22) d'après la réponse à « $$ ».

        - $22=0 (homing désactivé) ou $22 absent (homing non supporté) :
          GRBL refuserait le « $H » en tête de job (error:5). « Inclure $H »
          et le homing de la matrice de test sont décochés ET grisés, avec
          une infobulle qui explique pourquoi. Le décochage est enregistré
          dans le profil de la machine : la case reste décochée aux
          prochains démarrages. Message « Homing non supporté » seulement si
          une case était encore cochée (pas à chaque connexion).
        - $22 non nul : les cases redeviennent utilisables, sans être
          recochées.
        - Valeur illisible : rien ne change.
        """
        support = commands.homing_support(grbl_settings)
        if support is None:
            return
        available, reason = support
        tip = ""
        if not available:
            tip = tr("ui.homing_unavailable_tip" if reason == "disabled" else "ui.homing_unsupported_tip")
        if self._set_homing_available(available, tip):
            self.log.emit(tr("laser.grbl_homing_disabled"))
            self.dialogs.warning(tr("laser.homing_unsupported_title"), tr("laser.homing_unsupported"))

    def _on_reconnect_result(self, success):
        """Reconnexion automatique après une coupure USB pendant un job (le
        job, lui, reste arrêté)."""
        if success:
            self.log.emit(tr("laser.reconnect_success"))
            self.dialogs.warning(tr("laser.reconnect_success_title"), tr("laser.reconnect_success_body"))
        else:
            self.log.emit(tr("laser.reconnect_failed"))
            self.dialogs.error(tr("laser.reconnect_failed_title"), tr("laser.reconnect_failed_body"))

    # -- pilotage

    def home(self):
        """Lance le homing ($H) ; la position devient référencée (voir
        confirm_homed)."""
        if self.allowed(ms.HOME):
            self.connection.home()

    def jog(self, dx_mm, dy_mm, speed):
        """Déplacement relatif de `dx_mm`, `dy_mm`, à `speed` mm/min
        (JogControlPanel.jog_requested)."""
        if self.allowed(ms.JOG):
            self.connection.jog(dx_mm, dy_mm, speed)

    def send_direct(self, cmd):
        """Envoie un déplacement (zéro, retour au zéro…) ou une liste de commandes, si permis."""
        if self.allowed(ms.JOG, "laser.connect_via_usb"):
            self.connection.run_commands(cmd)

    def set_work_zero(self):
        """Origine de travail à la position actuelle (JobActionsPanel)."""
        self.send_direct(commands.SET_WORK_ZERO)

    def go_to_work_zero(self):
        """Retour à l'origine de travail (JobActionsPanel)."""
        self.send_direct(commands.GO_TO_WORK_ZERO)

    def send_console_command(self, cmd):
        """Commande GRBL tapée dans la console directe."""
        if cmd and self.allowed(ms.CONSOLE):
            self.connection.run_commands(cmd)

    def frame(self, contour=False):
        """Cadrage, laser allumé à GrblConfig.frame_power_pct % du S-Max (0,5 % par défaut, réglage de la
        machine) pour voir le parcours, d'après le G-Code de la
        console (ce qui sera gravé : image et calques vectoriels). Rectangle : X max, Y max, retour à X0
        puis Y0 ; sans G-Code, le cadre de l'image. `contour` : le tour au plus près de chaque pièce
        (gcode.framing.contour_paths), qui demande le G-Code."""
        if not self.allowed(ms.JOG):
            return
        text = self._current_gcode()
        segments = parse_preview_cached(text).burn_segments if text.strip() else []
        if contour:
            paths = framing.contour_paths(segments)
            if not paths:
                self.dialogs.warning(tr("frame.title"), tr("frame.need_gcode"))
                return
        else:
            extent = framing.burn_extent(segments)
            if extent is None:
                geometry = self._job_geometry()
                x, y = image_origin(geometry)
                extent = (x, y, x + geometry.width_mm, y + geometry.height_mm)
            paths = [framing.box_path(extent)]
        power = self.grbl.smax * self.grbl.frame_power_pct / 100.0
        frame = commands.frame_commands(paths, power)
        self.connection.run_commands(machine_lines(frame, self._rotary_config()))

    def unlock(self):
        """Envoie $X (déverrouillage GRBL) suite à une alarme (ex : fin de
        course déclenchée). Toujours une action volontaire de
        l'utilisateur, l'alarme pouvant signaler un vrai problème mécanique."""
        if not self.connection.can(ms.UNLOCK):
            return
        self.connection.unlock()
        self.log.emit(tr("laser.unlock_log"))

    def pause(self):
        """Pause (bouton, F7) ; sans effet si le graveur ne peut pas la recevoir (déconnecté)."""
        if not self.connection.can(ms.REALTIME):
            return
        self.connection.pause()
        self.log.emit(tr("laser.pause_log"))

    def resume(self):
        """Reprise (bouton vert, F8) : après une pause pendant un envoi, la reprise temps réel (~) ; sans envoi en
        cours et avec un job interrompu, la reprise de ce job (resume_job) : c'est ce bouton qu'on cherche après
        un arrêt d'urgence, et ~ n'y ferait rien. Sans effet si le graveur ne peut pas la recevoir."""
        if self.resume_point is not None and not self.connection.is_streaming():
            self.resume_job()
            return
        if not self.connection.can(ms.REALTIME):
            return
        self.connection.resume()
        self.log.emit(tr("laser.resume_log"))

    def reset(self):
        self.log.emit(tr("laser.reset_log"))
        self.connection.soft_reset()

    def emergency_stop(self):
        """Arrêt d'urgence (bouton du panneau, de la barre d'outils, F9) : reset immédiat du graveur ; sans effet
        s'il ne peut pas le recevoir (déconnecté)."""
        if not self.connection.can(ms.REALTIME):
            return
        self.log.emit(tr("laser.kill_log"))
        self.connection.soft_reset()

    # -- envoi d'un job

    def confirm_safe_gcode(self, gcode_text):
        """Avant un envoi ou un ajout à la file : un G-Code généré avant un changement de réglage (calque, taille,
        image…) ou qui réécrit la configuration de GRBL ($130=…, $RST=*) ou dépasse le S-Max n'est envoyé qu'après
        confirmation. True pour continuer."""
        if self._gcode_stale(gcode_text) and not self.dialogs.confirm_default_no(
                tr("laser.stale_gcode_title"), tr("laser.stale_gcode_body")):
            return False
        lines = commands.risky_lines(gcode_text, self.grbl.smax)
        if not lines:
            return True
        return self.dialogs.confirm_default_no(
            tr("laser.risky_gcode_title"),
            tr("laser.risky_gcode_body").format(smax=self.grbl.smax, lines="\n".join(lines)))

    def launch_warnings(self, gcode_text=None):
        """Points à vérifier avant d'envoyer `gcode_text` (None : reprise, G-Code déjà vérifié) : G-Code périmé,
        lignes qui réécrivent la configuration ou dépassent le S-Max, pas de homing depuis la connexion."""
        warnings = []
        if gcode_text is not None:
            if self._gcode_stale(gcode_text):
                warnings.append(tr("laser.check_stale"))
            lines = commands.risky_lines(gcode_text, self.grbl.smax)
            if lines:
                warnings.append(tr("laser.check_risky").format(smax=self.grbl.smax, lines="\n    ".join(lines)))
        if not self.connection.homed:
            warnings.append(tr("laser.check_not_homed"))
        return warnings

    def confirm_homed(self):
        """Avertit avant de lancer un job si aucun homing n'a été fait
        depuis la connexion — une position non référencée peut décaler
        toute la pièce gravée. True pour continuer. Ne bloque jamais :
        certaines machines n'ont pas de fins de course."""
        if self.connection.homed:
            return True
        return self.dialogs.confirm_default_no(tr("laser.no_homing_title"), tr("laser.no_homing_body"))

    def _rotary_config(self):
        """Axe rotatif d'après la configuration GRBL (gcode/rotary.py)."""
        return RotaryConfig.from_settings(self.grbl)

    def _surface_head(self, x, y):
        """Position de la tête rapportée par la machine -> position sur la surface du G-Code à plat, que la
        reprise d'un job (resume_gcode) compare aux traits. Axe rotatif sur Y : Y est reconverti. Axe dédié
        (A) : GRBL ne rapporte pas A dans Y, la position en Y est inconnue (None : la reprise repart alors
        quelques lignes avant l'arrêt, sans chercher le point exact)."""
        config = self._rotary_config()
        if not config.active:
            return (x, y)
        return (x, surface_y(y, config)) if config.axis == "Y" else None

    def _rotary_error(self, error):
        self.dialogs.error(tr("rotary.error_title"), tr("rotary.error_body").format(reason=error))

    def _check_rotary(self, gcode_text):
        """Avec l'axe rotatif, le G-Code doit pouvoir être converti (pas d'arc ni de pouces) : sinon
        l'envoi est refusé avant toute confirmation. Renvoie True si l'envoi peut continuer."""
        try:
            machine_gcode(gcode_text, self._rotary_config())
        except RotaryError as error:
            self._rotary_error(error)
            return False
        return True

    def _rotary_confirmation(self):
        """Rappel ajouté à la confirmation de lancement quand l'axe rotatif est actif."""
        config = self._rotary_config()
        if not config.active:
            return ""
        return "\n\n" + tr("laser.confirm_rotary").format(axis=config.axis, diameter=config.object_mm)

    def send_job(self, gcode_text=None):
        """« Envoyer au laser » : le G-Code affiché (ou `gcode_text`), après UNE fenêtre de confirmation qui
        rappelle la sécurité et liste ce qui pose problème (G-Code périmé ou à risque, pas de homing) : une suite
        de questions finissait par être validée sans être lue. Renvoie True si l'envoi a démarré."""
        if gcode_text is None:
            gcode_text = self._current_gcode()
        log.info("Envoi : clic sur « Envoyer au laser » (port ouvert=%s, homing fait=%s, état %s)",
                 self.connection.is_connected(), self.connection.homed, self.connection.last_state)
        log_gcode_summary(log, "Envoi : G-Code de la console", gcode_text)
        if not gcode_text.strip():
            self.dialogs.warning(tr("laser.no_port_title"), tr("laser.no_gcode"))
            return False
        if not self._check_rotary(gcode_text):
            return False
        if not self.allowed(ms.SEND_JOB, "laser.connect_via_usb"):     # aussi : job, homing en cours
            return False
        if not self.dialogs.confirm_default_no(
                tr("laser.confirm_title"),
                launch_confirmation_text(self.launch_warnings(gcode_text)) + self._rotary_confirmation()):
            return False
        self.direct_job_started.emit()
        self.connection.pause_status_poll()
        self.start_stream(gcode_text, self._on_direct_job_finished)
        return True

    def resume_job(self):
        """Reprend le job arrêté avant la fin (alarme, arrêt, coupure) là où il s'était arrêté, avec l'état du
        G-Code à ce point (grbl.streaming.resume_gcode), après confirmation et le rappel du homing."""
        if self.resume_point is None:
            return False
        gcode_text, acked, head = self.resume_point
        resume = resume_gcode(gcode_text, acked, head=head)
        if resume is None:
            self._set_resume_point(None)
            return False
        text, line, total = resume
        if self.connection.state == ms.ALARM:
            # Après un arrêt d'urgence, GRBL est en alarme : il faut d'abord retrouver une position sûre.
            self.dialogs.warning(tr("laser.resume_title"), tr("laser.resume_alarm"))
            return False
        if not self.allowed(ms.SEND_JOB, "laser.connect_via_usb"):
            return False
        question = tr("laser.resume_body").format(line=line, total=total)
        if not self.dialogs.confirm_default_no(
                tr("laser.resume_title"),
                launch_confirmation_text(self.launch_warnings(), question) + self._rotary_confirmation()):
            return False
        self.direct_job_started.emit()
        self.connection.pause_status_poll()
        start = line - 1                                       # 1re ligne du job reprise (lignes envoyées)
        prologue = len(gcode_lines(text)) - (total - start)    # retour au point d'arrêt, état du G-Code
        self.resume_starting.emit(gcode_text, start - prologue)
        self.start_stream(text, self._on_direct_job_finished)
        return True

    def _lines_acked(self, acked):
        self._acked = acked

    def _status_updated(self, state, x, y, _z):
        """Position de la tête pendant un envoi ; après un arrêt avant la fin, la première position rapportée
        machine arrêtée (exacte) devient celle de la reprise, puis ne bouge plus (un homing ensuite ne compte
        pas)."""
        if self._streaming is not None:
            self._head = self._surface_head(x, y)
        elif self._await_stop_position and state != "Run":
            self._await_stop_position = False
            if self.resume_point is not None:
                gcode_text, acked, _head = self.resume_point
                self.resume_point = (gcode_text, acked, self._surface_head(x, y))

    def _set_resume_point(self, point):
        self.resume_point = point
        self.resume_available.emit(point is not None)

    def repeat_last_job(self):
        """Relance le dernier G-Code effectivement envoyé (même si la console
        a changé depuis), avec les mêmes vérifications que send_job."""
        last = self.connection.last_sent_gcode
        if not last:
            return
        self.gcode_restored.emit(last)
        self.send_job(last)

    def start_stream(self, gcode_text, on_finished):
        """Lance l'envoi de `gcode_text`, pour « Envoyer au laser » comme pour
        chaque job de la file ; `on_finished(fin_propre)` est appelée à la fin."""
        self._streaming, self._acked, self._head = gcode_text, 0, None
        self._await_stop_position = False
        self._set_resume_point(None)
        self.stream_starting.emit(gcode_text)
        # Aperçu, suivi et « Répéter » gardent le G-Code à plat ; seule la machine reçoit le G-Code converti.
        try:
            machine_text = machine_gcode(gcode_text, self._rotary_config(), header=False)
        except RotaryError as error:
            self._rotary_error(error)
            on_finished(False)
            return None
        return self.connection.start_stream(gcode_text, on_finished, stream_text=machine_text)

    def end_stream(self, clean_finish):
        """Fin d'un envoi (direct ou job de la file) : suivi, contrôle de la
        position, aperçu 2D. Arrêté avant la fin : le job peut être repris (resume_job)."""
        if self._streaming is not None:
            self._set_resume_point(None if clean_finish else (self._streaming, self._acked, self._head))
            self._await_stop_position = not clean_finish
            self._streaming = None
        self.stream_ended.emit(clean_finish)
        self.connection.check_position_after_stream()

    def notify_job_done(self):
        """Fin d'un job ou de la file : signal sonore (job_done)."""
        self.job_done.emit()

    def _on_direct_job_finished(self, clean_finish):
        log.info("Envoi : terminé, fin propre=%s", clean_finish)
        self.end_stream(clean_finish)
        self.direct_job_finished.emit()
        self.connection.resume_status_poll()
        self.notify_job_done()
        if clean_finish:
            self.dialogs.info(tr("laser.finished_title"), tr("laser.finished"))
        else:
            text = tr("laser.interrupted")
            if self.resume_point is not None:
                text += "\n\n" + tr("laser.interrupted_resume")
            self.dialogs.warning(tr("laser.interrupted_title"), text)

    # -- configuration GRBL ($$)

    def read_settings(self):
        """Lit toute la configuration GRBL ($$) du graveur connecté et la met
        dans GrblConfig (affichée dans Configuration GRBL) : steps/mm,
        limites logicielles, accélérations…"""
        if not self.allowed(ms.SETTINGS):
            return
        try:
            response = self.connection.send_command(commands.READ_SETTINGS)
        except Exception as e:
            self.dialogs.error(tr("laser.error"), str(e))
            return
        lines = commands.response_setting_lines(response)
        if not lines:
            self.dialogs.warning(tr("ui.grbl_settings_box"), tr("ui.grbl_read_empty"))
            return
        self.grbl.update(grbl_settings="\n".join(lines))
        self.log.emit(tr("ui.grbl_read_success").format(count=len(lines)))

    def send_settings(self):
        """Envoie chaque ligne $N=valeur affichée : modifie la configuration
        EEPROM persistante du graveur, donc toujours après confirmation."""
        if not self.allowed(ms.SETTINGS):
            return
        lines = commands.setting_lines(self.grbl.grbl_settings)
        if not lines:
            self.dialogs.warning(tr("ui.grbl_settings_box"), tr("ui.grbl_send_empty"))
            return
        if not self.dialogs.confirm_default_no(tr("ui.grbl_send_confirm_title"),
                                               tr("ui.grbl_send_confirm_body").format(count=len(lines))):
            return
        errors = []
        for line in lines:
            try:
                resp = self.connection.send_command(line)
            except Exception as e:
                errors.append(f"{line}: {e}")
                continue
            if "error" in resp.lower():
                errors.append(f"{line}: {resp.strip()}")
        if errors:
            self.log.emit(tr("ui.grbl_send_errors").format(errors="\n".join(errors)))
            self.dialogs.warning(tr("ui.grbl_settings_box"),
                                 tr("ui.grbl_send_partial").format(count=len(lines) - len(errors), total=len(lines)))
        else:
            self.log.emit(tr("ui.grbl_send_success").format(count=len(lines)))
            self.dialogs.notify(tr("ui.grbl_send_all_success").format(count=len(lines)))

    def export_settings(self):
        """Enregistre la configuration GRBL affichée dans un fichier texte."""
        text = self.grbl.grbl_settings.strip()
        if not text:
            self.dialogs.warning(tr("ui.grbl_settings_box"), tr("ui.grbl_send_empty"))
            return
        path = self.dialogs.save_file(tr("ui.grbl_export"), "grbl_settings.txt", "Texte (*.txt)")
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text + "\n")
        except Exception as e:
            self.dialogs.error(tr("laser.error"), str(e))

    def import_settings(self):
        """Charge une configuration GRBL depuis un fichier (lignes $N=valeur)."""
        path = self.dialogs.open_file(tr("ui.grbl_import"), GRBL_SETTINGS_FILE_FILTER)
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.dialogs.error(tr("laser.error"), str(e))
            return
        self.grbl.update(grbl_settings="\n".join(commands.setting_lines(content)))
