"""File d'attente de jobs : plusieurs gravures envoyées au laser l'une après
l'autre, sans reconfigurer ni relancer entre chaque.

La file est sauvegardée sur disque à chaque modification et restaurée au
démarrage (voir save / load), pour ne pas la perdre à la fermeture.
"""

import datetime
import json
import os
from dataclasses import dataclass
from typing import Callable

from PyQt6.QtWidgets import QMessageBox

from laser_studio.core.debug_log import get_logger, log_gcode_summary
from laser_common.files import get_background_writer
from laser_studio.core.paths import get_autosave_dir
from laser_studio.i18n import tr

log = get_logger()

QUEUE_FILENAME = "laser_studio_pro_queue.json"


@dataclass
class Engraver:
    """Ce que la file demande au graveur (voir LaserControlMixin)."""

    # Le port est-il ouvert ?
    is_connected: Callable[[], bool]
    # Dernier état GRBL connu (pour le journal).
    last_state: Callable[[], str]
    # Pas de homing depuis la connexion : avertit ; False si annulé.
    confirm_homed: Callable[[], bool]
    # Lance l'envoi d'un G-Code ; la fonction reçoit fin_propre à la fin.
    start_stream: Callable[[str, Callable[[bool], None]], None]
    # Fin d'un envoi : repère dans le suivi, position, aperçu 2D.
    stream_ended: Callable[[bool], None]
    # Interrogation d'état du graveur, suspendue pendant les envois.
    pause_status_poll: Callable[[], None]
    resume_status_poll: Callable[[], None]
    # Plus aucun job en cours (notification, état des boutons...).
    jobs_finished: Callable[[], None]


