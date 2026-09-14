"""Petits utilitaires partagés par l'application (version, chemin de l'exécutable)."""
import sys
import os

APP_VERSION = "1.0.0"


def get_app_dir():
    """Dossier où se trouve réellement l'exécutable (ou le script), pour
    localiser des fichiers voisins (icône, bannière...). Nécessaire car dans
    un .exe PyInstaller --onefile, __file__ pointe vers le dossier temporaire
    d'extraction (sys._MEIPASS), pas vers le dossier du vrai .exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_bundle_dir():
    """Dossier temporaire dans lequel PyInstaller extrait les fichiers
    embarqués via --add-data (utile seulement en mode --onefile compilé ;
    sinon identique à get_app_dir())."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', get_app_dir())
    return get_app_dir()


def find_resource(filename):
    """Cherche un fichier de ressource (icône, bannière...) à deux endroits
    possibles, dans cet ordre :
    1. à côté de l'exécutable — pratique pour remplacer/ajouter une image
       après coup, sans recompiler ;
    2. dans le bundle PyInstaller, si le fichier a été embarqué au moment
       de la compilation avec --add-data.
    Renvoie le premier chemin trouvé, ou None si absent des deux."""
    for folder in (get_app_dir(), get_bundle_dir()):
        candidate = os.path.join(folder, filename)
        if os.path.exists(candidate):
            return candidate
    return None
