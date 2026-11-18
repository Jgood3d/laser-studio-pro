"""Ouverture et capture d'images depuis une webcam (OpenCV, sans Qt)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class CameraDevice:
    """Périphérique vidéo détecté."""
    index: int
    name: str
    width: int = 0
    height: int = 0


def list_cameras(max_index: int = 8) -> List[CameraDevice]:
    """Liste les webcams accessibles (indices 0 … max_index-1).

    Sous Linux le nom reste générique (« Camera 0 ») faute d'API stable
    sans dépendances supplémentaires ; sous Windows OpenCV renvoie parfois
    un libellé plus parlant via les backends MSMF / DSHOW.
    """
    devices: List[CameraDevice] = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_ANY)
        if not cap.isOpened():
            cap.release()
            continue
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        # Tentative de lecture d'un nom (souvent vide hors Windows).
        name = f"Camera {i}"
        backend = cap.getBackendName() if hasattr(cap, "getBackendName") else ""
        if backend:
            name = f"Camera {i} ({backend})"
        devices.append(CameraDevice(index=i, name=name, width=w, height=h))
        cap.release()
    return devices


class CameraCapture:
    """Session de capture sur une webcam.

    Usage :
        with CameraCapture(0) as cam:
            ok, frame = cam.read()
    """

    def __init__(self, index: int = 0, width: int = 0, height: int = 0):
        self.index = index
        self._requested_size = (width, height)
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        if self._cap is not None and self._cap.isOpened():
            return True
        self._cap = cv2.VideoCapture(self.index, cv2.CAP_ANY)
        if not self._cap.isOpened():
            self._cap = None
            return False
        w, h = self._requested_size
        if w > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        if h > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        return True

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "CameraCapture":
        if not self.open():
            raise RuntimeError(f"Impossible d'ouvrir la caméra {self.index}")
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def size(self) -> Tuple[int, int]:
        if not self.is_open:
            return (0, 0)
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        return (w, h)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Lit une frame BGR. Renvoie (False, None) en cas d'échec."""
        if not self.is_open:
            return False, None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return False, None
        return True, frame

    def grab_average(self, n: int = 3) -> Optional[np.ndarray]:
        """Moyenne de n frames pour réduire le bruit (utile en calibration)."""
        frames = []
        for _ in range(max(1, n)):
            ok, frame = self.read()
            if ok and frame is not None:
                frames.append(frame.astype(np.float32))
        if not frames:
            return None
        avg = np.mean(frames, axis=0)
        return np.clip(avg, 0, 255).astype(np.uint8)


def open_camera(index: int = 0, width: int = 0, height: int = 0) -> CameraCapture:
    """Raccourci : ouvre et renvoie une CameraCapture déjà ouverte."""
    cam = CameraCapture(index, width, height)
    if not cam.open():
        raise RuntimeError(f"Impossible d'ouvrir la caméra {index}")
    return cam
