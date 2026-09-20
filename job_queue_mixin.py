"""File d'attente de jobs : empiler plusieurs gravures à envoyer au laser
l'une après l'autre, sans reconfigurer/relancer manuellement entre chaque."""
import datetime
from PyQt6.QtWidgets import QMessageBox, QListWidgetItem
from workers import GCodeStreamerThread
from i18n import tr


class JobQueueMixin:
    def add_current_gcode_to_queue(self):
        """Ajoute le G-Code actuellement affiché dans la console à la file
        d'attente, sous un nom horodaté."""
        gcode_text = self.txt_console.toPlainText()
        if not gcode_text.strip():
            QMessageBox.warning(
    self,
    tr("queue.empty_title"),
    tr("queue.no_gcode")
)
            return
        if not hasattr(self, "job_queue"):
            self.job_queue = []
        name = f"Job {len(self.job_queue) + 1} — {datetime.datetime.now().strftime('%H:%M:%S')}"
        self.job_queue.append({"name": name, "gcode": gcode_text})
        self.list_job_queue.addItem(QListWidgetItem(name))
        self._update_queue_status()

    def remove_selected_from_queue(self):
        if not hasattr(self, "job_queue"):
            return
        row = self.list_job_queue.currentRow()
        if row < 0:
            return
        self.list_job_queue.takeItem(row)
        del self.job_queue[row]
        self._update_queue_status()

    def clear_job_queue(self):
        self.job_queue = []
        self.list_job_queue.clear()
        self._update_queue_status()

    def _update_queue_status(self):
        n = len(getattr(self, "job_queue", []))
        if n == 0:
            self.lbl_queue_status.setText(tr("queue.status_empty"))
        else:
            self.lbl_queue_status.setText(tr("queue.status_count").format(count=n))

    def run_job_queue(self):
        """Lance l'envoi des jobs de la file les uns après les autres : dès
        qu'un job se termine proprement, le suivant démarre automatiquement.
        Une erreur/interruption sur un job arrête la file (pas d'envoi en
        aveugle du reste si quelque chose s'est mal passé)."""
        if not getattr(self, "job_queue", None):
            QMessageBox.warning(
    self,
    tr("queue.empty_title"),
    tr("queue.status_empty")
)
            return
        if not self.usb.is_connected():
            QMessageBox.warning(
    self,
    tr("queue.usb_error"),
    tr("queue.usb_connect")
)
            return

        reply = QMessageBox.question(
    self,
    tr("queue.confirm_title"),
    tr("queue.confirm_body").format(count=len(self.job_queue)),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    QMessageBox.StandardButton.No
)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._queue_running_index = 0
        self.btn_run_queue.setEnabled(False)
        if getattr(self, "status_poll_thread", None):
            self.status_poll_thread.pause()
        self._run_next_queued_job()

    def _run_next_queued_job(self):
        if self._queue_running_index >= len(self.job_queue):
            self.txt_console.append(">>> File d'attente terminée.")
            if getattr(self, "status_poll_thread", None):
                self.status_poll_thread.resume()
            QMessageBox.information(
    self,
    tr("queue.done_title"),
    tr("queue.done_body")
)
            self.btn_run_queue.setEnabled(True)
            self.clear_job_queue()
            return

        job = self.job_queue[self._queue_running_index]
        self.list_job_queue.setCurrentRow(self._queue_running_index)

        self.txt_console.append(
            tr("queue.job_log").format(
                name=job["name"],
                index=self._queue_running_index + 1,
                total=len(self.job_queue)
            )
        )

        self.lbl_queue_status.setText(
            tr("queue.in_progress").format(
                name=job["name"],
                index=self._queue_running_index + 1,
                total=len(self.job_queue)
            )
        )

        self.progress_bar.setValue(0)
        self.streamer = GCodeStreamerThread(self.usb, job["gcode"])
        self.streamer.progress.connect(lambda current, total: self.progress_bar.setValue(int((current / total) * 100)))
        self.streamer.log_signal.connect(self.txt_console.append)
        self.streamer.status_updated.connect(self._on_status_updated)
        self.streamer.finished_signal.connect(self._on_queued_job_finished)
        self.streamer.start()

    def _on_queued_job_finished(self, clean_finish):
        if not clean_finish:
            self.btn_run_queue.setEnabled(True)
            if getattr(self, "status_poll_thread", None):
                self.status_poll_thread.resume()
            QMessageBox.warning(
                self, tr("queue.stopped_title"),
                tr("queue.stopped_body")
            )
            return
        self._queue_running_index += 1
        self._run_next_queued_job()
