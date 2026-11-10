"""Matrice de test à partir d'une image : source de l'image et zone gravée.

La page (ui/settings/test_matrix/) affiche les réglages ; ce mixin charge
l'image choisie, reprend celle de « Graver une image » et prépare la zone
d'image gravée dans chaque case.
"""

from PIL import Image
from PyQt6.QtWidgets import QFileDialog, QMessageBox

import matrix_image
from i18n import tr


class MatrixImageMixin:
    def _mat_choose_image(self):
        """Choix d'un fichier image pour le test, à sa taille réelle si sa
        résolution est plausible."""
        page = self.tab_matrix
        path, _ = QFileDialog.getOpenFileName(
            page, tr("ui.mat_image_file_title"), "", tr("ui.mat_image_file_filter"))
        if not path:
            return
        try:
            with Image.open(path) as img:
                img.load()
                dpi = img.info.get("dpi")
                gray = matrix_image.to_gray(img)
        except Exception as e:
            QMessageBox.warning(page, tr("ui.mat_image_group"),
                                tr("ui.mat_image_open_error").format(error=e))
            return
        # Taille réelle d'après la résolution de l'image si elle est plausible, sinon on garde
        # la largeur saisie.
        width_mm = None
        try:
            dpi_x = float(dpi[0] if isinstance(dpi, (tuple, list)) else dpi)
            if 20.0 <= dpi_x <= 2400.0:
                width_mm = gray.width / dpi_x * 25.4
        except (TypeError, ValueError, IndexError):
            pass
        page.set_source_image(gray, path.replace("\\", "/").rsplit("/", 1)[-1], width_mm)
        page.set_image_test_checked(True)

    def _mat_use_loaded_image(self):
        """Reprend l'image de « Graver une image », à la largeur qui lui y est donnée."""
        raw = getattr(self, "raw_image", None)
        if raw is None:
            QMessageBox.information(self.tab_matrix, tr("ui.mat_image_group"),
                                    tr("ui.mat_image_loaded_none"))
            return
        self.tab_matrix.set_source_image(matrix_image.to_gray(raw), tr("ui.mat_image_use_loaded"),
                                         self.spin_w.value() if hasattr(self, "spin_w") else None)

    def _on_mat_image_test_toggled(self, checked):
        """Test à partir d'une image coché sans image choisie : reprend celle
        de « Graver une image », s'il y en a une."""
        if checked and self.tab_matrix.source_image is None and getattr(self, "raw_image", None) is not None:
            self._mat_use_loaded_image()

    def build_matrix_image_tile(self, lines_mm):
        """Zone d'image à graver dans chaque case : recadrée puis traitée comme une gravure
        d'image (luminosité, contraste, gamma, netteté, inversion et tramage de « Graver une
        image »), à `lines_mm` lignes/mm. Renvoie {arr, w_mm, h_mm, grayscale} ou None (message
        affiché). Calcul court (quelques centaines de pixels de côté) : fait ici, sans thread."""
        from workers import ImageProcessingWorker      # import tardif : workers dépend de Qt/numba
        page = self.tab_matrix
        if page.source_image is None and getattr(self, "raw_image", None) is not None:
            self._mat_use_loaded_image()
        src = page.source_image
        if src is None:
            QMessageBox.warning(page, tr("ui.mat_image_missing_title"),
                                tr("ui.mat_image_missing_body"))
            return None
        try:
            box, w_mm, h_mm = matrix_image.crop_box_px(src.width, src.height, *page.tile_settings())
        except ValueError as e:
            QMessageBox.warning(page, tr("ui.mat_image_group"), str(e))
            return None
        if int(w_mm * lines_mm) < 1 or int(h_mm * lines_mm) < 1:
            QMessageBox.warning(page, tr("ui.mat_image_group"), tr("ui.mat_tile_too_small"))
            return None
        process_params = {
            'w_mm': w_mm, 'h_mm': h_mm, 'lmm': lines_mm,
            'mirror_h': False, 'mirror_v': False,
            'bright': self.slider_bright.value(),
            'contrast': self.slider_contrast.value(),
            'gamma': self.slider_gamma.value(),
            'sharp': self.slider_sharp.value(),
            'invert': self.chk_invert.isChecked(),
            'algo': self.combo_algo.currentText(),
        }
        result = {}
        worker = ImageProcessingWorker(src.crop(box), process_params)
        worker.finished.connect(lambda arr, _img: result.update(arr=arr))
        worker.run()        # appel direct (et non start()) : synchrone, résultat prêt au retour
        if "arr" not in result:
            QMessageBox.warning(page, tr("ui.mat_image_group"), tr("ui.mat_tile_too_small"))
            return None
        return {'arr': result["arr"], 'w_mm': w_mm, 'h_mm': h_mm,
                'grayscale': process_params['algo'] == "Niveaux de Gris"}
