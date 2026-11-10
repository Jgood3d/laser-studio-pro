"""Matrice de test à partir d'une image : image source et zone gravée."""

from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from i18n import tr
from image import matrix as matrix_image

# Résolutions d'image plausibles, en DPI : en dehors, la taille réelle de
# l'image n'est pas déduite de sa résolution.
PLAUSIBLE_DPI = (20.0, 2400.0)


class MatrixImageController:
    """Charge l'image du test (fichier, ou image de « Graver une image ») et
    prépare la zone d'image gravée dans chaque case.

        matrix_image = MatrixImageController(
            page, loaded_image=..., image_settings=panel.processing_settings
        )
        page.choose_image_requested.connect(matrix_image.choose_image)

    `page` : la page « Matrice de test » (TestMatrixPage).
    `loaded_image()` : (image PIL, largeur en mm) de « Graver une image »,
    ou None si aucune n'est chargée. `image_settings()` : réglages du
    tramage (voir ImageSettingsPanel.processing_settings).
    """

    def __init__(self, page, loaded_image, image_settings):
        self._page = page
        self._loaded_image = loaded_image
        self._image_settings = image_settings

    def choose_image(self):
        """Choix d'un fichier image pour le test, à sa taille réelle si sa
        résolution est plausible."""
        page = self._page
        path, _ = QFileDialog.getOpenFileName(
            page,
            tr("ui.mat_image_file_title"),
            "",
            tr("ui.mat_image_file_filter"),
        )
        if not path:
            return
        try:
            with Image.open(path) as img:
                img.load()
                dpi = img.info.get("dpi")
                gray = matrix_image.to_gray(img)
        except Exception as e:
            QMessageBox.warning(
                page,
                tr("ui.mat_image_group"),
                tr("ui.mat_image_open_error").format(error=e),
            )
            return
        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        page.set_source_image(gray, name, self._real_width_mm(gray, dpi))
        page.set_image_test_checked(True)

    @staticmethod
    def _real_width_mm(image, dpi):
        """Largeur réelle d'après la résolution de l'image si elle est
        plausible, sinon None (la largeur saisie est gardée)."""
        try:
            dpi_x = float(dpi[0] if isinstance(dpi, (tuple, list)) else dpi)
        except (TypeError, ValueError, IndexError):
            return None
        low, high = PLAUSIBLE_DPI
        if low <= dpi_x <= high:
            return image.width / dpi_x * 25.4
        return None

    def use_loaded_image(self):
        """Reprend l'image de « Graver une image », à la largeur qui lui y
        est donnée."""
        loaded = self._loaded_image()
        if loaded is None:
            QMessageBox.information(
                self._page,
                tr("ui.mat_image_group"),
                tr("ui.mat_image_loaded_none"),
            )
            return
        image, width_mm = loaded
        self._page.set_source_image(
            matrix_image.to_gray(image),
            tr("ui.mat_image_use_loaded"),
            width_mm,
        )

    def on_image_test_toggled(self, checked):
        """Test à partir d'une image coché sans image choisie : reprend
        celle de « Graver une image », s'il y en a une."""
        if (
            checked
            and self._page.source_image is None
            and self._loaded_image() is not None
        ):
            self.use_loaded_image()

    def build_tile(self, lines_mm):
        """Zone d'image à graver dans chaque case.

        Recadrée puis traitée comme une gravure d'image (réglages de
        « Graver une image »), à `lines_mm` lignes/mm. Renvoie {arr, w_mm,
        h_mm, grayscale}, ou None (message affiché). Calcul court
        (quelques centaines de pixels de côté) : fait ici, sans thread.
        """
        # Import tardif : workers dépend de Qt et de numba.
        from workers import ImageProcessingWorker

        page = self._page
        if page.source_image is None and self._loaded_image() is not None:
            self.use_loaded_image()
        src = page.source_image
        if src is None:
            QMessageBox.warning(
                page,
                tr("ui.mat_image_missing_title"),
                tr("ui.mat_image_missing_body"),
            )
            return None
        try:
            box, w_mm, h_mm = matrix_image.crop_box_px(
                src.width, src.height, *page.tile_settings()
            )
        except ValueError as e:
            QMessageBox.warning(page, tr("ui.mat_image_group"), str(e))
            return None
        if int(w_mm * lines_mm) < 1 or int(h_mm * lines_mm) < 1:
            QMessageBox.warning(
                page, tr("ui.mat_image_group"), tr("ui.mat_tile_too_small")
            )
            return None
        params = {
            "w_mm": w_mm,
            "h_mm": h_mm,
            "lmm": lines_mm,
            "mirror_h": False,
            "mirror_v": False,
            **self._image_settings(),
        }
        result = {}
        worker = ImageProcessingWorker(src.crop(box), params)
        worker.finished.connect(lambda arr, _img: result.update(arr=arr))
        # Appel direct (et non start()) : synchrone, résultat prêt au retour.
        worker.run()
        if "arr" not in result:
            QMessageBox.warning(
                page, tr("ui.mat_image_group"), tr("ui.mat_tile_too_small")
            )
            return None
        return {
            "arr": result["arr"],
            "w_mm": w_mm,
            "h_mm": h_mm,
            "grayscale": params["algo"] == "Niveaux de Gris",
        }
