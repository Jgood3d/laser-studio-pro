"""Assistant d'alignement workspace via AprilTags.

Étapes :
  1. Paramètres du motif (marge, taille tag, grille) + rappel de graver
  2. Capture de l'image du plateau (tags déjà gravés / collés)
  3. Détection automatique + calcul d'homographie → enregistrement
"""
from __future__ import annotations

from typing import List, Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from laser_studio.camera.capture import CameraCapture
from laser_studio.camera.lens_calibration import undistort
from laser_studio.camera.workspace_alignment import (
    AlignmentTarget,
    compute_homography,
    detect_apriltags,
    generate_apriltag_targets,
    targets_to_engrave_paths,
)
from laser_studio.controllers.camera import CameraController
from laser_studio.i18n import tr


def _numpy_to_qpixmap(bgr: np.ndarray, max_w: int = 520) -> QPixmap:
    if bgr.ndim == 2:
        h, w = bgr.shape
        qimg = QImage(bgr.data, w, h, w, QImage.Format.Format_Grayscale8).copy()
    else:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
    pix = QPixmap.fromImage(qimg)
    if pix.width() > max_w:
        pix = pix.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
    return pix


class WorkspaceAlignmentWizard(QDialog):
    """Wizard d'alignement pixel → mm via AprilTags."""

    def __init__(self, controller: CameraController, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("camera.align_wizard.title"))
        self.setMinimumSize(580, 500)
        self._ctrl = controller
        self._targets: List[AlignmentTarget] = []
        self._cap: Optional[CameraCapture] = None
        self._last_frame: Optional[np.ndarray] = None
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)

        self._stack = QStackedWidget()
        self._page_setup = self._build_setup()
        self._page_capture = self._build_capture()
        self._page_result = self._build_result()
        self._stack.addWidget(self._page_setup)
        self._stack.addWidget(self._page_capture)
        self._stack.addWidget(self._page_result)

        root = QVBoxLayout(self)
        root.addWidget(self._stack)
        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._next_btn = self._buttons.addButton(
            tr("camera.wizard.next"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._buttons.rejected.connect(self._close)
        self._buttons.accepted.connect(self._on_next)
        root.addWidget(self._buttons)

    # ------------------------------------------------------------------ pages

    def _build_setup(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        intro = QLabel(tr("camera.align_wizard.intro"))
        intro.setWordWrap(True)
        lay.addWidget(intro)

        form = QFormLayout()
        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(5.0, 80.0)
        self.spin_margin.setValue(20.0)
        self.spin_margin.setSuffix(" mm")
        form.addRow(tr("camera.align_wizard.margin"), self.spin_margin)

        self.spin_tag = QDoubleSpinBox()
        self.spin_tag.setRange(8.0, 60.0)
        self.spin_tag.setValue(20.0)
        self.spin_tag.setSuffix(" mm")
        form.addRow(tr("camera.align_wizard.tag_size"), self.spin_tag)

        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(2, 5)
        self.spin_cols.setValue(3)
        form.addRow(tr("camera.align_wizard.cols"), self.spin_cols)

        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(2, 5)
        self.spin_rows.setValue(3)
        form.addRow(tr("camera.align_wizard.rows"), self.spin_rows)
        lay.addLayout(form)

        self._lbl_targets = QLabel()
        self._lbl_targets.setWordWrap(True)
        lay.addWidget(self._lbl_targets)
        self._update_target_summary()
        for wdg in (self.spin_margin, self.spin_tag, self.spin_cols, self.spin_rows):
            wdg.valueChanged.connect(self._update_target_summary)

        hint = QLabel(tr("camera.align_wizard.engrave_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        lay.addWidget(hint)
        lay.addStretch()
        return w

    def _build_capture(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        help_lbl = QLabel(tr("camera.align_wizard.capture_help"))
        help_lbl.setWordWrap(True)
        lay.addWidget(help_lbl)
        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(260)
        self._preview.setStyleSheet("background: #222; color: #aaa;")
        lay.addWidget(self._preview, stretch=1)
        self._lbl_detect = QLabel("")
        lay.addWidget(self._lbl_detect)
        row = QHBoxLayout()
        self._btn_snap = QPushButton(tr("camera.align_wizard.snap"))
        self._btn_snap.clicked.connect(self._snap)
        row.addWidget(self._btn_snap)
        row.addStretch()
        lay.addLayout(row)
        return w

    def _build_result(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._lbl_result = QLabel()
        self._lbl_result.setWordWrap(True)
        lay.addWidget(self._lbl_result)
        lay.addStretch()
        return w

    def _update_target_summary(self):
        try:
            bed_w, bed_h = self._ctrl._bed_size()
            targets = generate_apriltag_targets(
                bed_w, bed_h,
                margin_mm=self.spin_margin.value(),
                tag_size_mm=self.spin_tag.value(),
                grid=(self.spin_cols.value(), self.spin_rows.value()),
            )
            self._targets = targets
            self._lbl_targets.setText(
                tr("camera.align_wizard.targets_ok").format(
                    n=len(targets),
                    bed=f"{bed_w:.0f}×{bed_h:.0f}",
                )
            )
        except ValueError as e:
            self._targets = []
            self._lbl_targets.setText(str(e))

    # ------------------------------------------------------------------ navigation

    def _on_next(self):
        idx = self._stack.currentIndex()
        if idx == 0:
            if len(self._targets) < 4:
                QMessageBox.warning(
                    self,
                    tr("camera.align_wizard.title"),
                    tr("camera.align_wizard.bad_grid"),
                )
                return
            if self._ctrl.profile is None or self._ctrl.profile.lens is None:
                QMessageBox.warning(
                    self,
                    tr("camera.align_wizard.title"),
                    tr("camera.err.need_lens_first"),
                )
                return
            if not self._open_camera():
                return
            self._stack.setCurrentIndex(1)
            self._preview_timer.start(120)
            self._next_btn.setText(tr("camera.align_wizard.compute"))
        elif idx == 1:
            if self._last_frame is None:
                QMessageBox.warning(
                    self,
                    tr("camera.align_wizard.title"),
                    tr("camera.align_wizard.need_snap"),
                )
                return
            self._preview_timer.stop()
            self._close_camera()
            self._run_alignment()
        elif idx == 2:
            self.accept()

    def _close(self):
        self._preview_timer.stop()
        self._close_camera()
        self.reject()

    def closeEvent(self, event):
        self._preview_timer.stop()
        self._close_camera()
        super().closeEvent(event)

    # ------------------------------------------------------------------ capture

    def _open_camera(self) -> bool:
        profile = self._ctrl.profile
        try:
            idx = int(profile.device_id) if str(profile.device_id).isdigit() else 0
            self._cap = CameraCapture(idx, profile.preferred_width, profile.preferred_height)
            if not self._cap.open():
                raise RuntimeError("open failed")
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("camera.align_wizard.title"),
                tr("camera.err.capture").format(error=e),
            )
            self._cap = None
            return False
        return True

    def _close_camera(self):
        if self._cap is not None:
            self._cap.close()
            self._cap = None

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Undistort + dessine les tags détectés."""
        und = undistort(frame, self._ctrl.profile.lens)
        expected = [t.tag_id for t in self._targets]
        found = detect_apriltags(und, expected_ids=expected)
        display = und.copy()
        for tid, (u, v) in found.items():
            cv2.circle(display, (int(u), int(v)), 8, (0, 255, 0), 2)
            cv2.putText(
                display, str(tid), (int(u) + 10, int(v) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
            )
        self._lbl_detect.setText(
            tr("camera.align_wizard.detected").format(
                found=len(found), total=len(self._targets)
            )
        )
        return display

    def _update_preview(self):
        if self._cap is None or not self._cap.is_open:
            return
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return
        try:
            display = self._process_frame(frame)
        except Exception:
            display = frame
        self._preview.setPixmap(_numpy_to_qpixmap(display))

    def _snap(self):
        if self._cap is None:
            return
        frame = self._cap.grab_average(3)
        if frame is None:
            return
        self._last_frame = frame
        try:
            display = self._process_frame(frame)
        except Exception:
            display = frame
        self._preview.setPixmap(_numpy_to_qpixmap(display))

    def _run_alignment(self):
        und = undistort(self._last_frame, self._ctrl.profile.lens)
        expected = [t.tag_id for t in self._targets]
        detections = detect_apriltags(und, expected_ids=expected)
        h, w = und.shape[:2]
        try:
            alignment = compute_homography(
                self._targets, detections, (w, h), min_tags=4
            )
        except ValueError as e:
            self._lbl_result.setText(tr("camera.align_wizard.failed").format(error=e))
            self._stack.setCurrentIndex(2)
            self._next_btn.setText(tr("camera.wizard.close"))
            return
        self._ctrl.update_alignment(alignment)
        self._lbl_result.setText(
            tr("camera.align_wizard.success").format(
                tags=len(alignment.used_tags),
                error=f"{alignment.reprojection_error_mm:.3f}",
                size=f"{w}×{h}",
            )
        )
        self._stack.setCurrentIndex(2)
        self._next_btn.setText(tr("camera.wizard.close"))
        cancel = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel:
            cancel.setEnabled(False)

    def engrave_paths(self) -> list:
        """Contours à graver pour le motif d'alignement (utilisable par l'appelant)."""
        return targets_to_engrave_paths(self._targets)
