"""Panneau machine (sous les onglets) relié au contrôleur du graveur.

    panel = build_machine_panel(engraver, connection, machine.max_speed,
                                max_speed_changed=page.max_speed_changed, help_parent=window)
"""
from PyQt6.QtGui import QStandardItemModel

from laser_studio.ui.machine.connection import port_help_dialog
from laser_studio.ui.machine.panel import MachinePanel


def build_machine_panel(engraver, connection, max_speed, *, max_speed_changed, help_parent):
    """Les sous-panneaux émettent les demandes de l'utilisateur, transmises à `engraver`
    (EngraverController). `max_speed` borne le curseur de vitesse du pilotage, puis suit
    `max_speed_changed` (Paramètres du graveur). Boutons actifs d'après l'état de `connection`
    (MachineConnection.can, puis JobDisplay.update_machine_state)."""
    panel = MachinePanel(QStandardItemModel(help_parent), max_speed)
    ports = panel.connection_panel
    ports.refresh_requested.connect(engraver.refresh_ports)
    ports.help_requested.connect(lambda: port_help_dialog(help_parent).exec())
    ports.connect_requested.connect(engraver.toggle_connection)
    ports.unlock_requested.connect(engraver.unlock)
    ports.command_submitted.connect(engraver.send_console_command)
    jog = panel.jog_panel
    jog.jog_requested.connect(engraver.jog)
    jog.home_requested.connect(engraver.home)
    jog.pause_requested.connect(engraver.pause)
    jog.resume_requested.connect(engraver.resume)
    jog.reset_requested.connect(engraver.reset)
    jog.emergency_stop_requested.connect(engraver.emergency_stop)
    jog.send_job_requested.connect(lambda: engraver.send_job())
    max_speed_changed.connect(jog.set_max_speed)
    job_actions = panel.job_actions_panel
    job_actions.frame_requested.connect(engraver.frame)
    job_actions.set_work_zero_requested.connect(engraver.set_work_zero)
    job_actions.go_to_work_zero_requested.connect(engraver.go_to_work_zero)
    job_actions.repeat_job_requested.connect(engraver.repeat_last_job)
    # Boutons actifs d'après l'état du graveur (puis JobDisplay.update_machine_state)
    panel.set_machine_state(connection.is_connected(), connection.can)
    return panel
