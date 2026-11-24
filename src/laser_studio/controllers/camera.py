"""Contrôleur caméra : profil actif, capture, calibration et overlay.

La logique pure vit dans `laser_studio.camera.*` ; ici on orchestre les
appels, les messages utilisateur et les signaux vers l'interface.
"""
from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from laser_studio.camera.capture import CameraDevice, list_cameras, CameraCapture
from laser_studio.camera.lens_calibration import LensCalibration, undistort
from laser_studio.camera.storage import (
    CameraProfile,
    load_profile,
    save_profile,
)
from laser_studio.camera.workspace_alignment import (
    WorkspaceAlignment,
    warp_to_bed,
)
from laser_studio.i18n import tr
from laser_studio.core.preferences import app_preferences


class CameraController(QObject):
    """État caméra de la session + actions exposées à l'UI.

    Signaux :
        overlay_ready(image_bgr, bed_w, bed_h)  image déjà projetée sur le lit
        status_changed(message)
        profile_changed()
    """

    overlay_ready = pyqtSignal(object, float, float)  # np.ndarray, bed_w, bed_h
    overlay_cleared = pyqtSignal()                    # retirer l'image de la caméra de l'éditeur vectoriel
    overlay_opacity_changed = pyqtSignal(float)       # 0,05 … 1
    status_changed = pyqtSignal(str)
    profile_changed = pyqtSignal()

    SETTINGS_KEY = "camera/active_device_id"

    def __init__(
        self,
        parent: QWidget,
        bed_size: Callable[[], tuple],
        *,
        px_per_mm: float = 5.0,
        dialogs=None,
    ):
        """
        parent     : widget parent (et des boîtes de dialogue par défaut)
        bed_size   : callable → (bed_w_mm, bed_h_mm)
        px_per_mm  : résolution de l'image d'overlay générée
        dialogs    : UserDialogs (par défaut, celles de `parent`)
        """
        super().__init__(parent)
        self._parent = parent
        # Boîtes de dialogue (UserDialogs) : celles de la fenêtre, ou un objet
        # qui répond à la place de l'utilisateur dans les tests.
        if dialogs is None:
            from laser_studio.ui.user_dialogs import UserDialogs
            dialogs = UserDialogs(parent)
        self._dialogs = dialogs
        self._bed_size = bed_size
        self._px_per_mm = px_per_mm
        self._profile: Optional[CameraProfile] = None
        self._load_active_profile()

    # ------------------------------------------------------------------
    # Profil actif
    # ------------------------------------------------------------------

    @property
    def profile(self) -> Optional[CameraProfile]:
        return self._profile

    def _load_active_profile(self) -> None:
        device_id = str(app_preferences().get(self.SETTINGS_KEY, "") or "")
        if device_id:
            self._profile = load_profile(device_id)
        else:
            self._profile = None

    def set_active_device(self, device_id: str, display_name: str = "") -> CameraProfile:
        """Choisit la caméra active (crée un profil vide si besoin)."""
        profile = load_profile(device_id)
        if profile is None:
            profile = CameraProfile(device_id=device_id, display_name=display_name or device_id)
            save_profile(profile)
        self._profile = profile
        app_preferences().set(self.SETTINGS_KEY, device_id)
        self.profile_changed.emit()
        self.status_changed.emit(tr("camera.status.active").format(name=profile.display_name))
        return profile

    def save_current_profile(self) -> None:
        if self._profile is not None:
            save_profile(self._profile)
            self.profile_changed.emit()

    def list_devices(self) -> List[CameraDevice]:
        return list_cameras()

    # ------------------------------------------------------------------
    # Capture ponctuelle
    # ------------------------------------------------------------------

    def capture_frame(self) -> Optional[np.ndarray]:
        """Ouvre la caméra active, lit une frame (moyenne de 3), ferme."""
        if self._profile is None:
            self._warn(tr("camera.err.no_device"))
            return None
        try:
            with CameraCapture(
                int(self._profile.device_id) if self._profile.device_id.isdigit() else 0,
                self._profile.preferred_width,
                self._profile.preferred_height,
            ) as cam:
                frame = cam.grab_average(3)
        except Exception as e:
            self._warn(tr("camera.err.capture").format(error=e))
            return None
        if frame is None:
            self._warn(tr("camera.err.capture").format(error="empty frame"))
            return None
        return frame

    # ------------------------------------------------------------------
    # Overlay
    # ------------------------------------------------------------------

    def refresh_overlay(self) -> bool:
        """Capture → undistort → warp sur le lit → signal overlay_ready.

        Renvoie True si l'image a été émise.
        """
        if self._profile is None or not self._profile.is_ready:
            self._warn(tr("camera.err.not_ready"))
            return False
        frame = self.capture_frame()
        if frame is None:
            return False
        und = undistort(frame, self._profile.lens)
        bed_w, bed_h = self._bed_size()
        warped = warp_to_bed(
            und, self._profile.alignment, bed_w, bed_h, px_per_mm=self._px_per_mm
        )
        self.overlay_ready.emit(warped, bed_w, bed_h)
        self.status_changed.emit(tr("camera.status.overlay_ok"))
        return True

    def clear_overlay(self) -> None:
        """Retire l'image de la caméra de l'éditeur vectoriel."""
        self.overlay_cleared.emit()

    def set_overlay_opacity(self, value: float) -> None:
        self.overlay_opacity_changed.emit(float(value))

    def update_lens(self, lens: LensCalibration) -> None:
        if self._profile is None:
            return
        self._profile.lens = lens
        self.save_current_profile()
        self.status_changed.emit(
            tr("camera.status.lens_ok").format(error=f"{lens.reprojection_error:.2f}")
        )

    def update_alignment(self, alignment: WorkspaceAlignment) -> None:
        if self._profile is None:
            return
        self._profile.alignment = alignment
        self.save_current_profile()
        self.status_changed.emit(
            tr("camera.status.align_ok").format(
                tags=len(alignment.used_tags),
                error=f"{alignment.reprojection_error_mm:.2f}",
            )
        )

    # ------------------------------------------------------------------
    # Helpers UI
    # ------------------------------------------------------------------

    def _warn(self, message: str) -> None:
        self.status_changed.emit(message)
        self._dialogs.warning(tr("camera.dialog_title"), message)

    def status_summary(self) -> str:
        if self._profile is None:
            return tr("camera.status.none")
        lens = tr("camera.status.yes") if self._profile.lens else tr("camera.status.no")
        align = tr("camera.status.yes") if self._profile.alignment else tr("camera.status.no")
        return tr("camera.status.summary").format(
            name=self._profile.display_name,
            lens=lens,
            align=align,
        )
