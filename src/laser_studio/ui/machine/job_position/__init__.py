"""Cadre « Position du job sur le plateau » : origine du repère.

Utilisation :

    from laser_studio.ui.machine.job_position import JobPositionBox

    box = JobPositionBox()
    origin = box.origin_combo.currentIndex()
"""

from laser_studio.ui.machine.job_position.box import JobPositionBox

__all__ = ["JobPositionBox"]
