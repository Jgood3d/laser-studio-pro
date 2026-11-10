"""Fenêtre principale de l'application.

FullLaserStudio construit la fenêtre (init_ui), branche les signaux de ses
panneaux et gère ses événements (fermeture, glisser-déposer) ; les mixins
apportent le contenu des onglets et la logique.
"""
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QScrollArea,
                             QSplitter, QTabWidget, QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from i18n import tr
from ui.machine import MachinePanel
from ui.settings.grbl_config import GrblConfigPage
from ui.settings.machine_params import MachineParamsPage
from ui.settings.machine_profiles import MachineProfilesPage
from ui.settings.test_matrix import TestMatrixPage
from ui.settings.window import SettingsWindow
from ui.statusbar import StatusBar
from ui.tabs.console import ConsoleTab
from ui.tabs.job_queue import JobQueueTab
from ui.tabs.layers import LayersTab
from ui.tabs.preview_2d import Preview2DTab

from grbl.connection import LaserUSBController
from vector_layers import LayerManager

from ui_setup_mixin import UiSetupMixin
from ui.app.window_controller import WindowControllerMixin
from matrix_image_mixin import MatrixImageMixin
from ui_image_tab import ImageTabMixin
from machine_profiles_mixin import MachineProfilesMixin
from image_processing_mixin import ImageProcessingMixin
from vector_editing_mixin import VectorEditingMixin
from gcode_generation_mixin import GcodeGenerationMixin
from laser_control_mixin import LaserControlMixin
from project_io_mixin import ProjectIOMixin
from job_queue_mixin import JobQueueMixin
from png2svg_mixin import Png2SvgMixin
from machine_profiles_mixin import DEFAULT_MATERIALS_DB
from separation_mixin import SeparationMixin


