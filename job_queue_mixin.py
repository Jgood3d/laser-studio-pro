"""File d'attente de jobs : empiler plusieurs gravures à envoyer au laser
l'une après l'autre, sans reconfigurer/relancer manuellement entre chaque."""
import datetime
from PyQt6.QtWidgets import QMessageBox, QListWidgetItem
from workers import GCodeStreamerThread


class JobQueueMixin:
    def add_current_gcode_to_queue(self):
        """Ajoute le G-Code actuellement affiché dans la console à la file
        d'attente, sous un nom horodaté."""
        gcode_text = self.txt_console.toPlainText()
        if not gcode_text.strip():
            QMessageBox.warning(self, "File d'attente", "Aucun G-Code à ajouter (génère d'abord un job).")
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
            self.lbl_queue_status.setText("File vide.")
        else:
            self.lbl_queue_status.setText(f"{n} job(s) en file.")

    def run_job_queue(self):
        """Lance l'envoi des jobs de la file les uns après les autres : dès
        qu'un job se termine proprement, le suivant démarre automatiquement.
        Une erreur/interruption sur un job arrête la file (pas d'envoi en
        aveugle du reste si quelque chose s'est mal passé)."""
        if not getattr(self, "job_queue", None):
            QMessageBox.warning(self, "File d'attente", "La file est vide.")
            return
        if not self.usb.is_connected():
            QMessageBox.warning(self, "Erreur USB", "Veuillez connecter le laser en USB.")
            return

        reply = QMessageBox.question(
            self, "Lancer la file d'attente",
            f"{len(self.job_queue)} job(s) vont être envoyés l'un après l'autre.\n\n"
            "Vérifie que :\n- la zone de travail est dégagée entre chaque pièce,\n"
            "- le capot/protection est en place,\n- tu portes une protection oculaire adaptée.\n\n"
            "Lancer la file maintenant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._queue_running_index = 0
        self.btn_run_queue.setEnabled(False)
        self._run_next_queued_job()

    def _run_next_queued_job(self):
        if self._queue_running_index >= len(self.job_queue):
            self.txt_console.append(">>> File d'attente terminée.")
            QMessageBox.information(self, "File d'attente terminée", "Tous les jobs de la file ont été envoyés.")
            self.btn_run_queue.setEnabled(True)
            self.clear_job_queue()
            return

        job = self.job_queue[self._queue_running_index]
        self.list_job_queue.setCurrentRow(self._queue_running_index)
        self.txt_console.append(f">>> File d'attente : envoi de « {job['name']} » "
                                 f"({self._queue_running_index + 1}/{len(self.job_queue)})")
        self.lbl_queue_status.setText(
            f"Envoi en cours : {job['name']} ({self._queue_running_index + 1}/{len(self.job_queue)})"
        )

        self.progress_bar.setValue(0)
        self.streamer = GCodeStreamerThread(self.usb, job["gcode"])
        self.streamer.progress.connect(lambda current, total: self.progress_bar.setValue(int((current / total) * 100)))
        self.streamer.log_signal.connect(self.txt_console.append)
        self.streamer.finished_signal.connect(self._on_queued_job_finished)
        self.streamer.start()

    def _on_queued_job_finished(self, clean_finish):
        if not clean_finish:
            self.btn_run_queue.setEnabled(True)
            QMessageBox.warning(
                self, "File d'attente interrompue",
                "Un job de la file a été interrompu (erreur GRBL, alarme, perte de "
                "connexion ou arrêt manuel). La file est arrêtée — consulte la "
                "console avant de relancer."
            )
            return
        self._queue_running_index += 1
        self._run_next_queued_job()
