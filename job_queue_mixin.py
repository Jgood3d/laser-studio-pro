"""File d'attente de jobs : empiler plusieurs gravures à envoyer au laser
l'une après l'autre, sans reconfigurer/relancer manuellement entre chaque.
La file est sauvegardée sur disque à chaque modification et restaurée au
démarrage (voir _save_job_queue / _load_job_queue), pour ne pas la perdre
à la fermeture de l'application."""
import datetime
import json
import os
from PyQt6.QtWidgets import QMessageBox, QListWidgetItem
from workers import GCodeStreamerThread
from app_utils import get_autosave_dir
from i18n import tr

QUEUE_FILENAME = "laser_studio_pro_queue.json"


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
        self._save_job_queue()

    def remove_selected_from_queue(self):
        if not hasattr(self, "job_queue"):
            return
        row = self.list_job_queue.currentRow()
        if row < 0:
            return
        self.list_job_queue.takeItem(row)
        del self.job_queue[row]
        self._update_queue_status()
        self._save_job_queue()

    def clear_job_queue(self):
        self.job_queue = []
        self.list_job_queue.clear()
        self._update_queue_status()
        self._save_job_queue()

    def _on_queue_reordered(self, *args):
        """Appelé après un glisser-déposer de réordonnancement dans la
        liste (voir setDragDropMode InternalMove dans ui_setup_mixin.py) :
        reconstruit job_queue pour qu'il corresponde au nouvel ordre
        visuel — les jobs sont réappariés par nom, unique en pratique
        puisqu'horodaté à la création."""
        if not hasattr(self, "job_queue"):
            return
        by_name = {job["name"]: job for job in self.job_queue}
        new_order = []
        for i in range(self.list_job_queue.count()):
            name = self.list_job_queue.item(i).text()
            if name in by_name:
                new_order.append(by_name[name])
        if len(new_order) == len(self.job_queue):
            self.job_queue = new_order
            self._save_job_queue()

    def _save_job_queue(self):
        """Sauvegarde silencieuse de la file — une erreur ici ne doit
        jamais interrompre l'utilisateur (même principe que l'autosave de
        projet, voir project_io_mixin.py)."""
        try:
            path = os.path.join(get_autosave_dir(), QUEUE_FILENAME)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(getattr(self, "job_queue", []), f)
        except Exception:
            pass

    def load_job_queue_from_disk(self):
        """Restaure la file d'attente sauvegardée lors de la précédente
        session — appelé une fois au démarrage (voir main_window.py)."""
        path = os.path.join(get_autosave_dir(), QUEUE_FILENAME)
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if not isinstance(loaded, list):
                return
            self.job_queue = [
                job for job in loaded
                if isinstance(job, dict) and "name" in job and "gcode" in job
            ]
        except Exception:
            self.job_queue = []
            return
        self.list_job_queue.clear()
        for job in self.job_queue:
            self.list_job_queue.addItem(QListWidgetItem(job["name"]))
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
            if hasattr(self, "_notify_job_finished"):
                self._notify_job_finished()
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
            if hasattr(self, "_notify_job_finished"):
                self._notify_job_finished()
            QMessageBox.warning(
                self, tr("queue.stopped_title"),
                tr("queue.stopped_body")
            )
            return
        self._queue_running_index += 1
        self._run_next_queued_job()
