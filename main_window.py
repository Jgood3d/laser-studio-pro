"""Fenêtre principale de l'application : assemble tous les mixins fonctionnels."""
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QTimer

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
        self._refresh_engrave_layer_combo()
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

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_autosave_recovery_pending", False):
            self._autosave_recovery_pending = False
            QTimer.singleShot(0, self.check_for_autosave_recovery)
