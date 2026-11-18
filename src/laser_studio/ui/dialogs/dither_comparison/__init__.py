"""Fenêtre de comparaison des algorithmes de tramage.

Utilisation :

    from laser_studio.ui.dialogs.dither_comparison import DitherComparisonDialog

    dialog = DitherComparisonDialog(self, [("Stucki", tableau), ...])
    dialog.algorithm_chosen.connect(lambda name: self.image_settings.update(algorithm=name))
"""

from laser_studio.ui.dialogs.dither_comparison.dialog import DitherComparisonDialog

__all__ = ["DitherComparisonDialog"]
