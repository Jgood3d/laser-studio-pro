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
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from laser_studio.camera.workspace_alignment import generate_apriltag_targets
from laser_studio.ui.dialogs.camera import preparation

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

        root.addWidget(self._build_preparation_box())

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

        # Image de la caméra dans l'éditeur vectoriel : opacité et retrait.
        from PyQt6.QtWidgets import QSlider
        view_row = QHBoxLayout()
        view_row.addWidget(QLabel(tr("camera.overlay_opacity")))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(5, 100)
        self.slider_opacity.setValue(70)
        self.slider_opacity.valueChanged.connect(lambda v: self._ctrl.set_overlay_opacity(v / 100.0))
        view_row.addWidget(self.slider_opacity, stretch=1)
        self.btn_clear_overlay = QPushButton(tr("camera.btn.clear_overlay"))
        self.btn_clear_overlay.clicked.connect(self._ctrl.clear_overlay)
        view_row.addWidget(self.btn_clear_overlay)
        root.addLayout(view_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    # Préparation : feuilles à imprimer et gabarit, avant la calibration

    def _build_preparation_box(self) -> QGroupBox:
        box = QGroupBox(tr("camera.group.prepare"))
        lay = QVBoxLayout(box)
        hint = QLabel(tr("camera.prepare.hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        lay.addWidget(hint)

        # Réglages du motif d'alignement : repris par l'assistant « Aligner sur le plateau ».
        saved = getattr(self._ctrl, "align_tag_params", None) or {}
        grid = QGridLayout()
        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(5.0, 80.0)
        self.spin_margin.setValue(saved.get("margin", 20.0))
        self.spin_margin.setSuffix(" mm")
        self.spin_tag = QDoubleSpinBox()
        self.spin_tag.setRange(8.0, 60.0)
        self.spin_tag.setValue(saved.get("tag", 20.0))
        self.spin_tag.setSuffix(" mm")
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(2, 5)
        self.spin_cols.setValue(saved.get("cols", 3))
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(2, 5)
        self.spin_rows.setValue(saved.get("rows", 3))
        for row, (label, spin) in enumerate((
            (tr("camera.align_wizard.margin"), self.spin_margin),
            (tr("camera.align_wizard.tag_size"), self.spin_tag),
            (tr("camera.align_wizard.cols"), self.spin_cols),
            (tr("camera.align_wizard.rows"), self.spin_rows),
        )):
            grid.addWidget(QLabel(label), row // 2, (row % 2) * 2)
            grid.addWidget(spin, row // 2, (row % 2) * 2 + 1)
            spin.valueChanged.connect(self._update_tag_summary)
        lay.addLayout(grid)

        self._lbl_tags = QLabel()
        self._lbl_tags.setWordWrap(True)
        lay.addWidget(self._lbl_tags)

        # Damier (calibration optique) puis AprilTags : imprimer ou enregistrer en PDF.
        for text, action in (
            (tr("camera.prepare.board"), preparation.print_board),
            (tr("camera.prepare.tags"), lambda parent, pdf=False: preparation.print_tags(
                parent, self._current_targets(), pdf=pdf)),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(text), stretch=1)
            btn_print = QPushButton(tr("camera.prepare.print"))
            btn_print.clicked.connect(lambda _=False, a=action: self._run_prepare(a, False))
            btn_pdf = QPushButton(tr("camera.prepare.pdf"))
            btn_pdf.clicked.connect(lambda _=False, a=action: self._run_prepare(a, True))
            row.addWidget(btn_print)
            row.addWidget(btn_pdf)
            lay.addLayout(row)

        self.btn_template = QPushButton(tr("camera.prepare.template"))
        self.btn_template.clicked.connect(self._on_add_template)
        lay.addWidget(self.btn_template)
        self._update_tag_summary()
        return box

    def _current_targets(self):
        """Positions des tags d'après les réglages affichés ; [] si la grille ne tient pas sur le plateau."""
        try:
            bed_w, bed_h = self._ctrl._bed_size()
            return generate_apriltag_targets(
                bed_w, bed_h,
                margin_mm=self.spin_margin.value(),
                tag_size_mm=self.spin_tag.value(),
                grid=(self.spin_cols.value(), self.spin_rows.value()),
            )
        except ValueError:
            return []

    def _update_tag_summary(self, *_args):
        try:
            bed_w, bed_h = self._ctrl._bed_size()
            targets = generate_apriltag_targets(
                bed_w, bed_h,
                margin_mm=self.spin_margin.value(),
                tag_size_mm=self.spin_tag.value(),
                grid=(self.spin_cols.value(), self.spin_rows.value()),
            )
            text = tr("camera.align_wizard.targets_ok").format(n=len(targets), bed=f"{bed_w:.0f}×{bed_h:.0f}")
        except ValueError as error:
            text = str(error)
        self._lbl_tags.setText(text)
        # Mémorisés : l'assistant d'alignement s'ouvre avec les mêmes positions que celles préparées ici.
        self._ctrl.align_tag_params = {
            "margin": self.spin_margin.value(), "tag": self.spin_tag.value(),
            "cols": self.spin_cols.value(), "rows": self.spin_rows.value(),
        }

    def _run_prepare(self, action, pdf):
        if action is not preparation.print_board and not self._current_targets():
            QMessageBox.warning(self, tr("camera.dialog_title"), self._lbl_tags.text())
            return
        action(self, pdf=pdf)

    def _on_add_template(self):
        preparation.add_template_to_editor(self, self._current_targets())

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
