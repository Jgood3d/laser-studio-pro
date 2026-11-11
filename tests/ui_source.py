"""Code source de l'interface, réparti entre main_window.py, les fichiers ui_*.py et le paquet ui/."""
import glob
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")


def ui_files():
    """Fichiers de l'interface, relatifs à la racine : main_window.py, ui_*.py et le paquet ui/."""
    files = [os.path.join(ROOT, "main_window.py")]
    files += glob.glob(os.path.join(ROOT, "ui_*.py"))
    files += glob.glob(os.path.join(ROOT, "ui", "**", "*.py"), recursive=True)
    return sorted(os.path.relpath(p, ROOT) for p in files)


def _join_wrapped_calls(src):
    """Remet sur une ligne les appels coupés par le formatage (79 caractères)."""
    src = re.sub(r"\(\n\s+", "(", src)
    src = re.sub(r",?\n\s+\)", ")", src)
    return re.sub(r",\n\s+", ", ", src)


def ui_source():
    """Texte de tous les fichiers de l'interface, mis bout à bout, sans dépendre de leur formatage."""
    parts = []
    for name in ui_files():
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            parts.append(f.read().replace("\r\n", "\n"))
    return _join_wrapped_calls("\n".join(parts))


def project_state_source():
    """Code qui lit et réapplique l'état d'un projet (main_window.py :
    _capture_project et _restore_project)."""
    with open(os.path.join(ROOT, "main_window.py"), encoding="utf-8") as f:
        src = f.read().replace("\r\n", "\n")
    start = src.index("    def _capture_project(self):")
    end = src.index("    # -- Événements de la fenêtre", start)
    return src[start:end]
