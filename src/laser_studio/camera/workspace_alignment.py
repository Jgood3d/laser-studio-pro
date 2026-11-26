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
    # Hauteur du plan des tags au-dessus du plateau : 0 pour des tags imprimés à plat sur le plateau,
    # l'épaisseur de la matière quand ils sont gravés dessus.
    tag_height_mm: float = 0.0

    def to_dict(self) -> dict:
        return {
            "homography": self.homography.tolist(),
            "inverse": self.inverse.tolist(),
            "image_size": list(self.image_size),
            "used_tags": list(self.used_tags),
            "reprojection_error_mm": float(self.reprojection_error_mm),
            "tag_height_mm": float(self.tag_height_mm),
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
            tag_height_mm=float(data.get("tag_height_mm", 0.0)),
        )


def generate_apriltag_targets(
    bed_w: float,
    bed_h: float,
    margin_mm: float = 20.0,
    tag_size_mm: float = 40.0,
    grid: Tuple[int, int] = (2, 2),
) -> List[AlignmentTarget]:
    """Place une grille d'AprilTags sur le plateau (par défaut 2×2 : les 4 coins).

    `margin_mm` : distance entre le bord du plateau et le bord du tag (c'est aussi le cadre que le gabarit
    trace, de la taille du tag). Un retrait de 20 mm évite les bords du plateau (rails, butées, coins de l'image où l'objectif déforme le plus). Les identifiants vont de 0 à
    (cols*rows - 1), ligne par ligne en partant du bas-gauche (repère machine Y↑).
    """
    cols, rows = grid
    if cols < 2 or rows < 2:
        raise ValueError("La grille d'alignement doit avoir au moins 2×2 tags")
    side = tag_cut_side_mm(tag_size_mm)
    half = side / 2.0
    x0, x1 = margin_mm + half, bed_w - margin_mm - half
    y0, y1 = margin_mm + half, bed_h - margin_mm - half
    # Deux carrés voisins ne doivent pas se toucher : il faut de la place pour les découper.
    gap = side + 2.0 * tag_quiet_mm(tag_size_mm)
    if (x1 - x0) / (cols - 1) < gap or (y1 - y0) / (rows - 1) < gap:
        raise ValueError("Plateau trop petit pour la marge et la taille de tag demandées")

    xs = [x0 + i * (x1 - x0) / (cols - 1) for i in range(cols)]
    ys = [y0 + j * (y1 - y0) / (rows - 1) for j in range(rows)]

    targets: List[AlignmentTarget] = []
    tag_id = 0
    for cy in ys:                        # j=0 → bas
        for cx in xs:
            targets.append(AlignmentTarget(tag_id=tag_id, cx_mm=cx, cy_mm=cy, size_mm=tag_size_mm))
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


def tag_quiet_mm(size_mm: float) -> float:
    """Zone claire à garder autour du tag (au moins une case) : la matière du plateau, ou le blanc du papier."""
    return max(6.0, size_mm * 0.15)


def tag_cut_side_mm(size_mm: float) -> float:
    """Côté du carré découpé et du cadre du gabarit : celui du tag (40 mm pour un tag de 40 mm), sans marge.
    Le tag imprimé se découpe le long de son bord noir et se pose dans le cadre de même taille."""
    return float(size_mm)


TAG_CELLS = 8      # un tag 36h11 = 6×6 cases de données + 1 case de bordure de chaque côté


def _detector(inverted: bool) -> "cv2.aruco.ArucoDetector":
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.cornerRefinementWinSize = 5
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 63
    params.adaptiveThreshWinSizeStep = 6
    params.minMarkerPerimeterRate = 0.02
    params.detectInvertedMarker = inverted
    return cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(APRILTAG_DICT), params)


def _detect_pass(gray: np.ndarray, scale: float, expected) -> Dict[int, np.ndarray]:
    """Une passe de détection (tag normal puis tag inversé), coins ramenés à l'échelle de l'image d'origine."""
    found: Dict[int, np.ndarray] = {}
    for inverted in (False, True):
        corners, ids, _rejected = _detector(inverted).detectMarkers(gray)
        if ids is None:
            continue
        for quad, tag_id in zip(corners, ids.flatten()):
            tid = int(tag_id)
            if expected is not None and tid not in expected:
                continue
            found.setdefault(tid, quad.reshape(4, 2).astype(np.float64) / scale)
    return found


