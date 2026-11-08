"""Passerelle Laser Studio Pro : range les fichiers exportés par le Studio dans les bons calques de LSP.

Sans dépendance Qt à l'import (testable seul). Utilise les modules de LSP (dxf_import, vector_import)
et les attributs de la fenêtre principale (layer_manager, vector_canvas, tab_vector_editor...).

Routage par calque DXF / groupe SVG :
  CUT      -> mode « Découpe »
  FRAME    -> mode « Marquage (Contour) » (préférence nom contenant « cadr »)
  ENGRAVE  -> mode « Gravure Remplie »
  LAYER_n  -> calque LSP dédié (créé si besoin), mode Découpe
"""
import os
import re
import unicodedata

# Identifiants internes LSP (vector_layers.LAYER_MODES) — ne pas traduire ici.
MODE_CUT = "Découpe"
MODE_MARK = "Marquage (Contour)"  # attention : pas « Marquage » seul
MODE_ENGRAVE = "Gravure Remplie"

_LAYER_N_RE = re.compile(r"^layer[_\s-]*(\d+)$", re.I)


def _norm(s):
    return unicodedata.normalize("NFD", str(s or "").lower()).encode("ascii", "ignore").decode()


def kind_for_layer_name(name):
    """Retourne ('cut'|'mark'|'engrave'|'multi', detail).

    detail = numéro de plaque pour 'multi', sinon None.
    """
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
    mode = {"cut": MODE_CUT, "mark": MODE_MARK, "engrave": MODE_ENGRAVE}[kind]
    cands = [l for l in layers if getattr(l, "mode", None) == mode]
    if kind == "mark":
        named = [l for l in cands if "cadr" in _norm(getattr(l, "name", ""))]
        cands = named or cands
    return cands[0] if cands else None


def ensure_multi_layer(layer_manager, index, color=None):
    """Calque LSP pour une plaque multicouche Studio (LAYER_n). Créé si absent."""
    name = f"LAYER_{index}"
    for l in layer_manager.layers:
        if _norm(getattr(l, "name", "")) == _norm(name):
            return l
    from vector_layers import LaserLayer, DEFAULT_LAYER_COLORS
    col = color or DEFAULT_LAYER_COLORS[(index - 1) % len(DEFAULT_LAYER_COLORS)]
    layer = LaserLayer(
        name=name,
        color=col,
        mode=MODE_CUT,
        power=90,
        speed=250,
        passes=1,
    )
    layer_manager.layers.append(layer)
    return layer


def _layer_key_from_source_tag(tag):
    """Extrait le nom de calque logique depuis source_tag (dxf:CUT, svg:FRAME, CUT…)."""
    tag = str(tag or "")
    if ":" in tag:
        prefix, name = tag.split(":", 1)
        if prefix.lower() in ("dxf", "svg", "g"):
            return name.strip() or tag
    return tag.strip()


def route_objects(objects, layer_manager, default_id):
    """Affecte obj.layer_id selon source_tag.

    Retourne un dict de stats : counts, missing_modes, multi_created
    """
    layers = layer_manager.layers
    counts = {"cut": 0, "mark": 0, "engrave": 0, "multi": 0}
    missing = set()
    multi_created = []
    cache = {}

    for obj in objects:
        key = _layer_key_from_source_tag(getattr(obj, "source_tag", ""))
        kind, detail = kind_for_layer_name(key)

        if kind == "multi":
            cache_key = ("multi", detail)
            if cache_key not in cache:
                before = {l.id for l in layer_manager.layers}
                layer = ensure_multi_layer(layer_manager, detail or 1)
                cache[cache_key] = layer
                if layer.id not in before:
                    multi_created.append(layer.name)
            layer = cache[cache_key]
            obj.layer_id = layer.id
            counts["multi"] += 1
            continue

        if kind not in cache:
            layer = pick_layer(layers, kind)
            cache[kind] = layer
            if layer is None:
                missing.add(kind)
        layer = cache[kind]
        if layer is not None:
            obj.layer_id = layer.id
        else:
            obj.layer_id = default_id
        counts[kind] += 1

    return {
        "counts": counts,
        "missing_modes": sorted(missing),
        "multi_created": multi_created,
    }


