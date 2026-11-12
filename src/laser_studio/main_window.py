"""Fenêtre principale de l'application.

FullLaserStudio construit la fenêtre (init_ui), branche les signaux de ses
panneaux et gère ses événements (fermeture, glisser-déposer) ; les mixins
apportent le contenu des onglets et la logique.
"""
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton, QScrollArea, QSplitter, QTabBar, QTabWidget,
                             QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QStandardItemModel

from laser_studio.core.constants import ORIGIN_BOTTOM_LEFT
from laser_studio.i18n import tr
from laser_studio.ui.machine import MachinePanel
from laser_studio.ui.machine.job_position import JobPositionBox
from laser_studio.ui.settings.grbl_config import GrblConfigPage
from laser_studio.ui.settings.machine_params import MachineParamsPage
from laser_studio.ui.settings.machine_profiles import MachineProfilesPage
from laser_studio.ui.settings.test_matrix import TestMatrixPage
from laser_studio.ui.settings.window import SettingsWindow
from laser_studio.ui.statusbar import StatusBar
from laser_studio.ui.tabs.console import ConsoleTab
from laser_studio.ui.tabs.image import ImageTab
from laser_studio.ui.tabs.job_queue import JobQueueTab
from laser_studio.ui.tabs.layers import LayersTab
from laser_studio.ui.tabs.png2svg import Png2SvgTab
from laser_studio.ui.tabs.preview_2d import Preview2DTab
from laser_studio.ui.tabs.separation import SeparationTab
from laser_studio.ui.utils import fullscreen_icon
from laser_studio.ui.widgets import FullscreenWindow, TabCloseButton

from laser_studio.controllers.job_queue import Engraver, JobQueueController
from laser_studio.controllers.materials import DEFAULT_MATERIALS_DB, MaterialsController
from laser_studio.controllers.layer_memory import apply_saved_layers
from laser_studio.controllers.machine_profiles import MachineProfilesController, ProfileFields
from laser_studio.controllers.matrix_image import MatrixImageController
from laser_studio.controllers.png2svg import Png2SvgController
from laser_studio.controllers.project import ProjectController
from laser_studio.grbl.connection import LaserUSBController
from laser_studio.vector_layers import LayerManager, VectorCanvasView

from laser_studio.ui.app.window_controller import WindowControllerMixin
from laser_studio.image_processing_mixin import ImageProcessingMixin
from laser_studio.vector_editing_mixin import VectorEditingMixin
from laser_studio.gcode_generation_mixin import GcodeGenerationMixin
from laser_studio.laser_control_mixin import LaserControlMixin
from laser_studio.separation_mixin import SeparationMixin


