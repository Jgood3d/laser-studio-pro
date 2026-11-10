"""Fenêtre de comparaison des algorithmes de tramage.

Utilisation :

    from ui.dialogs.dither_comparison import DitherComparisonDialog

    dialog = DitherComparisonDialog(self, [("Stucki", tableau), ...])
    dialog.algorithm_chosen.connect(self.combo_algo.setCurrentText)
"""

from ui.dialogs.dither_comparison.dialog import DitherComparisonDialog

__all__ = ["DitherComparisonDialog"]
