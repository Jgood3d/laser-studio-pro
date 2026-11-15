"""Panneau de connexion au graveur : port, actualisation, connexion.

Utilisation :

    from laser_studio.ui.machine.connection import ConnectionPanel

    panel = ConnectionPanel(ports_model)
    panel.connect_requested.connect(self.toggle_connection)
    panel.set_connected(True)
"""

from laser_studio.ui.machine.connection.panel import ConnectionPanel

__all__ = ["ConnectionPanel"]
