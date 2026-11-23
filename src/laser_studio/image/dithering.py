"""Traitement et tramage de l'image à graver, sans Qt.

    out_arr, dither_img = process_image(raw_image, params)

`params` : w_mm, h_mm, lmm (taille et résolution de gravure), mirror_h,
mirror_v, bright, contrast, gamma (× 100), sharp, invert et algo, au format
de ImageSettings.processing_params complété par la taille. Le calcul tourne
dans un thread (workers.ImageProcessingWorker) ; la comparaison des
algorithmes (comparison_thumbnails) est assez rapide pour le thread de
l'interface.
"""
import numpy as np
from PIL import Image, ImageEnhance

from laser_studio.image.filters import sharpen_image

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

GRAYSCALE = "Niveaux de Gris"
THRESHOLD = "Seuil Simple (Binaire)"
# Algorithmes de tramage, dans l'ordre de la liste de l'onglet « Graver une image ».
ALGORITHMS = (
    "Floyd-Steinberg",
    "Jarvis, Judice & Ninke",
    "Stucki",
    "Atkinson",
    "Sierra",
    "Sierra Lite (rapide)",
    "Burkes",
    "Bayer 2x2 (ordonné)",
    "Bayer 4x4 (ordonné)",
    "Bayer 8x8 (ordonné)",
    THRESHOLD,
    GRAYSCALE,
)
# Comparés côte à côte (comparison_thumbnails) : les tramages, sans le seuil ni les niveaux de gris.
COMPARED_ALGORITHMS = ALGORITHMS[:10]
# Taille maxi (px) des vignettes de la comparaison.
THUMBNAIL_SIZE = 220

ERROR_DIFFUSION_KERNELS = {
    "Jarvis, Judice & Ninke": [
        (0, 1, 7/48), (0, 2, 5/48),
        (1, -2, 3/48), (1, -1, 5/48), (1, 0, 7/48), (1, 1, 5/48), (1, 2, 3/48),
        (2, -2, 1/48), (2, -1, 3/48), (2, 0, 5/48), (2, 1, 3/48), (2, 2, 1/48)
    ],
    "Stucki": [
        (0, 1, 8/42), (0, 2, 4/42),
        (1, -2, 2/42), (1, -1, 4/42), (1, 0, 8/42), (1, 1, 4/42), (1, 2, 2/42),
        (2, -2, 1/42), (2, -1, 2/42), (2, 0, 4/42), (2, 1, 2/42), (2, 2, 1/42)
    ],
    "Atkinson": [
        (0, 1, 1/8), (0, 2, 1/8),
        (1, -1, 1/8), (1, 0, 1/8), (1, 1, 1/8),
        (2, 0, 1/8)
    ],
    "Sierra": [
        (0, 1, 5/32), (0, 2, 3/32),
        (1, -2, 2/32), (1, -1, 4/32), (1, 0, 5/32), (1, 1, 4/32), (1, 2, 2/32),
        (2, -1, 2/32), (2, 0, 3/32), (2, 1, 2/32)
    ],
    "Sierra Lite (rapide)": [
        (0, 1, 2/4),
        (1, -1, 1/4), (1, 0, 1/4)
    ],
    "Burkes": [
        (0, 1, 8/32), (0, 2, 4/32),
        (1, -2, 2/32), (1, -1, 4/32), (1, 0, 8/32), (1, 1, 4/32), (1, 2, 2/32)
    ]
}

if HAS_NUMBA:
    @njit(cache=True)
    def _diffuse_numba(arr, out, kdy, kdx, kw):
        h, w = arr.shape
        n_taps = len(kw)
        for y in range(h):
            for x in range(w):
                old_val = arr[y, x]
                new_val = 255.0 if old_val > 128.0 else 0.0
                out[y, x] = new_val
                err = old_val - new_val
                for i in range(n_taps):
                    ny = y + kdy[i]
                    nx = x + kdx[i]
                    if 0 <= ny < h and 0 <= nx < w:
                        arr[ny, nx] += err * kw[i]
        return out


def _diffuse_pure_python(arr_in, kernel):
    """Repli sans numba : la diffusion d'erreur reste intrinsèquement séquentielle
    (chaque pixel dépend du précédent), donc impossible à vectoriser avec numpy.
    On utilise ici des listes Python natives, nettement plus rapides que l'accès
    scalaire à un tableau numpy dans une boucle Python (2 à 4x plus rapide dans
    ce cas précis)."""
    h, w = arr_in.shape
    rows = arr_in.tolist()
    out_rows = [[0] * w for _ in range(h)]
    for y in range(h):
        row = rows[y]
        for x in range(w):
            old_val = row[x]
            new_val = 255 if old_val > 128 else 0
            out_rows[y][x] = new_val
            err = old_val - new_val
            if err != 0:
                for dy, dx, weight in kernel:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        rows[ny][nx] += err * weight
    return np.array(out_rows, dtype=np.uint8)


