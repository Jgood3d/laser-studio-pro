"""Code source de l'interface, réparti entre ui_setup_mixin.py et les fichiers ui_*.py."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ui_files():
    """Fichiers de l'interface, relatifs à la racine du projet."""
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "ui_*.py")))


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
