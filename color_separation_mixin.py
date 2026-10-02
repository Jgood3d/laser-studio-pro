"""Séparation couleur pour gravure sur verre : calque noir (tonalité) + calque couleur (impression).
Intégration avec Image & Filtres (L/C/G/Tramage) et aperçu en temps réel.
Export PNG tonalité + PNG couleur."""

import numpy as np
from PIL import Image, ImageEnhance
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from i18n import tr


class ColorSeparationMixin:
    """Mixin pour séparation couleur (tonalité noir + couleur)."""

    def compute_color_separation(self, source_img, params):
        """
        Sépare une image en deux calques :
        - Tonalité (noir) = max(R,G,B) avec L/C/Gamma appliqué
        - Couleur = image teintée (pour impression sur transparent)

        Args:
            source_img: PIL Image (mode L ou RGB)
            params: dict avec 'bright', 'contrast', 'gamma', 'invert', 'algo'

        Returns:
            (tonality_pil, color_pil) → deux PIL Images en mode L (tonalité) ou RGB (couleur)
        """
        if source_img is None:
            return None, None

        # Garantir RGB pour traiter les couleurs
        if source_img.mode != "RGB":
            img_rgb = source_img.convert("RGB")
        else:
            img_rgb = source_img.copy()

        arr = np.asarray(img_rgb, dtype=np.float32) / 255.0

        # --- TONALITÉ (noir) = max(R,G,B) → niveaux de gris
        # Représente la "profondeur" de la gravure laser
        tonality = arr.max(axis=2)

        # Appliquer luminosité
        bright = params.get("bright", 0)
        tonality = tonality + (bright / 100.0)

        # Appliquer contraste
        contrast = params.get("contrast", 0)
        tonality = (tonality - 0.5) * (1.0 + contrast / 100.0) + 0.5

        # Appliquer gamma
        gamma = params.get("gamma", 100) / 100.0
        if gamma != 1.0:
            tonality = tonality ** (1.0 / gamma)

        # Inverser si demandé
        if params.get("invert", False):
            tonality = 1.0 - tonality

        tonality = np.clip(tonality, 0.0, 1.0)

        # --- COULEUR = Saturation (S de HSV) conservée, mais tonalité = 1.0
        # Permet d'imprimer une "couleur pure" qui sera modulée par la gravure dessous
        # Calcul HSV simplifié : H et S conservés, V = 1.0
        color_hsv = self._rgb_to_hsv(arr)
        color_hsv[:, :, 2] = 1.0  # V = 1.0 → couleur saturée et claire
        color_rgb = self._hsv_to_rgb(color_hsv)
        color_rgb = np.clip(color_rgb, 0.0, 1.0)

        # Convertir en PIL
        tonality_uint8 = (tonality * 255).astype(np.uint8)
        tonality_pil = Image.fromarray(tonality_uint8, mode="L")

        color_uint8 = (color_rgb * 255).astype(np.uint8)
        color_pil = Image.fromarray(color_uint8, mode="RGB")

        return tonality_pil, color_pil

    @staticmethod
    def _rgb_to_hsv(rgb):
        """Convertit RGB (0-1) en HSV (0-1, 0-1, 0-1)."""
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        v = maxc
        delta = maxc - minc

        s = np.zeros_like(v)
        mask = maxc != 0
        s[mask] = delta[mask] / maxc[mask]

        h = np.zeros_like(v)
        mask_delta = delta != 0

        mask_r = mask_delta & (maxc == r)
        h[mask_r] = (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6) / 6.0

        mask_g = mask_delta & (maxc == g)
        h[mask_g] = (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2) / 6.0

        mask_b = mask_delta & (maxc == b)
        h[mask_b] = (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4) / 6.0

        return np.stack([h, s, v], axis=2)

    @staticmethod
    def _hsv_to_rgb(hsv):
        """Convertit HSV (0-1, 0-1, 0-1) en RGB (0-1)."""
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        h_i = (h * 6).astype(int) % 6
        f = (h * 6) - h_i

        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)

        r = np.zeros_like(v)
        g = np.zeros_like(v)
        b = np.zeros_like(v)

        mask0 = h_i == 0
        r[mask0], g[mask0], b[mask0] = v[mask0], t[mask0], p[mask0]

        mask1 = h_i == 1
        r[mask1], g[mask1], b[mask1] = q[mask1], v[mask1], p[mask1]

        mask2 = h_i == 2
        r[mask2], g[mask2], b[mask2] = p[mask2], v[mask2], t[mask2]

        mask3 = h_i == 3
        r[mask3], g[mask3], b[mask3] = p[mask3], q[mask3], v[mask3]

        mask4 = h_i == 4
        r[mask4], g[mask4], b[mask4] = t[mask4], p[mask4], v[mask4]

        mask5 = h_i == 5
        r[mask5], g[mask5], b[mask5] = v[mask5], p[mask5], q[mask5]

        return np.stack([r, g, b], axis=2)

    def export_color_separation(self):
        """Exporte les deux couches (tonalité noir + couleur) en PNG séparé."""
        if not hasattr(self, "_tonality_image") or self._tonality_image is None:
            QMessageBox.warning(
                self,
                tr("Erreur"),
                "Pas de séparation couleur disponible. Générez d'abord une image.",
            )
            return

        folder = QFileDialog.getExistingDirectory(self, tr("Dossier d'export"))
        if not folder:
            return

        try:
            tonality_path = f"{folder}/gravure_noir.png"
            color_path = f"{folder}/impression_couleur.png"

            self._tonality_image.save(tonality_path)
            self._color_image.save(color_path)

            QMessageBox.information(
                self,
                tr("Export terminé"),
                f"{tr('Fichiers créés :')} \n{tonality_path}\n{color_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, tr("Erreur"), str(e))

    def update_color_separation_preview(self):
        """Met à jour les aperçus couleur dans l'onglet Images/Tramage."""
        if not hasattr(self, "raw_image") or self.raw_image is None:
            return

        params = {
            "bright": self.slider_bright.value(),
            "contrast": self.slider_contrast.value(),
            "gamma": self.slider_gamma.value(),
            "invert": self.chk_invert.isChecked(),
            "algo": self.combo_algo.currentText(),
        }

        tonality_pil, color_pil = self.compute_color_separation(self.raw_image, params)
        if tonality_pil is None:
            return

        # Mémoriser pour export
        self._tonality_image = tonality_pil
        self._color_image = color_pil

        # Afficher dans l'interface (si widgets disponibles)
        if hasattr(self, "lbl_tonality_preview"):
            tonality_qimg = QImage(
                tonality_pil.tobytes(),
                tonality_pil.width,
                tonality_pil.height,
                tonality_pil.width,
                QImage.Format.Format_Grayscale8,
            )
            pixmap = QPixmap.fromImage(tonality_qimg).scaledToWidth(
                300, Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_tonality_preview.setPixmap(pixmap)

        if hasattr(self, "lbl_color_preview"):
            color_qimg = QImage(
                color_pil.tobytes("raw", "RGB"),
                color_pil.width,
                color_pil.height,
                3 * color_pil.width,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(color_qimg).scaledToWidth(
                300, Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_color_preview.setPixmap(pixmap)
