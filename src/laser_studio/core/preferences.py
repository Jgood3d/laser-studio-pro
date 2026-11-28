"""Préférences mémorisées de Laser Studio Pro (QSettings), en un seul endroit.

    from laser_studio.core.preferences import ui_preferences

    prefs = ui_preferences()
    prefs.get_bool("show_job_queue", True)
    prefs.set("app_theme", "new_dusk")      # écrit tout de suite (Windows compris)

Trois fichiers de réglages : `ui_preferences()` (UIConfig : interface, thème,
langue, onglets, projets récents…), `machine_preferences()` (MachineConfig :
plateau, profils machine, résolution) et `app_preferences()` (réglages par
défaut de l'application : caméra, matière de l'aperçu 2D).

Les valeurs relues sont converties (`get_bool`, `get_int`, `get_float`,
`get_list`) : selon le système, QSettings rend "true" / "1" au lieu de True,
une chaîne au lieu d'un nombre, ou une chaîne seule au lieu d'une liste.

Tests : `with in_memory():` remplace les vrais fichiers par des dictionnaires,
sans rien écrire chez l'utilisateur.
"""
from contextlib import contextmanager

from PyQt6.QtCore import QSettings

ORGANIZATION = "LaserStudioPro"
UI_CONFIG = "UIConfig"
MACHINE_CONFIG = "MachineConfig"
APP_CONFIG = None                  # réglages par défaut de l'application (QSettings())

_TRUE = (True, "true", "True", "1", 1)


class MemoryStore:
    """Magasin en mémoire, avec les méthodes de QSettings utilisées ici (tests)."""

    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def sync(self):
        pass


class Preferences:
    """Réglages d'un fichier : lecture convertie avec une valeur par défaut, écriture immédiate."""

    def __init__(self, store):
        self.store = store

    def get(self, key, default=None):
        return self.store.value(key, default)

    def get_bool(self, key, default=False):
        value = self.store.value(key, None)
        return default if value is None else value in _TRUE

    def get_int(self, key, default=0):
        try:
            return int(self.store.value(key, default))
        except (TypeError, ValueError):
            return default

    def get_float(self, key, default=0.0):
        try:
            return float(self.store.value(key, default))
        except (TypeError, ValueError):
            return default

    def get_list(self, key):
        """Liste mémorisée ([] si absente) ; une valeur seule devient une liste d'un élément."""
        value = self.store.value(key, None)
        if value is None or value == "":
            return []
        return list(value) if isinstance(value, (list, tuple)) else [value]

    def set(self, key, value):
        self.store.setValue(key, value)
        self.store.sync()  # écriture immédiate sous Windows

    def remove(self, key):
        self.store.remove(key)
        self.store.sync()


# Magasins en mémoire actifs (in_memory), par fichier ; None : vrais fichiers.
_memory = None


def _preferences(application):
    if _memory is not None:
        return Preferences(_memory.setdefault(application, MemoryStore()))
    store = QSettings() if application is None else QSettings(ORGANIZATION, application)
    return Preferences(store)


def ui_preferences():
    return _preferences(UI_CONFIG)


def machine_preferences():
    return _preferences(MACHINE_CONFIG)


def app_preferences():
    return _preferences(APP_CONFIG)


@contextmanager
def in_memory(ui=None, machine=None, app=None):
    """Pendant le bloc, les préférences sont des dictionnaires (valeurs de départ en paramètres) ;
    renvoie {fichier: MemoryStore} pour relire ce qui a été écrit."""
    global _memory
    previous = _memory
    _memory = {UI_CONFIG: MemoryStore(ui), MACHINE_CONFIG: MemoryStore(machine), APP_CONFIG: MemoryStore(app)}
    try:
        yield _memory
    finally:
        _memory = previous
