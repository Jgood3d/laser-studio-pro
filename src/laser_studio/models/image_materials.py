"""Matières de « Graver une image » : des jeux de réglages de CORRECTION de l'image (fond, négatif,
luminosité, contraste, gamma, netteté, algorithme de tramage). Sans Qt.

Ni la puissance ni la vitesse n'en font partie : elles dépendent de la machine et restent dans le calque
de gravure (profils matériaux de l'onglet Calques).

Deux sources, qui ne se mélangent jamais :

- BUILTIN : les matières fournies. Elles ne se modifient pas ; leur nom affiché vient des traductions
  `img.mat.<clé>` ;
- les matières de l'utilisateur, enregistrées dans un fichier JSON de son dossier de données. Enregistrer
  des réglages sous le nom d'une matière fournie crée une matière à soi : la fournie reste intacte.

    library = ImageMaterials()
    library.get("wood")                   # réglages d'une matière fournie
    key = library.save_user("Mon bois", settings.material_preset())    # -> "user:Mon bois"
    library.get(key)
    library.delete_user(key)

La clé d'une matière est ce que mémorise `ImageSettings.material` : la clé d'une matière fournie ou
« user:<nom> » ("" tant qu'aucune n'est choisie).
"""
import json
import os

from laser_common.files import atomic_write_json

PRESET_FILE = "image_materials.json"
USER_PREFIX = "user:"
GENERIC = ("dark", "light")

# Réglages portés par une matière : nom -> type. gamma × 100 (100 = 1,0).
PRESET_FIELDS = {
    "material_bg": str,
    "invert": bool,
    "brightness": int,
    "contrast": int,
    "gamma": int,
    "sharpness": int,
    "algorithm": str,
}
RANGES = {"brightness": (-100, 100), "contrast": (-100, 100), "gamma": (10, 300), "sharpness": (0, 100)}


def _preset(bg, brightness, contrast, sharpness, algorithm, gamma=100):
    """Matière fournie : le négatif suit le fond (fond noir : le laser éclaircit ce qu'il brûle)."""
    return {"material_bg": bg, "invert": bg == "dark", "brightness": brightness, "contrast": contrast,
            "gamma": gamma, "sharpness": sharpness, "algorithm": algorithm}


# Points de départ à affiner sur la machine (et à enregistrer comme matière de l'utilisateur).
# Fond clair : le laser noircit ce qu'il brûle ; fond noir : il l'éclaircit (négatif activé).
BUILTIN = {
    "wood": _preset("light", 0, 15, 10, "Jarvis, Judice & Ninke"),
    "leather": _preset("light", 5, 10, 0, "Floyd-Steinberg"),
    "cork": _preset("light", 10, 25, 15, "Atkinson"),
    "tile_titanium_white": _preset("light", 0, 20, 10, "Stucki"),
    "slate": _preset("dark", 10, 25, 10, "Atkinson"),
    "aluminium_anodized": _preset("dark", 0, 10, 15, "Stucki"),
    "stainless": _preset("dark", 0, 15, 10, "Floyd-Steinberg"),
    "acrylic_clear": _preset("dark", 0, 15, 10, "Stucki"),
    "acrylic_black": _preset("dark", 5, 15, 10, "Stucki"),
    "glass": _preset("dark", 0, 20, 10, "Stucki"),
    "glass_painted_black": _preset("dark", 0, 15, 5, "Floyd-Steinberg"),
    "tile_black_paint": _preset("dark", 5, 15, 10, "Stucki"),
}


def default_path():
    from laser_studio.core.paths import get_autosave_dir
    return os.path.join(get_autosave_dir(), PRESET_FILE)


def _algorithms():
    try:
        from laser_studio.image.dithering import ALGORITHMS
    except ImportError:
        return None
    return ALGORITHMS


def clean(data):
    """Réglages valides d'une matière : seuls les champs connus, au bon type et dans leurs bornes ; un
    algorithme inconnu est ignoré. Le fond manquant vaut « light », le négatif manquant suit le fond."""
    if not isinstance(data, dict):
        return {}
    out = {}
    for name, cast in PRESET_FIELDS.items():
        if name not in data:
            continue
        try:
            value = cast(data[name])
        except (TypeError, ValueError):
            continue
        if name == "material_bg" and value not in GENERIC:
            continue
        if name in RANGES:
            low, high = RANGES[name]
            value = max(low, min(high, value))
        if name == "algorithm":
            known = _algorithms()
            if known is not None and value not in known:
                continue
        out[name] = value
    out.setdefault("material_bg", "light")
    out.setdefault("invert", out["material_bg"] == "dark")
    return out


def load_user(path=None):
    """{nom: réglages} lu dans le fichier ; vide si le fichier manque ou est abîmé."""
    path = path or default_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(name): clean(preset) for name, preset in data.items() if isinstance(preset, dict)}


def _write(path, data):
    """Écriture atomique : un disque plein ou un arrêt en cours d'écriture laisse l'ancien fichier intact."""
    try:
        atomic_write_json(path, data, ensure_ascii=False, indent=1)
    except (OSError, TypeError, ValueError):
        return False
    return True


class ImageMaterials:
    """Matières fournies et matières de l'utilisateur (fichier lu une fois, réécrit à chaque changement)."""

    def __init__(self, path=None):
        self._path = path
        self._user = None

    def path(self):
        return self._path or default_path()

    def _users(self):
        if self._user is None:
            self._user = load_user(self.path())
        return self._user

    def user_names(self):
        """Noms des matières de l'utilisateur, par ordre alphabétique."""
        return sorted(self._users(), key=str.casefold)

    @staticmethod
    def is_user(key):
        return isinstance(key, str) and key.startswith(USER_PREFIX) and len(key) > len(USER_PREFIX)

    @staticmethod
    def user_name(key):
        """Nom de la matière de l'utilisateur de clé `key` (\"\" si ce n'en est pas une)."""
        return key[len(USER_PREFIX):] if ImageMaterials.is_user(key) else ""

    def get(self, key):
        """Réglages de la matière `key` (copie), ou None pour une clé inconnue."""
        if key in BUILTIN:
            return dict(BUILTIN[key])
        if self.is_user(key):
            preset = self._users().get(self.user_name(key))
            return dict(preset) if preset is not None else None
        return None

    def save_user(self, name, settings):
        """Enregistre (ou remplace) la matière `name` de l'utilisateur ; renvoie sa clé, ou None si le nom
        est vide ou si l'écriture échoue (rien n'est alors changé)."""
        name = str(name).strip()
        preset = clean(settings)
        if not name or not preset:
            return None
        data = dict(self._users())
        data[name] = preset
        if not _write(self.path(), data):
            return None
        self._user = data
        return USER_PREFIX + name

    def delete_user(self, key):
        """Supprime une matière de l'utilisateur ; les matières fournies ne se suppriment pas."""
        name = self.user_name(key)
        data = dict(self._users())
        if name not in data:
            return False
        del data[name]
        if not _write(self.path(), data):
            return False
        self._user = data
        return True
