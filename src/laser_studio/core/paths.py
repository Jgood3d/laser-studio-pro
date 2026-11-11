"""Chemins de l'application : dossier de l'exécutable, dossier des données
de l'utilisateur, fichiers de ressources (images, icône)."""
import sys
import os

# Racine du projet (sans PyInstaller) : le dossier parent de core/.
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_app_dir():
    """Dossier où se trouve réellement l'exécutable (ou le script), pour
    localiser des fichiers voisins (icône, bannière...). Nécessaire car dans
    un .exe PyInstaller --onefile, __file__ pointe vers le dossier temporaire
    d'extraction (sys._MEIPASS), pas vers le dossier du vrai .exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return _PROJECT_DIR


def get_bundle_dir():
    """Dossier temporaire dans lequel PyInstaller extrait les fichiers
    embarqués via --add-data (utile seulement en mode --onefile compilé ;
    sinon identique à get_app_dir())."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', get_app_dir())
    return get_app_dir()


def get_autosave_dir():
    """Dossier pour les fichiers de données de l'application (sauvegarde
    automatique de projet, file d'attente...) : un emplacement utilisateur
    TOUJOURS accessible en écriture, contrairement à get_app_dir() qui peut
    être en lecture seule une fois l'app installée (ex : Program Files sous
    Windows sans droits administrateur). Créé automatiquement s'il n'existe
    pas encore."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "LaserStudioPro")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        return get_app_dir()
    return path


# Dossier des ressources (images, icône), à la racine du projet et dans
# le bundle PyInstaller (--add-data "resources;resources").
RESOURCES_DIRNAME = "resources"


def resource_candidates(filename):
    """Emplacements possibles d'un fichier de ressource (icône, bannière...),
    dans l'ordre où find_resource les essaie :
    1. à côté de l'exécutable, dans resources/ puis directement à côté
       (ancien emplacement) — pratique pour remplacer/ajouter une image
       après coup, sans recompiler ;
    2. dans le bundle PyInstaller, si le fichier a été embarqué au moment
       de la compilation avec --add-data.
    Sans PyInstaller, les deux dossiers sont la racine du projet."""
    candidates = []
    for folder in (get_app_dir(), get_bundle_dir()):
        for path in (os.path.join(folder, RESOURCES_DIRNAME, filename),
                     os.path.join(folder, filename)):
            if path not in candidates:
                candidates.append(path)
    return candidates


def find_resource(filename):
    """Premier emplacement existant du fichier de ressource `filename` (voir
    resource_candidates), ou None s'il est introuvable."""
    for candidate in resource_candidates(filename):
        if os.path.exists(candidate):
            return candidate
    return None
