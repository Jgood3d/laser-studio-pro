"""Polices embarquées (resources/fonts/) : disponibles sur tous les systèmes,
quelles que soient les polices installées. Utilisées par les modèles de la
bibliothèque et l'éditeur vectoriel (textes).

    load_bundled_fonts()      # après la création de QApplication

Ajouter une police : déposer le fichier .ttf / .otf dans resources/fonts/,
avec sa licence (une licence libre compatible avec la GPL, OFL par exemple).
"""
import os

from PyQt6.QtGui import QFontDatabase

from laser_studio.core.paths import RESOURCES_DIRNAME, resource_candidates

FONTS_DIRNAME = "fonts"
FONT_EXTENSIONS = (".ttf", ".otf")
# Police par défaut des textes manuscrits des modèles (embarquée).
SCRIPT_FONT = "Dancing Script"

_loaded = None


def bundled_font_files():
    """Fichiers de police de resources/fonts/ (à côté de l'exécutable et
    dans le bundle)."""
    files = []
    for folder in resource_candidates(FONTS_DIRNAME):
        if os.path.basename(os.path.dirname(folder)) != RESOURCES_DIRNAME or not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if name.lower().endswith(FONT_EXTENSIONS) and path not in files:
                files.append(path)
    return files


def load_bundled_fonts():
    """Enregistre les polices embarquées (une seule fois). Renvoie les noms
    de familles ajoutés."""
    global _loaded
    if _loaded is None:
        _loaded = []
        for path in bundled_font_files():
            font_id = QFontDatabase.addApplicationFont(path)
            if font_id >= 0:
                _loaded += [f for f in QFontDatabase.applicationFontFamilies(font_id) if f not in _loaded]
    return list(_loaded)