def apply_error_diffusion(arr_in, algo):
    """Tramage de `arr_in` (float32, 0 à 255) par l'algorithme `algo` : diffusion
    d'erreur, ou tramage ordonné pour les « Bayer ». Renvoie un tableau uint8 de
    0 et 255 ; un algorithme inconnu est traité comme Jarvis, Judice & Ninke."""
    if algo == "Floyd-Steinberg":
        pil_img = Image.fromarray(np.clip(arr_in, 0, 255).astype(np.uint8))
        dithered = pil_img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        return np.where(np.array(dithered), 255, 0).astype(np.uint8)

    if algo.startswith("Bayer"):
        return apply_bayer_dither(arr_in, algo)

    h, w = arr_in.shape
    arr = arr_in.copy()
    out = np.zeros((h, w), dtype=np.uint8)
    kernel = ERROR_DIFFUSION_KERNELS.get(algo, ERROR_DIFFUSION_KERNELS.get("Jarvis, Judice & Ninke"))

    if HAS_NUMBA:
        kdy = np.array([k[0] for k in kernel], dtype=np.int64)
        kdx = np.array([k[1] for k in kernel], dtype=np.int64)
        kw = np.array([k[2] for k in kernel], dtype=np.float64)
        return _diffuse_numba(arr, out, kdy, kdx, kw)
    return _diffuse_pure_python(arr, kernel)


def apply_bayer_dither(arr_in, algo):
    """Tramage ordonné (matrice de Bayer) : contrairement à la diffusion
    d'erreur, chaque pixel est comparé à un seuil fixe qui se répète en
    motif régulier. Résultat plus régulier/répétitif (trame en points),
    souvent apprécié sur le bois pour sa texture homogène et sans
    'traînées' contrairement à Floyd-Steinberg. Aussi bien plus rapide
    (aucune dépendance séquentielle entre pixels)."""
    bayer_2x2 = np.array([[0, 2], [3, 1]], dtype=np.float64)
    bayer_4x4 = np.array([
        [0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]
    ], dtype=np.float64)
    bayer_8x8 = np.array([
        [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
        [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]
    ], dtype=np.float64)
    matrix = bayer_8x8 if "8x8" in algo else (bayer_2x2 if "2x2" in algo else bayer_4x4)
    n = matrix.shape[0]
    threshold_map = (matrix + 0.5) / (n * n) * 255.0

    h, w = arr_in.shape
    tiled = np.tile(threshold_map, (h // n + 1, w // n + 1))[:h, :w]
    return np.where(arr_in > tiled, 255, 0).astype(np.uint8)


def _adjust_tones(img, bright, contrast, gamma):
    """Luminosité et contraste (PIL), puis gamma : tableau float32."""
    if bright != 0:
        img = ImageEnhance.Brightness(img).enhance(1.0 + bright / 100.0)
    if contrast != 0:
        img = ImageEnhance.Contrast(img).enhance(1.0 + contrast / 100.0)
    arr = np.array(img, dtype=np.float32)
    if gamma != 1.0:
        arr = 255.0 * ((arr / 255.0) ** (1.0 / gamma))
        arr = np.clip(arr, 0, 255)
    return arr


def process_image(raw_image, params):
    """Image prête à graver : `raw_image` (PIL, niveaux de gris) mise à la taille
    de gravure (w_mm × h_mm à lmm lignes/mm), miroirs, tons, netteté, négatif
    puis tramage. Renvoie (tableau uint8 : 0 = brûlé, image PIL du tableau), ou
    None s'il n'y a pas d'image ou si la taille fait moins d'un pixel."""
    if not raw_image:
        return None
    lmm = params['lmm']
    px_w = int(params['w_mm'] * lmm)
    px_h = int(params['h_mm'] * lmm)
    if px_w < 1 or px_h < 1:
        return None

    img = raw_image.resize((px_w, px_h), Image.Resampling.LANCZOS)
    if params['mirror_h']:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if params['mirror_v']:
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    arr = _adjust_tones(img, params['bright'], params['contrast'], params['gamma'] / 100.0)

    # Netteté : après les réglages de tons, juste avant l'inversion et le tramage.
    sharp = float(params.get('sharp', 0) or 0)
    if sharp > 0:
        sharpened = sharpen_image(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), sharp, lmm)
        arr = np.array(sharpened, dtype=np.float32)

    if params['invert']:
        arr = 255.0 - arr

    algo = params['algo']
    if algo == GRAYSCALE:
        out_arr = arr.astype(np.uint8)
    elif algo == THRESHOLD:
        out_arr = np.where(arr > 128, 255, 0).astype(np.uint8)
    else:
        out_arr = apply_error_diffusion(arr, algo)
    return out_arr, Image.fromarray(out_arr)


def comparison_thumbnails(raw_image, brightness, contrast, gamma, sharpness, invert):
    """[(algorithme, tableau tramé)] : une vignette de `raw_image` par algorithme de
    COMPARED_ALGORITHMS, avec les réglages de tons actuels (gamma × 100).
    Calculé sur une miniature basse résolution : quasi instantané."""
    img = raw_image.copy()
    img.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
    arr = _adjust_tones(img, brightness, contrast, gamma / 100.0)
    if sharpness > 0:
        arr = np.array(sharpen_image(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), sharpness),
                       dtype=np.float32)
    if invert:
        arr = 255.0 - arr
    thumbnails = []
    for algo in COMPARED_ALGORITHMS:
        try:
            thumbnails.append((algo, apply_error_diffusion(arr.copy(), algo)))
        except Exception:  # un algorithme en échec ne prive pas des autres vignettes
            continue
    return thumbnails
