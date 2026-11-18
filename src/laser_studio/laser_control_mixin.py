"""Connexion au graveur, côté interface : boîtes de dialogue, panneau machine,
aperçu 2D. Le dialogue avec GRBL (port, threads, état « référencé ») est dans
controllers.machine_connection.MachineConnection (self.connection)."""
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMessageBox, QFileDialog)
from PyQt6.QtCore import QTimer
from laser_studio.controllers.machine_connection import parse_grbl_settings
from laser_studio.workers import image_origin
from laser_studio.i18n import tr
from laser_studio.grbl.ports import load_last_port, port_labels, port_of, save_last_port
from laser_studio.grbl.simulator import SIMULATED_PORT, simulation_enabled
from laser_studio.core.debug_log import get_logger, log_gcode_summary

log = get_logger()


class LaserControlMixin:
    """Abonné aux signaux de self.connection (voir _connect_machine_signals)
    et des panneaux de la machine (toggle_connection, jog_move, send_job...)."""

    def _connect_machine_signals(self):
        """Abonne la fenêtre aux signaux de la connexion au graveur."""
        c = self.connection
        c.connection_changed.connect(lambda _connected: self.update_connection_widgets())
        c.status_updated.connect(self._on_status_updated)
        c.log.connect(self.log_message)
        c.position_lost.connect(lambda: self.log_message(tr("laser.position_lost_log")))
        c.stream_progress.connect(
            lambda current, total: self.machine_panel.progress_bar.setValue(
                int((current / total) * 100) if total else 0))
        c.stream_lines_sent.connect(self.machine_panel.sent_gcode_log.append_lines)
        if hasattr(self, "on_lines_acked"):
            c.stream_lines_acked.connect(self.on_lines_acked)
        c.reconnecting.connect(lambda: self.log_message(tr("laser.reconnecting")))
        c.reconnected.connect(self._on_reconnect_result)

    def _require_connection(self, message_key="laser.connect_first"):
        """Vrai si le graveur est connecté ; sinon, le dit et renvoie Faux."""
        if self.connection.is_connected():
            return True
        QMessageBox.warning(self, tr("laser.usb_not_connected_title"), tr(message_key))
        return False

    def refresh_com_ports(self):
        """Liste les ports utilisables (sans les ports « n/a » sans matériel),
        les ports USB en tête, et resélectionne le port affiché avant
        l'actualisation, sinon le dernier port auquel on s'est connecté."""
        wanted = port_of(self.combo_ports.currentText()) or load_last_port()
        self.combo_ports.clear()
        if simulation_enabled():
            self.combo_ports.addItem(f"{SIMULATED_PORT} - {tr('usb.simulated_port')}")
        self.combo_ports.addItems(port_labels(serial.tools.list_ports.comports()))
        for index in range(self.combo_ports.count()):
            if wanted and port_of(self.combo_ports.itemText(index)) == wanted:
                self.combo_ports.setCurrentIndex(index)
                break

    def toggle_connection(self):
        if self.connection.is_connected():
            self.connection.disconnect()
            self.log_message(tr("laser.disconnected"))
            self._update_dro_display(None, None, None, None)
            return
        selected = self.combo_ports.currentText()
        if not selected:
            QMessageBox.warning(self, tr("laser.no_port_title"), tr("laser.no_port"))
            return
        port = port_of(selected)
        if not self.connection.connect(port):
            QMessageBox.critical(
                self, tr("laser.no_port_title"), tr("laser.connection_error").format(port=port))
            return
        save_last_port(port)
        self.log_message(tr("laser.connected").format(port=port))
        self._check_grbl_laser_mode()

    def home_machine(self):
        """Lance le homing ($H) ; la position devient référencée (voir
        _confirm_homed_before_job)."""
        if self._require_connection():
            self.connection.home()

    def _confirm_homed_before_job(self):
        """Avertit avant de lancer un job si aucun homing n'a été fait
        depuis la connexion — une position non référencée peut décaler
        toute la pièce gravée. Renvoie True pour continuer, False pour
        annuler. Ne bloque jamais : c'est une confirmation, pas une
        interdiction (certaines machines n'ont pas de fins de course)."""
        if self.connection.homed:
            return True
        reply = QMessageBox.question(
            self, tr("laser.no_homing_title"), tr("laser.no_homing_body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _on_status_updated(self, state, x, y, z):
        """État et position du graveur (sondage hors job, thread d'envoi
        pendant un job) : affichage, marqueur de position sur l'aperçu 2D,
        traits déjà gravés en rouge pendant un job."""
        self._update_dro_display(state, x, y, z)
        if hasattr(self, "update_gcode_position_marker"):
            self.update_gcode_position_marker(x, y)
        if hasattr(self, "update_burn_overlay") and self.connection.is_streaming():
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

    def _update_dro_display(self, state, x, y, z):
        """Transmet l'état (cadre Connexion) et la position (sous le pilotage)
        au panneau machine (MachinePanel.set_status)."""
        machine_panel = getattr(self, "machine_panel", None)
        if machine_panel is None:
            return
        machine_panel.set_status(state, x, y, z)
        # Déconnecté : plus de position connue, le point rouge de l'aperçu 2D disparaît.
        if state is None and hasattr(self, "gcode_position_marker"):
            self.gcode_position_marker.setData([], [])

    def read_grbl_settings(self):
        """Lit l'intégralité de la configuration GRBL ($$) depuis la machine
        connectée et l'affiche dans le champ dédié de l'onglet Configuration
        GRBL — au-delà des seules dimensions/focale déjà gérées par les
        profils machine, ceci couvre tous les réglages EEPROM natifs
        (steps/mm, limites logicielles, accélérations GRBL...)."""
        if not self.connection.is_connected():
            QMessageBox.warning(
                self, tr("laser.usb_not_connected_title"), tr("laser.connect_first")
            )
            return
        try:
            response = self.connection.send_command("$$")
        except Exception as e:
            QMessageBox.critical(self, tr("laser.error"), str(e))
            return
        lines = [l.strip() for l in response.splitlines() if l.strip().startswith("$")]
        if not lines:
            QMessageBox.warning(
                self, tr("ui.grbl_settings_box"), tr("ui.grbl_read_empty")
            )
            return
        self.grbl.update(grbl_settings="\n".join(lines))
        self.log_message(tr("ui.grbl_read_success").format(count=len(lines)))

    def send_grbl_settings(self):
        """Envoie à la machine chaque ligne $N=valeur actuellement affichée
        (après lecture, import de fichier, ou modification manuelle) —
        modifie la configuration EEPROM persistante de la machine, donc
        toujours avec confirmation avant envoi."""
        if not self.connection.is_connected():
            QMessageBox.warning(
                self, tr("laser.usb_not_connected_title"), tr("laser.connect_first")
            )
            return
        lines = [
            l.strip() for l in self.grbl.grbl_settings.splitlines()
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
                resp = self.connection.send_command(line)
            except Exception as e:
                errors.append(f"{line}: {e}")
                continue
            if "error" in resp.lower():
                errors.append(f"{line}: {resp.strip()}")
        if errors:
            self.log_message(tr("ui.grbl_send_errors").format(errors="\n".join(errors)))
            QMessageBox.warning(
                self, tr("ui.grbl_settings_box"),
                tr("ui.grbl_send_partial").format(count=len(lines) - len(errors), total=len(lines)),
            )
        else:
            self.log_message(tr("ui.grbl_send_success").format(count=len(lines)))
            QMessageBox.information(
                self, tr("ui.grbl_settings_box"),
                tr("ui.grbl_send_all_success").format(count=len(lines)),
            )

    def export_grbl_settings(self):
        text = self.grbl.grbl_settings.strip()
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
        self.grbl.update(grbl_settings="\n".join(lines))

    @staticmethod
    def _launch_confirmation_text():
        """Texte de « Confirmer le lancement » : l'avertissement de sécurité du
        démarrage (mêmes traductions), puis la liste des vérifications et la
        question."""
        return "\n".join((
            tr("startup.safety.body"),
            tr("startup.safety.detail"),
            "",
            tr("laser.confirm_body"),
        ))

    def _check_grbl_laser_mode(self):
        """Lit les réglages du graveur ($$) juste après la connexion.

        - Aucune réponse : le graveur ne répond pas sur ce port (mauvais
          port choisi ?) ; on prévient, sans rien changer aux réglages.
        - $22 (homing) : voir _apply_grbl_homing_setting.
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
            return
        if not grbl_settings:
            log.info("Connexion : aucune réponse à $$")
            self._warn(
                tr("laser.grbl_no_answer_title"),
                tr("laser.grbl_no_answer").format(port=self.connection.port or "?"),
            )
            return
        self._apply_grbl_homing_setting(grbl_settings)
        value = grbl_settings.get("$32")
        if value is None:
            self.log_message(tr("laser.grbl_mode_unknown"))
            self._warn(tr("laser.grbl_mode_missing_title"),
                       tr("laser.grbl_mode_missing"))
            return
        self.log_message(
    tr("laser.grbl_mode_status").format(value=value)
)
        if value != "1":
            self._warn(
    tr("laser.grbl_dynamic_off_title"),
    tr("laser.grbl_dynamic_off").format(value=value)
)

    def _warn(self, title, body):
        """Boîte d'avertissement (remplacée dans les tests)."""
        QMessageBox.warning(self, title, body)

    @staticmethod
    def _parse_grbl_settings(response):
        """Réponse de « $$ » -> {"$32": "1", "$22": "0", ...} (voir
        controllers.machine_connection.parse_grbl_settings)."""
        return parse_grbl_settings(response)

    def _apply_grbl_homing_setting(self, grbl_settings):
        """Homing ($22) d'après la réponse à « $$ ».

        - $22=0 (homing désactivé) ou $22 absent (homing non supporté) :
          GRBL refuserait le « $H » en tête de job (error:5). « Inclure $H »
          et le homing de la matrice de test sont décochés ET grisés, avec
          une infobulle qui explique pourquoi. Le décochage est enregistré
          dans le profil de la machine (signal homing_changed de la page
          Configuration GRBL) : la case reste décochée aux prochains
          démarrages. Message « Homing non supporté » seulement si une case
          était encore cochée (pas à chaque connexion).
        - $22 non nul : les cases redeviennent utilisables, sans être
          recochées.
        - Valeur illisible : rien ne change.
        """
        value = grbl_settings.get("$22")
        if value is not None and not value.isdigit():
            return
        homing_off = value is None or value == "0"
        tip = ""
        if homing_off:
            tip = tr("ui.homing_unavailable_tip" if value == "0"
                     else "ui.homing_unsupported_tip")
        unchecked = False
        for name in ("chk_homing", "chk_mat_homing"):
            checkbox = getattr(self, name, None)
            if checkbox is None:
                continue
            if homing_off and checkbox.isChecked():
                checkbox.setChecked(False)
                unchecked = True
            checkbox.setEnabled(not homing_off)
            checkbox.setToolTip(tip)
        if unchecked:
            self.log_message(tr("laser.grbl_homing_disabled"))
            self._warn(tr("laser.homing_unsupported_title"),
                       tr("laser.homing_unsupported"))

    def jog_move(self, dx_mm, dy_mm, speed):
        """Déplacement relatif (jog) de `dx_mm`, `dy_mm`, à `speed` mm/min.

        Abonné au signal JogControlPanel.jog_requested.
        """
        if self._require_connection():
            self.connection.jog(dx_mm, dy_mm, speed)

    def send_manual_direct_cmd(self, cmd):
        if self._require_connection("laser.connect_via_usb"):
            self.connection.run_commands(cmd)

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
                 self.connection.is_connected(), self.connection.homed,
                 self.connection.last_state)
        log_gcode_summary(log, "Envoi : G-Code de la console", gcode_text)
        if not gcode_text.strip():
            QMessageBox.warning(self, tr("laser.no_port_title"), tr("laser.no_gcode"))
            return
        if not self.connection.is_connected():
            QMessageBox.warning(self, tr("laser.usb_error_title"), tr("laser.connect_via_usb"))
            return
        if not self._confirm_homed_before_job():
            return
        reply = QMessageBox.question(
            self,
            tr("laser.confirm_title"),
            self._launch_confirmation_text(),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.machine_panel.jog_panel.set_send_enabled(False)
        self._pause_status_poll()
        # « Répéter le dernier job » rejoue le G-Code RÉELLEMENT envoyé
        # (connection.last_sent_gcode), même si la console a changé depuis.
        self.machine_panel.job_actions_panel.set_repeat_enabled(True)
        self.machine_panel.sent_gcode_log.clear_lines()
        self.machine_panel.sent_gcode_log.append_lines([tr("queue.sent_log_direct")])
        self._start_stream(gcode_text, self.on_stream_finished)

    def _start_stream(self, gcode_text, on_finished):
        """Lance l'envoi de `gcode_text` au graveur, pour « Envoyer au
        laser » comme pour chaque job de la file.

        Barre de progression, aperçu 2D (traits gravés en rouge), suivi du
        G-Code envoyé, console et DRO suivent l'envoi par les signaux de la
        connexion (voir _connect_machine_signals) ; `on_finished(fin_propre)`
        est appelée à la fin.
        """
        self.machine_panel.progress_bar.setValue(0)
        self._prepare_burn_overlay(gcode_text)
        return self.connection.start_stream(gcode_text, on_finished)

    def _stream_ended(self, clean_finish):
        """Fin d'un envoi (direct ou job de la file) : repère de fin dans le
        suivi, contrôle de la position, aperçu 2D."""
        self.machine_panel.sent_gcode_log.mark_end(clean_finish)
        self.connection.check_position_after_stream()
        if hasattr(self, "finish_burn_overlay"):
            self.finish_burn_overlay(clean_finish)

    def _pause_status_poll(self):
        """Pendant un envoi, c'est le thread d'envoi qui interroge l'état."""
        self.connection.pause_status_poll()

    def _resume_status_poll(self):
        self.connection.resume_status_poll()

    def _on_reconnect_result(self, success):
        """Reconnexion automatique après une coupure USB pendant un job (le
        job, lui, reste arrêté)."""
        if success:
            self.log_message(tr("laser.reconnect_success"))
            QMessageBox.warning(
                self, tr("laser.reconnect_success_title"), tr("laser.reconnect_success_body")
            )
        else:
            self.log_message(tr("laser.reconnect_failed"))
            QMessageBox.critical(
                self, tr("laser.reconnect_failed_title"), tr("laser.reconnect_failed_body")
            )

    def repeat_last_job(self):
        """Relance directement le dernier G-Code effectivement envoyé au
        laser, sans repasser par tout le pipeline de réglages — pratique
        pour une petite série de pièces identiques. Réutilise send_job
        (donc les mêmes vérifications de sécurité : connexion, homing,
        confirmation)."""
        last = self.connection.last_sent_gcode
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
        if not self.connection.is_connected():
            return
        self.connection.unlock()
        self.log_message(tr("laser.unlock_log"))

    def _notify_job_finished(self):
        """Signal sonore de fin de job (2 bips espacés) — en plus du
        message déjà affiché, pour être prévenu même sans regarder l'écran
        (ex : gravure longue, utilisateur dans une autre pièce)."""
        QTimer.singleShot(0, QApplication.beep)
        QTimer.singleShot(250, QApplication.beep)

    def on_stream_finished(self, clean_finish):
        log.info("Envoi : terminé, fin propre=%s", clean_finish)
        self._stream_ended(clean_finish)
        self.machine_panel.jog_panel.set_send_enabled(True)
        self._resume_status_poll()
        self._notify_job_finished()
        if clean_finish:
            QMessageBox.information(self, tr("laser.finished_title"), tr("laser.finished"))
        else:
            QMessageBox.warning(self, tr("laser.interrupted_title"), tr("laser.interrupted"))

    def send_pause(self):
        self.connection.pause()
        self.log_message(tr("laser.pause_log"))

    def send_resume(self):
        self.connection.resume()
        self.log_message(tr("laser.resume_log"))

    def send_reset(self):
        self.log_message(tr("laser.reset_log"))
        self.connection.soft_reset()

    def emergency_stop(self):
        self.log_message(tr("laser.kill_log"))
        self.connection.soft_reset()

    def send_console_command(self, cmd):
        """Envoie une commande GRBL tapée dans la console directe.

        Abonné au signal DirectConsolePanel.command_submitted.
        """
        if cmd and self._require_connection():
            self.connection.run_commands(cmd)

    def run_frame(self):
        if not self._require_connection():
            return

        w = self.spin_w.value()
        h = self.spin_h.value()
        ox, oy = image_origin({'origin_pos': self.job_position_box.origin(),
                               'offset_x': self.spin_off_x.value(), 'offset_y': self.spin_off_y.value(),
                               'width_mm': w, 'height_mm': h})

        cmds = [
            f"G0 X{ox:.3f} Y{oy:.3f}",
            f"G0 X{ox + w:.3f} Y{oy:.3f}",
            f"G0 X{ox + w:.3f} Y{oy + h:.3f}",
            f"G0 X{ox:.3f} Y{oy + h:.3f}",
            f"G0 X{ox:.3f} Y{oy:.3f}"
        ]
        self.connection.run_commands(cmds)
