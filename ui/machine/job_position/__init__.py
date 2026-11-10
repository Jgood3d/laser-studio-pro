"""Cadre « Position du job sur le plateau » : origine du repère.

Utilisation :

    from ui.machine.job_position import JobPositionBox

    box = JobPositionBox()
    origin = box.origin_combo.currentIndex()
"""

from ui.machine.job_position.box import JobPositionBox

__all__ = ["JobPositionBox"]
