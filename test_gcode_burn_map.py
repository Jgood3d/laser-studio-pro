"""Tests de non-régression de la génération du G-code d'une image.

Principe : on génère le G-code d'une petite image, puis on le « rejoue »
comme le fait GRBL (le S d'une ligne G1 s'applique au déplacement de cette
même ligne) pour reconstruire quels pixels sont réellement gravés et à quelle
puissance. On compare ensuite à ce que l'image demande.

Ces tests auraient détecté le bug où le S du segment SUIVANT était appliqué
au segment précédent (zones à garder gravées, zones à graver épargnées, une
ligne sur deux, et décalage d'un pixel en balayage droite -> gauche).

Lancer depuis le dossier du projet :
    python -m unittest discover tests -v      (ou : pytest tests)
"""
import os
import re
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import workers
except ImportError as exc:  # dépendance manquante (PyQt6, svg.path...)
    workers = None
    _IMPORT_ERROR = exc

S_MAX = 1000
SUB = 10  # sous-pixels par pixel pour mesurer les frontières


class _Params(dict):
    """Paramètres du worker : toute clé non fournie vaut ''."""
    def __missing__(self, key):
        return ""


def generate_gcode(arr, overscan=0.0, algo="Seuil Simple (Binaire)"):
    h, w = arr.shape
    params = _Params(
        width_mm=float(w), height_mm=float(h), origin_pos="Bas-Gauche (0,0)",
        offset_x=0.0, offset_y=0.0, power_engrave=100.0, speed_engrave=1000,
        enable_overscan=overscan > 0, overscan_mode="mm", overscan_dist=overscan,
        laser_cmd="M4", s_max=S_MAX, algo=algo, enable_cut=False,
    )
    worker = workers.AdvancedGCodeWorker(arr, None, params, {})
    out = {}
    worker.finished.connect(lambda gcode, *_: out.update(gcode=gcode))
    worker.error.connect(lambda msg: out.update(error=msg))
    worker.run()  # appel direct : pas besoin de démarrer le thread
    if "error" in out:
        raise AssertionError(f"Génération en erreur : {out['error']}")
    return out["gcode"]


def power_map(gcode, w, h):
    """Puissance (0..1) reçue par chaque pixel, en rejouant le G-code comme
    GRBL : le S d'une ligne G1 vaut pour le déplacement de cette ligne."""
    acc = np.zeros((h, w * SUB))
    x = y = 0.0
    s = 0.0
    for raw in gcode.splitlines():
        line = raw.split(";")[0].strip()
        if not line:
            continue
        move = re.match(r"(G0|G1)\b(.*)", line)
        if move:
            kind, rest = move.groups()
            mx = re.search(r"X(-?[\d.]+)", rest)
            my = re.search(r"Y(-?[\d.]+)", rest)
            ms = re.search(r"S(-?[\d.]+)", rest)
            nx = float(mx.group(1)) if mx else x
            ny = float(my.group(1)) if my else y
            if ms:
                s = float(ms.group(1))
            if kind == "G1" and s > 0 and nx != x:
                row = h - 1 - int(round(y))
                if 0 <= row < h:
                    a, b = sorted((x, nx))
                    ia = max(0, int(round(a * SUB)))
                    ib = min(w * SUB, int(round(b * SUB)))
                    if ib > ia:
                        acc[row, ia:ib] = s / S_MAX
            x, y = nx, ny
            continue
        modal = re.match(r"(?:M3|M4)?\s*S(\d+)", line)
        if modal:
            s = float(modal.group(1))
        elif line.startswith("M5"):
            s = 0.0
    return acc.reshape(h, w, SUB).mean(axis=2)


def _ascii(m, thr=0.5):
    return ["".join("#" if v > thr else "." for v in row) for row in m]


@unittest.skipIf(workers is None, "workers.py non importable ici (PyQt6/svg.path manquants ?)")
class BinaryBurnMapTests(unittest.TestCase):
    def assert_burn_matches(self, arr, overscan=0.0):
        h, w = arr.shape
        got = power_map(generate_gcode(arr, overscan), w, h)
        want = (arr == 0).astype(float)
        bad = np.abs(got - want) > 0.01
        if bad.any():
            self.fail(
                f"{int(bad.sum())}/{bad.size} pixels faux\n"
                "attendu :\n  " + "\n  ".join(_ascii(want)) +
                "\nobtenu :\n  " + "\n  ".join(_ascii(got))
            )

    def test_big_blocks_and_fine_pattern(self):
        # Le cas du bug : un bloc à graver, un motif fin, un bloc à NE PAS graver.
        arr = np.full((6, 30), 255, np.uint8)
        arr[:, :10] = 0
        arr[:, 10:20] = np.where(np.arange(10) % 2 == 0, 0, 255)
        self.assert_burn_matches(arr)

    def test_blocks_mirrored(self):
        arr = np.full((6, 30), 255, np.uint8)
        arr[:, 20:] = 0
        arr[:, 10:20] = np.where(np.arange(10) % 2 == 0, 255, 0)
        self.assert_burn_matches(arr)

    def test_random_binary(self):
        rng = np.random.default_rng(1)
        self.assert_burn_matches((rng.integers(0, 2, (8, 40)) * 255).astype(np.uint8))

    def test_single_vertical_edge_is_aligned_between_rows(self):
        # Une arête verticale doit tomber au même endroit sur les lignes
        # aller (gauche->droite) et retour (droite->gauche).
        arr = np.full((6, 20), 255, np.uint8)
        arr[:, 7:] = 0
        self.assert_burn_matches(arr)

    def test_with_overscan(self):
        arr = np.full((6, 30), 255, np.uint8)
        arr[:, :10] = 0
        arr[:, 10:20] = np.where(np.arange(10) % 2 == 0, 0, 255)
        self.assert_burn_matches(arr, overscan=3.0)

    def test_nothing_to_burn(self):
        self.assert_burn_matches(np.full((4, 20), 255, np.uint8))

    def test_everything_burned(self):
        self.assert_burn_matches(np.zeros((4, 20), np.uint8))


@unittest.skipIf(workers is None, "workers.py non importable ici (PyQt6/svg.path manquants ?)")
class GrayscalePowerTests(unittest.TestCase):
    def test_power_follows_pixel_darkness(self):
        # Niveaux de gris : puissance proportionnelle à (255 - valeur) / 255.
        row = np.concatenate([np.full(8, 0), np.linspace(0, 255, 16), np.full(8, 255)])
        arr = np.tile(row.astype(np.uint8), (4, 1))
        h, w = arr.shape
        got = power_map(generate_gcode(arr, 0.0, "Niveaux de Gris"), w, h)
        want = (255.0 - arr) / 255.0
        self.assertLess(np.abs(got - want).max(), 0.01)


if __name__ == "__main__":
    unittest.main()
