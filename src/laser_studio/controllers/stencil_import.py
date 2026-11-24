"""Fichiers exportés par Stencil Studio : rangement des objets dans les
calques de LSP selon le calque DXF / groupe SVG d'origine.

    stats = route_objects(objects, layers_model, default_id, focal=machine.focal)
    status.emit(import_summary("motif.svg", stats))

Routage (nom du calque DXF ou du groupe SVG, dans `obj.source_tag`) :
  CUT      -> calque en mode Découpe
  FRAME    -> calque en mode Marquage (de préférence un nom contenant « cadr »)
  ENGRAVE  -> calque en mode Gravure remplie
  LAYER_n  -> calque LSP dédié à la plaque n (créé si besoin), mode Découpe

L'import lui-même (lecture du fichier, ajout dans l'éditeur, repli) est
fait par VectorEditorController.import_stencil_export.
"""
import os
import re
import unicodedata

from laser_studio.i18n import tr
from laser_studio.models.layer_modes import MODE_CUT, MODE_FILL, MODE_MARK
from laser_studio.models.layers import DEFAULT_LAYER_COLORS, LaserLayer

_LAYER_N_RE = re.compile(r"^layer[_\s-]*(\d+)$", re.I)
_MODE_OF_KIND = {"cut": MODE_CUT, "mark": MODE_MARK, "engrave": MODE_FILL}
_LABEL_OF_KIND = {"cut": "layers.mode.cut", "mark": "layers.mode.mark", "engrave": "layers.mode.fill"}
# Réglages d'une plaque créée sans calque Découpe à imiter : valeurs « découpe » de LayersModel.
DEFAULT_CUT_SETTINGS = (90.0, 250, 1)
# Pas de remplissage d'une plaque sans focale connue ni calque lié à la focale.
DEFAULT_LINE_INTERVAL = 0.10


def _norm(s):
    return unicodedata.normalize("NFD", str(s or "").lower()).encode("ascii", "ignore").decode()


def kind_for_layer_name(name):
    """('cut' | 'mark' | 'engrave' | 'multi', détail) : détail = numéro de plaque pour 'multi', sinon None."""
    n = _norm(name).strip()
    if not n:
        return "cut", None
    if n in ("frame", "cadrage", "mark", "marquage", "contour"):
        return "mark", None
    if n in ("engrave", "gravure", "fill", "rempli"):
        return "engrave", None
    m = _LAYER_N_RE.match(n.replace(" ", ""))
    if m:
        return "multi", int(m.group(1))
    if n.startswith("layer"):
        digits = "".join(ch for ch in n if ch.isdigit())
        if digits:
            return "multi", int(digits)
    return "cut", None


def pick_layer(layers, kind):
    """Premier calque de LSP correspondant à `kind` ('cut' | 'mark' | 'engrave'), ou None."""
    cands = [layer for layer in layers if layer.mode == _MODE_OF_KIND[kind]]
    if kind == "mark":
        named = [layer for layer in cands if "cadr" in _norm(layer.name)]
        cands = named or cands
    return cands[0] if cands else None


def layer_key_from_source_tag(tag):
    """Nom de calque logique d'après source_tag (dxf:CUT, svg:FRAME, CUT…)."""
    tag = str(tag or "")
    if ":" in tag:
        prefix, name = tag.split(":", 1)
        if prefix.lower() in ("dxf", "svg", "g"):
            return name.strip() or tag
    return tag.strip()


def ensure_multi_layer(layers_model, index, focal=None):
    """Calque LSP de la plaque `index` d'un multicouche (LAYER_n), créé s'il manque.

    Puissance, vitesse et passes : celles du premier calque Découpe (valeurs
    typiques de découpe sinon). Pas de remplissage : la focale de la machine,
    lien à la focale activé (comme « + Calque ») ; à défaut celui d'un calque
    déjà lié à la focale, sinon 0,10 mm."""
    name = f"LAYER_{index}"
    for layer in layers_model.layers:
        if _norm(layer.name) == _norm(name):
            return layer
    ref = pick_layer(layers_model.layers, "cut")
    power, speed, passes = (ref.power, ref.speed, ref.passes) if ref is not None else DEFAULT_CUT_SETTINGS
    if focal is not None and focal > 0:
        line_interval, linked = focal, True
    else:
        source = next((layer for layer in layers_model.layers
                       if layer.line_interval_linked and layer.line_interval > 0), None)
        line_interval, linked = (source.line_interval, True) if source else (DEFAULT_LINE_INTERVAL, False)
    layer = LaserLayer(name=name, color=DEFAULT_LAYER_COLORS[(index - 1) % len(DEFAULT_LAYER_COLORS)],
                       mode=MODE_CUT, power=power, speed=speed, passes=passes,
                       line_interval=line_interval, line_interval_linked=linked)
    return layers_model.append_layer(layer)


