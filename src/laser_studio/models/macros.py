"""Modèle des macros de l'utilisateur : la liste (grbl.macros.Macro), lue et enregistrée dans macros.yaml, et
un signal quand elle change.

    macros = MacrosModel()          # lit macros.yaml s'il existe
    macros.changed.connect(panel_refresh)
    macros.set_macros(nouvelles)    # remplace la liste et l'enregistre
"""
import os

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import get_logger
from laser_studio.core.paths import get_autosave_dir
from laser_studio.grbl.macros import FILE_NAME, MacroError, dump_macros, load_macros

log = get_logger()


def default_path():
    return os.path.join(get_autosave_dir(), FILE_NAME)


class MacrosModel(QObject):
    """`path` : fichier des macros (par défaut macros.yaml dans le dossier des données). S'il est illisible,
    la liste reste vide, `load_error` garde l'erreur (MacroError) et le fichier n'est pas écrasé tant que
    l'utilisateur n'a pas enregistré de nouvelles macros."""

    changed = pyqtSignal()

    def __init__(self, path=None, parent=None):
        super().__init__(parent)
        self.path = path or default_path()
        self.macros = []
        self.load_error = None
        self.load()

    def load(self):
        self.load_error = None
        try:
            with open(self.path, encoding="utf-8") as f:
                self.macros = load_macros(f.read())
        except FileNotFoundError:
            self.macros = []
        except MacroError as error:
            log.warning("Macros : fichier %s illisible (%s %s)", self.path, error.code, error.info)
            self.macros, self.load_error = [], error
        self.changed.emit()

    def save(self):
        """Écrit macros.yaml (OSError si le dossier n'est pas accessible en écriture)."""
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(dump_macros(self.macros))
        os.replace(tmp, self.path)          # le fichier n'est jamais à moitié écrit
        self.load_error = None

    def set_macros(self, macros):
        """Remplace la liste, l'enregistre, et prévient les vues."""
        self.macros = list(macros)
        self.save()
        self.changed.emit()

    def visible_for(self, profile_name):
        """(rang, macro) des macros qui apparaissent pour le profil machine `profile_name`."""
        return [(index, macro) for index, macro in enumerate(self.macros) if macro.shown_for(profile_name)]
