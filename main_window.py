"""Fenêtre principale de l'application : assemble tous les mixins fonctionnels."""
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QTimer

from usb_controller import LaserUSBController
from vector_layers import LayerManager

from ui_setup_mixin import UiSetupMixin
from machine_profiles_mixin import MachineProfilesMixin
from image_processing_mixin import ImageProcessingMixin
from vector_editing_mixin import VectorEditingMixin
from gcode_generation_mixin import GcodeGenerationMixin
from laser_control_mixin import LaserControlMixin
from project_io_mixin import ProjectIOMixin


class FullLaserStudio(QMainWindow, UiSetupMixin, MachineProfilesMixin, ImageProcessingMixin,
                       VectorEditingMixin, GcodeGenerationMixin, LaserControlMixin, ProjectIOMixin):
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
        self.img_worker = None
        self.pending_reprocess = False

        self.materials_db = {
            "Personnalisé": {"sp_e": 2000, "pw_e": 30, "sp_c": 300, "pw_c": 90, "pass_c": 1},
            "Contreplaqué 3mm": {"sp_e": 2500, "pw_e": 35, "sp_c": 250, "pw_c": 95, "pass_c": 2},
            "MDF 4mm": {"sp_e": 2200, "pw_e": 40, "sp_c": 180, "pw_c": 100, "pass_c": 3},
            "Acrylique 3mm": {"sp_e": 3000, "pw_e": 25, "sp_c": 200, "pw_c": 90, "pass_c": 2},
            "Ardoise / Carrelage": {"sp_e": 1500, "pw_e": 45, "sp_c": 500, "pw_c": 0, "pass_c": 0},
            "Cuir 2mm": {"sp_e": 2800, "pw_e": 20, "sp_c": 350, "pw_c": 80, "pass_c": 1}
        }
        
        self.process_timer = QTimer()
        self.process_timer.setSingleShot(True)
        self.process_timer.setInterval(150)
        self.process_timer.timeout.connect(self._do_update_image_processing)

        self.init_ui()
        self.load_machine_settings()
        self.load_splitter_sizes()
        self.update_vector_work_area()
        self._refresh_engrave_layer_combo()
        self.refresh_com_ports()
