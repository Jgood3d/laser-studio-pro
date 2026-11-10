"""Page « Matrice de test » : réglages de la grille de calibrage.

Utilisation :

    from ui.settings.test_matrix import TestMatrixPage

    page = TestMatrixPage(lines_mm=10.0)
    page.generate_requested.connect(self.generate_test_matrix)
    params = page.matrix_params()
"""

from ui.settings.test_matrix.page import TestMatrixPage

__all__ = ["TestMatrixPage"]
