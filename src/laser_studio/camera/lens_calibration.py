"""Calibration optique (distorsion d'objectif) via damier ou AprilTag.

Produit une LensCalibration (matrice intrinsèque + coefficients de
distorsion) réutilisable tant que l'objectif ne change pas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np


@dataclass
class LensCalibration:
    """Résultat d'une calibration optique."""
    camera_matrix: np.ndarray          # 3×3
    dist_coeffs: np.ndarray            # 1×N ou N×1
    image_size: Tuple[int, int]        # (width, height) des images de calib
    reprojection_error: float = 0.0    # erreur RMS moyenne (px)
    # Cartes de remap précalculées (remplies au premier undistort)
    _map1: Optional[np.ndarray] = field(default=None, repr=False)
    _map2: Optional[np.ndarray] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.reshape(-1).tolist(),
            "image_size": list(self.image_size),
            "reprojection_error": float(self.reprojection_error),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LensCalibration":
        return cls(
            camera_matrix=np.array(data["camera_matrix"], dtype=np.float64),
            dist_coeffs=np.array(data["dist_coeffs"], dtype=np.float64).reshape(-1, 1),
            image_size=tuple(data["image_size"]),
            reprojection_error=float(data.get("reprojection_error", 0.0)),
        )

    def ensure_maps(self, size: Optional[Tuple[int, int]] = None) -> None:
        """Prépare les cartes de remap pour la taille demandée (ou image_size)."""
        w, h = size or self.image_size
        if self._map1 is not None and self._map1.shape[:2] == (h, w):
            return
        # Calibrée à une résolution, utilisée à une autre : la matrice suit l'échelle (même champ de vision).
        mtx = self.camera_matrix.copy()
        iw, ih = self.image_size
        if (w, h) != (iw, ih) and iw > 0 and ih > 0:
            mtx[0, :] *= w / iw
            mtx[1, :] *= h / ih
        new_mtx, _ = cv2.getOptimalNewCameraMatrix(mtx, self.dist_coeffs, (w, h), 1, (w, h))
        self._map1, self._map2 = cv2.initUndistortRectifyMap(
            mtx, self.dist_coeffs, None, new_mtx, (w, h), cv2.CV_16SC2
        )


def undistort(image: np.ndarray, calib: LensCalibration) -> np.ndarray:
    """Corrige la distorsion d'une image BGR ou grise."""
    h, w = image.shape[:2]
    calib.ensure_maps((w, h))
    return cv2.remap(image, calib._map1, calib._map2, interpolation=cv2.INTER_LINEAR)


def _find_chessboard(
    gray: np.ndarray, pattern_size: Tuple[int, int]
) -> Optional[np.ndarray]:
    """Coins d'un damier (pattern_size = colonnes intérieures × lignes)."""
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(gray, pattern_size, flags)
    if not found:
        return None
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    return cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)


def calibrate_lens_from_images(
    images: Sequence[np.ndarray],
    pattern_size: Tuple[int, int] = (9, 6),
    square_size_mm: float = 25.0,
) -> LensCalibration:
    """Calibre l'objectif à partir d'images d'un damier imprimé.

    `pattern_size` : nombre de coins intérieurs (colonnes, lignes).
    `square_size_mm` : côté d'une case (mm) — n'influence que l'échelle
    relative des extrinsèques, pas la matrice intrinsèque.

    Lève ValueError s'il n'y a pas assez de vues exploitables (< 4).
    """
    if not images:
        raise ValueError("Aucune image fournie pour la calibration optique")

    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size_mm

    obj_points: List[np.ndarray] = []
    img_points: List[np.ndarray] = []
    image_size: Optional[Tuple[int, int]] = None

    for img in images:
        if img.ndim == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        if image_size is None:
            image_size = (gray.shape[1], gray.shape[0])
        corners = _find_chessboard(gray, pattern_size)
        if corners is not None:
            obj_points.append(objp)
            img_points.append(corners)

    if len(obj_points) < 4:
        raise ValueError(
            f"Pas assez de vues de damier détectées ({len(obj_points)} < 4). "
            "Améliorez l'éclairage ou le contraste, et capturez sous des angles variés."
        )

    rms, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
        obj_points, img_points, image_size, None, None
    )
    return LensCalibration(
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        image_size=image_size,
        reprojection_error=float(rms),
    )


def generate_chessboard_image(
    pattern_size: Tuple[int, int] = (9, 6),
    square_px: int = 80,
    margin_px: int = 40,
) -> np.ndarray:
    """Image imprimable d'un damier (noir/blanc) pour la calibration optique.

    `pattern_size` = coins intérieurs → le damier a (cols+1) × (rows+1) cases.
    """
    cols, rows = pattern_size[0] + 1, pattern_size[1] + 1
    w = cols * square_px + 2 * margin_px
    h = rows * square_px + 2 * margin_px
    img = np.full((h, w), 255, dtype=np.uint8)
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2 == 0:
                x0 = margin_px + c * square_px
                y0 = margin_px + r * square_px
                img[y0:y0 + square_px, x0:x0 + square_px] = 0
    return img
