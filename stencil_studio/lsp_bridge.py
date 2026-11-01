"""Passerelle Laser Studio Pro : range les fichiers exportés par le Studio dans les bons calques de LSP.

Sans dépendance Qt à l'import (testable seul). Utilise les modules de LSP (dxf_import, vector_import)
et les attributs de la fenêtre principale (layer_manager, vector_canvas, tab_vector_editor...).

Routage par calque DXF :  CUT -> calque en mode « Découpe » ;  FRAME -> calque en mode « Marquage »
(de préférence nommé « Cadrage ») ;  ENGRAVE -> calque en mode « Gravure Remplie ».
"""
import unicodedata

MODE_CUT = "Découpe"
MODE_MARK = "Marquage"
MODE_ENGRAVE = "Gravure Remplie"


def _norm(s):
    return unicodedata.normalize("NFD", str(s or "").lower()).encode("ascii", "ignore").decode()


def kind_for_layer_name(name):
    n = _norm(name).strip()
    if n in ("frame", "cadrage", "mark", "marquage"):
        return "mark"
    if n in ("engrave", "gravure"):
        return "engrave"
    return "cut"


def pick_layer(layers, kind):
    """Premier calque de LSP correspondant à `kind` ('cut' | 'mark' | 'engrave'), ou None."""
    mode = {"cut": MODE_CUT, "mark": MODE_MARK, "engrave": MODE_ENGRAVE}[kind]
    cands = [l for l in layers if getattr(l, "mode", None) == mode]
    if kind == "mark":
        named = [l for l in cands if "cadr" in _norm(getattr(l, "name", ""))]
        cands = named or cands
    return cands[0] if cands else None


def route_objects(objects, layers, default_id):
    """Affecte obj.layer_id selon la couche DXF d'origine (obj.source_tag = 'dxf:<couche>').
    Retourne {'cut': n, 'mark': n, 'engrave': n}. Un type sans calque correspondant reste sur `default_id`."""
    counts = {"cut": 0, "mark": 0, "engrave": 0}
    cache = {}
    for obj in objects:
        tag = str(getattr(obj, "source_tag", "") or "")
        name = tag.split(":", 1)[1] if tag.startswith("dxf:") else ""
        kind = kind_for_layer_name(name)
        if kind not in cache:
            cache[kind] = pick_layer(layers, kind)
        layer = cache[kind]
        if layer is not None:
            obj.layer_id = layer.id
        counts[kind] += 1
    return counts


def import_exported_file(window, path):
    """Importe `path` (SVG ou DXF) dans l'éditeur vectoriel de LSP. Pour un DXF, les objets sont rangés dans
    les calques Découpe / Cadrage / Gravure ; sinon (SVG, ou échec) on utilise l'import standard de LSP."""
    if path.lower().endswith(".dxf"):
        try:
            return _import_dxf_routed(window, path)
        except Exception as e:  # repli sur l'import standard
            _say(window, f">>> Stencil Studio : routage des calques impossible ({e}), import standard.")
    window._import_vector_file(path)
    return None


def _say(window, text):
    try:
        window.txt_console.append(text)
    except Exception:
        pass


def _import_dxf_routed(window, path):
    import dxf_import                                   # modules de LSP (absolus)
    from vector_import import dxf_to_objects
    layers = window.layer_manager.layers
    if not layers:
        raise RuntimeError("aucun calque")
    default_layer = window.layer_manager.default_svg_layer()
    drawing = dxf_import.read_dxf(path)
    objects = dxf_to_objects(drawing, default_layer.id)
    if not objects:
        raise RuntimeError("DXF vide")
    counts = route_objects(objects, layers, default_layer.id)
    canvas = window.vector_canvas
    canvas.push_undo_snapshot()
    items = [canvas.add_object(o) for o in objects]
    window.main_tabs_view.setCurrentWidget(window.tab_vector_editor)
    canvas.request_recenter(items)
    _say(window, f">>> Stencil Studio : {len(objects)} objets importés "
                 f"(découpe {counts['cut']}, cadrage {counts['mark']}, gravure {counts['engrave']}).")
    return counts
