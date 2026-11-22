"""Assistant de calibration optique : plusieurs vues d'un damier imprimé.

Étapes :
  1. Instructions + génération / sauvegarde du damier à imprimer
  2. Capture guidée (N vues sous des angles variés)
  3. Calcul + résultat (erreur de reprojection) → enregistrement dans le profil
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
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from laser_studio.camera.capture import CameraCapture
from laser_studio.camera.lens_calibration import (
    calibrate_lens_from_images,
    generate_chessboard_image,
)
from laser_studio.controllers.camera import CameraController
from laser_studio.i18n import tr
from laser_studio.ui.dialogs.camera import preparation

# Coins intérieurs du damier (standard OpenCV 9×6)
PATTERN_SIZE = (9, 6)
MIN_VIEWS = 8
TARGET_VIEWS = 12


def _numpy_to_qpixmap(bgr: np.ndarray, max_w: int = 480) -> QPixmap:
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


class LensCalibrationWizard(QDialog):
    """Wizard multi-pages pour la calibration d'objectif."""

    def __init__(self, controller: CameraController, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("camera.lens_wizard.title"))
        self.setMinimumSize(560, 480)
        self._ctrl = controller
        self._frames: List[np.ndarray] = []
        self._cap: Optional[CameraCapture] = None
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)

        self._stack = QStackedWidget()
        self._page_intro = self._build_intro()
        self._page_capture = self._build_capture()
        self._page_result = self._build_result()
        self._stack.addWidget(self._page_intro)
        self._stack.addWidget(self._page_capture)
        self._stack.addWidget(self._page_result)

        root = QVBoxLayout(self)
        root.addWidget(self._stack)
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._next_btn = self._buttons.addButton(
            tr("camera.wizard.next"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._buttons.rejected.connect(self._close)
        self._buttons.accepted.connect(self._on_next)
        root.addWidget(self._buttons)
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------ pages

    def _build_intro(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel(tr("camera.lens_wizard.intro"))
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        row = QHBoxLayout()
        btn_save = QPushButton(tr("camera.lens_wizard.save_board"))
        btn_save.clicked.connect(self._save_chessboard)
        row.addWidget(btn_save)
        btn_print = QPushButton(tr("camera.print.board_button"))
        btn_print.clicked.connect(self._print_chessboard)
        row.addWidget(btn_print)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return w

    def _build_capture(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._lbl_capture_help = QLabel(tr("camera.lens_wizard.capture_help"))
        self._lbl_capture_help.setWordWrap(True)
        lay.addWidget(self._lbl_capture_help)
        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(240)
        self._preview.setStyleSheet("background: #222; color: #aaa;")
        lay.addWidget(self._preview, stretch=1)
        self._progress = QProgressBar()
        self._progress.setRange(0, TARGET_VIEWS)
        self._progress.setValue(0)
        lay.addWidget(self._progress)
        self._lbl_count = QLabel("0 / %d" % TARGET_VIEWS)
        lay.addWidget(self._lbl_count)
        row = QHBoxLayout()
        self._btn_snap = QPushButton(tr("camera.lens_wizard.snap"))
        self._btn_snap.clicked.connect(self._snap)
        row.addWidget(self._btn_snap)
        btn_clear = QPushButton(tr("camera.lens_wizard.clear"))
        btn_clear.clicked.connect(self._clear_frames)
        row.addWidget(btn_clear)
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

    # ------------------------------------------------------------------ navigation

    def _on_next(self):
        idx = self._stack.currentIndex()
        if idx == 0:
            if not self._open_camera():
                return
            self._stack.setCurrentIndex(1)
            self._preview_timer.start(100)
            if self._next_btn:
                self._next_btn.setText(tr("camera.lens_wizard.compute"))
        elif idx == 1:
            if len(self._frames) < MIN_VIEWS:
                QMessageBox.warning(
                    self,
                    tr("camera.lens_wizard.title"),
                    tr("camera.lens_wizard.need_more").format(n=MIN_VIEWS, have=len(self._frames)),
                )
                return
            self._preview_timer.stop()
            self._close_camera()
            self._run_calibration()
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
        if profile is None:
            QMessageBox.warning(self, tr("camera.lens_wizard.title"), tr("camera.err.no_device"))
            return False
        try:
            idx = int(profile.device_id) if str(profile.device_id).isdigit() else 0
            self._cap = CameraCapture(idx, profile.preferred_width, profile.preferred_height)
            if not self._cap.open():
                raise RuntimeError("open failed")
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("camera.lens_wizard.title"),
                tr("camera.err.capture").format(error=e),
            )
            self._cap = None
            return False
        return True

    def _close_camera(self):
        if self._cap is not None:
            self._cap.close()
            self._cap = None

    def _update_preview(self):
        if self._cap is None or not self._cap.is_open:
            return
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return
        # Dessine les coins si le damier est visible (retour visuel).
        display = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(
            gray, PATTERN_SIZE,
            cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE,
        )
        if found:
            cv2.drawChessboardCorners(display, PATTERN_SIZE, corners, True)
        self._preview.setPixmap(_numpy_to_qpixmap(display))

    def _snap(self):
        if self._cap is None:
            return
        frame = self._cap.grab_average(2)
        if frame is None:
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, _ = cv2.findChessboardCorners(
            gray, PATTERN_SIZE,
            cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE,
        )
        if not found:
            QMessageBox.information(
                self,
                tr("camera.lens_wizard.title"),
                tr("camera.lens_wizard.board_not_found"),
            )
            return
        self._frames.append(frame.copy())
        self._progress.setValue(min(len(self._frames), TARGET_VIEWS))
        self._lbl_count.setText("%d / %d" % (len(self._frames), TARGET_VIEWS))
        if len(self._frames) >= TARGET_VIEWS:
            self._lbl_capture_help.setText(tr("camera.lens_wizard.enough"))

    def _clear_frames(self):
        self._frames.clear()
        self._progress.setValue(0)
        self._lbl_count.setText("0 / %d" % TARGET_VIEWS)
        self._lbl_capture_help.setText(tr("camera.lens_wizard.capture_help"))

    def _save_chessboard(self):
        img = generate_chessboard_image(PATTERN_SIZE, square_px=80)
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("camera.lens_wizard.save_board"),
            "chessboard_9x6.png",
            "PNG (*.png)",
        )
        if path:
            cv2.imwrite(path, img)
            QMessageBox.information(
                self,
                tr("camera.lens_wizard.title"),
                tr("camera.lens_wizard.board_saved").format(path=path),
            )

    def _print_chessboard(self):
        """Imprime le damier à l'échelle réelle (feuille paysage, cases de 30 mm
        au plus), pour le coller sur une surface plane."""
        preparation.print_board(self)

    def _run_calibration(self):
        try:
            lens = calibrate_lens_from_images(self._frames, PATTERN_SIZE)
        except ValueError as e:
            self._lbl_result.setText(tr("camera.lens_wizard.failed").format(error=e))
            self._stack.setCurrentIndex(2)
            if self._next_btn:
                self._next_btn.setText(tr("camera.wizard.close"))
            return
        self._ctrl.update_lens(lens)
        self._lbl_result.setText(
            tr("camera.lens_wizard.success").format(
                error=f"{lens.reprojection_error:.3f}",
                views=len(self._frames),
                size=f"{lens.image_size[0]}×{lens.image_size[1]}",
            )
        )
        self._stack.setCurrentIndex(2)
        if self._next_btn:
            self._next_btn.setText(tr("camera.wizard.close"))
        # Remplacer Cancel par rien d'utile : on laisse Close via Next
        cancel = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel:
            cancel.setEnabled(False)
