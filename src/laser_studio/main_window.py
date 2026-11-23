"""Fenêtre principale de l'application.

FullLaserStudio construit la fenêtre (init_ui), branche les signaux de ses
panneaux et gère ses événements (fermeture, glisser-déposer) ; les mixins
apportent le contenu des onglets et la logique.
"""
from contextlib import contextmanager
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton, QScrollArea, QSplitter, QTabWidget,
                             QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QStandardItemModel

from laser_studio.core.constants import ORIGIN_BOTTOM_LEFT
from laser_studio.i18n import tr
from laser_studio.controllers.engraver import EngraverController
from laser_studio.controllers.job import JobController
from laser_studio.controllers.vector_editor import VectorEditorController
from laser_studio.ui.vector_editor.properties_panel import PropertiesWidgets, VectorPropertiesPanel
from laser_studio.ui.user_dialogs import UserDialogs
from laser_studio.ui.machine import MachinePanel
from laser_studio.ui.machine.connection import port_help_dialog
from laser_studio.ui.machine.job_position import JobPositionBox
from laser_studio.ui.settings.grbl_config import GrblConfigPage
from laser_studio.ui.settings.machine_params import MachineParamsPage
from laser_studio.ui.settings.test_matrix import TestMatrixPage
from laser_studio.ui.statusbar import StatusBar
from laser_studio.ui.tabs.console import ConsoleTab
from laser_studio.ui.tabs.image import ImageTab
from laser_studio.ui.tabs.job_queue import JobQueueTab
from laser_studio.ui.tabs.layers import LayersTab
from laser_studio.ui.tabs.png2svg import Png2SvgTab
from laser_studio.ui.tabs.preview_2d import Preview2DTab
from laser_studio.ui.tabs.separation import SeparationTab
from laser_studio.ui.utils import palette_icon
from laser_studio.ui.widgets import FloatingToolBar

from laser_studio.controllers.job_queue import Engraver, JobQueueController
from laser_studio.controllers.materials import (DEFAULT_MATERIALS_DB, MaterialsController,
                                                apply_material_to_layers, capture_material_layers)
from laser_studio.controllers.layer_memory import apply_saved_layers
from laser_studio.controllers.machine_profiles import MachineProfilesController, ProfileFields
from laser_studio.controllers.matrix_image import MatrixImageController
from laser_studio.controllers.library import LibraryController
from laser_studio.controllers.png2svg import Png2SvgController
from laser_studio.controllers.separation import SeparationController
from laser_studio.controllers.project import ProjectController
from laser_studio.controllers.machine_connection import MachineConnection
from laser_studio.models.vector_document import VectorDocument
from laser_studio.ui.vector_editor.canvas import VectorCanvasView
from laser_studio.models.image_settings import ImageSettings, ImageSettingsHistory
from laser_studio.models.layers import LayersModel
from laser_studio.models.machine import MachineConfig
from laser_studio.models.separation import SeparationSettings
from laser_studio.models.grbl import LASER_COMMANDS, GrblConfig
from laser_studio.ui.binding import bind

from laser_studio.ui.app.window_controller import WindowControllerMixin
from laser_studio.image_processing_mixin import ImageProcessingMixin


