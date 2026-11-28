"""Fenêtre principale de l'application.

FullLaserStudio construit la fenêtre (init_ui), crée les modèles et les
contrôleurs, branche les signaux de ses panneaux et du menu (_connect_app_actions)
et gère ses événements (fermeture, glisser-déposer). Ce qui agit sur la fenêtre :
controllers/window.py WindowController (réglages, actions transversales), MainTabs (onglets,
plein écran, panneau du bas), JobDisplay (résultats du job, état du graveur),
ImageToolbarActions (actions de la barre d'outils sur l'image).
"""
from types import SimpleNamespace

from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QMessageBox, QScrollArea, QSplitter, QTabWidget,
                             QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from laser_studio.controllers.engraver import EngraverController
from laser_studio.controllers.first_steps import FirstStepsController
from laser_studio.controllers.job import JobController
from laser_studio.controllers.machine_connection import MachineConnection
from laser_studio.controllers.project import ProjectController
from laser_studio.core.debug_log import get_logger
from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import tr
from laser_studio.gcode.rotary import RotaryConfig, surface_y
from laser_studio.models.grbl import GrblConfig
from laser_studio.models.image_settings import ImageSettings, ImageSettingsHistory
from laser_studio.models.job_placement import JobPlacement
from laser_studio.models.layers import LayersModel
from laser_studio.models.machine import MachineConfig
from laser_studio.models.vector_document import VectorDocument
from laser_studio.ui.app.image_actions import ImageToolbarActions
from laser_studio.ui.app.job_display import JobDisplay, set_homing_available
from laser_studio.ui.app.menu import AppActions, AppMenuBar, AppToolBar
from laser_studio.ui.app.bottom_panel import BottomPanel
from laser_studio.ui.app.tabs import MainTabs
from laser_studio.controllers.window import WindowController
from laser_studio.ui.app.window_forms import WindowForms
from laser_studio.ui.app.window_state import WindowState
from laser_studio.ui.binding import bind
from laser_studio.ui.machine.builder import build_machine_panel
from laser_studio.ui.machine.macros_builder import build_macros
from laser_studio.controllers.job_history import JobHistoryRecorder, duration_factor
from laser_studio.models.job_history import JobHistory
from laser_studio.ui.machine.job_position import JobPositionBox
from laser_studio.ui.dialogs.macros import MacroEditorDialog
from laser_studio.ui.settings.appearance import AppearancePage
from laser_studio.ui.settings.power_page import PowerPage
from laser_studio.controllers.power_inhibit import PowerInhibitController
from laser_studio.ui.settings.toolbar_page import ToolbarPage
from laser_studio.ui.settings.macros_page import MacrosPage
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
from laser_studio.ui.dialogs.first_steps import open_first_steps
from laser_studio.ui.user_dialogs import UserDialogs
from laser_studio.ui.wheel_guard import install_wheel_guard
from laser_studio.ui.vector_editor.builder import build_vector_editor
from laser_studio.ui.widgets import FloatingToolBar

log = get_logger()


class FullLaserStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("ui.window_title"))
        self.resize(1600, 980)
        
        self.setAcceptDrops(True)
        # La molette ne change pas une valeur au passage de la souris (ui/wheel_guard.py).
        install_wheel_guard(QApplication.instance())
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
        # Placement du job (taille, décalage, origine, lignes/mm, optimisation du chemin) : les champs de
        # « Graver une image » et du cadre « Position du job » y sont liés, la logique le lit ici.
        self.placement = JobPlacement(self)

        # Job : paramètres, contrôles avant génération, génération du G-Code
        # (thread), estimation, export / import, matrice de test. Il lit l'état
        # de l'interface par les fonctions ci-dessous ; JobDisplay (créé par
        # init_ui) affiche ses résultats : console, aperçu 2D.
        self.job = JobController(
            self.layer_manager, self.grbl, self.machine, self.image_settings, self.placement, self.vector_document,
            self.dialogs, image=lambda: self.image, parent=self,
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
            gcode_stale=self.job.is_stale,
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
        self.main_tabs_view.tabBar().setFocusPolicy(Qt.FocusPolicy.NoFocus)   # pas de cadre de focus (VS Code)
        self._build_center_tabs()
        center_bottom_scroll = self._build_machine_panel()
        center_panel.addWidget(self.center_v_splitter)
        self._build_job_tabs()

        # Panneau du bas, comme celui de VS Code : graveur, console G-Code et file d'attente, sous les onglets
        # de travail sur tous les onglets ; replié ou déplié (Ctrl+J, menu Affichage).
        self.bottom_panel = BottomPanel(
            [("machine", tr("panel.machine"), center_bottom_scroll),
             ("gcode", tr("ui.tab_console_gcode"), self.tab_console_gcode),
             ("queue", tr("ui.tab_job_queue"), self.tab_job_queue)],
            self.center_v_splitter)
        self.center_v_splitter.addWidget(self.bottom_panel)
        self.center_v_splitter.setCollapsible(1, False)       # sa barre d'onglets reste toujours visible
        self.tabs = MainTabs(
            self.main_tabs_view, self,
            splitter=self.center_v_splitter, bottom_panel=self.bottom_panel,
            preview_splitter=self.tab_vector_2d.splitter,
            vector_editor=self.tab_vector_editor, recenter_vector_editor=self.vector_canvas.navigation.request_recenter,
            png2svg=self.tab_png2svg, parent=self,
        )
        self._build_job_display()
        # Onglet Séparation affiché : ses aperçus, en retard, sont refaits.
        self.main_tabs_view.currentChanged.connect(
            lambda index: self.main_tabs_view.widget(index) is self.tab_separation and self.separation.refresh_if_dirty())
        self.main_tabs_view.currentChanged.connect(self.image_actions.update_state)
        # Onglets masqués au démarrage, ouverts à la demande depuis le menu Outils (MainTabs.show).
        for tab in (self.tab_separation, self.tab_png2svg):
            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)
        self.tabs.set_closable((self.tab_separation, self.tab_png2svg))     # croix : refermés, rouverts par Outils
        self._add_image_floating_toolbars()
        self.image_actions.update_state()

        # Largeur minimale EXPLICITE du centre. Sans elle, la largeur minimale serait calculée
        # d'après le contenu : la barre d'outils de l'éditeur vectoriel (11 boutons, ~1500 px) et la
        # rangée d'alignement imposeraient environ 1500 px à la fenêtre. Trop étroit, le centre se
        # contente de serrer ses boutons.
        center_widget.setMinimumWidth(480)
        # Séparateurs onglets / panneau du bas et aperçu / statistiques : positions mémorisées.
        self.center_v_splitter.splitterMoved.connect(self.tabs.save_splitter_sizes)
        self.tab_vector_2d.splitter.splitterMoved.connect(self.tabs.save_splitter_sizes)

        main_layout.addWidget(center_widget)
        # Historique des gravures : chaque job envoyé (direct ou file d'attente) y est noté à sa fin.
        self.job_history = JobHistory(parent=self)
        self.job_history_recorder = JobHistoryRecorder(self.job_history, self.connection, context=lambda: {
            "profile": self.machines.current_name(), "max_speed": self.machine.max_speed,
            "accel": self.machine.accel, "s_max": self.grbl.smax, "laser_cmd": self.grbl.laser_cmd})
        self.engraver.stream_starting.connect(self.job_history_recorder.job_started)
        self.engraver.stream_ended.connect(self.job_history_recorder.job_ended)
        self.job.generated.connect(self.job_history_recorder.remember_estimate)
        # Macros de l'utilisateur : boutons du panneau des actions de job, filtrés par profil machine.
        # « Gérer les macros » : la page « Macros » de la fenêtre Paramètres.
        self.macros = build_macros(self.machine_panel.job_actions_panel, self.engraver,
                                   self.machines, self.dialogs, parent=self,
                                   manage=lambda: self.window_controller.show_settings_window("macros"))
        # Empêcher la mise en veille pendant une gravure (ou tant que connecté), selon les préférences.
        self.power_inhibit = PowerInhibitController(
            self.engraver, self.connection, log=self.log_message, parent=self)
        # Actions qui touchent plusieurs parties de la fenêtre (thème, langue, réglages, caméra, matrice,
        # Stencil Studio) : créé une fois toutes ces parties construites, il les reçoit explicitement.
        self.window_controller = WindowController(
            self, forms=WindowForms(self), dialogs=self.dialogs, actions=self.app_actions, tabs=self.tabs,
            machine=self.machine, job=self.job, image=self.image, job_history=self.job_history,
            placement=self.placement,
            vector=SimpleNamespace(controller=self.vector_editor, canvas=self.vector_canvas, tab=self.tab_vector_editor),
            pages={"machine_params": self.tab_machine_params, "test_matrix": self.tab_matrix,
                   "matrix_image": self.matrix_image, "resolution": self.resolution_box, "layers": self.layers_tab,
                   "preview": self.tab_vector_2d},
            settings_pages={"machine_params": (self.tab_machine_params, "tab.machine_params"),
                            "grbl": (self.tab_grbl_config, "tab.grbl_config"),
                            "appearance": (AppearancePage(self.app_actions.language_actions,
                                                          self.app_actions.theme_actions), "settings.appearance"),
                            "power": (PowerPage(self.power_inhibit), "settings.power"),
                            "toolbar": (ToolbarPage(self.app_actions,
                                                    on_apply=self.main_toolbar.rebuild),
                                        "settings.toolbar"),
                            "macros": (MacrosPage(lambda: MacroEditorDialog(*self.macros.editor_args()),
                                                  self.macros.save), "macros.title"),
                            "test_matrix": (self.tab_matrix, "tab.test_matrix")},
            main_tabs={"tab_png2svg": self.tab_png2svg, "tab_separation": self.tab_separation},
        )
        # Menus abonnés une fois toute la fenêtre construite.
        self._connect_app_actions(self.app_actions)
        self.project.refresh_recent_projects()
        self.window_controller.schedule_stencil_preload()

    def _connect_app_actions(self, actions):
        """Abonne les parties de la fenêtre aux signaux du menu et de la barre d'outils (AppActions)."""
        controller = self.window_controller
        # Fichier
        actions.save_project_requested.connect(self.project.save)
        actions.gcode_export_requested.connect(
            lambda extension: self.job.export_gcode(extension, self.tab_console_gcode.gcode()))
        actions.open_project_requested.connect(self.project.open)
        actions.recent_project_requested.connect(self.project.open_path)
        actions.quit_requested.connect(self.close)
        # Paramètres et outils
        actions.settings_window_requested.connect(controller.show_settings_window)
        self.main_toolbar.customize_requested.connect(
            lambda: controller.show_settings_window("toolbar")
        )
        actions.language_selected.connect(controller.select_language)
        actions.theme_selected.connect(controller.change_theme)
        actions.stencil_studio_requested.connect(lambda: controller.stencil().open())
        actions.main_tab_requested.connect(controller.show_main_tab)
        in_editor, generators = controller.run_in_vector_editor, self.vector_generators
        actions.vector_import_requested.connect(lambda: in_editor(self.vector_editor.importer.open_dialog))
        actions.generator_requested.connect(lambda kind: in_editor(lambda: generators.open_generators(kind)))
        actions.camera_requested.connect(controller.open_camera_dialog)
        actions.history_requested.connect(controller.show_job_history)
        # Affichage
        actions.fullscreen_requested.connect(self.tabs.toggle_current_fullscreen)
        panel = self.bottom_panel
        actions.job_queue_requested.connect(lambda: panel.show_page("queue"))
        # Ctrl+J : action de la fenêtre (plus de menu Affichage), comme dans VS Code.
        self.addAction(actions.bottom_panel)
        actions.bottom_panel_toggled.connect(lambda shown: panel.set_collapsed(not shown))
        actions.bottom_panel.setChecked(not panel.is_collapsed())
        panel.collapsed_changed.connect(lambda collapsed: actions.bottom_panel.setChecked(not collapsed))
        self.statusBar().machine_clicked.connect(lambda: panel.show_page("machine"))
        self.tab_vector_editor.vectorize_requested.connect(lambda: self.tabs.show(self.tab_png2svg))
        # Aide
        actions.documentation_requested.connect(controller.show_documentation)
        self.first_steps = FirstStepsController(self.connection, {
            "machine": self.tab_machine_params.catalog_requested.emit,
            "connect": lambda: (self.bottom_panel.show_page("machine"), self.engraver.ensure_connected()),
            "home": self.engraver.home,
            "frame": self.engraver.frame,
        }, ui_preferences(), parent=self)
        actions.first_steps_requested.connect(lambda: open_first_steps(self, self.first_steps))
        actions.about_requested.connect(controller.forms.about)
        actions.support_requested.connect(controller.forms.support)
        actions.community_requested.connect(controller.forms.community)
        actions.coffee_requested.connect(controller.forms.coffee)
        # Image
        actions.image_undo_requested.connect(self.image_history.undo)
        actions.image_redo_requested.connect(self.image_history.redo)
        actions.image_delete_requested.connect(self.image_actions.delete)
        actions.image_rotate_requested.connect(self.image_actions.rotate)
        actions.mirror_changed.connect(self.image.schedule_processing)
        actions.image_reset_requested.connect(self.image.reset_settings)
        # G-code
        actions.estimate_requested.connect(self.job.estimate)
        actions.generate_requested.connect(self.job.generate)
        actions.send_job_requested.connect(lambda: self.engraver.send_job())
        actions.frame_requested.connect(self.engraver.frame)
        actions.frame_contour_requested.connect(lambda: self.engraver.frame(contour=True))
        actions.pause_requested.connect(self.engraver.pause)
        actions.resume_requested.connect(self.engraver.resume)
        actions.emergency_stop_requested.connect(self.engraver.emergency_stop)
        # G-Code à régénérer : mention cliquable dans la barre d'état ; une nouvelle image tramée compte aussi.
        self.job.gcode_stale_changed.connect(self.statusBar().set_gcode_stale)
        self.statusBar().regenerate_clicked.connect(self.job.generate)
        self.image.processed.connect(self.job.mark_stale)
        actions.gcode_import_requested.connect(self.job.import_gcode)

    def _build_app_menus(self):
        """Menu et barre d'outils : AppActions crée les actions partagées et
        émet les signaux, AppMenuBar et AppToolBar ne font que les ranger
        (abonnés par _connect_app_actions)."""
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
            show_machine_panel=lambda: self.bottom_panel.show_page("machine"),
            duration_factor=lambda: duration_factor(self.job_history.entries(), self.machines.current_name()),
            surface_y=lambda y: surface_y(y, RotaryConfig.from_settings(self.grbl)),
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
        """Barres des aperçus d'image (verticale à droite pour « Graver une image », flottantes ailleurs) : mêmes
        actions que celles de l'ancienne barre d'outils (état actif / coché partagé, voir ImageToolbarActions.update_state).

        Même ordre que dans l'éditeur vectoriel : les actions propres à la vue, puis annuler / refaire et
        les loupes, toujours au bout à droite.

        « Graver une image » : recadrer, pivoter, miroirs, réinitialiser, supprimer, annuler / refaire, loupes.
        Séparation : pivoter, miroirs, réinitialiser (réglages image et miroirs qu'elle reprend),
        supprimer. PNG ⇒ SVG : pivoter, supprimer (miroirs et réglages image n'y servent pas)."""
        a = self.app_actions
        rotate = [a.image_rotate_left, a.image_rotate_right]
        mirrors = [a.mirror_h, a.mirror_v]
        # « Graver une image » : barre verticale à droite des aperçus, comme celle de l'éditeur vectoriel.
        image_bar = self.tab_previews.edit_toolbar
        for action in (self.tab_previews.crop_action, None, *rotate, None, *mirrors, None, a.image_reset,
                       a.image_delete, None, a.image_undo, a.image_redo,
                       None, self.tab_previews.zoom_in_action, self.tab_previews.zoom_out_action):
            if action is None:
                image_bar.addSeparator()
            else:
                image_bar.addAction(action)
        self.separation_floating_toolbar = FloatingToolBar(
            [*rotate, None, *mirrors, None, a.image_reset, a.image_delete],
            self.tab_separation.preview_tabs, top_margin=34)
        self.png2svg_floating_toolbar = FloatingToolBar(
            [*rotate, None, a.image_delete], self.tab_png2svg.converter.splitter)

    def _build_machine_panel(self):
        """Panneau machine (build_machine_panel), dans une zone qui défile : l'onglet « Graveur » du panneau
        du bas, sous les onglets dans `center_v_splitter`. Renvoie la zone de défilement."""
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
        self.center_v_splitter.addWidget(self.main_tabs_view)       # puis le panneau du bas (init_ui)
        self.center_v_splitter.setStretchFactor(0, 3)
        self.center_v_splitter.setStretchFactor(1, 1)
        return center_bottom_scroll

    def _build_settings_pages(self):
        """Pages des fenêtres du menu Paramètres (WindowController.show_settings_window) : Paramètres du
        graveur (profils machine), Matrice de test, Configuration GRBL. La matrice suit les lignes/mm
        de « Graver une image » (WindowController.sync_matrix_lines_mm)."""
        # Le contrôleur de la fenêtre est créé à la fin d'init_ui : les boutons l'appellent au moment du clic.
        self.tab_machine_params, self.machines = build_machine_params_page(
            self.machine, self.state, self.dialogs, self,
            link_layers_to_focal=lambda: self.layers_tab.link_all_to_focal(),
            focal_changed=lambda focal: self.window_controller.machine_focal_changed(focal))
        self.tab_matrix, self.matrix_image = build_test_matrix_page(
            self.placement.lines_mm, generate=lambda: self.window_controller.generate_test_matrix_and_show(),
            loaded_image=self._loaded_image_and_width,
            image_settings=self.image_settings.processing_params)
        self.tab_grbl_config = build_grbl_config_page(self.grbl, self.job, self.engraver, self.machines)
        # Résolution de « Graver une image » reprise par la matrice de test (même densité de lignes).
        self.placement.changed.connect(
            lambda changes: self.tab_matrix.set_lines_mm(changes["lines_mm"]) if "lines_mm" in changes else None)

    def _build_image_tab(self):
        """Onglet « Graver une image » (build_image_tab) et cadre « Position du job ». Construit tôt :
        la matrice de test lit ses lignes/mm, l'aperçu 2D reçoit le cadre « Position du job ».
        L'onglet est placé dans les onglets par init_ui."""
        self.tab_previews, self.image = build_image_tab(
            self.image_settings, self.image_history, self.placement, self.machine, self.layer_manager, self.dialogs,
            self.image_actions, configure_focal=lambda: self.window_controller.goto_focal_settings(),
            compare=lambda: self.window_controller.show_dither_comparison(),
            status=self.show_status_message, parent=self)
        self.resolution_box = self.tab_previews.settings.resolution_box
        # Origine et décalage du job, liés au placement (affichés dans l'onglet Visualisation 2D).
        self.job_position_box = JobPositionBox()
        self.job_position_box.bind_placement(self.placement)

    def _loaded_image_and_width(self):
        """(image, largeur en mm) de « Graver une image », ou None."""
        if not self.image.has_image():
            return None
        return self.image.raw_image, self.placement.width_mm

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
        self.tab_separation, self.separation = build_separation_tab(
            self.image_settings, self.image, self.job, self.dialogs, self.image_actions, self,
            lines_mm=lambda: self.placement.lines_mm)
        tabs.addTab(self.tab_separation, tr("sep.tab_title"))
        # Résolution de « Graver une image » reprise par la Séparation (affichage, tonalité renvoyée).
        self.tab_previews.settings.resolution_changed.connect(lambda _lmm: self.separation.resolution_changed())
        editor = build_vector_editor(
            self.vector_document, self.layer_manager, self.machine, self.dialogs, self,
            image_frame=self.job.image_frame, overscan_margin=self.job.overscan_margin, status=self.show_status_message,
            show_tab=tabs.setCurrentWidget)
        self.tab_vector_editor, self.vector_canvas = editor.tab, editor.canvas
        self.vector_editor, self.library, self.vector_properties = editor.controller, editor.library, editor.properties
        self.vector_generators, self.vector_layout = editor.generators, editor.layout
        # Fond caméra de l'éditeur : capture et image projetée sur le canevas (WindowController, caméra créée à
        # la première utilisation).
        editor.tab.camera_background_toggled.connect(
            lambda enabled: self.window_controller.set_camera_background_enabled(enabled))
        editor.tab.camera_refresh_requested.connect(lambda: self.window_controller.refresh_camera_clicked())
        tabs.addTab(self.tab_vector_editor, tr("ui.tab_vector_editor"))
        tabs.addTab(self.layers_tab, tr("tab.layers"))
        # Visualisation 2D : G-Code généré ou importé (JobDisplay.plot), position de la tête et traits
        # déjà gravés pendant un job ; un clic sur une case de la matrice de test l'applique.
        self.tab_vector_2d = Preview2DTab(self.job_position_box)
        bind(self.tab_vector_2d.optimize_path_check, self.placement, "optimize_path")
        # Plateau de la machine dans l'aperçu 2D : repère tant qu'aucun job n'est généré.
        self.tab_vector_2d.set_bed(self.machine.bed_w, self.machine.bed_h)
        self.machine.changed.connect(lambda changes: self.tab_vector_2d.set_bed(self.machine.bed_w, self.machine.bed_h)
                                     if {"bed_w", "bed_h"} & set(changes) else None)
        self.tab_vector_2d.plot_clicked.connect(self.job.apply_matrix_cell)
        self.tab_vector_2d.log.connect(self.log_message)
        tabs.addTab(self.tab_vector_2d, tr("ui.tab_2d_preview"))

    def _build_job_tabs(self):
        """Console / G-Code et File d'attente (onglets du panneau du bas), qui envoie ses jobs par le
        contrôleur du graveur et suit l'envoi dans le panneau machine."""
        self.tab_console_gcode = ConsoleTab()
        self.tab_job_queue, self.job_queue = build_job_queue_tab(
            self.connection, self.engraver, self.dialogs, self,
            current_gcode=self.tab_console_gcode.gcode, log=self.log_message,
            sent_log=self.machine_panel.sent_gcode_log)

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
            if getattr(self, "power_inhibit", None) is not None:
                self.power_inhibit.shutdown()
            self.connection.shutdown()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Fermeture volontaire sans enregistrer : la sauvegarde automatique ne
            # doit pas être proposée en récupération au prochain démarrage.
            self.project.discard_autosave()
            self._flush_background_writes()
            if getattr(self, "power_inhibit", None) is not None:
                self.power_inhibit.shutdown()
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
                self.vector_editor.importer.import_file(file_path)
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
