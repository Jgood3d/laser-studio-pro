"""
converter.py
------------
Coeur de conversion PNG -> SVG, sans aucune dépendance à Qt.
Peut être importé directement dans Laser Studio Pro :

    from converter import ConversionSettings, convert_image_to_svg
    svg_text = convert_image_to_svg("logo.png", ConversionSettings(mode="bw"))

Algorithme :
- Mode "bw" (noir & blanc) : niveaux de gris -> seuillage -> contours OpenCV
  -> un seul <path> avec fill-rule="evenodd" (gère nativement les trous,
  ex. le centre d'un "O", sans avoir à gérer la hiérarchie des contours).
- Mode "color" : quantification couleur (k-means) -> un <path> par couleur.
- Mode de rendu "fill" (remplissage, gravure) ou "outline" (contour seul,
  découpe vectorielle). ATTENTION : "outline" trace le PÉRIMÈTRE de la
  zone noire, donc pour un simple trait dessiné (ex. un dessin au trait),
  cela produit un chemin qui longe les deux bords du trait -> visuellement
  un "doublage" du trait. Pour un dessin au trait destiné à être gravé
  en un seul passage, utiliser plutôt `centerline=True` (squelettisation),
  qui réduit chaque trait à une ligne centrale d'un seul pixel de large
  avant de la vectoriser : un seul chemin, pas de doublage.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Literal, Optional

import cv2
import numpy as np
from PIL import Image

Mode = Literal["bw", "color"]
RenderMode = Literal["fill", "outline"]
Unit = Literal["mm", "cm", "in", "px"]

_UNITS_PER_MM = {"mm": 1.0, "cm": 0.1, "in": 1.0 / 25.4, "px": None}  # px géré à part


@dataclass
class ConversionSettings:
    mode: Mode = "bw"
    render_mode: RenderMode = "fill"
    centerline: bool = False      # mode "bw" uniquement : squelette 1px au lieu du contour
    fill_threshold_px: float = 8.0  # au-delà de cette épaisseur (px), une zone est remplie
                                     # pleine plutôt que réduite à une ligne centrale
    threshold: int = 128          # 0-255, ignoré si auto_threshold=True
    auto_threshold: bool = True   # seuil automatique (Otsu)
    invert: bool = False
    blur: int = 0                 # rayon de flou de lissage (0 = aucun)
    simplify: float = 1.0         # 0 = très fidèle / détaillé, 5 = très simplifié
    min_area: float = 6.0         # aire minimale (px^2) pour garder un contour
    n_colors: int = 6             # nombre de couleurs en mode "color"
    stroke_width_mm: float = 0.1  # épaisseur de trait en mode "outline"
    output_width_mm: Optional[float] = None
    output_height_mm: Optional[float] = None
    keep_aspect_ratio: bool = True
    dpi: int = 96                 # utilisé seulement si aucune dimension n'est fournie


@dataclass
class ConversionResult:
    svg_text: str
    path_count: int
    image_width_px: int
    image_height_px: int
    output_width_mm: float
    output_height_mm: float
    preview_png: Optional[bytes] = field(default=None, repr=False)


def _load_image(source) -> np.ndarray:
    """Charge une image depuis un chemin, des bytes ou un ndarray -> RGBA numpy array."""
    if isinstance(source, np.ndarray):
        arr = source
    elif isinstance(source, (bytes, bytearray)):
        img = Image.open(io.BytesIO(source)).convert("RGBA")
        arr = np.array(img)
    else:
        img = Image.open(source).convert("RGBA")
        arr = np.array(img)
    return arr


def _compute_output_size(w_px: int, h_px: int, s: ConversionSettings) -> tuple[float, float]:
    if s.output_width_mm and s.output_height_mm and not s.keep_aspect_ratio:
        return s.output_width_mm, s.output_height_mm

    if s.output_width_mm and s.output_height_mm:
        # les deux fournis + aspect ratio verrouillé -> on respecte la largeur
        return s.output_width_mm, s.output_width_mm * h_px / w_px

    if s.output_width_mm:
        return s.output_width_mm, s.output_width_mm * h_px / w_px

    if s.output_height_mm:
        return s.output_height_mm * w_px / h_px, s.output_height_mm

    # aucune dimension fournie -> calcul depuis le DPI
    mm_per_px = 25.4 / s.dpi
    return w_px * mm_per_px, h_px * mm_per_px


def _binary_mask(gray: np.ndarray, s: ConversionSettings) -> np.ndarray:
    """Renvoie un masque binaire (255 = trait/objet) à partir du niveau de gris."""
    work = gray.copy()
    if s.blur > 0:
        k = s.blur * 2 + 1
        work = cv2.GaussianBlur(work, (k, k), 0)

    flag = cv2.THRESH_BINARY_INV if not s.invert else cv2.THRESH_BINARY
    if s.auto_threshold:
        _, binary = cv2.threshold(work, 0, 255, flag + cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(work, s.threshold, 255, flag)
    return binary


def _skeleton_to_polylines(skel: np.ndarray, min_len: int) -> list[list[tuple[int, int]]]:
    """Réduit un squelette 1px (bool array) en une liste de polylignes ouvertes,
    chaque segment n'étant parcouru qu'une seule fois (donc pas de doublage)."""
    ys, xs = np.nonzero(skel)
    pixels = set(zip(xs.tolist(), ys.tolist()))
    if not pixels:
        return []

    offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

    def neighbors(p):
        x, y = p
        return [(x + dx, y + dy) for dx, dy in offsets if (x + dx, y + dy) in pixels]

    degree = {p: len(neighbors(p)) for p in pixels}

    def walk(start, nxt):
        path = [start, nxt]
        prev, curr = start, nxt
        while degree.get(curr, 0) == 2:
            candidates = [n for n in neighbors(curr) if n != prev]
            if not candidates:
                break
            nxt2 = candidates[0]
            path.append(nxt2)
            prev, curr = curr, nxt2
        return path

    polylines: list[list[tuple[int, int]]] = []
    seen_edges: set[frozenset] = set()
    used_pixels: set = set()

    # 1) chemins partant d'une extrémité (degré 1) ou d'une jonction (degré >= 3)
    for p in sorted(pixels):
        if degree[p] == 2:
            continue
        for n in neighbors(p):
            path = walk(p, n)
            key = frozenset(path)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            polylines.append(path)
            used_pixels.update(path)

    # 2) boucles fermées isolées (ex. un rond) : que des pixels de degré 2
    remaining = pixels - used_pixels
    while remaining:
        start = next(iter(remaining))
        path = [start]
        prev, curr = None, start
        while True:
            candidates = [n for n in neighbors(curr) if n != prev]
            candidates = [n for n in candidates if n not in path or n == start]
            if not candidates:
                break
            nxt = candidates[0]
            if nxt == start and len(path) > 2:
                path.append(nxt)
                break
            path.append(nxt)
            prev, curr = curr, nxt
        remaining -= set(path)
        if len(path) >= min_len:
            polylines.append(path)

    return [p for p in polylines if len(p) >= min_len]


def _polyline_to_path_d(points: list[tuple[int, int]], scale_x: float, scale_y: float,
                         simplify: float) -> str:
    arr = np.array(points, dtype=np.int32).reshape(-1, 1, 2)
    if simplify > 0 and len(points) > 3:
        epsilon = max((simplify * 0.3) * cv2.arcLength(arr, False) / 100.0, 0.01)
        arr = cv2.approxPolyDP(arr, epsilon, False)
    pts = arr.reshape(-1, 2).astype(np.float64)
    pts[:, 0] *= scale_x
    pts[:, 1] *= scale_y
    d = f"M {pts[0][0]:.4f} {pts[0][1]:.4f} "
    d += " ".join(f"L {x:.4f} {y:.4f}" for x, y in pts[1:])
    return d


def _contours_bw(gray: np.ndarray, s: ConversionSettings) -> list[np.ndarray]:
    binary = _binary_mask(gray, s)
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return _simplify_and_filter(contours, s)


def _simplify_and_filter(contours, s: ConversionSettings) -> list[np.ndarray]:
    out = []
    for c in contours:
        if cv2.contourArea(c) < s.min_area:
            continue
        if s.simplify > 0:
            epsilon = (s.simplify * 0.3) * cv2.arcLength(c, True) / 100.0
            c = cv2.approxPolyDP(c, max(epsilon, 0.01), True)
        if len(c) >= 2:
            out.append(c)
    return out


def _contour_to_path_d(contour: np.ndarray, scale_x: float = 1.0, scale_y: float = 1.0) -> str:
    pts = contour.reshape(-1, 2).astype(np.float64)
    pts[:, 0] *= scale_x
    pts[:, 1] *= scale_y
    d = f"M {pts[0][0]:.4f} {pts[0][1]:.4f} "
    d += " ".join(f"L {x:.4f} {y:.4f}" for x, y in pts[1:])
    d += " Z"
    return d


def _build_svg(out_w_mm: float, out_h_mm: float,
                path_defs: list[str], s: ConversionSettings) -> str:
    body = "\n  ".join(path_defs)
    # viewBox exprimé directement en mm (et non en pixels source) : les
    # coordonnées des chemins sont déjà mises à l'échelle en mm, donc un
    # importeur qui lirait le viewBox sans tenir compte du suffixe "mm"
    # de width/height obtient quand même la bonne taille physique.
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{out_w_mm:.4f}mm" height="{out_h_mm:.4f}mm" '
        f'viewBox="0 0 {out_w_mm:.4f} {out_h_mm:.4f}">\n  {body}\n</svg>\n'
    )


def _rgb_to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def convert_image_to_svg(source, settings: Optional[ConversionSettings] = None) -> ConversionResult:
    """Point d'entrée principal. `source` : chemin de fichier, bytes ou ndarray RGBA."""
    s = settings or ConversionSettings()
    rgba = _load_image(source)
    h_px, w_px = rgba.shape[:2]
    out_w_mm, out_h_mm = _compute_output_size(w_px, h_px, s)

    stroke_attr = ""
    fill_rule = ' fill-rule="evenodd"'
    if s.render_mode == "outline":
        stroke_attr = f' stroke-width="{s.stroke_width_mm:.4f}"'
        fill_rule = ""

    scale_x = out_w_mm / w_px
    scale_y = out_h_mm / h_px

    path_defs: list[str] = []

    if s.mode == "bw":
        gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)

        if s.centerline:
            # Sépare les zones "épaisses" (aplats pleins : oreilles, nez...)
            # des zones "fines" (traits dessinés : cils, contours...) par
            # ouverture morphologique. Les aplats sont remplis normalement
            # (un remplissage n'est jamais "doublé"). Seuls les traits fins
            # sont réduits à une ligne centrale de 1px avant vectorisation
            # -> un seul passage, pas de doublage des bords.
            from skimage.morphology import skeletonize

            binary = _binary_mask(gray, s)
            k = max(3, int(round(s.fill_threshold_px)) | 1)  # taille impaire >= 3
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            thick_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            thick_dilated = cv2.dilate(thick_mask, kernel, iterations=1)
            thin_mask = cv2.bitwise_and(binary, cv2.bitwise_not(thick_dilated))

            thick_contours, _ = cv2.findContours(
                thick_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            thick_contours = _simplify_and_filter(thick_contours, s)
            if thick_contours:
                d_thick = " ".join(
                    _contour_to_path_d(c, scale_x, scale_y) for c in thick_contours
                )
                path_defs.append(f'<path d="{d_thick}" fill="#000000" fill-rule="evenodd"/>')

            skel = skeletonize(thin_mask > 0)
            min_len = max(3, int(s.min_area ** 0.5))
            polylines = _skeleton_to_polylines(skel, min_len)
            for pts in polylines:
                d = _polyline_to_path_d(pts, scale_x, scale_y, s.simplify)
                path_defs.append(
                    f'<path d="{d}" fill="none" stroke="#000000" '
                    f'stroke-width="{s.stroke_width_mm:.4f}" stroke-linecap="round"/>'
                )
        else:
            contours = _contours_bw(gray, s)
            d_all = " ".join(_contour_to_path_d(c, scale_x, scale_y) for c in contours)
            if d_all:
                if s.render_mode == "fill":
                    path_defs.append(f'<path d="{d_all}" fill="#000000"{fill_rule}/>')
                else:
                    path_defs.append(
                        f'<path d="{d_all}" fill="none" stroke="#000000"{stroke_attr}/>'
                    )
    else:
        rgb = rgba[:, :, :3]
        Z = rgb.reshape((-1, 3)).astype(np.float32)
        k = max(2, min(s.n_colors, 32))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
        _, labels, centers = cv2.kmeans(Z, k, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
        labels = labels.reshape(h_px, w_px)
        for i, center in enumerate(centers):
            mask = np.uint8(labels == i) * 255
            if s.blur > 0:
                kb = s.blur * 2 + 1
                mask = cv2.GaussianBlur(mask, (kb, kb), 0)
                _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = _simplify_and_filter(contours, s)
            if not contours:
                continue
            d_all = " ".join(_contour_to_path_d(c, scale_x, scale_y) for c in contours)
            hexcolor = _rgb_to_hex(center)
            if s.render_mode == "fill":
                path_defs.append(f'<path d="{d_all}" fill="{hexcolor}"{fill_rule}/>')
            else:
                path_defs.append(
                    f'<path d="{d_all}" fill="none" stroke="{hexcolor}"{stroke_attr}/>'
                )

    svg_text = _build_svg(out_w_mm, out_h_mm, path_defs, s)

    return ConversionResult(
        svg_text=svg_text,
        path_count=len(path_defs),
        image_width_px=w_px,
        image_height_px=h_px,
        output_width_mm=out_w_mm,
        output_height_mm=out_h_mm,
    )


def save_svg(result: ConversionResult, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.svg_text)
