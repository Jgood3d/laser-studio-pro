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
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from laser_studio.controllers.engraver import EngraverController
from laser_studio.controllers.job import JobController
from laser_studio.controllers.machine_connection import MachineConnection
from laser_studio.controllers.project import ProjectController
from laser_studio.core.debug_log import get_logger
from laser_studio.i18n import tr
from laser_studio.models.grbl import GrblConfig
from laser_studio.models.image_settings import ImageSettings, ImageSettingsHistory
from laser_studio.models.layers import LayersModel
from laser_studio.models.machine import MachineConfig
from laser_studio.models.vector_document import VectorDocument
from laser_studio.ui.app.image_actions import ImageToolbarActions
from laser_studio.ui.app.job_display import JobDisplay, set_homing_available
from laser_studio.ui.app.menu import AppActions, AppMenuBar, AppToolBar
from laser_studio.ui.app.tabs import GCODE_CONSOLE_SETTING, JOB_QUEUE_SETTING, MainTabs
from laser_studio.ui.app.window_controller import WindowController
from laser_studio.ui.app.window_state import WindowState
from laser_studio.ui.binding import bind
from laser_studio.ui.machine.builder import build_machine_panel
from laser_studio.ui.machine.job_position import JobPositionBox
from laser_studio.ui.settings.grbl_config.builder import build_grbl_config_page
from laser_studio.ui.settings.machine_params.builder import build_machine_params_page
from laser_studio.ui.settings.test_matrix.builder import build_test_matrix_page
from laser_studio.ui.statusbar import StatusBar
from laser_studio.ui.tabs.console import ConsoleTab
from laser_studio.ui.tabs.image.builder import build_image_tab
from laser_studio.ui.tabs.job_queue.builder import build_job_queue_tab
from laser_studio.ui.tabs.layers.builder import build_layers_tab
from laser_studio.ui.tabs.png2svg.builder import build_png2svg_tab
from laser_studio.ui.tabs.preview_2d import Preview2DTab
from laser_studio.ui.tabs.separation.builder import build_separation_tab
from laser_studio.ui.user_dialogs import UserDialogs
from laser_studio.ui.vector_editor.builder import build_vector_editor
from laser_studio.ui.widgets import FloatingToolBar

log = get_logger()


class FullLaserStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("ui.window_title"))
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
            optimize_path=lambda: self.tab_vector_2d.optimize_path_check.isChecked(),
            lines_mm=lambda: self.resolution_box.lines_per_mm(),
            material_summary=lambda: self.image.material_summary(),
            parent=self,
        )
        self.job.log.connect(self.log_message)
        self.job.status.connect(self.show_status_message)
        # Graveur : port, connexion, pilotage, envoi des jobs, configuration GRBL.
        self.engraver = EngraverController(
            self.connection, self.grbl, self.dialogs,
            selected_port=lambda: self.machine_panel.connection_panel.selected_port(),
            current_gcode=lambda: self.tab_console_gcode.gcode(),
            job_geometry=lambda: self.job.build_params(),
            set_homing_available=lambda available, tip: set_homing_available(
                (self.tab_grbl_config.homing_check, self.tab_matrix.homing_check), available, tip),
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
        self._build_image_tab()
        self._build_settings_pages()
        self.layers_tab, self.materials = build_layers_tab(
            self.layer_manager, self.machine, self.machines, self.state, self.dialogs, self)
        self.setStatusBar(StatusBar(self))

        center_widget = QWidget()
        center_panel = QVBoxLayout(center_widget)
        center_panel.setContentsMargins(0, 0, 0, 0)
        self.main_tabs_view = QTabWidget()
        self.main_tabs_view.setMovable(True)
        self._build_center_tabs()
        center_bottom_scroll = self._build_machine_panel()
        center_panel.addWidget(self.center_v_splitter)
        self._build_job_tabs()

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
            self.statusBar(), self.tab_console_gcode, self.tab_vector_2d, self.machine_panel,
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
            [*rotate, None, a.image_delete], self.tab_png2svg.converter.splitter)

    def _build_machine_panel(self):
        """Panneau machine sous les onglets (build_machine_panel), dans une zone qui défile, placée sous
        les onglets dans `center_v_splitter`. Renvoie la zone de défilement."""
        self.machine_panel = build_machine_panel(
            self.engraver, self.connection, self.machine.max_speed,
            max_speed_changed=self.tab_machine_params.max_speed_changed, help_parent=self)
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

    def _build_settings_pages(self):
        """Pages des fenêtres du menu Paramètres (WindowController.show_settings_window) : Paramètres du
        graveur (profils machine), Matrice de test, Configuration GRBL. La matrice suit les lignes/mm
        de « Graver une image » (WindowController.sync_matrix_lines_mm)."""
        controller = self.window_controller
        self.tab_machine_params, self.machines = build_machine_params_page(
            self.machine, self.state, self.dialogs, self,
            link_layers_to_focal=lambda: self.layers_tab.link_all_to_focal(),
            focal_changed=controller.machine_focal_changed)
        self.tab_matrix, self.matrix_image = build_test_matrix_page(
            self.resolution_box.lines_per_mm(), generate=controller.generate_test_matrix_and_show,
            loaded_image=self._loaded_image_and_width,
            image_settings=self.tab_previews.settings.processing_settings)
        self.tab_grbl_config = build_grbl_config_page(self.grbl, self.job, self.engraver, self.machines)
        for kind, page, title_key in (("machine_params", self.tab_machine_params, "tab.machine_params"),
                                      ("grbl", self.tab_grbl_config, "tab.grbl_config"),
                                      ("test_matrix", self.tab_matrix, "tab.test_matrix")):
            controller.add_settings_page(kind, page, title_key)
        # Résolution de « Graver une image » reprise par la matrice de test (même densité de lignes).
        self.tab_previews.settings.resolution_changed.connect(self.tab_matrix.set_lines_mm)

    def _build_image_tab(self):
        """Onglet « Graver une image » (build_image_tab) et cadre « Position du job ». Construit tôt :
        la matrice de test lit ses lignes/mm, l'aperçu 2D reçoit le cadre « Position du job ».
        L'onglet est placé dans les onglets par init_ui."""
        controller = self.window_controller
        self.tab_previews, self.image = build_image_tab(
            self.image_settings, self.image_history, self.machine, self.layer_manager, self.dialogs,
            self.image_actions, configure_focal=controller.goto_focal_settings, compare=controller.show_dither_comparison,
            status=self.show_status_message, parent=self)
        self.resolution_box = self.tab_previews.settings.resolution_box
        # Origine lue par code (job_position_box.origin()) : génération, projets, profils.
        self.job_position_box = JobPositionBox()

    def _job_geometry(self):
        """Taille et position du job, lues dans l'interface (voir JobController)."""
        (width, height), (offset_x, offset_y) = self.tab_previews.settings.size_mm(), self.tab_previews.settings.offset_mm()
        return {'width_mm': width, 'height_mm': height, 'origin_pos': self.job_position_box.origin(),
                'offset_x': offset_x, 'offset_y': offset_y}

    def _loaded_image_and_width(self):
        """(image, largeur en mm) de « Graver une image », ou None."""
        if not self.image.has_image():
            return None
        return self.image.raw_image, self.tab_previews.settings.size_mm()[0]

    def _build_center_tabs(self):
        """Onglets du centre, dans l'ordre : Graver une image, Vectorisation, Séparation, éditeur
        vectoriel, Calques, Visualisation 2D (la console et la file d'attente viennent après le panneau
        machine, dont elles dépendent)."""
        tabs = self.main_tabs_view
        tabs.addTab(self.tab_previews, tr("ui.tab_image_tracing"))
        self.tab_png2svg, self.png2svg = build_png2svg_tab(
            self.layer_manager, self.machine, self.dialogs, self.image_actions, self,
            add_to_vector_editor=lambda objects: self.vector_editor.import_objects(objects))
        tabs.addTab(self.tab_png2svg, tr("png2svg.tab_title"))
        self.window_controller.add_main_tab("tab_png2svg", self.tab_png2svg)
        self.tab_separation, self.separation = build_separation_tab(
            self.image_settings, self.image, self.job, self.dialogs, self.image_actions, self,
            lines_mm=self.resolution_box.lines_per_mm)
        tabs.addTab(self.tab_separation, tr("sep.tab_title"))
        # Résolution de « Graver une image » reprise par la Séparation (affichage, tonalité renvoyée).
        self.tab_previews.settings.resolution_changed.connect(lambda _lmm: self.separation.resolution_changed())
        self.window_controller.add_main_tab("tab_separation", self.tab_separation)
        editor = build_vector_editor(
            self.vector_document, self.layer_manager, self.machine, self.dialogs, self,
            image_frame=self.job.image_frame, overscan_margin=self.job.overscan_margin, status=self.show_status_message,
            show_tab=tabs.setCurrentWidget)
        self.tab_vector_editor, self.vector_canvas = editor.tab, editor.canvas
        self.vector_editor, self.library, self.vector_properties = editor.controller, editor.library, editor.properties
        tabs.addTab(self.tab_vector_editor, tr("ui.tab_vector_editor"))
        tabs.addTab(self.layers_tab, tr("tab.layers"))
        # Visualisation 2D : G-Code généré ou importé (JobDisplay.plot), position de la tête et traits
        # déjà gravés pendant un job ; un clic sur une case de la matrice de test l'applique.
        self.tab_vector_2d = Preview2DTab(self.job_position_box)
        self.tab_vector_2d.plot_clicked.connect(self.job.apply_matrix_cell)
        self.tab_vector_2d.log.connect(self.log_message)
        tabs.addTab(self.tab_vector_2d, tr("ui.tab_2d_preview"))

    def _build_job_tabs(self):
        """Console / G-Code (masquée au démarrage, menu Affichage) et File d'attente, qui envoie ses
        jobs par le contrôleur du graveur et suit l'envoi dans le panneau machine."""
        self.tab_console_gcode = ConsoleTab()
        self.main_tabs_view.addTab(self.tab_console_gcode, tr("ui.tab_console_gcode"))
        self.tab_job_queue, self.job_queue = build_job_queue_tab(
            self.connection, self.engraver, self.dialogs, self,
            current_gcode=self.tab_console_gcode.gcode, log=self.log_message,
            sent_log=self.machine_panel.sent_gcode_log)
        self.main_tabs_view.addTab(self.tab_job_queue, tr("ui.tab_job_queue"))

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
            log.warning("Fermeture : écritures en arrière-plan non attendues", exc_info=True)

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
        log.info("Message : %s", str(text).strip())
        self.statusBar().show_log(text)