def route_tree(objects, layers_model, default_id, focal=None):
    """Comme route_objects, pour l'arbre d'un SVG importé (vector/svg_tree_import.py) : chaque tracé est
    rangé d'après le nom de son plus proche groupe (CUT, FRAME, ENGRAVE, LAYER_n), puis chaque groupe
    reprend le calque de ses objets. Les objets cachés dans le fichier (calque « Ignoré ») y restent."""
    leaves, groups = [], []

    def collect(obj, group_name):
        children = getattr(obj, "children", None)
        if children is None:
            if not obj.is_ignored():
                obj.source_tag = f"svg:{group_name}"
                leaves.append(obj)
            return
        groups.append(obj)
        name = (getattr(obj, "name", "") or "").strip() or group_name
        for child in children:
            collect(child, name)

    for obj in objects:
        collect(obj, "")
    stats = route_objects(leaves, layers_model, default_id, focal)
    for group in reversed(groups):          # les sous-groupes d'abord, puis ceux qui les contiennent
        group.child_ignored_changed()
    return stats


def route_objects(objects, layers_model, default_id, focal=None):
    """Affecte obj.layer_id selon obj.source_tag. Renvoie les statistiques :
    {"counts": {cut, mark, engrave, multi}, "missing_modes": [...], "multi_created": [noms]}."""
    counts = {"cut": 0, "mark": 0, "engrave": 0, "multi": 0}
    missing = set()
    multi_created = []
    cache = {}
    for obj in objects:
        kind, detail = kind_for_layer_name(layer_key_from_source_tag(getattr(obj, "source_tag", "")))
        if kind == "multi":
            key = ("multi", detail)
            if key not in cache:
                before = {layer.id for layer in layers_model.layers}
                cache[key] = ensure_multi_layer(layers_model, detail or 1, focal)
                if cache[key].id not in before:
                    multi_created.append(cache[key].name)
            obj.layer_id = cache[key].id
            counts["multi"] += 1
            continue
        if kind not in cache:
            cache[kind] = pick_layer(layers_model.layers, kind)
            if cache[kind] is None:
                missing.add(kind)
        obj.layer_id = cache[kind].id if cache[kind] is not None else default_id
        counts[kind] += 1
    return {"counts": counts, "missing_modes": sorted(missing), "multi_created": multi_created}


def import_summary(path, stats):
    """Message de la barre d'état après l'import de `path` (stats de route_objects, ou None)."""
    name = os.path.basename(path)
    if not stats:
        return tr("stencil.imported").format(name=name)
    counts = stats.get("counts") or {}
    parts = [tr(f"stencil.count_{kind}").format(n=counts[kind])
             for kind in ("cut", "mark", "engrave", "multi") if counts.get(kind)]
    message = tr("stencil.imported_detail").format(detail=", ".join(parts) or tr("stencil.objects"), name=name)
    missing = stats.get("missing_modes") or []
    if missing:
        message += tr("stencil.missing_layers").format(modes=", ".join(tr(_LABEL_OF_KIND[m]) for m in missing))
    created = stats.get("multi_created") or []
    if created:
        message += tr("stencil.created_layers").format(names=", ".join(created))
    return message


def remove_temporary_export(path):
    """Supprime le fichier exporté s'il est dans un dossier temporaire (téléchargement de la page du Studio)."""
    norm = path.replace("\\", "/").lower()
    if ("/tmp" in norm or "temp" in norm or "stencil" in norm) and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
