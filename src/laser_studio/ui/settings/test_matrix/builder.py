"""Page « Matrice de test » et sa logique de test à partir d'une image, reliées.

    page, matrix_image = build_test_matrix_page(lines_mm, generate=..., loaded_image=..., image_settings=...)
"""
from laser_studio.controllers.matrix_image import MatrixImageController
from laser_studio.ui.settings.test_matrix.page import TestMatrixPage
from laser_studio.ui.user_dialogs import UserDialogs


def build_test_matrix_page(lines_mm, *, generate, loaded_image, image_settings):
    """Page à `lines_mm` lignes/mm ; `generate()` : bouton « Générer » ; test à partir d'une image :
    `loaded_image()` -> (image, largeur mm) ou None, `image_settings()` : réglages du tramage.
    Renvoie (page, MatrixImageController)."""
    page = TestMatrixPage(lines_mm)
    page.generate_requested.connect(generate)
    # Test à partir d'une image : fichier choisi, ou image de « Graver une
    # image » avec ses réglages de tramage.
    matrix_image = MatrixImageController(
        page,
        loaded_image=loaded_image,
        image_settings=image_settings,
        dialogs=UserDialogs(page),          # centrées sur la fenêtre de la matrice
    )
    page.choose_image_requested.connect(matrix_image.choose_image)
    page.use_loaded_image_requested.connect(matrix_image.use_loaded_image)
    page.image_test_toggled.connect(matrix_image.on_image_test_toggled)
    return page, matrix_image
