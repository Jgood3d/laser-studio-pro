"""Onglet « Graver une image » : réglages, aperçus et position du job."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from ui.widgets import ZoomableGraphicsView
from i18n import tr
from ui.widgets import AutoHideLabel


class ImageTabMixin:
    def create_slider_with_buttons(self, slider, step=5, value_formatter=None):
        layout = QHBoxLayout()
        btn_minus = QPushButton("-")
        btn_minus.setFixedWidth(30)
        btn_plus = QPushButton("+")
        btn_plus.setFixedWidth(30)

        btn_minus.clicked.connect(
            lambda: slider.setValue(slider.value() - step)
        )
        btn_plus.clicked.connect(
            lambda: slider.setValue(slider.value() + step)
        )

        lbl_value = QLabel()
        lbl_value.setFixedWidth(45)
        lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formatter = value_formatter or (lambda v: str(v))

        def refresh_label(v, _lbl=lbl_value, _fmt=formatter):
            _lbl.setText(_fmt(v))

        slider.valueChanged.connect(refresh_label)
        refresh_label(slider.value())

        layout.addWidget(btn_minus)
        layout.addWidget(slider)
        layout.addWidget(btn_plus)
        layout.addWidget(lbl_value)
        return layout

    @staticmethod
    def _side_settings_panel(content, width=360):
        """Panneau de réglages sur le côté d'un onglet central.

        Pour « Graver une image » : largeur fixe, comme le panneau de l'onglet
        Séparation, et défilement vertical si la hauteur manque. La largeur
        s'élargit au besoin pour que le contenu tienne sans défilement
        horizontal.
        """
        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        needed = (
            content.minimumSizeHint().width()
            + scroll.verticalScrollBar().sizeHint().width()
            + 2 * scroll.frameWidth()
        )
        scroll.setFixedWidth(max(width, needed))
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        return scroll

    def _build_image_settings(self):
        """Réglages de l'image (« Graver une image ») et position du job."""
        tab_img = QWidget()
        layout_img = QFormLayout(tab_img)

        btn_img = QPushButton(tr("img.load"))
        btn_img.clicked.connect(self.load_image)
        layout_img.addRow(btn_img)  # toute la largeur du panneau

        self.slider_bright = QSlider(Qt.Orientation.Horizontal)
        self.slider_bright.setRange(-100, 100)
        self.slider_bright.setValue(0)
        self.slider_bright.valueChanged.connect(self.update_image_processing)

        self.slider_contrast = QSlider(Qt.Orientation.Horizontal)
        self.slider_contrast.setRange(-100, 100)
        self.slider_contrast.setValue(0)
        self.slider_contrast.valueChanged.connect(self.update_image_processing)

        self.slider_gamma = QSlider(Qt.Orientation.Horizontal)
        self.slider_gamma.setRange(10, 300)
        self.slider_gamma.setValue(100)
        self.slider_gamma.valueChanged.connect(self.update_image_processing)
        self.slider_sharp = QSlider(Qt.Orientation.Horizontal)
        self.slider_sharp.setRange(0, 100)
        self.slider_sharp.setValue(0)
        self.slider_sharp.setToolTip(tr("img.sharpness_tip"))
        self.slider_sharp.valueChanged.connect(self.update_image_processing)

        self.chk_invert = QCheckBox(tr("img.invert"))
        self.chk_invert.stateChanged.connect(self.update_image_processing)

        # Sélecteur de matière : se contente de cocher/décocher « Inverser
        # Couleurs » (la case reste modifiable à la main). Le miroir reste
        # indépendant.
        self.combo_material_bg = QComboBox()
        self.combo_material_bg.addItem(tr("img.bg_dark"), "dark")
        self.combo_material_bg.addItem(tr("img.bg_light"), "light")
        # Fond clair = négatif désactivé (comportement historique).
        self.combo_material_bg.setCurrentIndex(1)
        self.combo_material_bg.setToolTip(tr("img.material_bg_tooltip"))
        # Les libellés sont longs (exemples de matières : 62 caractères en
        # français, 85 en allemand). Par défaut, une liste déroulante prend la
        # largeur de son élément le PLUS LONG comme largeur minimale : la
        # colonne de gauche ne pouvait plus être rétrécie avec le séparateur.
        # On fixe donc une largeur minimale courte ; la liste ouverte, elle,
        # reste assez large pour tout lire.
        self.combo_material_bg.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo_material_bg.setMinimumContentsLength(12)
        for i in range(self.combo_material_bg.count()):
            self.combo_material_bg.setItemData(
                i,
                self.combo_material_bg.itemText(i),
                Qt.ItemDataRole.ToolTipRole,
            )
        _popup = self.combo_material_bg.view()
        _popup.setMinimumWidth(_popup.sizeHintForColumn(0) + 24)
        self.combo_material_bg.currentIndexChanged.connect(
            self._on_material_bg_changed
        )

        shortcut_undo_img = QShortcut(QKeySequence.StandardKey.Undo, tab_img)
        shortcut_undo_img.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        shortcut_undo_img.activated.connect(self.undo_image_settings)
        shortcut_redo_img = QShortcut(QKeySequence.StandardKey.Redo, tab_img)
        shortcut_redo_img.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        shortcut_redo_img.activated.connect(self.redo_image_settings)

        self.combo_algo = QComboBox()
        self.combo_algo.addItems(
            [
                "Floyd-Steinberg",
                "Jarvis, Judice & Ninke",
                "Stucki",
                "Atkinson",
                "Sierra",
                "Sierra Lite (rapide)",
                "Burkes",
                "Bayer 2x2 (ordonné)",
                "Bayer 4x4 (ordonné)",
                "Bayer 8x8 (ordonné)",
                "Seuil Simple (Binaire)",
                "Niveaux de Gris",
            ]
        )
        self.combo_algo.currentIndexChanged.connect(
            self.update_image_processing
        )

        self.spin_lmm = QDoubleSpinBox()
        self.spin_lmm.setRange(1.0, 50.0)
        self.spin_lmm.setValue(10.0)
        self.spin_lmm.valueChanged.connect(self.update_image_processing)
        self.spin_lmm.valueChanged.connect(self._sync_dpi_and_quality_from_lmm)

        self.combo_lmm_mode = QComboBox()
        self.combo_lmm_mode.addItems(
            [tr("img.mode_lmm"), "DPI", tr("img.mode_focal")]
        )
        self.combo_lmm_mode.currentIndexChanged.connect(
            self.on_lmm_mode_changed
        )

        self.spin_dpi = QDoubleSpinBox()
        self.spin_dpi.setRange(10.0, 2000.0)
        self.spin_dpi.setDecimals(0)
        self.spin_dpi.setValue(254.0)
        self.spin_dpi.setSuffix(" DPI")
        self.spin_dpi.valueChanged.connect(self.on_dpi_value_changed)

        self.lbl_focal_info = QLabel()
        self.lbl_focal_info.setStyleSheet("color: #888888;")
        btn_configure_focal = QPushButton(tr("img.configure_focal"))
        btn_configure_focal.clicked.connect(self.goto_laser_focal_settings)

        self.stack_lmm_input = QStackedWidget()
        # Hauteur de son contenu, sans s'étirer : sinon la place libre de
        # l'onglet allait dans la pile et écartait la liste « Résolution », le
        # champ DPI et « Enregistrer comme focale ».
        self.stack_lmm_input.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        btn_save_focal_lmm = QPushButton(tr("img.save_as_focal"))
        btn_save_focal_lmm.clicked.connect(self.save_current_lmm_as_focal)
        page_lmm = QWidget()
        page_lmm_layout = QVBoxLayout(page_lmm)
        page_lmm_layout.setContentsMargins(0, 0, 0, 0)
        page_lmm_layout.addWidget(self.spin_lmm)
        page_lmm_layout.addWidget(btn_save_focal_lmm)
        self.stack_lmm_input.addWidget(page_lmm)

        btn_save_focal_dpi = QPushButton(tr("img.save_as_focal"))
        btn_save_focal_dpi.clicked.connect(self.save_current_lmm_as_focal)
        page_dpi = QWidget()
        page_dpi_layout = QVBoxLayout(page_dpi)
        page_dpi_layout.setContentsMargins(0, 0, 0, 0)
        page_dpi_layout.addWidget(self.spin_dpi)
        page_dpi_layout.addWidget(btn_save_focal_dpi)
        self.stack_lmm_input.addWidget(page_dpi)

        page_focal = QWidget()
        page_focal_layout = QVBoxLayout(page_focal)
        page_focal_layout.setContentsMargins(0, 0, 0, 0)
        page_focal_layout.addWidget(self.lbl_focal_info)
        page_focal_layout.addWidget(btn_configure_focal)
        self.stack_lmm_input.addWidget(page_focal)

        self.lbl_resolution_quality = AutoHideLabel()
        self.lbl_resolution_quality.setWordWrap(True)

        layout_img.addRow(
            tr("img.brightness"),
            self.create_slider_with_buttons(self.slider_bright, step=5),
        )
        layout_img.addRow(
            tr("img.contrast"),
            self.create_slider_with_buttons(self.slider_contrast, step=5),
        )
        layout_img.addRow(
            tr("img.gamma"),
            self.create_slider_with_buttons(
                self.slider_gamma,
                step=10,
                value_formatter=lambda v: f"{v / 100.0:.2f}",
            ),
        )
        layout_img.addRow(
            tr("img.sharpness"),
            self.create_slider_with_buttons(self.slider_sharp, step=5),
        )
        layout_img.addRow(tr("img.material_bg"), self.combo_material_bg)
        layout_img.addRow("", self.chk_invert)
        layout_img.addRow(tr("img.algorithm"), self.combo_algo)
        layout_img.addRow(tr("img.resolution"), self.combo_lmm_mode)
        layout_img.addRow("", self.stack_lmm_input)
        layout_img.addRow("", self.lbl_resolution_quality)

        self.combo_lmm_mode.setCurrentIndex(2)
        self.on_lmm_mode_changed(2)

        # Réglages de l'image : panneau de gauche de l'onglet central « Graver
        # une image ».
        self.tab_img = tab_img

        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0.1, 2000.0)
        self.spin_w.setValue(100.0)
        self.spin_w.valueChanged.connect(
            lambda v: self.on_dimension_changed("w", v)
        )
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0.1, 2000.0)
        self.spin_h.setValue(100.0)
        self.spin_h.valueChanged.connect(
            lambda v: self.on_dimension_changed("h", v)
        )
        self.chk_keep_ratio = QCheckBox(tr("dim.keep_ratio"))
        self.chk_keep_ratio.setChecked(True)

        self.combo_origin = QComboBox()
        self.combo_origin.addItems(
            [tr("ui.origin_bottom_left"), tr("ui.origin_center")]
        )
        self.spin_off_x = QDoubleSpinBox()
        self.spin_off_x.setRange(-1000.0, 1000.0)
        self.spin_off_x.setValue(0.0)
        self.spin_off_y = QDoubleSpinBox()
        self.spin_off_y.setRange(-1000.0, 1000.0)
        self.spin_off_y.setValue(0.0)

        # Taille + offset de l'image : en haut des réglages de « Graver une
        # image ».
        layout_img.insertRow(1, tr("dim.width"), self.spin_w)
        layout_img.insertRow(2, tr("dim.height"), self.spin_h)
        # Toute la largeur du panneau.
        layout_img.insertRow(3, self.chk_keep_ratio)
        # Offset X/Y du job sur le plateau (workers.AdvancedGCodeWorker /
        # G-code)
        layout_img.insertRow(4, tr("dim.offset_x"), self.spin_off_x)
        layout_img.insertRow(5, tr("dim.offset_y"), self.spin_off_y)

        # Origine du repère (bas-gauche / centre) : panneau machine, avec jog
        # / cadrage.
        self.job_position_box = QGroupBox(tr("ui.job_position_box"))
        job_position_layout = QFormLayout(self.job_position_box)
        job_position_layout.addRow(tr("dim.origin"), self.combo_origin)
        lbl_off_hint = QLabel(tr("ui.job_offset_in_image_tab"))
        lbl_off_hint.setWordWrap(True)
        lbl_off_hint.setStyleSheet("color: #888888;")
        job_position_layout.addRow(lbl_off_hint)

    def _on_show_original_toggled(self, checked: bool):
        """Affiche/masque l'image originale.

        Égalise les deux cadres quand les deux sont visibles.
        """
        if hasattr(self, "box_source_image"):
            self.box_source_image.setVisible(bool(checked))
        if checked:
            # Après le relayout Qt, forcer 50/50 originale | tramé
            QTimer.singleShot(0, self._equalize_preview_image_panes)

    def _equalize_preview_image_panes(self):
        """Donne la même largeur aux cadres originale et tramé."""
        splitter = getattr(self, "preview_image_splitter", None)
        if splitter is None or not hasattr(self, "box_source_image"):
            return
        if not self.box_source_image.isVisible():
            return
        total = sum(splitter.sizes())
        if total <= 0:
            total = max(splitter.width(), 200)
        half = total // 2
        splitter.setSizes([half, total - half])

    def _build_image_tab(self):
        """Onglet « Graver une image » : réglages, aperçus et comparaison."""
        tab_previews = QWidget()
        outer_layout_previews = QVBoxLayout(tab_previews)
        outer_layout_previews.setContentsMargins(4, 4, 4, 4)

        # Barre d'outils de l'onglet : comparaison des algorithmes à gauche
        # (ancien bouton de l'onglet Image & Filtres : n'agit que sur l'image
        # de cet onglet), plein écran aligné à droite.
        compare_icon = QIcon.fromTheme(
            "view-app-grid",
            QIcon.fromTheme(
                "view-list-icons",
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_FileDialogListView
                ),
            ),
        )
        # Affiche ou masque l'image originale (masquée par défaut, voir
        # box_source_image).
        self.chk_show_original = QCheckBox(tr("img.show_original"))
        self.chk_show_original.setToolTip(tr("img.show_original_tip"))
        self.chk_show_original.toggled.connect(self._on_show_original_toggled)
        toolbar_previews = self._build_tab_toolbar(
            tab_previews,
            self._toggle_fullscreen_image_tab,
            left_actions=[
                (
                    compare_icon,
                    tr("img.compare_algos"),
                    tr("img.compare_algos_tip"),
                    self.compare_dither_algorithms,
                )
            ],
            left_widgets=[self.chk_show_original],
        )
        outer_layout_previews.addWidget(toolbar_previews)

        layout_previews = QHBoxLayout()
        # Réglages de l'image à gauche, comme dans Séparation.
        img_settings_scroll = self._side_settings_panel(self.tab_img)
        layout_previews.addWidget(img_settings_scroll)

        box_src = QGroupBox(tr("ui.source_image_box"))
        layout_src = QVBoxLayout()
        layout_src.setContentsMargins(4, 4, 4, 4)
        self.view_preview_src = ZoomableGraphicsView()
        layout_src.addWidget(self.view_preview_src)
        box_src.setLayout(layout_src)
        box_src.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        box_dither = QGroupBox(tr("ui.final_raster_box"))
        layout_dither = QVBoxLayout()
        layout_dither.setContentsMargins(4, 4, 4, 4)
        self.view_preview_dither = ZoomableGraphicsView()
        layout_dither.addWidget(self.view_preview_dither)
        box_dither.setLayout(layout_dither)
        box_dither.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Splitter : dès que l'originale est visible, les deux cadres ont la
        # même largeur
        self.preview_image_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.preview_image_splitter.addWidget(box_src)
        self.preview_image_splitter.addWidget(box_dither)
        self.preview_image_splitter.setStretchFactor(0, 1)
        self.preview_image_splitter.setStretchFactor(1, 1)
        self.preview_image_splitter.setChildrenCollapsible(False)
        # Image originale masquée par défaut : le rendu tramé prend toute la
        # place.
        box_src.setVisible(False)
        self.box_source_image = box_src
        layout_previews.addWidget(self.preview_image_splitter, 1)
        outer_layout_previews.addLayout(layout_previews)
        self.main_tabs_view.addTab(tab_previews, tr("ui.tab_image_tracing"))
        self.tab_previews = tab_previews
