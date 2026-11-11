"""Mémoire des calques par machine : réglages (vitesse, puissance,
passes...) enregistrés dans chaque profil machine et réappliqués, sans Qt."""

# Réglages repris d'un profil machine quand on CHANGE de machine en cours de
# session (le nom, la couleur et l'identité des calques ne bougent pas : les
# objets du canevas y sont rattachés par identifiant), avec leur type.
LAYER_SETTING_CASTS = (
    ("mode", str),
    ("power", float),
    ("speed", int),
    ("passes", int),
    ("line_interval", float),
    ("line_interval_linked", bool),
    ("enabled", bool),
)


def coerce_layer_settings(layer, source, reset_invalid=False):
    """Copie les réglages de `source` (dictionnaire) vers `layer` en forçant
    le bon type.

    Une valeur inutilisable est ignorée (le calque garde sa valeur) ; avec
    reset_invalid=True (calque tout juste chargé, dont la valeur corrompue
    est déjà en place), elle est remplacée par la valeur par défaut d'un
    calque neuf.
    """
    try:
        from vector_layers import LAYER_MODES
    except ImportError:
        LAYER_MODES = None
    defaults = type(layer)() if reset_invalid else None
    for key, cast in LAYER_SETTING_CASTS:
        if key not in source:
            continue
        try:
            value = cast(source[key])
            if (
                key == "mode"
                and LAYER_MODES is not None
                and value not in LAYER_MODES
            ):
                raise ValueError(value)
        except (TypeError, ValueError):
            if defaults is not None:
                setattr(layer, key, getattr(defaults, key))
            continue
        setattr(layer, key, value)


def apply_saved_layers(layer_manager, saved_layers, full=False):
    """Applique les calques mémorisés dans un profil machine. Renvoie True
    s'il y en avait (False : rien n'a changé).

    full=True (démarrage) : remplace entièrement la liste des calques.
    full=False (changement de machine en cours de session) : ne reprend que
    les réglages, appliqués aux calques existants, retrouvés par
    identifiant puis, à défaut, par position. Les calques ne sont ni
    ajoutés, ni supprimés, ni renommés : sinon des objets du canevas
    perdraient leur calque et ne seraient plus gravés. Un profil sans
    calques mémorisés (ancien profil) ne change rien.
    """
    if not saved_layers or not isinstance(saved_layers, list):
        return False
    saved_layers = [d for d in saved_layers if isinstance(d, dict)]
    if not saved_layers:
        return False
    if full:
        layer_manager.load_list(saved_layers)
        # Valeurs corrompues dans les réglages enregistrés : on retombe sur un
        # type valide plutôt que de planter à l'ouverture.
        for layer in layer_manager.layers:
            coerce_layer_settings(layer, layer.to_dict(), reset_invalid=True)
    else:
        by_id = {d.get("id"): d for d in saved_layers}
        for i, layer in enumerate(layer_manager.layers):
            d = by_id.get(layer.id) or (
                saved_layers[i] if i < len(saved_layers) else None
            )
            if d:
                coerce_layer_settings(layer, d)
    return True
