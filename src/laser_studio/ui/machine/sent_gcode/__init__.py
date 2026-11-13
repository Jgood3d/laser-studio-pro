"""Suivi du G-Code envoyé au graveur, dans le panneau machine.

Utilisation :

    from laser_studio.ui.machine.sent_gcode import SentGcodeLog

    log = SentGcodeLog()
    log.append_lines(["G21", "G1 X10"])
    log.mark_end(clean_finish=True)
"""

from laser_studio.ui.machine.sent_gcode.log import SentGcodeLog

__all__ = ["SentGcodeLog"]
