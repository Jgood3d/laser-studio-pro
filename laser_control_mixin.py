"""Connexion USB/GRBL, streaming et commandes temps réel vers le laser."""
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QMessageBox)
from workers import GCodeStreamerThread, CommandThread, StatusPollThread
from i18n import tr


class LaserControlMixin:
    def refresh_com_ports(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.combo_ports.addItem(f"{p.device} - {p.description}")

    def toggle_usb(self):
        if self.usb.is_connected():
            self._stop_status_poll()
            self.usb.disconnect()
            self.btn_connect.setText(tr("laser.connect"))
            self.btn_connect.setStyleSheet("")
            self.txt_console.append(tr("laser.disconnected"))
            self._update_dro_display(None, None, None, None)
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
                self.btn_connect.setText(tr("laser.disconnect"))
                self.btn_connect.setStyleSheet("background-color: #27ae60; color: white;")
                self.txt_console.append(
    tr("laser.connected").format(port=port)
)
                self._check_grbl_laser_mode()
                self._start_status_poll()
            else:
                QMessageBox.critical(
    self,
    tr("laser.no_port_title"),
    tr("laser.connection_error").format(port=port)
)

    def _start_status_poll(self):
        """Démarre le thread de polling DRO (position/état machine en
        direct) via requêtes '?' périodiques — utilisé hors streaming actif
        (idle, jog, homing...). Mis en pause pendant un job (voir
        send_to_laser / run_job_queue), car c'est alors GCodeStreamerThread
        qui interroge lui-même le statut."""
        self._stop_status_poll()
        self.status_poll_thread = StatusPollThread(self.usb)
        self.status_poll_thread.status_updated.connect(self._on_status_updated)
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

    def _update_dro_display(self, state, x, y, z):
        if not hasattr(self, "lbl_dro_state"):
            return
        if state is None:
            self.lbl_dro_state.setText(tr("ui.dro_state").format(value="—"))
            self.lbl_dro_x.setText(tr("ui.dro_x").format(value="—"))
            self.lbl_dro_y.setText(tr("ui.dro_y").format(value="—"))
            self.lbl_dro_z.setText(tr("ui.dro_z").format(value="—"))
            return
        self.lbl_dro_state.setText(tr("ui.dro_state").format(value=state))
        self.lbl_dro_x.setText(tr("ui.dro_x").format(value=f"{x:.3f}"))
        self.lbl_dro_y.setText(tr("ui.dro_y").format(value=f"{y:.3f}"))
        self.lbl_dro_z.setText(tr("ui.dro_z").format(value=f"{z:.3f}"))
        state_colors = {
            "Idle": "#2ecc71", "Run": "#3498db", "Hold": "#e67e22",
            "Alarm": "#e74c3c", "Home": "#9b59b6", "Jog": "#1abc9c",
        }
        color = state_colors.get(state, "#cccccc")
        self.lbl_dro_state.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _check_grbl_laser_mode(self):
        """Vérifie que le mode laser dynamique GRBL ($32=1) est actif : les
        optimisations du G-Code généré en mode M4 (pas de coupure laser
        renvoyée à chaque ligne, en comptant sur la coupure automatique de
        GRBL pendant les déplacements rapides G0) supposent ce réglage."""
        try:
            response = self.usb.send_command("$$")
        except Exception:
            return
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("$32="):
                value = line.split("=", 1)[1].strip()
                self.txt_console.append(
    tr("laser.grbl_mode_status").format(value=value)
)
                if value != "1":
                    QMessageBox.warning(
    self,
    tr("laser.grbl_dynamic_off_title"),
    tr("laser.grbl_dynamic_off").format(value=value)
)
                return
        self.txt_console.append(tr("laser.grbl_mode_unknown"))

    def _run_commands_async(self, commands):
        if self.cmd_thread and self.cmd_thread.isRunning():
            return
        self.cmd_thread = CommandThread(self.usb, commands)
        self.cmd_thread.log_signal.connect(self.txt_console.append)
        self.cmd_thread.start()

    def jog_move(self, dx, dy):
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_first")
)
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
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_via_usb")
)
            return
        self._run_commands_async(cmd)

    def send_to_laser(self):
        gcode_text = self.txt_console.toPlainText()
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

        reply = QMessageBox.question(
    self,
    tr("laser.confirm_title"),
    tr("laser.confirm_body"),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    QMessageBox.StandardButton.No
)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_send.setEnabled(False)
        self.progress_bar.setValue(0)
        if getattr(self, "status_poll_thread", None):
            self.status_poll_thread.pause()
        self.streamer = GCodeStreamerThread(self.usb, gcode_text)
        self.streamer.progress.connect(lambda current, total: self.progress_bar.setValue(int((current / total) * 100)))
        self.streamer.log_signal.connect(self.txt_console.append)
        self.streamer.status_updated.connect(self._on_status_updated)
        self.streamer.finished_signal.connect(self.on_stream_finished)
        self.streamer.start()

    def on_stream_finished(self, clean_finish):
        self.btn_send.setEnabled(True)
        if getattr(self, "status_poll_thread", None):
            self.status_poll_thread.resume()
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

    def send_reset(self):
        if self.streamer and self.streamer.isRunning():
            self.streamer.stop()
        self.usb.send_raw_byte(b'\x18')
        self.txt_console.append(tr("laser.reset_log"))

    def send_kill(self):
        if self.streamer and self.streamer.isRunning():
            self.streamer.stop()
        self.usb.send_raw_byte(b'\x18')
        self.txt_console.append(tr("laser.kill_log"))

    def send_manual_cmd(self):
        cmd = self.txt_manual_cmd.text().strip()
        if not cmd:
            return
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("laser.usb_not_connected_title"),
    tr("laser.connect_first")
)
            return
        self.txt_manual_cmd.add_to_history(cmd)
        self._run_commands_async(cmd)
        self.txt_manual_cmd.clear()

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