class JobQueueController:
    """Liste des jobs, sauvegarde, et enchaînement des envois.

        queue = JobQueueController(
            tab, self, engraver,
            current_gcode=self.txt_console.toPlainText,
            log_to_console=self.txt_console.append,
            sent_log=machine_panel.sent_gcode_log,
        )
        tab.run_requested.connect(queue.run)

    `tab` : l'onglet File d'attente (JobQueueTab). `parent` : fenêtre des
    messages. `engraver` : voir Engraver. `current_gcode()` : G-Code
    affiché dans la console, ajouté par « Ajouter le G-Code actuel ».
    `log_to_console(text)` : écrit dans la console. `sent_log` : suivi du
    G-Code envoyé (SentGcodeLog : clear_lines, append_lines).
    """

    def __init__(self, tab, parent, engraver, current_gcode, log_to_console, sent_log):
        self._tab = tab
        self._sent_log = sent_log
        self._parent = parent
        self._engraver = engraver
        self._current_gcode = current_gcode
        self._log_to_console = log_to_console
        # [{"name": ..., "gcode": ...}], dans l'ordre d'envoi.
        self.jobs = []
        self._running_index = 0

    # -- liste

    def add_current_gcode(self):
        """Ajoute le G-Code de la console à la file, sous un nom horodaté."""
        gcode = self._current_gcode()
        if not gcode.strip():
            QMessageBox.warning(
                self._parent, tr("queue.empty_title"), tr("queue.no_gcode")
            )
            return
        time = datetime.datetime.now().strftime("%H:%M:%S")
        name = self._unique_name(f"Job {len(self.jobs) + 1} — {time}")
        log_gcode_summary(log, f"File : ajout de « {name} »", gcode)
        self.jobs.append({"name": name, "gcode": gcode})
        self._tab.add_job(name)
        self._update_status()
        self.save()

    def _unique_name(self, base_name):
        """Nom unique dans la file : deux jobs ajoutés dans la même seconde
        portaient le même nom, et le réordonnancement (par nom) échouait."""
        existing = {job["name"] for job in self.jobs}
        if base_name not in existing:
            return base_name
        n = 2
        while f"{base_name} ({n})" in existing:
            n += 1
        return f"{base_name} ({n})"

    def remove_selected(self):
        row = self._tab.selected_row()
        if row < 0:
            return
        self._tab.remove_job(row)
        del self.jobs[row]
        self._update_status()
        self.save()

    def clear(self):
        self.jobs = []
        self._tab.set_jobs([])
        self._update_status()
        self.save()

    def on_reordered(self):
        """Après un glisser-déposer dans la liste : la file suit l'ordre
        affiché (jobs réappariés par nom, unique)."""
        by_name = {job["name"]: job for job in self.jobs}
        new_order = [
            by_name[name] for name in self._tab.job_names() if name in by_name
        ]
        if len(new_order) == len(self.jobs):
            self.jobs = new_order
            self.save()

    def _update_status(self):
        n = len(self.jobs)
        if n == 0:
            self._tab.set_status(tr("queue.status_empty"))
        else:
            self._tab.set_status(tr("queue.status_count").format(count=n))

    # -- sauvegarde

    def save(self):
        """Sauvegarde silencieuse : une erreur ici ne doit jamais
        interrompre l'utilisateur (comme la sauvegarde automatique)."""
        try:
            path = os.path.join(get_autosave_dir(), QUEUE_FILENAME)
            writer = get_background_writer()
            error = writer.pop_error(path)
            if error is not None:
                self._log_to_console(
                    tr("queue.save_failed").format(error=error)
                )
            # Copie légère (les textes G-Code sont partagés) : la
            # sérialisation et l'écriture se font dans le thread d'écriture.
            snapshot = [dict(job) for job in self.jobs]
            writer.submit(path, lambda: json.dumps(snapshot))
        except Exception:
            pass

    def load(self):
        """Restaure la file de la session précédente (au démarrage)."""
        path = os.path.join(get_autosave_dir(), QUEUE_FILENAME)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, list):
                return
            self.jobs = []
            for job in loaded:
                if isinstance(job, dict) and "name" in job and "gcode" in job:
                    # Files sauvegardées avant correction : noms dédoublonnés.
                    job["name"] = self._unique_name(job["name"])
                    self.jobs.append(job)
        except Exception:
            self.jobs = []
            return
        self._tab.set_jobs([job["name"] for job in self.jobs])
        self._update_status()

    # -- envoi

    def run(self):
        """Envoie les jobs l'un après l'autre : dès qu'un job se termine
        proprement, le suivant démarre. Une erreur ou une interruption
        arrête la file (pas d'envoi en aveugle du reste)."""
        engraver = self._engraver
        log.info(
            "File : clic sur « Lancer la file » (%d job(s), port ouvert=%s)",
            len(self.jobs),
            engraver.is_connected(),
        )
        if not self.jobs:
            log.warning("File : vide, abandon")
            QMessageBox.warning(
                self._parent,
                tr("queue.empty_title"),
                tr("queue.status_empty"),
            )
            return
        if not engraver.is_connected():
            log.warning("File : graveur non connecté, abandon")
            QMessageBox.warning(
                self._parent, tr("queue.usb_error"), tr("queue.usb_connect")
            )
            return
        if not engraver.confirm_homed():
            log.info("File : annulée à l'avertissement « pas de homing »")
            return
        reply = QMessageBox.question(
            self._parent,
            tr("queue.confirm_title"),
            tr("queue.confirm_body").format(count=len(self.jobs)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            log.info("File : annulée à la confirmation")
            return
        log.info(
            "File : démarrage, dernier état GRBL connu %s",
            engraver.last_state(),
        )
        self._running_index = 0
        self._sent_log.clear_lines()
        self._tab.set_run_enabled(False)
        engraver.pause_status_poll()
        self._run_next()

    def _run_next(self):
        total = len(self.jobs)
        if self._running_index >= total:
            log.info("File : terminée, %d job(s) envoyés", total)
            self._log_to_console(tr("queue.finished_log"))
            self._engraver.resume_status_poll()
            self._engraver.jobs_finished()
            QMessageBox.information(
                self._parent, tr("queue.done_title"), tr("queue.done_body")
            )
            self._tab.set_run_enabled(True)
            self.clear()
            return
        job = self.jobs[self._running_index]
        index = self._running_index + 1
        self._tab.select_job(self._running_index)
        log_gcode_summary(
            log, f"File : job {index}/{total} « {job['name']} »", job["gcode"]
        )
        self._log_to_console(
            tr("queue.job_log").format(
                name=job["name"], index=index, total=total
            )
        )
        self._tab.set_status(
            tr("queue.in_progress").format(
                name=job["name"], index=index, total=total
            )
        )
        self._sent_log.append_lines(
            [
                tr("queue.sent_log_job").format(
                    index=index, total=total, name=job["name"]
                )
            ]
        )
        self._engraver.start_stream(job["gcode"], self._on_job_finished)

    def _on_job_finished(self, clean_finish):
        log.info(
            "File : job %d terminé, fin propre=%s",
            self._running_index + 1,
            clean_finish,
        )
        self._engraver.stream_ended(clean_finish)
        if not clean_finish:
            self._tab.set_run_enabled(True)
            self._engraver.resume_status_poll()
            self._engraver.jobs_finished()
            QMessageBox.warning(
                self._parent,
                tr("queue.stopped_title"),
                tr("queue.stopped_body"),
            )
            return
        self._running_index += 1
        self._run_next()
