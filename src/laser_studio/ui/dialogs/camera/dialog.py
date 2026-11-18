"""Fenêtre « Caméra » : choix de l'appareil, état du profil, actions.

V1 : sélection de la webcam, affichage de l'état (optique / alignement),
boutons pour lancer la calibration optique, l'alignement workspace et
l'actualisation de l'overlay. Les wizards complets (multi-étapes) seront
branchés ensuite ; pour l'instant les actions non prêtes affichent un
message clair.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from laser_studio.controllers.camera import CameraController
from laser_studio.i18n import tr


class CameraDialog(QDialog):
    """Dialogue principal Caméra."""

    def __init__(self, controller: CameraController, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("camera.dialog_title"))
        self.setMinimumWidth(420)
        self._ctrl = controller
        self._build_ui()
        self._reload_devices()
        self._refresh_status()
        controller.profile_changed.connect(self._refresh_status)
        controller.status_changed.connect(self._on_status)

    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- Appareil ---
        device_box = QGroupBox(tr("camera.group.device"))
        form = QFormLayout(device_box)
        self.combo_device = QComboBox()
        self.combo_device.currentIndexChanged.connect(self._on_device_chosen)
        form.addRow(tr("camera.label.device"), self.combo_device)
        btn_refresh = QPushButton(tr("camera.btn.refresh_devices"))
        btn_refresh.clicked.connect(self._reload_devices)
        form.addRow("", btn_refresh)
        root.addWidget(device_box)

        # --- État ---
        status_box = QGroupBox(tr("camera.group.status"))
        status_layout = QVBoxLayout(status_box)
        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status_layout.addWidget(self.lbl_status)
        self.lbl_message = QLabel()
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setStyleSheet("color: gray;")
        status_layout.addWidget(self.lbl_message)
        root.addWidget(status_box)

        # --- Actions ---
        actions = QHBoxLayout()
        self.btn_lens = QPushButton(tr("camera.btn.calibrate_lens"))
        self.btn_lens.clicked.connect(self._on_calibrate_lens)
        self.btn_align = QPushButton(tr("camera.btn.align_workspace"))
        self.btn_align.clicked.connect(self._on_align_workspace)
        self.btn_overlay = QPushButton(tr("camera.btn.refresh_overlay"))
        self.btn_overlay.clicked.connect(self._on_refresh_overlay)
        actions.addWidget(self.btn_lens)
        actions.addWidget(self.btn_align)
        actions.addWidget(self.btn_overlay)
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    # ------------------------------------------------------------------

    def _reload_devices(self):
        self.combo_device.blockSignals(True)
        self.combo_device.clear()
        devices = self._ctrl.list_devices()
        active_id = self._ctrl.profile.device_id if self._ctrl.profile else None
        select = 0
        for i, dev in enumerate(devices):
            label = f"{dev.name}  ({dev.width}×{dev.height})" if dev.width else dev.name
            self.combo_device.addItem(label, dev)
            if active_id is not None and str(dev.index) == str(active_id):
                select = i
        if not devices:
            self.combo_device.addItem(tr("camera.no_device"), None)
        self.combo_device.setCurrentIndex(select)
        self.combo_device.blockSignals(False)
        if devices:
            self._on_device_chosen(select)

    def _on_device_chosen(self, index: int):
        dev = self.combo_device.itemData(index)
        if dev is None:
            return
        self._ctrl.set_active_device(str(dev.index), dev.name)
        self._refresh_status()

    def _refresh_status(self):
        self.lbl_status.setText(self._ctrl.status_summary())
        ready = self._ctrl.profile is not None and self._ctrl.profile.is_ready
        self.btn_overlay.setEnabled(ready)

    def _on_status(self, message: str):
        self.lbl_message.setText(message)

    def _on_calibrate_lens(self):
        if self._ctrl.profile is None:
            QMessageBox.warning(self, tr("camera.dialog_title"), tr("camera.err.no_device"))
            return
        from laser_studio.ui.dialogs.camera.lens_wizard import LensCalibrationWizard
        if LensCalibrationWizard(self._ctrl, self).exec():
            self._refresh_status()

    def _on_align_workspace(self):
        if self._ctrl.profile is None:
            QMessageBox.warning(self, tr("camera.dialog_title"), tr("camera.err.no_device"))
            return
        if self._ctrl.profile.lens is None:
            QMessageBox.warning(self, tr("camera.dialog_title"), tr("camera.err.need_lens_first"))
            return
        from laser_studio.ui.dialogs.camera.align_wizard import WorkspaceAlignmentWizard
        if WorkspaceAlignmentWizard(self._ctrl, self).exec():
            self._refresh_status()


    def _on_refresh_overlay(self):
        self._ctrl.refresh_overlay()
