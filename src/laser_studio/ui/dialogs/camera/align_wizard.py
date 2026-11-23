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
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QApplication,
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
    compute_alignment,
    detect_apriltag_corners,
    merge_detections,
    generate_apriltag_targets,
    tag_cell_px,
    targets_to_engrave_paths,
)
from laser_studio.controllers.camera import CameraController
from laser_studio.i18n import tr
from laser_studio.ui.dialogs.camera import preparation


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

    # Le portique cache des tags différents selon sa position : on capture 2 à 3 fois en le déplaçant entre
    # deux captures, et on fusionne les tags vus.
    MIN_CAPTURES = 2
    MAX_CAPTURES = 3

    def __init__(self, controller: CameraController, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("camera.align_wizard.title"))
        self.setMinimumSize(580, 500)
        self._ctrl = controller
        self._targets: List[AlignmentTarget] = []
        self._cap: Optional[CameraCapture] = None
        self._last_frame: Optional[np.ndarray] = None
        self._captures: List[dict] = []                 # une entrée par capture : {tag_id: coins}
        self._img_size: Optional[tuple] = None
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
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self._buttons.rejected.connect(self._close)
        self._buttons.accepted.connect(self._on_next)
        next_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if next_btn:
            next_btn.setText(tr("camera.wizard.next"))
        root.addWidget(self._buttons)

    # ------------------------------------------------------------------ pages

    def _build_setup(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        intro = QLabel(tr("camera.align_wizard.intro"))
        intro.setWordWrap(True)
        lay.addWidget(intro)

        form = QFormLayout()
        saved = getattr(self._ctrl, "align_tag_params", None) or {}   # derniers réglages de cette session
        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(2.0, 80.0)
        self.spin_margin.setValue(saved.get("margin", 20.0))
        self.spin_margin.setSuffix(" mm")
        form.addRow(tr("camera.align_wizard.margin"), self.spin_margin)

        self.spin_tag = QDoubleSpinBox()
        self.spin_tag.setRange(15.0, 120.0)
        self.spin_tag.setValue(saved.get("tag", 40.0))
        self.spin_tag.setSuffix(" mm")
        form.addRow(tr("camera.align_wizard.tag_size"), self.spin_tag)

        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(2, 5)
        self.spin_cols.setValue(saved.get("cols", 2))
        form.addRow(tr("camera.align_wizard.cols"), self.spin_cols)

        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(2, 5)
        self.spin_rows.setValue(saved.get("rows", 2))
        form.addRow(tr("camera.align_wizard.rows"), self.spin_rows)

        # Plus la résolution est haute, plus les cases du tag font de pixels : c'est ce qui décide de la détection.
        self.combo_res = QComboBox()
        self.combo_res.addItem(tr("camera.align_wizard.res_auto"), (0, 0))
        for rw, rh in ((640, 480), (1280, 720), (1920, 1080)):
            self.combo_res.addItem(f"{rw}×{rh}", (rw, rh))
        profile = self._ctrl.profile
        if profile is not None:
            for i in range(self.combo_res.count()):
                if self.combo_res.itemData(i) == (profile.preferred_width, profile.preferred_height):
                    self.combo_res.setCurrentIndex(i)
        form.addRow(tr("camera.align_wizard.resolution"), self.combo_res)
        lay.addLayout(form)

        self._lbl_targets = QLabel()
        self._lbl_targets.setWordWrap(True)
        lay.addWidget(self._lbl_targets)
        self._update_target_summary()
        for wdg in (self.spin_margin, self.spin_tag, self.spin_cols, self.spin_rows):
            wdg.valueChanged.connect(self._update_target_summary)

        # Les vrais AprilTags à graver : placés dans l'éditeur vectoriel, aux positions du plateau.
        self.btn_add_tags = QPushButton(tr("camera.align_wizard.add_tags"))
        self.btn_add_tags.clicked.connect(self._add_tags_to_editor)
        lay.addWidget(self.btn_add_tags)

        # Ou les imprimer, à leur taille réelle, pour les découper et les poser sur le plateau.
        self.btn_print_tags = QPushButton(tr("camera.print.tags_button"))
        self.btn_print_tags.clicked.connect(self._print_tags)
        lay.addWidget(self.btn_print_tags)
        self.btn_template = QPushButton(tr("camera.prepare.template"))
        self.btn_template.clicked.connect(self._add_template)
        lay.addWidget(self.btn_template)

        hint = QLabel(tr("camera.align_wizard.engrave_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        lay.addWidget(hint)
        lay.addStretch()
        return w

    def _print_tags(self):
        """Imprime les AprilTags à taille réelle (numéro et position du centre
        sur chaque légende), à découper puis poser aux positions indiquées."""
        if not self._targets:
            QMessageBox.warning(self, tr("camera.align_wizard.title"), self._lbl_targets.text())
            return
        preparation.print_tags(self, self._targets)

    def _add_template(self):
        """Gabarit (cadres et numéros) des tags dans l'éditeur vectoriel, à marquer au laser."""
        preparation.add_template_to_editor(self, self._targets)

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
        self._lbl_quality = QLabel("")
        self._lbl_quality.setWordWrap(True)
        lay.addWidget(self._lbl_quality)
        self._lbl_captures = QLabel("")
        self._lbl_captures.setWordWrap(True)
        lay.addWidget(self._lbl_captures)
        row = QHBoxLayout()
        self._btn_snap = QPushButton(tr("camera.align_wizard.snap"))
        self._btn_snap.clicked.connect(self._snap)
        row.addWidget(self._btn_snap)
        self._btn_reset = QPushButton(tr("camera.align_wizard.reset_captures"))
        self._btn_reset.clicked.connect(self._reset_captures)
        row.addWidget(self._btn_reset)
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
            # Mémorisés pour rouvrir l'assistant avec les mêmes positions que celles qu'on a gravées.
            self._ctrl.align_tag_params = {
                "margin": self.spin_margin.value(), "tag": self.spin_tag.value(),
                "cols": self.spin_cols.value(), "rows": self.spin_rows.value(),
            }
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
            res_w, res_h = self.combo_res.currentData()
            profile = self._ctrl.profile
            if (profile.preferred_width, profile.preferred_height) != (res_w, res_h):
                profile.preferred_width, profile.preferred_height = res_w, res_h
                self._ctrl.save_current_profile()
            if not self._open_camera():
                return
            self._reset_captures()
            self._stack.setCurrentIndex(1)
            self._preview_timer.start(120)
            next_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
            if next_btn:
                next_btn.setText(tr("camera.align_wizard.compute"))
        elif idx == 1:
            if len(self._captures) < self.MIN_CAPTURES:
                QMessageBox.warning(
                    self,
                    tr("camera.align_wizard.title"),
                    tr("camera.align_wizard.need_captures").format(min=self.MIN_CAPTURES),
                )
                return
            if len(merge_detections(self._captures)) < 3:
                QMessageBox.warning(
                    self,
                    tr("camera.align_wizard.title"),
                    tr("camera.align_wizard.need_tags").format(total=len(self._targets)),
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
        """Undistort + dessine les tags détectés, avec leur taille en pixels."""
        und = undistort(frame, self._ctrl.profile.lens)
        expected = [t.tag_id for t in self._targets]
        found = detect_apriltag_corners(und, expected_ids=expected)
        display = und.copy()
        for tid, quad in merge_detections(self._captures).items():   # déjà collectés : en bleu, sous les détections
            cv2.polylines(display, [np.round(quad).astype(np.int32)], True, (255, 160, 40), 1)
        for tid, quad in found.items():
            cv2.polylines(display, [np.round(quad).astype(np.int32)], True, (0, 255, 0), 2)
            u, v = quad.mean(axis=0)
            cv2.putText(display, str(tid), (int(u) - 8, int(v) + 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        self._lbl_detect.setText(
            tr("camera.align_wizard.detected").format(found=len(found), total=len(self._targets))
        )
        if found:
            cell = min(tag_cell_px(q) for q in found.values())
            key = "camera.align_wizard.cell_ok" if cell >= 6.0 else "camera.align_wizard.cell_low"
            self._lbl_quality.setText(tr(key).format(px=f"{cell:.1f}", size=f"{und.shape[1]}×{und.shape[0]}"))
            self._lbl_quality.setStyleSheet("color: #2e9e4f;" if cell >= 6.0 else "color: #d9822b;")
        else:
            self._lbl_quality.setText(tr("camera.align_wizard.cell_none").format(size=f"{und.shape[1]}×{und.shape[0]}"))
            self._lbl_quality.setStyleSheet("color: #d9822b;")
        return display

    def _update_preview(self):
        if self._cap is None or not self._cap.is_open:
            return
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return
        try:
            display = self._process_frame(frame)
        except Exception:   # à chaque image : l'image brute est montrée plutôt que rien
            display = frame
        self._preview.setPixmap(_numpy_to_qpixmap(display))

    def _reset_captures(self):
        self._captures = []
        self._img_size = None
        self._last_frame = None
        self._update_captures_status()

    def _update_captures_status(self):
        merged = merge_detections(self._captures)
        total = [t.tag_id for t in self._targets]
        missing = [str(i) for i in total if i not in merged]
        text = tr("camera.align_wizard.captures_status").format(
            n=len(self._captures), max=self.MAX_CAPTURES, found=len(merged), total=len(total))
        if missing and self._captures:
            text += " " + tr("camera.align_wizard.captures_missing").format(ids=", ".join(missing))
        self._lbl_captures.setText(text)
        self._btn_snap.setEnabled(len(self._captures) < self.MAX_CAPTURES)
        self._btn_reset.setEnabled(bool(self._captures))

    def _snap(self):
        if self._cap is None or len(self._captures) >= self.MAX_CAPTURES:
            return
        frame = self._cap.grab_average(3)
        if frame is None:
            return
        und = undistort(frame, self._ctrl.profile.lens)
        found = detect_apriltag_corners(und, expected_ids=[t.tag_id for t in self._targets])
        if found:                                   # une capture sans aucun tag ne compte pas
            self._captures.append(found)
            self._img_size = (und.shape[1], und.shape[0])
            self._last_frame = frame
        self._update_captures_status()
        try:
            display = self._process_frame(frame)
        except Exception:   # à chaque image : l'image brute est montrée plutôt que rien
            display = frame
        self._preview.setPixmap(_numpy_to_qpixmap(display))

    def _run_alignment(self):
        detections = merge_detections(self._captures)
        w, h = self._img_size
        try:
            alignment = compute_alignment(
                self._targets, detections, (w, h), min_tags=3
            )
        except ValueError as e:
            self._lbl_result.setText(tr("camera.align_wizard.failed").format(error=e))
            self._stack.setCurrentIndex(2)
            next_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
            if next_btn:
                next_btn.setText(tr("camera.wizard.close"))
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
        next_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if next_btn:
            next_btn.setText(tr("camera.wizard.close"))
        cancel = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel:
            cancel.setEnabled(False)

    def _find_editor_window(self):
        """La fenêtre principale (celle qui porte l'éditeur vectoriel) : on remonte les parents, puis on cherche
        parmi les fenêtres de l'application."""
        def is_editor(widget):
            return hasattr(widget, "vector_canvas") and hasattr(widget, "layer_manager")

        widget = self.parent()
        while widget is not None:
            if is_editor(widget):
                return widget
            widget = widget.parent()
        for widget in QApplication.topLevelWidgets():
            if is_editor(widget):
                return widget
        return None

    def _add_tags_to_editor(self):
        """Crée les AprilTags (gravure) dans l'éditeur vectoriel, aux positions calculées pour le plateau."""
        title = tr("camera.align_wizard.title")
        if not self._targets:
            QMessageBox.warning(self, title, tr("camera.align_wizard.bad_grid"))
            return
        editor = self._find_editor_window()
        if editor is None:
            QMessageBox.warning(self, title, tr("camera.align_wizard.tags_unavailable"))
            return
        try:
            from laser_studio.vector.importers import apriltags_to_objects

            if not editor.layer_manager.layers:
                QMessageBox.warning(self, title, tr("vector.no_layer_body"))
                return
            layer = editor.layer_manager.engrave_layer() or editor.layer_manager.layers[0]
            objects = apriltags_to_objects(self._targets, layer.id)
            if not objects:
                QMessageBox.warning(self, title, tr("camera.align_wizard.tags_unavailable"))
                return
            canvas = editor.vector_canvas
            canvas.push_undo_snapshot()
            items = [canvas.add_object(obj) for obj in objects]
            canvas.scene_obj.clearSelection()
            for item in items:
                item.setSelected(True)
        except Exception as e:  # on montre la vraie cause plutôt qu'un message vague
            import traceback

            traceback.print_exc()
            QMessageBox.critical(self, title, f"{type(e).__name__}: {e}")
            return
        QMessageBox.information(
            self, title,
            tr("camera.align_wizard.tags_added").format(
                n=len(self._targets), layer=layer.name, size=f"{self.spin_tag.value():.0f}",
            ),
        )

    def engrave_paths(self) -> list:
        """Contours à graver pour le motif d'alignement (utilisable par l'appelant)."""
        return targets_to_engrave_paths(self._targets)
