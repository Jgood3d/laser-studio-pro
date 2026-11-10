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
from settings_window import SettingsWindow
from ui.machine import MachinePanel
from ui.statusbar import StatusBar
from ui.tabs.layers import LayersTab

from usb_controller import LaserUSBController
from vector_layers import LayerManager

from ui_setup_mixin import UiSetupMixin
from ui_window_controller import WindowControllerMixin
from ui_machine_params_page import MachineParamsPageMixin
from ui_machine_profiles_page import MachineProfilesPageMixin
from ui_test_matrix_page import TestMatrixPageMixin
from ui_grbl_config_page import GrblConfigPageMixin
from ui_image_tab import ImageTabMixin
from ui_preview_2d_tab import Preview2DTabMixin
from ui_job_tabs import JobTabsMixin
from ui_legacy_svg_box import LegacySvgBoxMixin
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


class FullLaserStudio(QMainWindow, UiSetupMixin, WindowControllerMixin, MachineParamsPageMixin, MachineProfilesPageMixin,
                       TestMatrixPageMixin, GrblConfigPageMixin, ImageTabMixin, Preview2DTabMixin, JobTabsMixin,
                       LegacySvgBoxMixin, MachineProfilesMixin,
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
        self._build_legacy_svg_box()
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
        self.spin_machine_max_speed.valueChanged.connect(jog.set_max_speed)

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