class FullLaserStudio(QMainWindow, WindowControllerMixin,
                       ImageProcessingMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laser Studio Pro - GRBL Controller")
        self.resize(1600, 980)
        
        self.setAcceptDrops(True)
        
        # Dialogue avec le graveur (port, threads, état « référencé ») ; son
        # pilotage (connexion, jog, envoi d'un job, configuration $$) est dans
        # self.engraver, construit plus bas.
        self.connection = MachineConnection(parent=self)
        # Boîtes de dialogue des contrôleurs (messages, confirmations, fichiers),
        # centrées sur la fenêtre : les contrôleurs n'ouvrent pas de QMessageBox
        # eux-mêmes, ce qui permet de les tester sans fenêtre.
        self.dialogs = UserDialogs(self)
        self.raw_image = None
        self.processed_array = None
        self.loaded_svg_path = None
        # Modèle des calques (models/layers.py) : seule source des réglages des calques.
        self.layer_manager = LayersModel(self)
        # Document de l'éditeur vectoriel (objets, annuler / refaire, presse-papiers) ;
        # le canevas (self.vector_canvas) en est la vue.
        self.vector_document = VectorDocument(self)
        # Réglages de la machine (plateau, spot, limites) et configuration GRBL : les pages de
        # réglages y sont liées (ui/binding.py), la logique les lit ici.
        self.machine = MachineConfig(self)
        self.grbl = GrblConfig(self)
        # > 0 : les changements de calques ne sont pas recopiés dans le matériau choisi (profil
        # machine, projet ou matériau en cours d'application, voir _store_layers_in_material).
        self._material_autosave_pause = 0
        self.block_aspect_signal = False
        self.img_worker = None
        self.pending_reprocess = False
        # Réglages de tramage de « Graver une image » et leur annulation (Ctrl+Z / Ctrl+Y) : les
        # champs de l'onglet y sont liés (_bind_image_settings), la logique les lit ici.
        self.image_settings = ImageSettings(self)
        self.image_history = ImageSettingsHistory(self.image_settings)

        # Job : paramètres, contrôles avant génération, génération du G-Code
        # (thread), estimation, export / import, matrice de test. Il lit l'état
        # de l'interface par les fonctions ci-dessous ; la fenêtre affiche ses
        # résultats (WindowControllerMixin : console, aperçu 2D).
        self.job = JobController(
            self.layer_manager, self.grbl, self.machine, self.image_settings, self.dialogs,
            geometry=self._job_geometry,
            image=lambda: self.processed_array,
            svg_path=lambda: self.loaded_svg_path,
            vector_objects=lambda: self.vector_document.objects,
            optimize_path=lambda: self.chk_optimize_path.isChecked(),
            lines_mm=lambda: self.spin_lmm.value(),
            material_summary=self.material_summary_text,
            parent=self,
        )
        self.job.started.connect(self.on_gcode_generation_started)
        self.job.progress.connect(self.on_gcode_generation_progress)
        self.job.generated.connect(self.on_gcode_generated)
        self.job.failed.connect(self.on_gcode_generation_error)
        self.job.imported.connect(self.show_imported_gcode)
        self.job.log.connect(self.log_message)
        self.job.status.connect(self.show_status_message)
        # Graveur : port, connexion, pilotage, envoi des jobs, configuration GRBL.
        self.engraver = EngraverController(
            self.connection, self.grbl, self.dialogs,
            selected_port=lambda: self.machine_panel.connection_panel.selected_port(),
            current_gcode=lambda: self.txt_console.toPlainText(),
            job_geometry=self._job_geometry,
            set_homing_available=self._set_homing_available,
            parent=self,
        )
        
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
            log_to_console=self.log_message,
            dialogs=self.dialogs,
        )
        self.autosave_timer = QTimer()
        self.autosave_timer.setInterval(5 * 60 * 1000)
        self.autosave_timer.timeout.connect(self.project.autosave)
        self.autosave_timer.start()

        self.init_ui()
        self._bind_image_settings()
        self._connect_machine_signals()
        self.load_machine_settings()
        self.load_splitter_sizes()
        self.restore_remembered_algorithm()
        self.update_vector_work_area()
        self.engraver.refresh_ports()
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
        # ou Affichage pour la console G-Code et la file d'attente (set_optional_tab_visible).
        for tab in (self.tab_separation, self.tab_png2svg, self.tab_console_gcode):
            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)
        self._add_image_floating_toolbars()
        self._update_bottom_panel_visibility()
        self.update_image_actions_state()
        # Console G-Code : affichée ou non comme à la dernière fermeture (masquée la première fois).
        self.app_actions.gcode_console.setChecked(self.gcode_console_was_visible())
        # File d'attente : affichée, sauf si elle a été masquée à la dernière utilisation.
        self.app_actions.job_queue.setChecked(self.job_queue_was_visible())
        if not self.app_actions.job_queue.isChecked():
            self.set_job_queue_visible(False)

        # Largeur minimale EXPLICITE du centre. Sans elle, la largeur minimale serait calculée
        # d'après le contenu : la barre d'outils de l'éditeur vectoriel (11 boutons, ~1500 px) et la
        # rangée d'alignement imposeraient environ 1500 px à la fenêtre. Trop étroit, le centre se
        # contente de serrer ses boutons.
        center_widget.setMinimumWidth(480)
        self.center_v_splitter.splitterMoved.connect(self.save_splitter_sizes)

        main_layout.addWidget(center_widget)

    def _add_image_floating_toolbars(self):
        """Barre flottante en haut des aperçus d'image : mêmes actions que celles de l'ancienne
        barre d'outils (état actif / coché partagé, voir update_image_actions_state).

        « Graver une image » : annuler / refaire, pivoter, miroirs, réinitialiser, supprimer.
        Séparation : pivoter, miroirs, réinitialiser (réglages image et miroirs qu'elle reprend),
        supprimer. PNG ⇒ SVG : pivoter, supprimer (miroirs et réglages image n'y servent pas)."""
        a = self.app_actions
        rotate = [a.image_rotate_left, a.image_rotate_right]
        mirrors = [a.mirror_h, a.mirror_v]
        self.image_floating_toolbar = FloatingToolBar(
            [a.image_undo, a.image_redo, None, *rotate, None, *mirrors, None, a.image_reset, a.image_delete],
            self.tab_previews.preview_area)
        self.separation_floating_toolbar = FloatingToolBar(
            [*rotate, None, *mirrors, None, a.image_reset, a.image_delete],
            self.tab_separation.preview_tabs, top_margin=34)
        self.png2svg_floating_toolbar = FloatingToolBar(
            [*rotate, None, a.image_delete], self.png2svg_widget.splitter)

    def _build_machine_panel(self):
        """Panneau machine sous les onglets, abonné à la logique de la machine.

        Les sous-panneaux émettent les demandes de l'utilisateur ; la fenêtre
        les transmet au contrôleur du graveur (self.engraver). La vitesse maximale
        du graveur (`spin_machine_max_speed`, qui doit déjà exister) borne le
        curseur de vitesse du pilotage. Renvoie la zone de défilement qui
        contient le panneau, placée sous les onglets dans `center_v_splitter`.
        """
        self.machine_panel = MachinePanel(
            QStandardItemModel(self),
            self.machine.max_speed,
        )
        connection = self.machine_panel.connection_panel
        engraver = self.engraver
        connection.refresh_requested.connect(engraver.refresh_ports)
        connection.help_requested.connect(lambda: port_help_dialog(self).exec())
        connection.connect_requested.connect(engraver.toggle_connection)
        jog = self.machine_panel.jog_panel
        jog.jog_requested.connect(engraver.jog)
        jog.home_requested.connect(engraver.home)
        jog.pause_requested.connect(engraver.pause)
        jog.resume_requested.connect(engraver.resume)
        jog.reset_requested.connect(engraver.reset)
        jog.emergency_stop_requested.connect(engraver.emergency_stop)
        jog.send_job_requested.connect(lambda: engraver.send_job())
        self.tab_machine_params.max_speed_changed.connect(jog.set_max_speed)

        job_actions = self.machine_panel.job_actions_panel
        job_actions.frame_requested.connect(engraver.frame)
        job_actions.set_work_zero_requested.connect(engraver.set_work_zero)
        job_actions.go_to_work_zero_requested.connect(engraver.go_to_work_zero)
        job_actions.repeat_job_requested.connect(engraver.repeat_last_job)

        connection.unlock_requested.connect(engraver.unlock)
        connection.command_submitted.connect(engraver.send_console_command)
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
            dialogs=self.dialogs,
        )
        page.profile_selected.connect(self.machines.on_selected)
        page.new_profile_requested.connect(self.machines.new_profile)
        page.update_profile_requested.connect(self.machines.update_profile)
        page.delete_profile_requested.connect(self.machines.delete_profile)
        page.bed_size_changed.connect(self.update_vector_work_area)
        page.focal_changed.connect(self._on_machine_focal_changed)
        # Champs liés au modèle des réglages machine (self.machine), que lit la logique.
        for widget, field in ((page.bed_width_spin, "bed_w"), (page.bed_height_spin, "bed_h"),
                              (page.focal_spin, "focal"), (page.max_speed_spin, "max_speed"),
                              (page.accel_spin, "accel")):
            bind(widget, self.machine, field)
        # Noms historiques des champs (Stencil Studio, focus sur le spot…).
        self.combo_machine_profile = page.profile_combo
        self.spin_machine_w = page.bed_width_spin
        self.spin_machine_h = page.bed_height_spin
        self.spin_machine_focal = page.focal_spin
        self.spin_machine_max_speed = page.max_speed_spin
        self.spin_machine_accel = page.accel_spin
        self.tab_machine_params = page

    def _build_grbl_config_page(self):
        """Page « Configuration GRBL », abonnée au dialogue avec le graveur.

        Affichée dans une fenêtre du menu Paramètres (show_settings_window).
        """
        page = GrblConfigPage()
        page.bidir_test_requested.connect(self.job.generate_bidir_test)
        # Décalage aller/retour : mémorisé dans le profil de la machine.
        page.scan_offset_changed.connect(self.machines.schedule_persist)
        # « Inclure $H » : mémorisé aussi (décoché d'office pour un graveur
        # sans homing, il le reste aux démarrages suivants).
        page.homing_changed.connect(self.machines.schedule_persist)
        page.read_settings_requested.connect(self.engraver.read_settings)
        page.send_settings_requested.connect(self.engraver.send_settings)
        page.export_settings_requested.connect(self.engraver.export_settings)
        page.import_settings_requested.connect(self.engraver.import_settings)
        page.link_settings_to_profile_requested.connect(
            self.machines.update_profile
        )
        # Champs liés au modèle de la configuration GRBL (self.grbl), que lit la logique.
        bind(page.laser_cmd_combo, self.grbl, "laser_cmd",
             to_widget=LASER_COMMANDS.index, from_widget=lambda i: LASER_COMMANDS[max(i, 0)])
        for widget, field in ((page.smax_spin, "smax"), (page.homing_check, "homing_enabled"),
                              (page.overscan_check, "overscan_enabled"),
                              (page.safe_cut_order_check, "safe_cut_order"),
                              (page.overscan_mode_combo, "overscan_mode"),
                              (page.overscan_dist_spin, "overscan_dist_mm"),
                              (page.overscan_pct_spin, "overscan_pct"),
                              (page.scan_offset_spin, "scan_offset_mm"),
                              (page.start_gcode_edit, "start_gcode"),
                              (page.end_gcode_edit, "end_gcode"),
                              (page.grbl_settings_edit, "grbl_settings")):
            bind(widget, self.grbl, field)
        # Noms historiques des champs (homing grisé selon $22, chargement de projet…).
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
            dialogs=UserDialogs(page),          # centrées sur la fenêtre de la matrice
        )
        page.choose_image_requested.connect(self.matrix_image.choose_image)
        page.use_loaded_image_requested.connect(
            self.matrix_image.use_loaded_image
        )
        page.image_test_toggled.connect(self.matrix_image.on_image_test_toggled)
        # Nom historique : décochée et grisée avec chk_homing quand le
        # graveur n'a pas de homing ($22=0, voir EngraverController).
        self.chk_mat_homing = page.homing_check
        self.tab_matrix = page

    def _job_geometry(self):
        """Taille et position du job, lues dans l'interface (voir JobController)."""
        return {
            'width_mm': self.spin_w.value(),
            'height_mm': self.spin_h.value(),
            'origin_pos': self.job_position_box.origin(),
            'offset_x': self.spin_off_x.value(),
            'offset_y': self.spin_off_y.value(),
        }

    def _loaded_image_and_width(self):
        """(image, largeur en mm) de « Graver une image », ou None."""
        if getattr(self, "raw_image", None) is None:
            return None
        return self.raw_image, self.spin_w.value()

    def _job_settings(self):
        """Réglages en cours, au format d'un matériau (voir MaterialsController) : ceux de chaque
        calque, et les anciennes valeurs de gravure image et de découpe SVG."""
        return {
            "sp_e": self.job.engrave_speed,
            "pw_e": self.job.engrave_power,
            "sp_c": self.job.cut_speed,
            "pw_c": self.job.cut_power,
            "pass_c": self.job.cut_passes,
            "layers": capture_material_layers(self.layer_manager),
        }

    def _apply_job_settings(self, material, layers=True):
        """Applique un matériau : découpe de l'ancien mode SVG, puis (layers=True) les réglages
        des calques. La gravure image n'a plus de réglage à part : elle suit le calque de gravure
        (un ancien matériau sp_e / pw_e est repris dans ce calque, voir complete_material).
        layers=False : profil machine qui vient de restaurer ses propres calques, à ne pas
        écraser. Le tableau, le canevas et le profil suivent le modèle des calques."""
        self.job.set_cut_settings(material["sp_c"], material["pw_c"], material["pass_c"])
        if layers:
            with self._material_autosave_paused():
                apply_material_to_layers(self.layer_manager, material)

    def _build_layers_tab(self):
        """Onglet « Calques », abonné à la logique des calques.

        Il est placé dans les onglets par init_ui, entre l'éditeur
        vectoriel et l'aperçu 2D.
        """
        materials = dict(DEFAULT_MATERIALS_DB)
        self.layers_tab = LayersTab(
            self.layer_manager,
            materials.keys(),
            focal_getter=lambda: self.machine.focal,
        )
        self.layer_manager.changed.connect(self.on_layers_changed)
        # Profils matériaux (barre d'outils de l'onglet) : un matériau mémorise les réglages des
        # calques ; le choisir dans la liste met le tableau à jour (_apply_job_settings).
        self.materials = MaterialsController(
            self,
            self.layers_tab.material_combo,
            materials,
            current_settings=self._job_settings,
            apply_settings=self._apply_job_settings,
            dialogs=self.dialogs,
        )
        tab = self.layers_tab
        tab.material_selected.connect(self.materials.apply_selected)
        tab.new_material_requested.connect(self.materials.new_material)
        tab.delete_material_requested.connect(self.materials.delete_selected)
        tab.export_materials_requested.connect(self.materials.export_materials)
        tab.import_materials_requested.connect(self.materials.import_materials)
        # Matériaux et matériau choisi : rangés dans le profil de la machine active et écrits sur
        # disque (voir _machine_memory), pour les retrouver au prochain démarrage. Connecté après
        # le contrôleur : enregistré une fois la liste à jour.
        for signal in (tab.material_selected, tab.new_material_requested,
                       tab.delete_material_requested, tab.import_materials_requested):
            signal.connect(self.machines.schedule_persist)
        # Chaque changement de calque est aussitôt recopié dans le matériau choisi (plus de bouton
        # « Enregistrer »), PUIS les calques et les matériaux sont rangés dans le profil de la
        # machine active.
        self.layer_manager.changed.connect(self._store_layers_in_material)
        self.layer_manager.changed.connect(self.machines.schedule_persist)

    @contextmanager
    def _material_autosave_paused(self):
        """Pendant le bloc, les changements de calques ne sont pas recopiés dans le matériau
        choisi : ils viennent d'un profil machine, d'un projet ou du matériau lui-même."""
        self._material_autosave_pause += 1
        try:
            yield
        finally:
            self._material_autosave_pause -= 1

    def _store_layers_in_material(self):
        """Un calque a changé : le matériau choisi reprend les réglages en cours (une fois le
        démarrage terminé, et hors chargement d'un profil, d'un projet ou d'un matériau)."""
        if self._material_autosave_pause or not self.machines.persist_ready:
            return
        self.materials.store_current_settings()

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
        # Matière choisie par l'utilisateur (pas par programme) : coche ou décoche le négatif.
        settings.material_combo.activated.connect(
            lambda _index: self.image_settings.choose_material(settings.material_combo.material()))
        settings.engrave_layer_changed.connect(self._on_engrave_layer_chosen)
        settings.size_changed.connect(self.on_dimension_changed)
        settings.resolution_mode_changed.connect(self.on_lmm_mode_changed)
        settings.lines_per_mm_changed.connect(
            self._sync_dpi_and_quality_from_lmm
        )
        settings.dpi_changed.connect(self.on_dpi_value_changed)
        settings.configure_focal_requested.connect(
            self.goto_laser_focal_settings
        )
        # Algorithme choisi dans la liste par l'utilisateur (pas par programme) : mémorisé.
        settings.algorithm_combo.textActivated.connect(self.remember_algorithm)
        settings.undo_requested.connect(self.undo_image_settings)
        settings.redo_requested.connect(self.redo_image_settings)
        tab.compare_requested.connect(self.compare_dither_algorithms)
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
        self._refresh_engrave_layer_combo()

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
            bed_height=lambda: self.machine.bed_h,
            add_to_vector_editor=lambda objects: self.vector_editor.add_objects(objects),
            dialogs=self.dialogs,
        )
        tab.send_to_vector_requested.connect(self.png2svg.send_to_vector_editor)
        tab.image_changed.connect(self.update_image_actions_state)
        # Nom historique du widget de conversion, lu par les actions de la
        # barre d'outils sur l'image (rotation, suppression).
        self.png2svg_widget = tab.converter
        self.main_tabs_view.addTab(tab, tr("png2svg.tab_title"))
        self.tab_png2svg = tab

    def _build_separation_tab(self):
        """Onglet « Séparation Couleur / Verre » (vue SeparationTab), ses
        réglages (SeparationSettings) et sa logique (SeparationController).
        Masqué au démarrage, ouvert depuis le menu Outils. La tonalité de
        l'image devient l'image de « Graver une image » (on_separation_tone),
        dont le calque noir revient aux aperçus (on_image_processed)."""
        tab = SeparationTab()
        self.separation_settings = SeparationSettings(self)
        tab.bind_settings(self.separation_settings)
        self.separation = SeparationController(
            self.separation_settings, self.image_settings,
            frame_args=tab.frame_args, engrave_lmm=lambda: self.spin_lmm.value(),
            dialogs=self.dialogs,
            engraved=lambda: self.processed_array,
            image_busy=lambda: bool(self.process_timer.isActive()
                                    or (self.img_worker and self.img_worker.isRunning())),
            current_preview=tab.preview_tabs.currentIndex,
            is_visible=tab.isVisible,
            busy=self._busy_cursor,
            parent=self,
        )
        separation = self.separation
        tab.load_requested.connect(separation.open_image)
        tab.image_dropped.connect(separation.load_path)
        tab.tone_changed.connect(separation.schedule_push)
        tab.preview_changed.connect(separation.schedule_previews)
        tab.gain_test_requested.connect(self.job.generate_gain_test)
        tab.export_requested.connect(separation.export_files)
        tab.preview_tab_changed.connect(separation.render_current)
        separation.source_changed.connect(tab.set_source)
        separation.source_changed.connect(self.update_image_actions_state)
        separation.image_loaded.connect(tab.fit_plate_to_image)
        separation.image_rotated.connect(tab.swap_plate_size)
        separation.preview_ready.connect(tab.show_preview)
        separation.previews_invalidated.connect(separation.refresh_previews)
        separation.engrave_dpi_changed.connect(tab.set_engrave_dpi)
        separation.tone_ready.connect(self.on_separation_tone)
        self.tab_separation = tab
        tab.set_engrave_dpi(separation.engrave_dpi())
        self.main_tabs_view.addTab(tab, tr("sep.tab_title"))

    def _build_vector_editor_tab(self):
        """Onglet « Éditeur vectoriel ». Partira dans ui/tabs/ quand Julien
        aura fini son travail sur le vectoriel."""
        tab_vector_editor = QWidget()
        layout_vector_editor = QVBoxLayout(tab_vector_editor)
        # Canevas (vue du document) et contrôleur de l'éditeur, créés d'abord pour y brancher les boutons ;
        # le canevas prend sa place dans la mise en page plus bas.
        self.vector_canvas = VectorCanvasView(self.layer_manager, document=self.vector_document)
        self.vector_editor = VectorEditorController(
            self.vector_document, self.vector_canvas, self.layer_manager, self.machine, self.dialogs, self,
            image_frame=self._image_frame, busy=self._busy_cursor,
        )
        self.vector_editor.show_editor.connect(lambda: self.main_tabs_view.setCurrentWidget(self.tab_vector_editor))
        self.vector_editor.status.connect(self.show_status_message)
        editor = self.vector_editor

        # Boutons d'outils (rangée du haut), avec une icône du pack Breeze embarqué.
        # Bibliothèque de modèles (resources/library/) : import dans l'éditeur.
        self.library = LibraryController(
            self, self.layer_manager,
            bed_height=lambda: self.machine.bed_h,
            add_to_vector_editor=lambda objects: self.vector_editor.add_objects(objects),
            dialogs=self.dialogs,
        )
        btn_import_svg_vector = QPushButton(tr("ui.vector_import_svg"))
        btn_import_svg_vector.setStyleSheet("background-color: #3a6b3a; color: white;")
        btn_import_svg_vector.clicked.connect(editor.import_dialog)
        btn_box_generator = QPushButton(tr("ui.vector_box_generator"))
        btn_box_generator.setToolTip(tr("ui.vector_box_generator_tip"))
        btn_box_generator.clicked.connect(editor.open_box_generator)
        btn_puzzle_generator = QPushButton(tr("ui.vector_puzzle_generator"))
        btn_puzzle_generator.setToolTip(tr("ui.vector_puzzle_generator_tip"))
        btn_puzzle_generator.clicked.connect(editor.open_puzzle_generator)
        btn_ornament_generator = QPushButton(tr("ui.vector_ornament_generator"))
        btn_ornament_generator.setToolTip(tr("ui.vector_ornament_generator_tip"))
        btn_ornament_generator.clicked.connect(editor.open_ornament_generator)
        btn_keychain_generator = QPushButton(tr("ui.vector_keychain_generator"))
        btn_keychain_generator.setToolTip(tr("ui.vector_keychain_generator_tip"))
        btn_keychain_generator.clicked.connect(editor.open_keychain_generator)
        btn_nesting = QPushButton(tr("ui.vector_nesting"))
        btn_nesting.setToolTip(tr("ui.vector_nesting_tip"))
        btn_nesting.clicked.connect(editor.open_nesting)
        for button, icon in ((btn_import_svg_vector, "document-import"), (btn_box_generator, "draw-cuboid"),
                             (btn_puzzle_generator, "games-config-board"), (btn_ornament_generator, "draw-ellipse"),
                             (btn_keychain_generator, "keychain"), (btn_nesting, "object-group")):
            button.setIcon(palette_icon(icon, self.palette()))
            # L'emoji du libellé (📥, 📦, 🧩) ferait doublon avec l'icône.
            label = button.text()
            if label and not label[0].isalnum():
                button.setText(label.split(" ", 1)[-1])
        # Édition de la sélection : barre flottante d'icônes en haut du canevas (voir plus bas), le
        # libellé en infobulle. Icônes du pack Breeze embarqué (palette_icon).
        vector_edit_actions = [
            self._vector_action(tr(key), tr(key).lstrip("↻↶↷ "), slot, icon) if key else None
            for key, icon, slot in (
                ("ui.vector_edit_selection", "document-edit", editor.edit_selected),
                ("ui.vector_rotate_90", "object-rotate-right", editor.rotate_selected),
                ("ui.vector_duplicate", "edit-duplicate", editor.duplicate_selected),
                ("ui.vector_serial_duplicate", "view-grid", editor.open_serial_duplicate),
                ("ui.vector_jig", "draw-rectangle", editor.open_jig_generator),
                ("ui.vector_delete", "edit-delete", editor.delete_selected),
                ("ui.vector_delete_all", "edit-clear-all", editor.delete_all),
                (None, None, None),
                ("vector.explode_path", "object-ungroup", lambda: self.vector_canvas.explode_selected()),
                ("vector.edit_nodes", "format-node-curve", lambda: self.vector_canvas.enter_node_edit()),
                ("vector.text_follow", "text-follow-path", editor.make_text_follow_selection),
                ("vector.medal", "insert-text", editor.open_medal_text),
                (None, None, None),
                ("ui.vector_undo", "edit-undo", lambda: self.vector_canvas.undo()),
                ("ui.vector_redo", "edit-redo", lambda: self.vector_canvas.redo()),
            )
        ]
        # Créer et dessiner : barre flottante d'icônes à gauche du canevas (voir plus bas). Texte et
        # forme ajoutent un objet ; sélection, ligne, rectangle, cercle, ellipse et mesure sont les outils de
        # la souris, un seul coché à la fois (set_vector_draw_tool).
        vector_create_actions = [
            self._vector_action(tr(key), tr(key).lstrip("+ "), slot, icon)
            for key, icon, slot in (
                ("ui.vector_add_text", "insert-text", editor.insert_text),
                ("ui.vector_add_shape", "shape-choose", editor.insert_shape),
            )
        ]
        # Bibliothèque de modèles : ajoute aussi des objets (la rangée du haut est pleine).
        vector_create_actions.append(self._vector_action(
            tr("ui.vector_library"), tr("ui.vector_library_tip"), self.library.open, "view-app-grid"))
        self._vector_draw_buttons = {}
        for tool, key, icon in (
            (None, "ui.vector_tool_select", "tool-pointer"),
            ("line", "ui.vector_tool_line", "draw-line"),
            ("rect", "ui.vector_tool_rect", "draw-rectangle"),
            ("circle", "ui.vector_tool_circle", "draw-circle"),
            ("ellipse", "ui.vector_tool_ellipse", "draw-ellipse"),
            ("measure", "ui.vector_tool_measure", "measure"),
        ):
            action = self._vector_action(
                tr(key), f"{tr(key)} — {tr(key + '_tip')}", lambda t=tool: self.set_vector_draw_tool(t), icon)
            action.setCheckable(True)
            self._vector_draw_buttons[tool] = action
        self._vector_draw_buttons[None].setChecked(True)

        # Une seule rangée en haut : marges réduites pour le canevas
        layout_vector_editor.setContentsMargins(4, 4, 4, 4)
        layout_vector_editor.setSpacing(4)

        # Rangée du haut : importer et outils (boîte, puzzle, boule de Noël, porte-clés, imbrication), puis la grille
        # magnétique à droite. Le plein écran est celui de la barre d'outils principale.
        toolbar_vector = QHBoxLayout()
        toolbar_vector.setSpacing(4)
        toolbar_vector.addWidget(btn_import_svg_vector)
        toolbar_vector.addWidget(btn_box_generator)
        toolbar_vector.addWidget(btn_puzzle_generator)
        toolbar_vector.addWidget(btn_ornament_generator)
        toolbar_vector.addWidget(btn_keychain_generator)
        toolbar_vector.addWidget(btn_nesting)
        toolbar_vector.addStretch()
        self.chk_vector_snap = QCheckBox(tr("ui.vector_snap_enable"))
        self.chk_vector_snap.toggled.connect(self.set_vector_snap_enabled)
        toolbar_vector.addWidget(self.chk_vector_snap)
        self.spin_vector_snap_step = QDoubleSpinBox()
        self.spin_vector_snap_step.setRange(0.1, 100.0)
        self.spin_vector_snap_step.setValue(5.0)
        self.spin_vector_snap_step.setSuffix(" mm")
        self.spin_vector_snap_step.valueChanged.connect(self.set_vector_snap_step)
        toolbar_vector.addWidget(self.spin_vector_snap_step)
        layout_vector_editor.addLayout(toolbar_vector)

        # Alignement / distribution : barre flottante verticale à droite du canevas. Le bouton ne
        # garde que le pictogramme du libellé (« ⊢ ») ; l'infobulle dit l'action (« Aligner à gauche »).
        vector_align_actions = [
            self._vector_action(tr(key).split(" ", 1)[0], tr(f"{key}_tip"), slot) if key else None
            for key, slot in (
                ("ui.vector_align_left", lambda: editor.align("left")),
                ("ui.vector_align_center_h", lambda: editor.align("center_h")),
                ("ui.vector_align_right", lambda: editor.align("right")),
                (None, None),
                ("ui.vector_align_top", lambda: editor.align("top")),
                ("ui.vector_align_middle_v", lambda: editor.align("middle_v")),
                ("ui.vector_align_bottom", lambda: editor.align("bottom")),
                (None, None),
                ("ui.vector_distribute_h", lambda: editor.distribute("h")),
                ("ui.vector_distribute_v", lambda: editor.distribute("v")),
            )
        ]

        layout_vector_editor.addWidget(self.vector_canvas, 1)  # stretch: occupe l'espace restant
        self.vector_create_toolbar = FloatingToolBar(
            [*vector_create_actions, None, *self._vector_draw_buttons.values()],
            self.vector_canvas, anchor="left")
        self.vector_edit_toolbar = FloatingToolBar(vector_edit_actions, self.vector_canvas, top_margin=8)
        self.vector_align_toolbar = FloatingToolBar(
            vector_align_actions, self.vector_canvas, anchor="right",
            button_style=Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Pictogrammes plus grands que le texte courant, pour rester lisibles.
        self.vector_align_toolbar.setStyleSheet(
            self.vector_align_toolbar.styleSheet() + " QToolButton { font-size: 16px; min-width: 24px; }")
        self.vector_align_toolbar.setToolTip(tr("ui.vector_align_box"))

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
        pos_row1.addWidget(self.spin_vec_x)
        pos_row1.addWidget(QLabel(tr("ui.vector_y_mm")))
        self.spin_vec_y = QDoubleSpinBox(); self.spin_vec_y.setRange(-1000.0, 1000.0); self.spin_vec_y.setDecimals(2)
        self.spin_vec_y.setMaximumWidth(90)
        pos_row1.addWidget(self.spin_vec_y)
        pos_row1.addWidget(QLabel(tr("ui.vector_rotation_deg")))
        self.spin_vec_rot = QDoubleSpinBox(); self.spin_vec_rot.setRange(-360.0, 360.0); self.spin_vec_rot.setDecimals(1)
        self.spin_vec_rot.setMaximumWidth(70)
        pos_row1.addWidget(self.spin_vec_rot)
        pos_row1.addWidget(QLabel(tr("ui.vector_layer")))
        self.combo_vec_layer = QComboBox()
        self.combo_vec_layer.setMinimumWidth(120)
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
        pos_row_size.addWidget(self.spin_vec_w)
        pos_row_size.addWidget(QLabel(tr("ui.vector_height_mm")))
        self.spin_vec_h = QDoubleSpinBox()
        self.spin_vec_h.setRange(0.05, 5000.0)
        self.spin_vec_h.setDecimals(2)
        self.spin_vec_h.setSuffix(" mm")
        self.spin_vec_h.setMaximumWidth(100)
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
        # Panneau des propriétés : rempli d'après la sélection, saisies transmises au contrôleur.
        self.vector_properties = VectorPropertiesPanel(
            PropertiesWidgets(
                label=self.lbl_vector_selection, box=pos_box, x=self.spin_vec_x, y=self.spin_vec_y,
                rotation=self.spin_vec_rot, layer=self.combo_vec_layer, size_row=self.pos_size_anchor_widget,
                width=self.spin_vec_w, height=self.spin_vec_h, anchor_lock=self.chk_vec_anchor_lock,
                anchor=self.combo_vec_anchor,
            ),
            self.layer_manager, self.vector_canvas, editor, parent=self,
        )
        self.vector_canvas.edit_requested.connect(editor.edit_object)
        self.vector_canvas.insert_text_requested.connect(editor.insert_text)
        self.vector_canvas.serial_duplicate_requested.connect(editor.open_serial_duplicate)
        self.vector_canvas.jig_requested.connect(editor.open_jig_generator)
        self.vector_canvas.medal_text_requested.connect(editor.open_medal_text)

        self.main_tabs_view.addTab(tab_vector_editor, tr("ui.tab_vector_editor"))
        self.tab_vector_editor = tab_vector_editor

    def _vector_action(self, text, tooltip, slot, icon_name=None):
        """Action de l'éditeur vectoriel (barres flottantes du canevas) : `text`, infobulle
        `tooltip`, icône `icon_name` du pack Breeze embarqué dans la couleur du thème."""
        action = QAction(text, self)
        action.setToolTip(tooltip)
        if icon_name:
            action.setIcon(palette_icon(icon_name, self.palette()))
        action.triggered.connect(lambda _checked=False: slot())
        return action

    def _build_2d_preview_tab(self):
        """Onglet « Visualisation 2D G-Code » : il dessine le G-Code généré ou
        importé (plot_gcode_preview), la position de la tête et les traits
        déjà gravés pendant un job."""
        tab = Preview2DTab(self.job_position_box)
        tab.display_options_changed.connect(
            self._on_preview_options_changed
        )
        tab.plot_clicked.connect(self.job.apply_matrix_cell)
        tab.log.connect(self.log_message)
        # Séparateur aperçu / statistiques : position mémorisée (load_splitter_sizes).
        tab.splitter.splitterMoved.connect(self.save_splitter_sizes)
        # Nom historique, lu par le job (optimize_path).
        self.chk_optimize_path = tab.optimize_path_check
        self.main_tabs_view.addTab(tab, tr("ui.tab_2d_preview"))
        self.tab_vector_2d = tab

    def _build_console_tab(self):
        """Onglet « Console / G-Code », masqué au démarrage (menu Affichage)."""
        tab = ConsoleTab()
        # Nom historique de la console : le G-Code généré ou importé, seul (les messages vont dans
        # la barre d'état, voir log_message).
        self.txt_console = tab.console_edit
        self.main_tabs_view.addTab(tab, tr("ui.tab_console_gcode"))
        self.tab_console_gcode = tab
        self._add_console_close_button()

    def _build_job_queue_tab(self):
        """Onglet « File d'attente », abonné à la file (JobQueueController),
        qui envoie ses jobs par le contrôleur du graveur (self.engraver)."""
        tab = JobQueueTab()
        engraver = Engraver(
            is_connected=self.connection.is_connected,
            last_state=lambda: self.connection.last_state,
            confirm_homed=self.engraver.confirm_homed,
            start_stream=self.engraver.start_stream,
            stream_ended=self.engraver.end_stream,
            pause_status_poll=self.connection.pause_status_poll,
            resume_status_poll=self.connection.resume_status_poll,
            jobs_finished=self.engraver.notify_job_done,
        )
        self.job_queue = JobQueueController(
            tab,
            self,
            engraver,
            current_gcode=self.txt_console.toPlainText,
            log_to_console=self.log_message,
            sent_log=self.machine_panel.sent_gcode_log,
            dialogs=self.dialogs,
        )
        tab.add_current_requested.connect(self.job_queue.add_current_gcode)
        tab.remove_selected_requested.connect(self.job_queue.remove_selected)
        tab.clear_requested.connect(self.job_queue.clear)
        tab.run_requested.connect(self.job_queue.run)
        tab.reordered.connect(self.job_queue.on_reordered)
        self.main_tabs_view.addTab(tab, tr("ui.tab_job_queue"))
        self.tab_job_queue = tab
        self._add_tab_close_button(tab, self.app_actions.job_queue)

    # -- Réglages machine : démarrage et fermeture

    def save_machine_settings(self):
        """Mémorise les réglages machine (profils, dimensions, résolution de
        l'image) pour les retrouver au prochain lancement, sans recharger de
        projet. Les calques sont rangés dans le profil de la machine active."""
        settings = QSettings("LaserStudioPro", "MachineConfig")
        settings.setValue("machine_bed_w_mm", self.machine.bed_w)
        settings.setValue("machine_bed_h_mm", self.machine.bed_h)
        settings.setValue("machine_focal_mm", self.machine.focal)
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
        for key, field in (("machine_bed_w_mm", "bed_w"),
                           ("machine_bed_h_mm", "bed_h"),
                           ("machine_focal_mm", "focal")):
            value = settings.value(key, None)
            if value is not None:
                self.machine.update(**{field: value})   # valeur illisible : ignorée
        # Comme à chaque validation de profil : les calques suivent la focale
        # dès le démarrage.
        self.layers_tab.link_all_to_focal()

        self.machines.load(
            settings.value("machine_profiles_json", ""),
            settings.value("last_machine_profile", None),
            {"name": "Machine par défaut", "w": self.machine.bed_w,
             "h": self.machine.bed_h},
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
            **self.machine.to_profile(),
            **self.job_position_box.profile_values(),
            **self.grbl.profile_values(),
            "materials_db": dict(self.materials.materials),
            "material": self.materials.model.current or "",
            "layers": self.layer_manager.to_list(),
        }

    def _apply_machine_profile(self, profile):
        """Réapplique les champs d'un profil (les calques à part)."""
        with self._material_autosave_paused():
            self.machine.apply_profile(profile)
            self.job_position_box.apply_profile_values(profile)
            self.grbl.apply_profile(profile)
            # Matériaux propres à cette machine (repli sur la base par défaut pour un profil
            # enregistré avant cette liaison), et matériau choisi à sa dernière utilisation
            # (sélectionné sans être appliqué).
            self.materials.model.set_materials(
                dict(profile.get("materials_db", DEFAULT_MATERIALS_DB)),
                current=profile.get("material"))
            # Calques : ceux mémorisés dans le profil, déjà appliqués ; le matériau ne les écrase pas.
            material = self.materials.model.current_material()
            if material is not None:
                self._apply_job_settings(material, layers=False)

    def _machine_memory(self):
        """Mémorisé en continu dans le profil actif : calques, matériaux (avec les réglages de leurs
        calques) et matériau choisi, réglages mécaniques (décalage des lignes retour, surbalayage,
        homing)."""
        return {"layers": self.layer_manager.to_list(),
                "materials_db": dict(self.materials.materials),
                "material": self.materials.model.current or "",
                **self.grbl.mechanical_values()}

    def _apply_profile_layers(self, saved_layers, full=False):
        """Réapplique les calques mémorisés (voir apply_saved_layers), puis
        met l'onglet Calques à jour."""
        with self._material_autosave_paused():
            if not apply_saved_layers(self.layer_manager, saved_layers, full):
                return
            # Les calques liés à la focale suivent la focale de CETTE machine.
            self.layers_tab.link_all_to_focal()

    def _after_machine_profile_selected(self):
        """Après un changement de profil : lignes/mm et DPI suivent la focale
        (même si elle n'a pas changé, ou si le profil n'en a pas), et la
        qualité des calques est recalculée."""
        self._apply_focal_to_lmm()
        with self._material_autosave_paused():
            self.layers_tab.refresh_focal_quality()

    # -- Projet : état de la fenêtre

    def _capture_project(self):
        """État du projet (pour ProjectController) : réglages de l'image,
        machine, gravure et découpe, matériaux, calques, objets vectoriels ;
        et l'image source (PIL), encodée par le contrôleur."""
        data = {
            "w_mm": self.spin_w.value(),
            "h_mm": self.spin_h.value(),
            "machine_bed_w_mm": self.machine.bed_w,
            "machine_bed_h_mm": self.machine.bed_h,
            "origin_pos": self.job_position_box.origin(),
            "offset_x": self.spin_off_x.value(),
            "offset_y": self.spin_off_y.value(),
            **self.image_settings.to_project(),
            "safe_cut_order": self.grbl.safe_cut_order,
            "lmm": self.spin_lmm.value(),
            "speed_engrave": self.job.engrave_speed,
            "power_engrave": self.job.engrave_power,
            "enable_cut": self.job.cut_enabled,
            "speed_cut": self.job.cut_speed,
            "power_cut": self.job.cut_power,
            "passes_cut": self.job.cut_passes,
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
        """Réapplique un projet ouvert (voir _restore_project_state), sans recopier ses calques
        dans le matériau choisi."""
        with self._material_autosave_paused():
            self._restore_project_state(data, image)

    def _restore_project_state(self, data, image):
        """Réapplique un projet ouvert (voir _capture_project). Les clés
        absentes (anciens projets) prennent leur valeur par défaut."""
        # Le projet impose ses propres réglages matière / négatif / miroir :
        # l'état mémorisé par l'onglet Séparation est oublié, sinon un
        # chargement d'image ultérieur le « rendrait » par-dessus.
        self.separation.forget_glass_settings()

        self.spin_w.setValue(data.get("w_mm", 100.0))
        self.spin_h.setValue(data.get("h_mm", 100.0))
        self.machine.update(bed_w=data.get("machine_bed_w_mm", self.machine.bed_w))
        self.machine.update(bed_h=data.get("machine_bed_h_mm", self.machine.bed_h))
        self.job_position_box.set_origin(data.get("origin_pos", ORIGIN_BOTTOM_LEFT))
        self.spin_off_x.setValue(data.get("offset_x", 0.0))
        self.spin_off_y.setValue(data.get("offset_y", 0.0))

        # Réglages de tramage (anciens projets sans "material_bg" : déduite du négatif).
        self.image_settings.load_project(data)
        self.grbl.update(safe_cut_order=data.get("safe_cut_order", True))
        self.spin_lmm.setValue(data.get("lmm", 10.0))

        # Ancien projet sans calques : sa vitesse / puissance de gravure image vont dans le calque
        # de gravure. Avec des calques, ce sont eux qui font foi (rechargés plus bas).
        if "layers" not in data:
            self.job.set_engrave_settings(data.get("speed_engrave", 2000), data.get("power_engrave", 30))
        self.job.cut_enabled = bool(data.get("enable_cut", False))
        self.job.set_cut_settings(data.get("speed_cut", 300), data.get("power_cut", 90),
                                  data.get("passes_cut", 2))

        if "materials_db" in data:
            self.materials.set_materials(data["materials_db"])

        if image is not None:
            self.raw_image = image
            self.display_source_image()

        self.loaded_svg_path = data.get("svg_path")

        if "layers" in data:
            self.layer_manager.load_list(data["layers"])
            self._refresh_engrave_layer_combo()
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
            self.connection.shutdown()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Fermeture volontaire sans enregistrer : la sauvegarde automatique ne
            # doit pas être proposée en récupération au prochain démarrage.
            self.project.discard_autosave()
            self._flush_background_writes()
            self.connection.shutdown()
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
            if file_path.lower().endswith(('.svg', '.dxf')) and hasattr(self, "vector_editor"):
                self.vector_editor.import_file(file_path)
                break
