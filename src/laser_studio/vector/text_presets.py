"""Préréglages du texte (police, taille, disposition sur un cercle ou un contour) : des jeux de réglages
nommés, enregistrés dans un fichier JSON du dossier de données de l'utilisateur. Sans Qt. Le texte lui-même,
sa position, son calque et son contour ne sont pas mémorisés (ils dépendent du projet)."""
import json
import os

PRESET_FILE = "text_presets.json"

# Réglages mémorisés : nom de l'attribut de TextObject -> type attendu (contrôle à la lecture).
KEYS = {
    "font_family": str, "bold": bool, "italic": bool, "size_mm": float, "letter_spacing_mm": float,
    "text_anchor": str, "arc_radius_mm": float, "arc_inside": bool,
    "follow_reverse": bool, "follow_gap_mm": float,
}


def default_path():
    from laser_studio.core.paths import get_autosave_dir
    return os.path.join(get_autosave_dir(), PRESET_FILE)


def clean(settings):
    """Seulement les réglages connus, convertis dans leur type ; le reste est ignoré."""
    out = {}
    for key, kind in KEYS.items():
        if key in settings:
            try:
                out[key] = kind(settings[key])
            except (TypeError, ValueError):
                pass
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
    return {str(k): clean(v) for k, v in data.items() if isinstance(v, dict)}


def _write(path, data):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        return False
    return True


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
