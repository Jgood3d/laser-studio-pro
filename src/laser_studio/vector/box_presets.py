"""Préréglages du générateur de boîte : des jeux de réglages nommés, enregistrés dans un fichier JSON du dossier
de données de l'utilisateur. Sans Qt. Les calques et les décors ne sont pas mémorisés (ils dépendent du projet)."""
import json
import os

PRESET_FILE = "box_presets.json"
_PROJECT_KEYS = ("cut_layer", "engrave_layer", "decors")

# Préréglages fournis : clé -> réglages (le nom affiché vient des traductions `box.preset_<clé>`).
BUILTIN = {
    "jewelry": {"dimensions": "outer", "width": 120.0, "depth": 80.0, "height": 50.0, "thickness": 3.0,
                "lid_type": "pinned", "hinge_style": "butterfly", "pin_through": True, "dividers_x": 1,
                "dividers_y": 0, "magnets": True, "magnet_count": 2, "engrave_motif": True,
                "motif_shape": "butterfly", "motif_size": 40.0},
    "tea": {"dimensions": "outer", "width": 100.0, "depth": 100.0, "height": 80.0, "thickness": 3.0,
            "lid_type": "lip", "handle": True, "handle_radius": 10.0, "dividers_x": 0, "dividers_y": 0,
            "engrave_motif": True, "motif_shape": "leaf", "motif_size": 40.0},
}


def default_path():
    from laser_studio.core.paths import get_autosave_dir
    return os.path.join(get_autosave_dir(), PRESET_FILE)


def clean(settings):
    """Réglages sans ce qui dépend du projet (calques, décors)."""
    return {k: v for k, v in dict(settings).items() if k not in _PROJECT_KEYS}


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
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def save_user(name, settings, path=None):
    """Enregistre (ou remplace) le préréglage `name` ; renvoie False si le nom est vide ou l'écriture échoue."""
    name = name.strip()
    if not name:
        return False
    path = path or default_path()
    data = load_user(path)
    data[name] = clean(settings)
    return _write(path, data)


def delete_user(name, path=None):
    path = path or default_path()
    data = load_user(path)
    if name not in data:
        return False
    del data[name]
    return _write(path, data)


def _write(path, data):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
    except OSError:
        return False
    return True