def import_exported_file(window, path):
    """Importe `path` (SVG ou DXF) dans l'éditeur vectoriel de LSP avec routage des calques."""
    path = os.path.abspath(path)
    try:
        if path.lower().endswith(".dxf"):
            stats = _import_dxf_routed(window, path)
        elif path.lower().endswith(".svg"):
            stats = _import_svg_routed(window, path)
        else:
            window._import_vector_file(path)
            stats = None
        _notify_import(window, path, stats)
        return stats
    except Exception as e:
        _say(window, f">>> Stencil Studio : import impossible ({e}), repli import standard.")
        try:
            window._import_vector_file(path)
        except Exception as e2:
            _say(window, f">>> Stencil Studio : échec import standard ({e2}).")
            _status(window, f"Stencil Studio : échec import — {e2}")
        return None
    finally:
        _cleanup_temp(path)


def _cleanup_temp(path):
    """Supprime le fichier s'il est dans un dossier temp typique du pont."""
    try:
        norm = path.replace("\\", "/").lower()
        if "/tmp" in norm or "temp" in norm or "stencil" in norm:
            if os.path.isfile(path):
                os.remove(path)
    except Exception:
        pass


def _say(window, text):
    try:
        window.txt_console.append(text)
    except Exception:
        pass


def _status(window, text):
    """Barre d'état LSP si dispo, sinon console."""
    try:
        if hasattr(window, "show_status_message"):
            window.show_status_message(text)
            return
    except Exception:
        pass
    _say(window, text)


def _notify_import(window, path, stats):
    base = os.path.basename(path)
    if not stats:
        _status(window, f"Stencil Studio : « {base} » importé.")
        return
    c = stats.get("counts") or {}
    parts = []
    if c.get("cut"):
        parts.append(f"découpe {c['cut']}")
    if c.get("mark"):
        parts.append(f"cadrage {c['mark']}")
    if c.get("engrave"):
        parts.append(f"gravure {c['engrave']}")
    if c.get("multi"):
        parts.append(f"plaques {c['multi']}")
    detail = ", ".join(parts) if parts else "objets"
    msg = f"Stencil Studio : {detail} importés depuis « {base} »."
    missing = stats.get("missing_modes") or []
    if missing:
        labels = {"cut": "Découpe", "mark": "Marquage (Contour)", "engrave": "Gravure Remplie"}
        miss = ", ".join(labels.get(m, m) for m in missing)
        msg += f" — Attention : aucun calque {miss} (objets sur le calque par défaut)."
    created = stats.get("multi_created") or []
    if created:
        msg += f" Calques créés : {', '.join(created)}."
    _say(window, ">>> " + msg)
    _status(window, msg)


def _import_dxf_routed(window, path):
    import dxf_import
    from vector_import import dxf_to_objects

    layers = window.layer_manager.layers
    if not layers:
        raise RuntimeError("aucun calque")
    default_layer = window.layer_manager.default_svg_layer()
    drawing = dxf_import.read_dxf(path)
    objects = dxf_to_objects(drawing, default_layer.id)
    if not objects:
        raise RuntimeError("DXF vide")
    stats = route_objects(objects, window.layer_manager, default_layer.id)
    canvas = window.vector_canvas
    canvas.push_undo_snapshot()
    items = [canvas.add_object(o) for o in objects]
    _refresh_layers_ui(window)
    window.main_tabs_view.setCurrentWidget(window.tab_vector_editor)
    canvas.request_recenter(items)
    return stats


def _import_svg_routed(window, path):
    from vector_layers import extract_svg_objects

    layers = window.layer_manager.layers
    if not layers:
        raise RuntimeError("aucun calque")
    default_layer = window.layer_manager.default_svg_layer()
    bed_h = 300.0
    try:
        bed_h = float(window.spin_machine_h.value())
    except Exception:
        pass
    objects = extract_svg_objects(
        path, default_layer.id, bed_h, ungroup=True
    )
    if not objects:
        raise RuntimeError("SVG vide")
    stats = route_objects(objects, window.layer_manager, default_layer.id)
    canvas = window.vector_canvas
    canvas.push_undo_snapshot()
    items = [canvas.add_object(o) for o in objects]
    _refresh_layers_ui(window)
    window.main_tabs_view.setCurrentWidget(window.tab_vector_editor)
    canvas.request_recenter(items)
    return stats


def _refresh_layers_ui(window):
    try:
        w = getattr(window, "layer_manager_widget", None)
        if w is not None and hasattr(w, "rebuild"):
            w.rebuild()
        elif w is not None and hasattr(w, "refresh"):
            w.refresh()
    except Exception:
        pass
