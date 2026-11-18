"""Catalogue de la bibliothèque de modèles : catégories et modèles trouvés
dans les dossiers resources/library/, sans Qt.

Organisation (voir resources/library/README.md) :

    resources/library/
        trophees/                      <- une catégorie par dossier
            _category.json             <- facultatif : nom dans chaque langue
            totem-brevet-aviron/       <- un modèle par dossier
                totem.svg              <- le modèle (le premier .svg du dossier)
                totem_photo.jpg        <- facultatif : photo de la pièce réalisée
                                          (nom contenant « photo » ou « preview ») ;
                                          l'aperçu, lui, est calculé à partir du SVG
                readme.txt             <- facultatif : texte de la fiche détail
                info.json              <- facultatif : titre, auteur, licence, description

Les dossiers resources/library/ à côté de l'exécutable et dans le bundle
sont tous lus : on peut ajouter des modèles sans recompiler.
"""
import json
import os
from dataclasses import dataclass, field

LIBRARY_DIRNAME = "library"
CATEGORY_FILE = "_category.json"
INFO_FILE = "info.json"
README_NAMES = ("readme.txt", "README.txt", "readme.md", "README.md", "LISEZMOI.txt", "lisezmoi.txt")
PREVIEW_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


@dataclass
class LibraryItem:
    """Un modèle : `key` (« catégorie/dossier »), `title`, `svg_path`,
    `preview_path` (photo fournie avec le modèle, ou None ; l'aperçu, lui,
    est toujours calculé à partir du SVG),
    `readme` (texte, ou ""), et les informations de info.json."""
    key: str
    category: str
    title: str
    svg_path: str
    preview_path: str = None
    readme: str = ""
    author: str = ""
    license: str = ""
    description: str = ""
    tags: list = field(default_factory=list)

    def matches(self, text):
        """Vrai si `text` apparaît dans le titre, la description ou les mots-clés."""
        needle = _plain(text)
        haystack = " ".join([self.title, self.description, " ".join(self.tags)])
        return needle in _plain(haystack)


@dataclass
class LibraryCategory:
    key: str
    title: str
    items: list = field(default_factory=list)


def _plain(text):
    table = str.maketrans("àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ", "aaaeeeeiioouuucAAAEEEEIIOOUUUC")
    return (text or "").lower().translate(table)


def pretty_name(name):
    """« totem-brevet_aviron » -> « Totem brevet aviron »."""
    text = name.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else name


def _localized(value, language):
    """Texte d'un champ JSON : chaîne, ou {"fr": ..., "en": ...} (langue
    demandée, sinon français, sinon anglais, sinon la première)."""
    if isinstance(value, dict):
        for lang in (language, "fr", "en"):
            if value.get(lang):
                return str(value[lang])
        return str(next(iter(value.values()), ""))
    return "" if value is None else str(value)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _read_text(path):
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(path, encoding=encoding) as f:
                return f.read().replace("\r\n", "\n")
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def _find_preview(folder, files):
    """Photo : une image dont le nom contient « photo », « preview » ou
    « apercu », sinon None."""
    images = sorted(f for f in files if f.lower().endswith(PREVIEW_EXTENSIONS))
    for name in images:
        lower = name.lower()
        if any(word in lower for word in ("photo", "preview", "apercu", "aperçu")):
            return os.path.join(folder, name)
    return None


def load_item(folder, category, language="fr"):
    """Modèle du dossier `folder`, ou None s'il n'y a pas de SVG."""
    try:
        files = sorted(os.listdir(folder))
    except OSError:
        return None
    svgs = [f for f in files if f.lower().endswith(".svg")]
    if not svgs:
        return None
    info = _read_json(os.path.join(folder, INFO_FILE)) if INFO_FILE in files else {}
    readme = ""
    for name in README_NAMES:
        if name in files:
            readme = _read_text(os.path.join(folder, name))
            break
    svg = info.get("svg") if info.get("svg") in svgs else svgs[0]
    name = os.path.basename(folder)
    tags = info.get("tags") or []
    return LibraryItem(
        key=f"{category}/{name}",
        category=category,
        title=_localized(info.get("title"), language) or pretty_name(name),
        svg_path=os.path.join(folder, svg),
        preview_path=_find_preview(folder, files),
        readme=_localized(info.get("readme"), language) or readme,
        author=_localized(info.get("author"), language),
        license=_localized(info.get("license"), language),
        description=_localized(info.get("description"), language),
        tags=[str(t) for t in tags] if isinstance(tags, list) else [],
    )


def load_catalog(roots, language="fr"):
    """Catégories (triées par nom, modèles triés par titre) des dossiers
    `roots` : chaque sous-dossier est une catégorie, chacun de ses
    sous-dossiers un modèle. Une même catégorie présente dans plusieurs
    racines regroupe leurs modèles ; un même modèle n'est lu qu'une fois (la
    première racine l'emporte). Les catégories vides sont omises."""
    categories = {}
    seen = set()
    for root in roots:
        try:
            names = sorted(os.listdir(root))
        except OSError:
            continue
        for cat_name in names:
            cat_dir = os.path.join(root, cat_name)
            if cat_name.startswith((".", "_")) or not os.path.isdir(cat_dir):
                continue
            category = categories.get(cat_name)
            if category is None:
                meta = _read_json(os.path.join(cat_dir, CATEGORY_FILE))
                title = _localized(meta.get("title", meta) if meta else None, language)
                category = LibraryCategory(cat_name, title or pretty_name(cat_name))
                categories[cat_name] = category
            for item_name in sorted(os.listdir(cat_dir)):
                item_dir = os.path.join(cat_dir, item_name)
                key = f"{cat_name}/{item_name}"
                if key in seen or item_name.startswith((".", "_")) or not os.path.isdir(item_dir):
                    continue
                item = load_item(item_dir, cat_name, language)
                if item is not None:
                    seen.add(key)
                    category.items.append(item)
    result = [c for c in categories.values() if c.items]
    for category in result:
        category.items.sort(key=lambda i: _plain(i.title))
    return sorted(result, key=lambda c: _plain(c.title))


def library_roots():
    """Dossiers resources/library/ existants : à côté de l'exécutable, puis
    dans le bundle (ou à la racine du projet, sans PyInstaller)."""
    from laser_studio.core.paths import RESOURCES_DIRNAME, resource_candidates
    roots = []
    for path in resource_candidates(LIBRARY_DIRNAME):
        # Seulement les dossiers resources/library (pas un dossier « library »
        # quelconque à côté de l'exécutable, ni ce paquet Python).
        if os.path.basename(os.path.dirname(path)) != RESOURCES_DIRNAME:
            continue
        real = os.path.realpath(path)
        if os.path.isdir(path) and real not in roots:
            roots.append(real)
    return roots
