"""Connexion USB/GRBL, streaming et commandes temps réel vers le laser."""
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMessageBox, QFileDialog)
from PyQt6.QtCore import QTimer
from workers import GCodeStreamerThread, CommandThread, StatusPollThread, ReconnectThread, image_origin
from i18n import tr
from grbl.simulator import SIMULATED_PORT, simulation_enabled
from debug_log import get_logger, log_gcode_summary

log = get_logger()


class LaserControlMixin:
    def refresh_com_ports(self):
        self.combo_ports.clear()
        if simulation_enabled():
            self.combo_ports.addItem(f"{SIMULATED_PORT} - {tr('usb.simulated_port')}")
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.combo_ports.addItem(f"{p.device} - {p.description}")

    def toggle_connection(self):
        if self.usb.is_connected():
            self._stop_status_poll()
            self.usb.disconnect()
            self.update_connection_widgets()
            self.txt_console.append(tr("laser.disconnected"))
            self._update_dro_display(None, None, None, None)
            self.has_homed_since_connect = False
        else:
            selected = self.combo_ports.currentText()
            if not selected:
                QMessageBox.warning(
    self,
    tr("laser.no_port_title"),
    tr("laser.no_port")
)
                return
            port = selected.split(" - ")[0]
            if self.usb.connect(port):
                self.update_connection_widgets()
                self.txt_console.append(
    tr("laser.connected").format(port=port)
)
                self.has_homed_since_connect = False
                self._check_grbl_laser_mode()
                self._start_status_poll()
            else:
                QMessageBox.critical(
    self,
    tr("laser.no_port_title"),
    tr("laser.connection_error").format(port=port)
)

    def home_machine(self):
        """Lance le homing ($H) et retient qu'il a eu lieu depuis la
        connexion — utilisé pour avertir avant un envoi de job si ça n'a
        jamais été fait (voir _confirm_homed_before_job)."""
        if not self.usb.is_connected():
            QMessageBox.warning(
                self, tr("laser.usb_not_connected_title"), tr("laser.connect_first")
            )
            return
        self._run_commands_async("$H")
        self.has_homed_since_connect = True

    def _confirm_homed_before_job(self):
        """Avertit avant de lancer un job si aucun homing n'a été fait
        depuis la connexion — une position non référencée peut décaler
        toute la pièce gravée. Renvoie True pour continuer, False pour
        annuler. Ne bloque jamais : c'est une confirmation, pas une
        interdiction (certaines machines n'ont pas de fins de course)."""
        if getattr(self, "has_homed_since_connect", False):
            return True
        reply = QMessageBox.question(
            self, tr("laser.no_homing_title"), tr("laser.no_homing_body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _start_status_poll(self):
        """Démarre le thread de polling DRO (position/état machine en
        direct) via requêtes '?' périodiques — utilisé hors streaming actif
        (idle, jog, homing...). Mis en pause pendant un job (voir
        _start_stream), car c'est alors GCodeStreamerThread
        qui interroge lui-même le statut."""
        self._stop_status_poll()
        self.status_poll_thread = StatusPollThread(self.usb)
        self.status_poll_thread.status_updated.connect(self._on_status_updated)
        # Port perdu hors job (câble débranché...) : bouton de connexion et commandes à jour.
        if hasattr(self, "update_connection_widgets"):
            self.status_poll_thread.connection_lost.connect(self.update_connection_widgets)
        self.status_poll_thread.start()

    def _stop_status_poll(self):
        thread = getattr(self, "status_poll_thread", None)
        if thread is not None:
            thread.stop()
            thread.wait(1000)
            self.status_poll_thread = None

    def _on_status_updated(self, state, x, y, z):
        """Reçu du DRO (StatusPollThread en idle, ou GCodeStreamerThread
        pendant un job) : met à jour l'affichage position/état et le
        marqueur de position sur l'aperçu 2D G-Code."""
        self._update_dro_display(state, x, y, z)
        if hasattr(self, "update_gcode_position_marker"):
            self.update_gcode_position_marker(x, y)
        # Pendant un job : les traits déjà gravés passent en rouge sur l'aperçu 2D.
        if hasattr(self, "update_burn_overlay") and self._job_in_progress():
            self.update_burn_overlay(x, y)

    def _prepare_burn_overlay(self, gcode_text):
        """Au début d'un envoi : l'aperçu 2D doit montrer le G-Code envoyé (un job de la file n'est
        pas forcément celui affiché) ; le calque « déjà gravé » repart de zéro."""
        if not hasattr(self, "plot_gcode_preview"):
            return
        if gcode_text != getattr(self, "_last_gcode_text", None):
            self.plot_gcode_preview(gcode_text)
        else:
            self.reset_burn_overlay()

    def _connect_burn_overlay(self, streamer):
        if hasattr(self, "on_lines_acked"):
            streamer.lines_acked.connect(self.on_lines_acked)

    def _update_dro_display(self, state, x, y, z):
        """Transmet l'état et la position au DRO (DroPanel.set_status)."""
        machine_panel = getattr(self, "machine_panel", None)
        if machine_panel is None:
            return
        machine_panel.dro_panel.set_status(state, x, y, z)
        # Déconnecté : plus de position connue, le point rouge de l'aperçu 2D disparaît.
        if state is None and hasattr(self, "gcode_position_marker"):
            self.gcode_position_marker.setData([], [])

    def read_grbl_settings(self):
        """Lit l'intégralité de la configuration GRBL ($$) depuis la machine
        connectée et l'affiche dans le champ dédié de l'onglet Configuration
        GRBL — au-delà des seules dimensions/focale déjà gérées par les
        profils machine, ceci couvre tous les réglages EEPROM natifs
        (steps/mm, limites logicielles, accélérations GRBL...)."""
        if not self.usb.is_connected():
            QMessageBox.warning(
                self, tr("laser.usb_not_connected_title"), tr("laser.connect_first")
            )
            return
        try:
            response = self.usb.send_command("$$")
        except Exception as e:
            QMessageBox.critical(self, tr("laser.error"), str(e))
            return
        lines = [l.strip() for l in response.splitlines() if l.strip().startswith("$")]
        if not lines:
            QMessageBox.warning(
                self, tr("ui.grbl_settings_box"), tr("ui.grbl_read_empty")
            )
            return
        self.txt_grbl_settings.setPlainText("\n".join(lines))
        self.txt_console.append(tr("ui.grbl_read_success").format(count=len(lines)))

    def send_grbl_settings(self):
        """Envoie à la machine chaque ligne $N=valeur actuellement affichée
        (après lecture, import de fichier, ou modification manuelle) —
        modifie la configuration EEPROM persistante de la machine, donc
        toujours avec confirmation avant envoi."""
        if not self.usb.is_connected():
            QMessageBox.warning(
                self, tr("laser.usb_not_connected_title"), tr("laser.connect_first")
            )
            return
        lines = [
            l.strip() for l in self.txt_grbl_settings.toPlainText().splitlines()
            if l.strip().startswith("$") and "=" in l
        ]
        if not lines:
            QMessageBox.warning(
                self, tr("ui.grbl_settings_box"), tr("ui.grbl_send_empty")
            )
            return
        reply = QMessageBox.question(
            self, tr("ui.grbl_send_confirm_title"),
            tr("ui.grbl_send_confirm_body").format(count=len(lines)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for line in lines:
            try:
                resp = self.usb.send_command(line)
            except Exception as e:
                errors.append(f"{line}: {e}")
                continue
            if "error" in resp.lower():
                errors.append(f"{line}: {resp.strip()}")
        if errors:
            self.txt_console.append(tr("ui.grbl_send_errors").format(errors="\n".join(errors)))
            QMessageBox.warning(
                self, tr("ui.grbl_settings_box"),
                tr("ui.grbl_send_partial").format(count=len(lines) - len(errors), total=len(lines)),
            )
        else:
            self.txt_console.append(tr("ui.grbl_send_success").format(count=len(lines)))
            QMessageBox.information(
                self, tr("ui.grbl_settings_box"),
                tr("ui.grbl_send_all_success").format(count=len(lines)),
            )

    def export_grbl_settings(self):
        text = self.txt_grbl_settings.toPlainText().strip()
        if not text:
            QMessageBox.warning(
                self, tr("ui.grbl_settings_box"), tr("ui.grbl_send_empty")
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("ui.grbl_export"), "grbl_settings.txt", "Texte (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text + "\n")
        except Exception as e:
            QMessageBox.critical(self, tr("laser.error"), str(e))

    def import_grbl_settings(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("ui.grbl_import"), "", "Texte (*.txt);;Tous (*.*)"
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, tr("laser.error"), str(e))
            return
        lines = [l.strip() for l in content.splitlines() if l.strip().startswith("$") and "=" in l]
        self.txt_grbl_settings.setPlainText("\n".join(lines))

    def _check_grbl_laser_mode(self):
        """Vérifie que le mode laser dynamique GRBL ($32=1) est actif : les
        optimisations du G-Code généré en mode M4 (pas de coupure laser
        renvoyée à chaque ligne, en comptant sur la coupure automatique de
        GRBL pendant les déplacements rapides G0) supposent ce réglage."""
        try:
            response = self.usb.send_command("$$")
        except Exception:
            return
        grbl_settings = self._parse_grbl_settings(response)
        self._apply_grbl_homing_setting(grbl_settings)
        value = grbl_settings.get("$32")
        if value is None:
            self.txt_console.append(tr("laser.grbl_mode_unknown"))
            return
        self.txt_console.append(
    tr("laser.grbl_mode_status").format(value=value)
)
        if value != "1":
            QMessageBox.warning(
    self,
    tr("laser.grbl_dynamic_off_title"),
    tr("laser.grbl_dynamic_off").format(value=value)
)

    @staticmethod
    def _parse_grbl_settings(response):
        """Réponse de « $$ » -> {"$32": "1", "$22": "0", ...} (commentaires « (...) » ignorés)."""
        grbl_settings = {}
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("$") and "=" in line:
                key, value = line.split("=", 1)
                grbl_settings[key.strip()] = value.split("(", 1)[0].strip()
        return grbl_settings

    def _apply_grbl_homing_setting(self, grbl_settings):
        """Homing désactivé sur la machine ($22=0) : GRBL refuserait le « $H » en tête de job
        (error:5). « Inclure $H » et le homing de la matrice de test sont donc décochés ET
        grisés, avec une infobulle qui explique pourquoi. Machine avec homing ($22 non nul) :
        les cases redeviennent utilisables, sans être recochées. Réglage inconnu (pas de
        réponse à « $$ ») : rien ne change, la case reste cochée d'office."""
        value = grbl_settings.get("$22")
        if value is None or not value.isdigit():
            return
        homing_off = value == "0"
        unchecked = False
        for name in ("chk_homing", "chk_mat_homing"):
            checkbox = getattr(self, name, None)
            if checkbox is None:
                continue
            if homing_off and checkbox.isChecked():
                checkbox.setChecked(False)
                unchecked = True
            checkbox.setEnabled(not homing_off)
            checkbox.setToolTip(tr("ui.homing_unavailable_tip") if homing_off else "")
        if unchecked:
            self.txt_console.append(tr("laser.grbl_homing_disabled"))

    def _run_commands_async(self, commands):
        if self.cmd_thread and self.cmd_thread.isRunning():
            return
        self.cmd_thread = CommandThread(self.usb, commands)
        self.cmd_thread.log_signal.connect(self.txt_console.append)
        self.cmd_thread.start()

    def jog_move(self, dx_mm, dy_mm, speed):
        """Déplacement relatif (jog) de `dx_mm`, `dy_mm`, à `speed` mm/min.

        Abonné au signal JogControlPanel.jog_requested.
        """
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_first")
)
            return

        cmd = f"$J=G91 G21 X{dx_mm:.3f} Y{dy_mm:.3f} F{speed}"
        self._run_commands_async(cmd)

    def send_manual_direct_cmd(self, cmd):
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_via_usb")
)
            return
        self._run_commands_async(cmd)

    def set_work_zero(self):
        """Fixe l'origine de travail à la position actuelle (G92 X0 Y0).

        Abonné au signal JobActionsPanel.set_work_zero_requested.
        """
        self.send_manual_direct_cmd("G92 X0 Y0")

    def go_to_work_zero(self):
        """Ramène la tête à l'origine de travail (G0 X0 Y0).

        Abonné au signal JobActionsPanel.go_to_work_zero_requested.
        """
        self.send_manual_direct_cmd("G0 X0 Y0")

    def send_job(self):
        gcode_text = self.txt_console.toPlainText()
        log.info("Envoi : clic sur « Envoyer au laser » (port ouvert=%s, homing fait=%s, état %s)",
                 self.usb.is_connected(), getattr(self, "has_homed_since_connect", False),
                 self.usb.last_state)
        log_gcode_summary(log, "Envoi : G-Code de la console", gcode_text)
        if not gcode_text.strip():
            QMessageBox.warning(
    self,
    tr("laser.no_port_title"),
    tr("laser.no_gcode")
)
            return

        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_error_title"),
    tr("laser.connect_via_usb")
)
            return

        if not self._confirm_homed_before_job():
            return

        reply = QMessageBox.question(
    self,
    tr("laser.confirm_title"),
    tr("laser.confirm_body"),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    QMessageBox.StandardButton.No
)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.machine_panel.jog_panel.set_send_enabled(False)
        self._pause_status_poll()
        # Mémorisé pour "Répéter le dernier job" (voir repeat_last_job) —
        # le G-Code RÉELLEMENT envoyé, pas juste généré, pour que "répéter"
        # corresponde toujours à ce qui a vraiment été gravé la dernière
        # fois, même si la console a changé depuis (nouvelle génération,
        # import...).
        self._last_sent_gcode = gcode_text
        if hasattr(self, "machine_panel"):
            self.machine_panel.job_actions_panel.set_repeat_enabled(True)
        self.tab_job_queue.clear_sent_gcode()
        self.tab_job_queue.append_sent_gcode([tr("queue.sent_log_direct")])
        self._start_stream(gcode_text, self.on_stream_finished)

    def _start_stream(self, gcode_text, on_finished):
        """Lance l'envoi de `gcode_text` au graveur (GCodeStreamerThread),
        pour « Envoyer au laser » comme pour chaque job de la file.

        Barre de progression, aperçu 2D (traits gravés en rouge), suivi du
        G-Code envoyé, console, DRO et perte de connexion suivent l'envoi ;
        `on_finished(fin_propre)` est appelée à la fin. L'envoi en cours
        reste dans self.streamer (arrêt d'urgence, Reset...).
        """
        self.machine_panel.progress_bar.setValue(0)
        self._prepare_burn_overlay(gcode_text)
        self.streamer = GCodeStreamerThread(self.usb, gcode_text)
        self._connect_burn_overlay(self.streamer)
        self.streamer.lines_sent.connect(self.tab_job_queue.append_sent_gcode)
        self.streamer.progress.connect(
            lambda current, total: self.machine_panel.progress_bar.setValue(
                int((current / total) * 100) if total else 0))
        self.streamer.log_signal.connect(self.txt_console.append)
        self.streamer.status_updated.connect(self._on_status_updated)
        self.streamer.finished_signal.connect(on_finished)
        self.streamer.connection_lost.connect(self._on_job_connection_lost)
        self.streamer.start()

    def _stream_ended(self, clean_finish):
        """Fin d'un envoi (direct ou job de la file) : repère de fin dans le
        suivi, contrôle de la position, aperçu 2D."""
        self.tab_job_queue.mark_sent_end(clean_finish)
        self._check_position_after_stream()
        if hasattr(self, "finish_burn_overlay"):
            self.finish_burn_overlay(clean_finish)

    def _pause_status_poll(self):
        """Pendant un envoi, c'est GCodeStreamerThread qui interroge l'état."""
        if getattr(self, "status_poll_thread", None):
            self.status_poll_thread.pause()

    def _resume_status_poll(self):
        if getattr(self, "status_poll_thread", None):
            self.status_poll_thread.resume()

    def _on_job_connection_lost(self):
        """Coupure USB détectée en cours de job (voir GCodeStreamerThread) :
        tente de rouvrir automatiquement le même port en arrière-plan. Le
        job reste arrêté (voir on_stream_finished, déjà appelé séparément
        avec clean_finish=False) — seule la LIAISON est rétablie
        automatiquement, jamais l'envoi du G-Code."""
        port = getattr(self.usb, "last_port", None)
        if not port:
            return
        self.txt_console.append(tr("laser.reconnecting"))
        self._reconnect_thread = ReconnectThread(self.usb, port, getattr(self.usb, "last_baudrate", 115200))
        self._reconnect_thread.reconnected.connect(self._on_reconnect_result)
        self._reconnect_thread.start()

    def _on_reconnect_result(self, success):
        self.update_connection_widgets()
        if success:
            self.has_homed_since_connect = False
            self._start_status_poll()
            self.txt_console.append(tr("laser.reconnect_success"))
            QMessageBox.warning(
                self, tr("laser.reconnect_success_title"), tr("laser.reconnect_success_body")
            )
        else:
            self.txt_console.append(tr("laser.reconnect_failed"))
            QMessageBox.critical(
                self, tr("laser.reconnect_failed_title"), tr("laser.reconnect_failed_body")
            )

    def repeat_last_job(self):
        """Relance directement le dernier G-Code effectivement envoyé au
        laser, sans repasser par tout le pipeline de réglages — pratique
        pour une petite série de pièces identiques. Réutilise send_job
        (donc les mêmes vérifications de sécurité : connexion, homing,
        confirmation)."""
        last = getattr(self, "_last_sent_gcode", None)
        if not last:
            return
        self.txt_console.setPlainText(last)
        self.send_job()

    def unlock_alarm(self):
        """Envoie $X (déverrouillage GRBL) suite à une alarme (ex : fin de
        course déclenchée). Toujours une action volontaire de
        l'utilisateur — jamais envoyé automatiquement sans clic, l'alarme
        pouvant signaler un vrai problème mécanique à vérifier avant de
        reprendre."""
        if not self.usb.is_connected():
            return
        self._run_commands_async("$X")
        self.txt_console.append(tr("laser.unlock_log"))

    def _notify_job_finished(self):
        """Signal sonore de fin de job (2 bips espacés) — en plus du
        message déjà affiché, pour être prévenu même sans regarder l'écran
        (ex : gravure longue, utilisateur dans une autre pièce)."""
        QTimer.singleShot(0, QApplication.beep)
        QTimer.singleShot(250, QApplication.beep)

    def _check_position_after_stream(self):
        """Après un job arrêté sur erreur GRBL (voir GCodeStreamerThread._stop_machine_after_error) :
        si le reset a eu lieu machine encore en mouvement, la position n'est plus fiable, comme
        pour un RESET manuel (_soft_reset) : on retire le statut « référencé »."""
        streamer = getattr(self, "streamer", None)
        if streamer is not None and getattr(streamer, "position_lost", False):
            self.has_homed_since_connect = False
            self.txt_console.append(tr("laser.position_lost_log"))

    def on_stream_finished(self, clean_finish):
        log.info("Envoi : terminé, fin propre=%s", clean_finish)
        self._stream_ended(clean_finish)
        self.machine_panel.jog_panel.set_send_enabled(True)
        self._resume_status_poll()
        self._notify_job_finished()
        if clean_finish:
            QMessageBox.information(
    self,
    tr("laser.finished_title"),
    tr("laser.finished")
)
        else:
            QMessageBox.warning(
    self,
    tr("laser.interrupted_title"),
    tr("laser.interrupted")
)

    def send_pause(self):
        self.usb.send_raw_byte(b'!')
        self.txt_console.append(tr("laser.pause_log"))

    def send_resume(self):
        self.usb.send_raw_byte(b'~')
        self.txt_console.append(tr("laser.resume_log"))

    def _soft_reset(self, log_key):
        """Reset logiciel GRBL (0x18), commun à RESET et KILL : arrête
        l'envoi en cours puis réinitialise le contrôleur.

        Si la machine n'était PAS à l'arrêt complet (job en cours, pause,
        jog, état inconnu), GRBL perd sa position (ALARM:3 « Reset while in
        motion »). On retire alors le statut « référencé » pour que le
        prochain job redemande un homing, au lieu de se fier à une position
        devenue fausse. Un reset fait machine à l'arrêt (Idle) ne change
        rien : la position reste valide."""
        streaming = bool(self.streamer and self.streamer.isRunning())
        was_idle = (not streaming) and getattr(self.usb, "last_state", None) == "Idle"
        if streaming:
            self.streamer.stop()
        self.usb.send_raw_byte(b'\x18')
        self.txt_console.append(tr(log_key))
        if not was_idle:
            self.has_homed_since_connect = False
            self.txt_console.append(tr("laser.position_lost_log"))

    def send_reset(self):
        self._soft_reset("laser.reset_log")

    def emergency_stop(self):
        self._soft_reset("laser.kill_log")

    def send_console_command(self, cmd):
        """Envoie une commande GRBL tapée dans la console directe.

        Abonné au signal DirectConsolePanel.command_submitted.
        """
        if not cmd:
            return
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_first")
)
            return
        self._run_commands_async(cmd)

    def run_frame(self):
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_first")
)
            return

        w = self.spin_w.value()
        h = self.spin_h.value()
        ox, oy = image_origin({'origin_pos': self.combo_origin.currentText(),
                               'offset_x': self.spin_off_x.value(), 'offset_y': self.spin_off_y.value(),
                               'width_mm': w, 'height_mm': h})

        cmds = [
            f"G0 X{ox:.3f} Y{oy:.3f}",
            f"G0 X{ox + w:.3f} Y{oy:.3f}",
            f"G0 X{ox + w:.3f} Y{oy + h:.3f}",
            f"G0 X{ox:.3f} Y{oy + h:.3f}",
            f"G0 X{ox:.3f} Y{oy:.3f}"
        ]
        self._run_commands_async(cmds)
