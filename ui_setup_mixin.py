"""Construction de l'interface graphique : layout principal, onglets, menu, boîtes de dialogue « À propos »."""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QFormLayout, QMessageBox, QCheckBox, QSlider, QTabWidget, QGridLayout, QLineEdit, QProgressBar, QStackedWidget, QSplitter, QDialog, QDialogButtonBox, QListWidget)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
import pyqtgraph as pg
from PIL import Image
import os
from vector_layers import (
    LayerManagerWidget, VectorCanvasView
)
from graphics_view import ZoomableGraphicsView
from app_utils import get_app_dir
from app_utils import get_bundle_dir
from app_utils import find_resource
from app_utils import APP_VERSION
from i18n import tr, SUPPORTED_LANGUAGES, get_current_language, set_language
from widgets_extra import HistoryLineEdit


class UiSetupMixin:
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.load_image_from_path(file_path)
                break

    def save_splitter_sizes(self, *_args):
        settings = QSettings("LaserStudioPro", "UIConfig")
        settings.setValue("main_splitter_sizes", self.main_splitter.sizes())
        if hasattr(self, "left_v_splitter"):
            settings.setValue("left_v_splitter_sizes", self.left_v_splitter.sizes())
        if hasattr(self, "center_v_splitter"):
            settings.setValue("center_v_splitter_sizes", self.center_v_splitter.sizes())

    def load_splitter_sizes(self):
        settings = QSettings("LaserStudioPro", "UIConfig")
        sizes = settings.value("main_splitter_sizes", None)
        if sizes:
            try:
                self.main_splitter.setSizes([int(s) for s in sizes])
            except (TypeError, ValueError):
                pass
        left_v_sizes = settings.value("left_v_splitter_sizes", None)
        if left_v_sizes and hasattr(self, "left_v_splitter"):
            try:
                self.left_v_splitter.setSizes([int(s) for s in left_v_sizes])
            except (TypeError, ValueError):
                pass
        center_v_sizes = settings.value("center_v_splitter_sizes", None)
        if center_v_sizes and hasattr(self, "center_v_splitter"):
            try:
                self.center_v_splitter.setSizes([int(s) for s in center_v_sizes])
            except (TypeError, ValueError):
                pass

    def closeEvent(self, event):
        self.save_machine_settings()
        self.save_splitter_sizes()
        reply = QMessageBox.question(
            self,
            tr("ui.quit_title"),
            tr("ui.quit_save_prompt"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.save_project()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            event.accept()
        else:
            event.ignore()

    def create_slider_with_buttons(self, slider, step=5, value_formatter=None):
        layout = QHBoxLayout()
        btn_minus = QPushButton("-")
        btn_minus.setFixedWidth(30)
        btn_plus = QPushButton("+")
        btn_plus.setFixedWidth(30)

        btn_minus.clicked.connect(lambda: slider.setValue(slider.value() - step))
        btn_plus.clicked.connect(lambda: slider.setValue(slider.value() + step))

        # Étiquette affichant la valeur courante à côté du slider (ex: le
        # Gamma affiche sa valeur réelle 0.10-3.00, pas la valeur brute du
        # slider 10-300).
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

    def _lines_mm_row(self, spin_box):
        """Ligne combinant un QDoubleSpinBox 'lignes/mm' et une étiquette
        affichant l'équivalent en DPI (1 pouce = 25.4 mm), mise à jour en
        direct quand la valeur change. La référence au layout et au label
        DPI est gardée sur le spin_box lui-même, pour pouvoir les
        afficher/masquer ensemble ailleurs (ex: on_mat_mode_changed)."""
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

    def _build_menu_bar(self):
        """Barre de menu façon LightBurn : Fichier (projet), Langue, et Aide."""
        menu_bar = self.menuBar()

        menu_fichier = menu_bar.addMenu(tr("menu.file"))
        action_save = menu_fichier.addAction(tr("menu.file.save_project"))
        action_save.triggered.connect(self.save_project)
        action_load = menu_fichier.addAction(tr("menu.file.open_project"))
        action_load.triggered.connect(self.load_project)
        self.menu_recent_projects = menu_fichier.addMenu(tr("menu.file.recent_projects"))
        self._refresh_recent_projects_menu()
        menu_fichier.addSeparator()
        action_quit = menu_fichier.addAction(tr("menu.file.quit"))
        action_quit.triggered.connect(self.close)

        menu_langue = menu_bar.addMenu(tr("menu.language"))
        current_lang = get_current_language()
        self._lang_actions = {}
        for lang_code, lang_label in SUPPORTED_LANGUAGES.items():
            action_lang = menu_langue.addAction(lang_label)
            action_lang.setCheckable(True)
            action_lang.setChecked(lang_code == current_lang)
            action_lang.triggered.connect(lambda checked, code=lang_code: self._on_language_selected(code))
            self._lang_actions[lang_code] = action_lang

        menu_aide = menu_bar.addMenu(tr("menu.help"))
        action_version = menu_aide.addAction(f"{tr('menu.help.version')} {APP_VERSION}")
        action_version.setEnabled(False)
        menu_aide.addSeparator()
        action_about = menu_aide.addAction(tr("menu.help.about"))
        action_about.triggered.connect(self.show_about_dialog)
        action_support = menu_aide.addAction(tr("menu.help.support"))
        action_support.triggered.connect(self.show_support_dialog)
        action_coffee = menu_aide.addAction(tr("menu.help.coffee"))
        action_coffee.triggered.connect(self.show_buy_me_a_coffee_dialog)

    def _on_language_selected(self, lang_code):
        """Change la langue mémorisée, coche la bonne entrée du menu, et
        prévient que le changement complet ne s'appliquera qu'au prochain
        démarrage (pas de reconstruction à chaud de toute l'interface)."""
        set_language(lang_code)
        for code, action in self._lang_actions.items():
            action.setChecked(code == lang_code)
        QMessageBox.information(
            self, tr("menu.language.restart_title"), tr("menu.language.restart_body")
        )

    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("ui.about_title"))
        layout = QVBoxLayout(dialog)

        banner_path = find_resource("laser_studio_pro_banner.png")
        if banner_path:
            pixmap = QPixmap(banner_path)
            if not pixmap.isNull():
                lbl_banner = QLabel()
                lbl_banner.setPixmap(pixmap.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation))
                lbl_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(lbl_banner)
            else:
                lbl_banner_missing = QLabel(tr("ui.banner_unreadable").format(path=banner_path))
                lbl_banner_missing.setStyleSheet("color: #cc6666;")
                lbl_banner_missing.setWordWrap(True)
                layout.addWidget(lbl_banner_missing)
        else:
            searched = [
                os.path.join(get_app_dir(), "laser_studio_pro_banner.png"),
                os.path.join(get_bundle_dir(), "laser_studio_pro_banner.png"),
            ]
            searched_txt = "\n".join(sorted(set(searched)))
            lbl_banner_missing = QLabel(tr("ui.banner_missing").format(paths=searched_txt))
            lbl_banner_missing.setStyleSheet("color: #cc6666;")
            lbl_banner_missing.setWordWrap(True)
            layout.addWidget(lbl_banner_missing)

        lbl_text = QLabel(
            f"<b>Laser Studio Pro</b> — version {APP_VERSION}<br>"
            "Logiciel de pilotage GRBL pour graveur/découpeuse laser<br>"
            "Gravure image, découpe/gravure vectorielle, calques multi-usages."
        )
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        layout.addWidget(lbl_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def show_support_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("ui.support_title"))
        layout = QVBoxLayout(dialog)

        lbl_text = QLabel(tr("ui.support_body"))
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        lbl_text.setOpenExternalLinks(True)
        lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(lbl_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def show_buy_me_a_coffee_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("ui.coffee_title"))
        layout = QVBoxLayout(dialog)

        lbl_text = QLabel(
    tr("ui.coffee_body").format(
        link="<a href=\"https://ko-fi.com/jb3dlaser\">"
             "ko-fi.com/jb3dlaser</a>"
    )
)
        lbl_text.setTextFormat(Qt.TextFormat.RichText)
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        lbl_text.setOpenExternalLinks(True)
        lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(lbl_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def init_ui(self):
        self._build_menu_bar()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_panel = QVBoxLayout(left_widget)
        left_panel.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.setMovable(True)
        self.settings_tabs = tabs
        self.tab_machine_params = tab_machine_params = QWidget()
        layout_machine_params = QVBoxLayout(tab_machine_params)

        machine_profiles_box = QGroupBox(tr("mach.profiles_box"))
        machine_profiles_layout = QVBoxLayout()
        self.combo_machine_profile = QComboBox()
        self.combo_machine_profile.currentIndexChanged.connect(self._on_machine_profile_selected)
        machine_profiles_layout.addWidget(self.combo_machine_profile)
        profile_btn_row = QHBoxLayout()
        btn_new_machine = QPushButton(tr("mach.new_machine"))
        btn_new_machine.clicked.connect(self._add_machine_profile)
        btn_update_machine = QPushButton(tr("mach.update"))
        btn_update_machine.clicked.connect(self._update_machine_profile)
        btn_del_machine = QPushButton(tr("mach.delete"))
        btn_del_machine.clicked.connect(self._delete_machine_profile)
        profile_btn_row.addWidget(btn_new_machine)
        profile_btn_row.addWidget(btn_update_machine)
        profile_btn_row.addWidget(btn_del_machine)
        machine_profiles_layout.addLayout(profile_btn_row)
        lbl_profile_info = QLabel(tr("mach.profile_info"))
        lbl_profile_info.setWordWrap(True)
        machine_profiles_layout.addWidget(lbl_profile_info)
        machine_profiles_box.setLayout(machine_profiles_layout)
        layout_machine_params.addWidget(machine_profiles_box)

        machine_bed_box = QGroupBox(tr("mach.bed_box"))
        machine_bed_layout = QFormLayout()
        self.spin_machine_w = QDoubleSpinBox(); self.spin_machine_w.setRange(1.0, 5000.0); self.spin_machine_w.setValue(300.0)
        self.spin_machine_w.setSuffix(" mm")
        self.spin_machine_w.valueChanged.connect(self.update_vector_work_area)
        self.spin_machine_h = QDoubleSpinBox(); self.spin_machine_h.setRange(1.0, 5000.0); self.spin_machine_h.setValue(200.0)
        self.spin_machine_h.setSuffix(" mm")
        self.spin_machine_h.valueChanged.connect(self.update_vector_work_area)
        machine_bed_layout.addRow(tr("mach.bed_w"), self.spin_machine_w)
        machine_bed_layout.addRow(tr("mach.bed_h"), self.spin_machine_h)
        lbl_machine_info = QLabel(tr("mach.bed_info"))
        lbl_machine_info.setWordWrap(True)
        machine_bed_layout.addRow(lbl_machine_info)
        machine_bed_box.setLayout(machine_bed_layout)
        layout_machine_params.addWidget(machine_bed_box)

        machine_laser_box = QGroupBox(tr("mach.laser_box"))
        machine_laser_layout = QFormLayout()
        self.spin_machine_focal = QDoubleSpinBox()
        self.spin_machine_focal.setRange(0.01, 2.0)
        self.spin_machine_focal.setSingleStep(0.01)
        self.spin_machine_focal.setDecimals(3)
        self.spin_machine_focal.setValue(0.10)
        self.spin_machine_focal.setSuffix(" mm")
        self.spin_machine_focal.valueChanged.connect(self._on_machine_focal_changed)
        machine_laser_layout.addRow(tr("mach.focal_size"), self.spin_machine_focal)
        lbl_focal_help = QLabel(tr("mach.focal_help"))
        lbl_focal_help.setWordWrap(True)
        machine_laser_layout.addRow(lbl_focal_help)
        machine_laser_box.setLayout(machine_laser_layout)
        layout_machine_params.addWidget(machine_laser_box)

        machine_limits_box = QGroupBox(tr("mach.limits_box"))
        machine_limits_layout = QFormLayout()
        self.spin_machine_max_speed = QDoubleSpinBox()
        self.spin_machine_max_speed.setRange(1.0, 50000.0)
        self.spin_machine_max_speed.setValue(6000.0)
        self.spin_machine_max_speed.setSuffix(" mm/min")
        self.spin_machine_accel = QDoubleSpinBox()
        self.spin_machine_accel.setRange(1.0, 20000.0)
        self.spin_machine_accel.setValue(500.0)
        self.spin_machine_accel.setSuffix(" mm/s²")
        machine_limits_layout.addRow(tr("mach.max_speed"), self.spin_machine_max_speed)
        machine_limits_layout.addRow(tr("mach.accel"), self.spin_machine_accel)
        lbl_limits_info = QLabel(tr("mach.limits_info"))
        lbl_limits_info.setWordWrap(True)
        machine_limits_layout.addRow(lbl_limits_info)
        machine_limits_box.setLayout(machine_limits_layout)
        layout_machine_params.addWidget(machine_limits_box)
        layout_machine_params.addStretch()
        tabs.addTab(tab_machine_params, tr("tab.machine_params"))

        tab_img = QWidget()
        layout_img = QFormLayout(tab_img)

        btn_img = QPushButton(tr("img.load"))
        btn_img.clicked.connect(self.load_image)
        layout_img.addRow("", btn_img)

        btn_clear_img = QPushButton(tr("img.delete"))
        btn_clear_img.clicked.connect(self.clear_image)
        layout_img.addRow("", btn_clear_img)

        rot_layout = QHBoxLayout()
        btn_rot_left = QPushButton(tr("img.rotate_left"))
        btn_rot_left.clicked.connect(self.rotate_image_left)
        btn_rot_right = QPushButton(tr("img.rotate_right"))
        btn_rot_right.clicked.connect(self.rotate_image_right)
        rot_layout.addWidget(btn_rot_left)
        rot_layout.addWidget(btn_rot_right)
        layout_img.addRow(tr("img.rotation"), rot_layout)

        mirror_layout = QHBoxLayout()
        self.chk_mirror_h = QCheckBox(tr("img.mirror_h"))
        self.chk_mirror_h.stateChanged.connect(self.update_image_processing)
        self.chk_mirror_v = QCheckBox(tr("img.mirror_v"))
        self.chk_mirror_v.stateChanged.connect(self.update_image_processing)
        mirror_layout.addWidget(self.chk_mirror_h)
        mirror_layout.addWidget(self.chk_mirror_v)
        layout_img.addRow(tr("img.mirror_mode"), mirror_layout)

        self.slider_bright = QSlider(Qt.Orientation.Horizontal); self.slider_bright.setRange(-100, 100); self.slider_bright.setValue(0)
        self.slider_bright.valueChanged.connect(self.update_image_processing)
        
        self.slider_contrast = QSlider(Qt.Orientation.Horizontal); self.slider_contrast.setRange(-100, 100); self.slider_contrast.setValue(0)
        self.slider_contrast.valueChanged.connect(self.update_image_processing)
        
        self.slider_gamma = QSlider(Qt.Orientation.Horizontal); self.slider_gamma.setRange(10, 300); self.slider_gamma.setValue(100)
        self.slider_gamma.valueChanged.connect(self.update_image_processing)

        self.chk_invert = QCheckBox(tr("img.invert"))
        self.chk_invert.stateChanged.connect(self.update_image_processing)

        btn_reset_img = QPushButton(tr("img.reset"))
        btn_reset_img.clicked.connect(self.reset_image_settings)

        self.combo_algo = QComboBox()
        self.combo_algo.addItems([
            "Floyd-Steinberg", "Jarvis, Judice & Ninke", "Stucki", "Atkinson",
            "Sierra", "Sierra Lite (rapide)", "Burkes",
            "Bayer 2x2 (ordonné)", "Bayer 4x4 (ordonné)", "Bayer 8x8 (ordonné)",
            "Seuil Simple (Binaire)", "Niveaux de Gris"
        ])
        self.combo_algo.currentIndexChanged.connect(self.update_image_processing)

        self.spin_lmm = QDoubleSpinBox(); self.spin_lmm.setRange(1.0, 50.0); self.spin_lmm.setValue(10.0)
        self.spin_lmm.valueChanged.connect(self.update_image_processing)
        # Garde le champ DPI et l'indicateur de qualité à jour dès que
        # lignes/mm change, quelle qu'en soit la cause (saisie directe,
        # ou calcul programmatique depuis DPI/focale).
        self.spin_lmm.valueChanged.connect(self._sync_dpi_and_quality_from_lmm)

        # Sélecteur de mode de saisie de la résolution : en lignes/mm
        # directement, en DPI (comme les logiciels "habituels"), ou calée
        # sur la focale (taille du spot) du laser configuré dans l'onglet
        # Paramètres Machine.
        self.combo_lmm_mode = QComboBox()
        self.combo_lmm_mode.addItems([tr("img.mode_lmm"), "DPI", tr("img.mode_focal")])
        self.combo_lmm_mode.currentIndexChanged.connect(self.on_lmm_mode_changed)

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

        # Indicateur de qualité (toujours visible, quel que soit le mode
        # choisi), comparant l'écart de lignes réellement utilisé à la
        # focale configurée dans les Paramètres Machine.
        self.lbl_resolution_quality = QLabel()
        self.lbl_resolution_quality.setWordWrap(True)

        layout_img.addRow(tr("img.brightness"), self.create_slider_with_buttons(self.slider_bright, step=5))
        layout_img.addRow(tr("img.contrast"), self.create_slider_with_buttons(self.slider_contrast, step=5))
        layout_img.addRow(tr("img.gamma"), self.create_slider_with_buttons(
            self.slider_gamma, step=10, value_formatter=lambda v: f"{v / 100.0:.2f}"
        ))
        layout_img.addRow("", self.chk_invert)
        layout_img.addRow("", btn_reset_img)
        layout_img.addRow(tr("img.algorithm"), self.combo_algo)
        layout_img.addRow(tr("img.resolution"), self.combo_lmm_mode)
        layout_img.addRow("", self.stack_lmm_input)
        layout_img.addRow("", self.lbl_resolution_quality)
        # Mode par défaut : calé sur la focale machine, pour que la
        # résolution soit correcte dès l'ouverture sans action de
        # l'utilisateur (load_machine_settings pourra ensuite restaurer un
        # mode différent si l'utilisateur en avait choisi un explicitement
        # lors d'une session précédente).
        self.combo_lmm_mode.setCurrentIndex(2)
        self.on_lmm_mode_changed(2)

        btn_compare_algos = QPushButton(tr("img.compare_algos"))
        btn_compare_algos.clicked.connect(self.compare_dither_algorithms)
        layout_img.addRow("", btn_compare_algos)

        tabs.addTab(tab_img, tr("tab.image_filters"))

        tab_dim = QWidget()
        layout_dim = QVBoxLayout(tab_dim)

        dim_box = QGroupBox(tr("dim.box_title"))
        dim_layout = QFormLayout()
        self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(0.1, 2000.0); self.spin_w.setValue(100.0)
        self.spin_w.valueChanged.connect(lambda v: self.on_dimension_changed('w', v))
        self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(0.1, 2000.0); self.spin_h.setValue(100.0)
        self.spin_h.valueChanged.connect(lambda v: self.on_dimension_changed('h', v))
        self.chk_keep_ratio = QCheckBox(tr("dim.keep_ratio")); self.chk_keep_ratio.setChecked(True)

        self.combo_origin = QComboBox()
        self.combo_origin.addItems([tr("ui.origin_bottom_left"), tr("ui.origin_center")])
        self.spin_off_x = QDoubleSpinBox(); self.spin_off_x.setRange(-1000.0, 1000.0); self.spin_off_x.setValue(0.0)
        self.spin_off_y = QDoubleSpinBox(); self.spin_off_y.setRange(-1000.0, 1000.0); self.spin_off_y.setValue(0.0)

        dim_layout.addRow(tr("dim.width"), self.spin_w)
        dim_layout.addRow(tr("dim.height"), self.spin_h)
        dim_layout.addRow("", self.chk_keep_ratio)
        dim_layout.addRow(tr("dim.origin"), self.combo_origin)
        dim_layout.addRow(tr("dim.offset_x"), self.spin_off_x)
        dim_layout.addRow(tr("dim.offset_y"), self.spin_off_y)
        dim_box.setLayout(dim_layout)
        layout_dim.addWidget(dim_box)
        layout_dim.addStretch()
        tabs.addTab(tab_dim, tr("tab.dimensions"))

        tab_mach = QWidget()
        layout_mach = QVBoxLayout(tab_mach)

        usb_box = QGroupBox(tr("usb.box_title"))
        usb_layout = QFormLayout()
        self.combo_ports = QComboBox()
        btn_refresh = QPushButton(tr("usb.refresh_ports"))
        btn_refresh.clicked.connect(self.refresh_com_ports)
        self.btn_connect = QPushButton(tr("usb.connect"))
        self.btn_connect.clicked.connect(self.toggle_usb)
        usb_layout.addRow(tr("usb.port"), self.combo_ports)
        usb_layout.addRow("", btn_refresh)
        usb_layout.addRow("", self.btn_connect)
        usb_box.setLayout(usb_layout)
        layout_mach.addWidget(usb_box)

        mat_box = QGroupBox(tr("material.box_title"))
        mat_layout = QFormLayout()
        self.combo_mat = QComboBox()
        self.combo_mat.addItems(list(self.materials_db.keys()))
        self.combo_mat.currentIndexChanged.connect(self.apply_material_profile)

        btn_save_mat = QPushButton(tr("material.save"))
        btn_save_mat.clicked.connect(self.save_material_profile)
        btn_add_mat = QPushButton(tr("material.new"))
        btn_add_mat.clicked.connect(self.add_material_profile)
        btn_del_mat = QPushButton(tr("material.delete"))
        btn_del_mat.clicked.connect(self.delete_material_profile)
        btn_export_mat = QPushButton(tr("material.export"))
        btn_export_mat.clicked.connect(self.export_material_profiles)
        btn_import_mat = QPushButton(tr("material.import"))
        btn_import_mat.clicked.connect(self.import_material_profiles)

        mat_layout.addRow(tr("material.select"), self.combo_mat)
        mat_layout.addRow("", btn_save_mat)
        mat_layout.addRow("", btn_add_mat)
        mat_layout.addRow("", btn_del_mat)
        mat_layout.addRow("", btn_export_mat)
        mat_layout.addRow("", btn_import_mat)
        mat_box.setLayout(mat_layout)
        layout_mach.addWidget(mat_box)
        layout_mach.addStretch()
        tabs.addTab(tab_mach, tr("tab.machine_profiles"))

        tab_matrix = QWidget()
        self.form_matrix = QFormLayout(tab_matrix)

        self.combo_mat_mode = QComboBox()
        self.combo_mat_mode.addItems([
    tr("ui.material_mode_engraving"),
    tr("ui.material_mode_cutting"),
])
        self.combo_mat_mode.currentIndexChanged.connect(self.on_mat_mode_changed)

        self.spin_mat_off_x = QDoubleSpinBox(); self.spin_mat_off_x.setRange(-1000.0, 1000.0); self.spin_mat_off_x.setValue(0.0)
        self.spin_mat_off_y = QDoubleSpinBox(); self.spin_mat_off_y.setRange(-1000.0, 1000.0); self.spin_mat_off_y.setValue(0.0)

        self.lbl_mat_p1 = QLabel(tr("ui.mat_min_power"))
        self.spin_mat_min_p = QSpinBox(); self.spin_mat_min_p.setRange(5, 100); self.spin_mat_min_p.setValue(10)
        
        self.spin_mat_max_p = QSpinBox(); self.spin_mat_max_p.setRange(5, 100); self.spin_mat_max_p.setValue(80)
        self.spin_mat_steps_p = QSpinBox(); self.spin_mat_steps_p.setRange(2, 20); self.spin_mat_steps_p.setValue(5)

        self.spin_mat_min_passes = QSpinBox(); self.spin_mat_min_passes.setRange(1, 20); self.spin_mat_min_passes.setValue(1)
        self.spin_mat_max_passes = QSpinBox(); self.spin_mat_max_passes.setRange(1, 20); self.spin_mat_max_passes.setValue(5)
        self.spin_mat_steps_passes = QSpinBox(); self.spin_mat_steps_passes.setRange(2, 20); self.spin_mat_steps_passes.setValue(5)

        self.spin_mat_min_s = QSpinBox(); self.spin_mat_min_s.setRange(100, 20000); self.spin_mat_min_s.setValue(1000)
        self.spin_mat_max_s = QSpinBox(); self.spin_mat_max_s.setRange(100, 20000); self.spin_mat_max_s.setValue(5000)
        self.spin_mat_steps_s = QSpinBox(); self.spin_mat_steps_s.setRange(2, 20); self.spin_mat_steps_s.setValue(5)

        self.spin_mat_size = QDoubleSpinBox(); self.spin_mat_size.setRange(2.0, 50.0); self.spin_mat_size.setValue(10.0)
        self.spin_mat_gap = QDoubleSpinBox(); self.spin_mat_gap.setRange(0.5, 20.0); self.spin_mat_gap.setValue(3.0)
        
        self.spin_mat_lmm = QDoubleSpinBox(); self.spin_mat_lmm.setRange(1.0, 50.0); self.spin_mat_lmm.setValue(5.0)

        self.combo_mat_laser_cmd = QComboBox()
        self.combo_mat_laser_cmd.addItems(["M4 (Dynamic Power)", "M3 (Constant Power)"])

        self.chk_mat_homing = QCheckBox(tr("ui.mat_homing"))
        self.chk_mat_homing.setChecked(False)

        btn_gen_matrix = QPushButton(tr("ui.gen_test_matrix"))
        btn_gen_matrix.setStyleSheet("background-color: #d35400; color: white; font-weight: bold; padding: 6px;")
        btn_gen_matrix.clicked.connect(self.generate_test_matrix)

        self.form_matrix.addRow(tr("ui.test_mode"), self.combo_mat_mode)
        self.form_matrix.addRow(tr("ui.mat_offset_x"), self.spin_mat_off_x)
        self.form_matrix.addRow(tr("ui.mat_offset_y"), self.spin_mat_off_y)
        self.form_matrix.addRow(tr("ui.mat_max_power"), self.spin_mat_max_p)
        self.form_matrix.addRow(tr("ui.mat_power_step"), self.spin_mat_steps_p)
        self.form_matrix.addRow(tr("ui.mat_min_passes"), self.spin_mat_min_passes)
        self.form_matrix.addRow(tr("ui.mat_max_passes"), self.spin_mat_max_passes)
        self.form_matrix.addRow(tr("ui.mat_passes_step"), self.spin_mat_steps_passes)
        self.form_matrix.addRow(tr("ui.mat_min_speed"), self.spin_mat_min_s)
        self.form_matrix.addRow(tr("ui.mat_max_speed"), self.spin_mat_max_s)
        self.form_matrix.addRow(tr("ui.mat_speed_step"), self.spin_mat_steps_s)
        self.form_matrix.addRow(tr("ui.mat_square_size"), self.spin_mat_size)
        self.form_matrix.addRow(tr("ui.mat_spacing"), self.spin_mat_gap)
        self.form_matrix.addRow(tr("ui.mat_lmm"), self._lines_mm_row(self.spin_mat_lmm))
        self.form_matrix.addRow(tr("ui.mat_laser_cmd"), self.combo_mat_laser_cmd)
        self.form_matrix.addRow("", self.chk_mat_homing)
        self.form_matrix.addRow("", btn_gen_matrix)
        tabs.addTab(tab_matrix, tr("tab.test_matrix"))

        self.on_mat_mode_changed(0)

        tab_gcode_cfg = QWidget()
        layout_gcode_cfg = QFormLayout(tab_gcode_cfg)

        self.combo_laser_cmd = QComboBox()
        self.combo_laser_cmd.addItems(["M4 (Dynamic Power)", "M3 (Constant Power)"])
        self.spin_smax = QSpinBox(); self.spin_smax.setRange(1, 10000); self.spin_smax.setValue(1000)
        self.chk_homing = QCheckBox(tr("ui.grbl_homing")); self.chk_homing.setChecked(False)
        self.chk_overscan = QCheckBox(tr("ui.overscan_enabled")); self.chk_overscan.setChecked(True)

        self.combo_overscan_mode = QComboBox()
        self.combo_overscan_mode.addItems([tr("ui.overscan_mode_fixed"), tr("ui.overscan_mode_pct")])
        self.combo_overscan_mode.currentIndexChanged.connect(self.on_overscan_mode_changed)

        self.spin_overscan_dist = QDoubleSpinBox()
        self.spin_overscan_dist.setRange(0.0, 50.0)
        self.spin_overscan_dist.setSingleStep(0.1)
        self.spin_overscan_dist.setDecimals(1)
        self.spin_overscan_dist.setValue(2.5)
        self.spin_overscan_dist.setSuffix(" mm")

        self.spin_overscan_pct = QDoubleSpinBox()
        self.spin_overscan_pct.setRange(0.0, 50.0)
        self.spin_overscan_pct.setSingleStep(0.1)
        self.spin_overscan_pct.setDecimals(1)
        self.spin_overscan_pct.setValue(5.0)
        self.spin_overscan_pct.setSuffix(" %")

        self.overscan_stacked = QStackedWidget()
        self.overscan_stacked.addWidget(self.spin_overscan_dist)
        self.overscan_stacked.addWidget(self.spin_overscan_pct)
        self.overscan_stacked.setFixedHeight(28)

        self.txt_start_gcode = QTextEdit()
        self.txt_start_gcode.setMaximumHeight(45)
        self.txt_start_gcode.setPlainText("G21 ; Unités mm\nG90 ; Absolu")

        self.txt_end_gcode = QTextEdit()
        self.txt_end_gcode.setMaximumHeight(45)
        self.txt_end_gcode.setPlainText("M5 ; Extinction Laser\nG0 X0 Y0 ; Retour origine")

        layout_gcode_cfg.addRow(tr("ui.gcode_laser_cmd"), self.combo_laser_cmd)
        layout_gcode_cfg.addRow(tr("ui.gcode_smax"), self.spin_smax)
        layout_gcode_cfg.addRow("", self.chk_homing)
        layout_gcode_cfg.addRow("", self.chk_overscan)
        layout_gcode_cfg.addRow(tr("ui.overscan_mode_label"), self.combo_overscan_mode)
        layout_gcode_cfg.addRow(tr("ui.overscan_value_label"), self.overscan_stacked)
        layout_gcode_cfg.addRow(tr("ui.gcode_start"), self.txt_start_gcode)
        layout_gcode_cfg.addRow(tr("ui.gcode_end"), self.txt_end_gcode)
        tabs.addTab(tab_gcode_cfg, tr("tab.grbl_config"))

        tab_layers = QWidget()
        layout_layers = QVBoxLayout(tab_layers)
        self.layer_widget = LayerManagerWidget(self.layer_manager)
        self.layer_widget.layers_changed.connect(self.on_layers_changed)
        layout_layers.addWidget(self.layer_widget)
        tabs.addTab(tab_layers, tr("tab.layers"))

        laser_box = QGroupBox(tr("ui.laser_exec_box"))
        laser_layout = QFormLayout()
        # Gardés en interne (alimentés automatiquement par le calque choisi
        # ci-dessous) : plus de saisie manuelle séparée, tout se règle depuis
        # les calques désormais. Le parent explicite (laser_box) les garde en
        # vie même s'ils ne sont jamais ajoutés au layout visible.
        self.spin_speed_engrave = QSpinBox(laser_box); self.spin_speed_engrave.setRange(10, 20000); self.spin_speed_engrave.setValue(2000)
        self.spin_power_engrave = QSpinBox(laser_box); self.spin_power_engrave.setValue(30)

        self.combo_engrave_layer = QComboBox()
        self.combo_engrave_layer.currentIndexChanged.connect(self._on_engrave_layer_selected)
        laser_layout.addRow(tr("ui.image_layer_label"), self.combo_engrave_layer)
        laser_box.setLayout(laser_layout)
        # Rattachée à l'onglet "Paramètres Machine" (regroupe tous les
        # réglages liés à la machine au même endroit), insérée juste avant le
        # stretch final de cet onglet pour ne pas laisser de trou.
        layout_machine_params.insertWidget(layout_machine_params.count() - 1, laser_box)
        # Masquée : la gravure image utilise désormais silencieusement le
        # premier calque disponible (ou celui déjà sélectionné) en arrière-
        # plan, sans qu'il soit nécessaire d'exposer un contrôle dédié — les
        # calques (onglet 'Calques') suffisent à tout piloter. Le combo et
        # les widgets internes restent vivants et fonctionnels (juste invisibles).
        laser_box.setVisible(False)

        legacy_svg_box = QGroupBox(tr("ui.svg_legacy_title"))
        legacy_svg_layout = QFormLayout()
        lbl_legacy_info = QLabel(
            "⚠ Ce mode charge un SVG entier avec UN SEUL réglage de puissance/vitesse,\n"
            "sans aperçu ni possibilité de mélanger découpe et gravure sur un même fichier.\n"
            "Préfère plutôt 'Importer SVG (multi-calques)' dans l'Éditeur Vectoriel, qui\n"
            "décompose le SVG en objets indépendants assignables à des calques différents,\n"
            "avec aperçu visuel. Conservé ici uniquement pour compatibilité."
        )
        lbl_legacy_info.setWordWrap(True)
        legacy_svg_layout.addRow(lbl_legacy_info)

        btn_svg = QPushButton(tr("ui.load_svg_legacy"))
        btn_svg.clicked.connect(self.load_svg)

        self.chk_enable_cut = QCheckBox(tr("ui.enable_cut"))
        self.chk_enable_cut.setChecked(False)

        self.spin_speed_cut = QSpinBox(); self.spin_speed_cut.setRange(10, 5000); self.spin_speed_cut.setValue(300)
        self.spin_power_cut = QSpinBox(); self.spin_power_cut.setValue(90)
        self.spin_passes_cut = QSpinBox(); self.spin_passes_cut.setValue(2)

        legacy_svg_layout.addRow(tr("ui.vector_file_label"), btn_svg)
        legacy_svg_layout.addRow("", self.chk_enable_cut)
        legacy_svg_layout.addRow(tr("ui.cut_speed"), self.spin_speed_cut)
        legacy_svg_layout.addRow(tr("ui.cut_power"), self.spin_power_cut)
        legacy_svg_layout.addRow(tr("ui.cut_passes"), self.spin_passes_cut)
        legacy_svg_box.setLayout(legacy_svg_layout)

        left_bottom_widget = QWidget()
        left_bottom_layout = QVBoxLayout(left_bottom_widget)
        left_bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Ce mode est déprécié au profit de l'import SVG multi-calques de
        # l'éditeur vectoriel : la boîte n'est plus affichée (elle compressait
        # le haut du panneau), mais elle reste rattachée au panneau (juste
        # invisible) pour que ses widgets restent vivants — un QGroupBox sans
        # parent est détruit par le ramasse-miettes, ce qui aurait aussi
        # détruit tous ses enfants (chk_enable_cut et les réglages associés),
        # d'où l'erreur "wrapped C/C++ object ... has been deleted".
        left_bottom_layout.addWidget(legacy_svg_box)
        legacy_svg_box.setVisible(False)

        btn_estimate = QPushButton(tr("gcode.estimate"))
        btn_estimate.clicked.connect(self.estimate_job_time)
        left_bottom_layout.addWidget(btn_estimate)

        btn_generate = QPushButton(tr("gcode.generate"))
        btn_generate.setStyleSheet("background-color: #2b5c8f; color: white; font-weight: bold; padding: 10px;")
        btn_generate.clicked.connect(self.generate_job)
        left_bottom_layout.addWidget(btn_generate)

        gen_progress_row_main = QHBoxLayout()
        self.lbl_gen_progress_main = QLabel("")
        self.gen_progress_bar_main = QProgressBar()
        self.gen_progress_bar_main.setRange(0, 100)
        self.gen_progress_bar_main.setValue(0)
        self.gen_progress_bar_main.setVisible(False)
        self.gen_progress_bar_main.setMaximumHeight(16)
        gen_progress_row_main.addWidget(self.lbl_gen_progress_main)
        gen_progress_row_main.addWidget(self.gen_progress_bar_main)
        left_bottom_layout.addLayout(gen_progress_row_main)

        btn_import_gcode = QPushButton(tr("gcode.import"))
        btn_import_gcode.clicked.connect(self.import_gcode_file)
        left_bottom_layout.addWidget(btn_import_gcode)

        self.chk_flip_raster_preview = QCheckBox(tr("preview.flip"))
        self.chk_flip_raster_preview.stateChanged.connect(self.on_flip_raster_preview_changed)
        left_bottom_layout.addWidget(self.chk_flip_raster_preview)

        self.chk_negative_raster_preview = QCheckBox(tr("preview.negative"))
        self.chk_negative_raster_preview.stateChanged.connect(self.on_flip_raster_preview_changed)
        left_bottom_layout.addWidget(self.chk_negative_raster_preview)
        self.chk_hide_rapid_moves = QCheckBox(tr("preview.hide_rapid"))
        self.chk_hide_rapid_moves.stateChanged.connect(
            self.on_flip_raster_preview_changed
        )
        left_bottom_layout.addWidget(self.chk_hide_rapid_moves)
        
        self._last_gcode_text = None

        # Séparateur vertical redimensionnable entre les onglets de réglages
        # et ce bloc de génération/import, pour ajuster la hauteur de chacun
        # selon ses besoins (comme le séparateur gauche/centre) — taille
        # mémorisée entre les sessions (voir save/load_splitter_sizes).
        self.left_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_v_splitter.addWidget(tabs)
        self.left_v_splitter.addWidget(left_bottom_widget)
        left_panel.addWidget(self.left_v_splitter)

        center_widget = QWidget()
        center_panel = QVBoxLayout(center_widget)
        center_panel.setContentsMargins(0, 0, 0, 0)
        self.main_tabs_view = QTabWidget()
        self.main_tabs_view.setMovable(True)

        tab_previews = QWidget()
        layout_previews = QHBoxLayout(tab_previews)
        
        box_src = QGroupBox(tr("ui.source_image_box"))
        layout_src = QVBoxLayout()
        self.view_preview_src = ZoomableGraphicsView()
        layout_src.addWidget(self.view_preview_src)
        box_src.setLayout(layout_src)

        box_dither = QGroupBox(tr("ui.final_raster_box"))
        layout_dither = QVBoxLayout()
        self.view_preview_dither = ZoomableGraphicsView()
        layout_dither.addWidget(self.view_preview_dither)
        box_dither.setLayout(layout_dither)

        layout_previews.addWidget(box_src)
        layout_previews.addWidget(box_dither)
        self.main_tabs_view.addTab(tab_previews, tr("ui.tab_image_tracing"))

        tab_vector_editor = QWidget()
        layout_vector_editor = QVBoxLayout(tab_vector_editor)

        toolbar_vector = QHBoxLayout()
        btn_add_text = QPushButton(tr("ui.vector_add_text"))
        btn_add_text.clicked.connect(self.insert_text_object)
        btn_add_shape = QPushButton(tr("ui.vector_add_shape"))
        btn_add_shape.clicked.connect(self.insert_shape_object)
        btn_import_svg_vector = QPushButton(tr("ui.vector_import_svg"))
        btn_import_svg_vector.setStyleSheet("background-color: #3a6b3a; color: white;")
        btn_import_svg_vector.clicked.connect(self.import_svg_to_vector_editor)
        btn_edit_selected = QPushButton(tr("ui.vector_edit_selection"))
        btn_edit_selected.clicked.connect(self.edit_selected_vector_object)
        btn_rotate_selected = QPushButton(tr("ui.vector_rotate_90"))
        btn_rotate_selected.clicked.connect(self.rotate_selected_vector_object)
        btn_dup_selected = QPushButton(tr("ui.vector_duplicate"))
        btn_dup_selected.clicked.connect(self.duplicate_selected_vector_object)
        btn_del_selected = QPushButton(tr("ui.vector_delete"))
        btn_del_selected.clicked.connect(self.delete_selected_vector_object)
        btn_undo_vector = QPushButton(tr("ui.vector_undo"))
        btn_undo_vector.clicked.connect(lambda: self.vector_canvas.undo())
        btn_fullscreen_vector = QPushButton(tr("ui.vector_fullscreen"))
        btn_fullscreen_vector.clicked.connect(self.toggle_fullscreen_vector_editor)
        toolbar_vector.addWidget(btn_add_text)
        toolbar_vector.addWidget(btn_add_shape)
        toolbar_vector.addWidget(btn_import_svg_vector)
        toolbar_vector.addWidget(btn_edit_selected)
        toolbar_vector.addWidget(btn_rotate_selected)
        toolbar_vector.addWidget(btn_dup_selected)
        toolbar_vector.addWidget(btn_del_selected)
        toolbar_vector.addWidget(btn_undo_vector)
        toolbar_vector.addWidget(btn_fullscreen_vector)
        toolbar_vector.addStretch()
        layout_vector_editor.addLayout(toolbar_vector)

        gen_progress_row_vector = QHBoxLayout()
        self.lbl_gen_progress_vector = QLabel("")
        self.gen_progress_bar_vector = QProgressBar()
        self.gen_progress_bar_vector.setRange(0, 100)
        self.gen_progress_bar_vector.setValue(0)
        self.gen_progress_bar_vector.setVisible(False)
        self.gen_progress_bar_vector.setMaximumHeight(16)
        gen_progress_row_vector.addWidget(self.lbl_gen_progress_vector)
        gen_progress_row_vector.addWidget(self.gen_progress_bar_vector)
        layout_vector_editor.addLayout(gen_progress_row_vector)

        self.vector_canvas = VectorCanvasView(self.layer_manager)
        layout_vector_editor.addWidget(self.vector_canvas)

        pos_box = QGroupBox(tr("ui.selection_props_box"))
        pos_form = QVBoxLayout()
        pos_row1 = QHBoxLayout()
        pos_row1.addWidget(QLabel(tr("ui.vector_x_mm")))
        self.spin_vec_x = QDoubleSpinBox(); self.spin_vec_x.setRange(-1000.0, 1000.0); self.spin_vec_x.setDecimals(2)
        self.spin_vec_x.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_x)
        pos_row1.addWidget(QLabel(tr("ui.vector_y_mm")))
        self.spin_vec_y = QDoubleSpinBox(); self.spin_vec_y.setRange(-1000.0, 1000.0); self.spin_vec_y.setDecimals(2)
        self.spin_vec_y.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_y)
        pos_row1.addWidget(QLabel(tr("ui.vector_rotation_deg")))
        self.spin_vec_rot = QDoubleSpinBox(); self.spin_vec_rot.setRange(-360.0, 360.0); self.spin_vec_rot.setDecimals(1)
        self.spin_vec_rot.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_rot)
        pos_row1.addStretch()
        pos_form.addLayout(pos_row1)

        pos_row2 = QHBoxLayout()
        pos_row2.addWidget(QLabel(tr("ui.vector_layer")))
        self.combo_vec_layer = QComboBox()
        self.combo_vec_layer.currentIndexChanged.connect(self.on_vector_layer_spin_changed)
        pos_row2.addWidget(self.combo_vec_layer)
        pos_row2.addStretch()
        pos_form.addLayout(pos_row2)

        pos_box.setLayout(pos_form)
        pos_box.setEnabled(False)
        self.pos_box_vector = pos_box
        layout_vector_editor.addWidget(pos_box)

        self.lbl_vector_selection = QLabel(tr("ui.no_selection_label"))
        layout_vector_editor.addWidget(self.lbl_vector_selection)
        self.vector_canvas.selection_changed.connect(self.on_vector_selection_changed)
        self.vector_canvas.object_moved.connect(self.on_vector_object_moved)
        self.vector_canvas.edit_requested.connect(self.edit_vector_object)

        self.main_tabs_view.addTab(tab_vector_editor, tr("ui.tab_vector_editor"))
        self.tab_vector_editor = tab_vector_editor

        tab_vector_2d = QWidget()
        layout_vector_2d = QVBoxLayout(tab_vector_2d)
        
        self.plot_widget = pg.PlotWidget(title=tr("ui.plot_title"))
        self.plot_widget.setBackground('#111111')
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('bottom', tr("ui.plot_x"), color='#ffffff')
        self.plot_widget.setLabel('left', tr("ui.plot_y"), color='#ffffff')
        self.plot_widget.scene().sigMouseClicked.connect(self._on_plot_clicked)
        
        self.info_text_item = pg.TextItem(html=f'<div style="color: #cccccc;">{tr("ui.plot_empty_state")}</div>', anchor=(0, 0))
        self.plot_widget.addItem(self.info_text_item)
        
        layout_vector_2d.addWidget(self.plot_widget)

        self.main_tabs_view.addTab(tab_vector_2d, tr("ui.tab_2d_preview"))
        self.tab_vector_2d = tab_vector_2d
        center_bottom_widget = QWidget()
        center_bottom_layout = QVBoxLayout(center_bottom_widget)
        center_bottom_layout.setContentsMargins(0, 0, 0, 0)

        jog_box = QGroupBox(tr("ui.jog_box"))
        jog_layout = QGridLayout()

        btn_up = QPushButton("▲ Y+")
        btn_down = QPushButton("▼ Y-")
        btn_left = QPushButton("◄ X-")
        btn_right = QPushButton("► X+")
        
        btn_up_left = QPushButton("◤")
        btn_up_right = QPushButton("◥")
        btn_down_left = QPushButton("◣")
        btn_down_right = QPushButton("◢")

        btn_up.clicked.connect(lambda: self.jog_move(0, 1))
        btn_down.clicked.connect(lambda: self.jog_move(0, -1))
        btn_left.clicked.connect(lambda: self.jog_move(-1, 0))
        btn_right.clicked.connect(lambda: self.jog_move(1, 0))

        btn_up_left.clicked.connect(lambda: self.jog_move(-1, 1))
        btn_up_right.clicked.connect(lambda: self.jog_move(1, 1))
        btn_down_left.clicked.connect(lambda: self.jog_move(-1, -1))
        btn_down_right.clicked.connect(lambda: self.jog_move(1, -1))

        self.combo_step = QComboBox()
        self.combo_step.addItems(["0.1 mm", "1 mm", "10 mm", "100 mm"])
        self.combo_step.setCurrentIndex(2)

        self.spin_jog_speed = QSpinBox()
        self.spin_jog_speed.setRange(100, 10000)
        self.spin_jog_speed.setValue(3000)

        btn_homing_now = QPushButton(tr("ui.homing_cmd"))
        btn_homing_now.clicked.connect(lambda: self.send_manual_direct_cmd("$H"))

        btn_zero_xy = QPushButton(tr("ui.zero_work"))
        btn_zero_xy.clicked.connect(lambda: self.send_manual_direct_cmd("G92 X0 Y0"))

        btn_go_zero = QPushButton(tr("ui.go_zero"))
        btn_go_zero.clicked.connect(lambda: self.send_manual_direct_cmd("G0 X0 Y0"))

        btn_pause = QPushButton(tr("ui.pause"))
        btn_pause.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        btn_pause.clicked.connect(self.send_pause)

        btn_resume = QPushButton(tr("ui.resume"))
        btn_resume.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_resume.clicked.connect(self.send_resume)

        btn_reset = QPushButton(tr("ui.reset"))
        btn_reset.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        btn_reset.clicked.connect(self.send_reset)

        btn_kill = QPushButton(tr("ui.kill"))
        btn_kill.setStyleSheet("background-color: #ff0000; color: white; font-weight: bold;")
        btn_kill.clicked.connect(self.send_kill)

        btn_frame = QPushButton(tr("ui.frame"))
        btn_frame.clicked.connect(self.run_frame)
        
        self.btn_send = QPushButton(tr("ui.send_to_laser"))
        self.btn_send.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_send.clicked.connect(self.send_to_laser)

        jog_layout.addWidget(btn_up_left, 0, 0)
        jog_layout.addWidget(btn_up, 0, 1)
        jog_layout.addWidget(btn_up_right, 0, 2)
        jog_layout.addWidget(btn_left, 1, 0)
        jog_layout.addWidget(btn_homing_now, 1, 1)
        jog_layout.addWidget(btn_right, 1, 2)
        jog_layout.addWidget(btn_down_left, 2, 0)
        jog_layout.addWidget(btn_down, 2, 1)
        jog_layout.addWidget(btn_down_right, 2, 2)

        jog_layout.addWidget(QLabel(tr("ui.jog_step_label")), 0, 3)
        jog_layout.addWidget(self.combo_step, 0, 4)
        jog_layout.addWidget(QLabel(tr("ui.jog_speed_label")), 1, 3)
        jog_layout.addWidget(self.spin_jog_speed, 1, 4)

        jog_layout.addWidget(btn_zero_xy, 2, 3)
        jog_layout.addWidget(btn_go_zero, 2, 4)

        jog_layout.addWidget(btn_pause, 3, 0)
        jog_layout.addWidget(btn_resume, 3, 1)
        jog_layout.addWidget(btn_reset, 3, 2)
        jog_layout.addWidget(btn_kill, 3, 3)
        jog_layout.addWidget(btn_frame, 4, 0)
        jog_layout.addWidget(self.btn_send, 4, 1, 1, 4)

        jog_box.setLayout(jog_layout)
        center_bottom_layout.addWidget(jog_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        center_bottom_layout.addWidget(self.progress_bar)

        cmd_box = QGroupBox(tr("ui.direct_console_box"))
        cmd_layout = QHBoxLayout()
        self.txt_manual_cmd = HistoryLineEdit()
        self.txt_manual_cmd.setPlaceholderText(tr("ui.manual_grbl_placeholder"))
        self.txt_manual_cmd.returnPressed.connect(self.send_manual_cmd)
        
        btn_send_cmd = QPushButton(tr("ui.manual_send"))
        btn_send_cmd.clicked.connect(self.send_manual_cmd)

        cmd_layout.addWidget(self.txt_manual_cmd)
        cmd_layout.addWidget(btn_send_cmd)
        cmd_box.setLayout(cmd_layout)
        center_bottom_layout.addWidget(cmd_box)

        # Séparateur vertical redimensionnable entre la vue à onglets
        # (images, éditeur vectoriel, aperçu 2D, console...) et les
        # contrôles Jog/Commandes en dessous — taille mémorisée entre les
        # sessions (voir save/load_splitter_sizes).
        self.center_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_v_splitter.addWidget(self.main_tabs_view)
        self.center_v_splitter.addWidget(center_bottom_widget)
        self.center_v_splitter.setStretchFactor(0, 3)
        self.center_v_splitter.setStretchFactor(1, 1)
        center_panel.addWidget(self.center_v_splitter)

        tab_console_gcode = QWidget()
        layout_console_gcode = QVBoxLayout(tab_console_gcode)
        layout_console_gcode.setContentsMargins(6, 6, 6, 6)

        stats_box = QGroupBox(tr("ui.job_stats_box"))
        stats_layout = QVBoxLayout()
        self.lbl_stat_lines = QLabel(tr("ui.job_lines"))
        self.lbl_stat_power = QLabel(tr("ui.job_avg_power"))
        self.lbl_stat_time = QLabel(tr("ui.job_estimated_time"))
        stats_layout.addWidget(self.lbl_stat_lines)
        stats_layout.addWidget(self.lbl_stat_power)
        stats_layout.addWidget(self.lbl_stat_time)
        stats_box.setLayout(stats_layout)
        layout_console_gcode.addWidget(stats_box)

        export_box = QGroupBox(tr("ui.gcode_export_box"))
        export_layout = QHBoxLayout()
        
        btn_exp_gcode = QPushButton("Export .gcode")
        btn_exp_gcode.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_exp_gcode.clicked.connect(lambda: self.export_gcode_with_ext(".gcode"))
        
        btn_exp_nc = QPushButton("Export .nc")
        btn_exp_nc.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_exp_nc.clicked.connect(lambda: self.export_gcode_with_ext(".nc"))
        
        btn_exp_gc = QPushButton("Export .gc")
        btn_exp_gc.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_exp_gc.clicked.connect(lambda: self.export_gcode_with_ext(".gc"))

        export_layout.addWidget(btn_exp_gcode)
        export_layout.addWidget(btn_exp_nc)
        export_layout.addWidget(btn_exp_gc)
        export_box.setLayout(export_layout)
        layout_console_gcode.addWidget(export_box)

        layout_console_gcode.addWidget(QLabel(tr("ui.generated_console_label")))
        self.txt_console = QTextEdit()
        self.txt_console.setFontFamily("Courier")
        layout_console_gcode.addWidget(self.txt_console)

        gen_progress_row = QHBoxLayout()
        self.lbl_gen_progress = QLabel("")
        self.gen_progress_bar = QProgressBar()
        self.gen_progress_bar.setRange(0, 100)
        self.gen_progress_bar.setValue(0)
        self.gen_progress_bar.setVisible(False)
        self.gen_progress_bar.setMaximumHeight(16)
        gen_progress_row.addWidget(self.lbl_gen_progress)
        gen_progress_row.addWidget(self.gen_progress_bar)
        layout_console_gcode.addLayout(gen_progress_row)

        self.main_tabs_view.addTab(tab_console_gcode, tr("ui.tab_console_gcode"))
        self.tab_console_gcode = tab_console_gcode

        tab_job_queue = QWidget()
        layout_job_queue = QVBoxLayout(tab_job_queue)
        layout_job_queue.setContentsMargins(6, 6, 6, 6)

        self.list_job_queue = QListWidget()
        layout_job_queue.addWidget(self.list_job_queue)

        queue_btn_row1 = QHBoxLayout()
        btn_queue_add = QPushButton(tr("ui.queue_add_current"))
        btn_queue_add.clicked.connect(self.add_current_gcode_to_queue)
        btn_queue_remove = QPushButton(tr("ui.queue_remove_selected"))
        btn_queue_remove.clicked.connect(self.remove_selected_from_queue)
        btn_queue_clear = QPushButton(tr("ui.queue_clear"))
        btn_queue_clear.clicked.connect(self.clear_job_queue)
        queue_btn_row1.addWidget(btn_queue_add)
        queue_btn_row1.addWidget(btn_queue_remove)
        queue_btn_row1.addWidget(btn_queue_clear)
        layout_job_queue.addLayout(queue_btn_row1)

        self.btn_run_queue = QPushButton(tr("ui.queue_run"))
        self.btn_run_queue.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 6px;")
        self.btn_run_queue.clicked.connect(self.run_job_queue)
        layout_job_queue.addWidget(self.btn_run_queue)

        self.lbl_queue_status = QLabel(tr("ui.queue_empty"))
        layout_job_queue.addWidget(self.lbl_queue_status)

        self.main_tabs_view.addTab(tab_job_queue, tr("ui.tab_job_queue"))
        self.tab_job_queue = tab_job_queue

        splitter.addWidget(left_widget)
        splitter.addWidget(center_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        # Empêche le panneau gauche de se retrouver écrasé à quelques pixels
        # si la fenêtre est redimensionnée manuellement en dessous de la
        # taille confortable.
        left_widget.setMinimumWidth(280)
        self.main_splitter = splitter
        splitter.splitterMoved.connect(self.save_splitter_sizes)
        self.left_v_splitter.splitterMoved.connect(self.save_splitter_sizes)
        self.center_v_splitter.splitterMoved.connect(self.save_splitter_sizes)

        main_layout.addWidget(splitter)
