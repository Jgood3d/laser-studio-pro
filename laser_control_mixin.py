"""Connexion USB/GRBL, streaming et commandes temps réel vers le laser."""
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QMessageBox)
from workers import GCodeStreamerThread, CommandThread


class LaserControlMixin:
    def refresh_com_ports(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.combo_ports.addItem(f"{p.device} - {p.description}")

    def toggle_usb(self):
        if self.usb.is_connected():
            self.usb.disconnect()
            self.btn_connect.setText("Connecter GRBL")
            self.btn_connect.setStyleSheet("")
            self.txt_console.append("Déconnecté du port COM.")
        else:
            selected = self.combo_ports.currentText()
            if not selected:
                QMessageBox.warning(self, "Erreur", "Aucun port COM sélectionné.")
                return
            port = selected.split(" - ")[0]
            if self.usb.connect(port):
                self.btn_connect.setText("Déconnecter")
                self.btn_connect.setStyleSheet("background-color: #27ae60; color: white;")
                self.txt_console.append(f"Connecté à {port} avec succès.")
            else:
                QMessageBox.critical(self, "Erreur", f"Échec de connexion sur {port}.")

    def _run_commands_async(self, commands):
        if self.cmd_thread and self.cmd_thread.isRunning():
            return
        self.cmd_thread = CommandThread(self.usb, commands)
        self.cmd_thread.log_signal.connect(self.txt_console.append)
        self.cmd_thread.start()

    def jog_move(self, dx, dy):
        if not self.usb.is_connected():
            QMessageBox.warning(self, "USB non connecté", "Connectez d'abord le laser.")
            return

        step_str = self.combo_step.currentText().replace(" mm", "")
        step = float(step_str)
        speed = self.spin_jog_speed.value()

        move_x = dx * step
        move_y = dy * step

        cmd = f"$J=G91 G21 X{move_x:.3f} Y{move_y:.3f} F{speed}"
        self._run_commands_async(cmd)

    def send_manual_direct_cmd(self, cmd):
        if not self.usb.is_connected():
            QMessageBox.warning(self, "USB non connecté", "Connectez le laser via USB.")
            return
        self._run_commands_async(cmd)

    def send_to_laser(self):
        gcode_text = self.txt_console.toPlainText()
        if not gcode_text.strip():
            QMessageBox.warning(self, "Erreur", "Aucun G-Code à envoyer.")
            return

        if not self.usb.is_connected():
            QMessageBox.warning(self, "Erreur USB", "Veuillez connecter le laser en USB.")
            return

        reply = QMessageBox.question(
            self, "Confirmer le lancement",
            "Le laser va démarrer.\n\nVérifiez que :\n"
            "- la zone de travail est dégagée,\n"
            "- le capot/protection est en place,\n"
            "- vous portez une protection oculaire adaptée.\n\n"
            "Lancer le job maintenant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_send.setEnabled(False)
        self.progress_bar.setValue(0)
        self.streamer = GCodeStreamerThread(self.usb, gcode_text)
        self.streamer.progress.connect(lambda current, total: self.progress_bar.setValue(int((current / total) * 100)))
        self.streamer.log_signal.connect(self.txt_console.append)
        self.streamer.finished_signal.connect(self.on_stream_finished)
        self.streamer.start()

    def on_stream_finished(self, clean_finish):
        self.btn_send.setEnabled(True)
        if clean_finish:
            QMessageBox.information(self, "Terminé", "Envoi du G-Code au laser terminé avec succès.")
        else:
            QMessageBox.warning(
                self, "Job interrompu",
                "L'envoi du G-Code a été interrompu (erreur GRBL, alarme, perte de "
                "connexion ou arrêt manuel). Consultez la console avant de relancer."
            )

    def send_pause(self):
        self.usb.send_raw_byte(b'!')
        self.txt_console.append(">>> Commande Temps Réel: PAUSE (!)")

    def send_resume(self):
        self.usb.send_raw_byte(b'~')
        self.txt_console.append(">>> Commande Temps Réel: REPRISE (~)")

    def send_reset(self):
        if self.streamer and self.streamer.isRunning():
            self.streamer.stop()
        self.usb.send_raw_byte(b'\x18')
        self.txt_console.append(">>> Commande Temps Réel: RESET (Ctrl+X)")

    def send_kill(self):
        if self.streamer and self.streamer.isRunning():
            self.streamer.stop()
        self.usb.send_raw_byte(b'\x18')
        self.txt_console.append(">>> ARRÊT D'URGENCE (KILL / RESET envoyé)")

    def send_manual_cmd(self):
        cmd = self.txt_manual_cmd.text().strip()
        if not cmd:
            return
        if not self.usb.is_connected():
            QMessageBox.warning(self, "USB non connecté", "Connectez le laser via USB.")
            return
        self._run_commands_async(cmd)
        self.txt_manual_cmd.clear()

    def run_frame(self):
        if not self.usb.is_connected():
            QMessageBox.warning(self, "USB non connecté", "Connectez d'abord le laser.")
            return

        w = self.spin_w.value()
        h = self.spin_h.value()
        ox = self.spin_off_x.value()
        oy = self.spin_off_y.value()
        if self.combo_origin.currentText() == "Centre":
            ox -= w / 2.0
            oy -= h / 2.0

        cmds = [
            f"G0 X{ox:.3f} Y{oy:.3f}",
            f"G0 X{ox + w:.3f} Y{oy:.3f}",
            f"G0 X{ox + w:.3f} Y{oy + h:.3f}",
            f"G0 X{ox:.3f} Y{oy + h:.3f}",
            f"G0 X{ox:.3f} Y{oy:.3f}"
        ]
        self._run_commands_async(cmds)
