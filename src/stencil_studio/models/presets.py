"""Réglages enregistrés de Stencil Studio (« Enregistrer sous... » dans la
page) : un fichier presets.json.

    store = PresetsStore()
    store.save({"Mon réglage": {...}})
    store.load()                            # {} si absent ou illisible
"""
import json
import os
import sys

# Dossier du paquet stencil_studio.
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir():
    """Dossier des données modifiables (réglages mémorisés). Dans le dossier du Studio si on peut y écrire ; sinon (LSP compilé
    avec PyInstaller, installation dans Program Files ou par un paquet...) dans le profil de l'utilisateur."""
    if not getattr(sys, "frozen", False) and os.access(PACKAGE_DIR, os.W_OK):
        return PACKAGE_DIR
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, "StencilStudio")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return PACKAGE_DIR
    return d


class PresetsStore:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "presets.json")

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                o = json.load(f)
            return o if isinstance(o, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self, obj):
        """Écriture atomique (fichier temporaire puis remplacement)."""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)