def detect_apriltag_corners(
    image: np.ndarray,
    expected_ids: Optional[Sequence[int]] = None,
) -> Dict[int, np.ndarray]:
    """Détecte les AprilTags et renvoie {tag_id: coins (4×2, pixels)}.

    Ordre des coins : haut-gauche, haut-droit, bas-droit, bas-gauche du TAG (pas de l'image).

    Les tags gravés sur une matière sombre (peinte en noir) apparaissent en négatif : ils sont
    cherchés aussi. Si des tags manquent, on retente avec le contraste renforcé puis l'image
    agrandie ×2 (petits tags).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    expected = None if expected_ids is None else set(int(i) for i in expected_ids)
    wanted = len(expected) if expected is not None else None

    found = _detect_pass(gray, 1.0, expected)
    if wanted is None or len(found) < wanted:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
        for tid, quad in _detect_pass(clahe, 1.0, expected).items():
            found.setdefault(tid, quad)
    if wanted is None or len(found) < wanted:
        big = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        for tid, quad in _detect_pass(big, 2.0, expected).items():
            found.setdefault(tid, quad)
    return found


def tag_cell_px(corners: np.ndarray) -> float:
    """Taille d'une case du tag dans l'image, en pixels (≥ 6 recommandé, 4 = limite)."""
    sides = [np.linalg.norm(corners[i] - corners[(i + 1) % 4]) for i in range(4)]
    return float(np.mean(sides)) / TAG_CELLS


def detect_apriltags(
    image: np.ndarray,
    expected_ids: Optional[Sequence[int]] = None,
) -> Dict[int, Tuple[float, float]]:
    """Centres des AprilTags détectés : {tag_id: (u, v)} en pixels (origine haut-gauche)."""
    return {tid: (float(q[:, 0].mean()), float(q[:, 1].mean()))
            for tid, q in detect_apriltag_corners(image, expected_ids).items()}


def _target_corners_mm(t: AlignmentTarget) -> np.ndarray:
    """Coins du tag en mm machine (Y↑), dans l'ordre haut-gauche, haut-droit, bas-droit, bas-gauche."""
    h = t.size_mm / 2.0
    return np.array([[t.cx_mm - h, t.cy_mm + h], [t.cx_mm + h, t.cy_mm + h],
                     [t.cx_mm + h, t.cy_mm - h], [t.cx_mm - h, t.cy_mm - h]], dtype=np.float64)


