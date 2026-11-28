"""Détection du sujet par réseau de neurones (U2-Net léger, ~4,5 Mo) via onnxruntime — optionnelle.

Si onnxruntime n'est pas installé ou si le modèle ne peut pas être téléchargé, `available()` / `mask()`
renvoient False / None et le Studio utilise ses méthodes classiques (aucune erreur).
Modèle : téléchargé une seule fois dans resources/models/ (à côté de ce fichier).
"""
import hashlib
import os
import threading
import time
import urllib.request

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
def _model_dir():
    """Modèle téléchargé à côté du module, ou dans le profil de l'utilisateur si on ne peut pas y écrire (appli compilée)."""
    import sys
    if not getattr(sys, "frozen", False) and os.access(HERE, os.W_OK):
        return os.path.join(HERE, "resources", "models")
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "StencilStudio", "models")


MODEL_DIR = _model_dir()
MODEL_FILE = os.path.join(MODEL_DIR, "u2netp.onnx")
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
# Empreinte du modèle attendu (celui livré dans resources/models/ et à MODEL_URL) : un fichier corrompu ou
# altéré n'est ni gardé ni chargé.
MODEL_SHA256 = "309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()
_LOCK = threading.Lock()
_SESS = [None]
_ERR = [""]
_RETRY_AT = [0.0]


def has_runtime():
    try:
        import onnxruntime  # noqa: F401
        return True
    except Exception:
        return False


FEDORA_INSTALL = "sudo dnf install --setopt=install_weak_deps=False python3-onnxruntime"
PIP_INSTALL = "pip install onnxruntime"


def _os_release_ids(path="/etc/os-release"):
    """ID et ID_LIKE de la distribution Linux (ensemble vide ailleurs ou si le fichier manque)."""
    ids = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                key, _, value = line.strip().partition("=")
                if key in ("ID", "ID_LIKE"):
                    ids.update(value.strip("\"'").split())
    except OSError:
        pass
    return ids


def install_command(os_release="/etc/os-release"):
    """Commande à proposer pour installer onnxruntime.

    Sur Fedora (et dérivées), avec le Python du système, c'est le paquet RPM : pip y installerait un
    doublon hors de dnf. install_weak_deps=False évite LaTeX et matplotlib, que sympy (requis par
    onnxruntime) recommande. Dans un environnement virtuel ou une appli compilée, pip reste la voie.
    """
    import sys
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not getattr(sys, "frozen", False) and not in_venv and "fedora" in _os_release_ids(os_release):
        return FEDORA_INSTALL
    return PIP_INSTALL


def last_error():
    return _ERR[0]


def _session():
    if _SESS[0] is not None:
        return _SESS[0]
    if time.time() < _RETRY_AT[0]:
        return None                       # échec récent (pas de réseau...) : on ne réessaie pas à chaque aperçu
    with _LOCK:
        if _SESS[0] is not None:
            return _SESS[0]
        try:
            import onnxruntime as ort
            if not os.path.isfile(MODEL_FILE) or _sha256(MODEL_FILE) != MODEL_SHA256:
                os.makedirs(MODEL_DIR, exist_ok=True)
                tmp = MODEL_FILE + ".part"
                with urllib.request.urlopen(MODEL_URL, timeout=60) as r, open(tmp, "wb") as f:
                    while True:
                        b = r.read(1 << 16)
                        if not b:
                            break
                        f.write(b)
                if _sha256(tmp) != MODEL_SHA256:
                    os.remove(tmp)
                    raise ValueError("modèle téléchargé corrompu ou différent de celui attendu")
                os.replace(tmp, MODEL_FILE)
            _SESS[0] = ort.InferenceSession(MODEL_FILE, providers=["CPUExecutionProvider"])
            _ERR[0] = ""
        except Exception as e:  # pas de runtime, pas de réseau, modèle corrompu...
            _ERR[0] = str(e) or e.__class__.__name__
            _SESS[0] = None
            _RETRY_AT[0] = time.time() + 300
    return _SESS[0]


def mask(rgb, valid=None):
    """Masque uint8 (1 = sujet) de la taille de `rgb`, ou None si indisponible / sujet introuvable."""
    s = _session()
    if s is None:
        return None
    h, w = rgb.shape[:2]
    x = cv2.resize(rgb, (320, 320), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    try:
        out = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    except Exception as e:
        _ERR[0] = str(e)
        return None
    out = (out - out.min()) / max(1e-6, out.max() - out.min())
    m = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
    m = (m > 0.5).astype(np.uint8)
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return None
    big = st[1:, cv2.CC_STAT_AREA].max()
    keep = [i + 1 for i in range(n - 1) if st[i + 1, cv2.CC_STAT_AREA] >= 0.05 * big]
    m = np.isin(lbl, keep).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)      # trous comblés
    m = np.zeros_like(m)
    cv2.drawContours(m, cnts, -1, 1, -1)
    cov = float(m.mean())
    if cov < 0.02 or cov > 0.97:
        return None
    if valid is not None:
        m = m & valid
    return m
