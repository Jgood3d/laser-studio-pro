"""Mesure du temps d'ouverture de la fenêtre du Studio : « +1.23 s message »
dans stencil_studio_timing.log (dossier temporaire) et sur la sortie
standard, compté depuis le clic sur le menu (ou le début du préchauffage)."""
import os
import tempfile
import time

_T0 = [None]


def restart():
    """Le compteur repart de zéro (clic sur le menu)."""
    _T0[0] = None


def log(msg):
    now = time.perf_counter()
    if _T0[0] is None:
        _T0[0] = now
    line = f"+{now - _T0[0]:6.2f} s  {msg}"
    try:
        print("[stencil] " + line, flush=True)
    except Exception:
        pass
    try:
        with open(os.path.join(tempfile.gettempdir(), "stencil_studio_timing.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
