"""Cadre « Position du job sur le plateau » : origine du repère et décalage, liés au modèle JobPlacement.

Utilisation :

    from laser_studio.ui.machine.job_position import JobPositionBox

    box = JobPositionBox()
    box.bind_placement(placement)
"""

from laser_studio.ui.machine.job_position.box import JobPositionBox

__all__ = ["JobPositionBox"]