class FullLaserStudio(QMainWindow, WindowControllerMixin,
                       ImageProcessingMixin,
                       VectorEditingMixin, GcodeGenerationMixin, LaserControlMixin,
                       SeparationMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laser Studio Pro - GRBL Controller")
        self.resize(1600, 980)
        
        self.setAcceptDrops(True)
        
        self.usb = LaserUSBController()
        self.raw_image = None
        self.processed_array = None
        self.loaded_svg_path = None
        self.layer_manager = LayerManager()
        self.block_aspect_signal = False
        self.streamer = None
        self.cmd_thread = None
        self.status_poll_thread = None
        self.has_homed_since_connect = False
        self.img_worker = None
        self.pending_reprocess = False
        self._img_undo_stack = []
        self._img_redo_stack = []
        self._img_last_undo_push_time = 0.0

        # Gravure d'une image : vitesse (mm/min) et puissance (%), reprises du
        # calque de gravure (engrave_layer_id, voir _on_engrave_layer_selected).
        self.engrave_speed = 2000
        self.engrave_power = 30
        self.engrave_layer_id = None
        # Ancien mode SVG : découpe d'un SVG entier (loaded_svg_path), avec un
        # seul réglage. Plus accessible depuis l'interface, mais encore lu dans
        # les anciens projets et les profils matériaux (voir set_cut_settings).
        self.cut_enabled = False
        self.cut_speed = 300
        self.cut_power = 90
        self.cut_passes = 2
        
        self.process_timer = QTimer()
        self.process_timer.setSingleShot(True)
        self.process_timer.setInterval(150)
        self.process_timer.timeout.connect(self._do_update_image_processing)

        # Sauvegarde automatique du projet toutes les 5 minutes, pour ne rien
        # perdre en cas de plantage ou de coupure de courant en pleine session.
        # Fichier du projet (enregistrer, ouvrir, récents, sauvegarde
        # automatique) ; l'état lui-même est lu et réappliqué par
        # _capture_project / _restore_project.
        self.project = ProjectController(
            self,
            capture=self._capture_project,
            restore=self._restore_project,
            show_recent_projects=lambda paths: (
                self.app_menu_bar.file_menu.set_recent_projects(paths)
            ),
            log_to_console=lambda text: self.txt_console.append(text),
        )
        self.autosave_timer = QTimer()
        self.autosave_timer.setInterval(5 * 60 * 1000)
        self.autosave_timer.timeout.connect(self.project.autosave)
        self.autosave_timer.start()

        self.init_ui()
        self.load_machine_settings()
        self.load_splitter_sizes()
        self.update_vector_work_area()
        self._refresh_engrave_layer()
        self.refresh_com_ports()
        # Différé (au lieu d'un appel direct ici) : à ce stade du __init__,
        # la fenêtre n'est pas encore affichée (main.py appelle showMaximized()
        # après la construction de FullLaserStudio, une fois l'écran de
        # démarrage resté quelques secondes). Une QMessageBox modale lancée
        # maintenant peut donc apparaître invisible/hors-écran avant même que
        # la fenêtre existe visuellement — la proposition est faite au premier
        # affichage de la fenêtre (voir showEvent).
        self._autosave_recovery_pending = True
        self.job_queue.load()

    # -- Construction de la fenêtre

    def init_ui(self):
        self._build_app_menus()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Plus de colonne de gauche : les pages de réglages s'ouvrent dans des fenêtres (menu
        # Paramètres), les réglages de l'image sont dans « Graver une image », la position du job
        # dans le panneau machine. Le centre occupe toute la largeur.
        self._build_machine_params_page()
        self._build_image_tab()
        self._build_machine_profiles_page()
        self._build_test_matrix_page()
        self._build_grbl_config_page()
        self._build_layers_tab()
        self.setStatusBar(StatusBar(self))

        self._last_gcode_text = None

        center_widget = QWidget()
        center_panel = QVBoxLayout(center_widget)
        center_panel.setContentsMargins(0, 0, 0, 0)
        self.main_tabs_view = QTabWidget()
        self.main_tabs_view.setMovable(True)

        self.main_tabs_view.addTab(self.tab_previews, tr("ui.tab_image_tracing"))

        self._build_png2svg_tab()

        # --- ONGLET SÉPARATION COULEUR ---
        self._build_separation_tab()

        self._build_vector_editor_tab()
        self.main_tabs_view.addTab(self.layers_tab, tr("tab.layers"))

        self._build_2d_preview_tab()
        center_bottom_scroll = self._build_machine_panel()
        center_panel.addWidget(self.center_v_splitter)

        self._build_console_tab()
        self._build_job_queue_tab()

        self.center_bottom_widget = center_bottom_scroll     # masqué / affiché selon l'onglet
        self.main_tabs_view.currentChanged.connect(self._update_bottom_panel_visibility)
        self.main_tabs_view.currentChanged.connect(self._on_main_tab_changed)
        self.main_tabs_view.currentChanged.connect(self.update_image_actions_state)
        # Onglets masqués au démarrage, ouverts à la demande depuis le menu Outils (show_main_tab),
        # ou Affichage pour la console G-Code (set_gcode_console_visible).
        for tab in (self.tab_separation, self.tab_png2svg, self.tab_console_gcode):
            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)
        self._update_bottom_panel_visibility()
        self.update_image_actions_state()
        # Console G-Code : affichée ou non comme à la dernière fermeture (masquée la première fois).
        self.app_actions.gcode_console.setChecked(self.gcode_console_was_visible())

        # Largeur minimale EXPLICITE du centre. Sans elle, la largeur minimale serait calculée
        # d'après le contenu : la barre d'outils de l'éditeur vectoriel (11 boutons, ~1500 px) et la
        # rangée d'alignement imposeraient environ 1500 px à la fenêtre. Trop étroit, le centre se
        # contente de serrer ses boutons.
        center_widget.setMinimumWidth(480)
        self.center_v_splitter.splitterMoved.connect(self.save_splitter_sizes)

        main_layout.addWidget(center_widget)

    def _build_machine_panel(self):
        """Panneau machine sous les onglets, abonné à la logique de la machine.

        Les sous-panneaux émettent les demandes de l'utilisateur ; la fenêtre
        les transmet aux méthodes de LaserControlMixin. La vitesse maximale
        du graveur (`spin_machine_max_speed`, qui doit déjà exister) borne le
        curseur de vitesse du pilotage. Renvoie la zone de défilement qui
        contient le panneau, placée sous les onglets dans `center_v_splitter`.
        """
        self.machine_panel = MachinePanel(
            self.combo_ports.model(),
            self.spin_machine_max_speed.value(),
        )
        connection = self.machine_panel.connection_panel
        # Même port choisi dans le panneau et dans la page des matériaux.
        connection.ports_combo.currentIndexChanged.connect(self.tab_machine_profiles.set_port_index)
        self.tab_machine_profiles.port_selected.connect(connection.ports_combo.setCurrentIndex)
        connection.refresh_requested.connect(self.refresh_com_ports)
        connection.connect_requested.connect(self.toggle_connection)
        jog = self.machine_panel.jog_panel
        jog.jog_requested.connect(self.jog_move)
        jog.home_requested.connect(self.home_machine)
        jog.pause_requested.connect(self.send_pause)
        jog.resume_requested.connect(self.send_resume)
        jog.reset_requested.connect(self.send_reset)
        jog.emergency_stop_requested.connect(self.emergency_stop)
        jog.send_job_requested.connect(self.send_job)
        self.tab_machine_params.max_speed_changed.connect(jog.set_max_speed)

        job_actions = self.machine_panel.job_actions_panel
        job_actions.frame_requested.connect(self.run_frame)
        job_actions.set_work_zero_requested.connect(self.set_work_zero)
        job_actions.go_to_work_zero_requested.connect(self.go_to_work_zero)
        job_actions.repeat_job_requested.connect(self.repeat_last_job)

        connection.unlock_requested.connect(self.unlock_alarm)
        connection.command_submitted.connect(self.send_console_command)
        # Commandes verrouillées tant que non connecté
        self.update_connection_widgets()

        self.main_tabs_view.setMinimumHeight(150)
        # Le panneau machine (DRO, jog, console directe) demande ~400 px.
        # Réduit plus bas avec le séparateur, il défile au lieu d'écraser ses
        # cadres jusqu'à n'en laisser que les titres.
        center_bottom_scroll = QScrollArea()
        center_bottom_scroll.setWidget(self.machine_panel)
        center_bottom_scroll.setWidgetResizable(True)
        center_bottom_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        center_bottom_scroll.setMinimumHeight(100)
        self.center_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_v_splitter.addWidget(self.main_tabs_view)
        self.center_v_splitter.addWidget(center_bottom_scroll)
        self.center_v_splitter.setStretchFactor(0, 3)
        self.center_v_splitter.setStretchFactor(1, 1)
        return center_bottom_scroll

    def _build_machine_params_page(self):
        """Page « Paramètres du graveur », abonnée à la logique des profils.

        Affichée dans une fenêtre du menu Paramètres (show_settings_window).
        """
        page = MachineParamsPage()
        self.machines = MachineProfilesController(
            self,
            page.profile_combo,
            ProfileFields(
                capture=self._capture_machine_profile,
                apply=self._apply_machine_profile,
                apply_layers=self._apply_profile_layers,
                memory=self._machine_memory,
                profile_selected=self._after_machine_profile_selected,
                link_layers_to_focal=lambda: self.layers_tab.link_all_to_focal(),
            ),
            save_settings=self.save_machine_settings,
        )
        page.profile_selected.connect(self.machines.on_selected)
        page.new_profile_requested.connect(self.machines.new_profile)
        page.update_profile_requested.connect(self.machines.update_profile)
        page.delete_profile_requested.connect(self.machines.delete_profile)
        page.bed_size_changed.connect(self.update_vector_work_area)
        page.focal_changed.connect(self._on_machine_focal_changed)
        # Noms historiques des champs, lus par la logique (profils,
        # génération, éditeur vectoriel, Stencil Studio…).
        self.combo_machine_profile = page.profile_combo
        self.spin_machine_w = page.bed_width_spin
        self.spin_machine_h = page.bed_height_spin
        self.spin_machine_focal = page.focal_spin
        self.spin_machine_max_speed = page.max_speed_spin
        self.spin_machine_accel = page.accel_spin
        self.tab_machine_params = page

    def _build_machine_profiles_page(self):
        """Page « Matériaux et connexion au graveur », abonnée à la logique.

        Sa liste des ports est celle du panneau « Connexion » (même modèle,
        voir _build_machine_panel), et le port choisi est le même des deux
        côtés.
        """
        materials = dict(DEFAULT_MATERIALS_DB)
        page = MachineProfilesPage(QStandardItemModel(self), materials.keys())
        self.materials = MaterialsController(
            self,
            page.material_combo,
            materials,
            current_settings=self._job_settings,
            apply_settings=self._apply_job_settings,
        )
        page.refresh_ports_requested.connect(self.refresh_com_ports)
        page.connect_requested.connect(self.toggle_connection)
        page.material_selected.connect(self.materials.apply_selected)
        page.save_material_requested.connect(self.materials.save_selected)
        page.new_material_requested.connect(self.materials.new_material)
        page.delete_material_requested.connect(self.materials.delete_selected)
        page.export_materials_requested.connect(self.materials.export_materials)
        page.import_materials_requested.connect(self.materials.import_materials)
        # Nom historique de la liste des ports, lu par la logique.
        self.combo_ports = page.ports_combo
        self.tab_machine_profiles = page

    def _build_grbl_config_page(self):
        """Page « Configuration GRBL », abonnée au dialogue avec le graveur.

        Affichée dans une fenêtre du menu Paramètres (show_settings_window).
        """
        page = GrblConfigPage()
        page.bidir_test_requested.connect(self.generate_bidir_test)
        # Décalage aller/retour : mémorisé dans le profil de la machine.
        page.scan_offset_changed.connect(self.machines.schedule_persist)
        page.read_settings_requested.connect(self.read_grbl_settings)
        page.send_settings_requested.connect(self.send_grbl_settings)
        page.export_settings_requested.connect(self.export_grbl_settings)
        page.import_settings_requested.connect(self.import_grbl_settings)
        page.link_settings_to_profile_requested.connect(
            self.machines.update_profile
        )
        # Noms historiques des champs, lus par la logique (génération,
        # profils machine, projets, connexion au graveur).
        self.combo_laser_cmd = page.laser_cmd_combo
        self.spin_smax = page.smax_spin
        self.chk_homing = page.homing_check
        self.chk_overscan = page.overscan_check
        self.chk_safe_cut_order = page.safe_cut_order_check
        self.combo_overscan_mode = page.overscan_mode_combo
        self.spin_overscan_dist = page.overscan_dist_spin
        self.spin_overscan_pct = page.overscan_pct_spin
        self.spin_scan_offset = page.scan_offset_spin
        self.txt_start_gcode = page.start_gcode_edit
        self.txt_end_gcode = page.end_gcode_edit
        self.txt_grbl_settings = page.grbl_settings_edit
        self.tab_grbl_config = page

    def _build_test_matrix_page(self):
        """Page « Matrice de test », abonnée à la génération de la matrice.

        Ses lignes/mm suivent celles de « Graver une image » (spin_lmm, qui
        doit déjà exister ; voir _sync_matrix_lmm_from_image).
        """
        page = TestMatrixPage(self.spin_lmm.value())
        page.generate_requested.connect(self._generate_test_matrix_and_show)
        # Test à partir d'une image : fichier choisi, ou image de « Graver une
        # image » avec ses réglages de tramage.
        self.matrix_image = MatrixImageController(
            page,
            loaded_image=self._loaded_image_and_width,
            image_settings=self.tab_previews.settings.processing_settings,
        )
        page.choose_image_requested.connect(self.matrix_image.choose_image)
        page.use_loaded_image_requested.connect(
            self.matrix_image.use_loaded_image
        )
        page.image_test_toggled.connect(self.matrix_image.on_image_test_toggled)
        # Nom historique : décochée et grisée avec chk_homing quand le
        # graveur n'a pas de homing ($22=0, voir LaserControlMixin).
        self.chk_mat_homing = page.homing_check
        self.tab_matrix = page

    def _loaded_image_and_width(self):
        """(image, largeur en mm) de « Graver une image », ou None."""
        if getattr(self, "raw_image", None) is None:
            return None
        return self.raw_image, self.spin_w.value()

    def _job_settings(self):
        """Vitesses, puissances et passes en cours, au format d'un matériau
        (voir MaterialsController)."""
        return {
            "sp_e": self.engrave_speed,
            "pw_e": self.engrave_power,
            "sp_c": self.cut_speed,
            "pw_c": self.cut_power,
            "pass_c": self.cut_passes,
        }

    def _apply_job_settings(self, material):
        """Applique les réglages d'un matériau (gravure, puis découpe)."""
        self.set_engrave_settings(material["sp_e"], material["pw_e"])
        self.set_cut_settings(material["sp_c"], material["pw_c"], material["pass_c"])

    def _generate_test_matrix_and_show(self):
        """Génère la matrice de test, puis ferme sa fenêtre et affiche
        l'aperçu 2D, où le G-Code apparaît. En cas d'erreur, la fenêtre
        reste ouverte pour corriger les réglages."""
        if not self.generate_test_matrix():
            return
        self.tab_matrix.window().close()
        self.show_main_tab("tab_vector_2d")
        self.raise_()
        self.activateWindow()

    def _build_layers_tab(self):
        """Onglet « Calques », abonné à la logique des calques.

        Il est placé dans les onglets par init_ui, entre l'éditeur
        vectoriel et l'aperçu 2D.
        """
        self.layers_tab = LayersTab(
            self.layer_manager,
            focal_getter=lambda: self.spin_machine_focal.value(),
        )
        self.layers_tab.layers_changed.connect(self.on_layers_changed)
        # Mémorise les réglages des calques dans le profil de la machine active.
        self.layers_tab.layers_changed.connect(self.machines.schedule_persist)

    def _build_image_tab(self):
        """Onglet « Graver une image » et cadre « Position du job », abonnés
        au traitement de l'image (ImageProcessingMixin).

        Construit tôt : la matrice de test lit ses lignes/mm, le panneau
        machine reçoit le cadre « Position du job ». L'onglet est placé
        dans les onglets par init_ui.
        """
        tab = ImageTab()
        settings = tab.settings
        settings.load_requested.connect(self.load_image)
        settings.processing_changed.connect(self.update_image_processing)
        settings.material_changed.connect(self._on_material_bg_changed)
        settings.size_changed.connect(self.on_dimension_changed)
        settings.resolution_mode_changed.connect(self.on_lmm_mode_changed)
        settings.lines_per_mm_changed.connect(
            self._sync_dpi_and_quality_from_lmm
        )
        settings.dpi_changed.connect(self.on_dpi_value_changed)
        settings.configure_focal_requested.connect(
            self.goto_laser_focal_settings
        )
        settings.save_as_focal_requested.connect(
            self.save_current_lmm_as_focal
        )
        settings.undo_requested.connect(self.undo_image_settings)
        settings.redo_requested.connect(self.redo_image_settings)
        tab.compare_requested.connect(self.compare_dither_algorithms)
        tab.fullscreen_requested.connect(self._toggle_fullscreen_image_tab)
        # Noms historiques des champs, lus par la logique (traitement de
        # l'image, génération, projets, profils, séparation, matrice).
        self.spin_w = settings.width_spin
        self.spin_h = settings.height_spin
        self.chk_keep_ratio = settings.keep_ratio_check
        self.spin_off_x = settings.offset_x_spin
        self.spin_off_y = settings.offset_y_spin
        self.slider_bright = settings.brightness_slider
        self.slider_contrast = settings.contrast_slider
        self.slider_gamma = settings.gamma_slider
        self.slider_sharp = settings.sharpness_slider
        self.chk_invert = settings.invert_check
        self.combo_material_bg = settings.material_combo
        self.combo_algo = settings.algorithm_combo
        self.spin_lmm = settings.lines_per_mm_spin
        self.combo_lmm_mode = settings.resolution_mode_combo
        self.spin_dpi = settings.dpi_spin
        self.lbl_focal_info = settings.focal_info_label
        self.stack_lmm_input = settings.resolution_stack
        self.lbl_resolution_quality = settings.resolution_quality_label
        self.view_preview_src = tab.source_view
        self.view_preview_dither = tab.dither_view
        self.tab_previews = tab
        # Résolution calée sur la focale du laser au départ, puis largeur du
        # panneau d'après ses textes (dont l'information sur la focale).
        self.on_lmm_mode_changed(settings.resolution_mode_combo.currentIndex())
        tab.fit_settings_width()

        # Origine lue par code (job_position_box.origin()) : génération, projets, profils.
        self.job_position_box = JobPositionBox()

    def _build_png2svg_tab(self):
        """Onglet « Vectorisation d'image », abonné à sa logique
        (Png2SvgController). Masqué au démarrage, ouvert depuis le menu
        Outils.
        """
        tab = Png2SvgTab()
        self.png2svg = Png2SvgController(
            self,
            self.layer_manager,
            bed_height=lambda: self.spin_machine_h.value(),
            add_to_vector_editor=self._add_objects_to_vector_editor,
        )
        tab.send_to_vector_requested.connect(self.png2svg.send_to_vector_editor)
        tab.image_changed.connect(self.update_image_actions_state)
        tab.fullscreen_requested.connect(self._toggle_fullscreen_png2svg)
        # Nom historique du widget de conversion, lu par les actions de la
        # barre d'outils sur l'image (rotation, suppression).
        self.png2svg_widget = tab.converter
        self.main_tabs_view.addTab(tab, tr("png2svg.tab_title"))
        self.tab_png2svg = tab

    def _build_separation_tab(self):
        """Onglet « Séparation Couleur / Verre », abonné à sa logique
        (SeparationMixin). Masqué au démarrage, ouvert depuis le menu Outils.
        """
        self._init_separation_state()
        tab = SeparationTab()
        tab.load_requested.connect(self.separation_load_image)
        tab.image_dropped.connect(self.separation_load_path)
        tab.tone_changed.connect(self._sep_schedule_push)
        tab.preview_changed.connect(self._sep_schedule_preview)
        tab.gain_test_requested.connect(self.separation_gain_test)
        tab.export_requested.connect(self.separation_export)
        tab.preview_tab_changed.connect(lambda _index: self._sep_render_current())
        tab.fullscreen_requested.connect(
            lambda: self._toggle_fullscreen_tab("tab_separation", "sep.tab_title"))
        # Noms historiques, lus par la logique de la séparation.
        self.sep_w = tab.plate_width_spin
        self.sep_h = tab.plate_height_spin
        self.sep_dp = tab.print_dpi_spin
        self.sep_gain = tab.gain_slider
        self.sep_sat = tab.saturation_slider
        self.sep_cla = tab.lightness_slider
        self.sep_mir_print = tab.mirror_print_check
        self.sep_dif = tab.diffusion_slider
        self.sep_int = tab.intensity_slider
        self.sep_lbl_file = tab.file_label
        self.sep_tabs = tab.preview_tabs
        self.sep_views = tab.preview_views
        self.tab_separation = tab
        self._sep_update_dpi_label()
        self.main_tabs_view.addTab(tab, tr("sep.tab_title"))

    def _build_vector_editor_tab(self):
        """Onglet « Éditeur vectoriel ». Partira dans ui/tabs/ quand Julien
        aura fini son travail sur le vectoriel."""
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
        btn_box_generator = QPushButton(tr("ui.vector_box_generator"))
        btn_box_generator.setToolTip(tr("ui.vector_box_generator_tip"))
        btn_box_generator.clicked.connect(self.open_box_generator)
        btn_puzzle_generator = QPushButton(tr("ui.vector_puzzle_generator"))
        btn_puzzle_generator.setToolTip(tr("ui.vector_puzzle_generator_tip"))
        btn_puzzle_generator.clicked.connect(self.open_puzzle_generator)
        btn_nesting = QPushButton(tr("ui.vector_nesting"))
        btn_nesting.setToolTip(tr("ui.vector_nesting_tip"))
        btn_nesting.clicked.connect(self.open_nesting)
        btn_edit_selected = QPushButton(tr("ui.vector_edit_selection"))
        btn_edit_selected.clicked.connect(self.edit_selected_vector_object)
        btn_rotate_selected = QPushButton(tr("ui.vector_rotate_90"))
        btn_rotate_selected.clicked.connect(self.rotate_selected_vector_object)
        btn_dup_selected = QPushButton(tr("ui.vector_duplicate"))
        btn_dup_selected.clicked.connect(self.duplicate_selected_vector_object)
        btn_del_selected = QPushButton(tr("ui.vector_delete"))
        btn_del_selected.clicked.connect(self.delete_selected_vector_object)
        btn_explode_path = QPushButton(tr("vector.explode_path"))
        btn_explode_path.clicked.connect(lambda: self.vector_canvas.explode_selected())
        btn_edit_nodes = QPushButton(tr("vector.edit_nodes"))
        btn_edit_nodes.clicked.connect(lambda: self.vector_canvas.enter_node_edit())
        btn_undo_vector = QPushButton(tr("ui.vector_undo"))
        btn_undo_vector.clicked.connect(lambda: self.vector_canvas.undo())
        btn_redo_vector = QPushButton(tr("ui.vector_redo"))
        btn_redo_vector.clicked.connect(lambda: self.vector_canvas.redo())
        btn_fullscreen_vector = QPushButton(tr("ui.vector_fullscreen"))
        btn_fullscreen_vector.setIcon(fullscreen_icon(self))
        btn_fullscreen_vector.clicked.connect(self.toggle_fullscreen_vector_editor)
        tab_vector_editor._fullscreen_control = btn_fullscreen_vector   # voir _show_fullscreen_control
        # Outils de dessin à la souris (ligne / rectangle / ellipse) + sélection
        self._vector_draw_buttons = {}
        btn_draw_select = QPushButton(tr("ui.vector_tool_select"))
        btn_draw_select.setCheckable(True)
        btn_draw_select.setChecked(True)
        btn_draw_select.setToolTip(tr("ui.vector_tool_select_tip"))
        btn_draw_select.clicked.connect(lambda: self.set_vector_draw_tool(None))
        btn_draw_line = QPushButton(tr("ui.vector_tool_line"))
        btn_draw_line.setCheckable(True)
        btn_draw_line.setToolTip(tr("ui.vector_tool_line_tip"))
        btn_draw_line.clicked.connect(lambda: self.set_vector_draw_tool("line"))
        btn_draw_rect = QPushButton(tr("ui.vector_tool_rect"))
        btn_draw_rect.setCheckable(True)
        btn_draw_rect.setToolTip(tr("ui.vector_tool_rect_tip"))
        btn_draw_rect.clicked.connect(lambda: self.set_vector_draw_tool("rect"))
        btn_draw_ellipse = QPushButton(tr("ui.vector_tool_ellipse"))
        btn_draw_ellipse.setCheckable(True)
        btn_draw_ellipse.setToolTip(tr("ui.vector_tool_ellipse_tip"))
        btn_draw_ellipse.clicked.connect(lambda: self.set_vector_draw_tool("ellipse"))
        btn_draw_measure = QPushButton(tr("ui.vector_tool_measure"))
        btn_draw_measure.setCheckable(True)
        btn_draw_measure.setToolTip(tr("ui.vector_tool_measure_tip"))
        btn_draw_measure.clicked.connect(lambda: self.set_vector_draw_tool("measure"))
        self._vector_draw_buttons = {
            None: btn_draw_select,
            "line": btn_draw_line,
            "rect": btn_draw_rect,
            "ellipse": btn_draw_ellipse,
            "measure": btn_draw_measure,
        }

        # Barres compactes : 2 rangées au lieu de 3 + marges réduites pour le canevas
        layout_vector_editor.setContentsMargins(4, 4, 4, 4)
        layout_vector_editor.setSpacing(4)

        # Rangée 1 : créer / importer / outils spéciaux + plein écran
        toolbar_vector = QHBoxLayout()
        toolbar_vector.setSpacing(4)
        toolbar_vector.addWidget(btn_add_text)
        toolbar_vector.addWidget(btn_add_shape)
        toolbar_vector.addWidget(btn_import_svg_vector)
        toolbar_vector.addWidget(btn_box_generator)
        toolbar_vector.addWidget(btn_puzzle_generator)
        toolbar_vector.addWidget(btn_nesting)
        toolbar_vector.addStretch()
        toolbar_vector.addWidget(btn_fullscreen_vector)
        layout_vector_editor.addLayout(toolbar_vector)

        # Rangée 2 : dessin + édition (une seule ligne)
        toolbar_vector_tools = QHBoxLayout()
        toolbar_vector_tools.setSpacing(4)
        for w in (
            btn_draw_select, btn_draw_line, btn_draw_rect, btn_draw_ellipse, btn_draw_measure,
        ):
            toolbar_vector_tools.addWidget(w)
        sep = QWidget()
        sep.setFixedWidth(8)
        toolbar_vector_tools.addWidget(sep)
        for w in (
            btn_edit_selected, btn_rotate_selected, btn_dup_selected, btn_del_selected,
            btn_explode_path, btn_edit_nodes, btn_undo_vector, btn_redo_vector,
        ):
            toolbar_vector_tools.addWidget(w)
        toolbar_vector_tools.addStretch()
        layout_vector_editor.addLayout(toolbar_vector_tools)


        align_box = QGroupBox(tr("ui.vector_align_box"))
        align_layout = QHBoxLayout()

        btn_align_left = QPushButton(tr("ui.vector_align_left"))
        btn_align_left.clicked.connect(lambda: self.align_vector_selection("left"))
        btn_align_center_h = QPushButton(tr("ui.vector_align_center_h"))
        btn_align_center_h.clicked.connect(lambda: self.align_vector_selection("center_h"))
        btn_align_right = QPushButton(tr("ui.vector_align_right"))
        btn_align_right.clicked.connect(lambda: self.align_vector_selection("right"))
        btn_align_top = QPushButton(tr("ui.vector_align_top"))
        btn_align_top.clicked.connect(lambda: self.align_vector_selection("top"))
        btn_align_middle_v = QPushButton(tr("ui.vector_align_middle_v"))
        btn_align_middle_v.clicked.connect(lambda: self.align_vector_selection("middle_v"))
        btn_align_bottom = QPushButton(tr("ui.vector_align_bottom"))
        btn_align_bottom.clicked.connect(lambda: self.align_vector_selection("bottom"))
        btn_distribute_h = QPushButton(tr("ui.vector_distribute_h"))
        btn_distribute_h.clicked.connect(lambda: self.distribute_vector_selection("h"))
        btn_distribute_v = QPushButton(tr("ui.vector_distribute_v"))
        btn_distribute_v.clicked.connect(lambda: self.distribute_vector_selection("v"))

        for b in (btn_align_left, btn_align_center_h, btn_align_right,
                  btn_align_top, btn_align_middle_v, btn_align_bottom,
                  btn_distribute_h, btn_distribute_v):
            align_layout.addWidget(b)

        align_layout.addStretch()

        self.chk_vector_snap = QCheckBox(tr("ui.vector_snap_enable"))
        self.chk_vector_snap.toggled.connect(self.set_vector_snap_enabled)
        align_layout.addWidget(self.chk_vector_snap)
        self.spin_vector_snap_step = QDoubleSpinBox()
        self.spin_vector_snap_step.setRange(0.1, 100.0)
        self.spin_vector_snap_step.setValue(5.0)
        self.spin_vector_snap_step.setSuffix(" mm")
        self.spin_vector_snap_step.valueChanged.connect(self.set_vector_snap_step)
        align_layout.addWidget(self.spin_vector_snap_step)

        align_box.setLayout(align_layout)
        align_box.setStyleSheet("QGroupBox { padding-top: 8px; margin-top: 4px; }")
        layout_vector_editor.addWidget(align_box)


        self.vector_canvas = VectorCanvasView(self.layer_manager)
        layout_vector_editor.addWidget(self.vector_canvas, 1)  # stretch: occupe l'espace restant

        # Propriétés compactes : 1 rangée position+calque ; 1 rangée taille/ancrage (formes uniquement)
        pos_box = QGroupBox(tr("ui.selection_props_box"))
        pos_form = QVBoxLayout(pos_box)
        pos_form.setContentsMargins(8, 6, 8, 6)
        pos_form.setSpacing(4)

        pos_row1 = QHBoxLayout()
        pos_row1.setSpacing(6)
        pos_row1.addWidget(QLabel(tr("ui.vector_x_mm")))
        self.spin_vec_x = QDoubleSpinBox(); self.spin_vec_x.setRange(-1000.0, 1000.0); self.spin_vec_x.setDecimals(2)
        self.spin_vec_x.setMaximumWidth(90)
        self.spin_vec_x.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_x)
        pos_row1.addWidget(QLabel(tr("ui.vector_y_mm")))
        self.spin_vec_y = QDoubleSpinBox(); self.spin_vec_y.setRange(-1000.0, 1000.0); self.spin_vec_y.setDecimals(2)
        self.spin_vec_y.setMaximumWidth(90)
        self.spin_vec_y.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_y)
        pos_row1.addWidget(QLabel(tr("ui.vector_rotation_deg")))
        self.spin_vec_rot = QDoubleSpinBox(); self.spin_vec_rot.setRange(-360.0, 360.0); self.spin_vec_rot.setDecimals(1)
        self.spin_vec_rot.setMaximumWidth(70)
        self.spin_vec_rot.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_rot)
        pos_row1.addWidget(QLabel(tr("ui.vector_layer")))
        self.combo_vec_layer = QComboBox()
        self.combo_vec_layer.setMinimumWidth(120)
        self.combo_vec_layer.currentIndexChanged.connect(self.on_vector_layer_spin_changed)
        pos_row1.addWidget(self.combo_vec_layer, 1)
        pos_form.addLayout(pos_row1)

        # Rangée taille + ancrage (masquée pour texte / SVG)
        self.pos_size_anchor_widget = QWidget()
        pos_row_size = QHBoxLayout(self.pos_size_anchor_widget)
        pos_row_size.setContentsMargins(0, 0, 0, 0)
        pos_row_size.setSpacing(6)
        pos_row_size.addWidget(QLabel(tr("ui.vector_width_mm")))
        self.spin_vec_w = QDoubleSpinBox()
        self.spin_vec_w.setRange(0.05, 5000.0)
        self.spin_vec_w.setDecimals(2)
        self.spin_vec_w.setSuffix(" mm")
        self.spin_vec_w.setMaximumWidth(100)
        self.spin_vec_w.valueChanged.connect(self.on_vector_size_spin_changed)
        pos_row_size.addWidget(self.spin_vec_w)
        pos_row_size.addWidget(QLabel(tr("ui.vector_height_mm")))
        self.spin_vec_h = QDoubleSpinBox()
        self.spin_vec_h.setRange(0.05, 5000.0)
        self.spin_vec_h.setDecimals(2)
        self.spin_vec_h.setSuffix(" mm")
        self.spin_vec_h.setMaximumWidth(100)
        self.spin_vec_h.valueChanged.connect(self.on_vector_size_spin_changed)
        pos_row_size.addWidget(self.spin_vec_h)
        self.chk_vec_anchor_lock = QCheckBox(tr("ui.vector_anchor_lock"))
        self.chk_vec_anchor_lock.setChecked(True)
        self.chk_vec_anchor_lock.setToolTip(tr("ui.vector_anchor_lock_tip"))
        pos_row_size.addWidget(self.chk_vec_anchor_lock)
        pos_row_size.addWidget(QLabel(tr("ui.vector_anchor")))
        self.combo_vec_anchor = QComboBox()
        for aid, key in (
            ("origin", "ui.vector_anchor_origin"),
            ("bl", "ui.vector_anchor_bl"),
            ("br", "ui.vector_anchor_br"),
            ("tl", "ui.vector_anchor_tl"),
            ("tr", "ui.vector_anchor_tr"),
        ):
            self.combo_vec_anchor.addItem(tr(key), aid)
        self.combo_vec_anchor.setCurrentIndex(0)
        self.combo_vec_anchor.setToolTip(tr("ui.vector_anchor_tip"))
        pos_row_size.addWidget(self.combo_vec_anchor)
        pos_row_size.addStretch()
        self.pos_size_anchor_widget.setVisible(False)
        pos_form.addWidget(self.pos_size_anchor_widget)

        self.lbl_vector_selection = QLabel(tr("ui.no_selection_label"))
        self.lbl_vector_selection.setStyleSheet("color: #9aa3b5; font-size: 12px;")
        pos_form.addWidget(self.lbl_vector_selection)

        pos_box.setEnabled(False)
        pos_box.setVisible(False)
        self.pos_box_vector = pos_box
        layout_vector_editor.addWidget(pos_box)
        # Le canevas prend tout l'espace vertical restant
        self.vector_canvas.selection_changed.connect(self.on_vector_selection_changed)
        self.vector_canvas.object_moved.connect(self.on_vector_object_moved)
        self.vector_canvas.edit_requested.connect(self.edit_vector_object)

        self.main_tabs_view.addTab(tab_vector_editor, tr("ui.tab_vector_editor"))
        self.tab_vector_editor = tab_vector_editor

    def _build_2d_preview_tab(self):
        """Onglet « Visualisation 2D G-Code », abonné à la génération.

        La génération dessine dans son graphique (plot_widget) et y place
        la tête du laser (gcode_position_marker).
        """
        tab = Preview2DTab(self.job_position_box)
        tab.display_options_changed.connect(
            self._on_preview_options_changed
        )
        tab.plot_clicked.connect(self._on_plot_clicked)
        # Séparateur aperçu / statistiques : position mémorisée (load_splitter_sizes).
        tab.splitter.splitterMoved.connect(self.save_splitter_sizes)
        tab.fullscreen_requested.connect(
            lambda: self._toggle_fullscreen_tab(
                "tab_vector_2d", "ui.tab_2d_preview"
            )
        )
        # Noms historiques, lus par la génération et la connexion au graveur.
        self.chk_flip_raster_preview = tab.flip_check
        self.chk_negative_raster_preview = tab.negative_check
        self.chk_hide_rapid_moves = tab.hide_rapid_check
        self.chk_optimize_path = tab.optimize_path_check
        self.plot_widget = tab.plot_widget
        self.gcode_position_marker = tab.position_marker
        self.info_text_item = tab.info_text_item
        self.main_tabs_view.addTab(tab, tr("ui.tab_2d_preview"))
        self.tab_vector_2d = tab

    def _build_console_tab(self):
        """Onglet « Console / G-Code », masqué au démarrage (menu Affichage)."""
        tab = ConsoleTab()
        tab.fullscreen_requested.connect(
            lambda: self._toggle_fullscreen_tab(
                "tab_console_gcode", "ui.tab_console_gcode",
                on_restored=self._add_console_close_button,
            )
        )
        # Nom historique de la console : toute l'application y écrit
        # (G-Code généré, messages du graveur, Stencil Studio…).
        self.txt_console = tab.console_edit
        self.main_tabs_view.addTab(tab, tr("ui.tab_console_gcode"))
        self.tab_console_gcode = tab
        self._add_console_close_button()

    def _add_console_close_button(self):
        """Croix sur l'onglet Console : le ferme en décochant « Affichage > Afficher/Masquer la
        console G-Code » (qui masque l'onglet et mémorise le choix). Remise au retour du plein
        écran : Qt supprime la croix quand l'onglet sort de la barre."""
        index = self.main_tabs_view.indexOf(self.tab_console_gcode)
        if index == -1:
            return
        button = TabCloseButton()
        button.clicked.connect(lambda: self.app_actions.gcode_console.setChecked(False))
        self.main_tabs_view.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, button)

    def _build_job_queue_tab(self):
        """Onglet « File d'attente », abonné à la file (JobQueueController),
        qui envoie ses jobs par la connexion au graveur (LaserControlMixin)."""
        tab = JobQueueTab()
        engraver = Engraver(
            is_connected=self.usb.is_connected,
            last_state=lambda: self.usb.last_state,
            confirm_homed=self._confirm_homed_before_job,
            start_stream=self._start_stream,
            stream_ended=self._stream_ended,
            pause_status_poll=self._pause_status_poll,
            resume_status_poll=self._resume_status_poll,
            jobs_finished=self._notify_job_finished,
        )
        self.job_queue = JobQueueController(
            tab,
            self,
            engraver,
            current_gcode=self.txt_console.toPlainText,
            log_to_console=self.txt_console.append,
            sent_log=self.machine_panel.sent_gcode_log,
        )
        tab.add_current_requested.connect(self.job_queue.add_current_gcode)
        tab.remove_selected_requested.connect(self.job_queue.remove_selected)
        tab.clear_requested.connect(self.job_queue.clear)
        tab.run_requested.connect(self.job_queue.run)
        tab.reordered.connect(self.job_queue.on_reordered)
        self.main_tabs_view.addTab(tab, tr("ui.tab_job_queue"))
        self.tab_job_queue = tab

    # -- Réglages machine : démarrage et fermeture

    def save_machine_settings(self):
        """Mémorise les réglages machine (profils, dimensions, résolution de
        l'image) pour les retrouver au prochain lancement, sans recharger de
        projet. Les calques sont rangés dans le profil de la machine active."""
        settings = QSettings("LaserStudioPro", "MachineConfig")
        settings.setValue("machine_bed_w_mm", self.spin_machine_w.value())
        settings.setValue("machine_bed_h_mm", self.spin_machine_h.value())
        settings.setValue("machine_focal_mm", self.spin_machine_focal.value())
        self.machines.store_memory()
        settings.setValue("machine_profiles_json", self.machines.to_json())
        name = self.machines.current_name()
        if name is not None:
            settings.setValue("last_machine_profile", name)
        settings.setValue("lmm_mode_index", self.combo_lmm_mode.currentIndex())
        settings.setValue("lmm_dpi_value", self.spin_dpi.value())
        settings.setValue("lmm_value", self.spin_lmm.value())

    def load_machine_settings(self):
        """Restaure au démarrage les réglages mémorisés par
        save_machine_settings."""
        settings = QSettings("LaserStudioPro", "MachineConfig")
        for key, spin in (("machine_bed_w_mm", self.spin_machine_w),
                          ("machine_bed_h_mm", self.spin_machine_h),
                          ("machine_focal_mm", self.spin_machine_focal)):
            value = settings.value(key, None)
            if value is not None:
                try:
                    spin.setValue(float(value))
                except (TypeError, ValueError):
                    pass
        # Comme à chaque validation de profil : les calques suivent la focale
        # dès le démarrage.
        self.layers_tab.link_all_to_focal()

        self.machines.load(
            settings.value("machine_profiles_json", ""),
            settings.value("last_machine_profile", None),
            {"name": "Machine par défaut", "w": self.spin_machine_w.value(),
             "h": self.spin_machine_h.value()},
        )

        lmm_value = settings.value("lmm_value", None)
        dpi_value = settings.value("lmm_dpi_value", None)
        mode_index = settings.value("lmm_mode_index", None)
        for value, spin in ((lmm_value, self.spin_lmm), (dpi_value, self.spin_dpi)):
            if value is not None:
                try:
                    spin.blockSignals(True)
                    spin.setValue(float(value))
                    spin.blockSignals(False)
                except (TypeError, ValueError):
                    pass
        if mode_index is not None:
            try:
                self.combo_lmm_mode.setCurrentIndex(int(mode_index))
            except (TypeError, ValueError):
                pass
        # Recalcule dans tous les cas l'écart lignes/mm et la pastille de
        # qualité à partir de l'état chargé, quel que soit le mode.
        self.on_lmm_mode_changed(self.combo_lmm_mode.currentIndex())
        # À partir d'ici seulement, un changement de calque est mémorisé.
        self.machines.persist_ready = True

    # -- Profils machine : champs de la fenêtre (voir ProfileFields)

    def _capture_machine_profile(self):
        """Champs d'un profil machine : pages Paramètres du graveur et
        Configuration GRBL, position du job, matériaux (une copie, pour que
        modifier ceux d'un profil n'affecte pas les autres) et calques."""
        return {
            **self.tab_machine_params.profile_values(),
            **self.job_position_box.profile_values(),
            **self.tab_grbl_config.profile_values(),
            "materials_db": dict(self.materials.materials),
            "layers": self.layer_manager.to_list(),
        }

    def _apply_machine_profile(self, profile):
        """Réapplique les champs d'un profil (les calques à part)."""
        self.tab_machine_params.apply_profile_values(profile)
        self.job_position_box.apply_profile_values(profile)
        self.tab_grbl_config.apply_profile_values(profile)
        # Matériaux propres à cette machine (repli sur la base par défaut
        # pour un profil enregistré avant cette liaison).
        self.materials.set_materials(
            dict(profile.get("materials_db", DEFAULT_MATERIALS_DB)),
            block_signals=True)
        self.materials.apply_selected()

    def _machine_memory(self):
        """Mémorisé en continu dans le profil actif : calques et réglages
        mécaniques (décalage des lignes retour, surbalayage)."""
        return {"layers": self.layer_manager.to_list(),
                **self.tab_grbl_config.mechanical_values()}

    def _apply_profile_layers(self, saved_layers, full=False):
        """Réapplique les calques mémorisés (voir apply_saved_layers), puis
        met l'onglet Calques à jour."""
        if not apply_saved_layers(self.layer_manager, saved_layers, full):
            return
        self.layers_tab.refresh()
        # Les calques liés à la focale suivent la focale de CETTE machine.
        self.layers_tab.link_all_to_focal()

    def _after_machine_profile_selected(self):
        """Après un changement de profil : lignes/mm et DPI suivent la focale
        (même si elle n'a pas changé, ou si le profil n'en a pas), et la
        qualité des calques est recalculée."""
        self._apply_focal_to_lmm()
        self.layers_tab.refresh_focal_quality()

    # -- Projet : état de la fenêtre

    def _capture_project(self):
        """État du projet (pour ProjectController) : réglages de l'image,
        machine, gravure et découpe, matériaux, calques, objets vectoriels ;
        et l'image source (PIL), encodée par le contrôleur."""
        data = {
            "w_mm": self.spin_w.value(),
            "h_mm": self.spin_h.value(),
            "machine_bed_w_mm": self.spin_machine_w.value(),
            "machine_bed_h_mm": self.spin_machine_h.value(),
            "origin_pos": self.job_position_box.origin(),
            "offset_x": self.spin_off_x.value(),
            "offset_y": self.spin_off_y.value(),
            "bright": self.slider_bright.value(),
            "contrast": self.slider_contrast.value(),
            "gamma": self.slider_gamma.value(),
            "sharp": self.slider_sharp.value(),
            "safe_cut_order": self.chk_safe_cut_order.isChecked(),
            "invert": self.chk_invert.isChecked(),
            "material_bg": self.get_material_bg(),
            "mirror_h": self.app_actions.mirror_h.isChecked(),
            "mirror_v": self.app_actions.mirror_v.isChecked(),
            "algo": self.combo_algo.currentText(),
            "lmm": self.spin_lmm.value(),
            "speed_engrave": self.engrave_speed,
            "power_engrave": self.engrave_power,
            "enable_cut": self.cut_enabled,
            "speed_cut": self.cut_speed,
            "power_cut": self.cut_power,
            "passes_cut": self.cut_passes,
            "materials_db": self.materials.materials,
            "raw_image_b64": None,  # rempli par ProjectController
            "svg_path": self.loaded_svg_path,
            "layers": self.layer_manager.to_list(),
            "vector_objects": (
                self.vector_canvas.serialize_objects()
                if hasattr(self, "vector_canvas") else []
            ),
        }
        return data, self.raw_image

    def _restore_project(self, data, image):
        """Réapplique un projet ouvert (voir _capture_project). Les clés
        absentes (anciens projets) prennent leur valeur par défaut."""
        # Le projet impose ses propres réglages matière / négatif / miroir :
        # l'état mémorisé par l'onglet Séparation est oublié, sinon un
        # chargement d'image ultérieur le « rendrait » par-dessus.
        self._sep_glass_settings_active = False
        self._sep_prev_image_settings = None

        self.spin_w.setValue(data.get("w_mm", 100.0))
        self.spin_h.setValue(data.get("h_mm", 100.0))
        self.spin_machine_w.setValue(data.get("machine_bed_w_mm", self.spin_machine_w.value()))
        self.spin_machine_h.setValue(data.get("machine_bed_h_mm", self.spin_machine_h.value()))
        self.job_position_box.set_origin(data.get("origin_pos", ORIGIN_BOTTOM_LEFT))
        self.spin_off_x.setValue(data.get("offset_x", 0.0))
        self.spin_off_y.setValue(data.get("offset_y", 0.0))

        self.slider_bright.setValue(data.get("bright", 0))
        self.slider_contrast.setValue(data.get("contrast", 0))
        self.slider_gamma.setValue(data.get("gamma", 100))
        self.slider_sharp.setValue(data.get("sharp", 0))
        self.chk_safe_cut_order.setChecked(data.get("safe_cut_order", True))
        # Anciens projets sans "material_bg" : déduit du négatif sauvegardé.
        self.set_material_bg(data.get("material_bg", "dark" if data.get("invert", False) else "light"))
        self.chk_invert.setChecked(data.get("invert", False))
        self.app_actions.mirror_h.setChecked(data.get("mirror_h", False))
        self.app_actions.mirror_v.setChecked(data.get("mirror_v", False))
        self.combo_algo.setCurrentText(data.get("algo", "Floyd-Steinberg"))
        self.spin_lmm.setValue(data.get("lmm", 10.0))

        self.set_engrave_settings(data.get("speed_engrave", 2000), data.get("power_engrave", 30))
        self.cut_enabled = bool(data.get("enable_cut", False))
        self.set_cut_settings(data.get("speed_cut", 300), data.get("power_cut", 90),
                              data.get("passes_cut", 2))

        if "materials_db" in data:
            self.materials.set_materials(data["materials_db"])

        if image is not None:
            self.raw_image = image
            self.display_source_image()

        self.loaded_svg_path = data.get("svg_path")

        if "layers" in data:
            self.layer_manager.load_list(data["layers"])
            self.layers_tab.refresh()
        if hasattr(self, "vector_canvas"):
            self.vector_canvas.load_objects(data.get("vector_objects"))
            self.update_vector_work_area()

        self.update_image_processing()

    # -- Événements de la fenêtre

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_autosave_recovery_pending", False):
            self._autosave_recovery_pending = False
            QTimer.singleShot(0, self.project.offer_autosave_recovery)

    def closeEvent(self, event):
        if hasattr(self, "_stop_status_poll"):
            self._stop_status_poll()
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
            # Enregistrement annulé ou en échec : on reste ouvert, rien n'est perdu.
            if not self.project.save():
                event.ignore()
                return
            self._flush_background_writes()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Fermeture volontaire sans enregistrer : la sauvegarde automatique ne
            # doit pas être proposée en récupération au prochain démarrage.
            self.project.discard_autosave()
            self._flush_background_writes()
            event.accept()
        else:
            event.ignore()

    def _flush_background_writes(self):
        """Attend (au plus quelques secondes) la fin des sauvegardes en
        arrière-plan — file d'attente, sauvegarde automatique — avant que le
        processus ne s'arrête, sinon une écriture en cours serait perdue."""
        try:
            from laser_common.files import get_background_writer
            get_background_writer().wait_idle(10)
        except Exception:
            pass

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.load_image_from_path(file_path)
                break
            if file_path.lower().endswith(('.svg', '.dxf')) and hasattr(self, "_import_vector_file"):
                self._import_vector_file(file_path)
                break

    # -- État de la fenêtre : panneau machine, séparateur, onglets

    def _on_main_tab_changed(self, idx):
      if hasattr(self, 'tab_separation') and self.main_tabs_view.widget(idx) == self.tab_separation:
          self.separation_refresh_if_dirty()

    def _job_in_progress(self):
        streamer = getattr(self, "streamer", None)
        try:
            return bool(streamer is not None and streamer.isRunning())
        except RuntimeError:
            return False

    def _update_bottom_panel_visibility(self, *_args):
        panel = getattr(self, "center_bottom_widget", None)
        if panel is None:
            return
        current = self.main_tabs_view.currentWidget()
        tabs_with_panel = (self.tab_vector_2d, self.tab_console_gcode, self.tab_job_queue)
        show = self._job_in_progress() or any(current is t for t in tabs_with_panel)
        if show and panel.isHidden():
            panel.setVisible(True)
            sizes = getattr(self, "_bottom_panel_sizes", None)
            if sizes:
                QTimer.singleShot(0, lambda s=sizes: self.center_v_splitter.setSizes(s))
        elif not show and not panel.isHidden():
            sizes = self.center_v_splitter.sizes()
            if all(v > 0 for v in sizes):
                self._bottom_panel_sizes = sizes
            panel.setVisible(False)

    def save_splitter_sizes(self, *_args):
        settings = QSettings("LaserStudioPro", "UIConfig")
        if hasattr(self, "center_v_splitter"):
            panel = getattr(self, "center_bottom_widget", None)
            if panel is not None and panel.isHidden():
                sizes = getattr(self, "_bottom_panel_sizes", None)
            else:
                sizes = self.center_v_splitter.sizes()
            if sizes and all(v > 0 for v in sizes):
                settings.setValue("center_v_splitter_sizes", sizes)
        # Aperçu 2D / colonne de droite (position du job, statistiques) : un côté peut être replié.
        preview = getattr(self, "tab_vector_2d", None)
        if preview is not None:
            sizes = preview.splitter.sizes()
            if sum(sizes) > 0:
                settings.setValue("preview_2d_side_sizes", sizes)

    def load_splitter_sizes(self):
        settings = QSettings("LaserStudioPro", "UIConfig")
        # Tailles de l'ancienne colonne de gauche, supprimée : plus utilisées.
        settings.remove("main_splitter_sizes")
        settings.remove("left_v_splitter_sizes")
        center_v_sizes = settings.value("center_v_splitter_sizes", None)
        if center_v_sizes and hasattr(self, "center_v_splitter"):
            try:
                loaded_sizes = [int(s) for s in center_v_sizes]
                if all(v > 0 for v in loaded_sizes):
                    self._bottom_panel_sizes = loaded_sizes
                    self.center_v_splitter.setSizes(loaded_sizes)
            except (TypeError, ValueError):
                pass
        # Moitié / moitié d'une version précédente : remplacé par la colonne étroite par défaut.
        settings.remove("preview_2d_splitter_sizes")
        preview_sizes = settings.value("preview_2d_side_sizes", None)
        preview = getattr(self, "tab_vector_2d", None)
        if preview_sizes and preview is not None:
            try:
                loaded_sizes = [int(s) for s in preview_sizes]
                if len(loaded_sizes) == 2 and min(loaded_sizes) >= 0 and sum(loaded_sizes) > 0:
                    preview.splitter.setSizes(loaded_sizes)
            except (TypeError, ValueError):
                pass

    # -- Fenêtres annexes : plein écran d'un onglet, réglages, messages

    def _toggle_fullscreen_png2svg(self):
        """Plein écran de « Vectorisation d'image », avec son propre titre."""
        self._open_tab_fullscreen(
            self.tab_png2svg,
            tr("png2svg.fullscreen_title"),
            tr("png2svg.close_fullscreen"),
            tr("png2svg.tab_title"),
        )

    def _add_objects_to_vector_editor(self, objects):
        """Ajoute des objets au canevas vectoriel (annulable d'un coup),
        affiche l'éditeur et centre la vue sur eux."""
        self.vector_canvas.push_undo_snapshot()
        new_items = [self.vector_canvas.add_object(obj) for obj in objects]
        self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
        self.vector_canvas.request_recenter(new_items)

    def _toggle_fullscreen_image_tab(self):
        """Plein écran de « Graver une image ». Ses réglages (ancien onglet Image & Filtres) sont
        maintenant dans l'onglet lui-même : le plein écran commun suffit."""
        self._toggle_fullscreen_tab("tab_previews", "ui.tab_image_tracing")

    @staticmethod
    def _show_fullscreen_control(tab_widget, visible):
        """Masque le bouton « Plein écran » d'un onglet pendant qu'il est affiché en plein écran,
        et le réaffiche quand il revient dans les onglets (voir les fonctions *fullscreen*)."""
        control = getattr(tab_widget, "_fullscreen_control", None)
        if control is not None:
            control.setVisible(visible)

    def _toggle_fullscreen_tab(self, tab_attr, title_key, on_restored=None):
        """Plein écran d'un onglet, avec le titre de l'onglet."""
        tab_widget = getattr(self, tab_attr, None)
        if tab_widget is None:
            return
        self._open_tab_fullscreen(
            tab_widget, tr(title_key), tr("vector.close_fullscreen"),
            tr(title_key), on_restored=on_restored)

    def _open_tab_fullscreen(self, tab_widget, window_title, close_text, tab_title,
                             on_restored=None):
        """Sort `tab_widget` des onglets dans une FullscreenWindow, et l'y remet
        à la même place quand elle se ferme (puis appelle `on_restored`).
        Sans effet si l'onglet est déjà en plein écran."""
        index = self.main_tabs_view.indexOf(tab_widget)
        if index == -1:
            return
        window = FullscreenWindow(self, tab_widget, window_title, close_text)
        self._show_fullscreen_control(tab_widget, False)

        def restore():
            self._show_fullscreen_control(tab_widget, True)
            self.main_tabs_view.insertTab(index, tab_widget, tab_title)
            self.main_tabs_view.setCurrentWidget(tab_widget)
            tab_widget.setVisible(True)
            tab_widget.updateGeometry()
            self.main_tabs_view.update()
            self.update()
            self.repaint()
            if on_restored is not None:
                on_restored()

        window.content_released.connect(restore)
        window.show_maximized()

    def show_settings_window(self, kind):
        """Ouvre (ou ramène au premier plan) la fenêtre « Machine & Profils » (kind="machine") ou
        « Configuration GRBL » (kind="grbl"). Créée à la première demande, puis réutilisée."""
        windows = self.__dict__.setdefault("_settings_windows", {})
        if kind not in windows:
            page, title = {
                "machine": (getattr(self, "tab_machine_profiles", None), tr("tab.machine_profiles")),
                "grbl": (getattr(self, "tab_grbl_config", None), tr("tab.grbl_config")),
                "machine_params": (getattr(self, "tab_machine_params", None), tr("tab.machine_params")),
                "test_matrix": (getattr(self, "tab_matrix", None), tr("tab.test_matrix")),
            }[kind]
            if page is None:
                return
            windows[kind] = SettingsWindow(self, title, page, kind)
        windows[kind].bring_to_front()

    def show_status_message(self, text, tooltip=None):
        """Raccourci vers StatusBar.show_info, utilisé par les mixins et Stencil Studio."""
        self.statusBar().show_info(text, tooltip)
