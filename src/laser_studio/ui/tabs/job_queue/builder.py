"""Onglet « File d'attente » relié à la file (JobQueueController), qui envoie ses jobs par le
contrôleur du graveur.

    tab, job_queue = build_job_queue_tab(connection, engraver, dialogs, parent, current_gcode=..., ...)
"""
from laser_studio.controllers.job_queue import Engraver, JobQueueController
from laser_studio.models import machine_state as ms
from laser_studio.ui.tabs.job_queue.tab import JobQueueTab


def build_job_queue_tab(connection, engraver, dialogs, parent, *, current_gcode, log, sent_log):
    """`connection` (MachineConnection) et `engraver` (EngraverController) : ce que la file demande au
    graveur ; `current_gcode()` : G-Code de la console ; `log(texte)` : messages ; `sent_log` : suivi
    du G-Code envoyé. Renvoie (JobQueueTab, JobQueueController)."""
    tab = JobQueueTab()
    machine = Engraver(
        is_connected=connection.is_connected,
        last_state=lambda: connection.last_state,
        confirm_homed=engraver.confirm_homed,
        start_stream=engraver.start_stream,
        stream_ended=engraver.end_stream,
        pause_status_poll=connection.pause_status_poll,
        resume_status_poll=connection.resume_status_poll,
        jobs_finished=engraver.notify_job_done,
        confirm_gcode=engraver.confirm_safe_gcode,
        may_send=lambda: engraver.allowed(ms.SEND_JOB, "queue.usb_connect"),
    )
    job_queue = JobQueueController(tab, parent, machine, current_gcode=current_gcode, log_to_console=log,
                                   sent_log=sent_log, dialogs=dialogs)
    tab.add_current_requested.connect(job_queue.add_current_gcode)
    tab.remove_selected_requested.connect(job_queue.remove_selected)
    tab.clear_requested.connect(job_queue.clear)
    tab.run_requested.connect(job_queue.run)
    tab.reordered.connect(job_queue.on_reordered)
    return tab, job_queue