class FullLaserStudio(QMainWindow, UiSetupMixin, WindowControllerMixin,
                       MatrixImageMixin, ImageTabMixin,
                       MachineProfilesMixin,
                       ImageProcessingMixin,
                       VectorEditingMixin, GcodeGenerationMixin, LaserControlMixin, ProjectIOMixin,
                       JobQueueMixin, Png2SvgMixin, SeparationMixin):
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
        self.job_queue = []
        self._img_undo_stack = []
        self._img_redo_stack = []
        self._img_last_undo_push_time = 0.0

        self.materials_db = dict(DEFAULT_MATERIALS_DB)
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
        self.autosave_timer = QTimer()
        self.autosave_timer.setInterval(5 * 60 * 1000)
        self.autosave_timer.timeout.connect(self.autosave_project)
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
        self.load_job_queue_from_disk()

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
        self._build_image_settings()
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

        self._build_image_tab()

        tab_png2svg = self._init_png2svg_tab()
        self.main_tabs_view.addTab(tab_png2svg, tr("png2svg.tab_title"))

        # --- ONGLET SÉPARATION COULEUR ---
        self.main_tabs_view.addTab(self._init_separation_tab(), tr("sep.tab_title"))

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
        # Onglets masqués au démarrage, ouverts à la demande depuis le menu Outils (show_main_tab).
        for tab in (self.tab_separation, self.tab_png2svg):
            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)
        self._update_bottom_panel_visibility()
        self.update_image_actions_state()

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
            self.job_position_box, self.spin_machine_max_speed.value()
        )
        jog = self.machine_panel.jog_panel
        jog.jog_requested.connect(self.jog_move)
        jog.home_requested.connect(self.send_homing)
        jog.pause_requested.connect(self.send_pause)
        jog.resume_requested.connect(self.send_resume)
        jog.reset_requested.connect(self.send_reset)
        jog.emergency_stop_requested.connect(self.send_kill)
        jog.send_job_requested.connect(self.send_to_laser)
        self.tab_machine_params.max_speed_changed.connect(jog.set_max_speed)

        job_actions = self.machine_panel.job_actions_panel
        job_actions.frame_requested.connect(self.run_frame)
        job_actions.set_work_zero_requested.connect(self.set_work_zero)
        job_actions.go_to_work_zero_requested.connect(self.go_to_work_zero)
        job_actions.repeat_job_requested.connect(self.repeat_last_job)

        self.machine_panel.dro_panel.unlock_requested.connect(
            self.unlock_alarm
        )
        self.machine_panel.console_panel.command_submitted.connect(
            self.send_manual_cmd
        )
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
        page.profile_selected.connect(self._on_machine_profile_selected)
        page.new_profile_requested.connect(self._add_machine_profile)
        page.update_profile_requested.connect(self._update_machine_profile)
        page.delete_profile_requested.connect(self._delete_machine_profile)
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

        Sa liste des ports est celle de la barre d'outils (même modèle), et
        le port choisi est le même des deux côtés.
        """
        ports = self.main_toolbar.ports_combo
        page = MachineProfilesPage(ports.model(), self.materials_db.keys())
        page.port_selected.connect(ports.setCurrentIndex)
        ports.currentIndexChanged.connect(page.set_port_index)
        page.refresh_ports_requested.connect(self.refresh_com_ports)
        page.connect_requested.connect(self.toggle_usb)
        page.material_selected.connect(self.apply_material_profile)
        page.save_material_requested.connect(self.save_material_profile)
        page.new_material_requested.connect(self.add_material_profile)
        page.delete_material_requested.connect(self.delete_material_profile)
        page.export_materials_requested.connect(self.export_material_profiles)
        page.import_materials_requested.connect(self.import_material_profiles)
        # Noms historiques des listes, lus par la logique.
        self.combo_ports = page.ports_combo
        self.combo_mat = page.material_combo
        self.tab_machine_profiles = page

    def _build_grbl_config_page(self):
        """Page « Configuration GRBL », abonnée au dialogue avec le graveur.

        Affichée dans une fenêtre du menu Paramètres (show_settings_window).
        """
        page = GrblConfigPage()
        page.bidir_test_requested.connect(self.generate_bidir_test)
        # Décalage aller/retour : mémorisé dans le profil de la machine.
        page.scan_offset_changed.connect(self._schedule_layer_persist)
        page.read_settings_requested.connect(self.read_grbl_settings)
        page.send_settings_requested.connect(self.send_grbl_settings)
        page.export_settings_requested.connect(self.export_grbl_settings)
        page.import_settings_requested.connect(self.import_grbl_settings)
        page.link_settings_to_profile_requested.connect(
            self.save_grbl_settings_to_profile
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
        page.choose_image_requested.connect(self._mat_choose_image)
        page.use_loaded_image_requested.connect(self._mat_use_loaded_image)
        page.image_test_toggled.connect(self._on_mat_image_test_toggled)
        # Nom historique : décochée et grisée avec chk_homing quand le
        # graveur n'a pas de homing ($22=0, voir LaserControlMixin).
        self.chk_mat_homing = page.homing_check
        self.tab_matrix = page

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
        self.layers_tab.layers_changed.connect(self._schedule_layer_persist)

    def _build_2d_preview_tab(self):
        """Onglet « Visualisation 2D G-Code », abonné à la génération.

        La génération dessine dans son graphique (plot_widget) et y place
        la tête du laser (gcode_position_marker).
        """
        tab = Preview2DTab()
        tab.display_options_changed.connect(
            self.on_flip_raster_preview_changed
        )
        tab.plot_clicked.connect(self._on_plot_clicked)
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
        """Onglet « Console / G-Code », abonné à l'export du G-Code."""
        tab = ConsoleTab()
        tab.export_requested.connect(self.export_gcode_with_ext)
        tab.fullscreen_requested.connect(
            lambda: self._toggle_fullscreen_tab(
                "tab_console_gcode", "ui.tab_console_gcode"
            )
        )
        # Nom historique de la console : toute l'application y écrit
        # (G-Code généré, messages du graveur, Stencil Studio…).
        self.txt_console = tab.console_edit
        self.main_tabs_view.addTab(tab, tr("ui.tab_console_gcode"))
        self.tab_console_gcode = tab

    def _build_job_queue_tab(self):
        """Onglet « File d'attente », abonné à la logique de la file."""
        tab = JobQueueTab()
        tab.add_current_requested.connect(self.add_current_gcode_to_queue)
        tab.remove_selected_requested.connect(self.remove_selected_from_queue)
        tab.clear_requested.connect(self.clear_job_queue)
        tab.run_requested.connect(self.run_job_queue)
        tab.reordered.connect(self._on_queue_reordered)
        # Noms historiques, lus par la file d'attente et l'envoi du G-Code.
        self.list_job_queue = tab.queue_list
        self.btn_run_queue = tab.run_button
        self.lbl_queue_status = tab.status_label
        self.txt_sent_gcode = tab.sent_gcode_edit
        self.main_tabs_view.addTab(tab, tr("ui.tab_job_queue"))
        self.tab_job_queue = tab

    # -- Événements de la fenêtre

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_autosave_recovery_pending", False):
            self._autosave_recovery_pending = False
            QTimer.singleShot(0, self.check_for_autosave_recovery)

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
            if not self.save_project():
                event.ignore()
                return
            self._flush_background_writes()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Fermeture volontaire sans enregistrer : la sauvegarde automatique ne
            # doit pas être proposée en récupération au prochain démarrage.
            self._clear_autosave()
            self._flush_background_writes()
            event.accept()
        else:
            event.ignore()

    def _flush_background_writes(self):
        """Attend (au plus quelques secondes) la fin des sauvegardes en
        arrière-plan — file d'attente, sauvegarde automatique — avant que le
        processus ne s'arrête, sinon une écriture en cours serait perdue."""
        try:
            from app_utils import get_background_writer
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

    # -- Fenêtres annexes : plein écran d'un onglet, réglages, messages

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

    def _toggle_fullscreen_tab(self, tab_attr, title_key):
        tab_widget = getattr(self, tab_attr, None)
        if tab_widget is None:
            return
        idx = self.main_tabs_view.indexOf(tab_widget)
        if idx == -1:
            return

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.WindowType.Window)
        dialog.setWindowTitle(tr(title_key))

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(4, 4, 4, 4)

        btn_close_fullscreen = QPushButton(tr("vector.close_fullscreen"))
        btn_close_fullscreen.setStyleSheet(
            "background-color: #8f2b2b; color: white; padding: 6px; font-weight: bold;"
        )
        btn_close_fullscreen.clicked.connect(dialog.close)
        dlg_layout.addWidget(btn_close_fullscreen)

        dlg_layout.addWidget(tab_widget)
        tab_widget.setVisible(True)
        self._show_fullscreen_control(tab_widget, False)

        def restore(_result=None):
            self._show_fullscreen_control(tab_widget, True)
            dlg_layout.removeWidget(tab_widget)
            tab_widget.setParent(None)
            self.main_tabs_view.insertTab(idx, tab_widget, tr(title_key))
            self.main_tabs_view.setCurrentWidget(tab_widget)
            tab_widget.updateGeometry()
            self.main_tabs_view.update()
            self.update()
            self.repaint()

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)

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
