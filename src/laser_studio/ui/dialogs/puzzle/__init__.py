"""Fenêtre du générateur de puzzle.

Utilisation :

    from laser_studio.ui.dialogs.puzzle import PuzzleGeneratorDialog

    dialog = PuzzleGeneratorDialog(self, layers, bed_w, bed_h, initial)
"""

from laser_studio.ui.dialogs.puzzle.dialog import PuzzleGeneratorDialog

__all__ = ["PuzzleGeneratorDialog"]
