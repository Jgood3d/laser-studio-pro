"""Page « Matériaux et connexion au graveur »."""

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from i18n import tr


class MachineProfilesPageMixin:
    def _build_machine_profiles_page(self):
        """Page « Matériaux et connexion au graveur »."""
        tab_mach = QWidget()
        layout_mach = QVBoxLayout(tab_mach)

        usb_box = QGroupBox(tr("usb.box_title"))
        usb_layout = QFormLayout()
        self.combo_ports = QComboBox()
        # Même liste que le sélecteur de la barre d'outils (modèle partagé) et
        # même port choisi.
        self.combo_ports.setModel(self.combo_ports_toolbar.model())
        self.combo_ports.currentIndexChanged.connect(
            self.combo_ports_toolbar.setCurrentIndex
        )
        self.combo_ports_toolbar.currentIndexChanged.connect(
            self.combo_ports.setCurrentIndex
        )
        btn_refresh = QPushButton(tr("usb.refresh_ports"))
        btn_refresh.clicked.connect(self.refresh_com_ports)
        self.btn_connect = QPushButton(tr("usb.connect"))
        self.btn_connect.clicked.connect(self.toggle_usb)
        usb_layout.addRow(tr("usb.port"), self.combo_ports)
        usb_layout.addRow("", btn_refresh)
        usb_layout.addRow("", self.btn_connect)

        lbl_driver_hint = QLabel(tr("usb.driver_hint"))
        lbl_driver_hint.setTextFormat(Qt.TextFormat.RichText)
        lbl_driver_hint.setOpenExternalLinks(True)
        lbl_driver_hint.setWordWrap(True)
        lbl_driver_hint.setStyleSheet("color: #888888;")
        hint_palette = lbl_driver_hint.palette()
        hint_palette.setColor(QPalette.ColorRole.Link, QColor("#5aa9ff"))
        lbl_driver_hint.setPalette(hint_palette)
        usb_layout.addRow(lbl_driver_hint)
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
        # Page affichée dans une fenêtre du menu (voir show_settings_window),
        # plus dans un onglet.
        self.tab_machine_profiles = tab_mach
