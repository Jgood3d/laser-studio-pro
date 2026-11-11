"""Fichiers Python de l'application, analysés par les outils et les tests.

Ce sont les fichiers de la racine du projet et ceux des paquets ui/, core/,
grbl/, i18n/, image/ et controllers/, avec leurs sous-dossiers. Les
autres dossiers (tests, tools, stencil_studio, .venv...) ne sont pas
concernés.
"""

import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paquets de l'application, parcourus avec leurs sous-dossiers.
PACKAGES = ("ui", "grbl", "i18n", "image", "controllers", "core")


def python_files(root=ROOT):
    """Chemins des fichiers .py de l'application, triés."""
    files = glob.glob(os.path.join(root, "*.py"))
    for package in PACKAGES:
        pattern = os.path.join(root, package, "**", "*.py")
        files += glob.glob(pattern, recursive=True)
    return sorted(files)


def display_name(path, root=ROOT):
    """Nom à afficher dans un rapport : chemin relatif à la racine.

    ui/about/dialog.py et ui/support/dialog.py restent ainsi distincts.
    """
    path = os.path.abspath(path)
    if path.startswith(os.path.abspath(root) + os.sep):
        return os.path.relpath(path, root)
    return os.path.basename(path)
