from __future__ import annotations

import base64
import io
from typing import Optional

import numpy as np
from PIL import Image, ImageEnhance
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr


class ImageSeparationMixin:
    """Onglet de séparation image noir / couleur pour gravure sur verre.

    Il réutilise les réglages déjà présents dans l'onglet Image & Filtres
    (luminosité, contraste, gamma, tramage, etc.) pour produire deux couches
    cohérentes de même dimension : la couche noire pour la gravure et la couche
    de couleur pour la partie imprimée / film.
    """

    def _sep_tr(self, key: str, **kwargs):
        text = tr(key)
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    def _init_image_separation_tab(self):
        if hasattr(self, "tab_image_separation"):
            return

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)

        form = QFormLayout()
        self.sep_glass_checkbox = QComboBox()
        self.sep_glass_checkbox.addItems([
            self._sep_tr("sep.glass_plate"),
            self._sep_tr("sep.plate_with_backing"),
        ])
        form.addRow(self._sep_tr("sep.glass_mode"), self.sep_glass_checkbox)

        self.sep_support_combo = QComboBox()
        self.sep_support_combo.addItems([
            self._sep_tr("sep.support_transparent_film"),
            self._sep_tr("sep.support_trace_paper"),
            self._sep_tr("sep.support_custom"),
        ])
        form.addRow(self._sep_tr("sep.print_medium"), self.sep_support_combo)

        self.sep_width_mm = QDoubleSpinBox()
        self.sep_width_mm.setRange(1.0, 10000.0)
        self.sep_width_mm.setDecimals(1)
        self.sep_width_mm.setValue(float(getattr(self, "spin_w", None).value() if hasattr(self, "spin_w") else 100.0))
        form.addRow(self._sep_tr("sep.width_mm"), self.sep_width_mm)

        self.sep_height_mm = QDoubleSpinBox()
        self.sep_height_mm.setRange(1.0, 10000.0)
        self.sep_height_mm.setDecimals(1)
        self.sep_height_mm.setValue(float(getattr(self, "spin_h", None).value() if hasattr(self, "spin_h") else 100.0))
        form.addRow(self._sep_tr("sep.height_mm"), self.sep_height_mm)

        self.sep_dpi = QDoubleSpinBox()
        self.sep_dpi.setRange(10.0, 10000.0)
        self.sep_dpi.setDecimals(0)
        self.sep_dpi.setValue(300.0)
        form.addRow(self._sep_tr("sep.engraving_dpi"), self.sep_dpi)

        action_row = QHBoxLayout()
        self.btn_sep_refresh = QPushButton(self._sep_tr("sep.refresh_preview"))
        self.btn_sep_export_black = QPushButton(self._sep_tr("sep.export_black_svg"))
        self.btn_sep_export_color = QPushButton(self._sep_tr("sep.export_color_svg"))
        self.btn_sep_refresh.clicked.connect(self._refresh_image_separation_preview)
        self.btn_sep_export_black.clicked.connect(lambda: self._export_sep_layer("black"))
        self.btn_sep_export_color.clicked.connect(lambda: self._export_sep_layer("color"))
        action_row.addWidget(self.btn_sep_refresh)
        action_row.addWidget(self.btn_sep_export_black)
        action_row.addWidget(self.btn_sep_export_color)
        layout.addLayout(form)
        layout.addLayout(action_row)

        preview_grid = QGridLayout()
        self.sep_preview_black = QLabel(self._sep_tr("sep.black_layer_preview"))
        self.sep_preview_color = QLabel(self._sep_tr("sep.color_layer_preview"))
        self.sep_preview_black.setMinimumSize(320, 220)
        self.sep_preview_color.setMinimumSize(320, 220)
        self.sep_preview_black.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sep_preview_color.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sep_preview_black.setStyleSheet("border: 1px solid #666; background: #111; color: white;")
        self.sep_preview_color.setStyleSheet("border: 1px solid #666; background: #111; color: white;")
        preview_grid.addWidget(self.sep_preview_black, 0, 0)
        preview_grid.addWidget(self.sep_preview_color, 0, 1)
        layout.addLayout(preview_grid)

        self.tab_image_separation = page
        self.main_tabs_view.addTab(page, self._sep_tr("sep.tab_title"))

    def _sync_color_separation_dimensions_from_job(self):
        if hasattr(self, "spin_w"):
            self.sep_width_mm.setValue(float(self.spin_w.value()))
        if hasattr(self, "spin_h"):
            self.sep_height_mm.setValue(float(self.spin_h.value()))
        if hasattr(self, "spin_lmm"):
            self.sep_dpi.setValue(float(self.spin_lmm.value() * 25.4))

    def _prepare_separation_image(self):
        if self.raw_image is None:
            return None

        img = self.raw_image.convert("RGB")

        if hasattr(self, "slider_bright"):
            img = ImageEnhance.Brightness(img).enhance(1.0 + self.slider_bright.value() / 100.0)
        if hasattr(self, "slider_contrast"):
            img = ImageEnhance.Contrast(img).enhance(1.0 + self.slider_contrast.value() / 100.0)

        gamma = 100.0
        if hasattr(self, "slider_gamma"):
            gamma = max(1.0, float(self.slider_gamma.value()))
        arr = np.asarray(img, dtype=np.float32) / 255.0
        arr = np.clip(arr ** (1.0 / (gamma / 100.0)), 0.0, 1.0)
        arr = np.clip(arr, 0.0, 1.0)

        if hasattr(self, "chk_invert") and self.chk_invert.isChecked():
            arr = 1.0 - arr

        img = Image.fromarray(np.uint8(np.clip(arr, 0.0, 1.0) * 255.0), "RGB")
        return img

    def _build_separation_layers(self):
        base = self._prepare_separation_image()
        if base is None:
            return None, None

        rgb = np.asarray(base, dtype=np.float32) / 255.0
        max_channel = rgb.max(axis=2)
        black_layer = np.clip(max_channel, 0.0, 1.0)

        # La couche noire représente la gravure de tonalité. On garde la
        # composante lumineuse pour la gravure, sans perdre la position exacte
        # ni la taille de l'image source.
        black_img = Image.fromarray(np.uint8(np.clip(black_layer * 255.0, 0, 255)), mode="L")

        # La couche couleur conserve le rendu de couleur de l'image d'origine.
        # Elle est rendue en RGB et exportée en SVG avec le même dimensionnement.
        color_arr = rgb.copy()
        color_arr = np.clip(color_arr, 0.0, 1.0)
        color_img = Image.fromarray(np.uint8(color_arr * 255.0), mode="RGB")

        # On force la même taille pour les deux couches, pour éviter un décalage
        # entre gravure et film lorsqu'ensuite ils sont assemblés dans l'outil.
        w_mm = float(self.sep_width_mm.value())
        h_mm = float(self.sep_height_mm.value())
        dpi = max(1.0, float(self.sep_dpi.value()))
        target_w = max(1, round(w_mm / 25.4 * dpi))
        target_h = max(1, round(h_mm / 25.4 * dpi))

        black_img = black_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        color_img = color_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        return black_img, color_img

    def _image_to_svg_data_uri(self, img: Image.Image) -> str:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _svg_from_image(self, img: Image.Image, title: str) -> str:
        w, h = img.size
        data_uri = self._image_to_svg_data_uri(img)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'  <title>{title}</title>\n'
            f'  <image href="{data_uri}" width="{w}" height="{h}" preserveAspectRatio="none" />\n'
            '</svg>\n'
        )

    def _set_label_pixmap(self, label: QLabel, img: Optional[Image.Image]):
        if img is None:
            label.setText(self._sep_tr("sep.no_image_loaded"))
            return
        arr = np.asarray(img)
        if arr.ndim == 2:
            qimg = QImage(arr.data, arr.shape[1], arr.shape[0], arr.shape[1], QImage.Format.Format_Grayscale8)
        else:
            qimg = QImage(arr.data, arr.shape[1], arr.shape[0], 3 * arr.shape[1], QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        label.setPixmap(pixmap.scaled(320, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        label.setText("")

    def _refresh_image_separation_preview(self):
        if self.raw_image is None:
            self.sep_preview_black.setText(self._sep_tr("sep.no_image_loaded"))
            self.sep_preview_color.setText(self._sep_tr("sep.no_image_loaded"))
            return

        layers = self._build_separation_layers()
        if layers is None:
            return
        black_img, color_img = layers
        self._set_label_pixmap(self.sep_preview_black, black_img)
        self._set_label_pixmap(self.sep_preview_color, color_img)

    def _export_sep_layer(self, kind: str):
        if self.raw_image is None:
            QMessageBox.warning(self, self._sep_tr("sep.title"), self._sep_tr("sep.no_image_loaded"))
            return

        layers = self._build_separation_layers()
        if layers is None:
            return
        black_img, color_img = layers
        target = black_img if kind == "black" else color_img
        svg = self._svg_from_image(target, kind)

        default_name = "laser_studio_pro_black.svg" if kind == "black" else "laser_studio_pro_color.svg"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._sep_tr("sep.export_title"),
            default_name,
            "SVG (*.svg)"
        )
        if not path:
            return
        if not path.lower().endswith(".svg"):
            path += ".svg"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            QMessageBox.information(
                self,
                self._sep_tr("sep.title"),
                self._sep_tr("sep.export_done").format(path=path)
            )
        except Exception as exc:
            QMessageBox.critical(self, self._sep_tr("sep.title"), str(exc))

    def _refresh_image_separation_on_new_image(self):
        if hasattr(self, "tab_image_separation"):
            self._sync_color_separation_dimensions_from_job()
            self._refresh_image_separation_preview()


# ---------------------------------------------------------------------------
# Traductions minimales utilisées par l'onglet séparé.
# Le système principal de l'app reste `i18n.py`; on ne duplique pas ici.
# ---------------------------------------------------------------------------

# These keys are intentionally resolved via tr(), so they integrate with the
# existing app language switcher. The fallback values below are kept as French
# source strings to be explicit while preserving runtime compatibility.

SEPARATION_FALLBACKS = {
    "sep.tab_title": "Séparation d'image",
    "sep.glass_mode": "Plaque de verre",
    "sep.glass_plate": "Plaque de verre",
    "sep.plate_with_backing": "Plaque avec support / film",
    "sep.print_medium": "Support d'impression",
    "sep.support_transparent_film": "Film transparent",
    "sep.support_trace_paper": "Papier calque",
    "sep.support_custom": "Personnalisé",
    "sep.width_mm": "Largeur (mm)",
    "sep.height_mm": "Hauteur (mm)",
    "sep.engraving_dpi": "DPI gravure",
    "sep.refresh_preview": "Actualiser l'aperçu",
    "sep.export_black_svg": "SVG noir",
    "sep.export_color_svg": "SVG couleur",
    "sep.black_layer_preview": "Calque noir / gravure",
    "sep.color_layer_preview": "Couleur extraite",
    "sep.no_image_loaded": "Aucune image chargée.",
    "sep.export_title": "Exporter vers SVG",
    "sep.export_done": "Fichier exporté : {path}",
    "sep.title": "Séparation d'image",
}


def _sep_fallback(key: str):
    return SEPARATION_FALLBACKS.get(key, key)


# Compatibility helper: if the existing `tr()` function ever doesn't know a key,
# it falls back to the localized French source text. This keeps the feature
# usable even without modifying the main dictionary immediately.
def tr_with_fallback(key: str, **kwargs):
    text = tr(key)
    if text == key:
        text = _sep_fallback(key)
    try:
        return text.format(**kwargs)
    except Exception:
        return text


# Backward compatibility for existing code paths that import this module.
ImageSeparationMixin._sep_tr = lambda self, key, **kwargs: tr_with_fallback(key, **kwargs)


# Import ready: only needed if some code calls `QFileDialog` without the app mixin.
try:
    from PyQt6.QtWidgets import QFileDialog
except Exception:  # pragma: no cover
    QFileDialog = None


__all__ = ["ImageSeparationMixin"]

