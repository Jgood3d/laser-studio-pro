"""Petits utilitaires partagés par l'application (version, chemin de l'exécutable)."""
import sys
import os
import json

APP_VERSION = "2.2.0"


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


def atomic_write_text(path, text, encoding="utf-8"):
    """Écrit `text` dans `path` de façon atomique : le contenu est d'abord
    écrit et vidé sur disque dans un fichier voisin « .tmp », puis ce fichier
    REMPLACE l'ancien d'un seul coup (os.replace). Un plantage, une coupure de
    courant ou un disque plein en cours d'écriture laisse donc l'ancien
    fichier intact au lieu d'un fichier tronqué — précieux pour l'autosave et
    la file d'attente, qui servent justement à se remettre d'un incident."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path, data, **dump_kwargs):
    """Sérialise `data` en JSON puis l'écrit de façon atomique (voir
    atomic_write_text). La sérialisation se fait AVANT toute écriture : une
    donnée non sérialisable ne touche donc jamais au fichier existant."""
    atomic_write_text(path, json.dumps(data, **dump_kwargs))


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
