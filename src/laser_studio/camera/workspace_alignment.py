"""Alignement workspace : homographie pixels caméra → mm machine via AprilTags.

La caméra est fixe au plafond / cadre. On grave un motif de N AprilTags aux
positions connues (mm), on les détecte dans l'image (après correction de
distorsion), et on calcule l'homographie 3×3 qui transforme un point pixel
en coordonnées machine (origine bas-gauche, Y vers le haut).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

# Famille AprilTag utilisée (DICT_APRILTAG_36h11 est la plus robuste et
# largement supportée par OpenCV ≥ 4.7).
APRILTAG_DICT = cv2.aruco.DICT_APRILTAG_36h11


@dataclass
class AlignmentTarget:
    """Un marqueur à graver / détecter."""
    tag_id: int
    # Centre du tag dans le repère machine (mm), origine bas-gauche, Y↑
    cx_mm: float
    cy_mm: float
    size_mm: float          # côté du carré noir extérieur du tag


@dataclass
class WorkspaceAlignment:
    """Résultat de l'alignement : homographie pixel → mm."""
    # H : [x_mm, y_mm, 1]^T ~ H @ [u, v, 1]^T  (u = col, v = row image)
    homography: np.ndarray           # 3×3
    inverse: np.ndarray              # 3×3  (mm → pixel)
    image_size: Tuple[int, int]      # (width, height) de l'image utilisée
    used_tags: List[int] = field(default_factory=list)
    reprojection_error_mm: float = 0.0

    def to_dict(self) -> dict:
        return {
            "homography": self.homography.tolist(),
            "inverse": self.inverse.tolist(),
            "image_size": list(self.image_size),
            "used_tags": list(self.used_tags),
            "reprojection_error_mm": float(self.reprojection_error_mm),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceAlignment":
        H = np.array(data["homography"], dtype=np.float64)
        inv = np.array(data.get("inverse") or np.linalg.inv(H), dtype=np.float64)
        return cls(
            homography=H,
            inverse=inv,
            image_size=tuple(data["image_size"]),
            used_tags=list(data.get("used_tags", [])),
            reprojection_error_mm=float(data.get("reprojection_error_mm", 0.0)),
        )


def generate_apriltag_targets(
    bed_w: float,
    bed_h: float,
    margin_mm: float = 15.0,
    tag_size_mm: float = 20.0,
    grid: Tuple[int, int] = (3, 3),
) -> List[AlignmentTarget]:
    """Place une grille d'AprilTags à l'intérieur du plateau.

    Les tags sont centrés dans une zone rétractée de `margin_mm` par rapport
    aux bords. Les identifiants vont de 0 à (cols*rows - 1), ligne par ligne
    en partant du bas-gauche (cohérent avec le repère machine Y↑).
    """
    cols, rows = grid
    if cols < 2 or rows < 2:
        raise ValueError("La grille d'alignement doit avoir au moins 2×2 tags")
    usable_w = bed_w - 2 * margin_mm
    usable_h = bed_h - 2 * margin_mm
    if usable_w <= tag_size_mm or usable_h <= tag_size_mm:
        raise ValueError("Plateau trop petit pour la marge et la taille de tag demandées")

    xs = [margin_mm + (0 if cols == 1 else i * usable_w / (cols - 1)) for i in range(cols)]
    ys = [margin_mm + (0 if rows == 1 else j * usable_h / (rows - 1)) for j in range(rows)]

    targets: List[AlignmentTarget] = []
    tag_id = 0
    for j, cy in enumerate(ys):          # j=0 → bas
        for i, cx in enumerate(xs):
            targets.append(AlignmentTarget(
                tag_id=tag_id,
                cx_mm=cx,
                cy_mm=cy,
                size_mm=tag_size_mm,
            ))
            tag_id += 1
    return targets


def _tag_image(tag_id: int, size_px: int = 200, border_bits: int = 1) -> np.ndarray:
    """Image binaire (0/255) d'un AprilTag 36h11."""
    dictionary = cv2.aruco.getPredefinedDictionary(APRILTAG_DICT)
    # generateImageMarker existe depuis OpenCV 4.7
    img = cv2.aruco.generateImageMarker(dictionary, tag_id, size_px, borderBits=border_bits)
    return img


def apriltag_black_cells(tag_id: int, border_bits: int = 1) -> np.ndarray:
    """Grille des cases d'un AprilTag 36h11 (8×8 avec sa bordure) : True = case noire."""
    img = _tag_image(tag_id, size_px=6 + 2 * border_bits, border_bits=border_bits)
    return img == 0


def apriltag_engrave_polygons(target: AlignmentTarget) -> List[List[Tuple[float, float]]]:
    """Le vrai motif d'un AprilTag, à graver : rectangles (mm, Y vers le haut) des cases NOIRES, centré sur la
    cible. Les cases noires voisines sont regroupées en rectangles (une ligne de cases, puis fusion verticale des
    lignes identiques). Les cases blanches ne sont pas gravées : c'est la matière claire qui les fait.

    Le tag fait `target.size_mm` de côté, bordure noire comprise ; il lui faut une zone claire tout autour."""
    cells = apriltag_black_cells(target.tag_id)
    n_rows, n_cols = cells.shape
    cell = target.size_mm / n_cols
    x_left = target.cx_mm - target.size_mm / 2.0
    y_top = target.cy_mm + target.size_mm / 2.0

    rects = []      # [col_debut, col_fin, ligne_debut, ligne_fin] (fin exclue)
    open_runs = {}  # (col_debut, col_fin) -> rectangle encore extensible vers le bas
    for r in range(n_rows):
        runs, c = [], 0
        while c < n_cols:
            if cells[r, c]:
                c0 = c
                while c < n_cols and cells[r, c]:
                    c += 1
                runs.append((c0, c))
            else:
                c += 1
        still_open = {}
        for run in runs:
            rect = open_runs.get(run)
            if rect is not None and rect[3] == r:
                rect[3] = r + 1
            else:
                rect = [run[0], run[1], r, r + 1]
                rects.append(rect)
            still_open[run] = rect
        open_runs = still_open

    polygons = []
    for c0, c1, r0, r1 in rects:
        xa, xb = x_left + c0 * cell, x_left + c1 * cell
        ya, yb = y_top - r1 * cell, y_top - r0 * cell
        polygons.append([(xa, ya), (xb, ya), (xb, yb), (xa, yb)])
    return polygons


def targets_to_engrave_paths(
    targets: Sequence[AlignmentTarget],
    kerf_mm: float = 0.0,
) -> List[List[Tuple[float, float]]]:
    """Contours carrés (mm) à graver/découper pour chaque tag.

    Pour une V1 simple on grave le contour extérieur + une croix centrale.
    (Le motif complet du tag peut être ajouté plus tard via bitmap fill.)
    """
    paths: List[List[Tuple[float, float]]] = []
    for t in targets:
        half = t.size_mm / 2.0
        # Carré extérieur (CCW)
        paths.append([
            (t.cx_mm - half, t.cy_mm - half),
            (t.cx_mm + half, t.cy_mm - half),
            (t.cx_mm + half, t.cy_mm + half),
            (t.cx_mm - half, t.cy_mm + half),
            (t.cx_mm - half, t.cy_mm - half),
        ])
        # Croix centrale (aide visuelle + détection manuelle de secours)
        arm = half * 0.35
        paths.append([
            (t.cx_mm - arm, t.cy_mm),
            (t.cx_mm + arm, t.cy_mm),
        ])
        paths.append([
            (t.cx_mm, t.cy_mm - arm),
            (t.cx_mm, t.cy_mm + arm),
        ])
    return paths


def detect_apriltags(
    image: np.ndarray,
    expected_ids: Optional[Sequence[int]] = None,
) -> Dict[int, Tuple[float, float]]:
    """Détecte les centres des AprilTags dans une image (BGR ou grise).

    Renvoie {tag_id: (u, v)} en coordonnées pixel (origine haut-gauche image,
    u vers la droite, v vers le bas).
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    dictionary = cv2.aruco.getPredefinedDictionary(APRILTAG_DICT)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dictionary, parameters)
    corners, ids, _rejected = detector.detectMarkers(gray)

    found: Dict[int, Tuple[float, float]] = {}
    if ids is None:
        return found
    for i, tag_id in enumerate(ids.flatten()):
        tid = int(tag_id)
        if expected_ids is not None and tid not in expected_ids:
            continue
        # Centre = moyenne des 4 coins
        pts = corners[i][0]
        u = float(pts[:, 0].mean())
        v = float(pts[:, 1].mean())
        found[tid] = (u, v)
    return found


def compute_homography(
    targets: Sequence[AlignmentTarget],
    detections: Dict[int, Tuple[float, float]],
    image_size: Tuple[int, int],
    min_tags: int = 4,
) -> WorkspaceAlignment:
    """Calcule l'homographie pixel → mm à partir des détections.

    Lève ValueError s'il y a moins de `min_tags` correspondances.
    """
    src = []  # pixels (u, v)
    dst = []  # mm (x, y)
    used = []
    by_id = {t.tag_id: t for t in targets}
    for tid, (u, v) in detections.items():
        if tid not in by_id:
            continue
        t = by_id[tid]
        src.append([u, v])
        dst.append([t.cx_mm, t.cy_mm])
        used.append(tid)

    if len(used) < min_tags:
        raise ValueError(
            f"Pas assez de tags détectés ({len(used)} < {min_tags}). "
            "Vérifiez l'éclairage, le contraste et que la caméra voit tout le plateau."
        )

    src_pts = np.array(src, dtype=np.float64)
    dst_pts = np.array(dst, dtype=np.float64)
    H, mask = cv2.findHomography(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if H is None:
        raise ValueError("Impossible de calculer l'homographie (points dégénérés)")

    # Erreur de reprojection moyenne (mm)
    ones = np.ones((len(src_pts), 1))
    pix_h = np.hstack([src_pts, ones])
    pred = (H @ pix_h.T).T
    pred = pred[:, :2] / pred[:, 2:3]
    err = np.linalg.norm(pred - dst_pts, axis=1)
    if mask is not None:
        inliers = mask.ravel().astype(bool)
        mean_err = float(err[inliers].mean()) if inliers.any() else float(err.mean())
    else:
        mean_err = float(err.mean())

    try:
        inv = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        inv = np.linalg.pinv(H)

    return WorkspaceAlignment(
        homography=H,
        inverse=inv,
        image_size=image_size,
        used_tags=sorted(used),
        reprojection_error_mm=mean_err,
    )


def pixel_to_mm(
    u: float, v: float, alignment: WorkspaceAlignment
) -> Tuple[float, float]:
    """Transforme un point image (u, v) en coordonnées machine (x_mm, y_mm)."""
    p = alignment.homography @ np.array([u, v, 1.0], dtype=np.float64)
    return float(p[0] / p[2]), float(p[1] / p[2])


def mm_to_pixel(
    x_mm: float, y_mm: float, alignment: WorkspaceAlignment
) -> Tuple[float, float]:
    """Transforme un point machine (x_mm, y_mm) en pixel (u, v)."""
    p = alignment.inverse @ np.array([x_mm, y_mm, 1.0], dtype=np.float64)
    return float(p[0] / p[2]), float(p[1] / p[2])


def warp_to_bed(
    image: np.ndarray,
    alignment: WorkspaceAlignment,
    bed_w: float,
    bed_h: float,
    px_per_mm: float = 5.0,
) -> np.ndarray:
    """Projette l'image caméra dans le repère machine (image orthographique).

    Le résultat a une taille (bed_w * px_per_mm) × (bed_h * px_per_mm).
    Origine image = coin bas-gauche machine ; Y image vers le haut du plateau
    est géré en retournant verticalement pour l'affichage Qt (origine haut-gauche).
    """
    out_w = max(1, int(round(bed_w * px_per_mm)))
    out_h = max(1, int(round(bed_h * px_per_mm)))

    # Matrice qui envoie un pixel de l'image de sortie vers les mm machine,
    # puis vers les pixels caméra via inverse.
    # Pixel sortie (col, row) avec row=0 en haut → y_mm = bed_h - row/px_per_mm
    # x_mm = col / px_per_mm
    scale = 1.0 / px_per_mm
    # [x_mm]   [ scale   0    0      ] [col]
    # [y_mm] = [ 0   -scale  bed_h  ] [row]
    # [ 1  ]   [ 0      0     1     ] [ 1 ]
    bed_from_out = np.array([
        [scale, 0.0, 0.0],
        [0.0, -scale, bed_h],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    # pixel_cam = inverse @ bed_from_out @ pixel_out
    M = alignment.inverse @ bed_from_out
    return cv2.warpPerspective(image, M, (out_w, out_h), flags=cv2.INTER_LINEAR)
