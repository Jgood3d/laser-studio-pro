"""Page « Matrice de test », ouverte depuis le menu Outils."""

from PIL import Image
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
)
import matrix_image
from i18n import tr
from matrix_tile_picker import TilePicker


class TestMatrixPageMixin:
    def _lines_mm_row(self, spin_box):
        row_layout = QHBoxLayout()
        lbl_dpi = QLabel()
        lbl_dpi.setStyleSheet("color: #888888;")

        def refresh_dpi(value, _lbl=lbl_dpi):
            _lbl.setText(f"≈ {value * 25.4:.0f} DPI")

        spin_box.valueChanged.connect(refresh_dpi)
        refresh_dpi(spin_box.value())

        row_layout.addWidget(spin_box)
        row_layout.addWidget(lbl_dpi)
        spin_box.dpi_label = lbl_dpi
        spin_box.dpi_row_layout = row_layout
        return row_layout

    def _build_test_matrix_page(self):
        """Page « Matrice de test », ouverte depuis le menu Outils."""
        tab_matrix = QWidget()
        self.form_matrix = QFormLayout(tab_matrix)

        self.combo_mat_mode = QComboBox()
        self.combo_mat_mode.addItems(
            [
                tr("ui.material_mode_engraving"),
                tr("ui.material_mode_cutting"),
            ]
        )
        self.combo_mat_mode.currentIndexChanged.connect(
            self.on_mat_mode_changed
        )

        self.spin_mat_off_x = QDoubleSpinBox()
        self.spin_mat_off_x.setRange(-1000.0, 1000.0)
        self.spin_mat_off_x.setValue(0.0)
        self.spin_mat_off_y = QDoubleSpinBox()
        self.spin_mat_off_y.setRange(-1000.0, 1000.0)
        self.spin_mat_off_y.setValue(0.0)

        self.lbl_mat_p1 = QLabel(tr("ui.mat_min_power"))
        self.spin_mat_min_p = QSpinBox()
        self.spin_mat_min_p.setRange(5, 100)
        self.spin_mat_min_p.setValue(10)

        self.spin_mat_max_p = QSpinBox()
        self.spin_mat_max_p.setRange(5, 100)
        self.spin_mat_max_p.setValue(80)
        self.spin_mat_steps_p = QSpinBox()
        self.spin_mat_steps_p.setRange(2, 20)
        self.spin_mat_steps_p.setValue(5)

        self.spin_mat_min_passes = QSpinBox()
        self.spin_mat_min_passes.setRange(1, 20)
        self.spin_mat_min_passes.setValue(1)
        self.spin_mat_max_passes = QSpinBox()
        self.spin_mat_max_passes.setRange(1, 20)
        self.spin_mat_max_passes.setValue(5)
        self.spin_mat_steps_passes = QSpinBox()
        self.spin_mat_steps_passes.setRange(2, 20)
        self.spin_mat_steps_passes.setValue(5)

        self.spin_mat_min_s = QSpinBox()
        self.spin_mat_min_s.setRange(100, 20000)
        self.spin_mat_min_s.setValue(1000)
        self.spin_mat_max_s = QSpinBox()
        self.spin_mat_max_s.setRange(100, 20000)
        self.spin_mat_max_s.setValue(5000)
        self.spin_mat_steps_s = QSpinBox()
        self.spin_mat_steps_s.setRange(2, 20)
        self.spin_mat_steps_s.setValue(5)

        self.spin_mat_size = QDoubleSpinBox()
        self.spin_mat_size.setRange(2.0, 50.0)
        self.spin_mat_size.setValue(10.0)
        self.spin_mat_gap = QDoubleSpinBox()
        self.spin_mat_gap.setRange(0.5, 20.0)
        self.spin_mat_gap.setValue(3.0)

        self.spin_mat_lmm = QDoubleSpinBox()
        self.spin_mat_lmm.setRange(1.0, 50.0)
        self.spin_mat_lmm.setValue(self.spin_lmm.value())
        self.spin_mat_lmm.setEnabled(False)
        self.spin_mat_lmm.setToolTip(tr("ui.mat_lmm_auto_tooltip"))

        self.combo_mat_laser_cmd = QComboBox()
        self.combo_mat_laser_cmd.addItems(
            ["M4 (Dynamic Power)", "M3 (Constant Power)"]
        )

        self.chk_mat_homing = QCheckBox(tr("ui.mat_homing"))
        self.chk_mat_homing.setChecked(False)

        btn_gen_matrix = QPushButton(tr("ui.gen_test_matrix"))
        btn_gen_matrix.setStyleSheet(
            "background-color: #d35400; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        btn_gen_matrix.clicked.connect(self.generate_test_matrix)

        self.form_matrix.addRow(tr("ui.test_mode"), self.combo_mat_mode)
        self.form_matrix.addRow(tr("ui.mat_offset_x"), self.spin_mat_off_x)
        self.form_matrix.addRow(tr("ui.mat_offset_y"), self.spin_mat_off_y)
        self.form_matrix.addRow(self.lbl_mat_p1, self.spin_mat_min_p)
        self.form_matrix.addRow(tr("ui.mat_max_power"), self.spin_mat_max_p)
        self.form_matrix.addRow(tr("ui.mat_power_step"), self.spin_mat_steps_p)
        self.form_matrix.addRow(
            tr("ui.mat_min_passes"), self.spin_mat_min_passes
        )
        self.form_matrix.addRow(
            tr("ui.mat_max_passes"), self.spin_mat_max_passes
        )
        self.form_matrix.addRow(
            tr("ui.mat_passes_step"), self.spin_mat_steps_passes
        )
        self.form_matrix.addRow(tr("ui.mat_min_speed"), self.spin_mat_min_s)
        self.form_matrix.addRow(tr("ui.mat_max_speed"), self.spin_mat_max_s)
        self.form_matrix.addRow(tr("ui.mat_speed_step"), self.spin_mat_steps_s)
        self.form_matrix.addRow(tr("ui.mat_square_size"), self.spin_mat_size)
        self.form_matrix.addRow(tr("ui.mat_spacing"), self.spin_mat_gap)
        self.form_matrix.addRow(
            tr("ui.mat_lmm"), self._lines_mm_row(self.spin_mat_lmm)
        )
        self.form_matrix.addRow(
            tr("ui.mat_laser_cmd"), self.combo_mat_laser_cmd
        )
        self.form_matrix.addRow("", self.chk_mat_homing)
        self._build_matrix_image_group()
        self.form_matrix.addRow(self.grp_mat_image)
        self.form_matrix.addRow("", btn_gen_matrix)
        # Affichée dans une fenêtre du menu (show_settings_window)
        self.tab_matrix = tab_matrix

        self.on_mat_mode_changed(0)
        # Après on_mat_mode_changed : le test à partir d'une image n'existe qu'en gravure.
        self.combo_mat_mode.currentIndexChanged.connect(self._on_mat_image_mode_changed)
        self._on_mat_image_mode_changed()

    # ------------------------------------------------------------------
    # Test de gravure à partir d'une image (zone de l'image gravée dans chaque case)
    # ------------------------------------------------------------------
    def _build_matrix_image_group(self):
        """Cadre « Test à partir d'une image » : choix de l'image, taille de la zone, aperçu."""
        self._mat_src_image = None          # image source en niveaux de gris (PIL)
        self.grp_mat_image = QGroupBox(tr("ui.mat_image_group"))
        self.grp_mat_image.setCheckable(True)
        self.grp_mat_image.setChecked(False)
        layout = QFormLayout(self.grp_mat_image)

        hint = QLabel(tr("ui.mat_image_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888888;")
        layout.addRow(hint)

        btn_file = QPushButton(tr("ui.mat_image_choose"))
        btn_file.clicked.connect(self._mat_choose_image)
        btn_loaded = QPushButton(tr("ui.mat_image_use_loaded"))
        btn_loaded.setToolTip(tr("ui.mat_image_use_loaded_tip"))
        btn_loaded.clicked.connect(self._mat_use_loaded_image)
        buttons = QHBoxLayout()
        buttons.addWidget(btn_file)
        buttons.addWidget(btn_loaded)
        layout.addRow(buttons)

        self.lbl_mat_image_name = QLabel(tr("ui.mat_image_none"))
        self.lbl_mat_image_name.setWordWrap(True)
        layout.addRow(self.lbl_mat_image_name)

        self.spin_mat_img_width = QDoubleSpinBox()
        self.spin_mat_img_width.setRange(1.0, 5000.0)
        self.spin_mat_img_width.setValue(100.0)
        self.spin_mat_img_width.setSuffix(" mm")
        self.spin_mat_img_width.setToolTip(tr("ui.mat_image_width_tip"))
        self.spin_mat_tile_w = QDoubleSpinBox()
        self.spin_mat_tile_w.setRange(1.0, 200.0)
        self.spin_mat_tile_w.setValue(15.0)
        self.spin_mat_tile_w.setSuffix(" mm")
        self.spin_mat_tile_h = QDoubleSpinBox()
        self.spin_mat_tile_h.setRange(1.0, 200.0)
        self.spin_mat_tile_h.setValue(15.0)
        self.spin_mat_tile_h.setSuffix(" mm")
        layout.addRow(tr("ui.mat_image_width"), self.spin_mat_img_width)
        layout.addRow(tr("ui.mat_tile_width"), self.spin_mat_tile_w)
        layout.addRow(tr("ui.mat_tile_height"), self.spin_mat_tile_h)

        self.mat_tile_picker = TilePicker()
        layout.addRow(self.mat_tile_picker)
        self.lbl_mat_tile_info = QLabel()
        self.lbl_mat_tile_info.setWordWrap(True)
        self.lbl_mat_tile_info.setStyleSheet("color: #888888;")
        layout.addRow(self.lbl_mat_tile_info)

        for spin in (self.spin_mat_img_width, self.spin_mat_tile_w, self.spin_mat_tile_h):
            spin.valueChanged.connect(self._mat_update_tile)
        self.grp_mat_image.toggled.connect(self._on_mat_image_toggled)

    def matrix_image_enabled(self):
        """Vrai si la matrice doit graver une zone d'image dans chaque case."""
        return self.grp_mat_image.isEnabled() and self.grp_mat_image.isChecked()

    def _on_mat_image_mode_changed(self, *_args):
        engraving = self.combo_mat_mode.currentIndex() == 0
        self.grp_mat_image.setEnabled(engraving)
        use_image = engraving and self.grp_mat_image.isChecked()
        # La taille des cases vient alors de la zone d'image.
        self.spin_mat_size.setEnabled(not use_image)
        self.spin_mat_size.setToolTip(tr("ui.mat_size_from_image_tip") if use_image else "")

    def _on_mat_image_toggled(self, checked):
        if checked and self._mat_src_image is None and getattr(self, "raw_image", None) is not None:
            self._mat_use_loaded_image()
        self._on_mat_image_mode_changed()

    def _mat_set_source(self, gray_image, name, width_mm=None):
        self._mat_src_image = gray_image
        self.lbl_mat_image_name.setText(name)
        if width_mm and width_mm > 0:
            self.spin_mat_img_width.blockSignals(True)
            self.spin_mat_img_width.setValue(min(max(width_mm, 1.0), 5000.0))
            self.spin_mat_img_width.blockSignals(False)
        self.mat_tile_picker.set_image(gray_image)
        self._mat_update_tile()

    def _mat_choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self.tab_matrix, tr("ui.mat_image_file_title"), "", tr("ui.mat_image_file_filter"))
        if not path:
            return
        try:
            with Image.open(path) as img:
                img.load()
                dpi = img.info.get("dpi")
                gray = matrix_image.to_gray(img)
        except Exception as e:
            QMessageBox.warning(self.tab_matrix, tr("ui.mat_image_group"),
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
        self._mat_set_source(gray, path.replace("\\", "/").rsplit("/", 1)[-1], width_mm)
        self.grp_mat_image.setChecked(True)

    def _mat_use_loaded_image(self):
        raw = getattr(self, "raw_image", None)
        if raw is None:
            QMessageBox.information(self.tab_matrix, tr("ui.mat_image_group"),
                                    tr("ui.mat_image_loaded_none"))
            return
        # Taille réelle : celle donnée à l'image dans « Graver une image ».
        self._mat_set_source(matrix_image.to_gray(raw), tr("ui.mat_image_use_loaded"),
                             self.spin_w.value() if hasattr(self, "spin_w") else None)

    def _mat_update_tile(self, *_args):
        src = self._mat_src_image
        if src is None:
            self.lbl_mat_tile_info.setText("")
            return
        args = (src.width, src.height, self.spin_mat_img_width.value(),
                self.spin_mat_tile_w.value(), self.spin_mat_tile_h.value())
        try:
            fw, fh = matrix_image.frame_fraction(*args)
            eff_w, eff_h = matrix_image.effective_tile_mm(*args)
        except ValueError:
            return
        self.mat_tile_picker.set_frame_fraction(fw, fh)
        text = tr("ui.mat_tile_info").format(w=eff_w, h=eff_h, pct=fw * 100.0)
        if eff_w < args[3] - 1e-6 or eff_h < args[4] - 1e-6:
            text += "\n" + tr("ui.mat_tile_clipped").format(w=eff_w, h=eff_h)
        self.lbl_mat_tile_info.setText(text)

    def build_matrix_image_tile(self, lines_mm):
        """Zone d'image à graver dans chaque case : recadrée puis traitée comme une gravure
        d'image (luminosité, contraste, gamma, netteté, inversion et tramage de « Graver une
        image »), à `lines_mm` lignes/mm. Renvoie {arr, w_mm, h_mm, grayscale} ou None (message
        affiché). Calcul court (quelques centaines de pixels de côté) : fait ici, sans thread."""
        from workers import ImageProcessingWorker      # import tardif : workers dépend de Qt/numba
        if self._mat_src_image is None and getattr(self, "raw_image", None) is not None:
            self._mat_use_loaded_image()
        src = self._mat_src_image
        if src is None:
            QMessageBox.warning(self.tab_matrix, tr("ui.mat_image_missing_title"),
                                tr("ui.mat_image_missing_body"))
            return None
        try:
            box, w_mm, h_mm = matrix_image.crop_box_px(
                src.width, src.height, self.spin_mat_img_width.value(),
                self.spin_mat_tile_w.value(), self.spin_mat_tile_h.value(),
                *self.mat_tile_picker.center())
        except ValueError as e:
            QMessageBox.warning(self.tab_matrix, tr("ui.mat_image_group"), str(e))
            return None
        if int(w_mm * lines_mm) < 1 or int(h_mm * lines_mm) < 1:
            QMessageBox.warning(self.tab_matrix, tr("ui.mat_image_group"), tr("ui.mat_tile_too_small"))
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
            QMessageBox.warning(self.tab_matrix, tr("ui.mat_image_group"), tr("ui.mat_tile_too_small"))
            return None
        return {'arr': result["arr"], 'w_mm': w_mm, 'h_mm': h_mm,
                'grayscale': process_params['algo'] == "Niveaux de Gris"}
