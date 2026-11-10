"""Code source de l'interface, réparti entre main_window.py, les fichiers ui_*.py et le paquet ui/."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
