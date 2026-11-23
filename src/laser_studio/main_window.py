"""Fenêtre principale de l'application.

FullLaserStudio construit la fenêtre (init_ui), crée les modèles et les
contrôleurs, branche les signaux de ses panneaux et gère ses événements
(fermeture, glisser-déposer). Ce qui agit sur la fenêtre est dans ui/app/ :
WindowController (menus, réglages, actions transversales), MainTabs (onglets,
plein écran, panneau du bas), JobDisplay (résultats du job, état du graveur),
ImageToolbarActions (actions de la barre d'outils sur l'image).
"""
from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow, QMessageBox, QScrollArea, QSplitter, QTabWidget,
                             QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QStandardItemModel

from laser_studio.core.debug_log import get_logger
from laser_studio.i18n import tr
from laser_studio.controllers.engraver import EngraverController
from laser_studio.controllers.job import JobController
from laser_studio.controllers.vector_editor import VectorEditorController
from laser_studio.ui.vector_editor.properties_panel import VectorPropertiesPanel
from laser_studio.ui.vector_editor.tab import VectorEditorTab
from laser_studio.ui.user_dialogs import UserDialogs
from laser_studio.ui.machine import MachinePanel
from laser_studio.ui.machine.connection import port_help_dialog
from laser_studio.ui.machine.job_position import JobPositionBox
from laser_studio.ui.settings.grbl_config import GrblConfigPage
from laser_studio.ui.settings.machine_params import MachineParamsPage
from laser_studio.ui.settings.test_matrix import TestMatrixPage
from laser_studio.ui.statusbar import StatusBar, status_text
from laser_studio.ui.tabs.console import ConsoleTab
from laser_studio.ui.tabs.image import ImageTab
from laser_studio.ui.tabs.job_queue import JobQueueTab
from laser_studio.ui.tabs.layers import LayersTab
from laser_studio.ui.tabs.png2svg import Png2SvgTab
from laser_studio.ui.tabs.preview_2d import Preview2DTab
from laser_studio.ui.tabs.separation import SeparationTab
from laser_studio.ui.utils import busy_cursor
from laser_studio.ui.widgets import FloatingToolBar

from laser_studio.controllers.job_queue import Engraver, JobQueueController
from laser_studio.controllers.materials import DEFAULT_MATERIALS_DB, MaterialsController
from laser_studio.controllers.machine_profiles import MachineProfilesController, ProfileFields
from laser_studio.controllers.matrix_image import MatrixImageController
from laser_studio.controllers.library import LibraryController
from laser_studio.controllers.image import ImageController
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

from laser_studio.ui.app.image_actions import ImageToolbarActions
from laser_studio.ui.app.job_display import JobDisplay, set_homing_available
from laser_studio.ui.app.menu import AppActions, AppMenuBar, AppToolBar
from laser_studio.ui.app.tabs import GCODE_CONSOLE_SETTING, JOB_QUEUE_SETTING, MainTabs
from laser_studio.ui.app.window_controller import WindowController
from laser_studio.ui.app.window_state import WindowState

log = get_logger()


class FullLaserStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laser Studio Pro - GRBL Controller")
        self.resize(1600, 980)
        
        self.setAcceptDrops(True)
        # Actions qui touchent toute la fenêtre (menus, réglages, résolution, Stencil Studio).
        self.window_controller = WindowController(self)
        # État qui s'enregistre et se restaure : réglages machine, profils, projet, matériau choisi.
        self.state = WindowState(self)

        # Dialogue avec le graveur (port, threads, état « référencé ») ; son
        # pilotage (connexion, jog, envoi d'un job, configuration $$) est dans
        # self.engraver, construit plus bas.
        self.connection = MachineConnection(parent=self)
        # Boîtes de dialogue des contrôleurs (messages, confirmations, fichiers),
        # centrées sur la fenêtre : les contrôleurs n'ouvrent pas de QMessageBox
        # eux-mêmes, ce qui permet de les tester sans fenêtre.
        self.dialogs = UserDialogs(self)
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
        # Réglages de tramage de « Graver une image » et leur annulation (Ctrl+Z / Ctrl+Y) : les
        # champs de l'onglet y sont liés (ImageSettingsPanel.bind_settings), la logique les lit ici.
        self.image_settings = ImageSettings(self)
        self.image_history = ImageSettingsHistory(self.image_settings)

        # Job : paramètres, contrôles avant génération, génération du G-Code
        # (thread), estimation, export / import, matrice de test. Il lit l'état
        # de l'interface par les fonctions ci-dessous ; JobDisplay (créé par
        # init_ui) affiche ses résultats : console, aperçu 2D.
        self.job = JobController(
            self.layer_manager, self.grbl, self.machine, self.image_settings, self.dialogs,
            geometry=self._job_geometry,
            image=lambda: self.image.processed_array,
            svg_path=lambda: self.loaded_svg_path,
            vector_objects=lambda: self.vector_document.objects,
            optimize_path=lambda: self.chk_optimize_path.isChecked(),
            lines_mm=lambda: self.spin_lmm.value(),
            material_summary=lambda: self.image.material_summary(),
            parent=self,
        )
        self.job.log.connect(self.log_message)
        self.job.status.connect(self.show_status_message)
        # Graveur : port, connexion, pilotage, envoi des jobs, configuration GRBL.
        self.engraver = EngraverController(
            self.connection, self.grbl, self.dialogs,
            selected_port=lambda: self.machine_panel.connection_panel.selected_port(),
            current_gcode=lambda: self.txt_console.toPlainText(),
            job_geometry=self._job_geometry,
            set_homing_available=lambda available, tip: set_homing_available(
                (self.chk_homing, self.chk_mat_homing), available, tip),
            parent=self,
        )

        # Sauvegarde automatique du projet toutes les 5 minutes, pour ne rien
        # perdre en cas de plantage ou de coupure de courant en pleine session.
        # Fichier du projet (enregistrer, ouvrir, récents, sauvegarde
        # automatique) ; l'état lui-même est lu et réappliqué par
        # WindowState (capture_project / restore_project).
        self.project = ProjectController(
            self,
            capture=self.state.capture_project,
            restore=self.state.restore_project,
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
        # Miroirs de la gravure, dans la barre d'outils de la fenêtre (créée par init_ui).
        bind(self.app_actions.mirror_h, self.image_settings, "mirror_h")
        bind(self.app_actions.mirror_v, self.image_settings, "mirror_v")
        self.job_display.connect_machine(self.connection, self.engraver)
        self.state.load_machine_settings()
        self.tabs.load_splitter_sizes()
        self.image.restore_remembered_algorithm()
        self.window_controller.update_vector_work_area()
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
        # « Pivoter », « Supprimer », miroirs : agissent sur l'image de l'onglet affiché
        # (chaque onglet d'image s'y inscrit en se construisant).
        self.image_actions = ImageToolbarActions(
            self.app_actions, current_tab=lambda: self.main_tabs_view.currentWidget(),
            dialogs=self.dialogs, parent=self)

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
        # Onglets, plein écran, panneau du bas : le panneau machine n'est montré que sur les
        # onglets du job (aperçu 2D, console, file d'attente) ou pendant un envoi.
        self.tabs = MainTabs(
            self.main_tabs_view, self,
            splitter=self.center_v_splitter, bottom_panel=center_bottom_scroll,
            panel_tabs=(self.tab_vector_2d, self.tab_console_gcode, self.tab_job_queue),
            preview_splitter=self.tab_vector_2d.splitter,
            job_in_progress=self.connection.is_streaming,
            vector_editor=self.tab_vector_editor, recenter_vector_editor=self.vector_canvas.request_recenter,
            png2svg=self.tab_png2svg, parent=self,
        )
        # Console G-Code (masquée la première fois) et file d'attente (affichée) : menu Affichage,
        # croix sur l'onglet, choix mémorisé.
        self.tabs.add_optional(self.tab_console_gcode, GCODE_CONSOLE_SETTING, self.app_actions.gcode_console)
        self.tabs.add_optional(self.tab_job_queue, JOB_QUEUE_SETTING, self.app_actions.job_queue)
        self._build_job_display()
        self.main_tabs_view.currentChanged.connect(self.tabs.update_bottom_panel)
        self.main_tabs_view.currentChanged.connect(self.window_controller.main_tab_changed)
        self.main_tabs_view.currentChanged.connect(self.image_actions.update_state)
        # Onglets masqués au démarrage, ouverts à la demande depuis le menu Outils (MainTabs.show),
        # ou Affichage pour la console G-Code et la file d'attente (MainTabs.set_optional_visible).
        for tab in (self.tab_separation, self.tab_png2svg, self.tab_console_gcode):
            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)
        self._add_image_floating_toolbars()
        self.tabs.update_bottom_panel()
        self.image_actions.update_state()
        self.tabs.restore_optional_tabs()

        # Largeur minimale EXPLICITE du centre. Sans elle, la largeur minimale serait calculée
        # d'après le contenu : la barre d'outils de l'éditeur vectoriel (11 boutons, ~1500 px) et la
        # rangée d'alignement imposeraient environ 1500 px à la fenêtre. Trop étroit, le centre se
        # contente de serrer ses boutons.
        center_widget.setMinimumWidth(480)
        # Séparateurs onglets / panneau du bas et aperçu / statistiques : positions mémorisées.
        self.center_v_splitter.splitterMoved.connect(self.tabs.save_splitter_sizes)
        self.tab_vector_2d.splitter.splitterMoved.connect(self.tabs.save_splitter_sizes)

        main_layout.addWidget(center_widget)
        # Menus abonnés une fois toute la fenêtre construite.
        self.window_controller.connect_actions(self.app_actions)
        self.project.refresh_recent_projects()
        self.window_controller.schedule_stencil_preload()

    def _build_app_menus(self):
        """Menu et barre d'outils : AppActions crée les actions partagées et
        émet les signaux, AppMenuBar et AppToolBar ne font que les ranger
        (abonnés par WindowController.connect_actions)."""
        self.app_actions = AppActions(self)
        self.app_menu_bar = AppMenuBar(self.app_actions)
        self.setMenuBar(self.app_menu_bar)
        self.main_toolbar = AppToolBar(self.app_actions, self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_toolbar)

    def _build_job_display(self):
        """Affichage des résultats du job (JobController) : barre d'état,
        console, statistiques et aperçu 2D ; l'état du graveur s'y ajoute
        (JobDisplay.connect_machine)."""
        self.job_display = JobDisplay(
            self.statusBar(), self.txt_console, self.tab_vector_2d, self.machine_panel,
            self.app_actions, self.dialogs,
            layers=self.layer_manager,
            test_matrix=lambda: self.job.last_test_matrix_params,
            show_preview=lambda: self.main_tabs_view.setCurrentWidget(self.tab_vector_2d),
            log=self.log_message,
            update_bottom_panel=self.tabs.update_bottom_panel,
            parent=self,
        )
        display = self.job_display
        self.job.started.connect(display.generation_started)
        self.job.progress.connect(display.generation_progress)
        self.job.generated.connect(display.show_generated)
        self.job.failed.connect(display.generation_failed)
        self.job.imported.connect(display.show_imported)
        self.tab_vector_2d.display_options_changed.connect(display.redraw)

    def _add_image_floating_toolbars(self):
        """Barre flottante en haut des aperçus d'image : mêmes actions que celles de l'ancienne
        barre d'outils (état actif / coché partagé, voir ImageToolbarActions.update_state).

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
        # Commandes verrouillées tant que non connecté (puis JobDisplay.update_connection)
        self.machine_panel.set_connected(self.connection.is_connected())

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

        Affichée dans une fenêtre du menu Paramètres (WindowController.show_settings_window).
        """
        page = MachineParamsPage()
        self.machines = MachineProfilesController(
            self,
            page.profile_combo,
            ProfileFields(
                capture=self.state.capture_machine_profile,
                apply=self.state.apply_machine_profile,
                apply_layers=self.state.apply_profile_layers,
                memory=self.state.machine_memory,
                profile_selected=self.state.after_machine_profile_selected,
                link_layers_to_focal=lambda: self.layers_tab.link_all_to_focal(),
            ),
            save_settings=self.state.save_machine_settings,
            dialogs=self.dialogs,
        )
        page.profile_selected.connect(self.machines.on_selected)
        page.new_profile_requested.connect(self.machines.new_profile)
        page.update_profile_requested.connect(self.machines.update_profile)
        page.delete_profile_requested.connect(self.machines.delete_profile)
        page.focal_changed.connect(self.window_controller.machine_focal_changed)
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

        Affichée dans une fenêtre du menu Paramètres (WindowController.show_settings_window).
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
        doit déjà exister ; voir WindowController.sync_matrix_lines_mm).
        """
        page = TestMatrixPage(self.spin_lmm.value())
        page.generate_requested.connect(self.window_controller.generate_test_matrix_and_show)
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

    def _image_frame(self):
        """(x, y, largeur, hauteur) en mm de l'image de « Graver une image »,
        pour caler le puzzle dessus (VectorEditorController)."""
        return (float(self.spin_off_x.value()), float(self.spin_off_y.value()),
                float(self.spin_w.value()), float(self.spin_h.value()))

    def _loaded_image_and_width(self):
        """(image, largeur en mm) de « Graver une image », ou None."""
        if not self.image.has_image():
            return None
        return self.image.raw_image, self.spin_w.value()

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
        # Profils matériaux (barre d'outils de l'onglet) : un matériau mémorise les réglages des
        # calques ; le choisir dans la liste met le tableau à jour (WindowState.apply_job_settings).
        self.materials = MaterialsController(
            self,
            self.layers_tab.material_combo,
            materials,
            current_settings=self.state.job_settings,
            apply_settings=self.state.apply_job_settings,
            dialogs=self.dialogs,
        )
        tab = self.layers_tab
        tab.material_selected.connect(self.materials.apply_selected)
        tab.new_material_requested.connect(self.materials.new_material)
        tab.delete_material_requested.connect(self.materials.delete_selected)
        tab.export_materials_requested.connect(self.materials.export_materials)
        tab.import_materials_requested.connect(self.materials.import_materials)
        # Matériaux et matériau choisi : rangés dans le profil de la machine active et écrits sur
        # disque (voir WindowState.machine_memory), pour les retrouver au prochain démarrage. Connecté après
        # le contrôleur : enregistré une fois la liste à jour.
        for signal in (tab.material_selected, tab.new_material_requested,
                       tab.delete_material_requested, tab.import_materials_requested):
            signal.connect(self.machines.schedule_persist)
        # Chaque changement de calque est aussitôt recopié dans le matériau choisi (plus de bouton
        # « Enregistrer »), PUIS les calques et les matériaux sont rangés dans le profil de la
        # machine active.
        self.layer_manager.changed.connect(self.state.store_layers_in_material)
        self.layer_manager.changed.connect(self.machines.schedule_persist)

    def _build_image_tab(self):
        """Onglet « Graver une image » (vue ImageTab) et sa logique
        (ImageController), et cadre « Position du job ».

        Construit tôt : la matrice de test lit ses lignes/mm, le panneau
        machine reçoit le cadre « Position du job ». L'onglet est placé
        dans les onglets par init_ui.
        """
        tab = ImageTab()
        settings = tab.settings
        settings.bind_settings(self.image_settings)
        self.resolution_box = settings.resolution_box
        self.image = ImageController(
            self.image_settings, self.machine, self.dialogs,
            size_mm=settings.size_mm,
            set_size=settings.set_size,
            keep_ratio=settings.keep_ratio_check.isChecked,
            lines_mm=self.resolution_box.lines_per_mm,
            parent=self,
        )
        image = self.image
        settings.load_requested.connect(image.open_image)
        settings.processing_changed.connect(image.schedule_processing)
        # Matière choisie par l'utilisateur (pas par programme) : coche ou décoche le négatif.
        settings.material_combo.activated.connect(
            lambda _index: self.image_settings.choose_material(settings.material_combo.material()))
        # Calque de gravure choisi : sa vitesse et sa puissance deviennent celles de la gravure.
        settings.engrave_layer_changed.connect(self.layer_manager.select_engrave_layer)
        settings.size_changed.connect(image.dimension_changed)
        settings.resolution_changed.connect(self.window_controller.resolution_changed)
        settings.configure_focal_requested.connect(self.window_controller.goto_focal_settings)
        # Algorithme choisi dans la liste par l'utilisateur (pas par programme) : mémorisé.
        settings.algorithm_combo.textActivated.connect(image.remember_algorithm)
        settings.undo_requested.connect(self.image_history.undo)
        settings.redo_requested.connect(self.image_history.redo)
        tab.compare_requested.connect(self.window_controller.show_dither_comparison)
        image.source_changed.connect(tab.show_source)
        image.source_changed.connect(self.image_actions.update_state)
        self.image_actions.add(
            tab, has_image=image.has_image,
            rotate=lambda clockwise: (image.rotate_right if clockwise else image.rotate_left)(),
            clear=image.clear, confirm_clear=False)          # clear() demande elle-même confirmation
        image.processed.connect(tab.show_processed)
        image.status.connect(self.show_status_message)
        # Noms historiques des champs, encore lus par la fenêtre (génération,
        # projets, profils, séparation, matrice).
        self.spin_w = settings.width_spin
        self.spin_h = settings.height_spin
        self.spin_off_x = settings.offset_x_spin
        self.spin_off_y = settings.offset_y_spin
        self.spin_lmm = settings.lines_per_mm_spin
        self.combo_lmm_mode = settings.resolution_mode_combo
        self.spin_dpi = settings.dpi_spin
        self.tab_previews = tab
        # Résolution calée sur la focale du laser au départ, puis largeur du
        # panneau d'après ses textes (dont l'information sur la focale).
        self.resolution_box.set_focal(self.machine.focal)
        self.resolution_box.refresh()
        tab.fit_settings_width()
        self.window_controller.refresh_engrave_layer_combo()
        self.layer_manager.changed.connect(self.window_controller.refresh_engrave_layer_combo)

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
        tab.image_changed.connect(self.image_actions.update_state)
        # Nom historique du widget de conversion (Stencil Studio, tests).
        self.png2svg_widget = tab.converter
        converter = tab.converter
        self.image_actions.add(
            tab, has_image=lambda: bool(converter.image_path),
            rotate=lambda clockwise: converter.rotate_image(90 if clockwise else -90),
            clear=converter.clear_image, mirrors=False)       # la conversion n'utilise pas les miroirs
        self.main_tabs_view.addTab(tab, tr("png2svg.tab_title"))
        self.tab_png2svg = tab

    def _build_separation_tab(self):
        """Onglet « Séparation Couleur / Verre » (vue SeparationTab), ses
        réglages (SeparationSettings) et sa logique (SeparationController).
        Masqué au démarrage, ouvert depuis le menu Outils. La tonalité de
        l'image devient l'image de « Graver une image » (ImageController.set_image),
        dont le calque noir revient aux aperçus (ImageController.processed)."""
        tab = SeparationTab()
        self.separation_settings = SeparationSettings(self)
        tab.bind_settings(self.separation_settings)
        self.separation = SeparationController(
            self.separation_settings, self.image_settings,
            frame_args=tab.frame_args, engrave_lmm=lambda: self.spin_lmm.value(),
            dialogs=self.dialogs,
            engraved=lambda: self.image.processed_array,
            image_busy=self.image.is_busy,
            current_preview=tab.preview_tabs.currentIndex,
            is_visible=tab.isVisible,
            busy=busy_cursor,
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
        separation.source_changed.connect(self.image_actions.update_state)
        self.image_actions.add(
            tab, has_image=separation.has_image,
            rotate=lambda clockwise: separation.rotate_image(-90 if clockwise else 90),   # PIL : positif = antihoraire
            clear=separation.clear)
        separation.image_loaded.connect(tab.fit_plate_to_image)
        separation.image_rotated.connect(tab.swap_plate_size)
        separation.preview_ready.connect(tab.show_preview)
        separation.previews_invalidated.connect(separation.refresh_previews)
        separation.engrave_dpi_changed.connect(tab.set_engrave_dpi)
        separation.tone_ready.connect(self.image.set_image)
        # Liens avec « Graver une image » : réglages du verre rendus quand une image y est
        # chargée, oubliés à la réinitialisation ; calque noir recalculé : aperçus à refaire.
        self.image.loading_file.connect(separation.release_glass_settings)
        self.image.resetting.connect(separation.forget_glass_settings)
        self.image.processed.connect(lambda *_args: separation.engraved_changed())
        self.tab_separation = tab
        tab.set_engrave_dpi(separation.engrave_dpi())
        self.main_tabs_view.addTab(tab, tr("sep.tab_title"))

    def _build_vector_editor_tab(self):
        """Onglet « Graver une image vectorielle » (vue VectorEditorTab), son canevas (vue du document) et sa
        logique : VectorEditorController, bibliothèque de modèles, panneau des propriétés."""
        canvas = self.vector_canvas = VectorCanvasView(self.layer_manager, document=self.vector_document)
        editor = self.vector_editor = VectorEditorController(
            self.vector_document, canvas, self.layer_manager, self.machine, self.dialogs, self,
            image_frame=self._image_frame, busy=busy_cursor,
        )
        # Bibliothèque de modèles (resources/library/) : import dans l'éditeur.
        self.library = LibraryController(
            self, self.layer_manager,
            bed_height=lambda: self.machine.bed_h,
            add_to_vector_editor=editor.add_objects,
            dialogs=self.dialogs,
        )
        tab = VectorEditorTab(canvas)
        commands = {**editor.commands(), "library": self.library.open}
        tab.command.connect(lambda name: commands[name]())
        tab.draw_tool_requested.connect(editor.choose_draw_tool)
        editor.draw_tool_changed.connect(tab.show_draw_tool)
        editor.show_editor.connect(lambda: self.main_tabs_view.setCurrentWidget(tab))
        editor.status.connect(self.show_status_message)
        # Panneau des propriétés : rempli d'après la sélection, saisies transmises au contrôleur.
        self.vector_properties = VectorPropertiesPanel(tab.properties_widgets, self.layer_manager, canvas, editor,
                                                       parent=self)
        canvas.edit_requested.connect(editor.edit_object)
        canvas.insert_text_requested.connect(editor.insert_text)
        canvas.serial_duplicate_requested.connect(editor.open_serial_duplicate)
        canvas.jig_requested.connect(editor.open_jig_generator)
        canvas.medal_text_requested.connect(editor.open_medal_text)
        # Couleurs des objets suivant celles des calques ; zone de travail à la taille du plateau.
        self.layer_manager.changed.connect(canvas.refresh_all)
        self.tab_machine_params.bed_size_changed.connect(self.window_controller.update_vector_work_area)
        self.main_tabs_view.addTab(tab, tr("ui.tab_vector_editor"))
        self.tab_vector_editor = tab

    def _build_2d_preview_tab(self):
        """Onglet « Visualisation 2D G-Code » : il dessine le G-Code généré ou
        importé (JobDisplay.plot), la position de la tête et les traits
        déjà gravés pendant un job."""
        tab = Preview2DTab(self.job_position_box)
        tab.plot_clicked.connect(self.job.apply_matrix_cell)
        tab.log.connect(self.log_message)
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

    # -- Événements de la fenêtre

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_autosave_recovery_pending", False):
            self._autosave_recovery_pending = False
            QTimer.singleShot(0, self.project.offer_autosave_recovery)

    def closeEvent(self, event):
        self.state.save_machine_settings()
        self.tabs.save_splitter_sizes()
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
                self.image.load_path(file_path)
                break
            if file_path.lower().endswith(('.svg', '.dxf')):
                self.vector_editor.import_file(file_path)
                break

    # -- Messages : barre d'état et journal

    def show_status_message(self, text, tooltip=None):
        """Raccourci vers StatusBar.show_info, utilisé par les contrôleurs et Stencil Studio."""
        self.statusBar().show_info(text, tooltip)

    def log_message(self, text):
        """Message d'une action (connexion, GRBL, file, projet…) : barre d'état, et journal de
        débogage pour l'historique. Jamais dans la console : elle ne contient que le G-Code
        généré, relu par l'export et la file d'attente."""
        text = str(text)
        log.info("Message : %s", text.strip())
        short = status_text(text)
        if short:
            self.show_status_message(short, text.strip())