def _apply_h(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    p = (H @ np.hstack([pts, np.ones((len(pts), 1))]).T).T
    return p[:, :2] / p[:, 2:3]


def merge_detections(
    observations: Sequence[Dict[int, np.ndarray]],
    max_dev_px: float = 3.0,
) -> Dict[int, np.ndarray]:
    """Fusionne plusieurs captures : {tag_id: coins (4×2)} pour chaque tag vu au moins une fois.

    Le portique cache des tags différents selon sa position : un tag manquant dans une capture est repris
    d'une autre. Un tag vu plusieurs fois est moyenné (médiane à partir de 3 vues) pour réduire le bruit ;
    si ses vues divergent de plus de `max_dev_px` (tag à demi caché par le portique), on garde la vue où il
    paraît le plus grand.
    """
    views: Dict[int, List[np.ndarray]] = {}
    for obs in observations:
        for tid, quad in obs.items():
            views.setdefault(int(tid), []).append(np.asarray(quad, dtype=np.float64))
    merged: Dict[int, np.ndarray] = {}
    for tid, quads in views.items():
        if len(quads) == 1:
            merged[tid] = quads[0]
            continue
        stack = np.stack(quads)                                   # (n, 4, 2)
        centre = np.median(stack, axis=0) if len(quads) >= 3 else stack.mean(axis=0)
        if float(np.abs(stack - centre).max()) <= max_dev_px:
            merged[tid] = centre
        else:
            merged[tid] = max(quads, key=tag_cell_px)
    return merged


def compute_alignment(
    targets: Sequence[AlignmentTarget],
    detections: Dict[int, np.ndarray],
    image_size: Tuple[int, int],
    min_tags: int = 3,
    tag_height_mm: float = 0.0,
) -> WorkspaceAlignment:
    """Homographie pixel → mm à partir des 4 COINS de chaque tag détecté.

    L'orientation d'un tag collé n'a pas d'importance : on la retrouve pour chaque tag à partir d'une
    première estimation faite avec les centres. Lève ValueError s'il y a moins de `min_tags` tags.
    """
    by_id = {t.tag_id: t for t in targets}
    ids = sorted(tid for tid in detections if tid in by_id)
    if len(ids) < min_tags:
        raise ValueError(
            f"Pas assez de tags détectés ({len(ids)} < {min_tags}). "
            "Vérifiez l'éclairage, le contraste, la taille des tags et que la caméra voit tout le plateau."
        )

    # 1. Première estimation avec les centres (donne l'orientation de chaque tag).
    px_c = np.array([detections[i].mean(axis=0) for i in ids], dtype=np.float64)
    mm_c = np.array([[by_id[i].cx_mm, by_id[i].cy_mm] for i in ids], dtype=np.float64)
    if len(ids) >= 4:
        H0, _ = cv2.findHomography(px_c, mm_c, 0)
    else:
        affine = cv2.getAffineTransform(px_c[:3].astype(np.float32), mm_c[:3].astype(np.float32))
        H0 = np.vstack([affine, [0.0, 0.0, 1.0]])
    if H0 is None:
        raise ValueError("Impossible de calculer l'homographie (points dégénérés)")

    # 2. Pour chaque tag, la rotation (0/90/180/270°) qui colle le mieux, puis ajustement sur tous les coins.
    src, dst = [], []
    for tid in ids:
        quad = detections[tid]
        canon = _target_corners_mm(by_id[tid])
        pred = _apply_h(H0, quad)
        best = min(range(4), key=lambda s: np.linalg.norm(pred - np.roll(canon, -s, axis=0), axis=1).sum())
        src.extend(quad.tolist())
        dst.extend(np.roll(canon, -best, axis=0).tolist())
    src_pts, dst_pts = np.array(src), np.array(dst)
    H, mask = cv2.findHomography(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if H is None:
        raise ValueError("Impossible de calculer l'homographie (points dégénérés)")

    err = np.linalg.norm(_apply_h(H, src_pts) - dst_pts, axis=1)
    inl = mask.ravel().astype(bool) if mask is not None else np.ones(len(err), bool)
    mean_err = float(err[inl].mean()) if inl.any() else float(err.mean())
    # Garde-fous : un tag doit mesurer à peu près sa taille réelle une fois ramené en mm, et l'erreur rester faible.
    # Sinon (tag mal reconnu, tags posés ailleurs que sur le gabarit), l'image de la caméra se retrouverait
    # minuscule ou déformée en fond de l'éditeur.
    for tid in ids:
        mm_quad = _apply_h(H, detections[tid])
        side = float(np.mean([np.linalg.norm(mm_quad[i] - mm_quad[(i + 1) % 4]) for i in range(4)]))
        expected = by_id[tid].size_mm
        if not 0.7 * expected <= side <= 1.3 * expected:
            raise ValueError(
                f"Le tag {tid} mesure {side:.0f} mm après alignement au lieu de {expected:g} mm : "
                "les tags ne sont pas aux positions du gabarit, ou un tag est mal reconnu."
            )
    if mean_err > 5.0:
        raise ValueError(
            f"Erreur d'alignement trop grande ({mean_err:.1f} mm) : vérifiez que chaque tag est dans son "
            "cadre, avec le bon numéro, et que la calibration optique est à la même résolution."
        )
    try:
        inv = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        inv = np.linalg.pinv(H)
    return WorkspaceAlignment(homography=H, inverse=inv, image_size=image_size,
                              used_tags=ids, reprojection_error_mm=mean_err,
                              tag_height_mm=float(tag_height_mm))


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


def camera_pose_from_alignment(
    alignment: WorkspaceAlignment, camera_matrix: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Position de la caméra par rapport au plateau, déduite de l'alignement.

    `camera_matrix` : matrice de la caméra REDRESSÉE (`LensCalibration.new_camera_matrix`). Les tags sont dans le
    plan situé à `alignment.tag_height_mm` au-dessus du plateau (0 s'ils sont imprimés à plat dessus). Renvoie
    (R, t, C) : R et t passent du repère machine (mm, Z vers le haut, Z = 0 au niveau du plateau) au repère
    caméra, C est le centre optique en mm. Lève ValueError si le résultat n'est pas plausible (matrice caméra
    fausse, alignement douteux).
    """
    A = np.linalg.inv(np.asarray(camera_matrix, dtype=np.float64)) @ alignment.inverse
    n1, n2 = np.linalg.norm(A[:, 0]), np.linalg.norm(A[:, 1])
    if not np.isfinite(n1 + n2) or n1 <= 0 or n2 <= 0 or not 0.7 <= n1 / n2 <= 1.43:
        raise ValueError("pose de la caméra non calculable à partir de l'alignement")
    s = 2.0 / (n1 + n2)
    r1, r2, t_plane = A[:, 0] * s, A[:, 1] * s, A[:, 2] * s
    if t_plane[2] < 0:                             # l'origine du plateau doit être devant la caméra
        r1, r2, t_plane = -r1, -r2, -t_plane
    U, _sv, Vt = np.linalg.svd(np.column_stack([r1, r2, np.cross(r1, r2)]))
    R = U @ Vt                                     # rotation la plus proche (orthonormale)
    if np.linalg.det(R) < 0:
        raise ValueError("pose de la caméra non calculable à partir de l'alignement")
    # L'alignement décrit le plan z = tag_height : t_plane = tag_height * r3 + t.
    t = t_plane - float(alignment.tag_height_mm) * R[:, 2]
    C = -R.T @ t
    if not (50.0 <= C[2] <= 20000.0):
        raise ValueError(f"hauteur de caméra estimée invraisemblable ({C[2]:.0f} mm)")
    return R, t, C


def camera_height_mm(alignment: WorkspaceAlignment, camera_matrix: np.ndarray) -> float:
    """Hauteur estimée de la caméra au-dessus du plateau, en mm."""
    return float(camera_pose_from_alignment(alignment, camera_matrix)[2][2])


def plane_inverse_at_height(
    alignment: WorkspaceAlignment, camera_matrix: np.ndarray, height_mm: float
) -> np.ndarray:
    """Homographie mm → pixels pour le plan horizontal situé `height_mm` au-dessus du PLATEAU (dessus d'une
    pièce épaisse). Pour la hauteur des tags, c'est `alignment.inverse`."""
    if abs(height_mm - alignment.tag_height_mm) < 1e-9:
        return alignment.inverse
    R, t, C = camera_pose_from_alignment(alignment, camera_matrix)
    if height_mm >= C[2] * 0.9:
        raise ValueError(f"épaisseur {height_mm:g} mm trop proche de la caméra (à {C[2]:.0f} mm)")
    K = np.asarray(camera_matrix, dtype=np.float64)
    return K @ np.column_stack([R[:, 0], R[:, 1], height_mm * R[:, 2] + t])


def warp_to_bed(
    image: np.ndarray,
    alignment: WorkspaceAlignment,
    bed_w: float,
    bed_h: float,
    px_per_mm: float = 5.0,
    thickness_mm: Optional[float] = None,
    camera_matrix: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Projette l'image caméra dans le repère machine (image orthographique).

    `thickness_mm` : épaisseur de la matière, mesurée depuis le plateau ; None = on reste dans le plan des tags,
    sans correction. Sinon on redresse le plan du DESSUS de la pièce
    au lieu du plan des tags (`alignment.tag_height_mm`), ce qui supprime le décalage de parallaxe ; sans effet
    si les deux hauteurs sont égales. Sinon demande `camera_matrix` (celle de la caméra redressée) et lève
    ValueError si la pose de la caméra n'est pas calculable.

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
    if thickness_mm is not None and abs(thickness_mm - alignment.tag_height_mm) > 1e-9:
        if camera_matrix is None:
            raise ValueError("matrice de la caméra nécessaire pour corriger l'épaisseur")
        inverse = plane_inverse_at_height(alignment, camera_matrix, thickness_mm)
    else:
        inverse = alignment.inverse
    M = inverse @ bed_from_out
    # M va de la sortie vers la caméra (« dst → src ») : sans WARP_INVERSE_MAP, OpenCV l'inverserait et l'image
    # de la caméra se retrouverait minuscule et déplacée dans le plateau.
    return cv2.warpPerspective(image, M, (out_w, out_h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
