"""Console directe : envoi d'une commande GRBL tapée à la main.

Utilisation :

    from laser_studio.ui.machine.console import DirectConsolePanel

    panel = DirectConsolePanel()
    panel.command_submitted.connect(self.send_console_command)
"""

from laser_studio.ui.machine.console.panel import DirectConsolePanel

__all__ = ["DirectConsolePanel"]
